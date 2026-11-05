"""Hierarchical binary Rasch fit: a DE rival candidate. See hier_binary_report.md.

Binary Rasch with board-level means for team abilities and problem difficulties:

    P(solve) = sigma((theta_t - b_p) / s)
    theta_t ~ N(sum_r mu_c(r) / n_t, sigma^2)     (mean of the team's boards)
    mu_c    ~ N(2000, tau^2)
    b_p     ~ N(nu_c(p), sigma_b^2)
    nu_c    ~ N(nu_0, tau_b^2),  nu_0 flat

The flat N(2000, 400^2) ability prior of ``model.fit`` shrinks every team seen
once toward 2000, so on a strong board the abilities, and with them the
difficulties, are pulled down; DE's solve-rate term repairs that bias after the
fact. Here a board's own field sets its prior mean instead. Only the ability
side anchors the level (average board 2000, the repo's MU0 convention); the
problem-set hyper-mean nu_0 is estimated. ``tau=0`` fixes every team's prior
mean at 2000 and ``tau_b=0`` every problem's (``sigma=400, tau=0, sigma_b=400,
tau_b=0`` is ``model.fit``'s model).

The posterior is strictly concave. Block-coordinate Newton converges very
slowly along board-wide shifts (eps 0.5 stops ~120 points short), so this fit
uses Newton steps solved by preconditioned conjugate gradients on all
parameters, with a backtracking line search, until the largest step is below
``eps``. Unlike ``model.fit`` it does not clip to [800, 4000] while fitting.

    python -m arch_b.hier_binary all [JOBS]   # every experiment -> output/hier_binary.json
"""

import gzip
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from arch_a import elo

S = elo.S
MU0 = 2000.0


