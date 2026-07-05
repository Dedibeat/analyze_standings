#!/usr/bin/env python3
"""Add official/unofficial team tags to tagged.json using XCPCIO board data.

For each East Asia regional contest that has a matching XCPCIO entry, fetch
XCPCIO's team.json (which records the official onsite field) and tag every
standing row with ``official: true/false``.

XCPCIO's team.json groups (e.g. ``"group": ["official"]``) are the ground truth
where available (49th/50th seasons). For older seasons (47th/48th) XCPCIO's
team list is all-official by construction (only domjudge-imported onsite teams),
so every XCPCIO team is treated as official.

Matching: XCPCIO team name → QOJ standing row team_name, normalized
(alphanumeric-only, case-insensitive).  In testing all XCPCIO teams matched
to a QOJ counterpart.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


# ── XCPCIO matching table ──────────────────────────────────────────────
# QOJ contest_id → (XCPCIO board_link, season, city)
# Generated 2026-07-05 from https://board.xcpcio.com/data/index/contest_list.json
EA_XCPCIO_MATCHES: dict[int, tuple[str, str, str]] = {
    1051: ("/icpc/47th/xian",              "47th", "xian"),
    1053: ("/icpc/47th/jinan",             "47th", "jinan"),
    1071: ("/icpc/47th/hangzhou",          "47th", "hangzhou"),
    1093: ("/icpc/47th/nanjing",           "47th", "nanjing"),
    1096: ("/icpc/47th/shenyang",          "47th", "shenyang"),
    1099: ("/icpc/47th/hongkong",          "47th", "hongkong"),
    1435: ("/icpc/48th/nanjing",           "48th", "nanjing"),
    1440: ("/icpc/48th/hefei",             "48th", "hefei"),
    1449: ("/icpc/48th/shenyang",          "48th", "shenyang"),
    1459: ("/icpc/48th/macau",             "48th", "macau"),
    1472: ("/icpc/48th/jinan",             "48th", "jinan"),
    1516: ("/icpc/48th/hangzhou",          "48th", "hangzhou"),
    1784: ("/icpc/48th/xian-invitational", "48th", "xian"),
    1821: ("/icpc/49th/chengdu",           "49th", "chengdu"),
    1828: ("/icpc/49th/nanjing",           "49th", "nanjing"),
    1865: ("/icpc/49th/shenyang",          "49th", "shenyang"),
    1871: ("/icpc/49th/kunming",           "49th", "kunming"),
    1885: ("/icpc/49th/hongkong",          "49th", "hongkong"),
    1893: ("/icpc/49th/hangzhou",          "49th", "hangzhou"),
    2562: ("/icpc/50th/xian",              "50th", "xian"),
    2567: ("/icpc/50th/chengdu",           "50th", "chengdu"),
    2581: ("/icpc/50th/nanjing",           "50th", "nanjing"),
    2609: ("/icpc/50th/wuhan",             "50th", "wuhan"),
    2641: ("/icpc/50th/shenyang",          "50th", "shenyang"),
    2908: ("/icpc/50th/shanghai",          "50th", "shanghai"),
    3169: ("/icpc/50th/hongkong",          "50th", "hongkong"),
}


def _team_name_str(value) -> str:
    """XCPCIO team names are either a plain string or an i18n dict like
    ``{'fallback_lang': 'zh-CN', 'texts': {'en': '...', 'zh-CN': '...'}}``.
    Return a best-effort plain string."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        texts = value.get("texts", {})
        return texts.get("zh-CN", "") or texts.get("en", "") or str(value)
    return str(value or "")


def _norm(name: str) -> str:
    return "".join(c for c in str(name).lower() if c.isalnum())


def _strip_paren(s: str) -> str:
    """Remove parenthetical translations like 'Beihang University' from
    '北京航空航天大学(Beihang University)'."""
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def _match_keys(xcpcio_team: dict) -> list[str]:
    """Return candidate normalized keys for matching an XCPCIO team to QOJ.

    QOJ stores team names in several formats:
    - Bare team name (ucup teams)
    - ``Org - TeamName - member1, member2, ...`` (domjudge teams, in display_name_raw)
    - ``TeamName - member1, member2, ...`` (domjudge teams, in team_name)

    We generate all plausible keys from the XCPCIO data (org + name),
    also trying stripped variants (without parenthetical translations).
    """
    name = _team_name_str(xcpcio_team.get("name", ""))
    org = str(xcpcio_team.get("organization", "") or "")
    name_short = _strip_paren(name)
    org_short = _strip_paren(org) if org else ""

    keys = [_norm(name), _norm(name_short)]
    if org:
        for sep in [" - ", "-", ": "]:
            keys.append(_norm(f"{org}{sep}{name}"))
            keys.append(_norm(f"{org_short}{sep}{name}"))
            keys.append(_norm(f"{org}{sep}{name_short}"))
            keys.append(_norm(f"{org_short}{sep}{name_short}"))
    return keys


