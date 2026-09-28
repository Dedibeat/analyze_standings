#!/usr/bin/env python3
"""Add the 2025-2026 online registration lists (PTA exports) to ``online_rosters.csv``.

``build_ec_online_data.py`` parses the 2022-2024 lists from icpc.pku.edu.cn
PDFs; the 2025-2026 lists exist only on uep.pintia.cn and were exported by hand
to ``data/`` (columns ``team_name, school_name_cn, members`` ('/'-separated),
``review_status``, ...).  REVIEWED rows are appended; rows of these seasons
already in the file are replaced, so the script is idempotent.  Run it after
the builder, which rewrites the file with 2022-2024 only.

PTA shows some schools under a newer or duplicate-marked name.  They are mapped
to the name of that season's official online ranking, where the school's teams
appear (checked by team names: 4-16 shared names each, 1 for 华北科技学院).  The
2026 ranking already uses most new names, so the map is per season; with it
every ranked 2025 and 2026 team matches a roster by school + team name.

    python3 scripts/add_pta_rosters.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ec_online" / "online_rosters.csv"
PTA_FILES = {
    ("2025", "1"): "icpc_2025_online_1_teams.csv",
    ("2025", "2"): "icpc_teams_2025_online_2_fixed.csv",
    ("2026", "1"): "icpc_2026_ec_round1_teams.csv",
    ("2026", "2"): "icpc_2026_ec_online_round2_teams.csv",
}
PTA_SCHOOL_ALIAS = {
    "2025": {
        "大连理工大学盘锦校区（重复）": "大连理工大学盘锦校区",
        "合肥工业大学宣城校区（重复）": "合肥工业大学宣城校区",
        "常熟理工学院（已改名）": "常熟理工学院(苏州工学院)",
        "华北科技学院（已更名为应急管理大学）": "华北科技学院",
        "哈尔滨理工大学威海校区": "哈尔滨理工大学(荣成)",
        "湖南理工大学": "湖南理工学院",
        "绍兴大学": "绍兴文理学院",
        "大连工程学院": "大连理工大学城市学院",
        "湖州师范大学": "湖州师范学院",
        "中国人民解放军网络空间部队信息工程大学": "信息工程大学",
    },
    "2026": {"湖南理工大学": "湖南理工学院"},
}


def pta_rows():
    out = []
    for (season, rnd), name in PTA_FILES.items():
        with open(ROOT / "data" / name, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["review_status"] != "REVIEWED":
                    continue
                school = r["school_name_cn"].strip()
                members = [m.strip() for m in r["members"].split("/") if m.strip()]
                out.append(dict(season=season, round=rnd, school=PTA_SCHOOL_ALIAS[season].get(school, school),
                                team=r["team_name"].strip(), members="|".join(members)))
    return out


def main():
    with open(OUT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seasons = {s for s, _ in PTA_FILES}
    new = pta_rows()
    rows = [r for r in rows if r["season"] not in seasons] + new
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["season", "round", "school", "team", "members"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(new)} PTA roster rows for {sorted(seasons)} -> {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
