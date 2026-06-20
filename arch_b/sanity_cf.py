"""Sanity-check predicted difficulties against official Codeforces ratings.

The 2026 ICPC Asia Pacific Championship (qoj contest 3747) was mirrored on
Codeforces as contest 2206, and Codeforces assigned each of its 13 problems a
problemset rating (fetched from the CF API, embedded below as the reference). CF
ratings are an authoritative, *numeric*, fully independent difficulty opinion --
the strongest external check available -- so we compare our estimates against them
for every model whose output file is present.

    python -m arch_b.sanity_cf
"""

import json
import os

import numpy as np

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
CONTEST = 3747  # qoj id of the 2026 APAC championship (CF mirror: contest 2206)

# Official Codeforces problemset ratings, contest 2206 (CF API problemset.problems).
CF = {"A": 3500, "B": 2500, "C": 2200, "D": 2600, "E": 2500, "F": 2400, "G": 3100,
      "H": 1800, "I": 2900, "J": 1700, "K": 1300, "L": 3500, "M": 2900}

MODELS = [("arch A", "problem_ratings.json"),
          ("arch B binary", "problem_ratings_b.json"),
          ("arch B survival", "problem_ratings_survival.json")]


def _spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _load(path):
    return {r["problem_label"]: r["difficulty"]
            for r in json.load(open(path)) if r["contest_id"] == CONTEST}


def main():
    labs = sorted(CF)
    cols = []
    for name, fname in MODELS:
        path = os.path.join(OUT, fname)
        if os.path.exists(path):
            cols.append((name, _load(path)))

    head = f"{'lbl':3} {'CF':>5} " + " ".join(f"{n:>15}" for n, _ in cols)
    print(head)
    for l in labs:
        row = f"{l:3} {CF[l]:5d} " + " ".join(f"{d.get(l, float('nan')):15.0f}" for _, d in cols)
        print(row)

    cfv = [CF[l] for l in labs]
    print()
    for name, d in cols:
        pv = [d[l] for l in labs]
        print(f"{name:16} Spearman={_spearman(cfv, pv):+.3f}  "
              f"Pearson={np.corrcoef(cfv, pv)[0, 1]:+.3f}")


if __name__ == "__main__":
    main()