def _fetch_json(url: str) -> dict:
    cmd = [
        "curl", "-sL", "--retry", "2", "--retry-delay", "1",
        "--max-time", "30",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", "Accept: application/json",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr[:200]}")
    return json.loads(result.stdout)


def fetch_official_keys(board_link: str) -> tuple[list[list[str]], bool]:
    """Return (list of candidate-key-lists per official team, has_explicit_groups).

    Each element is the list of _match_key outputs for one official XCPCIO team.
    A QOJ row matches if any of its keys hits any candidate key.
    """
    url = f"https://board.xcpcio.com/data{board_link}/team.json"
    teams = _fetch_json(url)
    team_list = list(teams.values()) if isinstance(teams, dict) else teams

    has_groups = any("official" in t.get("group", []) for t in team_list)
    if has_groups:
        official_teams = [t for t in team_list if "official" in t.get("group", [])]
    else:
        # Older seasons: entire XCPCIO list is the official field
        official_teams = team_list

    keys = [_match_keys(t) for t in official_teams]
    return keys, has_groups


def add_official_tags(
    contests: list[dict],
    matches: dict[int, tuple[str, str, str]],
    dry_run: bool = False,
) -> dict:
    """Add ``official`` field to every standing row of matched contests.

    Returns a stats dict with per-contest counts.
    """
    stats = {}
    total_tagged = 0

    for i, contest in enumerate(contests):
        cid = contest.get("contest_id")
        if cid not in matches:
            continue

        board_link, season, city = matches[cid]
        standings = contest.get("standings", [])
        if not standings:
            stats[cid] = {"error": "no standings in contest"}
            continue

        try:
            official_keys, has_groups = fetch_official_keys(board_link)
        except Exception as exc:
            print(f"  [{i+1}] QOJ {cid} ({season}/{city}): FETCH FAILED — {exc}", file=sys.stderr)
            stats[cid] = {"error": str(exc)}
            continue

        # Build flat lookup set from all candidate keys
        official_set: set[str] = set()
        for keys in official_keys:
            for k in keys:
                official_set.add(k)

        n_official = 0
        n_unofficial = 0
        for row in standings:
            # Build all candidate keys from QOJ row.
            # QOJ display_name_raw often has the form
            #   "Org - TeamName - member1, member2, ..."
            # while XCPCIO has "Org - TeamName" (no members).  Try every
            # " - "-delimited prefix of the raw string.
            qoj_keys = {_norm(row.get("team_name", ""))}
            raw = str(row.get("display_name_raw", "") or "")
            if raw:
                qoj_keys.add(_norm(raw))
                # Also try prefixes (strip trailing members)
                parts = raw.split(" - ")
                for n in range(2, len(parts) + 1):
                    qoj_keys.add(_norm(" - ".join(parts[:n])))

            row["official"] = bool(qoj_keys & official_set)
            if row["official"]:
                n_official += 1
            else:
                n_unofficial += 1

        tag = "groups" if has_groups else "all-xcpcio"
        print(f"  [{i+1}] QOJ {cid} ({season}/{city}): {n_official} official + {n_unofficial} unofficial [{tag}]", file=sys.stderr)
        stats[cid] = {
            "season": season, "city": city,
            "n_official": n_official, "n_unofficial": n_unofficial,
            "has_explicit_groups": has_groups,
        }
        total_tagged += 1

        if not dry_run:
            time.sleep(0.3)

    print(f"\nTagged {total_tagged} contests", file=sys.stderr)
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Add XCPCIO official tags to tagged.json")
    parser.add_argument("--input", default=str(PROJECT / "data" / "tagged.json"))
    parser.add_argument("--output", default=str(PROJECT / "data" / "tagged_with_official.json"))
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report, don't save")
    args = parser.parse_args()

    with open(args.input) as f:
        contests = json.load(f)

    matches = EA_XCPCIO_MATCHES
    print(f"Loaded {len(contests)} contests, {len(matches)} with XCPCIO matches", file=sys.stderr)
    stats = add_official_tags(contests, matches, dry_run=args.dry_run)

    if not args.dry_run:
        with open(args.output, "w") as f:
            json.dump(contests, f, ensure_ascii=False, indent=2)
        print(f"Wrote {args.output}", file=sys.stderr)

    n_with_groups = sum(1 for s in stats.values() if s.get("has_explicit_groups"))
    n_without = sum(1 for s in stats.values() if not s.get("has_explicit_groups") and "error" not in s)
    n_errors = sum(1 for s in stats.values() if "error" in s)
    print(f"Summary: {n_with_groups} with explicit groups, {n_without} inferred, {n_errors} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
