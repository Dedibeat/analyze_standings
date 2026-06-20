"""Calibrate the relative difficulty scale to Codeforces-equivalent points.

Our difficulties live on a relative scale pinned at the arbitrary anchor MU0=2000
(no member-CF ratings exist; see the anchoring decision in details.md), and the CF
sanity check showed the scale is *compressed* — correctly ranked but on a narrower
span than Codeforces. Where a problem was mirrored on Codeforces we now have a real
numeric anchor, so we fit a single global affine map  cf ≈ slope·b + intercept  and
apply it to every problem, turning the relative scale into approximate CF points.

The anchor set is small (problems from 3 CF-rated contests, ``CF_REF`` below) but
spans CF 800–3500, and the map is validated **leave-one-contest-out**: fit on two
contests, predict the third. For the survival model the CV RMSE (~250) barely
exceeds the in-fit RMSE (~240), i.e. the map generalizes across contests rather
than overfitting them — which is what licenses applying it to the full set.

    python -m arch_b.calibrate            # report all models; calibrate survival
    python -m arch_b.calibrate --binary   # calibrate the binary model instead

Writes output/problem_ratings_calibrated.json: every record gains
``difficulty_cf`` (= clip(slope·difficulty + intercept, 800, 4000)) and a scaled
``difficulty_cf_se`` (= slope·difficulty_se).
"""

import json
import os
import sys

import numpy as np

from arch_a import elo

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")

# Official Codeforces problemset ratings, keyed by our contest id -> {problem_name:
# rating}. Matched to our data by problem name. CF mirror ids in comments.
CF_REF = {
    3747: {  # CF 2206 — 2026 ICPC Asia Pacific Championship
        "Compare Suffixes": 3500, "Subtree Removal Game": 2500, "Upside Down Dijkstra": 2200,
        "Christmas Tree Un-decoration": 2600, "Parallel Sums": 2500, "Minesweeper String": 2400,
        "Extra Transition": 3100, "Growth Factor": 2900, "Reflect Sort": 1800,
        "Worldwide Playlist": 1700, "Time Display Stickers": 1300, "Onion": 3500,
        "Deformed Balance": 2900},
    2785: {  # CF 2181 — 2025 ICPC Northern Eurasia Finals
        "Alphabet City": 1300, "Battle of Arrays": 1400, "Cacti Classification": 3200,
        "Doorway": 2000, "Elevator Against Humanity": 2900, "Fragmented Nim": 1600,
        "Greta's Game": 2400, "Honey Cake": 1200, "Irrigation Interlock": 3500,
        "Jinx or Jackpot": 2300, "Knit the Grid": 3500, "LLM Training": 2800,
        "Medical Parity": 1700},
    2657: {  # CF 2172 — ICPC Taiwan
        "ASCII Art Contest": 800, "Buses": 1800, "Circles Are Far from Each Other": 3100,
        "Divisor Card Game": 3100, "Number Maze": 1200, "Cluster Computing System": 1600,
        "Gene Editor": 3300, "Shuffling Cards with Problem Solver 68!": 2500, "Birthday": 2000,
        "Sliding Tiles": 2300, "Kindergarten Homework": 2100, "Maximum Color Segment": 2300,
        "Maximum Distance To Port": 1300, "New Kingdom": 2800},
}

MODELS = [("arch A", "problem_ratings.json"),
          ("arch B binary", "problem_ratings_b.json"),
          ("arch B survival", "problem_ratings_survival.json")]


def _norm(s):
    return " ".join((s or "").lower().split())


def _anchors(records):
    """Pair our difficulty with the CF rating for every CF-anchored problem.

    Returns (our, cf, group): arrays of our difficulty, the CF rating, and the
    contest id (the CV grouping).
    """
    by_name = {(r["contest_id"], _norm(r["problem_name"])): r["difficulty"] for r in records}
    our, cf, grp = [], [], []
    for cid, names in CF_REF.items():
        for name, rating in names.items():
            d = by_name.get((cid, _norm(name)))
            if d is not None:
                our.append(d); cf.append(rating); grp.append(cid)
    return np.array(our, float), np.array(cf, float), np.array(grp, int)


def _spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _report(name, our, cf, grp):
    slope, intercept = np.polyfit(our, cf, 1)
    pred = slope * our + intercept
    rmse = np.sqrt(np.mean((pred - cf) ** 2))
    cv = []
    for g in np.unique(grp):
        tr, te = grp != g, grp == g
        s, i = np.polyfit(our[tr], cf[tr], 1)
        cv.append(s * our[te] + i - cf[te])
    cv_rmse = np.sqrt(np.mean(np.concatenate(cv) ** 2))
    print(f"{name:16} Spearman={_spearman(our, cf):+.3f}  affine: cf={slope:.2f}*b{intercept:+.0f}  "
          f"fit-RMSE={rmse:3.0f}  LOCO-CV-RMSE={cv_rmse:3.0f}")
    return slope, intercept


def main(use_binary=False):
    for name, fname in MODELS:
        path = os.path.join(OUT, fname)
        if os.path.exists(path):
            our, cf, grp = _anchors(json.load(open(path)))
            slope, intercept = _report(name, our, cf, grp)
            chosen = (name == "arch B binary") if use_binary else (name == "arch B survival")
            if chosen:
                pick = (name, fname, slope, intercept)

    name, fname, slope, intercept = pick
    records = json.load(open(os.path.join(OUT, fname)))
    for r in records:
        r["difficulty_cf"] = round(float(np.clip(slope * r["difficulty"] + intercept, elo.LO, elo.HI)), 1)
        if "difficulty_se" in r:
            r["difficulty_cf_se"] = round(float(slope * r["difficulty_se"]), 1)
    out = os.path.join(OUT, "problem_ratings_calibrated.json")
    with open(out, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\ncalibrated {name} (cf = {slope:.2f}*b {intercept:+.0f}) -> {os.path.normpath(out)}")


if __name__ == "__main__":
    main(use_binary="--binary" in sys.argv)
