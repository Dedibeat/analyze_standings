"""The 2026 Hong Kong field from its registration list, linked to online results.

The PTA export of the Hong Kong (港澳) registration (round 1: one team per
non-local school until 2026-10-30, 95 non-local seats, picked by online rank if
more register) lists members in Chinese, so each line-up links to the 2026
online rosters directly: per online round, the team of the same school sharing
>= 2 members, else the same school + team name. A line-up renamed between the
rounds keeps both ranks.

The 10-15 / 10-17 exports are CSVs. From 10-23 (``data/icpc_hk_macau_public_teams_20261023.xlsx``)
it is an xlsx with English school names, no creation time and an "Online
ranking" column, which is the school's 2026 combined online rank
(``online_schools.csv``): the round-1 cut is by school, so a line-up with no
online result of its own still has a rank.
For a team (``--team``) it gives the chance of the round-1 cut from the pace at
which schools ranked above it registered between the last two ``SNAPSHOTS``.

It compares that field with the 2024 / 2025 Hong Kong fields (``arch_b.hk_link``)
and gives each registered team its gold / silver / bronze chance from two Hong
Kong models fit on 2024 + 2025, both tested on the other year:

* absolute: ``logit P(medal >= k) = c_k + b_k x`` (``arch_b.online_medals``);
* field-relative: ``logit P(medal >= k) = c_k + b_k (x - line_k)``, where
  ``line_k`` is the linked team at 10% / 30% / 60% of the field's linked teams,
  so a stronger field lowers every chance.

    python3 -m arch_b.hk_field_2026 [--team NUM-R^3]

Writes ``output/hk_field_2026.json`` and ``output/hk_field_2026.md``.
"""

import argparse
import collections
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from arch_b import hk_gold as hg
from arch_b import hk_link as hk
from arch_b import online_gold as og
from arch_b import online_medals as om

REGISTRATION = og.ROOT / "data" / "icpc_hk_macau_public_teams_20261026.xlsx"  # 10-26 export
SNAPSHOTS = {  # export -> when taken (UTC): a CSV's last registration, an xlsx file name's stamp (UTC+8)
    "icpc_51_asia_hkmo_teams.csv": "2026-10-15T05:12",
    "icpc_hk_macau_regional_teams.csv": "2026-10-17T14:30",
    "icpc_hk_macau_public_teams_20261023.xlsx": "2026-10-23T14:45",
    "icpc_hk_macau_public_teams_20261026.xlsx": "2026-10-26T11:53",
}
ROUND1_CLOSE = "2026-10-30T16:00"  # end of 10-30 in UTC+8 (the notice gives the date only)
PACES = (1, 2, 3)
HK_EXPORTS = [og.ROOT / "data" / n for n in ("icpc_51_asia_hkmo_teams.csv", "icpc_hk_macau_regional_teams.csv")]
PTA_EXPORTS = [og.ROOT / "data" / n for n in ("icpc_2026_ec_round1_teams.csv", "icpc_2026_ec_online_round2_teams.csv")] \
    + HK_EXPORTS  # PTA CSVs: English school name -> Chinese name and province
NONLOCAL_SEATS = 95
COUNT_RANKS = (50, 100, 200, 500)
LOCAL_PROVINCES = ("香港特别行政区", "澳门特别行政区")


def pta_schools():
    """{English school name: (Chinese name, province)} from the PTA CSV exports."""
    out = {}
    for p in PTA_EXPORTS:
        with open(p, encoding="utf-8-sig") as f:
            out.update({r["school_name_en"]: (r["school_name_cn"], r["school_province"]) for r in csv.DictReader(f)})
    return out


def lineup(school, members):
    return og.norm_school(school), frozenset(og.norm_name(m) for m in members.split("/") if m.strip())


