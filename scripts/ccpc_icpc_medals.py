#!/usr/bin/env python3
"""How a CCPC regional-station medal relates to an ICPC Asia East regional medal.

Teams: official teams of the CCPC regional stations (8th-11th CCPC, seasons
2022-2025, XCPCIO boards) linked to official teams of the same season's ICPC
EC regionals (``data/ec_online/regional_teams.csv``): same school and >= 2
shared members.  Hong Kong boards list pinyin names and English schools, so
there the CCPC members are turned into pinyin (``arch_b.hk_link``) and the
school mapped through ``school_names_en.csv``; Hong Kong 2022 and Macau 2023
carry no members and stay unlinked.  Unit = (CCPC entry, ICPC entry) pair; a
CCPC entry takes at most one entry per ICPC regional.

CCPC medals: the board's own counts (8th, early 9th) or XCPCIO's "ccpc"
preset, the rule ``build_ec_online_data.medal_counts`` falls back to: gold to
rank ceil(10%), silver to ceil(30%), bronze to ceil(60%) of official teams
with >= 1 solve.  ICPC medals as in ``regional_teams.csv``.

Main tables use the model seasons 2023-2025; 2022 (online ICPC regionals) is
shown by season only.  Reports ranks, percentiles and medals, no solve counts
or problem data, except for the ``--board`` of a virtual run, which the user
has seen.

    python3 scripts/ccpc_icpc_medals.py [--board 11th/jinan --solved 4 --penalty 484]

Writes ``output/ccpc_icpc_medals.{json,md}``.  Needs numpy + pypinyin.
"""
import argparse
import collections
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_b import hk_link as hk  # noqa: E402
from arch_b import online_gold as og  # noqa: E402
import build_ec_online_data as bd  # noqa: E402

CCPC = {
    "2022": ["8th/guilin", "8th/weihai", "8th/guangzhou", "8th/mianyang"],
    "2023": ["9th/qinhuangdao", "9th/guilin", "9th/harbin", "9th/shenzhen"],
    "2024": ["10th/harbin", "10th/jinan", "10th/chongqing", "10th/zhengzhou"],
    "2025": ["11th/harbin", "11th/jinan", "11th/zhengzhou", "11th/chongqing"],
}
MEDALS = ("gold", "silver", "bronze", "")
OUTCOMES = ("gold", "silver+", "medal", "ecf_line")
ECF_RANK = 75  # mainland EC-Final line (anchor_teams)
HK_LINE = {"2024": 37, "2025": 32}  # 10th Hong Kong place under the 2026 rule (ecfinal_chance)
BINS = (0, .05, .1, .15, .2, .25, .3, .35, .4, .5, .6, .8, 1.01)
OUT = og.OUT / "ccpc_icpc_medals"


def members(text):
    return frozenset(og.norm_name(m) for m in text.split("|") if og.norm_name(m))


def medal_of(rank, solved, counts):
    gold, silver, bronze = counts
    if not rank or solved <= 0:
        return ""
    return ("gold" if rank <= gold else "silver" if rank <= gold + silver
            else "bronze" if rank <= gold + silver + bronze else "")


def ccpc_board(board):
    """Official rows of one CCPC board with official rank, percentile and medal."""
    config, rows = bd.regional_standings(board, "ccpc")
    gold, silver, bronze, how = bd.medal_counts(None, config, rows)  # CCPC board counts are real
    effective = sum(1 for r in rows if r["official"] and r["solved"] > 0)
    out = [dict(r, board=board, medal=medal_of(r["official_rank"], r["solved"], (gold, silver, bronze)),
                pct=r["official_rank"] / effective, s=og.norm_school(r["school"]), m=members(r["members"]),
                py=[hk.pinyin_variants(m) for m in r["members"].split("|")])
           for r in rows if r["official"]]
    return out, dict(board=board, official=len(out), effective=effective, gold=gold, silver=silver,
                     bronze=bronze, medal_source=how)


def icpc_rows(regional_teams):
    """Official ICPC EC regional rows; Hong Kong / Macau with mapped school and pinyin members."""
    en2cn = hk.school_map()
    out = []
    for r in regional_teams:
        if r["official"] != "1" or not r["official_rank"]:
            continue
        if r["site"] in og.EXCLUDED_SITES:
            s = en2cn.get(hk.norm_school_en(r["school"]))
            m = frozenset(hk.canon_person(x) for x in r["members"].split("|") if x)
        else:
            s, m = og.norm_school(r["school"]), members(r["members"])
        out.append(dict(r, rank=int(r["official_rank"]), mainland=r["site"] not in og.EXCLUDED_SITES, s=s, m=m))
    return out


