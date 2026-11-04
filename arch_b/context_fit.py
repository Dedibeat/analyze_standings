"""Experiment 1 of rating_rethink.md: participation context inside the binary fit.

Research only: writes ``output/context_experiment.json``; no shipped fit,
calibration or export changes.

Row context is an ID-based label, not verified exposure. On a board whose own
imported field (``$DEFAULT...`` rows) has at least ``MIN_EVENT_FIELD`` rows and
which also holds other rows, the other rows are mirror entries: ``ucup-team*``
rows (mirror_ucup) or any other QOJ id (mirror_account). Every other row is the
reference context: the event rows of those boards and all rows of boards
without such a field (UCup original stages, small imported fields).

    P(solve) = sigma((a_r - b_p) / s),
    a_r = theta_t + delta_k + gamma_k * (theta_t - MU0),   k = context of row r

``delta_0 = gamma_0 = 0``; 1 + gamma > 0 keeps the response increasing.

Identification. A team seen in one context only has the same likelihood for any
offset; the shared N(MU0, SIGMA_THETA^2) ability prior then picks the offset
that moves such teams toward MU0 (mirror entrants are stronger than average).
So offsets are applied to the rows of a chosen set of teams (``APPLY``):
``all`` (naive), ``multi`` (teams seen in two or more contexts) or ``onsite``
(those that also have an event row on a mixed board: the same team onsite and
as a mirror entrant). Every other team's ability is in its own contexts; when it
is predicted in a context it was not seen in, its ability is converted from its
most frequent context. A board-level context (an online round, say) would be
confounded with that board's difficulties, so none is fit.

Checks, all on the fit's 991,268 cells:
1. full-data estimates, prior sensitivity, CF guard (affine LOCO on the 185
   dev anchors) and how far each model's mixed-board difficulties sit from an
   event-rows-only refit with the same model's abilities;
2. whole-appearance hold-out (contest x identity groups), three seeds;
3. event-field transfer: four folds over mixed boards; the held-out fold's
   event rows are removed (with any other row of the same identity on that
   board), everything else, incl. the board's other mirror rows, is fit.
   Linked rows are scored with abilities from other contests; every held-out
   row is also scored split-half (ability from half its contest's problems).

    python -m arch_b.context_fit
"""

import json
import os
import sys

import numpy as np

from arch_a import elo
from arch_a.load import dedupe_contests
from .calibrate import _anchors, _loco_rmse
from .export_virtual_calc import MIN_EVENT_FIELD
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, load_joint_dataset
from .model import MU0, SIGMA_B, SIGMA_THETA, _require_converged
from .run import MIN_SOLVE_HOURS

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output", "context_experiment.json")
CONTEXTS = ("reference", "mirror_ucup", "mirror_account")
SIGMA_DELTA = 400.0
SIGMA_GAMMA = 0.25
SEEDS = (0, 1, 2)
FOLDS = 4
SEED = 20261104

# name: (mirror contexts "pooled" or "kind", teams the offsets apply to, slope)
MODELS = {"M0_pooled": None,
          "M1_naive": ("pooled", "all", False),
          "M1_multi_context": ("pooled", "multi", False),
          "M1_onsite_bridge": ("pooled", "onsite", False),
          "M3_onsite_bridge_slope": ("pooled", "onsite", True)}
DIAGNOSTIC = {"M2_naive": ("kind", "all", False),
              "M3_naive": ("kind", "all", True),
              "M2_multi_context": ("kind", "multi", False)}


# ---- labels ----

def raw_by_contest():
    raw = []
    for path in (TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP):
        with open(path, encoding="utf-8") as f:
            raw.extend(json.load(f))
    return {c["contest_id"]: c for c in dedupe_contests(raw)}


def row_context(ds, raw):
    """0 reference, 1 mirror_ucup, 2 mirror_account (see module docstring)."""
    ctx = np.zeros(len(ds.team_of_row), int)
    for ci in range(len(ds.contests)):
        rows = np.flatnonzero(ds.contest_of_row == ci)
        official = ds.official_of_row[rows]
        if official.sum() < MIN_EVENT_FIELD or official.all():
            continue
        for r in rows[~official]:
            cid, source = ds.participation_of_row[r]
            team_id = str(raw[cid]["standings"][source].get("team_id") or "")
            ctx[r] = 1 if team_id.startswith("ucup-team") else 2
    return ctx


