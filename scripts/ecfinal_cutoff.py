#!/usr/bin/env python3
"""How deep in a mainland regional's standings does an EC-Final seat reach?

Replays the EC-Final round-robin rule ("名额分配办法", 2025 and 2026 notices on
icpc.pku.edu.cn) on ``data/ec_online/regional_teams.csv``: mainland sites are
ordered by valid teams (official, >=1 solved), then rank 1 of every site, rank
2 of every site, ... is admitted, skipping a team that shares a member with an
admitted team and schools that already have 3 teams.  2026 gives 230 seats to
7 mainland sites (2025: 240 to 6); the 7-site depth is estimated by scaling
6-site admits by 7/6.

Usage: python scripts/ecfinal_cutoff.py [--check-2025 LIST.txt]
LIST.txt is ``pdftotext -layout`` of the 2025 EC-Final 参赛名额公示
(https://icpc.pku.edu.cn/docs/2025-12/0629355dfddf43fd8d34ffad3fd0a3bb.pdf).
"""
import collections
import csv
import re
import sys

ROWS = list(csv.DictReader(open("data/ec_online/regional_teams.csv", encoding="utf-8")))
NON_MAINLAND = {"hongkong", "macau"}


def members(x):
    return set(x["members"].split("|")) - {""}


def admits_by_depth(season, max_depth=120):
    """Teams admitted after each rank tier k (1-based) with unlimited seats."""
    by = collections.defaultdict(list)
    for x in ROWS:
        if x["season"] == season and x["official"] == "1" and x["official_rank"] and x["site"] not in NON_MAINLAND:
            by[x["site"]].append(x)
    for L in by.values():
        L.sort(key=lambda x: int(x["official_rank"]))
    order = sorted(by, key=lambda s: -sum(int(x["solved"] or 0) > 0 for x in by[s]))
    used, per_school, taken, counts = set(), collections.Counter(), [], {}
    for k in range(max_depth):
        for s in order:
            if k >= len(by[s]):
                continue
            x = by[s][k]
            if members(x) & used or per_school[x["school"]] >= 3:
                continue
            used |= members(x)
            per_school[x["school"]] += 1
            taken.append(x)
        counts[k + 1] = len(taken)
    return order, counts, taken


def main():
    for season in ("2023", "2024", "2025"):
        order, counts, taken = admits_by_depth(season)
        d240 = next(k for k in counts if counts[k] >= 240)
        d230_7 = next(k for k in counts if counts[k] * 7 / 6 >= 230)
        print(f"{season}: {len(order)} mainland sites; 240 seats reach rank {d240}; "
              f"2026 rule (230 seats, 7 sites) ~rank {d230_7}")
    if "--check-2025" in sys.argv:
        text = open(sys.argv[sys.argv.index("--check-2025") + 1], encoding="utf-8").read()
        text = re.sub(r"\s+", "", text[text.find("表二"):text.find("在获得第一次名额分配的高校报名结束后")])
        _, counts, taken = admits_by_depth("2025")
        sim = {frozenset(members(x)) for x in taken[:240]}
        hit = sum(sum(m in text for m in s) >= 2 for s in sim)
        print(f"2025 check: {hit}/240 simulated teams appear in the published qualifier table")


if __name__ == "__main__":
    main()
