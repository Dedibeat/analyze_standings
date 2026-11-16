"""Solve time in the hierarchical binary fit. See hier_time_report.md.

``hier_binary`` only knows whether a cell was solved. Here a solved cell also
says in which of ``bins`` equal slices of the contest window it was solved
(u = solve time / T_c, T_c the board's latest solve, as in ``survival``):

    P(solved by the end of slice k) = sigma(g - d_k),   g = (theta - b) / s,
    d_1 > ... > d_bins = 0

The last slice is the binary model itself, so theta and b keep its scale and a
team rated R still solves a problem rated R half the time. The thresholds d are
global and estimated by maximum likelihood, alternating with the fit (the joint
problem is convex, so the start does not matter).

The time likelihood enters at ``weight`` next to the binary one at 1 - weight.
At full weight it stretches difficulties within a board (teams solve easy
problems first, and the slices read that as extra ease) and costs held-out
accuracy. A small weight acts where the binary data is flat: at the floor.

A setting is (bins, weight, skip); ``skip`` also treats skip_cells'
``skip_partial`` cells as missing. (0, 0, False) is the frozen hier_binary fit.

    python -m arch_b.hier_time select [JOBS]     # dose selection, no CF label
    python -m arch_b.hier_time evaluate [JOBS]   # -> output/hier_time.json
    python -m arch_b.hier_time release           # -> output/problem_ratings_hier.json (+ problem_calibration_hier.json)
"""

import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from arch_a import elo
from . import hier_binary as hb, survival
from .skip_cells import CFG, skipped

S = elo.S
KW = dict(zip(("sigma", "tau", "sigma_b", "tau_b"), CFG))
BASE = (0, 0.0, False)
# Dose grid, frozen before the formal run (hier_time_report.md, Protocol).
GRID = [(k, w, False) for k in (3, 5, 10) for w in (0.05, 0.1, 0.25, 0.5, 1.0)]
OUT = hb.ROOT / "output/hier_time.json"
RELEASE = hb.ROOT / "output/problem_ratings_hier.json"
RELEASE_META = hb.ROOT / "output/problem_calibration_hier.json"
# Contests added on 2026-11-15, after the hier_binary setting was frozen (2026-11-05).
ADDED = (-216770522111721, -162528714534630, 4126, 4207, 4538, 4565, 4566, 4569, 4576, 4593, 4605,
         4606, 4607, 4614, 4617, 4620, 4694)
# Labels documented as wrong, left out of every CF map and RMSE here. Uniform Chemistry
# (SWERC 2022 B) is CF 3200 and about 2000 by hand (problem_rating_audit.md); Wuhan 2025 F
# was rated 2200 blind and 93% of its board solved it (skip_cells_report.md).
WRONG_ANCHORS = {(1123, "B")}
WRONG_HAND = {(2609, "F")}
FRESH_BOARDS = {4593: "Xi'an 2026", 4607: "Chengdu 2026", 4694: "Wuhan 2026",
                -216770522111721: "Nanjing 2026", -162528714534630: "Shenyang 2026"}


def name(setting):
    bins, weight, skip = setting
    return ("base" if not bins else f"k{bins}_w{weight:g}") + ("_skip" if skip else "")


def thresholds(g, k, d):
    """Maximum-likelihood thresholds for solved cells in slices ``k`` (1..K) at gaps ``g``."""
    n = len(d)
    up, low = k <= n, k >= 2          # cells whose upper / lower end is a free threshold

    def parts(d):
        ends = np.r_[np.inf, d, 0.0]
        a, b = ends[k], ends[k - 1]   # P(cell) = sigma(g - a) - sigma(g - b)
        with np.errstate(over="ignore", invalid="ignore"):
            e = np.exp(b - a)
            r, q = np.where(low, 1 / (e - 1), 0.0), np.where(low, e / (e - 1) ** 2, 0.0)
        ll = -np.sum(np.logaddexp(0, a - g) + np.logaddexp(0, g - b)) + np.sum(np.log1p(-np.exp((a - b)[low])))
        return ll, 1 / (1 + np.exp(a - g)), 1 / (1 + np.exp(b - g)), r, q

    for _ in range(50):
        ll, fa, fb, r, q = parts(d)
        grad = np.bincount(k[up] - 1, -(1 - fa[up]) - r[up], n) + np.bincount(k[low] - 2, fb[low] + r[low], n)
        hess = np.diag(np.bincount(k[up] - 1, -(fa * (1 - fa))[up] - q[up], n)
                       + np.bincount(k[low] - 2, -(fb * (1 - fb))[low] - q[low], n))
        off = np.bincount(k[up & low] - 2, q[up & low], n)[:n - 1]
        hess[np.arange(n - 1), np.arange(1, n)] += off
        hess[np.arange(1, n), np.arange(n - 1)] += off
        step = np.linalg.solve(hess, -grad)
        t = 1.0
        while np.any(np.diff(np.r_[d + t * step, 0.0]) >= 0) or parts(d + t * step)[0] < ll - 1e-9:
            t /= 2
            if t < 1e-8:
                raise RuntimeError("threshold line search failed")
        d = d + t * step
        if np.max(np.abs(t * step)) < 1e-6:
            return d
    raise RuntimeError("thresholds did not converge")


