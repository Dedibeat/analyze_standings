#!/usr/bin/env python3
"""2026 EC-Final qualifying ranks, re-estimated from the finished regionals.

Mainland (230 seats, 7 sites).  The round-robin rule of ``ecfinal_cutoff.py`` is replayed on
the 2026 sites already played (``data/xcpcio_51st_regionals.json``).  The sites still to come
are added from history: in 2023-2025 the 6th site in calendar order admitted m6(d) teams within
rank d that the first five sites had not admitted; a 7th site never existed, so it gets
rho * m6(d), with rho around the position-to-position ratio seen at sites 4-6.  The cutoff is
the first rank tier d at which admitted(d) + late(d) >= 230.

Hong Kong (up to 10 places, medal teams in rank order; a team with a member on the mainland
list is skipped; a school gets at most 3 - x, x = its mainland seats).  The field is the
registration list of ``arch_b.hk_field_2026`` (round 1 = top 95 non-local teams by school
rank, plus local teams up to 20).  A team's Hong Kong rank is drawn from a model fitted on the
2024/2025 Hong Kong boards: logit(rank / field) on online strength x, plus the team's mainland
result where it has one.  Unlinked and unregistered local teams draw from the 2024/2025 teams of
the same kind.  The cutoff is the rank of the 10th eligible medal team.

    python scripts/ecfinal_cutoff_2026.py [--team NUM-R^3]
"""
import collections
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_b import hk_field_2026 as hf  # noqa: E402
from arch_b import hk_gold as hg  # noqa: E402
from arch_b import hk_link as hk  # noqa: E402
from arch_b import online_gold as og  # noqa: E402
import ecfinal_cutoff as ec  # noqa: E402

SEATS, HK_PLACES, HK_LOCAL_SEATS = 230, 10, 20
CALENDAR = {"2023": ["xian", "nanjing", "shenyang", "hefei", "jinan", "hangzhou"],
            "2024": ["chengdu", "nanjing", "hangzhou", "shanghai", "shenyang", "kunming"],
            "2025": ["xian", "chengdu", "wuhan", "nanjing", "shenyang", "shanghai"]}  # XCPCIO start dates
PLAYED_2026 = ["xian", "chengdu", "wuhan", "nanjing", "shenyang"]  # to come: shanghai 12-05, nanchang 12-19
RHOS = (0.5, 0.7, 0.9)
SIMS = 4000


def norm(s):
    return re.sub(r"\s+", "", s or "").lower()


def keys(t):
    """Identity of a team for the shared-member rule: (school, member), or the team name without members."""
    school = og.norm_school(t["school"])
    return {(school, m) for m in t["members"]} or {(school, "#" + norm(t["team"]))}


def history_sites(season):
    sites = collections.defaultdict(list)
    for x in ec.ROWS:
        if x["season"] == season and x["official"] == "1" and x["official_rank"] and x["site"] in CALENDAR[season]:
            sites[x["site"]].append(dict(rank=int(x["official_rank"]), school=x["school"], team=x["team"],
                                         members=sorted(ec.members(x)), solved=int(x["solved"] or 0)))
    for rows in sites.values():
        rows.sort(key=lambda t: t["rank"])
    return sites


def sites_2026():
    """Official rows of the played 2026 sites.  Xi'an's board has no members: they are taken from
    the same school + team name on another 2026 board, else on a 2026 online roster."""
    rosters = collections.defaultdict(set)
    for r in og.load()["online_rosters"]:
        if r["season"] == "2026":
            rosters[(og.norm_school(r["school"]), norm(r["team"]))].update(m for m in r["members"].split("|") if m)
    sites = {}
    for c in json.load(open("data/xcpcio_51st_regionals.json", encoding="utf-8")):
        site = c["board_link"].rsplit("/", 1)[1]
        if site in PLAYED_2026:
            rows = sorted((r for r in c["standings"] if r["official"]), key=lambda r: r["rank"])
            sites[site] = [dict(rank=i, school=r["affiliation"], team=r["team_name"], members=list(r["members"]),
                                solved=r["total_solved"]) for i, r in enumerate(rows, 1)]
    boards = collections.defaultdict(set)
    for rows in sites.values():
        for t in rows:
            boards[(og.norm_school(t["school"]), norm(t["team"]))].update(t["members"])
    for t in sites["xian"]:
        k = (og.norm_school(t["school"]), norm(t["team"]))
        t["members"] = sorted(boards[k] or rosters.get(k, ()))
    return sites


