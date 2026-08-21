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
  reported_solved_in_contest, difficulty_cf, difficulty_cf_fit_se,
  difficulty_cf_level_sd, difficulty_cf_se). These come
  from the same single joint fit and the same shape+affine calibration as
  output/problem_ratings_calibrated.json -- since the 2026-08-21 audit the
  Universal Cup is ordinary fit data, so there is no longer a second scale
  to cross-walk (the old Phase-1-fit export sat ~90 CF points low).
- output/ucup_only_contests.json: contest+problem records in
  ../my-react-app/canonical/tagged.json's shape (no LLM tag/analysis
  fields -- that pipeline never ran on these problems; region is set to the
  literal "Universal Cup"). Many UCup rounds carry no ``year`` in the source
  data; those fall back to their season's most common year (2024 for
  ucup_s3.json, 2025 for ucup_s4.json) rather than null, since the app
  displays ``contest_name + ' ' + year`` verbatim and a null year rendered
  as the literal string "null".
"""

import json
import os
from collections import Counter

import numpy as np

from arch_a import elo
from arch_a.load import _max_solve_seconds, dedupe_contests
from . import survival
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, estimate_joint
from .calibrate import _anchors, _gym_shape
from .hier_calibrate import level_sd
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")


def build():
    ds, theta, b, _, uf = estimate_joint(
        fit_fn=survival.fit, min_solve_hours=MIN_SOLVE_HOURS, verbose=False)
    _, se_b = survival.laplace_se(ds, theta, b)

    # same shape+affine calibration as calibrate.py / export_virtual_calc.py
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

    # same three uncertainties as calibrate.py: the fit SE through the map, the
    # calibration level sd for a contest the CF anchors never saw, and the total
    level_by_contest, default_level = level_sd(records)

    def to_cf_se(d, se, contest_id):
        h = 10.0
        dz = (shape(np.array([d + h]))[0] - shape(np.array([d - h]))[0]) / (2 * h)
        fit_se = abs(slope * dz) * se
        level = level_by_contest.get(contest_id, default_level)
        return float(fit_se), float(level), float(np.hypot(fit_se, level))

    # a handful of UCup rounds are also carried by another source file (Petroz
    # camps mirrored as UCup rounds); the fit keeps that source's copy, so only
    # contests unique to the UCup seasons are exported here
    other_ids = set()
    for path in [TAGGED, OLDER_ICPC, PETROZ, WF]:
        with open(path) as f:
            other_ids.update(c["contest_id"] for c in json.load(f))

    raw = []
    fallback_year = {}  # contest_id -> season's most common year, for null-year contests
    for path in UCUP:
        with open(path) as f:
            file_contests = json.load(f)
        years = [c["year"] for c in file_contests if c.get("year") is not None]
        season_year = Counter(years).most_common(1)[0][0] if years else None
        for c in file_contests:
            fallback_year[c["contest_id"]] = season_year
        raw.extend(file_contests)
    raw = dedupe_contests(raw)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    raw = [c for c in raw if c["contest_id"] not in other_ids]
    ucup_only_ids = {c["contest_id"] for c in raw}

    ratings = []
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        cid = int(cid)
        if cid not in ucup_only_ids:
            continue
        solved = int(ds.solved_count[p])
        d = float(b[p])
        se = float(se_b[p])
        fit_se, level, total_se = to_cf_se(d, se, cid)
        ratings.append({
            "problem_id": pid,
            "problem_label": label,
            "problem_name": name,
            "contest_id": cid,
            "difficulty": round(d, 1),
            "difficulty_se": round(se, 1),
            "solved_count": solved,
            "reported_solved_in_contest": int(ds.raw_solved_count[p]),
            "difficulty_cf": round(to_cf(d), 1),
            "difficulty_cf_fit_se": round(fit_se, 1),
            "difficulty_cf_level_sd": round(level, 1),
            "difficulty_cf_se": round(total_se, 1),
        })

    contests = []
    for c in raw:
        contests.append({
            "contest_id": c["contest_id"],
            "contest_name": c.get("contest_name"),
            "year": c.get("year") or fallback_year.get(c["contest_id"]),
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
