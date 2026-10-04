"""Time-varying team ratings: do they forecast team performance better? (2026-10-04)

Research only: no shipped rating, calibration or export changes. Writes
``output/dynamic_rating.json`` and ``output/dynamic_rating.md``.

The shipped fit gives each team one ability for its whole history. If teams
improve, that ability is too high in a team's early contests and too low in its
late ones. This module measures that and tests models that let ratings move.
All of them use the shipped binary Rasch likelihood.

* ``static``: the shipped form, one ability per team.
* ``cf_filter`` (``filter_ratings``): the Codeforces-style system. Contests
  are processed in date order. Each contest is one small Rasch MAP whose team
  priors are the current ratings, and a Kalman update follows it. Between
  contests a rating's variance grows by ``q^2`` per year.
* ``dynamic`` (``smooth_fit``): one joint MAP in which each team has an
  ability per appearance day, tied by a Gaussian random walk (TrueSkill
  Through Time style). ``q = 0`` is exactly the static fit.
* Forecast add-ons:
  * a prior for new rosters from their members' earlier ratings;
  * an offset for ratings that rest on EC online rounds, applied when
    forecasting onsite contests.

Forecast protocol. At each month start from 2023-01, every model is refit on the
contests that started before that month. It then forecasts every row of that
month whose team had appeared earlier. 2023 is the tuning period;
2024-01..2026-10 is the test period. Scores:

* pairwise order accuracy within each contest (forecast vs finishing rank);
* pairwise log loss at a common scale;
* held-out solve log loss (``contest_scores``).

Contest dates are a proxy (``contest_day``): no date field exists.

    python3 -m arch_b.dynamic_rating
"""

import bisect
import collections
import json
import os
import re
import sys

import numpy as np

from arch_a import elo
from arch_a.load import _norm_member
from . import model
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, load_joint_dataset
from .model import MU0, SIGMA_B, SIGMA_THETA
from .run import MIN_SOLVE_HOURS

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_JSON = os.path.join(ROOT, "output", "dynamic_rating.json")
OUT_MD = os.path.join(ROOT, "output", "dynamic_rating.md")
SOURCES = ([("tagged", TAGGED), ("older", OLDER_ICPC), ("petroz", PETROZ), ("wf", WF)]
           + [("ucup", p) for p in UCUP])
YEAR = 365.25
SEED = 20261004
PAIR_SCALE = 1.25        # P(i above j) = sigma((f_i - f_j) / (PAIR_SCALE * S)); best for every model
ONLINE_OFFSET = 100.0    # binary online-minus-onsite offset (+102 [+88, +117], fit_mechanism_audit)
TEST_FROM = "2024-01-01"

# QOJ contest ids grow with creation time. These contests were created within days
# of being held (XCPCIO start dates; online rounds and Petrozavodsk camps by month).
ID_ANCHORS = [(819, "2022-02-01"), (1009, "2022-08-23"), (1051, "2022-11-13"),
              (1099, "2023-01-14"), (1435, "2023-11-05"), (1516, "2023-12-10"),
              (1794, "2024-09-15"), (1821, "2024-10-27"), (1885, "2024-12-22"),
              (2513, "2025-09-14"), (4071, "2026-09-13")]
_CHAMPIONSHIP = re.compile(r"championship|world final", re.I)


def _day(iso):
    return float(np.datetime64(iso, "D").astype(int))


def _year(day):
    return int(np.datetime64(int(day), "D").astype("datetime64[Y]").astype(int)) + 1970


def contest_day(contest, source):
    """Approximate start day (days since 1970-01-01) of one contest.

    QOJ ids are interpolated between ``ID_ANCHORS``. That is right for contests
    run live on QOJ (Universal Cup stages, recent Asia East regionals) but not for
    boards uploaded long after the event. So a contest with a ``year`` whose id
    date falls outside its season window gets the season's typical day:

    * regionals: window Aug..Feb, typical day Nov 15;
    * championships and World Finals: Jan..Oct of their own year, typical Apr 15;
    * Petrozavodsk camps by their Winter (Feb 1) / Summer (Aug 25) name;
    * EC online rounds: Sep 15 / Sep 21.

    Universal Cup files carry problem-set years, so they always use the id.
    """
    cid, year, name = contest["contest_id"], contest.get("year"), contest.get("contest_name") or ""
    by_id = float(np.interp(cid, [a for a, _ in ID_ANCHORS], [_day(d) for _, d in ID_ANCHORS]))
    if source == "ucup" or year is None:
        return by_id
    if name.startswith("EC Online"):
        return _day(f"{year}-09-15") + (6.0 if "(II)" in name else 0.0)
    if source == "petroz" and "Winter" in name:
        return _day(f"{year}-02-01")
    if source == "petroz" and "Summer" in name:
        return _day(f"{year}-08-25")
    if source == "petroz":
        lo, hi, typical = f"{year}-01-01", f"{year}-12-31", f"{year}-07-01"
    elif _CHAMPIONSHIP.search(name):
        lo, hi, typical = f"{year}-01-15", f"{year}-10-31", f"{year}-04-15"
    else:
        lo, hi, typical = f"{year}-08-01", f"{year + 1}-02-28", f"{year}-11-15"
    return by_id if _day(lo) <= by_id <= _day(hi) else _day(typical)


