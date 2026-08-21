"""The north-star metric: calibrated leave-one-contest-out RMSE in CF points.

One command, one scalar. Refits the survival model **from source** (so any code
or hyperparameter change is picked up), joins the fitted difficulties to the
official CF problemset ratings of every mirrored contest in
``data/cf_team_contests.txt`` (auto-mapped by problem-name vote, same machinery
as ``external_validate``), applies the locked gym-learned monotone shape from
``calibrate.py``, and scores leave-one-contest-out: for each anchor contest, fit
the affine leg on the *other* contests and predict the held-out one. Pooled RMSE
over all anchor problems, in CF points.

Why this metric (see details.md): it measures the shipped deliverable
(``difficulty_cf``) directly, in interpretable units; it is sensitive to both
ranking *and* scale (Spearman is blind to compression); and LOCO punishes
overfitting the anchor set. The shape is locked at NBINS=15, ALPHA=0.75, with
qoj 2692 excluded; auto-research may improve the fit but not tune calibration
against the same anchor set. Lower is better.

Guards. The CF anchors cover only Asia Pacific / Northern Eurasia / Europe, so
optimizing the metric alone could silently regress the unanchored regions or
break basic sanity. The same fit is therefore also checked against fixed
floors (baseline minus a noise margin); any violation exits nonzero, which an
auto-research loop must treat as "discard the change":

  * gym EC Spearman        -- Asia East Continent vs the gym-mirror yardstick
                              (``output/gym_difficulty.json``): the region with
                              no CF anchors at all.
  * gym pooled Spearman    -- all gym-covered problems.
  * Kattis pooled Spearman -- North America + Europe practice-population check.
  * AOJ within Spearman    -- Japan regionals, ranked within each contest to
                              remove unequal practice exposure.
  * solve-count sanity     -- per-contest median Spearman(difficulty,
                              solve_count) must stay strongly negative.
  * raw affine LOCO        -- the unshaped fit must not regress by more than
                              the 5-point keep threshold.

The last line on stdout is always
``METRIC calibrated_loco_cf_rmse=<value>``.

    python -m arch_b.metric            # survival model (the shipped one)
    python -m arch_b.metric --binary   # score the binary Rasch fit instead
"""

import contextlib
import io
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

from . import model, survival
from .aoj import load_matches as load_aoj_matches, within_contest_spearman
from .joint import estimate_joint
from .calibrate import _gym_shape
from .external_validate import GYM_OUT, KATTIS, _cf_mapping, _cf_problemset, _norm
from .run import MIN_SOLVE_HOURS

# Guard floors: current baseline minus a noise margin (~0.02-0.04). A change
# that pushes any of these below its floor is discarded regardless of the metric.
GUARDS = {
    "gym_ec_spearman": 0.93,        # baseline +0.977
    "gym_pooled_spearman": 0.92,    # baseline +0.969
    "kattis_pooled_spearman": 0.75, # baseline +0.772
    "aoj_within_spearman": 0.52,    # baseline +0.568
    "solvecount_sanity": 0.90,      # baseline +0.995 (sign flipped: -median)
}
RAW_LOCO_CEILING = 293.4  # baseline 288.4 + the 5-point keep threshold


def _spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    return float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])


def loco_rmse(our, cf, grp):
    """Leave-one-contest-out affine-calibrated RMSE (CF points)."""
    our, cf, grp = np.asarray(our, float), np.asarray(cf, float), np.asarray(grp)
    errs = []
    for g in np.unique(grp):
        tr, te = grp != g, grp == g
        slope, icept = np.polyfit(our[tr], cf[tr], 1)
        errs.append(slope * our[te] + icept - cf[te])
    return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))