def mixed_boards(ds, ctx):
    """Contest indices that hold both event rows and mirror rows."""
    return np.unique(ds.contest_of_row[ctx > 0])


# ---- fit ----

def fit(ds, ctx, n_ctx, slope=False, cells=None, apply=None, sigma_theta=SIGMA_THETA,
        sigma_b=SIGMA_B, sigma_delta=SIGMA_DELTA, sigma_gamma=SIGMA_GAMMA, eps=0.5, max_iter=500):
    """MAP of the context model; returns (theta, b, delta, gamma, iterations).

    ``cells`` is a boolean mask over observations (default all); ``apply`` a
    boolean per team: offsets act only on those teams' rows (default all). With
    every context 0 this is exactly ``model.fit`` (same blocks, same order).
    """
    cells = np.ones(len(ds.obs_y), bool) if cells is None else np.asarray(cells, bool)
    apply = np.ones(len(ds.teams), bool) if apply is None else np.asarray(apply, bool)
    row, prob = ds.obs_row[cells], ds.obs_prob[cells]
    y = ds.obs_y[cells].astype(float)
    team = ds.team_of_row[row]
    k = np.where(apply[team], ctx[row], 0)
    s = elo.S
    theta, b = np.full(len(ds.teams), MU0), np.full(len(ds.problems), MU0)
    delta, gamma = np.zeros(n_ctx), np.zeros(n_ctx)

    def ability():
        return theta[team] + delta[k] + gamma[k] * (theta[team] - MU0)

    def objective():
        gap = (ability() - b[prob]) / s
        return float(np.sum(y * gap - np.logaddexp(0.0, gap))
                     - 0.5 * np.sum((theta - MU0) ** 2) / sigma_theta ** 2
                     - 0.5 * np.sum((b - MU0) ** 2) / sigma_b ** 2
                     - 0.5 * np.sum(delta ** 2) / sigma_delta ** 2
                     - 0.5 * np.sum(gamma ** 2) / sigma_gamma ** 2)

    start = objective()
    history = []
    for _ in range(max_iter):
        lift = 1.0 + gamma[k]
        pi = elo.pi(ability(), b[prob])
        grad = np.bincount(team, lift * (y - pi), len(theta)) / s - (theta - MU0) / sigma_theta ** 2
        neg = np.bincount(team, lift ** 2 * pi * (1 - pi), len(theta)) / s ** 2 + 1 / sigma_theta ** 2
        new = np.clip(theta + grad / neg, elo.LO, elo.HI)
        change = np.max(np.abs(new - theta))
        theta = new

        pi = elo.pi(ability(), b[prob])
        grad = -np.bincount(prob, y - pi, len(b)) / s - (b - MU0) / sigma_b ** 2
        neg = np.bincount(prob, pi * (1 - pi), len(b)) / s ** 2 + 1 / sigma_b ** 2
        new = np.clip(b + grad / neg, elo.LO, elo.HI)
        change = max(change, np.max(np.abs(new - b)))
        b = new

        if n_ctx > 1:
            pi = elo.pi(ability(), b[prob])
            r, w, x = y - pi, pi * (1 - pi), theta[team] - MU0
            for c in range(1, n_ctx):
                m = k == c
                if not slope:
                    step = ((r[m].sum() / s - delta[c] / sigma_delta ** 2)
                            / (w[m].sum() / s ** 2 + 1 / sigma_delta ** 2))
                    change = max(change, abs(step))
                    delta[c] += step
                    continue
                g = np.array([r[m].sum() / s - delta[c] / sigma_delta ** 2,
                              (x[m] * r[m]).sum() / s - gamma[c] / sigma_gamma ** 2])
                h = np.array([[w[m].sum(), (x[m] * w[m]).sum()],
                              [(x[m] * w[m]).sum(), (x[m] ** 2 * w[m]).sum()]]) / s ** 2
                h += np.diag([1 / sigma_delta ** 2, 1 / sigma_gamma ** 2])
                step = np.linalg.solve(h, g)
                delta[c] += step[0]
                gamma[c] = max(gamma[c] + step[1], -0.9)
                change = max(change, abs(step[0]), abs(step[1]) * 400)
        history.append(change)
        if change < eps:
            break
    _require_converged(theta, b, history, eps)
    if objective() + 1e-7 < start:
        raise RuntimeError("context fit decreased its objective")
    return theta, b, delta, gamma, len(history)