def raw_contests():
    """contest_id -> (source, contest) in the joint fit's dedupe order (tagged first)."""
    out = {}
    for source, path in SOURCES:
        with open(path, encoding="utf-8") as f:
            for c in json.load(f):
                out.setdefault(c["contest_id"], (source, c))
    return out


def contest_days(ds, raw):
    """Day per contest index of ``ds`` (see ``contest_day``)."""
    return np.array([contest_day(raw[c][1], raw[c][0]) for c in ds.contests])


def row_members(ds, raw):
    """Normalized member names per row (empty for rows without a roster)."""
    return [tuple(sorted({n for n in (_norm_member(m) for m in
                                       raw[cid][1]["standings"][sr].get("members") or []) if n}))
            for cid, sr in ds.participation_of_row]


# ---- the Codeforces-style filter ----

class _Sub:
    """Minimal dataset shape for ``model.fit`` on a slice of teams/problems."""

    def __init__(self, n_teams, n_problems):
        self.teams = [None] * n_teams
        self.problems = [None] * n_problems


def filter_ratings(ds, day, q=100.0, sigma0=SIGMA_THETA, snapshots=()):
    """Codeforces-style rating: process contests in date order, update after each.

    State per team: rating mean ``mu``, variance ``var`` and the day of its last
    contest. Before a contest, a team's prior is ``N(mu, var + q^2*dt)``, with
    ``dt`` in years; a new team's prior is ``N(MU0, sigma0^2)``. The contest is
    one Rasch MAP over its own cells (``model.fit``), with problems on the usual
    ``N(MU0, SIGMA_B^2)`` prior. The MAP ability becomes the new mean. The
    Laplace precision (prior plus the Fisher information of the team's cells)
    becomes the new variance.

    ``snapshots`` is a sorted list of days. For each one, the state just
    before the first contest on or after that day is returned, as
    ``(rating, last_day)`` with NaN for unseen teams.
    """
    n_teams = len(ds.teams)
    mu, var = np.full(n_teams, MU0), np.full(n_teams, sigma0 ** 2)
    last = np.full(n_teams, np.nan)
    obs_contest = ds.contest_of_row[ds.obs_row]
    order = np.argsort(obs_contest, kind="stable")
    cuts = np.searchsorted(obs_contest[order], np.arange(len(ds.contests) + 1))
    snaps, k = [], 0
    for c in np.lexsort((np.array(ds.contests), day)):
        while k < len(snapshots) and day[c] >= snapshots[k]:
            snaps.append((np.where(np.isnan(last), np.nan, mu), last.copy()))
            k += 1
        obs = order[cuts[c]:cuts[c + 1]]
        if not len(obs):
            continue
        teams, t_local = np.unique(ds.team_of_row[ds.obs_row[obs]], return_inverse=True)
        probs, p_local = np.unique(ds.obs_prob[obs], return_inverse=True)
        dt = np.nan_to_num((day[c] - last[teams]) / YEAR)
        v0 = var[teams] + q ** 2 * dt
        theta, b, _ = model.fit(_Sub(len(teams), len(probs)), prior_mu=mu[teams],
                                sigma_theta=np.sqrt(v0), verbose=False,
                                obs=(t_local, p_local, ds.obs_y[obs].astype(float)))
        p = elo.pi(theta[t_local], b[p_local])
        info = np.bincount(t_local, p * (1 - p), len(teams)) / elo.S ** 2
        mu[teams], var[teams], last[teams] = theta, 1.0 / (1.0 / v0 + info), day[c]
    while k < len(snapshots):
        snaps.append((np.where(np.isnan(last), np.nan, mu), last.copy()))
        k += 1
    return snaps


# ---- the random-walk joint fit ----

def _nodes(ds, day, rows):
    """One ability node per (team, appearance day) of ``rows``, sorted by team then day.

    Returns ``(node_of_row, node_team, node_day, first)``; ``first[n]`` is True
    for a team's earliest node, otherwise node ``n - 1`` is its predecessor.
    """
    team, row_day = ds.team_of_row[rows], day[ds.contest_of_row[rows]]
    keys, inv = np.unique(np.column_stack((team, row_day)), axis=0, return_inverse=True)
    node_of_row = np.full(len(ds.team_of_row), -1)
    node_of_row[rows] = inv.ravel()
    node_team, node_day = keys[:, 0].astype(int), keys[:, 1]
    first = np.ones(len(keys), bool)
    first[1:] = node_team[1:] != node_team[:-1]
    return node_of_row, node_team, node_day, first


