"""Calibrate the relative difficulty scale to Codeforces-equivalent points.

Our difficulties live on a relative scale pinned at the arbitrary anchor MU0=2000
(no member-CF ratings exist; see the anchoring decision in details.md), and the CF
checks showed the scale is *compressed* — correctly ranked but on a narrower span
than Codeforces, more so in the hard tail. The map to CF points is therefore built
in two legs:

1. **Shape** (nonlinear, gym-learned): a monotone quantile map ``f`` fit on the
   ~660 problems the CF gym-mirror yardstick covers (``output/gym_difficulty.json``
   — certified nearly CF-native in scale, see details.md), shrunk toward its own
   linear approximation by ``ALPHA``. The gym population is authoritative on
   *scale* but noisier than our fit at *ranking*; a monotone map consumes only the
   scale and cannot reorder our problems. qoj 2692 (the one gym contest that is
   also a CF anchor contest) is excluded, so the shape shares no problems with the
   anchors that score it.
2. **Scale** (affine): ``cf ≈ A·f(b) + B`` fit on the official CF problemset
   ratings of every rated mirror in ``data/cf_team_contests.txt``, auto-mapped by
   problem-name vote (the ``external_validate`` machinery) — currently 185 anchor
   problems / 15 contests, superseding the 3 hardcoded contests this module
   originally used.

Validated **leave-one-contest-out** (fit the affine on 14 contests, predict the
held-out one; the shape never sees anchor problems, so it is leak-free per fold):
shaped LOCO-RMSE **266** vs plain-affine **288** (bootstrap CI of the difference
[-44, -3], P(worse) ≈ 1%; improvement in 10/15 contests, and the cf≥3200 tail
improves 477 → 434). A curved map fit on the CF anchors *alone* scores worse than
affine (297), so the gain is the gym information, not map flexibility. If the gym
file is missing the module falls back to the plain affine map.

    python -m arch_b.calibrate            # report all models; calibrate survival
    python -m arch_b.calibrate --binary   # calibrate the binary model instead

Writes output/problem_ratings_calibrated.json: every record gains
``difficulty_cf`` (clipped to [800, 4000]) and ``difficulty_cf_se``
(= difficulty_se scaled by the local slope of the composed map).
"""

import contextlib
import io
import json
import os
import sys
from collections import defaultdict

import numpy as np

from arch_a import elo
from .external_validate import GYM_OUT, _cf_mapping, _cf_problemset, _norm

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")

NBINS = 15    # quantile bins of the gym shape
ALPHA = 0.75  # shape shrinkage toward its own linear approximation
EXCLUDE_QOJ = {2692}  # gym contests that are also CF anchor contests

MODELS = [("arch A", "problem_ratings.json"),
          ("arch B binary", "problem_ratings_b.json"),
          ("arch B survival", "problem_ratings_survival.json")]


def _anchors(records):
    """Auto-mapped CF anchors: (our difficulty, cf rating, contest group).

    Same problem-name-vote join as ``metric.py`` / ``external_validate``, over
    every rated CF mirror in ``data/cf_team_contests.txt``.
    """
    by_name = {(r["contest_id"], _norm(r["problem_name"])): r["difficulty"]
               for r in records}
    contests_like = defaultdict(list)
    for r in records:
        contests_like[r["contest_id"]].append({"problem_label": r["problem_label"],
                                               "problem_name": r["problem_name"]})
    contests_like = [{"contest_id": cid, "problems": ps}
                     for cid, ps in contests_like.items()]
    rating = _cf_problemset()
    with contextlib.redirect_stdout(io.StringIO()):   # silence the mapping table
        mapping = _cf_mapping(contests_like, defaultdict(lambda: "?"), rating)
    our, cf, grp = [], [], []
    for cfid, qoj, _reg, matched in mapping:
        for nm in matched:
            if (qoj, nm) in by_name:
                our.append(by_name[(qoj, nm)])
                cf.append(rating[(cfid, nm)])
                grp.append(cfid)
    return np.array(our, float), np.array(cf, float), np.array(grp, int)