def fit(ds, setting=BASE, cells=None, rows=None, tol=0.01):
    """Hierarchical fit of ``setting`` on the observation mask ``cells``.

    Returns hier_binary's dict plus ``d`` (the thresholds) and ``cells`` (the
    mask actually fitted, after the skip rule). ``rows`` is passed through.
    """
    bins, weight, skip = setting
    cells = np.ones(len(ds.obs_y), bool) if cells is None else cells
    if skip:
        cells = cells & ~skipped(ds, cells, "skip_partial")
    team, prob, y = ds.team_of_row[ds.obs_row][cells], ds.obs_prob[cells], ds.obs_y[cells]
    obs = (team, prob, y.astype(float))
    if not bins:
        return {**hb.fit(ds, obs=obs, rows=rows, **KW), "d": np.zeros(0), "cells": cells}
    edges = np.arange(1, bins) / bins
    rho = survival._survival_observations(ds, duration_mask=cells)[3][cells]
    k = np.where(y, 1 + np.searchsorted(edges, rho, side="left"), 0)
    d, res = -3.0 * np.log(edges), {"x": None}
    for _ in range(30):
        ends = np.r_[np.inf, d, 0.0]
        cuts = (np.where(y, ends[np.maximum(k, 1)], -np.inf), np.where(y, ends[np.maximum(k, 1) - 1], 0.0))
        res = hb.fit(ds, obs=obs, rows=rows, cuts=cuts, cut_weight=weight, start=res["x"], **KW)
        new = thresholds((res["theta"][team] - res["b"][prob])[y] / S, k[y], d)
        moved, d = np.max(np.abs(new - d)), new
        if moved < tol:
            return {**res, "d": d, "cells": cells}
    raise RuntimeError("time thresholds did not settle")


# ---------------------------------------------------------------- experiment --

def _anchors():
    return json.loads((hb.ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))


def _anchor_index(ds):
    pi = {(cid, lab): p for p, (cid, lab, _, _) in enumerate(ds.problems)}
    return np.array([pi[(a["contest_id"], a["problem_label"])] for a in _anchors()]), pi


def _used(anchors):
    """Positions of the anchors whose CF label is trusted."""
    return [i for i, a in enumerate(anchors) if (a["contest_id"], a["problem_label"]) not in WRONG_ANCHORS]


def _cf_map(b, anchors):
    """Affine CF map from the trusted anchors; ``b`` is aligned with ``anchors``."""
    use = _used(anchors)
    return np.polyfit(np.asarray(b)[use], [anchors[i]["cf"] for i in use], 1)


def _split_job(job):
    """One fit on a split's training appearances; held-out scores on all and on non-skipped cells."""
    from . import model
    split, setting = job
    ds = hb._G["ds"]
    held = hb.appearance_split(ds, split)
    train = ~held[ds.obs_row]
    t, p, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    kind = "binary"
    if setting == "survival":
        rho = survival._survival_observations(ds, duration_mask=train)[3]
        theta, b, _ = survival.fit(ds, obs=(t[train], p[train], y[train], rho[train]), verbose=False)
        kind = "survival"
    elif setting == "binary":
        theta, b, _ = model.fit(ds, obs=(t[train], p[train], y[train]), verbose=False)
    else:
        res = fit(ds, tuple(setting), train)
        theta, b = res["theta"], res["b"]
    board_skip = skipped(ds, np.ones(len(ds.obs_y), bool), "skip_all")
    return job, {"all": hb.team_scores(ds, held, theta, b, kind),
                 "non_skipped": hb.team_scores(ds, held, theta, b, kind, ~board_skip)}


