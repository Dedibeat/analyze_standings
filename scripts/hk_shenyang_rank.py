"""Where a team ranks in the 2026 Hong Kong field, in Shenyang-rank terms.

Every Hong Kong registrant (``arch_b.hk_field_2026`` export) is linked to its
2026 appearances: the two EC online rounds, the five 51st-season regionals
(Xi'an, Chengdu, Wuhan, Nanjing, Shenyang) and the 2026 CCPC boards (Changchun,
Guizhou, Nanchang, Qinhuangdao). A regional/CCPC row is the same line-up when
it is from the same school and shares >= 2 members, or (no members on the
board) has the same team name.

Online and regional rows get their CF performance from the binary joint fit
(``export_virtual_calc.performance_fit``), so they are on one scale. CCPC boards
are not in the fit: each is mapped with ``perf = a + b log(rank)`` fitted on
its line-ups that also have a 2026 regional performance. A team's strength is
the mean of its appearances; its Shenyang-equivalent rank is 1 + the number of
official Shenyang teams with a higher performance.

    python3 scripts/hk_shenyang_rank.py [--team NUM-R^3]

Writes ``output/hk_shenyang_rank.md``.
"""

import argparse
import collections
import csv
import json
import math
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arch_b import hk_field_2026 as hf  # noqa: E402
from arch_b import online_gold as og  # noqa: E402
from arch_b.export_virtual_calc import performance_fit  # noqa: E402

ONLINE = {"1": 4071, "2": 4113}
XCPCIO = ROOT / "data" / "xcpcio_51st_regionals.json"
QOJ_OF = {"xian": 4593, "chengdu": 4607, "wuhan": 4694}  # boards the fit has from QOJ, not XCPCIO
CHANGCHUN = ROOT / "output" / "ccpc_12th_changchun_standings.csv"  # official rank.iccpc.cn board, with members
CCPC = [(ROOT / "data" / "xcpcio_ccpc.json", -130494359200770, "CCPC Guizhou"),
        (ROOT / "data" / "xcpcio_ccpc.json", -223919550453741, "CCPC Nanchang"),
        (ROOT / "data" / "xcpcio_ccpc.json", -195570550985916, "CCPC Qinhuangdao")]
OUT = ROOT / "output" / "hk_shenyang_rank.md"
VIRTUAL_DISCOUNT = 100  # a virtual scoreline reads up to ~100 CF stronger than onsite form (details.md, 2026-10-13)


def same_lineup(school, members, team, row):
    shared = len(members & {og.norm_name(m) for m in row.get("members") or []})
    if not row.get("affiliation"):  # XCPCIO CCPC boards: members only
        return shared >= 2
    if og.norm_school(row.get("affiliation")) not in school:
        return False
    return shared >= 2 or (not row.get("members") and og.norm_name(row["team_name"]) == team)


def official_ranked(rows):
    """Official rows in board order with their official rank (1-based)."""
    off = sorted(((i, r) for i, r in enumerate(rows) if r.get("official")), key=lambda t: t[1]["rank"])
    return [(i, r, k + 1) for k, (i, r) in enumerate(off)]