def _chain_solve(diag, off, rhs, first, by_pos):
    """Solve a block-diagonal tridiagonal system, one chain per team (Thomas).

    ``off[n]`` couples node n with n - 1 (0 where ``first[n]``); ``by_pos[k]``
    lists the nodes at chain position k. Vectorized across chains.
    """
    n = len(diag)
    nxt = np.zeros(n)
    nxt[:-1] = np.where(first[1:], 0.0, off[1:])
    cp, dp = np.zeros(n), np.zeros(n)
    for k, idx in enumerate(by_pos):
        a = off[idx] if k else 0.0
        den = diag[idx] - (a * cp[idx - 1] if k else 0.0)
        cp[idx] = nxt[idx] / den
        dp[idx] = (rhs[idx] - (a * dp[idx - 1] if k else 0.0)) / den
    x = np.zeros(n + 1)                     # x[n] = 0 pads the chain ends
    for idx in reversed(by_pos):
        x[idx] = dp[idx] - cp[idx] * x[idx + 1]
    return x[:n]


def smooth_fit(ds, day, q=100.0, drift=0.0, sigma0=SIGMA_THETA, cell_mask=None,
               eps=0.5, max_iter=400):
    """Joint MAP with a random-walk ability per team (TrueSkill Through Time style).

    Each team has one ability per appearance day. Consecutive abilities differ
    by ``N(drift*dt, q^2*dt)``, with ``dt`` in years.

    The shipped ability prior ``N(MU0, sigma0^2)`` is spread over a team's K
    nodes as ``N(MU0, K*sigma0^2)`` each. That is exactly the shipped prior on
    the team's mean ability, plus a weak pull on its deviations, and it treats
    early and late nodes alike. (A prior on the first node only shrinks early
    abilities more than late ones. That invents an upward trend for strong
    teams and a downward one for weak teams.)

    Problems keep the shipped ``N(MU0, SIGMA_B^2)`` prior, so ``q = 0`` is the
    shipped binary fit (one ability per team). The objective is concave. It is
    maximised by block-coordinate Newton, with the ability block solved
    exactly as one tridiagonal system per team. ``cell_mask`` restricts the
    observed cells (e.g. contests before a date).

    Returns ``(node_theta, b, node_of_row, node_team, node_day)``. Rows without
    a cell in the mask have node -1.
    """
    m = np.ones(len(ds.obs_y), bool) if cell_mask is None else cell_mask
    node_of_row, node_team, node_day, first = _nodes(ds, day, np.unique(ds.obs_row[m]))
    obs_node, obs_prob = node_of_row[ds.obs_row[m]], ds.obs_prob[m]
    y = ds.obs_y[m].astype(float)
    n_nodes, n_probs = len(node_team), len(ds.problems)
    dt = np.zeros(n_nodes)
    dt[1:] = np.where(first[1:], 0.0, (node_day[1:] - node_day[:-1]) / YEAR)
    edge_prec = np.where(first, 0.0, 1.0 / np.maximum(q ** 2 * dt, 1e-6))
    next_prec = np.append(edge_prec[1:], 0.0)
    node_prec = 1.0 / (np.bincount(node_team)[node_team] * sigma0 ** 2)
    pos = np.zeros(n_nodes, int)
    for n in np.flatnonzero(~first):
        pos[n] = pos[n - 1] + 1
    by_pos = [np.flatnonzero(pos == k) for k in range(pos.max() + 1)]
    s2 = elo.S ** 2
    theta, b = np.full(n_nodes, MU0), np.full(n_probs, MU0)
    for _ in range(max_iter):
        p = elo.pi(theta[obs_node], b[obs_prob])
        step = np.where(first, 0.0, theta - np.roll(theta, 1) - drift * dt)
        grad = (np.bincount(obs_node, y - p, n_nodes) / elo.S - node_prec * (theta - MU0)
                - edge_prec * step + next_prec * np.append(step[1:], 0.0))
        diag = np.bincount(obs_node, p * (1 - p), n_nodes) / s2 + node_prec + edge_prec + next_prec
        new = np.clip(theta + _chain_solve(diag, -edge_prec, grad, first, by_pos), elo.LO, elo.HI)
        change, theta = np.abs(new - theta).max(), new
        p = elo.pi(theta[obs_node], b[obs_prob])
        grad = -np.bincount(obs_prob, y - p, n_probs) / elo.S - (b - MU0) / SIGMA_B ** 2
        neg_h = np.bincount(obs_prob, p * (1 - p), n_probs) / s2 + 1.0 / SIGMA_B ** 2
        new = np.clip(b + grad / neg_h, elo.LO, elo.HI)
        change, b = max(change, np.abs(new - b).max()), new
        if change < eps:
            return theta, b, node_of_row, node_team, node_day
    raise RuntimeError("random-walk fit did not converge")


# ---- forecasts ----

def month_starts(first="2023-01", last="2026-11"):
    """Month boundaries (days) of the forecast test."""
    months = np.arange(np.datetime64(first, "M"), np.datetime64(last, "M") + 1)
    return months.astype("datetime64[D]").astype(int).astype(float)


