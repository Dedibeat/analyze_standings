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


def check_2025(list_txt):
    """Replay 2025 step by step and compare with the published 公示 tables.

    2025 had 239 mainland seats: Hong Kong (126 valid teams, < 130) gave its
    fixed number of teams, one (HKU, Hong Kong rank 7).  Writes
    output/ecfinal_2025_allocation.csv (every entry examined, in order) and
    output/ecfinal_2025_school_check.csv (per-school seats vs Table 1).
    """
    text = open(list_txt, encoding="utf-8").read()
    table1 = text[text.find("表一"):text.find("三. EC-Final 晋级队伍名单")]
    table2 = re.sub(r"\s+", "", text[text.find("表二"):text.find("在获得第一次名额分配的高校报名结束后")])
    published = {}
    for line in table1.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\S+(?:\s\S+)?)\s+(\d+)(?:\s+(\d+))?(?:\s+(\d+))?\s*$", line)
        if m:
            nums = [int(v) for v in m.groups()[2:] if v]
            published[m.group(2).replace(" ", "")] = (nums[0], nums[1] if len(nums) == 3 else 0)

    def listed(x):
        return sum(m in table2 for m in members(x)) >= 2 or re.sub(r"\s+", "", x["team"]) in table2

    by = collections.defaultdict(list)
    for x in ROWS:
        if x["season"] == "2025" and x["official"] == "1" and x["official_rank"] and x["site"] not in NON_MAINLAND:
            by[x["site"]].append(x)
    for L in by.values():
        L.sort(key=lambda x: int(x["official_rank"]))
    order = sorted(by, key=lambda s: -sum(int(x["solved"] or 0) > 0 for x in by[s]))
    admitted_at, per_school, log, seat, k = {}, collections.Counter(), [], 0, 0
    while seat < 239:
        for s in order:
            if seat >= 239:
                break
            x = by[s][k]
            prior = next((v for m, v in admitted_at.items() if m & members(x)), None)
            if prior:
                decision = f"skip: team already admitted at {prior}"
            elif per_school[x["school"]] >= 3:
                decision = "skip: school already has 3"
            else:
                seat += 1
                per_school[x["school"]] += 1
                admitted_at[frozenset(members(x))] = f"{s} #{x['official_rank']}"
                decision = "admitted"
            log.append((seat if decision == "admitted" else "", k + 1, s, x, decision))
        k += 1
    hk = next(x for x in ROWS if x["season"] == "2025" and x["site"] == "hongkong" and x["official_rank"] == "7")
    log.append((240, "", "hongkong", hk, "admitted: Hong Kong fixed seat (126 valid teams < 130)"))
    per_school["香港大学"] += 1  # Table 1 uses the Chinese name

    with open("output/ecfinal_2025_allocation.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "seat", "tier", "site", "official_rank", "school", "team", "members", "solved",
                    "penalty_minutes", "medal", "decision", "in_published_table2"])
        for step, (seat_no, tier, s, x, decision) in enumerate(log, 1):
            w.writerow([step, seat_no, tier, s, x["official_rank"], x["school"], x["team"], x["members"],
                        x["solved"], x["penalty_minutes"], x["medal"], decision,
                        ("yes" if listed(x) else "no") if seat_no else ""])
    with open("output/ecfinal_2025_school_check.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["school", "published_qualifier_seats", "published_reward_seats", "simulated_seats", "match"])
        for school in sorted(set(published) | set(per_school)):
            pub, reward = published.get(school, (0, 0))
            w.writerow([school, pub, reward, per_school[school], "yes" if pub == per_school[school] else "NO"])
    admitted = [row for row in log if row[0]]
    hits = sum(listed(row[3]) for row in admitted)
    same = sum(published.get(s, (0, 0))[0] == per_school[s] for s in set(published) | set(per_school))
    print(f"2025 check: {hits}/240 simulated teams are in Table 2; per-school seats match Table 1 for "
          f"{same}/{len(set(published) | set(per_school))} schools (Table 1 total {sum(v[0] for v in published.values())})")
    for s in order:
        last = [row for row in admitted if row[2] == s][-1]
        print(f"  {s}: last admitted #{last[3]['official_rank']} ({last[3]['solved']} solved, "
              f"{last[3]['penalty_minutes']} min); walk reached rank {max(row[1] for row in log if row[2] == s)}")


def main():
    for season in ("2023", "2024", "2025"):
        order, counts, taken = admits_by_depth(season)
        d240 = next(k for k in counts if counts[k] >= 240)
        d230_7 = next(k for k in counts if counts[k] * 7 / 6 >= 230)
        print(f"{season}: {len(order)} mainland sites; 240 seats reach rank {d240}; "
              f"2026 rule (230 seats, 7 sites) ~rank {d230_7}")
    if "--check-2025" in sys.argv:
        check_2025(sys.argv[sys.argv.index("--check-2025") + 1])
    if "--project-2026" in sys.argv:
        project_2026()


if __name__ == "__main__":
    main()
