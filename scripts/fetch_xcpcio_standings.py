#!/usr/bin/env python3
"""Convert hosted XCPCIO boards to the project's standings-only JSON schema."""

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


INDEX_URL = "https://board.xcpcio.com/data/index/contest_list.json"
DATA_URL = "https://board.xcpcio.com/data"
CORRECT = {"ACCEPTED", "CORRECT", "AC"}
IGNORED = {"PENDING", "SUBMITTED", "JUDGING", "COMPILATION_ERROR"}


def _fetch_json(url):
    error = None
    for _ in range(4):
        result = subprocess.run(
            [
                "curl", "-fsSL", "--retry", "3", "--retry-all-errors",
                "--connect-timeout", "10", "--max-time", "45",
                "-A", "Mozilla/5.0", url,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            error = RuntimeError(result.stderr.strip() or f"curl failed: {url}")
            continue
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            error = exc
    raise error


def _plain_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        texts = value.get("texts", {})
        fallback = value.get("fallback_lang")
        return texts.get(fallback, "") or texts.get("zh-CN", "") or texts.get("en", "")
    return str(value or "")


def _board_entries(node):
    if isinstance(node, dict):
        board_link = node.get("board_link")
        if board_link:
            yield board_link
            return
        for value in node.values():
            yield from _board_entries(value)


def _seconds(timestamp):
    timestamp = float(timestamp)
    return timestamp / 1000 if timestamp > 10_000_000_000 else timestamp


def _contest_id(board_link):
    digest = hashlib.sha256(board_link.encode()).hexdigest()[:12]
    return -int(digest, 16)


def _problem_id(board_link, label):
    digest = hashlib.sha256(f"{board_link}:{label}".encode()).hexdigest()[:12]
    return -int(digest, 16)


def _save(contests, output):
    contests.sort(key=lambda contest: (contest["year"], contest["board_link"]))
    temporary = output.with_suffix(output.suffix + ".tmp")
    with open(temporary, "w") as target:
        json.dump(contests, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(output)


def _organization_names(board_link, config):
    spec = config.get("organizations") or {}
    filename = spec.get("url") if isinstance(spec, dict) else None
    if not filename:
        return {}
    try:
        raw = _fetch_json(f"{DATA_URL}{board_link}/{filename}")
    except Exception as exc:
        print(f"warning: {board_link}: organizations: {exc}", file=sys.stderr)
        return {}
    values = raw.values() if isinstance(raw, dict) else raw
    return {str(item.get("id")): _plain_text(item.get("name")) for item in values}


def _convert(board_link, family, official_only):
    config = _fetch_json(f"{DATA_URL}{board_link}/config.json")
    start = _seconds(config["start_time"])
    end = _seconds(config["end_time"])
    duration = end - start
    if duration < 3.5 * 3600:
        return None

    teams_raw = _fetch_json(f"{DATA_URL}{board_link}/team.json")
    runs = _fetch_json(f"{DATA_URL}{board_link}/run.json")
    teams = teams_raw.values() if isinstance(teams_raw, dict) else teams_raw
    teams = list(teams)
    organizations = _organization_names(board_link, config)
    labels = [str(label) for label in config.get("problem_id", [])]
    if not labels:
        raise ValueError("config has no problem_id list")

    def explicitly_official(team):
        return "official" in (team.get("group") or []) or bool(team.get("official"))

    official_ids = {
        str(team.get("id", team.get("team_id")))
        for team in teams
        if explicitly_official(team)
    }
    has_groups = any(
        "official" in (team.get("group") or [])
        or "unofficial" in (team.get("group") or [])
        or "official" in team
        or "unofficial" in team
        for team in teams
    )
    if official_only and not has_groups:
        raise ValueError("official-only requested but board has no official group")

    unit = (config.get("options") or {}).get("submission_timestamp_unit", "second")
    multiplier = {"millisecond": 0.001, "minute": 60}.get(unit, 1)
    wrong_penalty = int(config.get("penalty", 1200))
    by_cell = defaultdict(list)
    for run in runs:
        team_id = str(run.get("team_id"))
        if official_only and team_id not in official_ids:
            continue
        problem = run.get("problem_id")
        if isinstance(problem, int) and 0 <= problem < len(labels):
            label = labels[problem]
        else:
            label = str(problem)
        if label not in labels:
            continue
        by_cell[(team_id, label)].append(
            (int(float(run.get("timestamp", 0)) * multiplier), str(run.get("status", "")).upper())
        )

    rows = []
    for team in teams:
        team_id = str(team.get("id", team.get("team_id")))
        if official_only and team_id not in official_ids:
            continue
        cells = {}
        solved_times = []
        for label in labels:
            attempts = sorted(by_cell.get((team_id, label), []))
            if not attempts:
                continue
            wrong = 0
            solved_at = None
            for timestamp, status in attempts:
                if status in CORRECT:
                    solved_at = timestamp
                    break
                if status not in IGNORED:
                    wrong += 1
            solved = solved_at is not None
            if solved:
                solved_times.append((solved_at, wrong))
            cells[label] = {
                "solved": solved,
                "score": 100 if solved else 0,
                "time_seconds": solved_at or 0,
                "wrong_attempts": wrong,
            }
        solved_count = len(solved_times)
        penalty = sum(
            timestamp + wrong_penalty * wrong for timestamp, wrong in solved_times
        )
        organization_id = str(team.get("organization_id", ""))
        members = [_plain_text(member) for member in (team.get("members") or [])]
        rows.append(
            {
                "rank": 0,
                "team_id": f"$DEFAULT_XCPCIO::{board_link}::{team_id}",
                "team_name": _plain_text(team.get("name")) or team_id,
                "members": [member for member in members if member],
                "affiliation": organizations.get(organization_id) or None,
                "display_name_raw": _plain_text(team.get("name")) or team_id,
                "official": team_id in official_ids if has_groups else True,
                "total_solved": solved_count,
                "total_score": solved_count * 100,
                "penalty_seconds": penalty,
                "problems": cells,
            }
        )

    ordered = sorted(rows, key=lambda row: (-row["total_solved"], row["penalty_seconds"]))
    previous = None
    rank = 0
    for position, row in enumerate(ordered, 1):
        score = (row["total_solved"], row["penalty_seconds"])
        if score != previous:
            rank = position
            previous = score
        row["rank"] = rank

    cid = _contest_id(board_link)
    contest_name = _plain_text(config.get("contest_name")) or board_link.rsplit("/", 1)[-1]
    solved_counts = {
        label: sum(row["problems"].get(label, {}).get("solved", False) for row in rows)
        for label in labels
    }
    return {
        "contest_id": cid,
        "contest_name": contest_name,
        "year": datetime.datetime.fromtimestamp(start, datetime.UTC).year,
        "region": {
            "provincial-contest": "China Provincial",
            "camp": "Training Camp",
        }.get(family, "Asia East Continent"),
        "contest_url": f"https://board.xcpcio.com{board_link}",
        "editorial_url": None,
        "source": "xcpcio",
        "board_link": board_link,
        "duration_seconds": int(duration),
        "problems": [
            {
                "problem_id": _problem_id(board_link, label),
                "problem_label": label,
                "problem_name": f"{contest_name} {label}",
                "problem_solved_in_contest": solved_counts[label],
            }
            for label in labels
        ],
        "standings": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=["provincial-contest", "icpc", "ccpc", "camp"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--max-year", type=int)
    parser.add_argument("--official-only", action="store_true")
    parser.add_argument(
        "--board-link",
        action="append",
        help="fetch an exact board link instead of traversing the family index",
    )
    args = parser.parse_args()

    if args.board_link:
        board_links = sorted(set(args.board_link))
    else:
        index = _fetch_json(INDEX_URL)
        board_links = sorted(set(_board_entries(index.get(args.family, {}))))
    board_links = [
        link for link in board_links
        if "warmup" not in link.lower() and "assets" not in link.lower()
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        with open(args.output) as source:
            contests = json.load(source)
    else:
        contests = []
    wrong_family = [
        contest["board_link"] for contest in contests
        if not contest["board_link"].startswith(f"/{args.family}/")
    ]
    if wrong_family:
        raise ValueError(
            f"output contains boards outside family {args.family}: {wrong_family[0]}"
        )
    if args.official_only and any(
        not row.get("official")
        for contest in contests
        for row in contest["standings"]
    ):
        raise ValueError("output already contains unofficial rows; choose a new output")
    completed = {contest["board_link"] for contest in contests}
    for position, board_link in enumerate(board_links, 1):
        if board_link in completed:
            continue
        parts = board_link.strip("/").split("/")
        path_year = int(parts[1]) if args.family == "provincial-contest" else None
        if args.min_year is not None and path_year is not None and path_year < args.min_year:
            continue
        if args.max_year is not None and path_year is not None and path_year > args.max_year:
            continue
        try:
            contest = _convert(board_link, args.family, args.official_only)
            if contest is None:
                continue
            year = contest["year"]
            if args.min_year is not None and year < args.min_year:
                continue
            if args.max_year is not None and year > args.max_year:
                continue
            contests.append(contest)
            _save(contests, args.output)
            print(
                f"[{position}/{len(board_links)}] {board_link}: "
                f"{len(contest['standings'])} teams",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"warning: {board_link}: {exc}", file=sys.stderr)

    ids = [contest["contest_id"] for contest in contests]
    if len(ids) != len(set(ids)):
        raise RuntimeError("synthetic contest-id collision")
    _save(contests, args.output)
    print(f"wrote {len(contests)} contests to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
