"""Hand audit of problem ratings: EC boards, worst CF anchors, DE vs hierarchical gaps.

Run from the repository root (about 3 min):
    PYTHONUTF8=1 ./.venv/Scripts/python -m scripts.problem_rating_audit

Research only. Writes output/problem_rating_audit.json; nothing shipped changes.
HAND ratings are one reviewer's CF-scale judgments from the statements (and the
solution idea), roughly +-200 except sign-in problems (+-100). They are a sanity
panel, not labels: they were written after seeing both models' numbers.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from arch_a import elo
from arch_b import hier_binary as hb
from arch_b.calibrate import problem_cf

ROOT = Path(__file__).resolve().parents[1]
CFG = dict(sigma=300.0, tau=800.0, sigma_b=600.0, tau_b=400.0)  # hier_binary selection

# (contest_id, label): (hand CF, group, short reason)
HAND = {
    (1096, "D"): (800, "ec_signin", "count T vs D in 5 letters"),
    (1440, "F"): (800, "ec_signin", "majority string"),
    (1093, "I"): (800, "ec_signin", "n minus max letter count"),
    (1472, "D"): (900, "ec_signin", "range >= 10 gives 9, else brute force"),
    (2562, "G"): (1100, "ec_signin", "sort, simulate both orders"),
    (1197, "M"): (1200, "ec_signin", "simple greedy on a cycle"),
    (2581, "C"): (850, "ec_signin", "n even -> n/2, n/2; odd impossible"),
    (1865, "J"): (800, "ec_signin", "simulate an 8-team bracket"),
    (1821, "L"): (900, "ec_signin", "construct 100 values"),
    (1449, "C"): (850, "ec_signin", "small case analysis"),
    (2641, "I"): (900, "ec_signin", "balloon rules simulation"),
    (1071, "F"): (850, "ec_signin", "substring 'bie' with dedup"),
    (1051, "J"): (1000, "ec_signin", "at most two elements can be chosen"),
    (1053, "K"): (1200, "ec_signin", "count descents of the inverse"),
    (1485, "L"): (800, "ec_signin", "max(2, ceil) formula"),
    (1794, "M"): (800, "ec_signin", "count distinct solvers"),
    (1799, "F"): (800, "ec_signin", "simulate rating"),
    (2513, "G"): (1050, "ec_signin", "every adjacent comparator present"),
    (2513, "B"): (1100, "ec_online", "leave a contiguous block"),
    (2513, "A"): (1600, "ec_online", "freeze best/worst case implementation"),
    (2513, "I"): (1850, "ec_online", "Dijkstra on (bags, load)"),
    (2513, "M"): (2050, "ec_online", "n layers of tree relaxation"),
    (2513, "D"): (2150, "ec_online", "tree DP, +a/-a states"),
    (2513, "C"): (2250, "ec_online", "greedy matching of intervals to gaps"),
    (2513, "J"): (2500, "ec_online", "rotate, window inclusion-exclusion"),
    (2513, "F"): (2900, "ec_online", "interactive trapping construction"),
    (2513, "H"): (3100, "ec_online", "grid cut with rectangle penalties"),
    (2513, "K"): (3200, "ec_online", "Lagrange inversion, many queries"),
    (2513, "L"): (3400, "ec_online", "3 solvers; hard DS DP"),
    (2524, "D"): (1650, "ec_online", "sort, power-of-two coefficients"),
    (2524, "C"): (1700, "ec_online", "Hall-type bound for 3 students"),
    (2524, "E"): (2000, "ec_online", "XOR-zero counting recurrence"),
    (2524, "H"): (2100, "ec_online", "pairs (u,v) x derangements"),
    (2524, "I"): (2100, "ec_online", "polynomial interpolation in c"),
    (2524, "J"): (2500, "ec_online", "complete multipartite diameter pairs"),
    (2524, "K"): (2700, "ec_online", "subtrees minus two-centroid ones"),
    (2524, "A"): (2400, "ec_online", "hull + Steiner formula"),
    (2524, "L"): (3100, "ec_online", "persistent tree for index XOR, 64 MB"),
    (2524, "B"): (3200, "ec_online", "hard min-cut modelling"),
    (2524, "G"): (3350, "ec_online", "10 solvers; flow on medians"),
    (1435, "I"): (1400, "ec_regional", "sort conditions, check consistency"),
    (1435, "F"): (1700, "ec_regional", "find a commuting adjacent pair"),
    (1435, "C"): (1800, "ec_regional", "count k with (kP+1) xor (P-1) <= m"),
    (1435, "G"): (1850, "ec_regional", "prefix knapsack + suffix top-k"),
    (1435, "A"): (2050, "ec_regional", "BFS shapes, compare"),
    (1435, "L"): (2150, "ec_regional", "greedy from the top floor"),
    (1435, "M"): (2500, "ec_regional", "segment tree, monotone-stack merge"),
    (1435, "D"): (2650, "ec_regional", "small-to-large slope merge"),
    (1435, "K"): (2900, "ec_regional", "card-draw DP"),
    (1435, "E"): (3000, "ec_regional", "min-cost flow on the dual"),
    (1435, "H"): (3100, "ec_regional", "tiling construction"),
    (1435, "J"): (3400, "ec_regional", "7 solvers; suffix structure"),
    (1435, "B"): (3350, "ec_regional", "3 solvers; geometry search"),
    (3504, "H"): (800, "weak_na", "four cases"),
    (3504, "A"): (850, "weak_na", "centre words"),
    (3504, "B"): (1100, "weak_na", "case analysis"),
    (3504, "D"): (1150, "weak_na", "greedy counting"),
    (3504, "L"): (1500, "weak_na", "relative order mapping"),
    (3504, "K"): (1600, "weak_na", "pick safe x"),
    (3504, "E"): (1900, "weak_na", "connect three trees"),
    (3504, "C"): (2000, "weak_na", "feasible initial-load interval"),
    (3504, "M"): (2100, "weak_na", "maximal empty rectangles"),
    (3504, "F"): (2100, "weak_na", "binary search k + hashing"),
    (3504, "J"): (1850, "weak_na", "theorems given in the statement"),
    (1964, "F"): (1900, "strong_eu", "greedy subsequence avoidance"),
    (1964, "J"): (1900, "strong_eu", "characterise splits, n <= 100"),
    (1964, "C"): (2100, "strong_eu", "greedy grouping by three"),
    (1964, "A"): (2150, "strong_eu", "McGarvey-style construction"),
    (1964, "B"): (2700, "strong_eu", "binomial decomposition construction"),
    (1123, "B"): (2000, "anchor", "hitting-time DP, n <= 100"),
    (3297, "A"): (800, "anchor", "missing number of 1..5"),
    (2692, "E"): (1400, "anchor", "Minkowski shape + prefix counts"),
}

# Fresh blind panel (2026-11-10): the two most-solved problems of the 16 EC boards
# with statements that HAND does not touch. Rated from the statements alone, before
# any model rating or solve count for these problems was looked at. The group is
# the board's solve order (fresh_first = most solved), not the reviewer's view.
FRESH = {
    (1099, "H"): (800, "fresh_first", "k * ceil(l/b) * b"),
    (1099, "K"): (1100, "fresh_second", "min, or min/2 when some a is in (min, 2min]"),
    (1522, "B"): (1300, "fresh_first", "fewest digits, then smallest: DP from the back"),
    (1522, "E"): (1800, "fresh_second", "case analysis on d"),
    (1516, "M"): (1100, "fresh_first", "whole array, a prefix or a suffix"),
    (1516, "J"): (1300, "fresh_second", "pair queries, then 2-3 checks"),
    (1459, "J"): (1600, "fresh_first", "shortest path with a helper cycle"),
    (1459, "I"): (1500, "fresh_second", "small DP over refresh times"),
    (1784, "N"): (1200, "fresh_first", "outer loop, inner arithmetic series"),
    (1784, "G"): (1400, "fresh_second", "(prod(2e+1)+1)/2"),
    (1894, "I"): (1800, "fresh_first", "bipartite colouring, flip leaves"),
    (1894, "A"): (2100, "fresh_second", "greedy with a heap"),
    (1893, "K"): (1200, "fresh_first", "per row, (m-k)-th position"),
    (1893, "A"): (1150, "fresh_second", "merge letters, find a separating position"),
    (1885, "C"): (900, "fresh_first", "positions of the maximum"),
    (1885, "K"): (1500, "fresh_second", "subsequence check with fixed ends"),
    (1871, "J"): (1300, "fresh_first", "small case analysis"),
    (1871, "M"): (1400, "fresh_second", "diagonal construction"),
    (1828, "E"): (900, "fresh_first", "at most 6 shifts matter"),
    (1828, "J"): (1400, "fresh_second", "single gains plus best edge"),
    (1913, "C"): (1150, "fresh_first", "parity of l and 2l <= r"),
    (1913, "I"): (1150, "fresh_second", "sort, multiply k-1 at a time, mind zeros"),
    (3295, "B"): (2000, "fresh_first", "prefix conditions, counting DP"),
    (3295, "J"): (2200, "fresh_second", "path cover with an order constraint"),
    (2567, "G"): (1100, "fresh_first", "count multiples, pair them"),
    (2567, "J"): (900, "fresh_second", "two sums per paper"),
    (3169, "H"): (900, "fresh_first", "n-1 if two equal neighbours, else n-2"),
    (3169, "K"): (1800, "fresh_second", "best rotation among the minima"),
    (2908, "D"): (1450, "fresh_first", "3^n DP"),
    (2908, "H"): (1700, "fresh_second", "game characterisation"),
    (2609, "E"): (1500, "fresh_first", "invariants of the pair move"),
    (2609, "F"): (2200, "fresh_second", "greedy reach per layer"),
}


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def skipped_cells(ds):
    """No submission on a problem more of the board solved than the row's hardest solve."""
    row, prob, y = ds.obs_row, ds.obs_prob, ds.obs_y
    solved = ds.solved_count.astype(float)
    hardest = np.full(row.max() + 1, np.inf)
    np.minimum.at(hardest, row[y], solved[prob[y]])
    return (~y) & (ds.obs_wrong == 0) & (solved[prob] > hardest[row])