def _splits(key, todo, jobs):
    def compute():
        out = {}
        with ProcessPoolExecutor(jobs, initializer=hb._init) as ex:
            for (split, setting), sc in ex.map(_split_job, todo):
                n = setting if isinstance(setting, str) else name(setting)
                out[f"{split}:{n}"] = {k: {m: v.tolist() for m, v in s.items()} for k, s in sc.items()}
                print(f"split {split} {n} log loss {hb.summarize(sc['all'])['log_loss']:.5f}", flush=True)
        return out
    return hb._cached(key, compute)


def _view_cells(view):
    """Rows and cells of one de_stability view (same selection as hier_binary._view_job)."""
    from . import de_stability_data as dsd, model
    ds, _, boards, ctx = hb._G["view_state"]
    team, prob, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    excluded = np.array([], int)
    selector = eligible = None
    if view in ("strength_pool", "strong", "weak"):
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
    return rows, active


def _view_job(job):
    """One view, several settings: anchor b, kept-team theta, and b of every anchor-board problem."""
    view, settings = job
    ds, _, boards, _ = hb._G["view_state"]
    rows, active = _view_cells(view)
    idx, _ = _anchor_index(ds)
    has = np.bincount(ds.contest_of_row[rows], minlength=len(ds.contests))[ds.contest_of_problem[idx]] > 0
    kept = np.unique(ds.team_of_row[rows])
    board_problems = np.flatnonzero(np.isin(ds.contest_of_problem, boards))
    fits = {}
    for setting in settings:
        res = fit(ds, tuple(setting), active[ds.obs_row], rows=active)
        fits[name(setting)] = {"b": res["b"][idx].tolist(), "theta": res["theta"][kept].tolist(),
                               "board_b": res["b"][board_problems].tolist(), "d": res["d"].tolist()}
    return view, {"kept_teams": kept.tolist(), "has_field": has.tolist(), "fits": fits}


def _views(key, views, settings, jobs):
    def compute():
        out = {}
        with ProcessPoolExecutor(jobs, initializer=hb._view_init) as ex:
            for view, rec in ex.map(_view_job, [(v, settings) for v in views]):
                out[view] = rec
                print(f"view {view} done", flush=True)
        return out
    return hb._cached(key, compute)


def select(jobs):
    """Stage 1: held-out log loss on split 0 within 1% of the best. Stage 2: among those time
    settings, the least latent-difficulty drift over the training views. No CF label is used."""
    from .de_stability_data import TRAIN
    raw = _splits("time_select", [(hb.SELECT_SPLIT, s) for s in [BASE] + GRID], jobs)
    loss = {s: hb.summarize(hb._np(raw[f"{hb.SELECT_SPLIT}:{name(s)}"]["all"]))["log_loss"] for s in [BASE] + GRID}
    best = min(loss.values())
    admissible = [s for s in GRID if loss[s] <= best * (1 + hb.TOLERANCE)]
    if not admissible:
        return None, {"log_loss": {name(s): v for s, v in loss.items()}, "admissible": []}
    views = _views("time_drift_" + "_".join(name(s) for s in admissible), TRAIN, [BASE] + admissible, jobs)
    drift = {}
    for s in [BASE] + admissible:
        full = np.array(views["full"]["fits"][name(s)]["board_b"])
        drift[s] = float(np.mean([np.sqrt(np.mean((np.array(views[v]["fits"][name(s)]["board_b"]) - full) ** 2))
                                  / full.std() for v in TRAIN if v != "full"]))
    chosen = min(admissible, key=lambda s: (drift[s], s))
    return chosen, {"tolerance": hb.TOLERANCE, "log_loss": {name(s): v for s, v in loss.items()},
                    "admissible": [name(s) for s in admissible],
                    "relative_drift": {name(s): v for s, v in drift.items()}, "selected": name(chosen)}