def seen_contexts(ds, ctx, n_ctx, cells):
    """Per team: training rows in each context (teams x n_ctx counts)."""
    rows = np.unique(ds.obs_row[cells])
    out = np.zeros((len(ds.teams), n_ctx), int)
    np.add.at(out, (ds.team_of_row[rows], ctx[rows]), 1)
    return out


def apply_rule(rule, seen, has_event):
    if rule == "all":
        return np.ones(len(seen), bool)
    multi = (seen > 0).sum(1) >= 2
    return multi if rule == "multi" else multi & has_event


def row_ability(theta, delta, gamma, team, k, apply, seen):
    """Ability of each (team, context) pair under the fitted model (see module docstring)."""
    t = theta[team]
    direct = t + delta[k] + gamma[k] * (t - MU0)
    known = seen[team]
    absorbed = (known[np.arange(len(team)), k] > 0) | (known.sum(1) == 0)
    home = known.argmax(1)
    ref = (t - delta[home] + gamma[home] * MU0) / (1.0 + gamma[home])
    converted = ref + delta[k] + gamma[k] * (ref - MU0)
    return np.where(apply[team], direct, np.where(absorbed, t, converted))


def model_setup(spec, ctx):
    """(row contexts, number of contexts, apply rule, slope) for one model spec."""
    if spec is None:
        return np.zeros_like(ctx), 1, "all", False
    kind, rule, slope = spec
    return ((ctx > 0).astype(int), 2, rule, slope) if kind == "pooled" else (ctx, 3, rule, slope)


# ---- scoring ----

def contest_sums(contest, y, p):
    """{contest: [log-loss sum, Brier sum, cells]}."""
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll, br = -(y * np.log(p) + (1 - y) * np.log(1 - p)), (p - y) ** 2
    n = int(contest.max()) + 1 if len(contest) else 0
    sums = np.stack([np.bincount(contest, ll, n), np.bincount(contest, br, n),
                     np.bincount(contest, None, n)], 1)
    return {int(c): sums[c] for c in np.unique(contest)}


def summarize(sums):
    t = np.sum(list(sums.values()), axis=0)
    return {"log_loss": float(t[0] / t[2]), "brier": float(t[1] / t[2]), "cells": int(t[2]),
            "contests": len(sums)}


def paired(sums, base, n=2000):
    """Model minus base log loss, with a paired contest-bootstrap 95% interval."""
    keys = sorted(sums)
    a, b = np.array([sums[c] for c in keys]), np.array([base[c] for c in keys])
    idx = np.random.default_rng(SEED).integers(0, len(keys), (n, len(keys)))

    def diff(x, z):
        return x[..., 0].sum(-1) / x[..., 2].sum(-1) - z[..., 0].sum(-1) / z[..., 2].sum(-1)
    return [float(diff(a, b)), *map(float, np.percentile(diff(a[idx], b[idx]), [2.5, 97.5]))]


def solve_decreasing(grad, n, iters=50):
    """Per-parameter root of a decreasing gradient on [LO, HI] by vectorized bisection.

    A one-parameter MAP with the others fixed is concave, but a plain Newton step
    from a distant start can bounce between the clip bounds where the curvature
    vanishes; bisection cannot. A root outside the bounds clamps to the bound.
    """
    lo, hi = np.full(n, elo.LO), np.full(n, elo.HI)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        up = grad(mid) > 0
        lo, hi = np.where(up, mid, lo), np.where(up, hi, mid)
    return 0.5 * (lo + hi)


def row_abilities(row, prob, y, b, n_rows, sigma=SIGMA_THETA):
    """MAP ability per row from the given cells with difficulties fixed."""
    return solve_decreasing(lambda a: np.bincount(row, y - elo.pi(a[row], b[prob]), n_rows) / elo.S
                            - (a - MU0) / sigma ** 2, n_rows)


