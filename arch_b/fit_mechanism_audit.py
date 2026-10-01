"""What the binary/survival disagreement measures, and what else the fit misses (2026-09-28).

Research only, on the roster-attached candidate fit (``scripts/attach_online_rosters.py``);
writes ``output/fit_mechanism_audit.json``. Ratings and exports are unchanged.

1. Decomposition. Difficulties are refit with abilities frozen at the other
   model's values, so binary-minus-survival splits into an ability-scale part
   and a likelihood part, along both paths. Each part replaces the
   disagreement feature in DE under the same nested LOCO.
2. Ability mapping. Fitted abilities of both models against roster-complete
   Codeforces team abilities (``cf_prior.team_abilities``, 54 elite teams).
3. Timing residuals. For solved cells the survival model implies a conditional
   solve-time distribution; its PIT should be uniform (mean 0.5). Reported by
   solve order within a row, by elapsed time and by the row's total solves.
4. Online vs onsite, whole appearances held out. Rows: official EC online-round
   rows whose roster was attached (verified), regional-board rows whose roster
   matches an XCPCIO onsite team (onsite), and roster rows on the same boards
   matching none (online mirror). Teams with verified online and 2024-25
   onsite rows are split into 5 folds; each design hides one kind of row, refits
   and predicts the hidden appearances. Hiding evidence shrinks predictions the
   same way in both directions, so the paired online-minus-onsite offset
   isolates the context effect.
5. Offsets in the fit: shrunk team-season abilities (theta + delta, delta ~
   N(0, tau^2)) and an online-participation offset, scored on held-out cells
   and on the CF anchors (raw affine and DE nested LOCO).

    python3 -m arch_b.fit_mechanism_audit /tmp/tagged_rosters.json
"""

import collections
import csv
import hashlib
import json
import os
import sys

import numpy as np

from arch_a import elo
from arch_a.load import _norm_member, dedupe_contests, season_of
from . import model, survival
from .calibration_experiment import build_anchor_table
from .cf_prior import team_abilities
from .de_release_audit import (DE, bisquare_location, contest_bootstrap, loco, problem_records,
                               rmse, with_binary)
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, load_joint_dataset
from .model import MU0, SIGMA_B, SIGMA_THETA
from .predict_eval import _grouped_test_mask
from .run import MIN_SOLVE_HOURS

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT = os.path.join(ROOT, "output", "fit_mechanism_audit.json")
REGIONALS = os.path.join(ROOT, "data", "ec_online", "regional_teams.csv")
ONLINE_ROUNDS = (1794, 1799, 2513, 2524)   # rosters attached; 1485 (2023 round) has its own members
SEED = 20260928


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cells(kind, gap, y=None, rho=None):
    """P(solve by the end) and, when ``y`` is given, the per-cell residual and curvature."""
    if kind == "binary":
        q = 1 / (1 + np.exp(-gap))
        return q if y is None else (y - q, q * (1 - q))
    lam = survival.LN2 * np.exp(gap)
    return 1 - np.exp(-lam) if y is None else (y - lam * rho, lam * rho)


