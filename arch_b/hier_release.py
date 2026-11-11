"""Release candidate: hierarchical binary ratings in the shipped record format.

One full-data ``hier_binary.fit`` at the frozen setting (sigma 300, tau 800,
sigma_b 600, tau_b 400) with the ``skip_partial`` data rule and the row-level
team prior (``row_prior``; both in skip_cells_report.md), put on the CF scale by one affine map fitted on the 185 CF anchors. The same
map rates problems and teams: a team rated R solves a problem rated R half the
time.

    python -m arch_b.hier_release

Writes
- output/problem_ratings_hier.json: one record per problem with the fields of
  output/problem_ratings_calibrated.json (``difficulty`` is the latent b,
  ``difficulty_cf`` the CF rating clipped to [800, 4000]; no ``difficulty_se``),
  plus ``field_count`` (cells fitted) and ``skipped_cells``;
- output/team_ratings_hier.json: one record per resolved team;
- output/hier_release.json: setting, map, anchor accuracy, checks, input hashes.

It does not replace the shipped DE ratings: consumers still read
``calibrate.problem_cf``. See "Release candidate" in hier_binary_report.md.
"""

import hashlib
import json
from collections import Counter

import numpy as np

from arch_a import elo
from . import hier_binary as hb
from .calibrate import SMALL_BOARD_ROWS
from .skip_cells import CFG, PARTIAL_MAX, skipped

RULE = "skip_partial"
OUT = hb.ROOT / "output"
INPUTS = ("arch_b/hier_release.py", "arch_b/hier_binary.py", "arch_b/skip_cells.py", "arch_a/load.py",
          "arch_b/joint.py", "data/de_stability_anchors.json", "data/tagged.json")
# A board mean far from its own teams is a regression coefficient, not a level
# (hier_binary_report.md, update 2026-11-10). A team seen only there would get
# that mean as its prior, so the release refuses to rate such a team. The
# row-level prior exists to pass this check: without it the largest gap is 753.
MU_GAP = 600.0


def release_fit(ds):
    """The release fit: ``(fit result, skipped-cell mask)``."""
    skip = skipped(ds, np.ones(len(ds.obs_y), bool), RULE)
    team = ds.team_of_row[ds.obs_row]
    res = hb.fit(ds, obs=(team[~skip], ds.obs_prob[~skip], ds.obs_y[~skip].astype(float)),
                 row_prior=True, **dict(zip(("sigma", "tau", "sigma_b", "tau_b"), CFG)))
    return res, skip


def cf_map(b, anchors, index):
    """Affine CF map on the anchors and its accuracy (fit and leave-one-contest-out)."""
    from .calibration_ablation import _purged_train
    x = np.array([b[index[(a["contest_id"], a["problem_label"])]] for a in anchors])
    cf = np.array([a["cf"] for a in anchors])
    slope, icept = np.polyfit(x, cf, 1)
    err = np.zeros(len(anchors))
    for c in sorted({a["cf_contest"] for a in anchors}):
        held = [i for i, a in enumerate(anchors) if a["cf_contest"] == c]
        keep = {r["row_id"] for r in _purged_train(anchors, [anchors[i] for i in held])}
        train = [i for i, a in enumerate(anchors) if a["row_id"] in keep]
        err[held] = np.polyval(np.polyfit(x[train], cf[train], 1), x[held]) - cf[held]
    return float(slope), float(icept), {
        "anchors": len(anchors), "contests": len({a["cf_contest"] for a in anchors}),
        "fit_rmse": float(np.sqrt(np.mean((slope * x + icept - cf) ** 2))),
        "loco_rmse": float(np.sqrt(np.mean(err ** 2))), "loco_mean_error": float(err.mean())}


def one_off_prior_gaps(ds, res):
    """|board mean - median ability of the board's rows| for teams seen on one board only."""
    rows = np.bincount(ds.team_of_row, minlength=len(ds.teams))
    median = np.array([np.median(res["theta"][ds.team_of_row[ds.contest_of_row == c]])
                       if np.any(ds.contest_of_row == c) else res["mu"][c] for c in range(len(ds.contests))])
    single = rows[ds.team_of_row] == 1
    return np.abs(res["mu"] - median)[ds.contest_of_row[single]]