def scorecard(views, names):
    """Nested-LOCO CF accuracy and drift per view; maps come from the full view's other contests."""
    from .calibration_ablation import _purged_train
    from .de_release_audit import contest_bootstrap
    from .de_stability import drift, metrics
    anchors = _anchors()
    cf = np.array([a["cf"] for a in anchors])
    used = _used(anchors)
    preds = {v: [] for v in views}
    for c in sorted({a["cf_contest"] for a in anchors}):
        held = [i for i in used if anchors[i]["cf_contest"] == c]
        keep = {r["row_id"] for r in _purged_train(anchors, [anchors[i] for i in held])}
        train = [i for i in used if anchors[i]["row_id"] in keep]
        maps = {m: np.polyfit(np.array(views["full"]["fits"][m]["b"])[train], cf[train], 1) for m in names}
        for v, rec in views.items():
            preds[v] += [{"row_id": anchors[i]["row_id"], "cf_contest": c, "cf": anchors[i]["cf"],
                          "region": anchors[i]["region"],
                          **{m: float(np.polyval(maps[m], rec["fits"][m]["b"][i])) for m in names}}
                         for i in held if rec["has_field"][i]]
    card, team_drift = {}, {}
    for v, rows in preds.items():
        ref_view = "strength_pool" if v in ("strong", "weak", "strength_pool") else "full"
        card[v] = {}
        for m in names:
            full = metrics(rows, m)
            entry = {k: full.get(k) for k in ("problems", "rmse", "mean_error", "predicted_sd")}
            entry["drift"] = drift(rows, preds[ref_view], m)
            if m != names[0]:
                entry["rmse_minus_base"] = contest_bootstrap(rows, np.array([r[m] for r in rows]),
                                                             np.array([r[names[0]] for r in rows]), n=hb.BOOT)
            card[v][m] = entry
        if v in ("full", "strength_pool"):
            continue
        pos = {t: j for j, t in enumerate(views[ref_view]["kept_teams"])}
        common = [(j, pos[t]) for j, t in enumerate(views[v]["kept_teams"]) if t in pos]
        team_drift[v] = {}
        for m in names:
            a, b = np.array(views[v]["fits"][m]["theta"]), np.array(views[ref_view]["fits"][m]["theta"])
            delta = np.array([a[j] - b[i] for j, i in common])
            team_drift[v][m] = {"teams": len(delta), "signed_mean_latent": float(delta.mean()),
                                "rms_latent": float(np.sqrt(np.mean(delta ** 2)))}
    return {"scorecard": card, "team_theta_drift": team_drift, "predictions": preds}


def full_data(settings):
    """Full-data fits: CF map, hand panels, CF-rated teams, floors, and nested-LOCO DE on current data.
    Also writes every problem's rating under each setting to output/hier_time_ratings.json."""
    from scripts.problem_rating_audit import FRESH, HAND, hand_scores
    from .calibrate import problem_cf
    from .calibration_experiment import build_anchor_table
    from .cf_prior import team_abilities
    from .de_release_audit import loco
    hb._init()
    ds, uf = hb._G["ds"], hb._G["uf"]
    idx, pi = _anchor_index(ds)
    fresh = {k: v for k, v in FRESH.items() if k not in WRONG_HAND}
    shipped = problem_cf(ds.problems)
    de = np.array([shipped[(int(c), lab)] for c, lab, _, _ in ds.problems])
    index = {tk: i for i, tk in enumerate(ds.teams)}
    pairs = [(index[tk], v[0]) for tk, v in team_abilities(uf).items() if tk in index]
    ti, target = np.array([i for i, _ in pairs]), np.array([c for _, c in pairs])
    ratings, out = {"de": de}, {"maps": {}, "thresholds": {}, "missing_cells": {}, "external_cf_teams": {}}
    for label, setting in settings.items():
        res = fit(ds, setting)
        s, i = _cf_map(res["b"][idx], _anchors())
        ratings[label] = np.clip(s * res["b"] + i, elo.LO, elo.HI)
        out["maps"][label] = [float(s), float(i)]
        out["thresholds"][label] = res["d"].tolist()
        out["missing_cells"][label] = int((~res["cells"]).sum())
        err = s * res["theta"][ti] + i - target
        out["external_cf_teams"][label] = {"teams": len(err), "rmse": float(np.sqrt(np.mean(err ** 2))),
                                           "mean_error": float(err.mean())}
    out["hand_scores"] = hand_scores(pi, ratings)
    out["fresh_scores"] = hand_scores(pi, ratings, fresh)
    both = {**HAND, **fresh}
    out["both_panels"] = {n: {"bias": float(np.mean([r[pi[k]] - both[k][0] for k in both])),
                              "rmse": float(np.sqrt(np.mean([(r[pi[k]] - both[k][0]) ** 2 for k in both])))}
                          for n, r in ratings.items()}
    rate = ds.solved_count / np.maximum(ds.field_count, 1)
    bins = [(0, .005), (.005, .05), (.05, .3), (.3, .7), (.7, .95), (.95, 1.01)]
    out["minus_de_by_solve_rate"] = {
        label: {f"{lo}-{hi}": float(np.mean((ratings[label] - de)[(rate >= lo) & (rate < hi)])) for lo, hi in bins}
        for label in settings}
    out["minus_de"] = {label: {"mean": float(np.mean(ratings[label] - de)), "sd": float(np.std(ratings[label] - de))}
                       for label in settings}
    out["hand"] = [{"contest_id": c, "label": lab, "hand": h, "group": g,
                    **{n: round(float(r[pi[(c, lab)]]), 1) for n, r in ratings.items()}}
                   for (c, lab), (h, g, _) in both.items()]
    table = build_anchor_table()      # nested-LOCO DE on the current shipped fit, by anchor row
    table = [table[i] for i in _used(table)]
    out["de_nested_loco"] = dict(zip((r["row_id"] for r in table), loco(table, "clip")[0].tolist()))
    (hb.ROOT / "output/hier_time_ratings.json").write_text(json.dumps(
        {"research_only": True, "settings": {m: list(s) for m, s in settings.items()}, "maps": out["maps"],
         "problems": [{"contest_id": int(c), "problem_label": lab, "de_cf": round(float(de[p]), 1),
                       **{f"{m}_cf": round(float(ratings[m][p]), 1) for m in settings},
                       "solved": int(ds.solved_count[p]), "field": int(ds.field_count[p])}
                      for p, (c, lab, _, _) in enumerate(ds.problems)]}, indent=0) + "\n", encoding="utf-8")
    return out