def main(use_binary=False):
    t0 = time.time()
    mod = model if use_binary else survival
    with contextlib.redirect_stdout(io.StringIO()):   # silence the fit trace
        ds, theta, b, history, _ = estimate_joint(
            fit_fn=mod.fit, min_solve_hours=MIN_SOLVE_HOURS)

    # Fitted difficulties keyed both ways the yardsticks join.
    by_label = {(int(cid), label): float(b[p])
                for p, (cid, label, pid, name) in enumerate(ds.problems)}
    by_name = {(int(cid), _norm(name)): float(b[p])
               for p, (cid, label, pid, name) in enumerate(ds.problems)}

    # --- the metric: LOCO CF-point RMSE over all mapped rated mirrors ---
    contests_like = defaultdict(list)
    for cid, label, pid, name in ds.problems:
        contests_like[int(cid)].append({"problem_label": label, "problem_name": name})
    contests_like = [{"contest_id": cid, "problems": ps}
                     for cid, ps in contests_like.items()]
    region_of = defaultdict(lambda: "?")
    rating = _cf_problemset()
    with contextlib.redirect_stdout(io.StringIO()):   # silence the mapping table
        mapping = _cf_mapping(contests_like, region_of, rating)
    our, cf, grp = [], [], []
    for cfid, qoj, _reg, matched in mapping:
        for nm in matched:
            if (qoj, nm) in by_name:
                our.append(by_name[(qoj, nm)])
                cf.append(rating[(cfid, nm)])
                grp.append(cfid)
    raw_rmse = loco_rmse(our, cf, grp)
    records = [{"contest_id": int(cid), "problem_label": label,
                "difficulty": float(b[p])}
               for p, (cid, label, _pid, _name) in enumerate(ds.problems)]
    shape = _gym_shape(records)
    if shape is None:
        raise RuntimeError("locked gym calibration shape is unavailable")
    calibrated_rmse = loco_rmse(shape(np.asarray(our, float)), cf, grp)

    # --- guards, from the same fit ---
    gym = json.load(open(GYM_OUT))
    gy_all, gy_ec = [], []
    for r in gym:
        k = (r["contest_id"], r["problem_label"])
        if k in by_label:
            pair = (by_label[k], r["difficulty"])
            gy_all.append(pair)
            if r["region"] == "Asia East Continent":
                gy_ec.append(pair)
    kat = {_norm(v["name"]): v["difficulty"]
           for v in json.load(open(KATTIS)).values()}
    # Same convention as external_validate's "Kat pld": North America + Europe,
    # the two regions Kattis genuinely covers (elsewhere it is stragglers and
    # title collisions).
    tagged = json.load(open(os.path.join(os.path.dirname(GYM_OUT),
                                         os.pardir, "data", "tagged.json")))
    kat_region = {c["contest_id"]: c["region"] for c in tagged
                  if c["region"] in ("North America", "Europe")}
    ka = [(d, kat[nm]) for (cid, nm), d in by_name.items()
          if nm in kat and cid in kat_region]
    aoj = load_aoj_matches()
    ao = [(cid, d, aoj[(cid, label)]) for (cid, label), d in by_label.items()
          if (cid, label) in aoj]

    per_contest = defaultdict(list)
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        ci = int(ds.contest_of_problem[p])
        per_contest[ci].append((float(b[p]), int(ds.solved_count[p])))
    sanity = [-s for v in per_contest.values() if len(v) >= 3
              for s in [_spearman([d for d, _ in v], [c for _, c in v])]
              if not np.isnan(s)]

    guards = {
        "gym_ec_spearman": _spearman([a for a, _ in gy_ec], [g for _, g in gy_ec]),
        "gym_pooled_spearman": _spearman([a for a, _ in gy_all], [g for _, g in gy_all]),
        "kattis_pooled_spearman": _spearman([a for a, _ in ka], [k for _, k in ka]),
        "aoj_within_spearman": within_contest_spearman(ao),
        "solvecount_sanity": float(np.median(sanity)),
    }

    fail = [name for name, floor in GUARDS.items() if guards[name] < floor]
    raw_fail = raw_rmse > RAW_LOCO_CEILING
    print(f"model={'binary' if use_binary else 'survival'}  "
          f"anchors: {len(our)} problems / {len(set(grp))} contests  "
          f"({time.time() - t0:.0f}s)")
    for name, floor in GUARDS.items():
        mark = "FAIL" if name in fail else "ok"
        print(f"GUARD {name}={guards[name]:+.3f} (floor {floor:+.2f}) {mark}")
    print(f"GUARD raw_loco_cf_rmse={raw_rmse:.1f} "
          f"(ceiling {RAW_LOCO_CEILING:.1f}) {'FAIL' if raw_fail else 'ok'}")
    print(f"METRIC calibrated_loco_cf_rmse={calibrated_rmse:.1f}")
    if fail or raw_fail:
        sys.exit(1)


if __name__ == "__main__":
    main(use_binary="--binary" in sys.argv[1:])