def split_half_probs(ds, b, cells):
    """Each scored row's ability from one half of its contest's problems (b fixed), predicting the other.

    Context terms are not used: the row's own ability absorbs most of a constant
    shift (the ability prior keeps a small level dependence), so this mainly
    scores the spacing of the difficulties.
    """
    idx = np.flatnonzero(cells)
    row, prob, y = ds.obs_row[idx], ds.obs_prob[idx], ds.obs_y[idx].astype(float)
    half = prob % 2
    p = np.zeros(len(idx))
    for h in (0, 1):
        fit_m, pred_m = half == h, half != h
        a = row_abilities(row[fit_m], prob[fit_m], y[fit_m], b, len(ds.team_of_row))
        p[pred_m] = elo.pi(a[row[pred_m]], b[prob[pred_m]])
    return idx, p


def fixed_ability_b(ds, ability, cells):
    """Difficulties refit from the given cells only, cell abilities fixed (MAP per problem)."""
    prob, y, a = ds.obs_prob[cells], ds.obs_y[cells].astype(float), ability[cells]
    return solve_decreasing(lambda b: -np.bincount(prob, y - elo.pi(a, b[prob]), len(ds.problems)) / elo.S
                            - (b - MU0) / SIGMA_B ** 2, len(ds.problems))


def cf_guard(ds, b):
    records = [{"contest_id": int(cid), "problem_label": label, "problem_name": name,
                "difficulty": float(b[p])} for p, (cid, label, _pid, name) in enumerate(ds.problems)]
    our, cf, grp = _anchors(records)
    return {"anchors": len(cf),
            "affine_loco_rmse": _loco_rmse(np.asarray(our), np.asarray(cf), np.asarray(grp))}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---- experiment ----

class Setup:
    def __init__(self):
        self.ds, _uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
        ds = self.ds
        self.ctx = row_context(ds, raw_by_contest())
        self.boards = mixed_boards(ds, self.ctx)
        self.event_row = (self.ctx == 0) & ds.official_of_row & np.isin(ds.contest_of_row, self.boards)
        self.cell_ctx = self.ctx[ds.obs_row]
        self.cell_event = self.event_row[ds.obs_row]
        self.cell_contest = ds.contest_of_row[ds.obs_row]
        self.cell_team = ds.team_of_row[ds.obs_row]
        self.y = ds.obs_y.astype(float)

    def run_model(self, spec, cells, **kw):
        """Fit on ``cells``; return (theta, b, delta, gamma, iterations, ability of every cell)."""
        ds = self.ds
        k, n, rule, slope = model_setup(spec, self.ctx)
        seen = seen_contexts(ds, k, n, cells)
        has_event = np.zeros(len(ds.teams), bool)
        has_event[self.cell_team[cells & self.cell_event]] = True
        apply = apply_rule(rule, seen, has_event)
        theta, b, delta, gamma, it = fit(ds, k, n, slope, cells=cells, apply=apply, **kw)
        a = row_ability(theta, delta, gamma, self.cell_team, k[ds.obs_row], apply, seen)
        return theta, b, delta, gamma, it, a, int(apply.sum()) if spec else 0


def offsets(delta, gamma, names):
    return {names[c]: {"delta": float(delta[c]), "gamma": float(gamma[c]),
                       **{f"offset_at_{t}": float(delta[c] + gamma[c] * (t - MU0))
                          for t in (1800, 2200, 2600, 3000)}}
            for c in range(1, len(delta))}