def buckets(ds, day, bounds):
    """Per row: its month bucket (-1 outside) and whether its team appeared before it."""
    row_day = day[ds.contest_of_row]
    k = np.searchsorted(bounds, row_day, side="right") - 1
    k = np.where((k >= 0) & (k < len(bounds) - 1), k, -1)
    first = np.full(len(ds.teams), np.inf)
    np.minimum.at(first, ds.team_of_row, row_day)
    seen = k >= 0
    seen[seen] = first[ds.team_of_row[seen]] < bounds[k[seen]]
    return k, seen


def bucket_ratings(ds, day, bounds, months, q=0.0, drift=0.0):
    """Per month: ``(rating, last_day)`` per team from a fit on earlier contests.

    The rating is the team's last random-walk ability (``q = 0``: the static
    ability). NaN for teams with no earlier cell.
    """
    obs_day = day[ds.contest_of_row[ds.obs_row]]
    out = {}
    for j in months:
        theta, _, _, node_team, node_day = smooth_fit(
            ds, day, q=q, drift=drift, cell_mask=obs_day < bounds[j])
        is_last = np.append(node_team[1:] != node_team[:-1], True)
        rating, last = np.full(len(ds.teams), np.nan), np.full(len(ds.teams), np.nan)
        rating[node_team[is_last]], last[node_team[is_last]] = theta[is_last], node_day[is_last]
        out[j] = (rating, last)
    return out


def team_forecasts(ds, day, k, ratings, drift=0.0):
    """Forecast per row = its team's rating at the bucket start (+ drift to the contest day)."""
    f = np.full(len(ds.team_of_row), np.nan)
    for j, (rating, last) in ratings.items():
        rows = np.flatnonzero(k == j)
        t = ds.team_of_row[rows]
        f[rows] = rating[t] + drift * (day[ds.contest_of_row[rows]] - last[t]) / YEAR
    return f


def member_ratings(ds, day, bounds, k, rows, members, ratings):
    """Mean rating of each row's members from their latest earlier team, and their count.

    For a member, the latest earlier team is the team of their last row before the
    bucket start, and its rating is that team's rating at the bucket start.
    """
    row_day = day[ds.contest_of_row]
    hist = collections.defaultdict(lambda: ([], []))
    for r in np.argsort(row_day, kind="stable"):
        for m in members[r]:
            hist[m][0].append(row_day[r])
            hist[m][1].append(ds.team_of_row[r])
    mean, count = np.full(len(row_day), np.nan), np.zeros(len(row_day), int)
    for r in rows:
        rating = ratings[k[r]][0]
        vals = []
        for m in members[r]:
            days, teams = hist[m]
            i = bisect.bisect_left(days, bounds[k[r]])
            if i:
                vals.append(rating[teams[i - 1]])
        if vals:
            mean[r], count[r] = np.mean(vals), len(vals)
    return mean, count


def row_performance(ds, b, sigma=SIGMA_THETA, iters=40):
    """One-row MAP ability given difficulties ``b`` (prior ``N(MU0, sigma^2)``)."""
    n = len(ds.team_of_row)
    perf = np.full(n, MU0)
    for _ in range(iters):
        p = elo.pi(perf[ds.obs_row], b[ds.obs_prob])
        grad = np.bincount(ds.obs_row, ds.obs_y - p, n) / elo.S - (perf - MU0) / sigma ** 2
        neg_h = np.bincount(ds.obs_row, p * (1 - p), n) / elo.S ** 2 + 1 / sigma ** 2
        perf = np.clip(perf + grad / neg_h, elo.LO, elo.HI)
    return perf


def fit_member_prior(mean, count, target, train):
    """Least squares ``target - MU0 ~ a_k + w_k (mean - MU0)`` per known-member count k."""
    coef = {}
    for kk in (1, 2, 3):
        m = train & (np.minimum(count, 3) == kk)
        x = np.column_stack((np.ones(m.sum()), mean[m] - MU0))
        coef[kk] = tuple(float(v) for v in np.linalg.lstsq(x, target[m] - MU0, rcond=None)[0])
    return coef


def apply_member_prior(mean, count, coef):
    f = np.full(len(mean), np.nan)
    for kk, (a, w) in coef.items():
        m = np.minimum(count, 3) == kk
        f[m] = MU0 + a + w * (mean[m] - MU0)
    return f


def online_share(ds, day, bounds, k, online_contest):
    """Per row: the share of its team's earlier rows (before the bucket) from EC online rounds."""
    row_day, row_online = day[ds.contest_of_row], online_contest[ds.contest_of_row]
    share = np.zeros(len(row_day))
    for j in sorted(set(k[k >= 0])):
        before = row_day < bounds[j]
        n_all = np.bincount(ds.team_of_row[before], minlength=len(ds.teams))
        n_on = np.bincount(ds.team_of_row[before], row_online[before], len(ds.teams))
        rows = np.flatnonzero(k == j)
        t = ds.team_of_row[rows]
        share[rows] = n_on[t] / np.maximum(n_all[t], 1)
    return share


# ---- scoring ----