def fit_map(ds, keep, idx, cf):
    team = ds.team_of_row[ds.obs_row]
    res = hb.fit(ds, obs=(team[keep], ds.obs_prob[keep], ds.obs_y[keep].astype(float)), **CFG)
    s, i = np.polyfit(res["b"][idx], cf, 1)
    return np.clip(s * res["b"] + i, elo.LO, elo.HI), [float(s), float(i)]


def hand_scores(key, ratings, panel=HAND):
    out = {}
    for g in sorted({v[1] for v in panel.values()}) + ["all"]:
        ks = [k for k, v in panel.items() if g in ("all", v[1])]
        out[g] = {"n": len(ks)}
        for name, r in ratings.items():
            e = np.array([r[key[k]] - panel[k][0] for k in ks])
            out[g][name] = {"bias": round(float(e.mean()), 1), "rmse": round(float(np.sqrt((e ** 2).mean())), 1)}
    return out


def anchor_checks():
    pred = json.loads((ROOT / "output/hier_binary.json").read_text(encoding="utf-8"))
    full = pred["field_stability"]["predictions"]["full"]
    anchors = {a["row_id"]: a for a in json.loads((ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))}
    cfp = json.loads((ROOT / "data/cf_mirror_solves.json").read_text(encoding="utf-8"))["problems"]
    tagged = {c["contest_id"]: c for c in json.loads((ROOT / "data/tagged.json").read_text(encoding="utf-8"))}
    rows = []
    for r in full:
        a = anchors[r["row_id"]]
        name = next(p["problem_name"] for p in tagged[a["contest_id"]]["problems"] if p["problem_label"] == a["problem_label"])
        m = next(p for p in cfp if p["contest"] == r["cf_contest"] and p["name"].lower() == name.lower())
        rows.append({"contest_id": a["contest_id"], "label": a["problem_label"], "name": name, "cf_index": m["index"],
                     "cf": r["cf"], "cf_solved": m["solved"], "onsite_solve_rate": round(a["solve_rate"], 4),
                     "de": round(r["DE"], 1), "hb": round(r["hb"], 1)})
    for cid in {r["contest_id"] for r in rows}:
        g = [r for r in rows if r["contest_id"] == cid]
        on = sorted(g, key=lambda r: -r["onsite_solve_rate"])
        cfo = sorted(g, key=lambda r: -r["cf_solved"])
        for r in g:
            r["order_shift"] = on.index(r) - cfo.index(r)  # negative = easier onsite than on CF
    def rm(rs, k):
        return round(math.sqrt(sum((r[k] - r["cf"]) ** 2 for r in rs) / len(rs)), 1)
    drop = [r for r in rows if r["name"] != "Uniform Chemistry"]
    return {"worst": sorted(rows, key=lambda r: -max(abs(r["de"] - r["cf"]), abs(r["hb"] - r["cf"])))[:20],
            "largest_order_shift": sorted(rows, key=lambda r: -abs(r["order_shift"]))[:8],
            "loco_rmse": {"all": {"n": len(rows), "de": rm(rows, "de"), "hb": rm(rows, "hb")},
                          "without_uniform_chemistry": {"n": len(drop), "de": rm(drop, "de"), "hb": rm(drop, "hb")}}}


