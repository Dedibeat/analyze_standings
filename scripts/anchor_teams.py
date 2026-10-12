#!/usr/bin/env python3
"""Anchor teams for judging a result on a non-regional contest (CCPC, provincial, invitational).

Pool: 2026 teams that played both EC online rounds.  A team is the same in
both rounds when the two PTA registrations (``data/icpc_2026_ec_round1_teams.csv``,
``data/icpc_2026_ec_online_round2_teams.csv``) share a school and >= 2 members,
so renamed teams still count.  Online ranks come from ``online_teams.csv`` by
each round's registered name; x = -mean log online rank.

Tiers, per team at one mainland 2026 regional it attends:

* gold      P(gold) >= 0.5, the ``arch_b.online_gold`` model averaged over the
            seven 2026 rules lines;
* ecfinal   P(EC-Final seat) >= 0.5, the ``scripts/ecfinal_chance.py`` model
            (rank <= K, K = 70/75/80 weighted 1/4, 1/2, 1/4).

Once a team has a 51st-season (2026) regional row in ``regional_teams.csv``,
its tier comes from its best actual result instead: gold medal -> gold,
official rank <= 75 at a mainland site -> ecfinal (a proxy until the EC-Final
公示), else none.

    python3 scripts/anchor_teams.py                       # write output/anchor_teams.csv
    python3 scripts/anchor_teams.py --board ccpc/12th/harbin --team NUM-R^3
    python3 scripts/anchor_teams.py --board ccpc/11th/jinan --solved 6 --penalty 800   # a virtual run
    python3 scripts/anchor_teams.py --overlap [--since 2026-03-01]

``--board`` takes an XCPCIO board link (as in board.xcpcio.com/<link>), finds
the anchors on it (same school and >= 2 shared members, else same school and
team name) and counts how many the team beat on (solved, penalty).
``--overlap`` lists every non-warmup XCPCIO board since ``--since`` with how
many of its contestants played the 2026 online rounds and how many anchors
attended.  Run from the repository root (needs numpy + pypinyin).
"""
import argparse
import collections
import csv
import datetime
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_b import online_gold as og  # noqa: E402
import build_ec_online_data as bd  # noqa: E402
import ecfinal_chance as ecc  # noqa: E402

PTA = ("data/icpc_2026_ec_round1_teams.csv", "data/icpc_2026_ec_online_round2_teams.csv")
OUT = og.OUT / "anchor_teams.csv"
SEASON = "2026"
ECF_RANK = 75
THRESHOLD = 0.5
INDEX_URL = "https://board.xcpcio.com/data/index/contest_list.json"


def members(names):
    return frozenset(og.norm_name(m) for m in names if og.norm_name(m))


def same_team(school_a, members_a, school_b, members_b):
    return school_a == school_b and len(members_a & members_b) >= 2


def online_ranks(online_teams):
    """{round: {(school, team): rank}}, zero-solve teams at the unranked midpoint."""
    out = {}
    for rnd in ("1", "2"):
        rs = [r for r in online_teams if r["season"] == SEASON and r["round"] == rnd]
        ranked = sum(1 for r in rs if r["rank"])
        out[rnd] = {(og.norm_school(r["school"]), og.norm_name(r["team"])):
                    int(r["rank"]) if r["rank"] else (ranked + 1 + len(rs)) / 2 for r in rs}
    return out


def pool(data):
    """Teams in both 2026 online rounds, paired across rounds by PTA roster."""
    ranks = online_ranks(data["online_teams"])
    regs = []
    for path in PTA:
        with open(path, encoding="utf-8-sig") as f:
            regs.append([dict(r, s=og.norm_school(r["school_name_cn"]), t=og.norm_name(r["team_name"]),
                              m=members(r["members"].split("/"))) for r in csv.DictReader(f)])
    by_school = collections.defaultdict(list)
    for r in regs[1]:
        by_school[r["s"]].append(r)
    teams, used = [], set()
    for a in sorted(regs[0], key=lambda a: not any(b["t"] == a["t"] for b in by_school[a["s"]])):  # name matches first
        b = next((b for b in by_school[a["s"]] if id(b) not in used and b["t"] == a["t"]), None) or next(
            (b for b in by_school[a["s"]] if id(b) not in used and same_team(a["s"], a["m"], b["s"], b["m"])), None)
        if b is None or (a["s"], a["t"]) not in ranks["1"] or (b["s"], b["t"]) not in ranks["2"]:
            continue
        used.add(id(b))
        r1, r2 = ranks["1"][(a["s"], a["t"])], ranks["2"][(b["s"], b["t"])]
        teams.append({"school": b["school_name_cn"], "school_en": b["school_name_en"], "team": b["team_name"],
                      "team_en": b["team_name_en"], "round1_team": a["team_name"], "members": b["members"],
                      "s": b["s"], "m": a["m"] | b["m"], "rank1": r1, "rank2": r2,
                      "x": -float(np.mean(np.log([r1, r2])))})
    return teams