def contest_scores(ds, rows, forecast, b_ruler):
    """Per contest of ``rows``: [correct pairs, pairs, pair log loss, cell log loss, cells].

    Pairs: every two rows of a contest with different ranks. A pair is correct
    when the forecast orders it like the finish (forecast ties count half). Its
    log loss uses ``P(i above j) = sigma((f_i - f_j) / (PAIR_SCALE * S))``.

    Cells: the rows are split into two random halves. Problem difficulties come
    from one fixed ruler for every model (``b_ruler``, the full-data static
    fit). One half's solves fit a single level offset for the contest. The
    other half's solves are then predicted from their forecasts plus that
    offset, and vice versa.
    """
    rows = np.asarray(rows)
    half = np.random.default_rng(SEED).integers(0, 2, len(ds.team_of_row))
    in_rows = np.zeros(len(ds.team_of_row), bool)
    in_rows[rows] = True
    obs = np.flatnonzero(in_rows[ds.obs_row])
    cell_row, cell_y = ds.obs_row[obs], ds.obs_y[obs].astype(float)
    cell_gap = forecast[cell_row] - b_ruler[ds.obs_prob[obs]]
    cell_contest = ds.contest_of_row[cell_row]
    contest = ds.contest_of_row[rows]
    out = {}
    for c in np.unique(contest):
        r = rows[contest == c]
        i, j = np.triu_indices(len(r), 1)
        rank = ds.rank_of_row[r]
        keep = rank[i] != rank[j]
        d = np.where(rank[i] < rank[j], 1.0, -1.0)[keep] * (forecast[r][i[keep]] - forecast[r][j[keep]])
        score = [np.sum(d > 0) + 0.5 * np.sum(d == 0), len(d),
                 np.sum(np.logaddexp(0.0, -d / (PAIR_SCALE * elo.S))), 0.0, 0]
        m = np.flatnonzero(cell_contest == c)
        h = half[cell_row[m]]
        for a, s in ((m[h == 0], m[h == 1]), (m[h == 1], m[h == 0])):
            if not len(a) or not len(s):
                continue
            offset = 0.0
            for _ in range(30):
                p = elo.pi(cell_gap[a] + offset, 0.0)
                offset += elo.S * np.sum(cell_y[a] - p) / max(np.sum(p * (1 - p)), 1e-9)
            p = np.clip(elo.pi(cell_gap[s] + offset, 0.0), 1e-9, 1 - 1e-9)
            score[3] -= np.sum(cell_y[s] * np.log(p) + (1 - cell_y[s]) * np.log(1 - p))
            score[4] += len(s)
        out[int(c)] = np.array(score, float)
    return out


def summarize(scores):
    s = np.sum(list(scores.values()), axis=0)
    return {"accuracy": s[0] / s[1], "pair_log_loss": s[2] / s[1], "cell_log_loss": s[3] / s[4],
            "pairs": int(s[1]), "cells": int(s[4]), "contests": len(scores)}


def bootstrap(scores, base, n=2000):
    """Model minus base for each metric, with a paired contest-bootstrap 95% interval."""
    keys = sorted(scores)
    a = np.array([scores[c] for c in keys])
    b = np.array([base[c] for c in keys])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(keys), (n, len(keys)))

    def metrics(x):
        s = x.sum(axis=-2)
        return np.stack((s[..., 0] / s[..., 1], s[..., 2] / s[..., 1], s[..., 3] / s[..., 4]), -1)

    diff = metrics(a) - metrics(b)
    draws = metrics(a[idx]) - metrics(b[idx])
    lo, hi = np.percentile(draws, [2.5, 97.5], axis=0)
    return {name: [float(diff[i]), float(lo[i]), float(hi[i])]
            for i, name in enumerate(("accuracy", "pair_log_loss", "cell_log_loss"))}


def row_pair_counts(ds, rows, forecast):
    """Per row: correctly ordered same-contest pairs (ties half) and its pair count."""
    rows = np.asarray(rows)
    good, total = np.zeros(len(ds.team_of_row)), np.zeros(len(ds.team_of_row))
    contest = ds.contest_of_row[rows]
    for c in np.unique(contest):
        r = rows[contest == c]
        i, j = np.triu_indices(len(r), 1)
        rank = ds.rank_of_row[r]
        keep = rank[i] != rank[j]
        i, j = i[keep], j[keep]
        d = np.where(rank[i] < rank[j], 1.0, -1.0) * (forecast[r][i] - forecast[r][j])
        score = (d > 0) + 0.5 * (d == 0)
        for side in (i, j):
            np.add.at(good, r[side], score)
            np.add.at(total, r[side], 1)
    return good, total


# ---- retrospective comparisons ----

def row_residuals(ds, theta_row, b):
    """One-step performance minus rating per row (rating points) and its information."""
    n = len(ds.team_of_row)
    p = elo.pi(theta_row[ds.obs_row], b[ds.obs_prob])
    info = np.bincount(ds.obs_row, p * (1 - p), n)
    resid = np.bincount(ds.obs_row, ds.obs_y - p, n)
    return np.clip(elo.S * resid / np.maximum(info, 1e-9), -800, 800), info