def fit(ds, obs=None, rows=None, sigma=300.0, tau=800.0, sigma_b=600.0, tau_b=400.0,
        eps=1e-3, max_newton=60, cg_tol=1e-4, cg_max=500):
    """MAP fit; returns dict(theta, b, mu, nu, nu0, newton, cg, max_step).

    ``obs`` = (obs_team, obs_prob, obs_y) restricts the likelihood cells.
    ``rows`` is a boolean mask of standings rows that define each team's
    board membership (default: every row); a team with no active row gets
    prior mean 2000.
    """
    team, prob, y = ((ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y) if obs is None else obs)
    y = np.asarray(y, float)
    n_t, n_p, n_c = len(ds.teams), len(ds.problems), len(ds.contests)
    rows = np.ones(len(ds.team_of_row), bool) if rows is None else np.asarray(rows, bool)
    r_t, r_c = ds.team_of_row[rows], ds.contest_of_row[rows]
    n_rows = np.bincount(r_t, minlength=n_t).astype(float)
    r_w = 1.0 / n_rows[r_t]
    p_c = np.asarray(ds.contest_of_problem)
    has_mu, has_nu = tau > 0, tau_b > 0
    cut = np.cumsum([n_t, n_p, n_c, n_c])

    def w_mu(mu):          # W @ mu: each team's mean board level
        out = np.bincount(r_t, r_w * mu[r_c], n_t)
        out[n_rows == 0] = MU0
        return out

    def wt(z):             # W.T @ z
        return np.bincount(r_c, r_w * z[r_t], n_c)

    def unpack(x):
        th, b, mu, nu, nu0 = np.split(x, cut)
        return th, b, mu, nu, nu0[0]

    def prior_means(mu, nu):
        return (w_mu(mu) if has_mu else np.full(n_t, MU0)), (nu[p_c] if has_nu else np.full(n_p, MU0))

    def objective(x):      # negative log posterior (minimized)
        th, b, mu, nu, nu0 = unpack(x)
        g = (th[team] - b[prob]) / S
        m, mb = prior_means(mu, nu)
        f = np.sum(np.logaddexp(0.0, g) - y * g)
        f += np.sum((th - m) ** 2) / (2 * sigma ** 2) + np.sum((b - mb) ** 2) / (2 * sigma_b ** 2)
        if has_mu:
            f += np.sum((mu - MU0) ** 2) / (2 * tau ** 2)
        if has_nu:
            f += np.sum((nu - nu0) ** 2) / (2 * tau_b ** 2)
        return float(f)

    x = np.full(n_t + n_p + 2 * n_c + 1, MU0)
    n_newton = n_cg = 0
    step_max = np.inf
    for n_newton in range(1, max_newton + 1):
        th, b, mu, nu, nu0 = unpack(x)
        pr = 1.0 / (1.0 + np.exp(-(th[team] - b[prob]) / S))
        m, mb = prior_means(mu, nu)
        rt, rb = th - m, b - mb
        resid = pr - y
        grad = np.concatenate([
            np.bincount(team, resid, n_t) / S + rt / sigma ** 2,
            -np.bincount(prob, resid, n_p) / S + rb / sigma_b ** 2,
            (-wt(rt) / sigma ** 2 + (mu - MU0) / tau ** 2) if has_mu else np.zeros(n_c),
            (-np.bincount(p_c, rb, n_c) / sigma_b ** 2 + (nu - nu0) / tau_b ** 2) if has_nu else np.zeros(n_c),
            [-np.sum(nu - nu0) / tau_b ** 2 if has_nu else 0.0]])
        w = pr * (1 - pr) / S ** 2
        diag = np.concatenate([
            np.bincount(team, w, n_t) + 1 / sigma ** 2,
            np.bincount(prob, w, n_p) + 1 / sigma_b ** 2,
            (np.bincount(r_c, r_w ** 2, n_c) / sigma ** 2 + 1 / tau ** 2) if has_mu else np.ones(n_c),
            (np.bincount(p_c, None, n_c) / sigma_b ** 2 + 1 / tau_b ** 2) if has_nu else np.ones(n_c),
            [n_c / tau_b ** 2 if has_nu else 1.0]])

        def hvp(v):
            vt, vb, vm, vn, vn0 = unpack(v)
            u = w * (vt[team] - vb[prob])
            dt = vt - (np.bincount(r_t, r_w * vm[r_c], n_t) if has_mu else 0)
            db = vb - (vn[p_c] if has_nu else 0)
            return np.concatenate([
                np.bincount(team, u, n_t) + dt / sigma ** 2,
                -np.bincount(prob, u, n_p) + db / sigma_b ** 2,
                (-wt(dt) / sigma ** 2 + vm / tau ** 2) if has_mu else vm,
                (-np.bincount(p_c, db, n_c) / sigma_b ** 2 + (vn - vn0) / tau_b ** 2) if has_nu else vn,
                [-np.sum(vn - vn0) / tau_b ** 2 if has_nu else vn0]])

        # preconditioned conjugate gradients for H d = -grad
        d = np.zeros_like(x)
        r = -grad
        z = r / diag
        q = z.copy()
        rz = r @ z
        target = cg_tol * np.sqrt(grad @ grad)
        for _ in range(cg_max):
            hq = hvp(q)
            alpha = rz / (q @ hq)
            d += alpha * q
            r -= alpha * hq
            n_cg += 1
            if np.sqrt(r @ r) < target:
                break
            z = r / diag
            rz, rz_old = r @ z, rz
            q = z + (rz / rz_old) * q
        f0, slope, t = objective(x), grad @ d, 1.0
        while objective(x + t * d) > f0 + 1e-4 * t * slope:
            t *= 0.5
            if t < 1e-8:
                raise RuntimeError("line search failed")
        x = x + t * d
        step_max = float(np.max(np.abs(t * d)))
        if step_max < eps:
            break
    else:
        raise RuntimeError(f"hierarchical fit did not converge: last step {step_max:.3g}")
    if not np.all(np.isfinite(x)):
        raise RuntimeError("hierarchical fit produced non-finite values")
    th, b, mu, nu, nu0 = unpack(x.copy())
    return {"theta": th, "b": b, "mu": mu, "nu": nu, "nu0": float(nu0),
            "newton": n_newton, "cg": n_cg, "max_step": step_max}


# ---------------------------------------------------------------- experiment --


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "hier_binary_run"
OUT = ROOT / "output/hier_binary.json"
SEED = 20261106
SELECT_SPLIT, REPORT_SPLITS = 0, (1, 2)
FRAC = 0.2
# Selection grid, frozen before any team-side score was seen. Flat rows (tau=0,
# tau_b=0) include the shipped binary prior (sigma 400).
GRID = ([(s, t, sb, tb) for s in (250, 300, 400, 600) for t in (400, 800)
         for sb in (300, 400, 600) for tb in (0, 200, 400)]
        + [(s, 0, 400, tb) for s in (400, 600, 800, 1200) for tb in (0, 200, 400)])
BOOT = 2000


def config_name(cfg):
    return "hb_s{}_t{}_sb{}_tb{}".format(*[int(v) for v in cfg])