def problem_records(ds, res, skip, slope, icept):
    board_rows = np.bincount(ds.contest_of_row, minlength=len(ds.contests))[ds.contest_of_problem]
    skipped_cells = np.bincount(ds.obs_prob[skip], minlength=len(ds.problems))
    cf = np.clip(slope * res["b"] + icept, elo.LO, elo.HI)
    return [{"problem_id": pid, "problem_label": label, "problem_name": name, "contest_id": int(cid),
             "difficulty": round(float(res["b"][p]), 1), "solved_count": int(ds.solved_count[p]),
             "field_count": int(ds.field_count[p] - skipped_cells[p]), "skipped_cells": int(skipped_cells[p]),
             "reported_solved_in_contest": int(ds.raw_solved_count[p]),
             "difficulty_cf": round(float(cf[p]), 1), "board_rows": int(board_rows[p]),
             "small_board": bool(board_rows[p] < SMALL_BOARD_ROWS)}
            for p, (cid, label, pid, name) in enumerate(ds.problems)]


def team_records(ds, res, slope, icept, raw):
    """One record per team: its most frequent name and affiliation, appearances, CF rating."""
    names = [Counter() for _ in ds.teams]
    for t, (cid, source) in zip(ds.team_of_row, ds.participation_of_row):
        s = raw[cid]["standings"][source]
        names[t][(s.get("team_name") or "", s.get("affiliation") or "")] += 1
    rows = np.bincount(ds.team_of_row, minlength=len(ds.teams))
    cf = slope * res["theta"] + icept
    out = [{"team_name": n.most_common(1)[0][0][0], "affiliation": n.most_common(1)[0][0][1],
            "appearances": int(rows[t]), "rating_cf": round(float(cf[t]), 1)} for t, n in enumerate(names)]
    return sorted(out, key=lambda r: (-r["rating_cf"], r["team_name"]))


def main():
    from .calibrate import problem_cf
    from .context_fit import raw_by_contest
    hb._init()
    ds = hb._G["ds"]
    anchors = json.loads((hb.ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    index = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    res, skip = release_fit(ds)
    slope, icept, accuracy = cf_map(res["b"], anchors, index)
    gaps = one_off_prior_gaps(ds, res)
    if np.any(gaps > MU_GAP):
        raise RuntimeError(f"{int(np.sum(gaps > MU_GAP))} one-board teams sit on a board whose mean is "
                           f"more than {MU_GAP:.0f} from its teams; their ratings would be the prior")
    problems = problem_records(ds, res, skip, slope, icept)
    teams = team_records(ds, res, slope, icept, raw_by_contest())
    shipped = problem_cf(ds.problems)
    diff = np.array([r["difficulty_cf"] - shipped[(r["contest_id"], r["problem_label"])] for r in problems])
    de_eval = json.loads((OUT / "de_stability_evaluation.json").read_text(encoding="utf-8"))
    meta = {"release_candidate": True, "replaces_shipped": False,
            "model": "hierarchical binary Rasch (hier_binary_report.md)",
            "config": {**dict(zip(("sigma", "tau", "sigma_b", "tau_b"), CFG)), "row_prior": True},
            "data_rule": {"name": RULE, "partial_max": PARTIAL_MAX, "skipped_cells": int(skip.sum()),
                          "rows": int(len(np.unique(ds.obs_row[skip])))},
            "map": {"slope": slope, "intercept": icept, "applies_to": "problem difficulty and team ability"},
            "anchor_accuracy": {**accuracy, "shipped_de_loco_rmse": de_eval["scorecard"]["full"]["DE"]["rmse"]},
            "fit": {"newton_steps": res["newton"], "max_last_step": res["max_step"], "nu0": res["nu0"],
                    "rows": len(ds.team_of_row), "teams": len(ds.teams), "contests": len(ds.contests)},
            "problems": {"count": len(problems), "at_floor": sum(r["difficulty_cf"] <= elo.LO for r in problems),
                         "at_ceiling": sum(r["difficulty_cf"] >= elo.HI for r in problems),
                         "small_board": sum(r["small_board"] for r in problems)},
            "versus_shipped_de": {"mean": float(diff.mean()), "sd": float(diff.std()),
                                  "over_300": int(np.sum(np.abs(diff) > 300))},
            "checks": {"largest_one_board_prior_gap": float(gaps.max()), "limit": MU_GAP},
            "display": [elo.LO, elo.HI, "rounded to 0.1; team ratings are not clipped"],
            "uncertainty": "unavailable",
            "small_board": f"board_rows < {SMALL_BOARD_ROWS}: rated from a handful of rows",
            "inputs_sha256": {n: hashlib.sha256((hb.ROOT / n).read_bytes()).hexdigest() for n in INPUTS}}
    (OUT / "problem_ratings_hier.json").write_text(
        json.dumps(problems, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "team_ratings_hier.json").write_text(
        json.dumps(teams, indent=0, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "hier_release.json").write_text(json.dumps(meta, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("map", "anchor_accuracy", "data_rule", "problems",
                                           "versus_shipped_de", "checks")}, indent=1))
    print(f"wrote {len(problems)} problems and {len(teams)} teams to {OUT}")


if __name__ == "__main__":
    main()