def gold_model(data, strengths):
    """P(gold | attends one mainland site) as a function of x, averaged over 2026 sites."""
    rows = og.model_rows(data, strengths)
    _, rho = og.quota_split(data, strengths, og.MODEL_SEASONS)
    lines = {k: og.rules_line(*k, data, strengths, rho) for k in {(r["season"], r["site"]) for r in rows}}
    w, _ = og.fit_final(rows, lines, n_boot=0)
    sites = [r["site"] for r in data["rules"].values() if r["season"] == 2026 and r.get("online_bands")]
    lines26 = [og.rules_line(SEASON, s, data, strengths, rho) for s in sites]
    return lambda x: float(np.mean([og.sigmoid(np.array([1, x, ln]) @ w) for ln in lines26]))


def ecfinal_model(data, strengths):
    """P(EC-Final seat | attends one mainland site), as in ``scripts/ecfinal_chance.py``."""
    ranks, _ = ecc.official_ranks()
    rows = []
    for r in og.link_regionals(data, strengths):
        k = (r["season"], r["site"], r["school"], r["team"])
        if r["season"] in og.MODEL_SEASONS and r["site"] not in og.EXCLUDED_SITES and r["link"] and k in ranks:
            rows.append(dict(r, rank=ranks[k]))
    w = ecc.fit(rows)
    return lambda x: sum(wk * ecc.prob(w, x, k) for k, wk in ecc.K_2026.items())


def actual_results(data, team):
    """Best 51st-season regional result so far: 'gold', 'ecfinal', 'none' or None (no regional yet)."""
    best = None
    for r in data["regional_teams"]:
        if r["season"] != SEASON or r["official"] != "1" or not same_team(
                team["s"], team["m"], og.norm_school(r["school"]), members(r["members"].split("|"))):
            continue
        if r["medal"] == "gold":
            return "gold"
        if r["site"] not in og.EXCLUDED_SITES and r["official_rank"] and int(r["official_rank"]) <= ECF_RANK:
            best = "ecfinal"
        best = best or "none"
    return best


def anchors():
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    p_gold, p_ecf = gold_model(data, strengths), ecfinal_model(data, strengths)
    teams = pool(data)
    for t in teams:
        t["p_gold"], t["p_ecfinal"] = round(p_gold(t["x"]), 4), round(p_ecf(t["x"]), 4)
        predicted = "gold" if t["p_gold"] >= THRESHOLD else "ecfinal" if t["p_ecfinal"] >= THRESHOLD else ""
        actual = actual_results(data, t)
        t["source"] = "actual" if actual else "predicted"
        t["tier"] = predicted if actual is None else "" if actual == "none" else actual
    return sorted(teams, key=lambda t: -t["x"])


FIELDS = ["tier", "source", "p_gold", "p_ecfinal", "rank1", "rank2", "school", "team", "round1_team",
          "members", "school_en", "team_en"]


def write(teams):
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(teams)


# ------------------------------------------------------------------ boards

def english_schools():
    """Normalized English school name -> normalized Chinese name, from the PTA registrations."""
    out = {}
    for path in PTA:
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out[og.norm_school(r["school_name_en"])] = og.norm_school(r["school_name_cn"])
    return out


def board_rows(link):
    kind, board = link.strip("/").split("/", 1)
    _, rows = bd.regional_standings(board, kind)
    en = english_schools()
    for r in rows:
        s = og.norm_school(r["school"])
        r["s"], r["m"] = en.get(s, s), members(r["members"].split("|"))
    return rows


def match(teams, rows):
    """One-to-one (anchor, board row) pairs: same school and >= 2 shared members (most shared first),
    then same school + team name for anchors and rows still unpaired."""
    by_school = collections.defaultdict(list)
    for r in rows:
        by_school[r["s"]].append(r)
    cands = [(len(t["m"] & r["m"]), i, j, t, r) for i, t in enumerate(teams) for j, r in enumerate(by_school[t["s"]])
             if same_team(t["s"], t["m"], r["s"], r["m"])]
    cands += [(0, i, j, t, r) for i, t in enumerate(teams) for j, r in enumerate(by_school[t["s"]])
              if og.norm_name(r["team"]) == og.norm_name(t["team"])]
    pairs, used_t, used_r = [], set(), set()
    for shared, _, _, t, r in sorted(cands, key=lambda c: (-c[0], c[1], c[2])):
        if id(t) not in used_t and id(r) not in used_r:
            used_t.add(id(t))
            used_r.add(id(r))
            pairs.append((t, r))
    return pairs


