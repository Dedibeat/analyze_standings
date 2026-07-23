"""Run Architecture B end to end and write problem ratings.

    python -m arch_b.run              # binary Rasch model (strat.tex section 4)
    python -m arch_b.run --survival   # solve-time survival model (section 5)

Produces output/problem_ratings_b.json (or output/problem_ratings_survival.json
with --survival): one record per problem with its MAP-estimated difficulty b_p on
the Codeforces-like [800, 4000] scale. Written to a distinct file so Architecture
A's output/problem_ratings.json is left untouched.
"""

import json
import os
import sys

import numpy as np

from . import model, survival
from .anchor import estimate_anchored

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")

# Drop short-format contests (warm-ups, 3 h rounds) whose latest solve is below
# this many hours -- a duration proxy (no duration field exists). Validated
# metric-neutral vs CF/LLM in arch_b.season_experiment while removing noise.
MIN_SOLVE_HOURS = 3.5


def _spearman(x, y):
    """Spearman rank correlation (no scipy dependency)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return np.nan
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def main(use_survival=False):
    mod = survival if use_survival else model
    out_name = "problem_ratings_survival.json" if use_survival else "problem_ratings_b.json"

    ds, theta, b, history, _ = estimate_anchored(fit_fn=mod.fit, min_solve_hours=MIN_SOLVE_HOURS)
    _, se_b = mod.laplace_se(ds, theta, b)  # Laplace posterior SE per difficulty

    records = []
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        ci = ds.contest_of_problem[p]
        rows = np.where(ds.contest_of_row == ci)[0]
        solved = int(np.sum(ds.y[rows, p] & ds.solve_mask[rows, p]))
        records.append({
            "problem_id": pid,
            "problem_label": label,
            "problem_name": name,
            "contest_id": int(cid),
            "difficulty": round(float(b[p]), 1),
            "difficulty_se": round(float(se_b[p]), 1),
            "solved_count": solved,
            "reported_solved_in_contest": int(ds.raw_solved_count[p]),
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, out_name)
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    _verify(ds, theta, b, records)
    print(f"wrote {len(records)} problem ratings to {os.path.normpath(out_path)}")


def _verify(ds, theta, b, records):
    print("=== verification ===")
    print(f"theta: [{theta.min():.0f}, {theta.max():.0f}] mean {theta.mean():.0f}")
    print(f"b:     [{b.min():.0f}, {b.max():.0f}] mean {b.mean():.0f}")
    se = np.array([r["difficulty_se"] for r in records])
    print(f"b SE:  [{se.min():.0f}, {se.max():.0f}] median {np.median(se):.0f} "
          f"(Laplace; high SE = few/all solvers, relaxes to prior sd)")

    # 1) Within each contest, harder problems (lower solve count) should rate
    # higher -> negative Spearman between difficulty and solve count.
    corrs = []
    for ci in range(len(ds.contests)):
        ps = [i for i in range(len(ds.problems)) if ds.contest_of_problem[i] == ci]
        if len(ps) < 3:
            continue
        diff = [b[i] for i in ps]
        cnt = [records[i]["solved_count"] for i in ps]
        rho = _spearman(diff, cnt)
        if not np.isnan(rho):
            corrs.append(rho)
    med = float(np.median(corrs))
    print(f"per-contest Spearman(difficulty, solve_count): median {med:+.3f} "
          f"over {len(corrs)} contests (expect strongly negative)")
    assert med < -0.5, med

    # 2) Strong recurring teams should land high. Report the top by appearances.
    counts = np.zeros(len(ds.teams), dtype=int)
    np.add.at(counts, ds.team_of_row, 1)
    top = np.argsort(counts)[::-1][:5]
    print("most-recurring teams (appearances, theta):")
    for ti in top:
        print(f"  {ds.teams[ti]:<24} n={counts[ti]:3d}  theta={theta[ti]:.0f}")

    print("verification passed")


if __name__ == "__main__":
    main(use_survival="--survival" in sys.argv)
