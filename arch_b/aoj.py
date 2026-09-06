"""Build and consume the Aizu Online Judge external-difficulty artifact.

AOJ statistics describe accumulated practice, not the onsite contest population,
so they are validation-only.  A problem is accepted only when:

* its normalized title is unique in both AOJ and ``data/tagged.json``; and
* at least ``MIN_CONTEST_MATCHES`` problems from the same contest match.

The second condition makes the surrounding problem set corroborate the contest
mirror and rejects isolated global-title collisions.  Difficulty is represented
by ``submissions / solvedUser`` (larger is harder) and evaluated only through
within-contest ranks.

    python -m arch_b.aoj --refresh
"""

import argparse
import json
import os
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DATA = os.path.join(ROOT, "data")
TAGGED = os.path.join(DATA, "tagged.json")
AOJ_FILE = os.path.join(DATA, "aoj_difficulty.json")
AOJ_URL = "https://judgeapi.u-aizu.ac.jp/problems?page=0&size=10000"
AOJ_PROBLEM_URL = "https://onlinejudge.u-aizu.ac.jp/problems/{id}"
MIN_CONTEST_MATCHES = 3
UA = "analyze_standings/1.0 (external validation dataset)"


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _unique_contests(contests):
    seen = set()
    for contest in contests:
        if contest["contest_id"] not in seen:
            seen.add(contest["contest_id"])
            yield contest


def build_artifact(aoj_problems, contests, retrieved_at,
                   min_contest_matches=MIN_CONTEST_MATCHES):
    """Return a provenance-rich, validation-ready AOJ artifact."""
    aoj_by_name = defaultdict(list)
    for problem in aoj_problems:
        aoj_by_name[_norm(problem["name"])].append(problem)

    tagged_by_name = defaultdict(list)
    for contest in _unique_contests(contests):
        for problem in contest["problems"]:
            tagged_by_name[_norm(problem["problem_name"])].append((contest, problem))

    candidates = []
    for name, tagged_rows in tagged_by_name.items():
        aoj_rows = aoj_by_name.get(name, [])
        if not name or len(tagged_rows) != 1 or len(aoj_rows) != 1:
            continue
        contest, problem = tagged_rows[0]
        candidates.append((contest, problem, aoj_rows[0]))

    contest_hits = Counter(contest["contest_id"] for contest, _, _ in candidates)
    accepted, rejected = [], []
    for contest, problem, aoj in sorted(
            candidates, key=lambda row: (row[0]["contest_id"], row[1]["problem_label"])):
        solved_user = int(aoj["solvedUser"])
        submissions = int(aoj["submissions"])
        row = {
            "contest_id": contest["contest_id"],
            "contest_name": contest["contest_name"],
            "year": contest.get("year"),
            "region": contest["region"],
            "problem_label": problem["problem_label"],
            "problem_name": problem["problem_name"],
            "aoj_problem_id": aoj["id"],
            "aoj_problem_name": aoj["name"],
            "solved_user": solved_user,
            "submissions": submissions,
            "attempts_per_solved_user": (
                round(submissions / solved_user, 8) if solved_user else None),
            "match_method": "unique_normalized_exact_title",
            "source_problem_url": AOJ_PROBLEM_URL.format(id=aoj["id"]),
        }
        if contest_hits[contest["contest_id"]] < min_contest_matches:
            row["match_confidence"] = "title_only_candidate"
            row["rejection_reason"] = (
                f"fewer_than_{min_contest_matches}_unique_title_matches_in_contest")
            rejected.append(row)
        elif solved_user == 0:
            row["match_confidence"] = "contest_corroborated"
            row["rejection_reason"] = "zero_solved_users"
            rejected.append(row)
        else:
            row["match_confidence"] = "contest_corroborated"
            accepted.append(row)

    return {
        "schema_version": 1,
        "source": {
            "name": "Aizu Online Judge",
            "url": AOJ_URL,
            "retrieved_at": retrieved_at,
            "raw_problem_count": len(aoj_problems),
        },
        "matching": {
            "normalization": "lowercase_ascii_alphanumeric",
            "title_cardinality": "one_to_one_across_both_datasets",
            "minimum_matches_per_contest": min_contest_matches,
            "candidate_count": len(candidates),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "role": "external_validation_only",
            "difficulty_proxy": "submissions_per_solved_user",
        },
        "matches": accepted,
        "rejected_candidates": rejected,
    }


def refresh(output_path=AOJ_FILE):
    request = urllib.request.Request(AOJ_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        aoj_problems = json.load(response)
    with open(TAGGED) as source:
        contests = json.load(source)
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    artifact = build_artifact(aoj_problems, contests, retrieved_at)
    with open(output_path, "w") as destination:
        json.dump(artifact, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    return artifact


def load_matches(path=AOJ_FILE):
    with open(path) as source:
        artifact = json.load(source)
    return {
        (row["contest_id"], row["problem_label"]): row["attempts_per_solved_user"]
        for row in artifact["matches"]
    }


def _rank(values):
    """Average ranks, including ties, with zero-based rank values."""
    values = np.asarray(values, float)
    if not np.all(np.isfinite(values)):
        raise ValueError("rank values must be finite")
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def spearman(x, y):
    """Spearman correlation with average ranks for ties."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.shape != y.shape:
        raise ValueError("Spearman inputs must have the same shape")
    if len(x) < 2:
        return float("nan")
    rx, ry = _rank(x), _rank(y)
    if np.all(rx == rx[0]) or np.all(ry == ry[0]):
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def within_contest_spearman(pairs):
    """Spearman after ranking both values separately inside each contest.

    ``pairs`` contains ``(contest_id, model_difficulty, aoj_proxy)`` rows.
    Pooling the within-contest ranks retains all observations without allowing
    different practice exposure between contests to become a difficulty signal.
    """
    grouped = defaultdict(list)
    for contest_id, model_value, aoj_value in pairs:
        grouped[contest_id].append((model_value, aoj_value))
    model_ranks, aoj_ranks = [], []
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        model_ranks.extend(_rank([row[0] for row in rows]))
        aoj_ranks.extend(_rank([row[1] for row in rows]))
    if len(model_ranks) < 2:
        return None
    return spearman(model_ranks, aoj_ranks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="fetch AOJ and rebuild data/aoj_difficulty.json")
    args = parser.parse_args()
    artifact = refresh() if args.refresh else json.load(open(AOJ_FILE))
    source = artifact["source"]
    matching = artifact["matching"]
    contests = len({row["contest_id"] for row in artifact["matches"]})
    print(f"AOJ snapshot {source['retrieved_at']}: {source['raw_problem_count']} problems")
    print(f"unique-title candidates={matching['candidate_count']}, "
          f"accepted={matching['accepted_count']} across {contests} contests, "
          f"rejected={matching['rejected_count']}")


if __name__ == "__main__":
    main()