def within_team_slope(ds, day, value, weight, mask):
    """Weighted slope (per year) of ``value`` on time centred within each team."""
    t, row_day = ds.team_of_row, day[ds.contest_of_row]
    sw = np.bincount(t, weight, len(ds.teams))
    centre = np.bincount(t, weight * row_day, len(ds.teams)) / np.maximum(sw, 1e-12)
    x = (row_day - centre[t]) / YEAR
    w = weight * mask
    return float(np.sum(w * x * value) / np.sum(w * x * x))


def cf_anchor_check(ds, theta_row, b, contest_year):
    """Raw-ridge CF-anchor LOCO of binary difficulties (``de_release_audit`` protocol)."""
    from .calibration_experiment import build_anchor_table
    from .de_release_audit import loco, problem_records, with_binary
    p = elo.pi(theta_row[ds.obs_row], b[ds.obs_prob])
    se = 1 / np.sqrt(np.bincount(ds.obs_prob, p * (1 - p), len(b)) / elo.S ** 2 + 1 / SIGMA_B ** 2)
    recs = problem_records(ds, b, se)
    rows = with_binary(build_anchor_table(recs, recs), recs)
    pred, _ = loco(rows, "ridge", ("raw_b",))
    year_of = dict(zip(ds.contests, contest_year))
    years = np.array([year_of[int(r["row_id"].split(":")[1])] for r in rows])
    return rows, pred, years


# ---- experiment ----