def fit_offsets(ds, kind, group_of_row=None, n_groups=0, tau=0.0, ctx_of_row=None, n_ctx=0,
                ctx_sd=200.0, cell_mask=None, rho=None, eps=0.5, max_iter=400):
    """MAP with row ability theta_team + delta_group + gamma_ctx (tau = 0 and no ctx is the shipped fit).

    delta ~ N(0, tau^2) per group (team-season); gamma ~ N(0, ctx_sd^2) per
    context (-1 = none). Block-coordinate Newton with 400-point step caps.
    Returns (theta, delta, gamma, b).
    """
    t_obs, p_obs, y, rho_all = survival._survival_observations(ds)
    rho = rho_all if rho is None else rho
    rows = ds.obs_row
    grp = np.zeros(len(ds.team_of_row), int) if group_of_row is None else group_of_row
    ctx = np.full(len(ds.team_of_row), n_ctx) if ctx_of_row is None else np.where(ctx_of_row < 0, n_ctx, ctx_of_row)
    m = np.ones(len(y), bool) if cell_mask is None else cell_mask
    t_obs, p_obs, y, rho, g_obs, c_obs = t_obs[m], p_obs[m], y[m], rho[m], grp[rows][m], ctx[rows][m]
    s = elo.S
    theta, b = np.full(len(ds.teams), MU0), np.full(len(ds.problems), MU0)
    delta, gamma = np.zeros(max(n_groups, 1)), np.zeros(n_ctx + 1)

    def step(param, index, mu, prec, sign, bounds):
        resid, info = _cells(kind, (theta[t_obs] + delta[g_obs] + gamma[c_obs] - b[p_obs]) / s, y, rho)
        grad, neg_h = np.zeros_like(param), np.full_like(param, prec)
        np.add.at(grad, index, resid)
        np.add.at(neg_h, index, info / s ** 2)
        return np.clip(param + np.clip((sign * grad / s - prec * (param - mu)) / neg_h, -400, 400), *bounds)

    offset = (elo.LO - MU0, elo.HI - MU0)
    for _ in range(max_iter):
        new = step(theta, t_obs, MU0, 1 / SIGMA_THETA ** 2, 1.0, (elo.LO, elo.HI))
        change, theta = np.abs(new - theta).max(), new
        if tau > 0:
            new = step(delta, g_obs, 0.0, 1 / tau ** 2, 1.0, offset)
            change, delta = max(change, np.abs(new - delta).max()), new
        new = step(b, p_obs, MU0, 1 / SIGMA_B ** 2, -1.0, (elo.LO, elo.HI))
        change, b = max(change, np.abs(new - b).max()), new
        if n_ctx:
            new = step(gamma, c_obs, 0.0, 1 / ctx_sd ** 2, 1.0, offset)
            new[-1] = 0.0
            change, gamma = max(change, np.abs(new - gamma).max()), new
        if change < eps:
            return theta, delta, gamma, b
    raise RuntimeError("offset fit did not converge")


def offset_records(ds, kind, theta, delta, gamma, b, group_of_row, ctx_of_row, n_ctx):
    """Problem records with the conditional SE of b at the fitted row abilities."""
    t_obs, p_obs, _, rho = survival._survival_observations(ds)
    grp = np.zeros(len(ds.team_of_row), int) if group_of_row is None else group_of_row
    ctx = np.full(len(ds.team_of_row), n_ctx) if ctx_of_row is None else np.where(ctx_of_row < 0, n_ctx, ctx_of_row)
    gap = (theta[t_obs] + delta[grp[ds.obs_row]] + gamma[ctx[ds.obs_row]] - b[p_obs]) / elo.S
    info = _cells(kind, gap, np.zeros(len(gap)), rho)[1]
    neg_h = np.full(len(b), 1 / SIGMA_B ** 2)
    np.add.at(neg_h, p_obs, info / elo.S ** 2)
    return problem_records(ds, b, 1 / np.sqrt(neg_h))


def b_given_theta(ds, theta, kind, init, tol=1e-2):
    """MAP difficulties with abilities frozen (each b is a 1-D concave problem)."""
    t_obs, p_obs, y, rho = survival._survival_observations(ds)
    b = init.copy()
    for _ in range(2000):
        resid, info = _cells(kind, (theta[t_obs] - b[p_obs]) / elo.S, y, rho)
        grad, neg_h = np.zeros_like(b), np.full_like(b, 1 / SIGMA_B ** 2)
        np.add.at(grad, p_obs, resid)
        np.add.at(neg_h, p_obs, info / elo.S ** 2)
        new = np.clip(b + np.clip((-grad / elo.S - (b - MU0) / SIGMA_B ** 2) / neg_h, -100, 100), elo.LO, elo.HI)
        change, b = np.abs(new - b).max(), new
        if change < tol:
            return b
    raise RuntimeError("frozen-ability refit did not converge")