def compare(link, query, teams, result=None):
    """``result`` = (solved, penalty minutes) of a virtual run; else ``query`` names our team on the board."""
    rows = board_rows(link)
    if result:
        me = {"team": "virtual", "school": "-", "solved": result[0], "penalty_minutes": result[1]}
    else:
        ours = [r for r in rows if query in r["team"]]
        if len(ours) != 1:
            sys.exit(f"--team {query!r} matches {len(ours)} teams on {link}: {[r['team'] for r in ours][:10]}")
        me = ours[0]
    key = (-me["solved"], me["penalty_minutes"])
    print(f"{link}: {me['team']} ({me['school']}) solved {me['solved']}, penalty {me['penalty_minutes']}")
    pairs = match([t for t in teams if t["tier"]], rows)
    for tier in ("gold", "ecfinal"):
        hits = [(t, r) for t, r in pairs if t["tier"] == tier and r is not me]
        beat = sum((-r["solved"], r["penalty_minutes"]) > key for _, r in hits)
        tied = sum((-r["solved"], r["penalty_minutes"]) == key for _, r in hits)
        print(f"\n{tier} anchors present: {len(hits)}; beaten {beat}, tied {tied}, lost to {len(hits) - beat - tied}")
        for t, r in sorted(hits, key=lambda h: (-h[1]["solved"], h[1]["penalty_minutes"])):
            mark = "beat" if (-r["solved"], r["penalty_minutes"]) > key else "tie" if (
                -r["solved"], r["penalty_minutes"]) == key else "lost"
            print(f"  {mark:4s} {r['solved']:2d} {r['penalty_minutes']:5d}  {r['school']} {r['team']} "
                  f"(online #{t['rank1']:.0f}/#{t['rank2']:.0f}, P gold {t['p_gold']:.0%}, "
                  f"ECF {t['p_ecfinal']:.0%}, {t['source']})")


def boards_since(since):
    index = subprocess.run(["curl", "-sSfL", "--max-time", "120", INDEX_URL], check=True,
                           capture_output=True, text=True).stdout  # not cached: new boards appear
    out = []

    def walk(node):
        if isinstance(node, dict):
            if "board_link" in node and "config" in node:
                out.append(node)
                return
            for v in node.values():
                walk(v)
    walk(json.loads(index))
    for n in out:
        t = n["config"]["start_time"]
        n["start"] = datetime.date.fromtimestamp(t / 1000 if t > 1e11 else t)
    return sorted((n for n in out if n["start"] >= since and "warmup" not in n["board_link"]),
                  key=lambda n: n["start"])


def overlap(since, teams):
    online = collections.defaultdict(set)  # school -> members of any 2026 online team
    for path in PTA:
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                online[og.norm_school(r["school_name_cn"])] |= members(r["members"].split("/"))
    print("start      teams  online%  gold  ecfinal  board")
    for n in boards_since(since):
        try:
            rows = board_rows(n["board_link"])
        except Exception as e:  # unpublished or malformed board
            print(f"{n['start']}  skipped ({e.__class__.__name__})  {n['board_link']}")
            continue
        seen = sum(1 for r in rows if len(r["m"] & online[r["s"]]) >= 2 or (len(r["m"]) == 1 and r["m"] <= online[r["s"]]))
        tiers = collections.Counter(t["tier"] for t, _ in match([t for t in teams if t["tier"]], rows))
        print(f"{n['start']}  {len(rows):5d}  {seen / max(1, len(rows)):6.0%}  {tiers['gold']:4d}  "
              f"{tiers['ecfinal']:7d}  {n['board_link']}  {n['config']['contest_name']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", help="XCPCIO board link, e.g. ccpc/12th/harbin")
    ap.add_argument("--team", help="our team on --board (substring of its name)")
    ap.add_argument("--solved", type=int, help="instead of --team: solved count of a virtual run")
    ap.add_argument("--penalty", type=int, default=0, help="with --solved: penalty minutes")
    ap.add_argument("--overlap", action="store_true", help="list boards by overlap with the 2026 online field")
    ap.add_argument("--since", type=datetime.date.fromisoformat, default=datetime.date(2026, 3, 1))
    args = ap.parse_args()
    teams = anchors()
    write(teams)
    tiers = collections.Counter(t["tier"] for t in teams)
    print(f"{len(teams)} teams in both 2026 online rounds; anchors: gold {tiers['gold']}, "
          f"ecfinal {tiers['ecfinal']} -> {OUT.relative_to(og.ROOT)}")
    if args.board:
        compare(args.board, args.team or "", teams, None if args.solved is None else (args.solved, args.penalty))
    if args.overlap:
        overlap(args.since, teams)


if __name__ == "__main__":
    main()
