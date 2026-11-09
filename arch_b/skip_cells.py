"""Skipped cells as missing data in the hierarchical binary fit. See skip_cells_report.md.

The hand audit (problem_rating_audit.md) found EC sign-in problems rated far too
hard: their only "failures" are mirror accounts that never submitted to them.
A cell is *skipped* when, within the cells being fitted, the row made no
submission to the problem (not solved, 0 wrong attempts) and more of the board
solved that problem than solved the row's own hardest solved problem.

Rules, frozen before any result of this module was seen:
- ``base``: every cell counts (the selected hier_binary fit);
- ``skip_all``: skipped cells are missing in every row (the audit's diagnostic);
- ``skip_partial``: skipped cells are missing only in rows that submitted to at
  most PARTIAL_MAX problems (partial participants such as mirror accounts);
- ``skip_mirror`` (added 2026-11-09, after the first run): ``skip_partial`` but
  only in rows that are not official registrations (``official_of_row``).

The hier_binary setting (sigma 300, tau 800, sigma_b 600, tau_b 400) is held
fixed; nothing is reselected. Skip status is always recomputed from the cells a
fit may use (training appearances, or a stability view's active rows).

Primary team metric: held-out appearances scored on their non-skipped cells
(skip defined on the full board, the same cells for every rule); all cells are
reported too. The recorded-date forward replay is not run: its panel
(member_forecast.training_data) carries no attempt counts.

    python -m arch_b.skip_cells [JOBS]   -> output/skip_cells.json
"""

import gzip
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from arch_a import elo
from . import hier_binary as hb

CFG = (300, 800, 600, 400)
RULES = ("base", "skip_all", "skip_partial", "skip_mirror")
PARTIAL_MAX = 2
OUT = hb.ROOT / "output/skip_cells.json"


def skipped(ds, cells, rule):
    """Observation mask of skipped cells under ``rule``, using only ``cells``."""
    out = np.zeros(len(ds.obs_y), bool)
    if rule == "base":
        return out
    idx = np.flatnonzero(cells)
    row, prob, y = ds.obs_row[idx], ds.obs_prob[idx], ds.obs_y[idx]
    tried = y | (ds.obs_wrong[idx] > 0)
    solved = np.bincount(prob[y], minlength=len(ds.problems)).astype(float)
    hardest = np.full(len(ds.team_of_row), np.inf)
    np.minimum.at(hardest, row[y], solved[prob[y]])
    skip = ~tried & (solved[prob] > hardest[row])
    if rule in ("skip_partial", "skip_mirror"):
        skip &= np.bincount(row[tried], minlength=len(ds.team_of_row))[row] <= PARTIAL_MAX
    if rule == "skip_mirror":
        skip &= ~ds.official_of_row[row]
    out[idx[skip]] = True
    return out


def _fit(ds, keep, rows=None):
    team = ds.team_of_row[ds.obs_row]
    return hb.fit(ds, obs=(team[keep], ds.obs_prob[keep], ds.obs_y[keep].astype(float)), rows=rows,
                  **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), CFG)))


def _team_job(job):
    split, rule = job
    ds = hb._G["ds"]
    held = hb.appearance_split(ds, split)
    train = ~held[ds.obs_row]
    res = _fit(ds, train & ~skipped(ds, train, rule))
    board_skip = skipped(ds, np.ones(len(ds.obs_y), bool), "skip_all")
    return job, {"all": hb.team_scores(ds, held, res["theta"], res["b"], "binary"),
                 "non_skipped": hb.team_scores(ds, held, res["theta"], res["b"], "binary", ~board_skip)}


def team_experiment(jobs):
    def compute():
        out = {}
        with ProcessPoolExecutor(jobs, initializer=hb._init) as ex:
            for (split, rule), sc in ex.map(_team_job, [(s, r) for s in hb.REPORT_SPLITS for r in RULES]):
                out[f"{split}:{rule}"] = {k: {m: v.tolist() for m, v in s.items()} for k, s in sc.items()}
                print(f"team split {split} {rule} done", flush=True)
        return out
    raw = hb._cached("skip_team_" + "_".join(RULES), compute)
    out = {}
    for split in hb.REPORT_SPLITS:
        out[str(split)] = {}
        for subset in ("non_skipped", "all"):
            sc = {r: hb._np(raw[f"{split}:{r}"][subset]) for r in RULES}
            out[str(split)][subset] = {"summary": {r: hb.summarize(v) for r, v in sc.items()},
                                       **{f"{r}_minus_base": hb.paired_bootstrap(sc[r], sc["base"])
                                          for r in RULES[1:]}}
    return out


def _view_job(view):
    """One de_stability view: the skip rules' anchor b and kept-team theta (base comes from cache)."""
    from . import de_stability_data as dsd, model
    ds, anchors, boards, ctx = hb._G["view_state"]
    team, prob, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    excluded = np.array([], int)
    selector = eligible = None
    if view in ("strength_pool", "strong", "weak"):   # same selection as hier_binary._view_job
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
    pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(r["contest_id"], r["problem_label"])] for r in anchors])
    kept_teams = np.unique(ds.team_of_row[rows])
    fits = {}
    for rule in RULES[1:]:
        res = _fit(ds, cells & ~skipped(ds, cells, rule), rows=active)
        fits[rule] = {"b": res["b"][idx].tolist(), "theta": res["theta"][kept_teams].tolist()}
    return view, {"kept_anchor_rows": rows.tolist(), "kept_teams": kept_teams.tolist(), "fits": fits}


