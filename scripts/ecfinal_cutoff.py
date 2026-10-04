#!/usr/bin/env python3
"""How deep in a mainland regional's standings does an EC-Final seat reach?

Replays the EC-Final round-robin rule ("名额分配办法", 2025 and 2026 notices on
icpc.pku.edu.cn) on ``data/ec_online/regional_teams.csv``: mainland sites are
ordered by valid teams (official, >=1 solved), then rank 1 of every site, rank
2 of every site, ... is admitted, skipping a team that shares a member with an
admitted team and schools that already have 3 teams.  2026 gives 230 seats to
7 mainland sites (2025: 240 to 6).  ``--project-2026`` replays each season's
real teams (school, strength = mean logit rank percentile, number of sites)
into the 2026 site capacities with Gaussian rank noise; the noise scale is
calibrated so the same replay reproduces that season's real 6-site depth.
Two bounds for 2026's extra seats: they become second sites of one-site teams
(``dup``) or go to new teams (``new``).

Usage: python scripts/ecfinal_cutoff.py [--check-2025 LIST.txt] [--project-2026]
LIST.txt is ``pdftotext -layout`` of the 2025 EC-Final 参赛名额公示
(https://icpc.pku.edu.cn/docs/2025-12/0629355dfddf43fd8d34ffad3fd0a3bb.pdf).
"""
import collections
import csv
import math
import random
import re
import statistics
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


CAP_2026 = {"xian": 380, "chengdu": 320, "wuhan": 400, "nanjing": 320,
            "shenyang": 400, "shanghai": 336, "nanchang": 360}  # slot_rules.json


def season_teams(season):
    rows = [x for x in ROWS if x["season"] == season and x["official"] == "1" and x["official_rank"]
            and x["site"] not in NON_MAINLAND and members(x)]
    size = collections.Counter(x["site"] for x in rows)
    teams = {}
    for x in rows:
        p = (int(x["official_rank"]) - 0.5) / size[x["site"]]
        teams.setdefault(frozenset(members(x)), {"school": x["school"], "l": []})["l"].append(math.log(p / (1 - p)))
    noise = statistics.pstdev([t["l"][0] - t["l"][1] for t in teams.values() if len(t["l"]) == 2]) / math.sqrt(2)
    return [(sum(t["l"]) / len(t["l"]), len(t["l"]), t["school"]) for t in teams.values()], noise, dict(size)


def replay_depth(teams, noise, caps, seats, extra, rng):
    """Depth reached when ``teams`` are redrawn onto sites ``caps``."""
    k_sites = [k for _, k, _ in teams]
    if extra == "dup":
        ones = [i for i, k in enumerate(k_sites) if k == 1]
        rng.shuffle(ones)
        for i in ones[:max(0, sum(caps.values()) - sum(k_sites))]:
            k_sites[i] = 2
    sites, weights = list(caps), list(caps.values())
    field = collections.defaultdict(list)
    for i, (strength, _, _) in enumerate(teams):
        chosen = set()
        while len(chosen) < k_sites[i]:
            chosen.add(rng.choices(sites, weights)[0])
        for s in chosen:
            field[s].append((strength + rng.gauss(0, noise), i))
    order = sorted(sites, key=lambda s: -len(field[s]))
    for s in order:
        field[s].sort()
    used, per_school, n, k = set(), collections.Counter(), 0, 0
    while True:
        for s in order:
            if k >= len(field[s]):
                continue
            i = field[s][k][1]
            if i in used or per_school[teams[i][2]] >= 3:
                continue
            used.add(i)
            per_school[teams[i][2]] += 1
            n += 1
            if n >= seats:
                return k + 1
        k += 1


def project_2026(reps=200):
    for season in ("2023", "2024", "2025"):
        teams, noise, sizes = season_teams(season)
        real = next(k for k, c in admits_by_depth(season)[1].items() if c >= 240)
        for extra in ("dup", "new"):
            def median_depth(m):
                rng = random.Random(7)
                return sorted(replay_depth(teams, noise * m, sizes, 240, extra, rng)
                              for _ in range(reps // 2))[reps // 4]
            scale = min((0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0), key=lambda m: abs(median_depth(m) - real))
            rng = random.Random(11)
            d = sorted(replay_depth(teams, noise * scale, CAP_2026, 230, extra, rng) for _ in range(reps))
            print(f"{season} teams, extra seats={extra}: noise x{scale} replays {median_depth(scale)} "
                  f"(real {real}); 2026 depth median {d[reps // 2]} "
                  f"(10-90% {d[reps // 10]}-{d[9 * reps // 10]})")


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
    if "--project-2026" in sys.argv:
        project_2026()


if __name__ == "__main__":
    main()