def read_registration(path):
    """Rows with the PTA CSV columns. For the xlsx export the Chinese school name and province come from the PTA
    CSVs with the same English name, and created_at from an earlier Hong Kong export listing the same line-up
    (blank for a team new since)."""
    if Path(path).suffix != ".xlsx":
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    import openpyxl
    schools, created = pta_schools(), {}
    for p in HK_EXPORTS:
        with open(p, encoding="utf-8-sig") as f:
            created.update({lineup(r["school_name_cn"], r["members"]): r["created_at"] for r in csv.DictReader(f)})
    head, *rows = openpyxl.load_workbook(path, read_only=True).active.iter_rows(values_only=True)
    out = []
    for r in (dict(zip(head, v)) for v in rows):
        cn, province = schools[r["School"]]  # KeyError: an English school name no PTA export has
        members = "/".join(m.replace("(Team Leader)", "").strip() for m in r["Team members"].split("/"))
        out.append(dict(team_name=r["Team name"], team_name_en=r["English team name"], school_name_cn=cn,
                        school_name_en=r["School"], school_province=province, members=members,
                        review_status=r["Review status"], online_ranking=r["Online ranking"],
                        created_at=created.get(lineup(cn, members), "")))
    return out


def round_ranks(online_teams, season="2026"):
    """{(round, school, team): rank}; unranked teams get the midpoint of the
    unranked tail, as in ``online_gold.online_strengths``."""
    by_round = collections.defaultdict(list)
    for r in online_teams:
        if r["season"] == season:
            by_round[r["round"]].append(r)
    out = {}
    for rnd, rs in by_round.items():
        ranked = sum(1 for r in rs if r["rank"])
        for r in rs:
            out[(rnd, og.norm_school(r["school"]), og.norm_name(r["team"]))] = \
                int(r["rank"]) if r["rank"] else (ranked + 1 + len(rs)) / 2
    return out


def binom_tail(groups, k):
    """P(sum of independent Binomial(n, p) over (n, p) in ``groups`` >= k)."""
    pmf = np.array([1.0])
    for n, p in groups:
        pmf = np.convolve(pmf, [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)])
    return float(pmf[k:].sum())


def cut_risk(path, top, past_hk, room):
    """Chance that more than ``room`` of the schools in ``top`` (non-local, better school rank) not registered yet
    register before round 1 closes. Each registers at its group's per-day rate between the last two snapshots
    (groups: had a 2024/2025 Hong Kong team or not), carried to the close at 1x / 2x / 3x that rate; the last
    row has every past-Hong Kong school return. None without an earlier snapshot."""
    names = list(SNAPSHOTS)
    if Path(path).name not in names[1:]:
        return None
    names = names[names.index(Path(path).name) - 1:][:2]
    t0, t1, close = (datetime.fromisoformat(v) for v in (SNAPSHOTS[names[0]], SNAPSHOTS[names[1]], ROUND1_CLOSE))
    reg0, reg1 = ({og.norm_school(r["school_name_cn"]) for r in read_registration(og.ROOT / "data" / n)} for n in names)
    days, left = (t1 - t0).total_seconds() / 86400, max(0.0, (close - t1).total_seconds() / 86400)
    groups = {}
    for g, schools in (("past_hk", top & past_hk), ("other", top - past_hk)):
        before, after = len(schools - reg0), len(schools - reg1)
        groups[g] = dict(schools=len(schools), unregistered=after, registered_since=before - after,
                         per_day=math.log(before / after) / days if after else 0.0)
    rows = []
    for name, ps in [(f"{k}x the pace", {g: 1 - math.exp(-k * v["per_day"] * left) for g, v in groups.items()})
                     for k in PACES] + [(f"every past-HK school, others at {PACES[-1]}x", {"past_hk": 1.0, "other": 1 - math.exp(
                         -PACES[-1] * groups["other"]["per_day"] * left)})]:
        n = [(groups[g]["unregistered"], ps[g]) for g in groups]
        rows.append(dict(assumption=name, p_past_hk=round(ps["past_hk"], 3), p_other=round(ps["other"], 3),
                         expected_new=round(sum(a * b for a, b in n), 1), p_cut=round(binom_tail(n, room + 1), 4)))
    # If every past-Hong Kong school returns: the chance per other school that gives a 5% / 50% cut.
    k, n = room + 1 - groups["past_hk"]["unregistered"], groups["other"]["unregistered"]
    break_even = {}
    for target in (0.05, 0.5):
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if binom_tail([(n, mid)], k) < target else (lo, mid)
        break_even[str(target)] = round(hi, 3)
    return dict(since=names[0], days=round(days, 2), days_left=round(left, 2), need=room + 1, groups=groups,
                scenarios=rows, others_needed=k, break_even_p_other=break_even)