def run():
    raw = raw_contests()
    ds, _, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    day = contest_days(ds, raw)
    contest_year = np.array([_year(d) for d in day])
    members = row_members(ds, raw)
    online_contest = np.array([raw[c][1]["contest_name"].startswith("EC Online") for c in ds.contests])
    n_rows = len(ds.team_of_row)
    multi = np.bincount(ds.team_of_row)[ds.team_of_row] >= 2
    out = {"contests": len(ds.contests), "teams": len(ds.teams), "rows": n_rows}

    # 1. Retrospective: is the static ability too high early and too low late?
    theta0, b0, nor0, _, _ = smooth_fit(ds, day, q=0.0)
    static_row = theta0[nor0]
    resid, info = row_residuals(ds, static_row, b0)
    team_theta = np.zeros(len(ds.teams))
    team_theta[ds.team_of_row] = static_row
    cuts = np.quantile(team_theta[np.bincount(ds.team_of_row) >= 2], [0, 1 / 3, 2 / 3, 1])
    tercile = np.clip(np.searchsorted(cuts, static_row, side="right") - 1, 0, 2)
    row_day = day[ds.contest_of_row]
    first_day = np.full(len(ds.teams), np.inf)
    last_day = np.full(len(ds.teams), -np.inf)
    np.minimum.at(first_day, ds.team_of_row, row_day)
    np.maximum.at(last_day, ds.team_of_row, row_day)
    span = (last_day - first_day)[ds.team_of_row]
    frac = np.where(span > 0, (row_day - first_day[ds.team_of_row]) / np.maximum(span, 1e-9), 0.5)
    long_span = (np.bincount(ds.team_of_row)[ds.team_of_row] >= 4) & (span >= 180)
    retro = {"static_residual_slope": {
        "all": within_team_slope(ds, day, resid, info, multi),
        "terciles": [within_team_slope(ds, day, resid, info, multi & (tercile == g)) for g in range(3)],
        "tercile_cuts": cuts.tolist()},
        "static_residual_by_span_fraction": {}}
    for lo, hi in [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.01)]:
        m = long_span & (frac >= lo) & (frac < hi)
        retro["static_residual_by_span_fraction"][f"{lo:.1f}-{min(hi, 1):.1f}"] = [
            float(np.sum(resid[m] * info[m]) / np.sum(info[m])), int(m.sum())]
    rows0, pred0, anchor_years = cf_anchor_check(ds, static_row, b0, contest_year)
    cf_y = np.array([r["cf"] for r in rows0])
    retro["cf_anchor"] = {"0": {"loco": float(np.sqrt(np.mean((pred0 - cf_y) ** 2))),
                                "residual_by_year": {str(y): [float(np.mean((pred0 - cf_y)[anchor_years == y])),
                                                              int(np.sum(anchor_years == y))]
                                                     for y in sorted(set(anchor_years))}}}
    from .de_release_audit import contest_bootstrap
    for q in (50.0, 100.0):
        theta, b, nor, _, _ = smooth_fit(ds, day, q=q)
        dyn_row = theta[nor]
        rows_q, pred_q, _ = cf_anchor_check(ds, dyn_row, b, contest_year)
        assert [r["row_id"] for r in rows_q] == [r["row_id"] for r in rows0]
        retro[f"q{int(q)}"] = {
            "slope_terciles": [within_team_slope(ds, day, dyn_row - static_row, info, multi & (tercile == g))
                               for g in range(3)],
            "b_shift_by_year": {str(y): float(np.mean((b - b0)[contest_year[ds.contest_of_problem] == y]))
                                for y in sorted(set(contest_year))},
            "theta_shift_by_year": {str(y): float(np.mean((dyn_row - static_row)[multi & (contest_year[ds.contest_of_row] == y)]))
                                    for y in sorted(set(contest_year))}}
        retro["cf_anchor"][str(int(q))] = {
            "loco": float(np.sqrt(np.mean((pred_q - cf_y) ** 2))),
            "minus_static": contest_bootstrap(rows0, pred_q, pred0, n=5000),
            "residual_by_year": {str(y): float(np.mean((pred_q - cf_y)[anchor_years == y]))
                                 for y in sorted(set(anchor_years))}}
    out["retrospective"] = retro

    # 2. Forecasts, month by month.
    bounds = month_starts()
    k, seen = buckets(ds, day, bounds)
    months = sorted(set(k[k >= 0]))
    test = row_day >= _day(TEST_FROM)
    tune = (k >= 0) & ~test
    ratings = {"static": bucket_ratings(ds, day, bounds, months, q=0.0)}
    forecasts = {"static": team_forecasts(ds, day, np.where(seen, k, -1), ratings["static"])}
    for q in (25.0, 50.0, 100.0):
        ratings[f"dynamic_q{int(q)}"] = bucket_ratings(ds, day, bounds, months, q=q)
        forecasts[f"dynamic_q{int(q)}"] = team_forecasts(ds, day, np.where(seen, k, -1),
                                                          ratings[f"dynamic_q{int(q)}"])
    drift_ratings = bucket_ratings(ds, day, bounds, months, q=50.0, drift=25.0)
    forecasts["dynamic_q50_drift25"] = team_forecasts(ds, day, np.where(seen, k, -1), drift_ratings, drift=25.0)
    for q in (0.0, 100.0):
        snaps = filter_ratings(ds, day, q=q, snapshots=bounds[:-1])
        forecasts[f"cf_filter_q{int(q)}"] = team_forecasts(
            ds, day, np.where(seen, k, -1), {j: snaps[j] for j in months})
    share = online_share(ds, day, bounds, k, online_contest)
    onsite = ~online_contest[ds.contest_of_row]
    for name in ("static", "dynamic_q50"):
        for g in (50.0, ONLINE_OFFSET, 150.0):
            forecasts[f"{name}+online{int(g)}"] = forecasts[name] - g * share * onsite

    # New rosters: forecast from members' earlier ratings, fitted on the tuning period.
    perf = row_performance(ds, b0)
    new = (k >= 0) & ~seen
    member_info = {}
    for name in ("static", "dynamic_q50"):
        mean, count = member_ratings(ds, day, bounds, k, np.flatnonzero(new), members, ratings[name])
        coef = fit_member_prior(mean, count, perf, new & tune & (count > 0))
        member_f = apply_member_prior(mean, count, coef)
        member_info[name] = {"coef": {str(kk): v for kk, v in coef.items()},
                             "rows_by_known_members": {str(kk): int(np.sum(new & (np.minimum(count, 3) == kk)))
                                                       for kk in (0, 1, 2, 3)}}
        known = new & (count > 0)
        if name == "static":
            forecasts["static+cold_MU0"] = np.where(known, MU0, forecasts["static"])
            forecasts["static+members"] = np.where(known, member_f, forecasts["static"])
        else:
            forecasts["dynamic_q50+online100+members"] = np.where(
                known, member_f, forecasts["dynamic_q50+online100"])
    out["members"] = member_info

    b_ruler = b0
    history = seen & (k >= 0)
    sets = {"history": history, "history_plus_new_with_members": history | known}
    results = {}
    for set_name, mask in sets.items():
        for period, pmask in (("tuning_2023", tune), ("test_2024_2026", test)):
            rows = np.flatnonzero(mask & pmask)
            names = [n for n in forecasts if not n.endswith("+members") and "cold" not in n] \
                if set_name == "history" else \
                ["static+cold_MU0", "static+members", "dynamic_q50+online100+members"]
            base_name = "static" if set_name == "history" else "static+cold_MU0"
            scores = {n: contest_scores(ds, rows, forecasts[n], b_ruler) for n in names}
            entry = {"rows": int(len(rows))}
            for n in names:
                entry[n] = summarize(scores[n])
                if n != base_name:
                    entry[n]["minus_" + base_name] = bootstrap(scores[n], scores[base_name])
            results[f"{set_name}/{period}"] = entry
            print(f"done {set_name}/{period}", file=sys.stderr, flush=True)
    out["forecast"] = results

    # Where dynamics help: test-period history rows by number of earlier appearances.
    rows = np.flatnonzero(history & test)
    prior_n = np.zeros(n_rows, int)
    for j in months:
        before = row_day < bounds[j]
        cnt = np.bincount(ds.team_of_row[before], minlength=len(ds.teams))
        sel = np.flatnonzero(k == j)
        prior_n[sel] = cnt[ds.team_of_row[sel]]
    by_history = {}
    counts = {n: row_pair_counts(ds, rows, forecasts[n]) for n in ("static", "dynamic_q50", "cf_filter_q100")}
    for lo, hi in ((1, 2), (2, 5), (5, 10), (10, 10 ** 6)):
        m = np.zeros(n_rows, bool)
        m[rows] = True
        m &= (prior_n >= lo) & (prior_n < hi)
        by_history[f"{lo}-{hi - 1 if hi < 10 ** 6 else '+'}"] = {
            "rows": int(m.sum()), **{n: float(g[m].sum() / t[m].sum()) for n, (g, t) in counts.items()}}
    out["accuracy_by_earlier_appearances"] = by_history
    return out