def appearance_split(ds, split):
    """Hold out FRAC of whole (contest, identity) appearances; returns a row mask."""
    key = ds.contest_of_row.astype(np.int64) * len(ds.teams) + ds.team_of_row
    _, inv = np.unique(key, return_inverse=True)
    return (np.random.default_rng([SEED, split]).random(inv.max() + 1) < FRAC)[inv]


def team_scores(ds, held_row, theta, b, kind):
    """Per-contest sums on held-out appearances (all / linked / cold cells, rows, pairs)."""
    from . import survival
    cells = held_row[ds.obs_row]
    team, prob, y = ds.team_of_row[ds.obs_row][cells], ds.obs_prob[cells], ds.obs_y[cells].astype(float)
    row, c = ds.obs_row[cells], ds.contest_of_row[ds.obs_row][cells]
    gap = (theta[team] - b[prob]) / S
    p = 1 / (1 + np.exp(-gap)) if kind == "binary" else 1 - np.exp(-survival.LN2 * np.exp(gap))
    p = np.clip(p, 1e-6, 1 - 1e-6)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    train_team = np.zeros(len(ds.teams), bool)
    train_team[ds.team_of_row[ds.obs_row][~held_row[ds.obs_row]]] = True
    linked = train_team[team]
    n_c = len(ds.contests)
    out = {}
    for name, m in (("all", np.ones(len(y), bool)), ("linked", linked), ("cold", ~linked)):
        out[name] = np.column_stack([np.bincount(c[m], ll[m], n_c), np.bincount(c[m], (p[m] - y[m]) ** 2, n_c),
                                     np.bincount(c[m], None, n_c)])
    # expected minus actual solves per held row, and rank-pair order among linked held rows
    exp_r = np.bincount(row, p, len(ds.team_of_row))
    act_r = np.bincount(row, y, len(ds.team_of_row))
    rows = np.flatnonzero(held_row)
    rows = rows[np.isin(rows, row)]
    sq = np.bincount(ds.contest_of_row[rows], (exp_r[rows] - act_r[rows]) ** 2, n_c)
    nr = np.bincount(ds.contest_of_row[rows], None, n_c)
    good = np.zeros(n_c)
    npairs = np.zeros(n_c)
    lrows = rows[train_team[ds.team_of_row[rows]]]
    for ci in np.unique(ds.contest_of_row[lrows]):
        r = lrows[ds.contest_of_row[lrows] == ci]
        if len(r) < 2:
            continue
        i, j = np.triu_indices(len(r), 1)
        rank, th = ds.rank_of_row[r], theta[ds.team_of_row[r]]
        keep = rank[i] != rank[j]
        agree = np.sign(rank[j] - rank[i]) * np.sign(th[i] - th[j])
        good[ci] = np.sum((agree[keep] > 0) + 0.5 * (agree[keep] == 0))
        npairs[ci] = keep.sum()
    out["rows"] = np.column_stack([sq, nr])
    out["pairs"] = np.column_stack([good, npairs])
    return out


def summarize(sc):
    a, l, cold = sc["all"].sum(0), sc["linked"].sum(0), sc["cold"].sum(0)
    return {"log_loss": a[0] / a[2], "brier": a[1] / a[2], "cells": int(a[2]),
            "linked_log_loss": l[0] / l[2], "linked_cells": int(l[2]),
            "cold_log_loss": cold[0] / max(cold[2], 1), "cold_cells": int(cold[2]),
            "solve_count_rmse": float(np.sqrt(sc["rows"][:, 0].sum() / sc["rows"][:, 1].sum())),
            "linked_pair_accuracy": float(sc["pairs"][:, 0].sum() / sc["pairs"][:, 1].sum()),
            "linked_pairs": int(sc["pairs"][:, 1].sum())}


def paired_bootstrap(a, b, seed=SEED):
    """Contest-resampled differences a - b of pooled metrics, from per-contest sums."""
    keys = ("log_loss", "linked_log_loss", "solve_count_rmse", "linked_pair_accuracy")
    used = np.flatnonzero(a["all"][:, 2] > 0)
    rng = np.random.default_rng(seed)

    def pooled(sc, idx):
        al, li = sc["all"][idx].sum(0), sc["linked"][idx].sum(0)
        rw, pr = sc["rows"][idx].sum(0), sc["pairs"][idx].sum(0)
        return np.array([al[0] / al[2], li[0] / max(li[2], 1), np.sqrt(rw[0] / rw[1]), pr[0] / max(pr[1], 1)])
    point = pooled(a, used) - pooled(b, used)
    draws = np.array([pooled(a, k) - pooled(b, k) for k in
                      (used[rng.integers(0, len(used), len(used))] for _ in range(BOOT))])
    lo, hi = np.percentile(draws, [2.5, 97.5], axis=0)
    return {k: [float(p), float(l), float(h)] for k, p, l, h in zip(keys, point, lo, hi)}