def school_ranks(data, season="2026"):
    return {og.norm_school(r["school"]): int(r["rank"]) for r in data["online_schools"]
            if r["season"] == season and r["table"] == "combined"}


def link_registered(reg, data, season="2026"):
    ranks, school_rank = round_ranks(data["online_teams"], season), school_ranks(data, season)
    rosters = collections.defaultdict(list)  # (round, school) -> [(team, members)]
    for r in data["online_rosters"]:
        if r["season"] == season:
            rosters[(r["round"], og.norm_school(r["school"]))].append(
                (og.norm_name(r["team"]), {og.norm_name(m) for m in r["members"].split("|") if m}))
    out = []
    for r in reg:
        school, team = og.norm_school(r["school_name_cn"]), og.norm_name(r["team_name"])
        members = {og.norm_name(m) for m in r["members"].split("/") if m.strip()}
        linked = {}
        for rnd in sorted({k[0] for k in ranks}):
            votes = sorted(((len(members & ms), t) for t, ms in rosters[(rnd, school)]
                            if (rnd, school, t) in ranks), reverse=True)
            if votes and votes[0][0] >= 2:
                linked[rnd] = (votes[0][1], ranks[(rnd, school, votes[0][1])], "members")
            elif (rnd, school, team) in ranks:
                linked[rnd] = (team, ranks[(rnd, school, team)], "name")
        rk = [v[1] for v in linked.values()]
        out.append(dict(school=r["school_name_cn"], school_en=r["school_name_en"], team=r["team_name"],
                        members=r["members"], status=r["review_status"], created=r["created_at"],
                        local=r["school_province"] in LOCAL_PROVINCES,
                        school_rank=school_rank.get(school), export_rank=r.get("online_ranking"),
                        online_teams={k: v[0] for k, v in linked.items()},
                        online_ranks={k: v[1] for k, v in linked.items()},
                        link="+".join(sorted({v[2] for v in linked.values()})),
                        x=-float(np.mean(np.log(rk))) if rk else None))
    return out


def lines(xs):
    xs = sorted(xs, reverse=True)
    return {name: xs[max(1, round(frac * len(xs))) - 1] for name, frac, _ in om.LEVELS}


def fit(rows, relative):
    """Per level: coefficients of [1, x] or [1, x - line] on 2024/2025 linked rows."""
    by_season = {s: lines([r["x"] for r in rows if r["season"] == s]) for s in {r["season"] for r in rows}}
    return {name: og.logistic([[1, r["x"] - (by_season[r["season"]][name] if relative else 0)] for r in rows],
                              [om.won(medals)(r) for r in rows], l2=1e-2)
            for name, _, medals in om.LEVELS}


def predict(w, x, line=None):
    cum = np.array([og.sigmoid(w[n] @ [1, x - (line[n] if line else 0)]) for n, _, _ in om.LEVELS])
    p = om.class_probs(cum)
    return {c: round(float(p[i]), 4) for i, c in enumerate(om.CLASSES[:3])}


