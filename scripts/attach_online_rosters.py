"""Attach registration-roster members to the EC online-round rows of tagged.json.

    python3 scripts/attach_online_rosters.py IN.json OUT.json

The 2024-2026 EC online rounds (QOJ 1794/1799, 2513/2524, 4071/4113) are in the
rating fit, but their QOJ rows carry members on only a few rows each, so their
~2,500 teams link to other contests only through trusted names. ``online_rosters.csv`` has
the official registration roster of every ranked team. A row gets its roster
when the key is unambiguous and the solved count agrees with the official
PKU ranking (``online_teams.csv``; zero-solve teams are not ranked and match on
the key alone):

* 2024 boards print ``team (<b>school</b>)``, so the key is school + team;
* 2025-2026 boards print the team name only, which must be unique in both the
  round's roster and the board.

Rows that already have >=2 members are left alone, so rerunning is a no-op.
Measured before shipping (details.md, 2026-09-28): calibrated LOCO neutral,
held-out Asia East cell log loss -0.00069 [-0.00141, -0.00005].
"""

import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from arch_b.online_gold import norm_name, norm_school  # noqa: E402

EC = os.path.join(os.path.dirname(__file__), os.pardir, "data", "ec_online")
ROUNDS = {1794: ("2024", "1"), 1799: ("2024", "2"), 2513: ("2025", "1"), 2524: ("2025", "2"),
          4071: ("2026", "1"), 4113: ("2026", "2")}
SCHOOL_MARK = re.compile(r"^(.*?)\s*\(<b>(.*?)</b>\)\s*$")


def _rows(name):
    with open(os.path.join(EC, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def attach(contest, season, rnd, rosters, ranking):
    """Attach members in place to one online-round contest; returns outcome counts."""
    roster = {(norm_school(r["school"]), norm_name(r["team"])): r["members"].split("|")
              for r in rosters if (r["season"], r["round"]) == (season, rnd)}
    schools_of = collections.defaultdict(list)
    for school, team in roster:
        schools_of[team].append(school)
    solved = {(norm_school(r["school"]), norm_name(r["team"])): int(r["solved"])
              for r in ranking if (r["season"], r["round"]) == (season, rnd)}
    on_board = collections.Counter(norm_name(s["team_name"] or "") for s in contest["standings"])
    counts = collections.Counter()
    for s in contest["standings"]:
        if s.get("members") and len(s["members"]) >= 2:
            counts["had members"] += 1
            continue
        m = SCHOOL_MARK.match(s["team_name"] or "")
        if m:
            key = (norm_school(m.group(2)), norm_name(m.group(1)))
        else:
            team = norm_name(s["team_name"] or "")
            if len(schools_of.get(team, ())) != 1 or on_board[team] != 1:
                counts["ambiguous name"] += 1
                continue
            key = (schools_of[team][0], team)
        if key not in roster:
            counts["not in roster"] += 1
        elif solved.get(key, 0) != s["total_solved"]:
            counts["solved count disagrees"] += 1
        else:
            s["members"] = [x for x in roster[key] if x]
            counts["attached"] += 1
    return counts


def main(src, dst):
    with open(src, encoding="utf-8") as f:
        contests = json.load(f)
    rosters, ranking = _rows("online_rosters.csv"), _rows("online_teams.csv")
    for c in contests:
        if c["contest_id"] in ROUNDS:
            print(c["contest_id"], dict(attach(c, *ROUNDS[c["contest_id"]], rosters, ranking)))
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(contests, f, ensure_ascii=False)


if __name__ == "__main__":
    main(*sys.argv[1:3])