def _gym_shape(records):
    """The gym-learned monotone shape f (with ALPHA shrinkage), or None.

    Fit on (our difficulty, b_gym) pairs joined by (contest_id, problem_label),
    excluding EXCLUDE_QOJ. Returns a vectorized callable.
    """
    if not os.path.exists(GYM_OUT):
        return None
    by_label = {(r["contest_id"], r["problem_label"]): r["difficulty"]
                for r in records}
    x, y = [], []
    for g in json.load(open(GYM_OUT)):
        if g["contest_id"] in EXCLUDE_QOJ:
            continue
        d = by_label.get((g["contest_id"], g["problem_label"]))
        if d is not None:
            x.append(d)
            y.append(g["difficulty"])
    if len(x) < 10 * NBINS:
        return None
    x, y = np.array(x, float), np.array(y, float)
    o = np.argsort(x)
    xs, ys = x[o], y[o]
    edges = np.linspace(0, len(xs), NBINS + 1).astype(int)
    bx = np.array([np.median(xs[a:c]) for a, c in zip(edges[:-1], edges[1:])])
    by = np.array([np.median(ys[a:c]) for a, c in zip(edges[:-1], edges[1:])])
    by = np.maximum.accumulate(by)                     # enforce monotone
    lin = np.polyfit(x, np.interp(x, bx, by), 1)       # shrinkage target

    def f(t):
        t = np.asarray(t, float)
        lo_s = (by[1] - by[0]) / max(bx[1] - bx[0], 1e-9)
        hi_s = (by[-1] - by[-2]) / max(bx[-1] - bx[-2], 1e-9)
        q = np.interp(t, bx, by)
        q = np.where(t < bx[0], by[0] + lo_s * (t - bx[0]), q)
        q = np.where(t > bx[-1], by[-1] + hi_s * (t - bx[-1]), q)
        return ALPHA * q + (1 - ALPHA) * np.polyval(lin, t)

    return f


def _spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _loco_rmse(z, cf, grp):
    errs = []
    for g in np.unique(grp):
        tr, te = grp != g, grp == g
        s, i = np.polyfit(z[tr], cf[tr], 1)
        errs.append(s * z[te] + i - cf[te])
    return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))


def _report(name, our, cf, grp, shape):
    """Print affine vs shaped LOCO; return the final affine leg (A, B)."""
    z = shape(our) if shape else our
    slope, intercept = np.polyfit(z, cf, 1)
    fit_rmse = float(np.sqrt(np.mean((slope * z + intercept - cf) ** 2)))
    loco_aff = _loco_rmse(our, cf, grp)
    loco_shp = _loco_rmse(z, cf, grp) if shape else loco_aff
    print(f"{name:16} Spearman={_spearman(our, cf):+.3f}  "
          f"LOCO affine={loco_aff:3.0f}  shaped={loco_shp:3.0f}  "
          f"(fit-RMSE {fit_rmse:3.0f}, n={len(our)}/{len(np.unique(grp))} contests)")
    return slope, intercept


def main(use_binary=False):
    pick = None
    for name, fname in MODELS:
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            continue
        records = json.load(open(path))
        our, cf, grp = _anchors(records)
        shape = _gym_shape(records)
        slope, intercept = _report(name, our, cf, grp, shape)
        chosen = (name == "arch B binary") if use_binary else (name == "arch B survival")
        if chosen:
            pick = (name, records, shape, slope, intercept)

    name, records, shape, slope, intercept = pick
    if shape is None:
        print("(gym_difficulty.json unavailable — plain affine map)")
        shape = lambda t: np.asarray(t, float)
    for r in records:
        d = float(r["difficulty"])
        r["difficulty_cf"] = round(float(np.clip(
            slope * shape(np.array([d]))[0] + intercept, elo.LO, elo.HI)), 1)
        if "difficulty_se" in r:
            # local slope of the composed map via central difference
            h = 10.0
            dz = (shape(np.array([d + h]))[0] - shape(np.array([d - h]))[0]) / (2 * h)
            r["difficulty_cf_se"] = round(float(abs(slope * dz) * r["difficulty_se"]), 1)
    out = os.path.join(OUT, "problem_ratings_calibrated.json")
    with open(out, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\ncalibrated {name} (cf = {slope:.2f}*f(b) {intercept:+.0f}) "
          f"-> {os.path.normpath(out)}")


if __name__ == "__main__":
    main(use_binary="--binary" in sys.argv)