def build(file, team="NUM-R^3"):
    """Registrants with their 2026 appearances on the performance scale (``reg``, ``ranked``, ``me``), the
    boards, the CCPC maps, and the helpers ``sy_rank(perf)`` and ``virtual_perf(board, rank)``."""
    _, _, _, lookup = performance_fit()
    perf = {k: v[1] for k, v in lookup.items()}
    tagged = {c["contest_id"]: c for c in json.load(open(ROOT / "data" / "tagged.json"))}

    data = og.load()
    reg = hf.link_registered(hf.read_registration(file), data)
    solved = {(r["round"], og.norm_school(r["school"]), og.norm_name(r["team"])): int(r["solved"] or 0)
              for r in data["online_teams"] if r["season"] == "2026"}
    online_rows = {rnd: collections.defaultdict(list) for rnd in ONLINE}  # team name -> [(row, solved)]
    for rnd, cid in ONLINE.items():
        for i, s in enumerate(tagged[cid]["standings"]):
            online_rows[rnd][og.norm_name(s["team_name"])].append((i, int(s.get("total_solved") or 0)))

    # Regional boards: official rows with members; the fit's row for each.
    regionals = {}
    for c in json.load(open(XCPCIO)):
        city = c["board_link"].rsplit("/", 1)[1]
        cid = QOJ_OF.get(city, c["contest_id"])
        qoj = collections.defaultdict(list)
        if city in QOJ_OF:
            for i, s in enumerate(tagged[cid]["standings"]):
                qoj[(og.norm_name(s["team_name"]), int(s.get("total_solved") or 0))].append(i)
        rows = []
        for i, r, rank in official_ranked(c["standings"]):
            if city in QOJ_OF:
                hit = qoj.get((og.norm_name(r["team_name"]), r["total_solved"]), [])
                p = perf.get((cid, hit[0])) if len(hit) == 1 else None
            else:
                p = perf.get((cid, i))
            rows.append(dict(r, official_rank=rank, perf=p))
        regionals[city.capitalize().replace("Xian", "Xi'an")] = rows
    shenyang = sorted((r["perf"] for r in regionals["Shenyang"] if r["perf"] is not None), reverse=True)

    ccpc = []
    for path, cid, name in CCPC:
        c = next(c for c in json.load(open(path)) if c["contest_id"] == cid)
        rows = official_ranked(c["standings"]) if any(r.get("official") for r in c["standings"]) \
            else [(i, r, int(r["rank"])) for i, r in enumerate(c["standings"])]  # no official flags: board rank
        ccpc.append((name, [dict(r, official_rank=k) for _, r, k in rows]))
    with open(CHANGCHUN, encoding="utf-8") as f:
        ccpc.insert(0, ("CCPC Changchun", [
            dict(team_name=r["team"], affiliation=r["school"], members=r["members"].split("|"),
                 official_rank=int(r["official_rank"])) for r in csv.DictReader(f) if r["official"] == "1"]))

    def appearances(school, members, team, rnd_teams):
        out = []
        for rnd, t in rnd_teams.items():
            want = next((solved[(rnd, sc, t)] for sc in school if (rnd, sc, t) in solved), None)
            hits = [i for i, s in online_rows[rnd].get(t, []) if s == want]
            if len(hits) == 1 and (ONLINE[rnd], hits[0]) in perf:
                out.append((f"Online {rnd}", perf[(ONLINE[rnd], hits[0])], None))
        for city, rows in regionals.items():
            for r in rows:
                if same_lineup(school, members, team, r) and r["perf"] is not None:
                    out.append((city, r["perf"], r["official_rank"]))
        return out

    for r in reg:
        r["key"] = ({og.norm_school(r["school"]), og.norm_school(r["school_en"])}, {og.norm_name(m) for m in r["members"].split("/") if m.strip()},
                    og.norm_name(r["team"]))
        r["apps"] = appearances(*r["key"], {k: og.norm_name(v) for k, v in r["online_teams"].items()})

    # CCPC: perf = a + b log(rank), fitted on line-ups with a 2026 regional performance (any school,
    # not only registrants).
    lineups = []  # (school, members, regional perf)
    for rows in regionals.values():
        for x in rows:
            if x["perf"] is not None and len(x["members"]) >= 2:
                lineups.append((og.norm_school(x["affiliation"]), {og.norm_name(m) for m in x["members"]}, x["perf"]))
    ccpc_maps = {}
    for name, rows in ccpc:
        pts = []
        for x in rows:
            ms = {og.norm_name(m) for m in x.get("members") or []}
            ps = [p for sc, m2, p in lineups if len(ms & m2) >= 2
                  and (not x.get("affiliation") or og.norm_school(x["affiliation"]) == sc)]
            if ps:
                pts.append((math.log(x["official_rank"]), float(np.mean(ps))))
        if len(pts) < 10:
            ccpc_maps[name] = (len(pts), None)
            continue
        b, a = np.polyfit(*zip(*pts), 1)
        ccpc_maps[name] = (len(pts), (a, b, float(np.corrcoef(*zip(*pts))[0, 1])))
        for r in reg:
            for x in rows:
                if same_lineup(*r["key"], x):
                    r["apps"].append((name, a + b * math.log(x["official_rank"]), x["official_rank"]))

    def sy_rank(p):
        return 1 + sum(1 for q in shenyang if q > p)

    def virtual_perf(board, k):
        """Between the official teams at ranks k-1 and k (regional), or the board's CCPC map."""
        if board in regionals:
            ps = [r["perf"] for r in regionals[board] if r["official_rank"] in (k - 1, k) and r["perf"] is not None]
            return float(np.mean(ps))
        a, b, _ = ccpc_maps[board][1]
        return a + b * math.log(k)

    for r in reg:
        r["strength"] = float(np.mean([p for _, p, _ in r["apps"]])) if r["apps"] else None
        onsite = [p for c, p, _ in r["apps"] if not c.startswith("Online")]
        r["onsite"] = float(np.mean(onsite)) if onsite else None
    ranked = sorted((r for r in reg if r["strength"] is not None), key=lambda r: -r["strength"])
    me = next(r for r in reg if r["team"] == team)
    return SimpleNamespace(**{k: v for k, v in locals().items() if k != "f"})