def full_data(su):
    ds = su.ds
    everything = np.ones(len(ds.obs_y), bool)
    on_mixed = np.isin(su.cell_contest, su.boards)
    event_cells = on_mixed & (su.cell_ctx == 0)
    solved = np.bincount(ds.obs_prob[event_cells], su.y[event_cells], len(ds.problems))
    field = np.bincount(ds.obs_prob[event_cells], None, len(ds.problems))
    ok = np.flatnonzero((solved > 0) & (solved < field))
    out, bands = {}, None
    labels = ("<1600", "1600-2000", "2000-2400", "2400-2800", ">=2800")
    variants = [(n, s, {}) for n, s in {**MODELS, **DIAGNOSTIC}.items()]
    variants += [(f"{n}_sigma_theta_{v:.0f}", {**MODELS, **DIAGNOSTIC}[n], {"sigma_theta": v})
                 for n in ("M2_naive", "M1_multi_context", "M1_onsite_bridge") for v in (800.0, 1600.0)]
    for name, spec, kw in variants:
        _theta, b, delta, gamma, it, a, n_apply = su.run_model(spec, everything, **kw)
        b_event = fixed_ability_b(ds, a, event_cells)
        if bands is None:
            bands = np.digitize(b_event[ok], (1600, 2000, 2400, 2800))
        names = ("reference", "mirror") if len(delta) == 2 else CONTEXTS
        out[name] = {"iterations": it, "teams_with_offsets": n_apply,
                     "contexts": offsets(delta, gamma, names), "cf_guard": cf_guard(ds, b),
                     "mixed_board_b_minus_event_only_refit": {
                         labels[i]: [float(np.mean((b - b_event)[ok][bands == i])), int((bands == i).sum())]
                         for i in range(5)}}
        log(f"full {name}: {it} iters {out[name]['contexts']}")
        if name == "M1_onsite_bridge":
            out[name]["bridge_team_gaps"] = bridge_gaps(su, b)
    return out


def bridge_gaps(su, b, sigma=800.0, draws=5000):
    """Per bridge team (event rows and mirror rows): mirror minus event ability with ``b`` fixed.

    Each side is a separate MAP under a weak N(MU0, sigma^2) prior; the summary is
    the precision-weighted mean gap with a team bootstrap.
    """
    ds = su.ds
    mirror = su.cell_ctx > 0
    bridge = np.zeros(len(ds.teams), bool)
    bridge[np.intersect1d(su.cell_team[su.cell_event], su.cell_team[mirror])] = True

    def side(cells):
        team, prob, y = su.cell_team[cells], ds.obs_prob[cells], su.y[cells]
        t = solve_decreasing(lambda t: np.bincount(team, y - elo.pi(t[team], b[prob]), len(ds.teams)) / elo.S
                             - (t - MU0) / sigma ** 2, len(ds.teams))
        p = elo.pi(t[team], b[prob])
        return t, 1 / (np.bincount(team, p * (1 - p), len(t)) / elo.S ** 2 + 1 / sigma ** 2)

    event, var_e = side(su.cell_event & bridge[su.cell_team])
    mir, var_m = side(mirror & bridge[su.cell_team])
    ids = np.flatnonzero(bridge)
    gap, w = (mir - event)[ids], 1 / (var_e + var_m)[ids]
    k = np.random.default_rng(SEED).integers(0, len(ids), (draws, len(ids)))
    boot = np.sum(w[k] * gap[k], 1) / np.sum(w[k], 1)
    return {"teams": int(len(ids)), "weighted_mean_gap": float(np.sum(w * gap) / np.sum(w)),
            "team_bootstrap_95": [float(x) for x in np.percentile(boot, [2.5, 97.5])],
            "median_gap": float(np.median(gap))}


def holdout(su):
    ds = su.ds
    groups = np.unique(np.column_stack((ds.contest_of_row, ds.team_of_row)), axis=0,
                       return_inverse=True)[1].ravel()
    on_mixed = np.isin(su.cell_contest, su.boards)
    runs = {}
    for seed in SEEDS:
        test = (np.random.default_rng(seed).random(groups.max() + 1) < 0.2)[groups][ds.obs_row]
        seen = seen_contexts(ds, su.ctx, 3, ~test)
        linked = test & (seen.sum(1) > 0)[su.cell_team]
        switch = linked & (seen[su.cell_team, su.cell_ctx] == 0)
        subsets = {"all": test, "linked": linked,
                   "linked_event_rows": linked & su.cell_event,
                   "linked_mirror_rows": linked & (su.cell_ctx > 0),
                   "linked_other_reference_rows": linked & (su.cell_ctx == 0) & ~su.cell_event,
                   "linked_new_context_for_team": switch,
                   "linked_on_mixed_boards": linked & on_mixed}
        res = {}
        for name, spec in MODELS.items():
            _theta, b, _d, _g, _it, a, _n = su.run_model(spec, ~test)
            p = elo.pi(a, b[ds.obs_prob])
            res[name] = {sub: contest_sums(su.cell_contest[m], su.y[m], p[m]) for sub, m in subsets.items()}
            log(f"holdout seed {seed} {name} done")
        runs[seed] = res
    return _aggregate(runs)