def shared(c, r):
    if r["mainland"]:
        return len(c["m"] & r["m"])
    return sum(1 for v in c["py"] if v & r["m"])


def link(ccpc, icpc):
    """(CCPC row, ICPC row) pairs: same season and school, >= 2 shared members;
    per ICPC regional the entry sharing the most members."""
    by_key = collections.defaultdict(list)
    for r in icpc:
        by_key[(r["season"], r["s"])].append(r)
    pairs = []
    for c in ccpc:
        best = {}
        for r in by_key[(c["season"], c["s"])]:
            n = shared(c, r)
            if n >= 2 and n > best.get(r["site"], (0, None))[0]:
                best[r["site"]] = (n, r)
        pairs += [(c, r) for _, r in best.values()]
    return pairs


def icpc_pairs(icpc):
    """Ordered pairs of one team's two mainland ICPC regionals in a season (benchmark)."""
    by_key = collections.defaultdict(list)
    for r in icpc:
        if r["mainland"]:
            by_key[(r["season"], r["s"])].append(r)
    return [(a, b) for rows in by_key.values() for a in rows for b in rows
            if a["site"] != b["site"] and len(a["m"] & b["m"]) >= 2]


def outcomes(r):
    line = ECF_RANK if r["mainland"] else HK_LINE.get(r["season"], 0)
    return {"gold": r["medal"] == "gold", "silver+": r["medal"] in ("gold", "silver"),
            "medal": r["medal"] != "", "ecf_line": r["rank"] <= line}


def table(pairs):
    """Per source medal: n, share of each target outcome, and target medal counts."""
    out = {}
    for m in MEDALS:
        hit = [t for s, t in pairs if s["medal"] == m]
        out[m or "none"] = dict(n=len(hit), counts={(x or "none"): sum(t["medal"] == x for t in hit) for x in MEDALS},
                                **{k: float(np.mean([outcomes(t)[k] for t in hit])) if hit else None
                                   for k in OUTCOMES})
    return out


def logit(p):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def fit(xs, ys, iters=30):
    """Logistic regression y ~ a + b x by Newton's method."""
    X = np.column_stack([np.ones(len(xs)), xs])
    y = np.asarray(ys, float)
    w = np.zeros(2)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        w += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]), X.T @ (y - p))
    return w


def curve(pairs, n_boot=500, seed=2026):
    """Per outcome: logistic fit on logit(CCPC percentile) and team-clustered bootstrap fits."""
    rng = np.random.default_rng(seed)
    teams = collections.defaultdict(list)
    for c, r in pairs:
        teams[(c["season"], c["s"], c["m"])].append((logit(c["pct"]), outcomes(r)))
    keys = list(teams)
    draws = [[keys[i] for i in rng.integers(len(keys), size=len(keys))] for _ in range(n_boot)]
    models = {}
    for k in OUTCOMES:
        def fit_on(ks):
            return fit(*zip(*[(x, o[k]) for key in ks for x, o in teams[key]]))
        models[k] = (fit_on(keys), [fit_on(d) for d in draws])
    return models


def predict(models, pct):
    """{outcome: (P, 10%, 90%)} at a CCPC percentile."""
    x = logit(pct)
    out = {}
    for k, (w, boot) in models.items():
        p = [1 / (1 + math.exp(-(b[0] + b[1] * x))) for b in boot]
        out[k] = (1 / (1 + math.exp(-(w[0] + w[1] * x))), float(np.percentile(p, 10)), float(np.percentile(p, 90)))
    return out


def station_offsets(pairs, models, iters=30):
    """{board: {outcome: intercept shift}} with the pooled slope fixed: how much better (> 0) the
    station's teams did at ICPC than their CCPC percentile implies, i.e. the station's field strength."""
    out = {}
    for board in dict.fromkeys(c["board"] for c, _ in pairs):
        hit = [(c, r) for c, r in pairs if c["board"] == board]
        x = np.array([logit(c["pct"]) for c, _ in hit])
        out[board] = {}
        for k, (w, _) in models.items():
            y = np.array([outcomes(r)[k] for _, r in hit], float)
            off = 0.0
            for _ in range(iters):
                p = 1 / (1 + np.exp(-(w[0] + w[1] * x + off)))
                off += (y - p).sum() / (p * (1 - p)).sum()
            out[board][k] = float(off)
    return out