def _md(out):
    r = out["retrospective"]
    lines = ["# Time-varying team ratings (2026-10-04)", "",
             "Generated by `python3 -m arch_b.dynamic_rating`; details in `details.md`.", "",
             f"{out['contests']} contests, {out['teams']} teams, {out['rows']} rows (binary Rasch, joint inputs).", "",
             "## Are older appearances over-rated?", "",
             "Static-fit performance minus rating, by position in a team's observed span "
             "(teams with >= 4 rows over >= 180 days):", "",
             "| span fraction | mean residual | rows |", "|---|---|---|"]
    lines += [f"| {key} | {v[0]:+.1f} | {v[1]} |" for key, v in r["static_residual_by_span_fraction"].items()]
    s = r["static_residual_slope"]
    lines += ["", f"Within-team trend of the static residual: {s['all']:+.1f} points/year "
              f"(weak / middle / strong tercile: {s['terciles'][0]:+.1f} / {s['terciles'][1]:+.1f} / "
              f"{s['terciles'][2]:+.1f}).", "",
              "Random-walk fit minus static fit, mean by contest year (problems / multi-row teams' abilities):", "",
              "| year | " + " | ".join(f"q={q[1:]} b | q={q[1:]} theta" for q in ("q50", "q100")) + " |",
              "|---|---|---|---|---|"]
    for y in r["q50"]["b_shift_by_year"]:
        lines.append(f"| {y} | " + " | ".join(f"{r[q]['b_shift_by_year'][y]:+.1f} | {r[q]['theta_shift_by_year'][y]:+.1f}"
                                               for q in ("q50", "q100")) + " |")
    cf = r["cf_anchor"]
    lines += ["", "CF-anchor raw LOCO (binary difficulties) and mean residual (predicted − CF) by anchor year:", "",
              "| fit | LOCO | Δ vs static [95% CI] | " + " | ".join(cf["0"]["residual_by_year"]) + " |",
              "|---|---|---|" + "---|" * len(cf["0"]["residual_by_year"])]
    lines.append(f"| static | {cf['0']['loco']:.2f} | | " + " | ".join(
        f"{v[0]:+.0f} ({v[1]})" for v in cf["0"]["residual_by_year"].values()) + " |")
    for q in ("50", "100"):
        d = cf[q]["minus_static"]
        lines.append(f"| q={q} | {cf[q]['loco']:.2f} | {d['difference']:+.2f} [{d['bootstrap_2.5_97.5'][0]:+.2f}, "
                     f"{d['bootstrap_2.5_97.5'][1]:+.2f}] | " + " | ".join(f"{v:+.0f}" for v in cf[q]["residual_by_year"].values()) + " |")
    lines += ["", "## Forecasts", "",
              "Pair accuracy (higher is better), pair log loss and held-out solve log loss (lower is better); "
              "Δ vs the base with a contest-bootstrap 95% interval.", ""]
    for key, entry in out["forecast"].items():
        lines += [f"### {key} ({entry['rows']} rows)", "", "| model | accuracy | pair log loss | cell log loss | Δ accuracy | Δ cell log loss |",
                  "|---|---|---|---|---|---|"]
        for name, v in entry.items():
            if name == "rows":
                continue
            delta = next((v[x] for x in v if x.startswith("minus_")), None)
            fmt = lambda d: f"{d[0]:+.4f} [{d[1]:+.4f}, {d[2]:+.4f}]"
            lines.append(f"| {name} | {v['accuracy']:.4f} | {v['pair_log_loss']:.4f} | {v['cell_log_loss']:.5f} | "
                         f"{fmt(delta['accuracy']) if delta else ''} | {fmt(delta['cell_log_loss']) if delta else ''} |")
        lines.append("")
    lines += ["Test-period pair accuracy by the team's number of earlier appearances:", "",
              "| earlier rows | rows | static | dynamic q=50 | cf_filter q=100 |", "|---|---|---|---|---|"]
    for key, v in out["accuracy_by_earlier_appearances"].items():
        lines.append(f"| {key} | {v['rows']} | {v['static']:.4f} | {v['dynamic_q50']:.4f} | {v['cf_filter_q100']:.4f} |")
    lines += ["", "Member prior (new rosters; forecast = 2000 + a + w·(member mean − 2000), fit on 2023):", "",
              "| fit | known members | a | w | rows |", "|---|---|---|---|---|"]
    for name, v in out["members"].items():
        for kk, (a, w) in v["coef"].items():
            lines.append(f"| {name} | {kk} | {a:+.1f} | {w:.3f} | {v['rows_by_known_members'][kk]} |")
    return "\n".join(lines) + "\n"


def main():
    out = run()
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(_md(out))
    print(_md(out))


if __name__ == "__main__":
    main()