def main():
    hb._init()
    ds = hb._G["ds"]
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text(encoding="utf-8"))
    pi = {(cid, lab): p for p, (cid, lab, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors])
    cf = np.array([a["cf"] for a in anchors])
    shipped = problem_cf(ds.problems)
    de = np.array([shipped[(int(c), lab)] for c, lab, _, _ in ds.problems])
    skip = skipped_cells(ds)
    base, base_map = fit_map(ds, np.ones(len(skip), bool), idx, cf)
    alt, alt_map = fit_map(ds, ~skip, idx, cf)
    ratings = {"de": de, "hb": base, "hb_skip_missing": alt}
    hand = [{"contest_id": c, "label": lab, "hand": h, "group": g, "why": why,
             **{n: round(float(r[pi[(c, lab)]]), 1) for n, r in ratings.items()}}
            for (c, lab), (h, g, why) in HAND.items()]
    out = {"research_only": True,
           "sha256": {p: sha(p) for p in ("arch_b/hier_binary.py", "data/tagged.json", "data/de_stability_anchors.json",
                                          "data/cf_mirror_solves.json", "output/hier_binary.json")},
           "skipped_cells": {"cells": int(len(skip)), "skipped": int(skip.sum()),
                             "rows": int(len(np.unique(ds.obs_row[skip])))},
           "maps": {"hb": base_map, "hb_skip_missing": alt_map},
           "in_sample_anchor_rmse": {n: round(float(np.sqrt(np.mean((r[idx] - cf) ** 2))), 1) for n, r in ratings.items()},
           "hand_scores": hand_scores(pi, ratings), "hand": hand, "anchors": anchor_checks()}
    (ROOT / "output/problem_rating_audit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("skipped_cells", "maps", "in_sample_anchor_rmse", "hand_scores")}, indent=1))


if __name__ == "__main__":
    main()