def even_odds(models):
    """{outcome: (CCPC percentile where P = 50%, 10%, 90%)}."""
    def at(w):
        return 1 / (1 + math.exp(w[0] / w[1]))
    return {k: (at(w), *np.percentile([at(b) for b in boot], [10, 90])) for k, (w, boot) in models.items()}


def bins(pairs, models):
    out = []
    for lo, hi in zip(BINS, BINS[1:]):
        hit = [(c, r) for c, r in pairs if lo <= c["pct"] < hi]
        mid = float(np.median([c["pct"] for c, _ in hit]))
        out.append(dict(lo=lo, hi=min(hi, 1), n=len(hit), model=predict(models, mid),
                        **{k: float(np.mean([outcomes(r)[k] for _, r in hit])) for k in OUTCOMES}))
    return out


def place(board_rows, info, solved, penalty):
    """Official rank, percentile and medal a (solved, penalty) run would have had, and the board's medal lines."""
    rank = 1 + sum((r["solved"], -r["penalty_minutes"]) > (solved, -penalty) for r in board_rows)
    counts = (info["gold"], info["silver"], info["bronze"])
    lines = {}
    for medal, last in zip(("gold", "silver", "bronze"), np.cumsum(counts)):
        r = max((r for r in board_rows if r["official_rank"] <= last), key=lambda r: r["official_rank"])
        lines[medal] = dict(rank=int(last), solved=r["solved"], penalty=r["penalty_minutes"])
    return dict(rank=rank, effective=info["effective"], pct=rank / info["effective"],
                medal=medal_of(rank, solved, counts), lines=lines)


# ------------------------------------------------------------------ report

def pct(v):
    return "–" if v is None else f"{v:.0%}"


def outcome_table(t, line_label):
    lines = [f"| {'medal':8s} | n | gold | silver+ | any medal | {line_label} | counts G / S / B / none |",
             "|---|---|---|---|---|---|---|"]
    for m, v in t.items():
        c = v["counts"]
        lines.append(f"| {m} | {v['n']} | {pct(v['gold'])} | {pct(v['silver+'])} | {pct(v['medal'])} | "
                     f"{pct(v['ecf_line'])} | {c['gold']} / {c['silver']} / {c['bronze']} / {c['none']} |")
    return lines