def backtest(rows):
    """Train one season, test the other: log loss and expected counts per level."""
    out = {}
    for test in om.HK_SEASONS:
        te, tr = [r for r in rows if r["season"] == test], [r for r in rows if r["season"] != test]
        line = lines([r["x"] for r in te])
        res = {}
        for name, _, medals in om.LEVELS:
            y = np.array([om.won(medals)(r) for r in te])
            res[name] = {"actual": int(y.sum())}
            for model, relative in (("absolute", False), ("field_relative", True)):
                w = fit(tr, relative)[name]
                p = og.sigmoid(np.array([[1, r["x"] - (line[name] if relative else 0)] for r in te]) @ w)
                res[name][model] = {"log_loss": round(float(om.log_loss(p, y).mean()), 4),
                                    "expected": round(float(p.sum()), 1)}
        out[test] = res
    return out


def field_row(label, xs, teams, nonlocal_, line_w=None):
    ranks = sorted(math.exp(-x) for x in xs)
    ln = lines(xs)
    row = dict(field=label, teams=teams, nonlocal_teams=nonlocal_, linked=len(xs),
               median_online_rank=round(float(np.median(ranks)), 1),
               within={k: sum(q <= k for q in ranks) for k in COUNT_RANKS},
               line_online_rank={n: round(math.exp(-v), 1) for n, v in ln.items()})
    if line_w:  # expected golds / silver+ / medals among linked teams under the absolute model
        row["expected_absolute"] = {n: round(float(sum(og.sigmoid(line_w[n] @ [1, x]) for x in xs)), 1)
                                    for n, _, _ in om.LEVELS}
    return row


