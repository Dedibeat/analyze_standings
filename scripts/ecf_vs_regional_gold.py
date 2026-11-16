"""Is an EC-Final medal harder than a regional gold?  A check that does not use the
repository's ratings.

Data: the official XCPCIO boards of the 48th-50th seasons (the regionals of each
season and its EC-Final), cached in ``data/xcpcio_boards/<season>_<site>/``.
Standings are recomputed from ``run.json`` with the ICPC rule (solved, then
penalty = accepted minute + 20 per earlier rejected run, compile errors free).
Official teams only; medal lines are the board's own official counts.

Two answers:

1. Paired, model-free.  Teams that played the EC-Final *and* a regional of the
   same season (linked by school plus two shared members, or by school plus team
   name where a board has no members).  For every such regional appearance we ask
   two yes/no questions: gold at that regional?  medal at the EC-Final?  The
   discordant pairs (gold but no EC-Final medal vs EC-Final medal but no gold)
   say which result is harder for the same teams.

2. A season-level Bradley-Terry fit of our own.  Every pair of official teams
   (with at least one solve) on a board is a game won by the better-ranked team;
   linked teams share one strength across boards.  No problems, no difficulties,
   no outside ratings.  We then ask where each regional's gold-cutoff teams would
   finish in the EC-Final field (expected official rank).

    python scripts/ecf_vs_regional_gold.py
"""

import json
import math
import os
import re
from collections import defaultdict

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
CACHE = os.path.join(ROOT, "data", "xcpcio_boards")
OUT = os.path.join(ROOT, "output", "ecf_vs_regional_gold.md")

SEASONS = {
    "48th": ["nanjing", "hefei", "shenyang", "macau", "jinan", "hangzhou", "xian"],
    "49th": ["chengdu", "nanjing", "shenyang", "kunming", "hongkong", "hangzhou", "shanghai"],
    "50th": ["xian", "chengdu", "nanjing", "wuhan", "shenyang", "shanghai", "hongkong"],
}
COHORT = 2          # gold-cutoff cohort = official ranks cutoff-2 .. cutoff+2


def _text(x):
    if isinstance(x, dict):
        t = x.get("texts", {})
        return t.get("zh-CN") or t.get(x.get("fallback_lang")) or next(iter(t.values()), "")
    return x or ""


def _norm(s):
    return re.sub(r"[\s\W_]+", "", _text(s)).lower()


def _load(name, d):
    p = os.path.join(d, name)
    with open(p) as f:
        return json.load(f)