def hk_model(c, file):
    """perf -> online strength x (linear fit over registrants with both online rounds), then the
    field-relative Hong Kong model on the registered field (``arch_b.hk_field_2026``).
    Returns ``(intercept, slope, r, n, chances)``; ``chances(perf)`` gives ``(x, {gold, silver, bronze})``."""
    both = [(np.mean([p for k, p, _ in r["apps"] if k.startswith("Online")]), r["x"]) for r in c.reg
            if r["x"] is not None and sum(k.startswith("Online") for k, _, _ in r["apps"]) == 2]
    slope, icpt = np.polyfit(*zip(*both), 1)
    res = hf.run(file)
    past = [r for r in hf.hk.link_hk(c.data, og.online_strengths(c.data["online_teams"]))
            if r["season"] in hf.om.HK_SEASONS and r["x"] is not None]
    w_rel, line = hf.fit(past, True), {n: -math.log(v) for n, v in res["lines_registered"].items()}

    def chances(p):
        x = icpt + slope * p
        return x, hf.predict(w_rel, x, line)
    return icpt, slope, float(np.corrcoef(*zip(*both))[0, 1]), len(both), chances


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="NUM-R^3")
    ap.add_argument("--file", type=Path, default=ROOT / "data" / "icpc_hk_macau_public_teams_20261122.xlsx",
                    help="Hong Kong registration export (default: the 11-22 one)")
    ap.add_argument("--virtual", action="append", default=[], metavar="BOARD:RANK",
                    help="a virtual result as an official-equivalent rank, e.g. Chengdu:35 or 'CCPC Changchun':29")
    args = ap.parse_args()
    c = build(args.file, args.team)
    reg, ranked, me, data = c.reg, c.ranked, c.me, c.data
    regionals, ccpc_maps, sy_rank, virtual_perf = c.regionals, c.ccpc_maps, c.sy_rank, c.virtual_perf
    above = [r for r in ranked if r["strength"] > me["strength"]]
    above_onsite = [r for r in reg if r["onsite"] is not None and r["onsite"] > me["onsite"]]

    L = [f"# {args.team} in the 2026 Hong Kong field, by Shenyang rank", "",
         f"Registration: `{args.file.name}` ({len(reg)} teams); {len(ranked)} have a 2026 result "
         f"({sum(1 for r in reg if r['onsite'] is not None)} onsite: regional or CCPC).", "",
         f"Shenyang official board: {len(regionals['Shenyang'])} teams.", "",
         "## CCPC maps (perf = a + b log rank, line-ups with a 2026 regional)", "",
         "| board | pairs | a | b | r |", "|---|---|---|---|---|"]
    for name, (n, m) in ccpc_maps.items():
        L.append(f"| {name} | {n} | " + (" | ".join(f"{v:.2f}" for v in m) if m else "– | – | –") + " |")
    L += ["", f"## {args.team}", ""]
    L += [f"- {c}: perf {p:.0f}" + (f", official #{k}" if k else "") + f" (Shenyang-equivalent #{sy_rank(p)})"
          for c, p, k in me["apps"]]
    L += [f"- **All appearances:** mean {me['strength']:.0f}, Shenyang-equivalent #{sy_rank(me['strength'])}; "
          f"**{len(above) + 1}th** of {len(ranked)} registrants with a result ({len(above)} ahead, "
          f"{sum(1 for r in above if r['local'])} of them local).",
          f"- **Onsite only:** mean {me['onsite']:.0f}, Shenyang-equivalent #{sy_rank(me['onsite'])}; "
          f"{len(above_onsite)} registrants with an onsite result are stronger.", "",
          "## Registrants by strength (mean of 2026 appearances)", "",
          "| # | school | team | local | Shenyang-eq. | strength | onsite | appearances |",
          "|---|---|---|---|---|---|---|---|"]
    for k, r in enumerate(ranked, 1):
        apps = "; ".join(f"{c} {p:.0f}" + (f" (#{n})" if n else "") for c, p, n in r["apps"])
        L.append(f"| {k} | {r['school']} | {r['team']} | {'yes' if r['local'] else ''} | {sy_rank(r['strength'])} | "
                 f"{r['strength']:.0f} | {'' if r['onsite'] is None else round(r['onsite'])} | {apps} |")
    if args.virtual:
        # Hong Kong medal chances: perf -> online strength x (linear fit over registrants with both online
        # rounds), then the field-relative Hong Kong model on the registered field (arch_b.hk_field_2026).
        icpt, slope, corr, n_both, chances = hk_model(c, args.file)
        L += ["", "## Virtuals and the Hong Kong field", "",
              f"Online-equivalent rank: x = {icpt:.3f} + {slope:.5f} perf (r = "
              f"{corr:.2f}, {n_both} registrants). Gold / silver / bronze: "
              "field-relative Hong Kong model on the registered field. "
              f"'−{VIRTUAL_DISCOUNT}' reads the virtual {VIRTUAL_DISCOUNT} CF weaker.", "",
              "| result | perf | Shenyang-eq. | Hong Kong position | online-eq. rank | gold / silver / bronze |",
              "|---|---|---|---|---|---|"]
        cases = [(f"{args.team} Shenyang onsite (#{next(k for c, _, k in me['apps'] if c == 'Shenyang')})",
                  next(p for c, p, _ in me["apps"] if c == "Shenyang"))]
        for v in args.virtual:
            board, k = v.rsplit(":", 1)
            p = virtual_perf(board, int(k))
            cases += [(f"{board} virtual #{k}", p), (f"{board} virtual #{k} −{VIRTUAL_DISCOUNT}", p - VIRTUAL_DISCOUNT)]
        for label, p in cases:
            x, pr = chances(p)
            pos = 1 + sum(1 for r in ranked if r["strength"] > p and r["team"] != args.team)
            L.append(f"| {label} | {p:.0f} | {sy_rank(p)} | {pos} of {len(ranked)} | {math.exp(-x):.0f} | "
                     + " / ".join(f"{100 * pr[c]:.0f}%" for c in hf.om.CLASSES[:3]) + " |")
    none = [r for r in reg if r["strength"] is None]
    L += ["", f"## No 2026 result ({len(none)})", "", ", ".join(f"{r['school']} {r['team']}" for r in none)]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