def forward_2026(settings):
    """Fit without the contests added on 2026-11-15, then rank the linked teams of the five
    2026 EC regionals: the first results none of these models or settings ever saw."""
    from . import model
    hb._init()
    ds = hb._G["ds"]
    added = np.isin(ds.contests, ADDED)
    active = ~added[ds.contest_of_row]
    cells = active[ds.obs_row]
    t, p, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    seen = np.zeros(len(ds.teams), bool)
    seen[ds.team_of_row[active]] = True
    theta = {"binary": model.fit(ds, obs=(t[cells], p[cells], y[cells]), verbose=False)[0]}
    rho = survival._survival_observations(ds, duration_mask=cells)[3]
    theta["survival"] = survival.fit(ds, obs=(t[cells], p[cells], y[cells], rho[cells]), verbose=False)[0]
    for label, setting in settings.items():
        theta[label] = fit(ds, setting, cells, rows=active)["theta"]
    out = {"boards": {}}
    good, valid = {m: [] for m in theta}, []
    for cid, board in FRESH_BOARDS.items():
        r = np.flatnonzero((ds.contest_of_row == ds.contests.index(cid)) & seen[ds.team_of_row])
        rank = ds.rank_of_row[r]
        valid.append(np.triu(rank[:, None] != rank[None, :], 1).astype(float))
        out["boards"][board] = {"linked_rows": len(r), "pairs": int(valid[-1].sum()),
                                "rows": int(np.sum(ds.contest_of_row == ds.contests.index(cid)))}
        for m, th in theta.items():
            t = th[ds.team_of_row[r]]
            agree = np.sign(rank[None, :] - rank[:, None]) * np.sign(t[:, None] - t[None, :])
            good[m].append(valid[-1] * ((agree > 0) + 0.5 * (agree == 0)))
            out["boards"][board][m] = float(good[m][-1].sum() / valid[-1].sum())

    def pooled(m, w):      # pair accuracy with each linked row counted w times
        return sum(x @ g @ x for x, g in zip(w, good[m])) / sum(x @ v @ x for x, v in zip(w, valid))
    out["pooled"] = {m: float(pooled(m, [np.ones(len(v)) for v in valid])) for m in theta}
    rng = np.random.default_rng(hb.SEED)
    draws = {m: [] for m in theta}
    for _ in range(hb.BOOT):   # resample linked rows within each board, the same draw for every model
        w = [np.bincount(rng.integers(0, len(v), len(v)), minlength=len(v)).astype(float) for v in valid]
        for m in theta:
            draws[m].append(pooled(m, w))
    out["difference"] = {}
    for a, b in [("base", "binary"), ("base", "survival")] + [(m, "base") for m in settings if m != "base"]:
        d = np.array(draws[a]) - np.array(draws[b])
        out["difference"][f"{a}_minus_{b}"] = [out["pooled"][a] - out["pooled"][b],
                                               float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    return out


def verdict(full, splits, card, names):
    """The four pre-registered criteria of hier_time_report.md for every setting but base."""
    from .de_stability_data import STRESS
    out = {}
    reserved = [v for v in STRESS if v != "strength_pool"]
    for m in names[1:]:
        hand = full["hand_scores"]
        others = [g for g in hand if g not in ("all", "ec_signin")]
        worst = max(hand[g][m]["rmse"] - hand[g]["base"]["rmse"] for g in others)
        c1 = (abs(hand["ec_signin"][m]["bias"]) <= 150 and worst <= 50
              and full["fresh_scores"]["all"][m]["rmse"] < full["fresh_scores"]["all"]["base"]["rmse"])
        c2 = card["full"][m]["rmse_minus_base"]["bootstrap_2.5_97.5"][0] <= 0
        subset = "non_skipped" if m.endswith("skip") else "all"
        loss = [splits[str(s)][subset]["summary"][m]["log_loss"] / splits[str(s)][subset]["summary"]["base"]["log_loss"]
                for s in hb.REPORT_SPLITS]
        pair = [splits[str(s)]["all"][f"{m}_minus_base"]["linked_pair_accuracy"][0] for s in hb.REPORT_SPLITS]
        c3 = max(loss) <= 1 + hb.TOLERANCE and min(pair) >= (0 if m.startswith("time") else -np.inf)
        wins = sum(card[v][m]["drift"]["rms"] <= card[v]["base"]["drift"]["rms"] for v in reserved)
        out[m] = {"1_hand": bool(c1), "signin_bias": hand["ec_signin"][m]["bias"], "worst_other_group_rmse_change": worst,
                  "2_cf": bool(c2), "3_teams": bool(c3), "log_loss_ratio": loss, "pair_accuracy_change": pair,
                  "4_stability": bool(wins >= 5), "reserved_views_drift_le_base": int(wins),
                  "passes": bool(c1 and c2 and c3 and wins >= 5)}
    return out


def evaluate(jobs):
    from .de_release_audit import contest_bootstrap
    from .de_stability_data import VIEWS
    chosen, selection = select(jobs)
    settings = {"base": BASE, "skip": (0, 0.0, True)}
    if chosen is not None:
        settings.update(time=chosen, time_skip=(chosen[0], chosen[1], True))
    names = list(settings)
    tag = "_".join(name(s) for s in settings.values())
    raw = _splits("time_report_" + tag, [(s, x) for s in hb.REPORT_SPLITS
                                         for x in ["survival", "binary"] + list(settings.values())], jobs)
    key = {**{m: name(s) for m, s in settings.items()}, "survival": "survival", "binary": "binary"}
    splits = {}
    for split in hb.REPORT_SPLITS:
        splits[str(split)] = {}
        for subset in ("all", "non_skipped"):
            sc = {m: hb._np(raw[f"{split}:{k}"][subset]) for m, k in key.items()}
            splits[str(split)][subset] = {"summary": {m: hb.summarize(v) for m, v in sc.items()},
                                          **{f"{m}_minus_base": hb.paired_bootstrap(sc[m], sc["base"])
                                             for m in key if m != "base"}}
    views = _views("time_views_" + tag, VIEWS, list(settings.values()), jobs)
    views = {v: {**rec, "fits": {m: rec["fits"][name(s)] for m, s in settings.items()}} for v, rec in views.items()}
    card = scorecard(views, names)
    full = full_data(settings)
    rows = card["predictions"]["full"]
    de = np.array([full["de_nested_loco"][r["row_id"]] for r in rows])
    full["cf_full_fields"] = {"DE": {"rmse": float(np.sqrt(np.mean((de - [r["cf"] for r in rows]) ** 2)))},
                              **{m: {"rmse": card["scorecard"]["full"][m]["rmse"], "rmse_minus_DE": contest_bootstrap(
                                  rows, np.array([r[m] for r in rows]), de, n=hb.BOOT)} for m in names}}
    forward = hb._cached("time_forward_" + tag, lambda: forward_2026(settings))
    checks = verdict(full, splits, card["scorecard"], names)
    passing = [m for m in names[1:] if checks[m]["passes"]]
    best = min(passing, key=lambda m: full["both_panels"][m]["rmse"]) if passing else None
    # ties within 10 on the pooled hand panels go to the setting with fewer components
    candidate = next((m for m in passing if full["both_panels"][m]["rmse"] <= full["both_panels"][best]["rmse"] + 10),
                     "base")
    out = {"research_only": True, "independent_confirmation": False,
           "sha256": {p: hashlib.sha256((hb.ROOT / p).read_bytes()).hexdigest() for p in
                      ("arch_b/hier_time.py", "arch_b/hier_binary.py", "arch_b/skip_cells.py", "arch_a/load.py",
                       "scripts/problem_rating_audit.py", "data/de_stability_anchors.json", "data/tagged.json",
                       "output/problem_ratings_calibrated.json")},
           "config": list(CFG), "grid": [name(s) for s in GRID], "selection": selection,
           "settings": {m: list(s) for m, s in settings.items()}, "criteria": checks,
           "release_candidate": candidate, "full_data": full, "team_prediction": splits,
           "field_stability": {k: card[k] for k in ("scorecard", "team_theta_drift")}, "forward_2026": forward}
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"selected": selection.get("selected"), "criteria": checks, "release_candidate": candidate}, indent=1))
    print(f"wrote {OUT}")
    return out