def replay(sites, max_depth=140):
    """Admitted teams after each rank tier with unlimited seats: ({tier: count}, [(tier, site, team)])."""
    order = sorted(sites, key=lambda s: -sum(t["solved"] > 0 for t in sites[s]))
    used, per_school, taken, counts = set(), collections.Counter(), [], {}
    for k in range(max_depth):
        for s in order:
            if k >= len(sites[s]):
                continue
            t = sites[s][k]
            if keys(t) & used or per_school[og.norm_school(t["school"])] >= 3:
                continue
            used |= keys(t)
            per_school[og.norm_school(t["school"])] += 1
            taken.append((k + 1, s, t))
        counts[k + 1] = len(taken)
    return counts, taken


def mainland(team):
    sites = sites_2026()
    now, taken = replay(sites)
    blind = sum(not t["members"] for t in sites["xian"][:100])
    print(f"2026 sites played: " + ", ".join(f"{s} {len(sites[s])}" for s in PLAYED_2026)
          + f"; Xi'an teams in its top 100 without members (matched by name only): {blind}")
    late, ratios = {}, []
    print("\nadmitted within rank d by the first j sites (calendar order)")
    print("  season  j=5: d=70  75  80  85  90 | 6th site adds: d=70  75  80  85  90")
    for season, cal in CALENDAR.items():
        hist = history_sites(season)
        first = [replay({s: hist[s] for s in cal[:j]})[0] for j in (3, 4, 5, 6)]
        late[season] = {d: first[3][d] - first[2][d] for d in first[3]}
        ratios += [(first[j + 1][80] - first[j][80]) / (first[j][80] - first[j - 1][80]) for j in (1, 2)]
        print(f"  {season}        " + " ".join(f"{first[2][d]:3}" for d in (70, 75, 80, 85, 90))
              + "               " + " ".join(f"{late[season][d]:3}" for d in (70, 75, 80, 85, 90)))
    print("  2026        " + " ".join(f"{now[d]:3}" for d in (70, 75, 80, 85, 90)))
    print(f"  site j+1 adds this share of what site j added (d = 80, sites 4-6): "
          + ", ".join(f"{r:.2f}" for r in ratios) + f"; mean {np.mean(ratios):.2f}")

    cutoffs = {}
    print(f"\nrank tier of the {SEATS}th seat: 6th site as in each season, 7th site = rho x the 6th")
    for season in CALENDAR:
        for rho in RHOS:
            cutoffs[(season, rho)] = next(d for d in now if now[d] + (1 + rho) * late[season][d] >= SEATS)
        print(f"  6th site as {season}: " + ", ".join(f"rho {rho} -> {cutoffs[(season, rho)]}" for rho in RHOS))
    v = sorted(cutoffs.values())
    print(f"  median {v[len(v) // 2]}, range {v[0]}-{v[-1]}; with no further admits at all: "
          f"{next(d for d in now if now[d] >= SEATS)}")
    mine = next(((s, t) for s in sites for t in sites[s] if t["team"] == team), None)
    if mine:
        d = mine[1]["rank"]
        need = SEATS - 1 - now[d - 1]
        got = sorted(round((1 + rho) * late[season][d - 1], 1) for season in CALENDAR for rho in RHOS)
        print(f"\n{team}: {mine[0]} #{d}. A seat needs the two remaining sites to admit at most {need} new teams "
              f"within rank {d - 1}; the scenarios give {got[0]}-{got[-1]}.")
    return taken, v[len(v) // 2], (v[0], v[-1])


def hk_history():
    """2024/2025 Hong Kong teams with the replayed 2026-rule eligibility (as ecfinal_chance.hk_depth)."""
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    size = collections.Counter((r["season"], r["site"]) for r in ec.ROWS if r["official"] == "1" and r["official_rank"])
    rank = {(r["season"], r["site"], r["school"], r["team"]): int(r["official_rank"])
            for r in ec.ROWS if r["official"] == "1" and r["official_rank"]}
    main, admitted, seats = collections.defaultdict(list), set(), collections.Counter()
    linked = og.link_regionals(data, strengths)
    for season in ("2024", "2025"):
        taken = ec.admits_by_depth(season)[2][:239 if season == "2025" else 240]
        key = {(r["school"], r["team"]): r["online_key"] for r in linked if r["season"] == season}
        admitted |= {key.get((t["school"], t["team"])) for t in taken}
        seats.update((season, og.norm_school(t["school"])) for t in taken)
    for r in linked:
        k = (r["season"], r["site"], r["school"], r["team"])
        if r["link"] and k in rank and r["site"] not in ec.NON_MAINLAND:
            main[r["online_key"]].append(share(rank[k], size[k[:2]]))
    rows = []
    for r in hk.link_hk(data, strengths):
        if r["site"] == "hongkong" and r["season"] in ("2024", "2025"):
            key = (r["season"], r["online_school"], r["online_team"]) if r["online_school"] else None
            school = r["online_school"] or og.norm_school(r["school"])
            m = main.get(key, [])
            rows.append(dict(season=r["season"], rank=int(r["official_rank"]), medal=bool(r["medal"]), x=r["x"],
                             y=share(int(r["official_rank"]), size[(r["season"], "hongkong")]),
                             main=float(np.mean(m)) if m else None, local=hg.is_local(r["school"]),
                             skip=key is not None and key in admitted, school_key=school,
                             school_seats=seats[(r["season"], school)]))
    return rows


def share(rank, n):
    return math.log((rank - 0.5) / (n - rank + 0.5))


def hk_model(rows):
    def ols(sel, cols):
        y = np.array([r["y"] for r in sel])
        X = np.column_stack([np.ones(len(sel))] + [[r[c] for r in sel] for c in cols])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        return b, float((y - X @ b).std(ddof=X.shape[1])), len(sel)

    linked = [r for r in rows if r["x"] is not None]
    return dict(with_main=ols([r for r in linked if r["main"] is not None], ("x", "main")),
                online=ols([r for r in linked if r["main"] is None], ("x",)),
                unlinked={local: [r["y"] for r in rows if r["x"] is None and r["local"] == local] for local in (True, False)},
                local_all=[r["y"] for r in rows if r["local"]])


def simulate(teams, model, phantom, medals, me=None, seed=1):
    """Draw Hong Kong ranks SIMS times; walk the medal ranks giving HK_PLACES places under the 2026 rule.
    ``phantom`` extra local teams (not on the list) draw from the past local teams."""
    rng = np.random.default_rng(seed)
    mu, sd, pool = np.zeros(len(teams)), np.zeros(len(teams)), {}
    for i, t in enumerate(teams):
        if t["x"] is None:
            pool[i] = model["unlinked"][t["local"]]
        elif t["main"] is not None:
            b, sd[i], _ = model["with_main"]
            mu[i] = b[0] + b[1] * t["x"] + b[2] * t["main"]
        else:
            b, sd[i], _ = model["online"]
            mu[i] = b[0] + b[1] * t["x"]
    out = dict(cut=[], skipped=[], local=[], rank=[], place=0)
    for _ in range(SIMS):
        y = mu + sd * rng.standard_normal(len(teams))
        for i, p in pool.items():
            y[i] = rng.choice(p)
        order = np.argsort(np.concatenate([y, rng.choice(model["local_all"], phantom)]))
        got, last, skipped, local = collections.Counter(), medals, 0, 0
        for pos, i in enumerate(order[:medals], 1):
            t = teams[i] if i < len(teams) else None
            if t and (t["skip"] or t["school_seats"] + got[t["school_key"]] >= 3):
                skipped += 1
                continue
            got[t["school_key"] if t else f"local{i}"] += 1
            local += not t or t["local"]
            out["place"] += me is not None and i == me
            if sum(got.values()) == HK_PLACES:
                last = pos
                break
        out["cut"].append(last)
        out["skipped"].append(skipped)
        out["local"].append(local)
        if me is not None:
            out["rank"].append(int(np.where(order == me)[0][0]) + 1)
    return out


def quantiles(v):
    q = np.percentile(v, [10, 25, 50, 75, 90]).round().astype(int).tolist()
    return f"median {q[2]}, 25-75% {q[1]}-{q[3]}, 10-90% {q[0]}-{q[4]}"


def backtest(rows):
    """Fit on one season, simulate the other with its real eligibility; compare with the board's replay."""
    print("\nHong Kong backtest: rank of the 10th eligible medal team under the 2026 rule")
    for season, other in (("2024", "2025"), ("2025", "2024")):
        field = [r for r in rows if r["season"] == season]
        got, real = collections.Counter(), None
        for r in sorted(field, key=lambda r: r["rank"]):
            if r["medal"] and not r["skip"] and r["school_seats"] + got[r["school_key"]] < 3:
                got[r["school_key"]] += 1
                if sum(got.values()) == HK_PLACES:
                    real = r["rank"]
                    break
        sim = simulate(field, hk_model([r for r in rows if r["season"] == other]), 0, sum(r["medal"] for r in field))
        print(f"  {season} ({len(field)} teams, {sum(r['skip'] for r in field)} with a mainland seat): board {real}; "
              f"simulated from the {other} model {quantiles(sim['cut'])}")


def hong_kong(taken, depth, team, rows):
    """Hong Kong rank of the 10th eligible medal team, given mainland qualifiers down to ``depth``."""
    res = hf.run(teams=())
    reg = res["teams"] + res["unlinked"]
    round1 = sorted((r for r in reg if r["round1"] and not r["local"]), key=lambda r: r["school_rank"] or math.inf)
    field = round1[:hf.NONLOCAL_SEATS] + [r for r in reg if r["local"]]
    qualified, seats = set(), collections.Counter()
    for tier, _, t in taken:
        if tier <= depth:
            qualified |= keys(t)
            seats[og.norm_school(t["school"])] += 1
    result = {}  # member -> logit rank shares at the played 2026 sites
    for site in sites_2026().values():
        for t in site:
            for k in keys(t):
                result.setdefault(k, []).append(share(t["rank"], len(site)))
    teams = []
    for r in field:
        t = dict(school=r["school"], team=r["team"], members=[m for m in re.split(r"[/|]", r["members"] or "") if m])
        m = [v for k in keys(t) for v in result.get(k, [])]
        teams.append(dict(t, x=r["x"], local=r["local"], main=float(np.mean(m)) if m else None,
                          skip=bool(keys(t) & qualified), school_key=og.norm_school(r["school"]),
                          school_seats=seats[og.norm_school(r["school"])]))
    phantom = max(0, HK_LOCAL_SEATS - sum(t["local"] for t in teams))
    n = len(teams) + phantom
    medals = round(0.6 * n)
    me = next((i for i, t in enumerate(teams) if t["team"] == team), None)
    sim = simulate(teams, hk_model(rows), phantom, medals, me)
    print(f"\nHong Kong, mainland seats down to rank {depth}: field {sum(not t['local'] for t in teams)} non-local "
          f"(round 1 by school rank) + {sum(t['local'] for t in teams)} registered local + {phantom} local teams "
          f"not on the list = {n}, medals to rank {medals}")
    print(f"  {sum(t['skip'] for t in teams)} field teams hold a mainland seat, "
          f"{sum(not t['skip'] and t['school_seats'] >= 3 for t in teams)} more are from schools with 3 seats; "
          f"{sum(t['main'] is not None for t in teams)} have a 2026 mainland result, "
          f"{sum(t['x'] is None for t in teams)} have no online link")
    print(f"  rank of the 10th eligible medal team: {quantiles(sim['cut'])}; teams skipped above it: median "
          f"{int(np.median(sim['skipped']))}; places taken by local teams: mean {np.mean(sim['local']):.1f}")
    if me is not None:
        r = np.percentile(sim["rank"], [10, 50, 90]).round().astype(int).tolist()
        print(f"  {team}: predicted Hong Kong rank median {r[1]} (10-90% {r[0]}-{r[2]}); takes one of the "
              f"{HK_PLACES} places in {sim['place'] / SIMS:.0%} of the draws"
              + (" (already holds a mainland seat)" if teams[me]["skip"] else ""))


def main():
    team = sys.argv[sys.argv.index("--team") + 1] if "--team" in sys.argv else "NUM-R^3"
    taken, depth, (lo, hi) = mainland(team)
    rows = hk_history()
    for b, sd, k in (hk_model(rows)[m] for m in ("with_main", "online")):
        print(f"\nHong Kong rank model on 2024/2025 ({k} teams): coefficients {np.round(b, 3).tolist()}, residual SD {sd:.2f}", end="")
    print()
    backtest(rows)
    for d in sorted({lo, depth, hi}):
        hong_kong(taken, d, team, rows)


if __name__ == "__main__":
    main()