def _anchor_rows(recs):
    return with_binary(build_anchor_table(recs["survival"], recs["binary"]), recs["binary"])


def decomposition(ds, fits, recs):
    (t_s, b_s), (t_b, b_b) = fits["survival"], fits["binary"]
    b_b_ts = b_given_theta(ds, t_s, "binary", b_b)     # binary likelihood, survival abilities
    b_s_tb = b_given_theta(ds, t_b, "survival", b_s)   # survival likelihood, binary abilities
    d = b_b - b_s
    parts = {"path1_ability": b_b - b_b_ts, "path1_likelihood": b_b_ts - b_s,
             "path2_likelihood": b_b - b_s_tb, "path2_ability": b_s_tb - b_s}
    out = {"disagreement_mean_sd": [float(d.mean()), float(d.std())],
           "parts": {k: {"mean": float(v.mean()), "sd": float(v.std()),
                         "share_of_disagreement_variance": float(np.cov(v, d)[0, 1] / d.var())}
                     for k, v in parts.items()},
           "binary_vs_survival_difficulty_slope": float(np.polyfit(b_s, b_b, 1)[0])}
    counts = np.bincount(ds.team_of_row, minlength=len(ds.teams))
    m = counts >= 3
    out["binary_vs_survival_ability_slope_teams_3plus_rows"] = float(np.polyfit(t_s[m], t_b[m], 1)[0])
    index = {(c, lab): i for i, (c, lab, _, _) in enumerate(ds.problems)}
    rows = _anchor_rows(recs)
    for r in rows:
        i = index[(r["contest_id"], r["problem_label"])]
        r.update({k: float(v[i]) for k, v in parts.items()})
    specs = {"DE": DE, "evidence_only": ("raw_b",) + DE[2:],
             "evidence_plus_path1_likelihood": ("raw_b", "path1_likelihood") + DE[2:],
             "evidence_plus_path1_ability": ("raw_b", "path1_ability") + DE[2:],
             "evidence_plus_both_path1_parts": ("raw_b", "path1_likelihood", "path1_ability") + DE[2:],
             "evidence_plus_path2_likelihood": ("raw_b", "path2_likelihood") + DE[2:],
             "evidence_plus_path2_ability": ("raw_b", "path2_ability") + DE[2:]}
    oof = {k: loco(rows, "ridge", f)[0] for k, f in specs.items()}
    out["nested_loco"] = {k: {"rmse": rmse(p, rows)} | ({} if k == "DE" else {"minus_DE": contest_bootstrap(rows, p, oof["DE"])})
                          for k, p in oof.items()}
    y = np.array([r["cf"] for r in rows])
    out["anchor_cf_slope"] = {"survival_b": float(np.polyfit([r["raw_b"] for r in rows], y, 1)[0]),
                              "binary_b": float(np.polyfit([r["b_bin"] for r in rows], y, 1)[0])}
    return out


def ability_mapping(ds, uf, fits):
    index = {tk: i for i, tk in enumerate(ds.teams)}
    pairs = [(index[tk], v[0]) for tk, v in team_abilities(uf).items() if tk in index]
    cf = np.array([c for _, c in pairs])
    rng = np.random.default_rng(SEED)
    out = {"teams": len(pairs)}
    for name, (theta, _) in fits.items():
        x = theta[[i for i, _ in pairs]]
        boots = [np.polyfit(x[k], cf[k], 1)[0] for k in (rng.integers(0, len(x), len(x)) for _ in range(2000))]
        out[name] = {"ols_slope": float(np.polyfit(x, cf, 1)[0]),
                     "ols_slope_bootstrap_2.5_97.5": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                     "reverse_regression_slope": float(1 / np.polyfit(cf, x, 1)[0]),
                     "pearson": float(np.corrcoef(x, cf)[0, 1])}
    return out