_G = {}


def _init():
    from .joint import load_joint_dataset
    from .run import MIN_SOLVE_HOURS
    ds, uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    _G.update(ds=ds, uf=uf)


def _team_job(job):
    """One fit on the training appearances of a split; returns per-contest scores."""
    from . import model, survival
    split, cfg = job
    ds = _G["ds"]
    held = appearance_split(ds, split)
    train = ~held[ds.obs_row]
    t, p, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    if cfg == "survival":
        _, _, _, rho = survival._survival_observations(ds, duration_mask=train)
        th, b, _ = survival.fit(ds, obs=(t[train], p[train], y[train], rho[train]), verbose=False)
        return job, team_scores(ds, held, th, b, "survival")
    if cfg == "binary":
        th, b, _ = model.fit(ds, obs=(t[train], p[train], y[train]), verbose=False)
        return job, team_scores(ds, held, th, b, "binary")
    res = fit(ds, obs=(t[train], p[train], y[train]), **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))
    return job, team_scores(ds, held, res["theta"], res["b"], "binary")


def _cached(name, compute):
    RUN.mkdir(exist_ok=True)
    path = RUN / f"{name}.json.gz"
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    value = compute()
    path.write_bytes(gzip.compress(json.dumps(value).encode(), mtime=0))
    return value


def _np(sc):
    return {k: np.array(v) for k, v in sc.items()}


def team_experiment(jobs):
    """Selection on split 0 over GRID; report splits with the selected config."""
    def select():
        todo = [(SELECT_SPLIT, "survival"), (SELECT_SPLIT, "binary")] + [(SELECT_SPLIT, cfg) for cfg in GRID]
        res = {}
        with ProcessPoolExecutor(jobs, initializer=_init) as ex:
            for (split, cfg), sc in ex.map(_team_job, todo):
                key = cfg if isinstance(cfg, str) else config_name(cfg)
                res[key] = {k: v.tolist() for k, v in sc.items()}
                print(f"select split {split}: {key} log loss {summarize(sc)['log_loss']:.5f}", flush=True)
        return res
    sel = _cached("team_select", select)
    summary = {k: summarize(_np(v)) for k, v in sel.items()}
    flat = [c for c in GRID if c[1] == 0]
    chosen, stage2 = stability_selection(summary, jobs)
    chosen_flat = min(flat, key=lambda c: (summary[config_name(c)]["log_loss"], c))

    def report():
        todo = [(s, m) for s in REPORT_SPLITS for m in ("survival", "binary", chosen, chosen_flat)]
        res = {}
        with ProcessPoolExecutor(jobs, initializer=_init) as ex:
            for (split, cfg), sc in ex.map(_team_job, todo):
                key = cfg if isinstance(cfg, str) else config_name(cfg)
                res[f"{split}:{key}"] = {k: v.tolist() for k, v in sc.items()}
                print(f"report split {split}: {key} {summarize(sc)}", flush=True)
        return res
    rep = _cached("team_report_" + config_name(chosen) + "_" + config_name(chosen_flat), report)
    out = {"selection_split": SELECT_SPLIT, "selection": summary, "stability_selection": stage2,
           "selected": list(chosen), "selected_flat": list(chosen_flat), "report": {}}
    names = {"survival": "survival", "binary": "binary", "hb": config_name(chosen), "flat": config_name(chosen_flat)}
    for split in REPORT_SPLITS:
        sc = {m: _np(rep[f"{split}:{k}"]) for m, k in names.items()}
        out["report"][str(split)] = {
            "summary": {m: summarize(v) for m, v in sc.items()},
            "hb_minus_survival": paired_bootstrap(sc["hb"], sc["survival"]),
            "hb_minus_binary": paired_bootstrap(sc["hb"], sc["binary"]),
            "hb_minus_flat": paired_bootstrap(sc["hb"], sc["flat"])}
    return out, chosen, chosen_flat


# ------------------------------------------------------- forward forecasts --