def run(path=REGISTRATION, teams=("NUM-R^3",)):
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    hk_all = hk.link_hk(data, strengths)
    past = [r for r in hk_all if r["season"] in om.HK_SEASONS and r["x"] is not None]
    reg = link_registered(read_registration(path), data)
    w_abs, w_rel = fit(past, False), fit(past, True)

    first = {}  # round 1 takes one team per school: the earliest registered; later ones wait for round 2
    for r in sorted(reg, key=lambda r: (not r["created"], r["created"])):  # no time (new since the CSVs): later
        r["round1"] = first.setdefault(r["school"], r) is r
    linked = [r for r in reg if r["x"] is not None]
    # Round 1 keeps the top 95 non-local teams by school rank (2026 combined online rank), linked or not.
    round1 = sorted((r for r in reg if r["round1"] and not r["local"]), key=lambda r: r["school_rank"] or math.inf)
    registered = {og.norm_school(r["school"]) for r in reg}
    # Scenario: every 2025 non-local school not registered yet comes back with a team as strong as its
    # 2025 Hong Kong team (2025 online ranks), and round 1 keeps the top 95 by school rank.
    late = {}
    for r in past:
        if r["season"] == "2025" and not hg.is_local(r["school"]) and r["online_school"] not in registered:
            late[r["online_school"]] = max(late.get(r["online_school"], -math.inf), r["x"])
    ranks = school_ranks(data)
    pool = sorted([(r["school_rank"] or math.inf, r["x"]) for r in round1]
                  + [(ranks.get(s, math.inf), x) for s, x in late.items()], key=lambda p: p[0])
    scenario = [x for _, x in pool[:NONLOCAL_SEATS] if x is not None]
    line_reg, line_sc = lines([r["x"] for r in linked]), lines(scenario)
    field = [field_row(f"{s} hongkong (official)", [r["x"] for r in past if r["season"] == s],
                       sum(r["season"] == s for r in hk_all),
                       sum(r["season"] == s and not hg.is_local(r["school"]) for r in hk_all), w_abs)
             for s in om.HK_SEASONS]
    field.append(field_row("2026 registered so far", [r["x"] for r in linked], len(reg),
                           sum(not r["local"] for r in reg), w_abs))
    field.append(field_row(f"2026 scenario: + {len(late)} unregistered 2025 schools, top {NONLOCAL_SEATS} by school rank",
                           scenario, NONLOCAL_SEATS, NONLOCAL_SEATS, w_abs))

    order = sorted(linked, key=lambda r: -r["x"])
    for i, r in enumerate(order, 1):
        r.update(field_position=i, mean_online_rank=round(math.exp(-r["x"]), 1),
                 best_online_rank=min(r["online_ranks"].values()),
                 scenario_position=1 + sum(k < r["school_rank"] for k, _ in pool) if r in round1 else None,
                 absolute=predict(w_abs, r["x"]), field_relative_registered=predict(w_rel, r["x"], line_reg),
                 field_relative_scenario=predict(w_rel, r["x"], line_sc))

    provinces = {og.norm_school(cn): p for cn, p in pta_schools().values()}
    smap = hk.school_map()  # schools with a 2024/2025 Hong Kong team, linked or by the board's English name
    past_hk = {r["online_school"] or smap.get(hk.norm_school_en(r["school"]))
               for r in hk_all if r["season"] in om.HK_SEASONS} - {None}
    selection = {}  # round 1 picks by school rank if more than 95 non-local teams register
    for t in teams:
        r = next((q for q in linked if q["team"] == t), None)
        if r is not None:
            ahead = sum((q["school_rank"] or math.inf) < r["school_rank"] for q in round1)
            top = {s for s, k in ranks.items() if k < r["school_rank"] and provinces.get(s) not in LOCAL_PROVINCES}
            selection[t] = dict(
                school_rank=r["school_rank"], best_online_rank=r["best_online_rank"],
                mean_online_rank=r["mean_online_rank"], ahead=ahead, room=NONLOCAL_SEATS - 1 - ahead,
                unregistered_ahead=len(top - registered),
                scenario_position=r["scenario_position"], scenario_pool=len(pool),
                scenario_cut_school_rank=pool[:NONLOCAL_SEATS][-1][0],
                cut_risk=cut_risk(path, top, past_hk, NONLOCAL_SEATS - 1 - ahead))

    kept, cut = round1[:NONLOCAL_SEATS], round1[NONLOCAL_SEATS:]  # if round 1 closed now
    cut_now = dict(round1_nonlocal=len(round1), unlinked=sum(r["x"] is None for r in round1), cut=len(cut),
                   last_kept_school_rank=kept[-1]["school_rank"],
                   first_cut_school_rank=cut[0]["school_rank"] if cut else None,
                   cut_teams=[(r["school"], r["team"], r["school_rank"]) for r in cut])
    rank_check = dict(rows=sum(r["export_rank"] is not None for r in reg),
                      mismatches=[(r["school"], r["team"], r["export_rank"], r["school_rank"]) for r in reg
                                  if r["export_rank"] is not None and r["export_rank"] != r["school_rank"]])

    # Schools of the 2024/2025 fields not registered yet (non-local, linked).
    missing = collections.defaultdict(list)
    for r in past:
        if not hg.is_local(r["school"]) and r["online_school"] not in registered:
            missing[r["online_school"]].append(f"{r['season']} #{r['official_rank']} {r['medal'] or '-'}")
    returning = {s: len({r["online_school"] for r in past if r["season"] == s and not hg.is_local(r["school"])}
                        & registered) for s in om.HK_SEASONS}
    return dict(file=Path(path).name, registered=len(reg),
                extra_teams=[(r["school"], r["team"]) for r in reg if not r["round1"] and not r["local"]],
                status=dict(collections.Counter(r["status"] for r in reg)),
                created=[min(r["created"] for r in reg if r["created"]), max(r["created"] for r in reg if r["created"])],
                created_unknown=sum(not r["created"] for r in reg), rank_check=rank_check,
                link=dict(collections.Counter(r["link"] or "unlinked" for r in reg)),
                field=field, backtest=backtest(past),
                lines_registered={n: round(math.exp(-v), 1) for n, v in line_reg.items()},
                lines_scenario={n: round(math.exp(-v), 1) for n, v in line_sc.items()},
                teams=order, unlinked=[r for r in reg if r["x"] is None], selection=selection, cut_now=cut_now,
                returning_schools=returning,
                missing_medal_schools={s: v for s, v in sorted(missing.items())
                                       if any("gold" in e or "silver" in e for e in v)})