def release():
    """Full-data fit of the release candidate, in the shipped files' layout: the records of
    problem_ratings_calibrated.json (``difficulty_cf`` and all) plus a CF-scale standard error."""
    from .calibrate import SMALL_BOARD_ROWS
    result = json.loads(OUT.read_text(encoding="utf-8"))
    setting = tuple(result["settings"][result["release_candidate"]])
    hb._init()
    ds = hb._G["ds"]
    res = fit(ds, setting)
    idx, _ = _anchor_index(ds)
    used = _used(_anchors())
    slope, icept = _cf_map(res["b"][idx], _anchors())
    rows = np.bincount(ds.contest_of_row, minlength=len(ds.contests))[ds.contest_of_problem]
    records = [{"problem_id": pid, "problem_label": label, "problem_name": pname, "contest_id": int(cid),
                "difficulty": round(float(res["b"][p]), 1), "difficulty_se": round(float(res["b_se"][p]), 1),
                "solved_count": int(ds.solved_count[p]), "reported_solved_in_contest": int(ds.raw_solved_count[p]),
                "difficulty_cf": round(float(np.clip(slope * res["b"][p] + icept, elo.LO, elo.HI)), 1),
                "difficulty_cf_se": round(float(slope * res["b_se"][p]), 1),
                "board_rows": int(rows[p]), "small_board": bool(rows[p] < SMALL_BOARD_ROWS)}
               for p, (cid, label, pid, pname) in enumerate(ds.problems)]
    meta = {"research_only": True, "method": "hierarchical binary Rasch with solve-time slices (hier_time_report.md)",
            "setting": {**KW, "bins": setting[0], "time_weight": setting[1], "skip_partial": setting[2]},
            "thresholds": res["d"].tolist(), "map": {"slope": float(slope), "intercept": float(icept)},
            "map_scope": "problems and teams: a team rated R solves a problem rated R half the time",
            "anchors": len(used), "anchor_contests": len({a["cf_contest"] for a in _anchors()}),
            "anchors_left_out": sorted(map(list, WRONG_ANCHORS)),
            "display": [elo.LO, elo.HI, "rounded to 0.1"],
            "uncertainty": "difficulty_se / difficulty_cf_se: the teams held fixed; no map or board-level error",
            "small_board": f"board_rows < {SMALL_BOARD_ROWS}: rated from a handful of rows",
            "inputs_sha256": result["sha256"]}
    RELEASE.write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
    RELEASE_META.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {RELEASE}: {len(records)} problems, setting {name(setting)}, map {slope:.3f} b {icept:+.0f}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if command == "select":
        print(json.dumps(select(workers)[1], indent=1))
    elif command == "evaluate":
        evaluate(workers)
    elif command == "release":
        release()
    else:
        sys.exit(__doc__)