def forward_experiment(cfg):
    """Recorded-date replay (member_forecast panel): flat binary vs this fit."""
    from types import SimpleNamespace
    from . import member_forecast as mf, model
    boards, excluded, _ = mf.panel()
    records = {"flat": [], "hb": []}
    for target in boards:
        earlier = [b for b in boards if b["end"] < target["start"]]
        if not earlier:
            for k in records:
                records[k].append({"contest_id": target["contest_id"], "date": target["date"], "rows": []})
            continue
        ds = mf.training_data(earlier)
        sizes = [b["n_problems"] for b in earlier]
        ds = SimpleNamespace(**vars(ds), contests=list(range(len(earlier))),
                             contest_of_problem=np.repeat(np.arange(len(earlier)), sizes))
        th_flat, _, _ = model.fit(ds, verbose=False, eps=mf.EPS, max_iter=400)
        th_hb = fit(ds, **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))["theta"]
        latest = {}
        for b in sorted(earlier, key=lambda b: b["end"]):
            for r in b["rows"]:
                for m in r["roster"]:
                    when, sources = latest.get(m, (-1, set()))
                    if b["end"] > when:
                        latest[m] = (b["end"], {r["key"]})
                    elif b["end"] == when:
                        sources.add(r["key"])
        for name, th in (("flat", th_flat), ("hb", th_hb)):
            static = dict(zip(ds.teams, th))
            rows = []
            for r in target["rows"]:
                if not r["roster"]:
                    continue
                sources = [next(iter(latest[m][1])) for m in r["roster"] if m in latest and len(latest[m][1]) == 1]
                seen = r["key"] in static
                if not seen and not sources:
                    continue
                rows.append({"rank": r["rank"], "roster": r["roster"], "history": seen,
                             "static": float(static[r["key"]]) if seen else MU0,
                             "member_delta": 0.0 if seen else sum(float(static[s]) - MU0 for s in sources) / 3})
            records[name].append({"contest_id": target["contest_id"], "date": target["date"], "rows": rows})
        print(f"forward {target['date']} {target['contest_id']}", flush=True)

    def scores(recs, weight=0.0, population="combined"):
        return {r["contest_id"]: s for r in recs if (s := mf.score(r["rows"], weight, False, population)) is not None}
    out = {"panel_boards": len(boards), "excluded": len(excluded)}
    for name, recs in records.items():
        tune = [r for r in recs if r["date"].startswith("2023")]
        weight = min(mf.WEIGHTS, key=lambda w: (mf.aggregate(scores(tune, w, "cold_involving"))["contest_log_loss"], w))
        out[f"{name}_member_weight"] = weight
    ev = {k: [r for r in v if r["date"] >= "2024-01-01"] for k, v in records.items()}
    for population in ("history", "cold_involving", "combined"):
        res = {}
        for name in records:
            for members in (False, True):
                w = out[f"{name}_member_weight"] if members else 0.0
                res[f"{name}{'+members' if members else ''}"] = scores(ev[name], w, population)
        out[population] = {k: mf.aggregate(v) for k, v in res.items()}
        out[population]["hb_minus_flat"] = mf.comparison(res["hb"], res["flat"])
        out[population]["hb+members_minus_flat+members"] = mf.comparison(res["hb+members"], res["flat+members"])
    return out


# --------------------------------------------------------- field stability --

def _view_init():
    from . import de_stability_data as dsd
    dsd.initialize()
    _G["view_state"] = dsd._STATE


def _view_job(job):
    """Refit one de_stability view with each model; anchor b and anchor-board team theta."""
    from . import de_stability_data as dsd, model, survival
    view, cfgs = job
    ds, anchors, boards, ctx = _G["view_state"]
    team, prob = ds.team_of_row[ds.obs_row], ds.obs_prob
    y = ds.obs_y.astype(float)
    excluded = np.array([], int)
    selector = eligible = None
    if view in ("strength_pool", "strong", "weak"):   # same selection as de_stability_data
        others = np.setdiff1d(np.arange(len(ds.contests)), boards)
        a = np.random.default_rng(20261305).permutation(others)[::2]
        cells_a = np.isin(ds.contest_of_row[ds.obs_row], a)
        cells_b = ~np.isin(ds.contest_of_row[ds.obs_row], np.r_[boards, a])
        selector, _, _ = model.fit(ds, obs=(team[cells_a], prob[cells_a], y[cells_a]), verbose=False)
        eligible = np.zeros(len(ds.teams), bool)
        eligible[np.intersect1d(team[cells_a], team[cells_b])] = True
        excluded = a
    rows = dsd.sample_rows(ds, ctx, boards, view, selector, eligible)
    active = ~np.isin(ds.contest_of_row, np.r_[boards, excluded])
    active[rows] = True
    cells = active[ds.obs_row]
    obs = (team[cells], prob[cells], y[cells])
    pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(r["contest_id"], r["problem_label"])] for r in anchors])
    fields = np.bincount(ds.contest_of_row[rows], minlength=len(ds.contests))
    has = fields[ds.contest_of_problem[idx]] > 0
    kept_teams = np.unique(ds.team_of_row[rows])
    fits = {}
    _, _, _, rho = survival._survival_observations(ds, duration_mask=cells)
    th, _, _ = survival.fit(ds, obs=obs + (rho[cells],), verbose=False)
    fits["survival"] = {"theta": th[kept_teams].tolist()}
    th, b, _ = model.fit(ds, obs=obs, verbose=False)
    fits["binary"] = {"b": b[idx].tolist(), "theta": th[kept_teams].tolist()}
    for name, cfg in cfgs.items():
        res = fit(ds, obs=obs, rows=active, **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))
        fits[name] = {"b": res["b"][idx].tolist(), "theta": res["theta"][kept_teams].tolist()}
    return view, {"kept_anchor_rows": rows.tolist(), "kept_teams": kept_teams.tolist(),
                  "has_field": has.tolist(), "fits": fits}