def timing(ds, theta, b):
    t_obs, p_obs, y, rho = survival._survival_observations(ds)
    solved = y > 0
    lam = survival.LN2 * np.exp((theta[t_obs] - b[p_obs]) / elo.S)
    q_end = 1 - np.exp(-lam)
    pit = (1 - np.exp(-lam * rho)) / np.maximum(q_end, 1e-12)
    rows = ds.obs_row
    idx = np.flatnonzero(solved)
    idx = idx[np.lexsort((rho[idx], rows[idx]))]
    first = np.r_[True, rows[idx][1:] != rows[idx][:-1]]
    order = np.zeros(len(y), int)
    order[idx] = np.arange(len(idx)) - np.maximum.accumulate(np.where(first, np.arange(len(idx)), 0)) + 1
    expected_rho = np.where(lam > 1e-8, 1 / lam - np.exp(-lam) / q_end, 0.5)
    by_order = {}
    for k in range(1, 12):
        m = solved & ((order == k) if k < 11 else (order >= 11))
        by_order[str(k) if k < 11 else "11+"] = {"cells": int(m.sum()), "mean_pit": float(pit[m].mean()),
                                                 "mean_rho": float(rho[m].mean()),
                                                 "model_mean_rho": float(expected_rho[m].mean())}
    by_time = {f"{lo:.1f}-{lo + 0.2:.1f}": float(pit[solved & (rho >= lo) & ((rho < lo + 0.2) | (lo > 0.7))].mean())
               for lo in (0.0, 0.2, 0.4, 0.6, 0.8)}
    obs = np.bincount(rows, weights=y, minlength=len(ds.team_of_row))
    pred = np.bincount(rows, weights=q_end, minlength=len(ds.team_of_row))
    edges = np.quantile(obs, np.linspace(0, 1, 6))
    totals = [{"observed_range": [float(lo), float(hi)], "rows": int(m.sum()),
               "observed_mean": float(obs[m].mean()), "predicted_mean": float(pred[m].mean())}
              for lo, hi in zip(edges[:-1], edges[1:]) for m in [(obs >= lo) & (obs <= hi)]]
    return {"solved_cells": int(solved.sum()), "mean_pit": float(pit[solved].mean()),
            "pit_deciles": (np.histogram(pit[solved], bins=10, range=(0, 1))[0] / solved.sum()).round(4).tolist(),
            "by_solve_order": by_order, "by_elapsed_fifth": by_time, "row_totals_by_observed_quintile": totals}


