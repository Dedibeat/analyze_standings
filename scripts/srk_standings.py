#!/usr/bin/env python3
"""Standings CSV from an algoux srk ranklist (rl.algoux.cn, github.com/algoux/srk-collection).

For boards XCPCIO does not carry, e.g. the 12th CCPC Changchun station
(2026-10-18).  Rows keep the ranklist's order.  Penalty is the srk total time
truncated to minutes (the ranklist's ``rankingTimePrecision``); equal
(solved, penalty) share a rank.  Medals go to official teams with at least one
solve, by official rank, using the counts in the ranklist's "#" series.

    python3 scripts/srk_standings.py              # 12th CCPC Changchun
    python3 scripts/srk_standings.py URL OUT.csv
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_ec_online_data as bd  # noqa: E402

URL = ("https://raw.githubusercontent.com/algoux/srk-collection/master/"
       "official/ccpc/ccpc2026/ccpc2026changchun.srk.json")
OUT = bd.ROOT / "output" / "ccpc_12th_changchun_standings.csv"
FIELDS = ["rank", "official_rank", "medal", "team", "team_en", "school", "members", "coach",
          "official", "female", "solved", "penalty_minutes", "team_id"]


def _ranks(rows):
    out = []
    for i, r in enumerate(rows):
        tied = i and (r["solved"], r["penalty_minutes"]) == (rows[i - 1]["solved"], rows[i - 1]["penalty_minutes"])
        out.append(out[-1] if tied else i + 1)
    return out


def standings(srk):
    rows = []
    for r in srk["rows"]:
        u = r["user"]
        people = u.get("teamMembers") or []
        rows.append(dict(
            team=u["name"].get("zh-CN") or u["name"]["fallback"], team_en=u["name"].get("en-US", ""),
            school=u.get("organization", ""),
            members="|".join(m["name"] for m in people if m.get("role") != "coach"),
            coach="|".join(m["name"] for m in people if m.get("role") == "coach"),
            official=int(bool(u.get("official"))), female=int("female" in (u.get("markers") or [])),
            solved=r["score"]["value"], penalty_minutes=r["score"]["time"][0] // 60000,
            team_id=u["id"], official_rank="", medal=""))
    for r, k in zip(rows, _ranks(rows)):
        r["rank"] = k
    official = [r for r in rows if r["official"]]
    gold, silver, bronze = next(s for s in srk["series"] if s["title"] == "#")["rule"]["options"]["count"]["value"]
    for r, k in zip(official, _ranks(official)):
        r["official_rank"] = k
        if r["solved"]:
            r["medal"] = ("gold" if k <= gold else "silver" if k <= gold + silver
                          else "bronze" if k <= gold + silver + bronze else "")
    return rows


def main(url=URL, out=OUT):
    srk = json.loads(bd.fetch(url, bd.CACHE / "srk" / url.rsplit("/", 1)[1]).read_text(encoding="utf-8"))
    rows = standings(srk)
    bd.write_csv(out, FIELDS, rows)
    print(f"{len(rows)} teams ({sum(r['official'] for r in rows)} official) -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