def pct(d):
    return " / ".join(f"{d[c]:.0%}" for c in om.CLASSES[:3])


def markdown(res):
    L = ["# 2026 Hong Kong registration list vs online results", "",
         f"`arch_b.hk_field_2026` on `{res['file']}`: {res['registered']} teams, registered "
         f"{res['created'][0][:10]} – {res['created'][1][:10]} ({', '.join(f'{k} {v}' for k, v in res['status'].items())}"
         + (f"; {res['created_unknown']} new since the last CSV export, with no creation time" if res["created_unknown"] else "")
         + "). "
         "Online rank = exp(mean log rank) over the online rounds the line-up played (matched per round by >= 2 "
         "members at the same school, else by name). Links: " +
         ", ".join(f"{k} {v}" for k, v in sorted(res["link"].items())) + ".", "",
         "## Field", "",
         "| field | teams | non-local | linked | median online rank | linked within online #50 / #100 / #200 / #500 | "
         "10% / 30% / 60% line (online rank) | expected gold / silver+ / medal (absolute model) |",
         "|---|---|---|---|---|---|---|---|"]
    for f in res["field"]:
        e = f.get("expected_absolute", {})
        L.append(f"| {f['field']} | {f['teams']} | {f['nonlocal_teams']} | {f['linked']} | {f['median_online_rank']} | "
                 + " / ".join(str(f["within"][k]) for k in COUNT_RANKS) + " | "
                 + " / ".join(str(f["line_online_rank"][n]) for n, _, _ in om.LEVELS) + " | "
                 + " / ".join(str(e.get(n, "-")) for n, _, _ in om.LEVELS) + " |")
    L += ["", f"Returning non-local schools already registered: {res['returning_schools']['2024']} of the 2024 field, "
          f"{res['returning_schools']['2025']} of the 2025 field.", "",
          "2024/2025 gold or silver schools not registered yet: " +
          "; ".join(f"{s} ({', '.join(v)})" for s, v in res["missing_medal_schools"].items()) + ".", "",
          "## Models (train one season, test the other)", "",
          "| test | level | actual | absolute: log loss (expected) | field-relative: log loss (expected) |",
          "|---|---|---|---|---|"]
    for s, b in res["backtest"].items():
        for n, _, _ in om.LEVELS:
            v = b[n]
            L.append(f"| {s} | {n} | {v['actual']} | {v['absolute']['log_loss']} ({v['absolute']['expected']}) | "
                     f"{v['field_relative']['log_loss']} ({v['field_relative']['expected']}) |")
    ln = lambda d: " / #".join(str(d[n]) for n, _, _ in om.LEVELS)  # noqa: E731
    L += ["", "## Registered teams by online strength", "",
          "Gold / silver / bronze, conditional on attending. Field-relative with the lines of the list so far "
          f"(online #{ln(res['lines_registered'])}) and of the scenario field (#{ln(res['lines_scenario'])}). "
          "School rank = the school's 2026 combined online rank. Scenario # = position by school rank among the "
          "scenario's non-local round-1 teams before the top-95 cut; extra = a "
          "school's later registration, which waits for round 2 (" +
          ("; ".join(f"{s} {t}" for s, t in res["extra_teams"]) or "none") + ").", "",
          "| # | school | team | school rank | online r1 / r2 | online rank | scenario # | absolute | "
          "field-relative (list so far) | field-relative (scenario) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["teams"]:
        rr = " / ".join(str(round(r["online_ranks"][k])) if k in r["online_ranks"] else "-" for k in ("1", "2"))
        L.append(f"| {r['field_position']} | {r['school']} | {r['team']} | {r['school_rank']} | {rr} | {r['mean_online_rank']} | "
                 f"{r['scenario_position'] or ('local' if r['local'] else 'extra')} | {pct(r['absolute'])} | {pct(r['field_relative_registered'])} | "
                 f"{pct(r['field_relative_scenario'])} |")
    L += ["", "Not linked to an online result: " +
          "; ".join(f"{r['school']} {r['team']} ({len(r['members'].split('/'))} members)" for r in res["unlinked"]) + ".",
          "", "## Round-1 selection by school rank", "",
          f"If more than {NONLOCAL_SEATS} non-local teams register by 10-30, {NONLOCAL_SEATS} are taken by online rank. "
          + (f"The export's Online ranking is the school's 2026 combined online rank on {res['rank_check']['rows']} rows"
             + (f", except {res['rank_check']['mismatches']}" if res["rank_check"]["mismatches"] else "") + ". "
             if res["rank_check"]["rows"] else "")
          + f"If it closed now: {res['cut_now']['round1_nonlocal']} round-1 non-local teams "
          f"({res['cut_now']['unlinked']} with no online result of their own), so {res['cut_now']['cut']} are cut: the "
          f"last kept is school #{res['cut_now']['last_kept_school_rank']}, the first cut "
          f"#{res['cut_now']['first_cut_school_rank']}. Cut: "
          + ("; ".join(f"{s} {t} (#{k})" for s, t, k in res["cut_now"]["cut_teams"]) or "none") + ".", "",
          "| team | school rank | best / mean online rank | registered round-1 teams ahead | more that can register "
          "before it is cut | unregistered non-local schools ahead | scenario position (of pool) | scenario cut at "
          "school rank |", "|---|---|---|---|---|---|---|---|"]
    for t, v in res["selection"].items():
        L.append(f"| {t} | {v['school_rank']} | {v['best_online_rank']} / {v['mean_online_rank']} | {v['ahead']} | "
                 f"{v['room']} | {v['unregistered_ahead']} | {v['scenario_position']} of {v['scenario_pool']} | "
                 f"{v['scenario_cut_school_rank']} |")
    for t, v in res["selection"].items():
        c = v["cut_risk"]
        if c is None:
            continue
        g = c["groups"]
        L += ["", f"Chance {t} is cut in round 1: it is cut if {c['need']} more of the {v['unregistered_ahead']} "
              f"unregistered non-local schools above it register in the {c['days_left']} days left (to {ROUND1_CLOSE} "
              f"UTC). Since `{c['since']}` ({c['days']} days), {g['past_hk']['registered_since']} of the schools with a "
              f"2024/2025 Hong Kong team registered ({g['past_hk']['unregistered']} of {g['past_hk']['schools']} left) "
              f"and {g['other']['registered_since']} of the others ({g['other']['unregistered']} of "
              f"{g['other']['schools']} left). Each school registers independently at its group's rate.", "",
              "| assumption | P(register): past-HK / other | expected new | P(cut) |", "|---|---|---|---|"]
        L += [f"| {r['assumption']} | {r['p_past_hk']} / {r['p_other']} | {r['expected_new']} | {r['p_cut']:.1%} |"
              for r in c["scenarios"]]
        L += ["", f"If every past-HK school returns, the cut needs {c['others_needed']} of the {g['other']['unregistered']} "
              f"others: a 5% / 50% chance if each registers with probability {c['break_even_p_other']['0.05']} / "
              f"{c['break_even_p_other']['0.5']} (at the pace above: {c['scenarios'][0]['p_other']})."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=str(REGISTRATION))
    ap.add_argument("--team", action="append", default=["NUM-R^3"])
    a = ap.parse_args()
    res = run(a.file, tuple(dict.fromkeys(a.team)))
    og.OUT.mkdir(exist_ok=True)
    (og.OUT / "hk_field_2026.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = markdown(res)
    (og.OUT / "hk_field_2026.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