def view_experiment(jobs):
    from .de_stability_data import VIEWS
    path = hb.RUN / ("views_" + hb.config_name(CFG) + "_hb_s400_t0_sb400_tb200.json.gz")
    if not path.exists():
        raise RuntimeError("run python -m arch_b.hier_binary all first (base view fits)")
    cached = json.loads(gzip.decompress(path.read_bytes()))

    def compute():
        out = {}
        with ProcessPoolExecutor(jobs, initializer=hb._view_init) as ex:
            for view, rec in ex.map(_view_job, VIEWS):
                out[view] = rec
                print(f"view {view} done", flush=True)
        return out
    new = hb._cached("skip_views_" + "_".join(RULES), compute)
    views = {}
    for v, rec in cached.items():
        assert new[v]["kept_anchor_rows"] == rec["kept_anchor_rows"], v
        fits = {"survival": rec["fits"]["survival"], "binary": rec["fits"]["binary"], "base": rec["fits"]["hb"]}
        fits.update(new[v]["fits"])
        views[v] = {**rec, "fits": fits}
    card = hb.stability_scorecard(views, {r: CFG for r in RULES})
    from .de_release_audit import contest_bootstrap
    for v, rows in card["predictions"].items():
        for r in RULES[1:]:
            card["scorecard"][v][r]["rmse_minus_base"] = contest_bootstrap(
                rows, np.array([x[r] for x in rows]), np.array([x["base"] for x in rows]), n=hb.BOOT)
    return card


def full_data(jobs_unused=None):
    """Full-data fits: hand panel, EC solve-rate buckets, anchors, CF-rated teams."""
    from scripts.problem_rating_audit import HAND, hand_scores
    from .calibrate import problem_cf
    from .cf_prior import team_abilities
    hb._init()
    ds, uf = hb._G["ds"], hb._G["uf"]
    anchors = json.loads((hb.ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    pi = {(cid, lab): p for p, (cid, lab, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors])
    cf = np.array([a["cf"] for a in anchors])
    shipped = problem_cf(ds.problems)
    de = np.array([shipped[(int(c), lab)] for c, lab, _, _ in ds.problems])
    index = {tk: i for i, tk in enumerate(ds.teams)}
    pairs = [(index[tk], v[0]) for tk, v in team_abilities(uf).items() if tk in index]
    ti, target = np.array([i for i, _ in pairs]), np.array([c for _, c in pairs])
    every = np.ones(len(ds.obs_y), bool)
    ratings, out = {"de": de}, {"skipped_cells": {}, "maps": {}, "external_cf_teams": {}}
    for rule in RULES:
        skip = skipped(ds, every, rule)
        res = _fit(ds, ~skip)
        s, i = np.polyfit(res["b"][idx], cf, 1)
        ratings[rule] = np.clip(s * res["b"] + i, elo.LO, elo.HI)
        out["skipped_cells"][rule] = {"cells": int(skip.sum()), "rows": int(len(np.unique(ds.obs_row[skip])))}
        out["maps"][rule] = [float(s), float(i)]
        err = s * res["theta"][ti] + i - target
        out["external_cf_teams"][rule] = {"teams": len(err), "rmse": float(np.sqrt(np.mean(err ** 2))),
                                          "mean_error": float(err.mean())}
    out["hand_scores"] = hand_scores(pi, ratings)
    rate = ds.solved_count / np.maximum(ds.field_count, 1)
    bins = [(0, .005), (.005, .05), (.05, .3), (.3, .7), (.7, .95), (.95, 1.01)]
    ec = np.array([cid in _ec_contests() for cid, _, _, _ in ds.problems])
    out["ec_minus_de_by_solve_rate"] = {
        rule: {f"{lo}-{hi}": float(np.mean((ratings[rule] - de)[ec & (rate >= lo) & (rate < hi)]))
               for lo, hi in bins} for rule in RULES}
    out["hand"] = [{"contest_id": c, "label": lab, "hand": h, "group": g,
                    **{n: round(float(r[pi[(c, lab)]]), 1) for n, r in ratings.items()}}
                   for (c, lab), (h, g, _) in HAND.items()]
    return out


def _ec_contests():
    raw = json.loads((hb.ROOT / "output/hier_binary.json").read_text(encoding="utf-8"))
    return {c["contest_id"] for c in raw["versus_shipped_de"]["contests"]
            if c["region"] == "Asia East Continent"}


def main(jobs):
    out = {"research_only": True, "config": list(CFG), "rules": list(RULES), "partial_max": PARTIAL_MAX,
           "sha256": {**hb.sha256s(), **{p: hashlib.sha256((hb.ROOT / p).read_bytes()).hexdigest()
                                         for p in ("arch_b/skip_cells.py", "scripts/problem_rating_audit.py")}}}
    out["full_data"] = full_data()
    print(json.dumps(out["full_data"]["hand_scores"]["all"]), flush=True)
    out["team_prediction"] = team_experiment(jobs)
    card = view_experiment(jobs)
    out["field_stability"] = {k: card[k] for k in ("scorecard", "map_slopes", "team_theta_drift")}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
