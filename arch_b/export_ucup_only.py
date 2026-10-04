"""Export the Universal Cup contests that never made it into tagged.json.

    python -m arch_b.export_ucup_only

52 UCup rounds (ucup_s3.json + ucup_s4.json) pass MIN_SOLVE_HOURS but are not
among the 146 tagged.json contests, so they're absent from both
output/problem_ratings_calibrated.json (ratings) and canonical/tagged.json in
../my-react-app (the browsable problem list) -- see the virtual-calc fix for
the same root cause. This writes two files, matching those two schemas
exactly, for `../my-react-app` to merge in:

- output/ucup_only_ratings.json: these contests' records copied from
  output/problem_ratings_calibrated.json (the shipped DE ratings; run
  ``arch_b.calibrate`` first), so both files carry the same numbers. Since the
  2026-08-21 audit the Universal Cup is ordinary fit data, so there is no
  longer a second scale to cross-walk (the old Phase-1-fit export sat ~90 CF
  points low).
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

from arch_a.load import _max_solve_seconds, dedupe_contests
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")


def build():
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

    with open(os.path.join(OUT_DIR, "problem_ratings_calibrated.json"), encoding="utf-8") as f:
        ratings = [r for r in json.load(f) if r["contest_id"] in ucup_only_ids]

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