TOLERANCE = 0.01   # stage 1: within 1% of the best held-out team log loss


def _drift_job(job):
    """Latent difficulties of every problem on the anchor boards, one view and setting."""
    from . import de_stability_data as dsd
    view, cfg = job
    ds, anchors, boards, ctx = _G["view_state"]
    team, prob = ds.team_of_row[ds.obs_row], ds.obs_prob
    rows = dsd.sample_rows(ds, ctx, boards, view)
    active = ~np.isin(ds.contest_of_row, boards)
    active[rows] = True
    cells = active[ds.obs_row]
    probs = np.flatnonzero(np.isin(ds.contest_of_problem, boards))
    res = fit(ds, obs=(team[cells], prob[cells], ds.obs_y[cells].astype(float)), rows=active,
              **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))
    return job, res["b"][probs].tolist()


def stability_selection(summary, jobs):
    """Stage 2: among settings within TOLERANCE of the best team log loss, the one whose
    anchor-board difficulties move least (RMS / full-view SD) across the training views.
    Uses no CF label and no reserved view."""
    from .de_stability_data import TRAIN
    best = min(summary[config_name(c)]["log_loss"] for c in GRID if c[1] > 0)
    admissible = [c for c in GRID if c[1] > 0 and summary[config_name(c)]["log_loss"] <= best * (1 + TOLERANCE)]

    def compute():
        out = {}
        todo = [(v, c) for c in admissible for v in TRAIN]
        with ProcessPoolExecutor(jobs, initializer=_view_init) as ex:
            for (view, cfg), b in ex.map(_drift_job, todo):
                out[f"{view}:{config_name(cfg)}"] = b
                print(f"drift {view} {config_name(cfg)}", flush=True)
        return out
    cache = _cached("stability_select", compute)
    scores = {}
    for c in admissible:
        full = np.array(cache[f"full:{config_name(c)}"])
        rel = [float(np.sqrt(np.mean((np.array(cache[f"{v}:{config_name(c)}"]) - full) ** 2)) / full.std())
               for v in TRAIN if v != "full"]
        scores[config_name(c)] = {"log_loss": summary[config_name(c)]["log_loss"],
                                  "relative_drift": float(np.mean(rel)), "per_view": rel}
    chosen = min(admissible, key=lambda c: (scores[config_name(c)]["relative_drift"], c))
    return chosen, {"tolerance": TOLERANCE, "best_log_loss": best, "admissible": len(admissible),
                    "scores": scores}


def view_experiment(cfgs, jobs):
    from .de_stability_data import VIEWS
    key = "views_" + "_".join(config_name(c) for c in cfgs.values())

    def compute():
        out = {}
        with ProcessPoolExecutor(jobs, initializer=_view_init) as ex:
            for view, rec in ex.map(_view_job, [(v, cfgs) for v in VIEWS]):
                out[view] = rec
                print(f"view {view} done", flush=True)
        return out
    return _cached(key, compute)


