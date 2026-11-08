#!/usr/bin/env python3
"""Standings CSV from an official CCPC board on rank.iccpc.cn.

For boards XCPCIO does not carry, e.g. the 12th CCPC Changchun station
(2026-10-18).  The official board page loads
``/upload/outrank_attach/<board id>/rank.json``: teams, problems, every
submission and the award settings.  The board's own rules are reproduced
(``static/ojweb/csgoj/contest/rank_core.js`` and ``rank_tool.js``):

* runs are ordered by time, then solution id; compile errors (11) are dropped
  and runs after a team's first accepted run (4) on a problem are ignored;
* penalty = seconds to that first AC + 20 min per earlier run; order by
  (solved, penalty seconds, team id), ranks tie on whole penalty minutes;
* star teams (``tkind`` 2) are unranked; ``tkind`` 1 is a girls' team;
* medals: ``award_ratio`` packs gold/silver/bronze percent (gold in the low
  three digits); with ``flg_award_base`` 1 the base B is the official teams
  that submitted anything; lines are cumulative ceil(B * pct / 100).

    python3 scripts/iccpc_standings.py             # 12th CCPC Changchun
    python3 scripts/iccpc_standings.py BOARD_ID OUT.csv
"""
import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_ec_online_data as bd  # noqa: E402

BOARD = "8a3a28e3-f6b3-4a58-b4ac-fa8039fb2c72"  # 12th CCPC Changchun
OUT = bd.ROOT / "output" / "ccpc_12th_changchun_standings.csv"
FIELDS = ["rank", "official_rank", "medal", "team", "team_en", "school", "members", "coach",
          "official", "female", "solved", "penalty_minutes", "team_id"]
AC, CE = 4, 11


def medal_lines(data):
    contest = data["contest"]
    assert int(contest["flg_award_base"]) == 1 and int(contest["flg_award_qty_mode"]) == 0
    ratio, pcts = int(contest["award_ratio"]), []
    for _ in range(3):
        pcts.append(ratio % 1000)
        ratio //= 1000
    submitted = {s["team_id"] for s in data["solution"]}
    base = sum(1 for t in data["team"] if t["tkind"] != 2 and t["team_id"] in submitted)
    acc, lines = 0, []
    for p in pcts:
        acc += base * p
        lines.append(min(base, -(-acc // 100)))
    return lines


def standings(data):
    start = datetime.datetime.fromisoformat(data["contest"]["start_time"])
    runs = sorted((s for s in data["solution"] if 4 <= s["result"] < CE),
                  key=lambda s: (s["in_date"], s["solution_id"]))
    cells = collections.defaultdict(list)
    for s in runs:
        cells[(s["team_id"], s["problem_id"])].append(s)
    score = collections.defaultdict(lambda: [0, 0])
    for (tid, _), cell in cells.items():
        ac = next((i for i, s in enumerate(cell) if s["result"] == AC), None)
        if ac is not None:
            seconds = int((datetime.datetime.fromisoformat(cell[ac]["in_date"]) - start).total_seconds())
            score[tid][0] += 1
            score[tid][1] += seconds + ac * 1200

    rows = []
    for t in data["team"]:
        solved, penalty = score[t["team_id"]]
        rows.append(dict(team=t["name"], team_en=t.get("name_en", ""), school=t["school"],
                         members="|".join(m for m in t["tmember"].split("、") if m),
                         coach="|".join(c for c in t["coach"].split("、") if c),
                         official=int(t["tkind"] != 2), female=int(t["tkind"] == 1),
                         solved=solved, penalty_seconds=penalty, team_id=t["team_id"]))
    rows.sort(key=lambda r: (-r["solved"], r["penalty_seconds"], r["team_id"]))
    gold, silver, bronze = medal_lines(data)
    order = official_order = 0
    prev = {}
    for r in rows:
        r["penalty_minutes"] = r.pop("penalty_seconds") // 60
        key = (r["solved"], r["penalty_minutes"])
        order += 1
        r["rank"] = prev["all"][1] if prev.get("all", (None,))[0] == key else order
        prev["all"] = (key, r["rank"])
        r["official_rank"] = r["medal"] = ""
        if r["official"]:
            official_order += 1
            k = prev["off"][1] if prev.get("off", (None,))[0] == key else official_order
            prev["off"] = (key, k)
            r["official_rank"] = k
            r["medal"] = "gold" if k <= gold else "silver" if k <= silver else "bronze" if k <= bronze else ""
    return rows


def main(board=BOARD, out=OUT):
    url = f"https://rank.iccpc.cn/upload/outrank_attach/{board}/rank.json"
    data = json.loads(bd.fetch(url, bd.CACHE / "iccpc" / f"{board}.json").read_text(encoding="utf-8"))
    rows = standings(data)
    bd.write_csv(out, FIELDS, rows)
    print(f"{data['contest']['title']}: {len(rows)} teams "
          f"({sum(r['official'] for r in rows)} official), medal lines {medal_lines(data)} -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