def transfer_masks(cell_contest, cell_team, cell_event, boards):
    """(test, train) cells: the boards' event cells, and everything except any cell of a
    held-out event team on its held-out board (a same-board mirror row would leak)."""
    held = np.isin(cell_contest, boards)
    test = held & cell_event
    pair = cell_contest.astype(np.int64) * (int(cell_team.max()) + 1) + cell_team
    return test, ~(held & np.isin(pair, np.unique(pair[test])))


def transfer(su):
    ds = su.ds
    order = np.random.default_rng(SEED).permutation(su.boards)
    runs = {}
    for f in range(FOLDS):
        test, train = transfer_masks(su.cell_contest, su.cell_team, su.cell_event, order[f::FOLDS])
        seen = seen_contexts(ds, su.ctx, 3, train)
        linked = test & (seen.sum(1) > 0)[su.cell_team]
        res = {}
        for name, spec in MODELS.items():
            _theta, b, _d, _g, _it, a, _n = su.run_model(spec, train)
            p = elo.pi(a, b[ds.obs_prob])
            idx, ph = split_half_probs(ds, b, test)
            res[name] = {sub: contest_sums(su.cell_contest[m], su.y[m], p[m]) for sub, m in (
                ("linked", linked),
                ("linked_seen_only_as_mirror", linked & (seen[:, 0] == 0)[su.cell_team]))}
            res[name]["split_half_all_event_rows"] = contest_sums(su.cell_contest[idx], su.y[idx], ph)
            log(f"transfer fold {f} {name} done")
        runs[f] = res
    return _aggregate(runs)


def _aggregate(runs):
    """Pool contest sums over seeds/folds and compare each model with M0."""
    first = next(iter(runs.values()))
    out = {}
    for sub in first["M0_pooled"]:
        pooled = {}
        for name in first:
            acc = {}
            for res in runs.values():
                for c, v in res[name][sub].items():
                    acc[c] = acc.get(c, 0) + v
            pooled[name] = acc
        out[sub] = {name: {**summarize(pooled[name]),
                           **({} if name == "M0_pooled" else
                              {"log_loss_minus_M0": paired(pooled[name], pooled["M0_pooled"])})}
                    for name in first}
    return out


def provenance(modules):
    """sha256 of the shipped standings inputs and of the experiment's own code."""
    import hashlib
    root = os.path.join(os.path.dirname(__file__), os.pardir)
    paths = [TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP] + [os.path.join(root, m) for m in modules]
    return {os.path.relpath(p, root): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths}


def run():
    su = Setup()
    ds, ctx = su.ds, su.ctx
    sets = {}
    for team, k in zip(ds.team_of_row, ctx):
        sets.setdefault(int(team), set()).add(int(k))
    by_set = {}
    for v in sets.values():
        key = "+".join(CONTEXTS[c] for c in sorted(v))
        by_set[key] = by_set.get(key, 0) + 1
    event_teams = set(ds.team_of_row[su.event_row])
    out = {"scope": "Research only; ID-based contexts, not verified exposure",
           "sha256": provenance(["arch_b/context_fit.py", "arch_b/model.py", "arch_a/load.py"]),
           "rows_by_context": {n: int((ctx == c).sum()) for c, n in enumerate(CONTEXTS)},
           "mixed_boards": int(len(su.boards)), "event_rows": int(su.event_row.sum()),
           "identities_by_context_set": by_set,
           "identities_with_event_and_mirror_rows": {
               CONTEXTS[c]: len(event_teams & set(ds.team_of_row[ctx == c])) for c in (1, 2)}}
    out["full_data"] = full_data(su)
    out["whole_appearance_holdout"] = holdout(su)
    out["event_field_transfer"] = transfer(su)
    return out


def main():
    out = run()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