def markdown(res):
    out = ["# CCPC medal vs ICPC EC regional medal", "",
           "Generated by `scripts/ccpc_icpc_medals.py`. Same-season (CCPC station, ICPC regional) pairs of "
           "official teams, linked by school + >= 2 shared members. Ranks, percentiles and medals only.", "",
           f"Linked: {res['linked']}.", "",
           "## CCPC medal -> mainland ICPC regional (2023-2025)", "",
           "Share of pairs where the same team, at an ICPC mainland regional of the same season, got gold, "
           "silver or better, any medal, or official rank <= 75 (the 2026 EC-Final line).", ""]
    out += outcome_table(res["ccpc_to_mainland"], "rank <= 75")
    out += ["", "## Benchmark: medal at one mainland ICPC regional -> another (2023-2025)", ""]
    out += outcome_table(res["icpc_to_icpc"], "rank <= 75")
    out += ["", "## CCPC medal -> Hong Kong (2024-2025)", "",
            "Line = the 10th Hong Kong place under the 2026 rule (rank 37 in 2024, 32 in 2025).", ""]
    out += outcome_table(res["ccpc_to_hongkong"], "HK line")
    out += ["", "## By season (mainland): P(ICPC gold / silver+ / medal / rank <= 75)", "",
            "| season | CCPC gold | CCPC silver | CCPC bronze | no CCPC medal |", "|---|---|---|---|---|"]
    for s, t in res["by_season"].items():
        out.append(f"| {s} | " + " | ".join(
            f"{pct(v['gold'])} / {pct(v['silver+'])} / {pct(v['medal'])} / {pct(v['ecf_line'])} (n {v['n']})"
            for v in t.values()) + " |")
    out += ["", "## Even odds: the CCPC percentile where P(mainland ICPC outcome) = 50%", "",
            "| ICPC outcome | CCPC percentile (10–90%) | rank at a 260-team station |", "|---|---|---|"]
    for k, label in zip(OUTCOMES, ("gold", "silver or better", "any medal", "rank <= 75")):
        p, lo, hi = res["even_odds"][k]
        out.append(f"| {label} | {p:.3f} ({lo:.3f}–{hi:.3f}) | {p * 260:.0f} |")
    out += ["", "## By CCPC percentile (official rank / teams with >= 1 solve), mainland 2023-2025", "",
            "Observed share, then the logistic model at the bin's median percentile.", "",
            "| CCPC percentile | n | gold | silver+ | any medal | rank <= 75 |", "|---|---|---|---|---|---|"]
    for b in res["bins"]:
        out.append(f"| {b['lo']:.2f}–{b['hi']:.2f} | {b['n']} | " + " | ".join(
            f"{pct(b[k])} ({pct(b['model'][k][0])})" for k in OUTCOMES) + " |")
    if "run" in res:
        r = res["run"]
        out += ["", f"## Virtual run: {r['board']}, {r['solved']} solved / {r['penalty']} min", "",
                f"Official rank {r['rank']} of {r['effective']} (percentile {r['pct']:.3f}) -> "
                f"CCPC {r['medal'] or 'no medal'}. Medal lines on this board (last official rank: solved / penalty): "
                + "; ".join(f"{m} {v['rank']}: {v['solved']} / {v['penalty']}" for m, v in r["lines"].items()) + ".",
                "", "| mainland ICPC outcome | P | 10–90% (team bootstrap) | with this station's offset |",
                "|---|---|---|---|"]
        for k, label in zip(OUTCOMES, ("gold", "silver or better", "any medal", "rank <= 75")):
            p, lo, hi = r["predicted"][k]
            out.append(f"| {label} | {p:.0%} | {lo:.0%}–{hi:.0%} | {pct(r['with_station_offset'].get(k))} |")
    out += ["", "## Station offsets (log-odds, pooled slope fixed; > 0 = its teams did better at ICPC than "
            "their CCPC percentile implies)", "",
            "| board | gold | silver+ | any medal | rank <= 75 |", "|---|---|---|---|---|"]
    for b, offs in res["station_offsets"].items():
        out.append(f"| {b} | " + " | ".join(f"{offs[k]:+.2f}" for k in OUTCOMES) + " |")
    out += ["", "## CCPC boards", "", "| board | official | >= 1 solve | gold | silver | bronze | source |",
            "|---|---|---|---|---|---|---|"]
    for b in res["boards"]:
        out.append(f"| {b['board']} | {b['official']} | {b['effective']} | {b['gold']} | {b['silver']} | "
                   f"{b['bronze']} | {b['medal_source']} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", help="CCPC board of a virtual run, e.g. 11th/jinan")
    ap.add_argument("--solved", type=int)
    ap.add_argument("--penalty", type=int, default=0)
    args = ap.parse_args()

    ccpc, boards = [], {}
    for season, links in CCPC.items():
        for b in links:
            rows, info = ccpc_board(b)
            ccpc += [dict(r, season=season) for r in rows]
            boards[b] = (rows, info)
    icpc = icpc_rows(og.load()["regional_teams"])
    pairs = link(ccpc, icpc)
    model = [(c, r) for c, r in pairs if c["season"] in og.MODEL_SEASONS]
    mainland = [(c, r) for c, r in model if r["mainland"]]
    models = curve(mainland)
    res = dict(linked=f"{len(ccpc)} official CCPC entries, {len({id(c) for c, _ in pairs})} linked to >= 1 ICPC "
                      f"regional; {len(pairs)} pairs, {len(mainland)} mainland 2023-2025, "
                      f"{sum(not r['mainland'] for _, r in pairs)} Hong Kong",
               ccpc_to_mainland=table(mainland),
               icpc_to_icpc=table([(a, b) for a, b in icpc_pairs(icpc) if a["season"] in og.MODEL_SEASONS]),
               ccpc_to_hongkong=table([(c, r) for c, r in pairs if not r["mainland"]]),
               by_season={s: table([(c, r) for c, r in pairs if c["season"] == s and r["mainland"]]) for s in CCPC},
               even_odds=even_odds(models),
               bins=bins(mainland, models),
               station_offsets=station_offsets(mainland, models),
               boards=[info for _, info in boards.values()])
    if args.board:
        rows, info = boards[args.board]
        res["run"] = dict(board=args.board, solved=args.solved, penalty=args.penalty,
                          **place(rows, info, args.solved, args.penalty))
        res["run"]["predicted"] = predict(models, res["run"]["pct"])
        x, offs = logit(res["run"]["pct"]), res["station_offsets"].get(args.board, {})
        res["run"]["with_station_offset"] = {k: 1 / (1 + math.exp(-(w[0] + w[1] * x + offs[k])))
                                             for k, (w, _) in models.items() if k in offs}
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(res["linked"])
    print(f"-> {OUT.relative_to(og.ROOT)}.json / .md")


if __name__ == "__main__":
    main()
