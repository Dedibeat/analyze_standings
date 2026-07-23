#!/usr/bin/env python3
"""Fetch standings-only supplemental contests from a QOJ category.

The sibling ``qoj-intergration/qoj.py`` module owns the QOJ HTML parser.  This
script deliberately requests only contest dashboards and standings: it does not
fetch statements, editorials, submissions, or solutions.
"""

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

try:
    import qoj
except ImportError:
    raise SystemExit(
        "qoj module not found; set PYTHONPATH to the qoj-intergration directory"
    )


def _existing_ids(paths):
    ids = set()
    for path in paths:
        with open(path) as source:
            ids.update(int(contest["contest_id"]) for contest in json.load(source))
    return ids


def _fetch_contest(uri, region, min_year=None, max_year=None):
    contest_id = qoj.contest_id_from_source(uri)
    dashboard = qoj.fetch_text(uri)
    metadata = qoj.parse_dashboard_metadata(dashboard)
    year = metadata["year"]
    if min_year is not None and (year is None or year < min_year):
        return None
    if max_year is not None and (year is None or year > max_year):
        return None
    problems = qoj.parse_dashboard_problems(dashboard)
    standings = qoj.get_standings(contest_id, process_unofficial=True)

    solved = {
        problem["problem_label"]: sum(
            bool(row.get("problems", {}).get(problem["problem_label"], {}).get("solved"))
            for row in standings
        )
        for problem in problems
    }
    for problem in problems:
        label = problem["problem_label"]
        problem["problem_solved_in_contest"] = solved[label]

    return {
        "contest_id": int(contest_id),
        "contest_name": metadata["contest_name"],
        "year": metadata["year"],
        "region": metadata["region"] or region,
        "contest_url": uri,
        "editorial_url": None,
        "problems": problems,
        "standings": standings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category", help="QOJ category id or URL")
    parser.add_argument("output", type=Path)
    parser.add_argument("--region", default="Training Camp")
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--max-year", type=int)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--exclude-json",
        action="append",
        default=[],
        help="JSON contest array whose contest ids must be skipped (repeatable)",
    )
    args = parser.parse_args()

    existing = _existing_ids(args.exclude_json)
    uris = list(
        dict.fromkeys(
            uri
            for uri in qoj.get_contests_from_category(args.category)
            if int(qoj.contest_id_from_source(uri)) not in existing
        )
    )

    def fetch(uri):
        try:
            contest = _fetch_contest(
                uri, args.region, min_year=args.min_year, max_year=args.max_year
            )
            if contest is None:
                return None
            print(
                f"fetched QOJ {contest['contest_id']}: "
                f"{len(contest['standings'])} rows",
                file=sys.stderr,
            )
            return contest
        except Exception as exc:
            print(f"warning: {uri}: {exc}", file=sys.stderr)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        contests = [contest for contest in executor.map(fetch, uris) if contest]
    contests.sort(key=lambda contest: (contest["year"] or 0, contest["contest_id"]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as target:
        json.dump(contests, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(f"wrote {len(contests)} contests to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