def stability_scorecard(views, cfgs):
    """CF accuracy and drift per view, with the DE predictions of the de_stability run."""
    from .calibration_ablation import _purged_train
    from .de_release_audit import contest_bootstrap
    from .de_stability import drift, metrics
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    de_eval = json.loads((ROOT / "output/de_stability_evaluation.json").read_text(encoding="utf-8"))
    de_pred = {v: {r["row_id"]: r for f in de_eval["folds"].values() for r in f["predictions"][v]}
               for v in views}
    models = ["binary"] + list(cfgs)
    full = views["full"]["fits"]
    preds = {v: [] for v in views}
    for c in sorted({a["cf_contest"] for a in anchors}):
        held_i = [i for i, a in enumerate(anchors) if a["cf_contest"] == c]
        held_ids = {anchors[i]["row_id"] for i in held_i}
        train_i = [i for i, a in enumerate(anchors) if a["row_id"] in
                   {r["row_id"] for r in _purged_train(anchors, [anchors[j] for j in held_i])}]
        maps = {m: np.polyfit(np.array(full[m]["b"])[train_i], [anchors[i]["cf"] for i in train_i], 1)
                for m in models}
        for v, rec in views.items():
            for i in held_i:
                if not rec["has_field"][i]:
                    continue
                a = anchors[i]
                row = {"row_id": a["row_id"], "canonical_task": a["canonical_task"], "cf_contest": c,
                       "cf": a["cf"], "region": a["region"], "DE": de_pred[v][a["row_id"]]["DE"]}
                for m in models:
                    row[m] = float(np.polyval(maps[m], rec["fits"][m]["b"][i]))
                preds[v].append(row)
        assert held_ids
    card = {}
    for v, rows in preds.items():
        ref = preds["strength_pool" if v in ("strong", "weak", "strength_pool") else "full"]
        card[v] = {}
        for m in ["DE"] + models:
            entry = {**metrics(rows, m), "drift": drift(rows, ref, m)}
            if m != "DE":
                entry["rmse_minus_DE"] = contest_bootstrap(rows, np.array([r[m] for r in rows]),
                                                           np.array([r["DE"] for r in rows]), n=BOOT)
            card[v][m] = entry
    # team-rating drift: anchor-board teams kept in a view vs the full / pool fit
    slopes = {m: float(np.polyfit(full[m]["b"], [a["cf"] for a in anchors], 1)[0]) for m in models}
    team_drift = {}
    for v, rec in views.items():
        refv = views["strength_pool" if v in ("strong", "weak") else "full"]
        pos = {t: k for k, t in enumerate(refv["kept_teams"])}
        common = [(k, pos[t]) for k, t in enumerate(rec["kept_teams"]) if t in pos]
        if v in ("full", "strength_pool") or not common:
            continue
        team_drift[v] = {}
        for m in ["survival"] + models:
            d = np.array([rec["fits"][m]["theta"][k] - refv["fits"][m]["theta"][j] for k, j in common])
            spread = float(np.std([refv["fits"][m]["theta"][j] for _, j in common]))
            team_drift[v][m] = {"teams": len(d), "signed_mean_latent": float(d.mean()),
                                "rms_latent": float(np.sqrt(np.mean(d ** 2))),
                                "rms_over_team_sd": float(np.sqrt(np.mean(d ** 2)) / spread)}
    return {"scorecard": card, "map_slopes": slopes, "team_theta_drift": team_drift, "predictions": preds}


# -------------------------------------------------- external team yardstick --

def external_team_check(cfgs):
    """Full-data team ratings, on each model's own problem->CF map, vs CF team ability."""
    from . import model, survival
    from .cf_prior import team_abilities
    _init()
    ds, uf = _G["ds"], _G["uf"]
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(r["contest_id"], r["problem_label"])] for r in anchors])
    cf = np.array([r["cf"] for r in anchors])
    index = {tk: i for i, tk in enumerate(ds.teams)}
    pairs = [(index[tk], v[0]) for tk, v in team_abilities(uf).items() if tk in index]
    ti, target = np.array([i for i, _ in pairs]), np.array([c for _, c in pairs])
    fits = {"survival": survival.fit(ds, verbose=False)[:2], "binary": model.fit(ds, verbose=False)[:2]}
    for name, cfg in cfgs.items():
        res = fit(ds, **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))
        fits[name] = (res["theta"], res["b"])
    out = {"teams": len(pairs)}
    rng = np.random.default_rng(SEED)
    for name, (theta, b) in fits.items():
        slope, icept = np.polyfit(b[idx], cf, 1)
        mapped = slope * theta[ti] + icept
        err = mapped - target
        boot = [np.sqrt(np.mean(err[k] ** 2)) for k in (rng.integers(0, len(err), len(err)) for _ in range(BOOT))]
        out[name] = {"problem_map_slope": float(slope), "mean_error": float(err.mean()),
                     "rmse": float(np.sqrt(np.mean(err ** 2))),
                     "rmse_bootstrap_2.5_97.5": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                     "pearson": float(np.corrcoef(theta[ti], target)[0, 1]),
                     "ols_slope_cf_on_theta": float(np.polyfit(theta[ti], target, 1)[0])}
    return out


