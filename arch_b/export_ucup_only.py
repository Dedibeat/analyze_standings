"""Export the Universal Cup contests that never made it into tagged.json.

    python -m arch_b.export_ucup_only

52 UCup rounds (ucup_s3.json + ucup_s4.json) pass MIN_SOLVE_HOURS but are not
among the 146 tagged.json contests, so they're absent from both
output/problem_ratings_calibrated.json (ratings) and canonical/tagged.json in
../my-react-app (the browsable problem list) -- see the virtual-calc fix for
the same root cause. This writes two files, matching those two schemas
exactly, for `../my-react-app` to merge in:

- output/ucup_only_ratings.json: same record shape as
  problem_ratings_calibrated.json (problem_id, problem_label, problem_name,
  contest_id, difficulty, difficulty_se, solved_count,
  reported_solved_in_contest, difficulty_cf, difficulty_cf_se), computed from
  the Phase-1 UCup-only survival fit (estimate_anchored's return_ucup extra)
  and calibrated with the same shape+affine map as arch_b.calibrate / the
  virtual calc (fit once on the tagged-scale records, reused here -- see the
  "same scale and anchor" verification in details.md).
- output/ucup_only_contests.json: contest+problem records in
  ../my-react-app/canonical/tagged.json's shape (no LLM tag/analysis
  fields -- that pipeline never ran on these problems; region is set to the
  literal "Universal Cup").
"""

import json
import os

import numpy as np

from arch_a import elo
from arch_a.load import _max_solve_seconds, dedupe_contests
from . import survival
from .anchor import UCUP, estimate_anchored
from .calibrate import _anchors, _gym_shape
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")


def build():
    ds, theta, b, _, uf, (ds_ucup, theta_u, b_u) = estimate_anchored(
        fit_fn=survival.fit, min_solve_hours=MIN_SOLVE_HOURS, verbose=False,
        return_ucup=True)
    _, se_b_u = survival.laplace_se(ds_ucup, theta_u, b_u)

    # same shape+affine calibration as calibrate.py / export_virtual_calc.py,
    # fit once on the tagged-scale records and reused for the UCup-only b_u
    records = [{"contest_id": int(cid), "problem_label": lab, "problem_name": name,
                "difficulty": float(b[p])}
               for p, (cid, lab, pid, name) in enumerate(ds.problems)]
    shape = _gym_shape(records)
    if shape is None:
        shape = lambda t: np.asarray(t, float)  # noqa: E731
    our, cf, _ = _anchors(records)
    slope, intercept = np.polyfit(shape(our), cf, 1)

    def to_cf(d):
        return float(np.clip(slope * shape(np.array([d]))[0] + intercept, elo.LO, elo.HI))

    def to_cf_se(d, se):
        h = 10.0
        dz = (shape(np.array([d + h]))[0] - shape(np.array([d - h]))[0]) / (2 * h)
        return float(abs(slope * dz) * se)

    tagged_ids = {int(cid) for cid in ds.contests}

    ratings = []
    for p, (cid, label, pid, name) in enumerate(ds_ucup.problems):
        cid = int(cid)
        if cid in tagged_ids:
            continue
        ci = ds_ucup.contest_of_problem[p]
        rows = np.where(ds_ucup.contest_of_row == ci)[0]
        solved = int(np.sum(ds_ucup.y[rows, p] & ds_ucup.solve_mask[rows, p]))
        d = float(b_u[p])
        se = float(se_b_u[p])
        ratings.append({
            "problem_id": pid,
            "problem_label": label,
            "problem_name": name,
            "contest_id": cid,
            "difficulty": round(d, 1),
            "difficulty_se": round(se, 1),
            "solved_count": solved,
            "reported_solved_in_contest": int(ds_ucup.raw_solved_count[p]),
            "difficulty_cf": round(to_cf(d), 1),
            "difficulty_cf_se": round(to_cf_se(d, se), 1),
        })

    raw = []
    for path in UCUP:
        with open(path) as f:
            raw.extend(json.load(f))
    raw = dedupe_contests(raw)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    raw = [c for c in raw if c["contest_id"] not in tagged_ids]

    contests = []
    for c in raw:
        contests.append({
            "contest_id": c["contest_id"],
            "contest_name": c.get("contest_name"),
            "year": c.get("year"),
            "region": "Universal Cup",
            "contest_url": c.get("contest_url"),
            "editorial_url": c.get("editorial_url"),
            "problems": [{
                "problem_id": p["problem_id"],
                "problem_name": p["problem_name"],
                "problem_url": p["problem_url"],
                "problem_solved_in_contest": p.get("problem_solved_in_contest"),
                "problem_score": p.get("problem_score"),
                "total_number_of_participant": p.get("total_number_of_participant"),
                "average_score": p.get("average_score"),
                "statement": p.get("statement"),
                "shortest_solution": p.get("shortest_solution"),
            } for p in c["problems"]],
        })

    return ratings, contests


def main():
    ratings, contests = build()
    os.makedirs(OUT_DIR, exist_ok=True)

    ratings_path = os.path.join(OUT_DIR, "ucup_only_ratings.json")
    with open(ratings_path, "w") as f:
        json.dump(ratings, f, indent=2, ensure_ascii=False)

    contests_path = os.path.join(OUT_DIR, "ucup_only_contests.json")
    with open(contests_path, "w") as f:
        json.dump(contests, f, indent=2, ensure_ascii=False)

    n_contests = len({r["contest_id"] for r in ratings})
    print(f"wrote {len(ratings)} ratings ({n_contests} contests) "
          f"to {os.path.normpath(ratings_path)}")
    print(f"wrote {len(contests)} contests ({sum(len(c['problems']) for c in contests)} problems) "
          f"to {os.path.normpath(contests_path)}")


if __name__ == "__main__":
    main()