def row_categories(ds, tagged):
    """ONL (roster attached in an online round), ONS (matches an XCPCIO onsite roster), MIR (board roster matching none)."""
    cand = {c["contest_id"]: c for c in dedupe_contests(_read(tagged))}
    base = {c["contest_id"]: c for c in dedupe_contests(_read(TAGGED))}
    roster = lambda s: {_norm_member(m) for m in (s.get("members") or []) if m.strip()}
    pairs = set()
    with open(REGIONALS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mem = sorted({_norm_member(x) for x in r["members"].split("|") if x.strip()})
            pairs.update(((r["season"], r["site"]), a, b) for i, a in enumerate(mem) for b in mem[i + 1:])
    sites = {key for key, _, _ in pairs}
    match = lambda site, mem: any((site, a, b) in pairs for i, a in enumerate(sorted(mem)) for b in sorted(mem)[i + 1:])
    site_of, cat = {}, np.full(len(ds.team_of_row), "", dtype=object)
    for r, (cid, source) in enumerate(ds.participation_of_row):
        c = cand.get(cid)
        if c is None or c.get("region") != "Asia East Continent" or c.get("year") not in (2022, 2023, 2024, 2025):
            continue
        if cid in ONLINE_ROUNDS:
            if len(roster(c["standings"][source])) >= 2 and len(roster(base[cid]["standings"][source])) < 2:
                cat[r] = "ONL"
            continue
        if cid == 1485:   # 2023 online round: not a regional board
            continue
        if cid not in site_of:
            # a regional board: one site's onsite rosters are >= 40% of its roster rows
            votes, n = collections.Counter(), 0
            for s in c["standings"]:
                mem = roster(s)
                if len(mem) >= 2:
                    n += 1
                    votes.update(k for k in sites if k[0] == str(c["year"]) and match(k, mem))
            top = votes.most_common(1)
            site_of[cid] = top[0][0] if top and top[0][1] >= max(50, 0.4 * n) else None
        mem = roster(c["standings"][source])
        if site_of[cid] is not None and len(mem) >= 2:
            cat[r] = "ONS" if match(site_of[cid], mem) else "MIR"
    years = np.array([cand[cid].get("year") if cid in cand else None for cid, _ in ds.participation_of_row], dtype=object)
    return cat, years, {str(k): "/".join(v) for k, v in site_of.items() if v}


def online_onsite(ds, cat, years, fits):
    team = ds.team_of_row
    onl, ons, mir = cat == "ONL", (cat == "ONS") & np.isin(years, [2024, 2025]), cat == "MIR"
    both = sorted(set(team[onl]) & set(team[ons]))
    mirror = sorted(set(team[mir]) & set(team[~mir]))
    rng = np.random.default_rng(SEED)
    t_obs, p_obs, y, _ = survival._survival_observations(ds)
    per_row = collections.defaultdict(list)
    for design, eligible, rowmask in (("hide_online", both, onl), ("hide_onsite", both, ons), ("hide_mirror", mirror, mir)):
        shuffled = np.array(eligible)
        rng.shuffle(shuffled)
        for k in range(5):
            test = (rowmask & np.isin(team, shuffled[k::5]))[ds.obs_row]
            rho = survival._survival_observations(ds, duration_mask=~test)[3]
            for kind in ("survival", "binary"):
                theta, _, _, b = fit_offsets(ds, kind, cell_mask=~test, rho=rho)
                gap = (theta[t_obs[test]] - b[p_obs[test]]) / elo.S
                q = _cells(kind, gap)
                dq = (np.exp(-survival.LN2 * np.exp(gap)) * survival.LN2 * np.exp(gap) if kind == "survival"
                      else q * (1 - q)) / elo.S
                r = ds.obs_row[test]
                n = len(team)
                o, e, d = (np.bincount(r, weights=w, minlength=n) for w in (y[test], q, dq))
                for row in np.unique(r):
                    per_row[(design, kind)].append((int(row), int(team[row]), o[row], e[row], d[row]))
    out = {"rows": {k: int(v.sum()) for k, v in (("verified_online", onl), ("onsite_2024_2025", ons), ("mirror", mir))},
           "teams_online_and_onsite": len(both), "teams_with_mirror_rows": len(mirror)}
    for kind in ("survival", "binary"):
        res = {}
        for design in ("hide_online", "hide_onsite", "hide_mirror"):
            a = np.array(per_row[(design, kind)])
            teams = np.unique(a[:, 1])
            pos = {t: np.flatnonzero(a[:, 1] == t) for t in teams}
            boot = []
            for _ in range(2000):
                kk = np.concatenate([pos[t] for t in rng.choice(teams, len(teams))])
                boot.append(((a[kk, 2] - a[kk, 3]).mean(), (a[kk, 2] - a[kk, 3]).sum() / a[kk, 4].sum()))
            boot = np.array(boot)
            per_team = [float((a[pos[t], 2] - a[pos[t], 3]).mean()) for t in teams]
            res[design] = {"appearances": len(a), "teams": len(teams),
                           "observed_mean": float(a[:, 2].mean()), "expected_mean": float(a[:, 3].mean()),
                           "residual_solves": float((a[:, 2] - a[:, 3]).mean()),
                           "residual_team_bootstrap": np.percentile(boot[:, 0], [2.5, 97.5]).tolist(),
                           "offset_points": float((a[:, 2] - a[:, 3]).sum() / a[:, 4].sum()),
                           "offset_team_bootstrap": np.percentile(boot[:, 1], [2.5, 97.5]).tolist(),
                           "bisquare_per_team_residual": bisquare_location(per_team)[0]}
        by = {d: collections.defaultdict(lambda: [0.0, 0.0]) for d in ("hide_online", "hide_onsite")}
        for d in by:
            for row, t, o, e, dq in per_row[(d, kind)]:
                by[d][t][0] += o - e
                by[d][t][1] += dq
        common = sorted(set(by["hide_online"]) & set(by["hide_onsite"]))
        diff = np.array([by["hide_online"][t][0] / by["hide_online"][t][1] - by["hide_onsite"][t][0] / by["hide_onsite"][t][1]
                         for t in common])
        boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
        th = fits[kind][0][common]   # full-fit ability: stratifying on a held-out fit's theta regresses to the mean
        cuts = np.quantile(th, [0, 1 / 3, 2 / 3, 1])
        res["paired_online_minus_onsite_offset"] = {
            "teams": len(common), "mean": float(diff.mean()), "bootstrap_2.5_97.5": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "bisquare": bisquare_location(diff)[0],
            "by_ability_tertile": [float(diff[(th >= lo) & (th <= hi)].mean()) for lo, hi in zip(cuts[:-1], cuts[1:])]}
        out[kind] = res
    return out


def team_seasons(ds):
    season = {}
    for path in [TAGGED, OLDER_ICPC, PETROZ, WF] + UCUP:
        for c in _read(path):
            # UCup stages carry no year: season 3 ran in the 2024 ICPC season, season 4 in 2025
            fallback = 2024 if "ucup_s3" in path else 2025 if "ucup_s4" in path else None
            season.setdefault(c["contest_id"], season_of(c) or fallback)
    keys, group = {}, np.empty(len(ds.team_of_row), int)
    for r, (t, (cid, _)) in enumerate(zip(ds.team_of_row, ds.participation_of_row)):
        group[r] = keys.setdefault((int(t), season[cid]), len(keys))
    return group, len(keys), np.array([season[cid] for cid, _ in ds.participation_of_row], dtype=object)


def offsets(ds, cat):
    group, n_groups, season = team_seasons(ds)
    cid = np.array([c for c, _ in ds.participation_of_row])
    t_obs, p_obs, y, _ = survival._survival_observations(ds)
    online_teams = set(ds.team_of_row[np.isin(cid, ONLINE_ROUNDS)])
    touch = collections.Counter(cid[r] for r in range(len(cid)) if ds.team_of_row[r] in online_teams and cid[r] not in ONLINE_ROUNDS)
    affected = {c for c, n in touch.items() if n >= 50}
    keys = [(ds.participation_of_row[r][0], ds.participation_of_row[r][1], ds.problems[p][1]) for r, p in zip(ds.obs_row, ds.obs_prob)]
    holdouts = {"asia_east_cells": np.array([k[0] in affected and int(hashlib.md5(repr(k).encode()).hexdigest(), 16) % 5 == 0 for k in keys]),
                "random_cells": _grouped_test_mask(t_obs, p_obs)}
    ctx = np.full(len(cid), -1)
    ctx[np.isin(cid, ONLINE_ROUNDS + (1485,))] = 0     # every row of an EC online round
    ctx[cat == "MIR"] = 1                              # online mirror rows on regional boards
    configs = {f"tau_{int(tau)}": dict(group_of_row=group, n_groups=n_groups, tau=tau) for tau in (0.0, 100.0, 200.0, 400.0)}
    configs["online_context"] = dict(ctx_of_row=ctx, n_ctx=2)
    out = {"affected_contests": len(affected), "team_seasons": n_groups, "held_out": {}, "cf_loco": {}}
    for hname, test in holdouts.items():
        rho = survival._survival_observations(ds, duration_mask=~test)[3]
        contests = np.array([k[0] for k, h in zip(keys, test) if h])
        groups = [np.flatnonzero(contests == c) for c in sorted(set(contests))]
        for kind in ("survival", "binary"):
            losses = {}
            for name, cfg in configs.items():
                theta, delta, gamma, b = fit_offsets(ds, kind, cell_mask=~test, rho=rho, **cfg)
                r = ds.obs_row[test]
                g = group[r] if "group_of_row" in cfg else np.zeros(len(r), int)
                c = np.where(ctx[r] < 0, 2, ctx[r]) if "ctx_of_row" in cfg else np.zeros(len(r), int)
                q = np.clip(_cells(kind, (theta[t_obs[test]] + delta[g] + gamma[c] - b[p_obs[test]]) / elo.S), 1e-6, 1 - 1e-6)
                losses[name] = -(y[test] * np.log(q) + (1 - y[test]) * np.log(1 - q))
                entry = {"log_loss": float(losses[name].mean()),
                         "by_season": {str(s): float(losses[name][season[r] == s].mean()) for s in (2022, 2023, 2024, 2025)}}
                if name != "tau_0":
                    dl = losses[name] - losses["tau_0"]
                    rng = np.random.default_rng(SEED)
                    boots = [dl[np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])].mean() for _ in range(1000)]
                    entry["minus_tau_0"] = [float(dl.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
                if "ctx_of_row" in cfg:
                    entry["gamma_online_round_mirror"] = gamma[:2].tolist()
                out["held_out"][f"{hname}/{kind}/{name}"] = entry
    oof = {}
    for name, cfg in configs.items():
        recs, extra = {}, {}
        for kind in ("survival", "binary"):
            theta, delta, gamma, b = fit_offsets(ds, kind, **cfg)
            recs[kind] = offset_records(ds, kind, theta, delta, gamma, b, cfg.get("group_of_row"), cfg.get("ctx_of_row"), cfg.get("n_ctx", 0))
            online = np.isin([c for c, _, _, _ in ds.problems], ONLINE_ROUNDS + (1485,))
            extra[kind] = {"gamma": gamma[:-1].tolist(), "online_round_mean_b": float(b[online].mean())}
        rows = _anchor_rows(recs)
        oof[name] = (rows, loco(rows, "ridge", ("raw_b",))[0], loco(rows, "ridge", DE)[0])
        out["cf_loco"][name] = {"raw_ridge": rmse(oof[name][1], rows), "DE": rmse(oof[name][2], rows)} | extra
    for name in configs:
        if name != "tau_0":
            assert [r["row_id"] for r in oof[name][0]] == [r["row_id"] for r in oof["tau_0"][0]]
            out["cf_loco"][name]["DE_minus_tau_0"] = contest_bootstrap(oof["tau_0"][0], oof[name][2], oof["tau_0"][2])
    return out


def run(tagged):
    ds, uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS, tagged=tagged)
    fits, recs = {}, {}
    for kind, mod in (("survival", survival), ("binary", model)):
        theta, b, _ = mod.fit(ds, verbose=False)
        fits[kind] = (theta, b)
        recs[kind] = problem_records(ds, b, mod.laplace_se(ds, theta, b)[1])
    result = {"research_only": True, "production_changed": False,
              "decomposition": decomposition(ds, fits, recs)}
    print("decomposition done", flush=True)
    result["ability_mapping_cf_teams"] = ability_mapping(ds, uf, fits)
    result["survival_timing_residuals"] = timing(ds, *fits["survival"])
    cat, years, sites = row_categories(ds, tagged)
    result["board_sites"] = sites
    result["online_vs_onsite_held_out"] = online_onsite(ds, cat, years, fits)
    print("online/onsite done", flush=True)
    result["offsets"] = offsets(ds, cat)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    return result


if __name__ == "__main__":
    out = run(sys.argv[1])
    print(json.dumps({"paired": {k: out["online_vs_onsite_held_out"][k]["paired_online_minus_onsite_offset"]
                                 for k in ("survival", "binary")}, "cf_loco": out["offsets"]["cf_loco"]}, indent=1))