def load_board(season, site):
    """Official teams of one board, ranked: list of dicts, best first."""
    d = os.path.join(CACHE, f"{season}_{site}")
    cfg, teams, runs = _load("config.json", d), _load("team.json", d), _load("run.json", d)
    teams = teams if isinstance(teams, list) else list(teams.values())
    orgs = {}
    try:
        o = _load("organizations.json", d)
        for x in (o if isinstance(o, list) else o.values()):
            orgs[x.get("id")] = _text(x.get("name"))
    except (OSError, ValueError):
        pass
    has_flag = any("official" in t or "group" in t for t in teams)
    unit = cfg.get("options", {}).get("submission_timestamp_unit", "second")
    scale = {"millisecond": 1000, "second": 1, "nanosecond": 1e9}[unit]
    pen = cfg.get("penalty", 1200)

    rows = {}
    for t in teams:
        tid = str(t.get("id", t.get("team_id")))
        official = (not has_flag or t.get("official") is True
                    or "official" in (t.get("group") or []))
        if not official:
            continue
        school = t.get("organization") or orgs.get(t.get("organization_id"), "")
        rows[tid] = {"id": tid, "name": _norm(t.get("name")), "school": _norm(school),
                     "members": frozenset(_norm(m) for m in (t.get("members") or []) if _norm(m)),
                     "solved": 0, "penalty": 0}

    seen = defaultdict(lambda: [False, 0])          # (team, problem) -> [accepted, rejects]
    for r in sorted(runs, key=lambda r: r["timestamp"]):
        tid = str(r["team_id"])
        if tid not in rows:
            continue
        st = seen[(tid, r["problem_id"])]
        if st[0]:
            continue
        s = r["status"].upper()
        if s in ("ACCEPTED", "CORRECT"):
            st[0] = True
            rows[tid]["solved"] += 1
            rows[tid]["penalty"] += int(r["timestamp"] / scale // 60) * 60 + st[1] * pen
        elif s not in ("COMPILATION_ERROR", "COMPILE_ERROR", "PENDING", "FROZEN", "JUDGING"):
            st[1] += 1

    ranked = sorted(rows.values(), key=lambda r: (-r["solved"], r["penalty"]))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    m = cfg["medal"]["official"]
    g, s, b = m["gold"], m["gold"] + m["silver"], m["gold"] + m["silver"] + m["bronze"]
    for r in ranked:
        r["tier"] = ("gold" if r["rank"] <= g else "silver" if r["rank"] <= s
                     else "bronze" if r["rank"] <= b else "none")
    return {"site": site, "start": cfg["start_time"] / (1000 if cfg["start_time"] > 1e11 else 1),
            "rows": ranked, "cut": {"gold": g, "silver": s, "bronze": b}}


def same_team(a, b):
    if a["school"] != b["school"]:
        return False
    if a["members"] and b["members"]:
        return len(a["members"] & b["members"]) >= 2
    return a["name"] == b["name"] and a["name"] != ""


def link(ecf, regionals):
    """{(regional site, regional team id): ecf row} for teams in both."""
    by_school = defaultdict(list)
    for e in ecf["rows"]:
        by_school[e["school"]].append(e)
    out = {}
    for reg in regionals:
        for r in reg["rows"]:
            hits = [e for e in by_school.get(r["school"], []) if same_team(r, e)]
            if len(hits) == 1:
                out[(reg["site"], r["id"])] = hits[0]
    return out


def sign_test(b, c):
    """Two-sided exact binomial p for b vs c discordant pairs."""
    n = b + c
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def bradley_terry(boards, linked, iters=2000):
    """MM fit (Hunter 2004) with one virtual win and loss against a unit-strength
    reference per team.  Returns {(site, team id): log strength}."""
    key = {}
    for (site, tid), e in linked.items():          # regional rows share the ECF entity
        key[(site, tid)] = ("ecfinal", e["id"])
    ents = {}
    for bd in boards:
        for r in bd["rows"]:
            k = key.get((bd["site"], r["id"]), (bd["site"], r["id"]))
            ents.setdefault(k, len(ents))
    n = len(ents)
    wins = np.zeros(n)
    games = np.zeros((n, n))
    for bd in boards:
        rs = [r for r in bd["rows"] if r["solved"] > 0]
        idx = np.array([ents[key.get((bd["site"], r["id"]), (bd["site"], r["id"]))] for r in rs])
        sp = [(r["solved"], r["penalty"]) for r in rs]
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                if sp[i] == sp[j]:
                    continue                       # exact ties carry no order
                wins[idx[i]] += 1
                games[idx[i], idx[j]] += 1
                games[idx[j], idx[i]] += 1
    p = np.ones(n)
    for _ in range(iters):
        denom = (games / (p[:, None] + p[None, :])).sum(1) + 2 / (p + 1)
        new = (wins + 1) / denom
        new /= np.exp(np.mean(np.log(new)))
        if np.max(np.abs(np.log(new) - np.log(p))) < 1e-9:
            p = new
            break
        p = new
    logp = np.log(p)
    return {k: logp[i] for k, i in ents.items()}


def main():
    lines = ["# EC-Final medal vs regional gold (no ratings used)", "",
             "Generated by `scripts/ecf_vs_regional_gold.py` from the official XCPCIO "
             "boards (48th-50th seasons). Official teams only; standings recomputed "
             "from run.json.", ""]
    total = defaultdict(int)
    for season, sites in SEASONS.items():
        ecf = load_board(season, "ecfinal")
        regs = [load_board(season, s) for s in sites]
        regs = [r for r in regs if r["start"] < ecf["start"]]
        linked = link(ecf, regs)

        # 1. paired table
        tab = defaultdict(int)
        for reg in regs:
            for r in reg["rows"]:
                e = linked.get((reg["site"], r["id"]))
                if e:
                    tab[(r["tier"], e["tier"] != "none")] += 1
        gm, gn = tab[("gold", True)], tab[("gold", False)]
        om = sum(v for (t, m), v in tab.items() if t != "gold" and m)
        on = sum(v for (t, m), v in tab.items() if t != "gold" and not m)
        for k, v in (("gm", gm), ("gn", gn), ("om", om), ("on", on)):
            total[k] += v
        best = {}                                  # ECF team -> got gold at any regional
        for (site, tid), e in linked.items():
            reg = next(r for r in regs if r["site"] == site)
            gold = next(x for x in reg["rows"] if x["id"] == tid)["tier"] == "gold"
            best[e["id"]] = best.get(e["id"], False) or gold
        for e in ecf["rows"]:
            if e["id"] in best:
                total[("team", best[e["id"]], e["tier"] != "none")] += 1
        ecf_teams = len(ecf["rows"])
        linked_ecf = len({id(e) for e in linked.values()})
        lines += [f"## {season} season (EC-Final: {ecf_teams} official teams, "
                  f"{linked_ecf} found at a regional; regionals: "
                  f"{', '.join(r['site'] for r in regs)})", "",
                  "Regional appearances of EC-Final teams:", "",
                  "| regional result | EC-Final medal | no EC-Final medal |",
                  "|---|---|---|"]
        for t in ("gold", "silver", "bronze", "none"):
            lines.append(f"| {t} | {tab[(t, True)]} | {tab[(t, False)]} |")
        lines += ["", f"- Gold at a regional, then EC-Final medal: {gm}/{gm + gn} "
                  f"({gm / max(1, gm + gn):.0%}).",
                  f"- Discordant: gold but no EC-Final medal = {gn}; EC-Final medal "
                  f"without that regional's gold = {om}.", ""]

        # 2. own Bradley-Terry fit
        s = bradley_terry([ecf] + regs, linked)
        ecf_s = np.array([s[("ecfinal", e["id"])] for e in ecf["rows"]])

        def ecf_rank(x):                           # expected official rank in the ECF field
            return 1 + float(np.sum(1 / (1 + np.exp(x - ecf_s))))

        def cohort(bd, cut):
            rs = bd["rows"][max(0, cut - 1 - COHORT): cut + COHORT]
            ks = [("ecfinal", linked[(bd["site"], r["id"])]["id"])
                  if (bd["site"], r["id"]) in linked and bd["site"] != "ecfinal"
                  else (bd["site"], r["id"]) for r in rs]
            return float(np.mean([s[k] for k in ks]))

        ec = ecf["cut"]
        lines += ["Own Bradley-Terry fit (log strength, EC-Final field mean = "
                  f"{ecf_s.mean():.2f}). EC-Final lines: gold {cohort(ecf, ec['gold']):.2f}, "
                  f"silver {cohort(ecf, ec['silver']):.2f}, bronze {cohort(ecf, ec['bronze']):.2f} "
                  f"(official ranks {ec['gold']}/{ec['silver']}/{ec['bronze']}).", "",
                  "| regional | gold cutoff rank | gold-cohort strength | "
                  "expected EC-Final rank | EC-Final tier |", "|---|---|---|---|---|"]
        for reg in regs:
            x = cohort(reg, reg["cut"]["gold"])
            rk = ecf_rank(x)
            tier = ("gold" if rk <= ec["gold"] else "silver" if rk <= ec["silver"]
                    else "bronze" if rk <= ec["bronze"] else "none")
            total["n_reg"] += 1
            total["reg_" + tier] += 1
            lines.append(f"| {reg['site']} | {reg['cut']['gold']} | {x:.2f} | {rk:.0f} | {tier} |")
        lines.append("")

    gm, gn, om, on = total["gm"], total["gn"], total["om"], total["on"]
    lines += ["## All three seasons", "",
              f"- Regional gold, then EC-Final medal: {gm}/{gm + gn} ({gm / (gm + gn):.0%}).",
              f"- EC-Final medal without gold at that regional: {om}/{om + on} "
              f"of non-gold appearances ({om / (om + on):.0%}).",
              f"- Discordant pairs: {gn} (gold, no ECF medal) vs {om} (ECF medal, no "
              f"gold); exact sign test p = {sign_test(gn, om):.2g}.",
              f"- Per team (any gold that season): {total[('team', True, True)]}/"
              f"{total[('team', True, True)] + total[('team', True, False)]} season-gold teams "
              f"medalled at the EC-Final; {total[('team', False, True)]}/"
              f"{total[('team', False, True)] + total[('team', True, True)]} linked EC-Final "
              f"medallists had no regional gold that season.",
              f"- Gold-cutoff cohorts placed in the EC-Final field by the own fit: "
              + ", ".join(f"{t} {total['reg_' + t]}" for t in ("gold", "silver", "bronze", "none"))
              + f" (of {total['n_reg']} regionals).", ""]
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