def compare_with_de(cfg):
    """Full-data problem ratings on the affine CF map vs shipped DE, by contest."""
    from .calibrate import problem_cf
    from .context_fit import raw_by_contest
    _init()
    ds = _G["ds"]
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(r["contest_id"], r["problem_label"])] for r in anchors])
    res = fit(ds, **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), cfg)))
    slope, icept = np.polyfit(res["b"][idx], [r["cf"] for r in anchors], 1)
    ours = np.clip(slope * res["b"] + icept, elo.LO, elo.HI)
    shipped = problem_cf(ds.problems)
    de = np.array([shipped[(int(c), label)] for c, label, _, _ in ds.problems])
    raw = raw_by_contest()
    contests = []
    for ci, cid in enumerate(ds.contests):
        m = ds.contest_of_problem == ci
        if not m.any():
            continue
        c = raw.get(cid, {})
        contests.append({"contest_id": int(cid), "name": c.get("contest_name") or str(cid),
                         "region": c.get("region") or "", "year": c.get("year"),
                         "problems": int(m.sum()), "mean_minus_de": float(np.mean(ours[m] - de[m])),
                         "board_mu": float(res["mu"][ci]), "teams": int(np.sum(ds.contest_of_row == ci))})
    contests.sort(key=lambda r: r["mean_minus_de"])
    diff = ours - de
    return {"map": {"slope": float(slope), "intercept": float(icept)},
            "problems": len(diff), "mean_minus_de": float(diff.mean()), "sd_minus_de": float(diff.std()),
            "spearman_with_de": float(np.corrcoef(np.argsort(np.argsort(ours)), np.argsort(np.argsort(de)))[0, 1]),
            "contests": contests,
            "ratings": [{"contest_id": int(c), "problem_label": label, "hier_cf": round(float(o), 1),
                         "de_cf": round(float(d), 1), "solved": int(ds.solved_count[p]),
                         "field": int(ds.field_count[p])}
                        for p, ((c, label, _, _), o, d) in enumerate(zip(ds.problems, ours, de))]}


def sha256s():
    names = ["arch_b/hier_binary.py", "arch_b/model.py", "arch_b/survival.py", "arch_b/de_stability_data.py",
             "arch_b/de_stability.py", "arch_b/member_forecast.py", "arch_b/cf_prior.py", "arch_a/elo.py",
             "arch_a/load.py", "arch_b/joint.py", "data/de_stability_anchors.json",
             "output/de_stability_evaluation.json", "data/tagged.json"]
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}


def main(jobs):
    teams, chosen, chosen_flat = team_experiment(jobs)
    cfgs = {"hb": chosen, "flat": chosen_flat}
    print(f"selected {config_name(chosen)} / flat {config_name(chosen_flat)}", flush=True)
    views = view_experiment(cfgs, jobs)
    stability = stability_scorecard(views, cfgs)
    forward = _cached("forward_" + config_name(chosen), lambda: forward_experiment(chosen))
    external = _cached("external_" + config_name(chosen) + "_" + config_name(chosen_flat),
                       lambda: external_team_check(cfgs))
    versus = _cached("versus_de_" + config_name(chosen), lambda: compare_with_de(chosen))
    out = {"research_only": True, "independent_confirmation": False, "sha256": sha256s(),
           "selected_config": dict(zip(("sigma", "tau", "sigma_b", "tau_b"), chosen)),
           "selected_flat_config": dict(zip(("sigma", "tau", "sigma_b", "tau_b"), chosen_flat)),
           "team_prediction": teams, "field_stability": stability, "forward_forecast": forward,
           "external_cf_teams": external, "versus_shipped_de": {k: v for k, v in versus.items() if k != "ratings"}}
    (ROOT / "output/hier_binary_ratings.json").write_text(
        json.dumps({"research_only": True, "config": out["selected_config"], "map": versus["map"],
                    "problems": versus["ratings"]}, indent=0) + "\n")
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(f"wrote {OUT}")
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["teams"]:
        out, chosen, flat = team_experiment(int(sys.argv[2]) if len(sys.argv) > 2 else 8)
        print(json.dumps({"selected": out["selected"], "selected_flat": out["selected_flat"],
                          "report": {s: r["summary"] for s, r in out["report"].items()}}, indent=1))
    elif sys.argv[1:2] == ["all"]:
        main(int(sys.argv[2]) if len(sys.argv) > 2 else 8)
