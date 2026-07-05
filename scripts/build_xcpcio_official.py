#!/usr/bin/env python3
"""Build a local cache of XCPCIO official team identity keys for East Asia
medal-awarding contests.  Fetched once; consumed by ``arch_b.medals``.

Output: ``data/xcpcio_ea_official.json`` — a dict keyed by QOJ contest_id,
each value ``{"board_link": ..., "season": ..., "official_keys": [...]}``.

Matching strategy (same as scripts/add_xcpcio_official.py):
- XCPCIO team name + org → multiple normalized candidate keys
- QOJ row team_name + display_name_raw → multiple candidate keys
- Exact set intersection determines official/unofficial
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT / "data" / "xcpcio_ea_official.json"


# ── QOJ contest_id → (XCPCIO board_link, season, label) ──────────────────
# Regional sites + EC-Finals.  Built from the XCPCIO contest index at
# https://board.xcpcio.com/data/index/contest_list.json
EA_XCPCIO_MATCHES: dict[int, tuple[str, str, str]] = {
    # -- 47th season (2022-23) --
    1051: ("/icpc/47th/xian",              "47th", "Xi'an 2022"),
    1053: ("/icpc/47th/jinan",             "47th", "Jinan 2022"),
    1071: ("/icpc/47th/hangzhou",          "47th", "Hangzhou 2022"),
    1093: ("/icpc/47th/nanjing",           "47th", "Nanjing 2022"),
    1096: ("/icpc/47th/shenyang",          "47th", "Shenyang 2022"),
    1099: ("/icpc/47th/hongkong",          "47th", "Hong Kong & Macau 2022"),
    1522: ("/icpc/48th/ecfinal",           "47th", "EC-Final 2023 (Shanghai)"),
    # -- 48th season (2023-24) --
    1435: ("/icpc/48th/nanjing",           "48th", "Nanjing 2023"),
    1440: ("/icpc/48th/hefei",             "48th", "Hefei 2023"),
    1449: ("/icpc/48th/shenyang",          "48th", "Shenyang 2023"),
    1459: ("/icpc/48th/macau",             "48th", "Macau 2023"),
    1472: ("/icpc/48th/jinan",             "48th", "Jinan 2023"),
    1516: ("/icpc/48th/hangzhou",          "48th", "Hangzhou 2023"),
    1784: ("/icpc/48th/xian-invitational", "48th", "Xi'an 2023"),
    1894: ("/icpc/49th/ecfinal",           "48th", "EC-Final 2024 (China)"),
    # -- 49th season (2024-25) --
    1821: ("/icpc/49th/chengdu",           "49th", "Chengdu 2024"),
    1828: ("/icpc/49th/nanjing",           "49th", "Nanjing 2024"),
    1865: ("/icpc/49th/shenyang",          "49th", "Shenyang 2024"),
    1871: ("/icpc/49th/kunming",           "49th", "Kunming 2024"),
    1885: ("/icpc/49th/hongkong",          "49th", "Hong Kong 2024"),
    1893: ("/icpc/49th/hangzhou",          "49th", "Hangzhou 2024"),
    # -- 50th season (2025-26) --
    2562: ("/icpc/50th/xian",              "50th", "Xi'an 2025"),
    2567: ("/icpc/50th/chengdu",           "50th", "Chengdu 2025"),
    2581: ("/icpc/50th/nanjing",           "50th", "Nanjing 2025"),
    2609: ("/icpc/50th/wuhan",             "50th", "Wuhan 2025"),
    2641: ("/icpc/50th/shenyang",          "50th", "Shenyang 2025"),
    2908: ("/icpc/50th/shanghai",          "50th", "Shanghai 2025"),
    3169: ("/icpc/50th/hongkong",          "50th", "Hong Kong 2025"),
    # -- 50th EC-Final (not yet in tagged.json, reserved) --
}


def _norm(name: str) -> str:
    return "".join(c for c in str(name).lower() if c.isalnum())


def _strip_paren(s: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def _team_name_str(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        texts = value.get("texts", {})
        return texts.get("zh-CN", "") or texts.get("en", "") or str(value)
    return str(value or "")


def _xcpcio_official_keys(board_link: str) -> tuple[list[str], bool]:
    """Return (list of official key lists, has_explicit_groups)."""
    url = f"https://board.xcpcio.com/data{board_link}/team.json"
    cmd = [
        "curl", "-sL", "--retry", "3", "--retry-delay", "2",
        "--max-time", "60",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", "Accept: application/json",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr[:200]}")
    teams = json.loads(result.stdout)
    team_list = list(teams.values()) if isinstance(teams, dict) else teams

    has_groups = any("official" in t.get("group", []) for t in team_list)
    if has_groups:
        official_teams = [t for t in team_list if "official" in t.get("group", [])]
    else:
        official_teams = team_list

    all_keys = []
    for t in official_teams:
        name = _team_name_str(t.get("name", ""))
        org = str(t.get("organization", "") or "")
        name_s = _strip_paren(name)
        org_s = _strip_paren(org)
        keys = {_norm(name), _norm(name_s)}
        if org:
            for sep in [" - ", "-", ": "]:
                keys.add(_norm(f"{org}{sep}{name}"))
                keys.add(_norm(f"{org_s}{sep}{name}"))
                keys.add(_norm(f"{org}{sep}{name_s}"))
                keys.add(_norm(f"{org_s}{sep}{name_s}"))
        all_keys.append(sorted(keys))
    return all_keys, has_groups


def build_cache(matches: dict, output_path: Path) -> dict:
    """Fetch XCPCIO official keys for every matched contest and save."""
    cache = {}
    for qoj_id, (board_link, season, label) in sorted(matches.items()):
        print(f"  {label:30s} ({season}/{board_link.split('/')[-1]}) ...", end=" ", flush=True)
        try:
            keys, has_groups = _xcpcio_official_keys(board_link)
            cache[str(qoj_id)] = {
                "board_link": board_link,
                "season": season,
                "label": label,
                "has_explicit_groups": has_groups,
                "n_official": len(keys),
                "official_keys": keys,
            }
            tag = "groups" if has_groups else "all-xcpcio"
            print(f"OK ({len(keys)} teams, {tag})")
        except Exception as exc:
            print(f"FAIL: {exc}")
            cache[str(qoj_id)] = {"board_link": board_link, "season": season,
                                  "label": label, "error": str(exc)}
        time.sleep(0.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    n_ok = sum(1 for v in cache.values() if "error" not in v)
    n_err = sum(1 for v in cache.values() if "error" in v)
    print(f"\nWrote {output_path} ({n_ok} ok, {n_err} errors, {len(cache)} total)")
    return cache


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build XCPCIO official-team cache for EA contests")
    parser.add_argument("-o", "--output", default=str(OUTPUT))
    args = parser.parse_args()

    if os.path.exists(args.output):
        print(f"Loading existing cache from {args.output}")
        with open(args.output) as f:
            cache = json.load(f)
        missing = {qid: info for qid, info in EA_XCPCIO_MATCHES.items()
                   if str(qid) not in cache or "error" in cache[str(qid)]}
        if missing:
            print(f"Refreshing {len(missing)} missing/error entries...")
            new_entries = {}
            for qoj_id, (board_link, season, label) in sorted(missing.items()):
                print(f"  {label:30s} ({season}/{board_link.split('/')[-1]}) ...", end=" ", flush=True)
                try:
                    keys, has_groups = _xcpcio_official_keys(board_link)
                    new_entries[str(qoj_id)] = {
                        "board_link": board_link, "season": season, "label": label,
                        "has_explicit_groups": has_groups,
                        "n_official": len(keys), "official_keys": keys,
                    }
                    tag = "groups" if has_groups else "all-xcpcio"
                    print(f"OK ({len(keys)} teams, {tag})")
                except Exception as exc:
                    print(f"FAIL: {exc}")
                    new_entries[str(qoj_id)] = {"board_link": board_link, "season": season,
                                                "label": label, "error": str(exc)}
                time.sleep(0.5)
            # Merge into cache
            cache.update(new_entries)
            with open(args.output, "w") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            n_ok = sum(1 for v in cache.values() if "error" not in v)
            n_err = sum(1 for v in cache.values() if "error" in v)
            print(f"\nUpdated {args.output} ({n_ok} ok, {n_err} errors, {len(cache)} total)")
        else:
            print("All entries present, nothing to fetch.")
    else:
        build_cache(EA_XCPCIO_MATCHES, Path(args.output))


if __name__ == "__main__":
    main()
