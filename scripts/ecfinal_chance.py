#!/usr/bin/env python3
"""Chance that a 2026 online team earns an EC-Final seat from each regional.

Mainland: a team qualifies at a site by finishing at or above that site's
qualifying rank K (``scripts/ecfinal_cutoff.py --project-2026``: ~75, 70-80)
unless already admitted or its school is capped (not binding for one team of
a school with few seats).  P(rank <= K) comes from a cumulative-logit model on
2023-2025 mainland teams linked to their online results
(``arch_b.online_gold.link_regionals``):

    logit P(rank <= K) = a + b x + c log K + d x log K

with x = -mean log online rank.  Absolute rank, not percentile of the field:
bigger fields add weak teams at the bottom, and the 2025 backtest (Shenyang
and Xi'an grew to ~400) is badly biased on percentile (expected 62-64 vs
actual 86-87 teams above the cutoff) and close on rank.
Hong Kong: up to 10 places to Hong Kong medal teams, skipping teams already
registered for the EC-Final and capped schools; the depth D of the 10th place
is replayed on 2024/2025 Hong Kong boards, and P(rank <= D) uses the same
model fitted on Hong Kong linked teams.

    python scripts/ecfinal_chance.py [--team NUM-R^3] [--school 蒙古国立大学]
"""
import collections
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_b import hk_link as hk  # noqa: E402
from arch_b import online_gold as og  # noqa: E402
import ecfinal_cutoff as ec  # noqa: E402

THRESHOLDS = (10, 20, 30, 45, 60, 75, 90, 110, 130, 160)
K_2026 = {70: 0.25, 75: 0.5, 80: 0.25}  # projected qualifying rank (ecfinal_cutoff --project-2026)
FIELD_2026 = ec.CAP_2026 | {"hongkong": 115}
HK_PLACES = 10
BOOTSTRAPS = 300


def official_ranks():
    out, size = {}, collections.Counter()
    for r in ec.ROWS:
        if r["official"] == "1" and r["official_rank"]:
            out[(r["season"], r["site"], r["school"], r["team"])] = int(r["official_rank"])
            size[(r["season"], r["site"])] += 1
    return out, size


def design(x, k):
    lk = math.log(k)
    return np.array([1.0, x, lk, x * lk])


def fit(rows, l2=1e-3):
    X, y = [], []
    for r in rows:
        for k in THRESHOLDS:
            X.append(design(r["x"], k))
            y.append(int(r["rank"] <= k))
    return og.logistic(X, y, l2=l2)


def fit_boot(rows, rng, n=BOOTSTRAPS):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["season"], r["site"])].append(r)
    keys = sorted(groups)
    return np.array([fit([r for j in rng.integers(0, len(keys), len(keys)) for r in groups[keys[j]]])
                     for _ in range(n)])


def prob(w, x, rank, n=None):
    return float(og.sigmoid(design(x, rank) @ w))


def hk_depth(season, mainland_rows, hk_rows, data, strengths):
    """Hong Kong rank of the HK_PLACES-th eligible medal team under the 2026 rule.

    Registered = the replayed mainland qualifiers (online key) plus each
    school's published / simulated seat count as its x."""
    _, _, taken = ec.admits_by_depth(season)
    taken = taken[:239 if season == "2025" else 240]
    keyed = {(r["school"], r["team"]): r["online_key"] for r in mainland_rows if r["season"] == season}
    registered = {keyed.get((t["school"], t["team"])) for t in taken} - {None}
    seats = collections.Counter(og.norm_school(t["school"]) for t in taken)
    got, depth = collections.Counter(), None
    for r in sorted((r for r in hk_rows if r["season"] == season), key=lambda r: int(r["official_rank"])):
        if not r["medal"]:
            break
        key = (season, r["online_school"], r["online_team"]) if r["online_school"] else None
        school = r["online_school"] or og.norm_school(r["school"])
        if key in registered or seats[school] + got[school] >= 3:
            continue
        got[school] += 1
        depth = int(r["official_rank"])
        if sum(got.values()) == HK_PLACES:
            break
    return depth


def main():
    team_q = sys.argv[sys.argv.index("--team") + 1] if "--team" in sys.argv else "NUM-R^3"
    school_q = sys.argv[sys.argv.index("--school") + 1] if "--school" in sys.argv else "蒙古国立大学"
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    ranks, size = official_ranks()
    linked = og.link_regionals(data, strengths)
    rows = []
    for r in linked:
        k = (r["season"], r["site"], r["school"], r["team"])
        if r["season"] in og.MODEL_SEASONS and r["site"] not in og.EXCLUDED_SITES and r["link"] and k in ranks:
            rows.append(dict(r, rank=ranks[k], n=size[(r["season"], r["site"])]))
    hk_all = [r for r in hk.link_hk(data, strengths) if r["site"] == "hongkong"]
    hk_rows = [dict(r, rank=int(r["official_rank"]), n=size[(r["season"], r["site"])])
               for r in hk_all if r["x"] is not None]
    rng = np.random.default_rng(1)

    # Backtest: train 2023-2024, predict 2025 counts above the real qualifying rank.
    w_bt = fit([r for r in rows if r["season"] != "2025"])
    print("Backtest 2025 (train 2023-2024): linked teams at or above the site's qualifying rank")
    walk = {"wuhan": 91, "shenyang": 91, "xian": 90, "nanjing": 90, "chengdu": 90, "shanghai": 90}
    for site, k in walk.items():
        test = [r for r in rows if r["season"] == "2025" and r["site"] == site]
        exp = sum(prob(w_bt, r["x"], k, r["n"]) for r in test)
        act = sum(r["rank"] <= k for r in test)
        print(f"  {site}: expected {exp:.1f}, actual {act} (of {len(test)} linked)")
    for lo, hi in ((1, 150), (151, 400), (401, 800), (801, 10 ** 6)):
        band = [r for r in rows if r["season"] == "2025" and lo <= math.exp(-r["x"]) <= hi]
        exp = np.mean([prob(w_bt, r["x"], walk[r["site"]], r["n"]) for r in band])
        act = np.mean([r["rank"] <= walk[r["site"]] for r in band])
        print(f"  online #{lo}-{hi if hi < 10 ** 6 else '+'}: predicted {exp:.1%}, actual {act:.1%} ({len(band)} teams)")

    w, boots = fit(rows), fit_boot(rows, rng)
    w_hk, boots_hk = fit(hk_rows, l2=1e-2), fit_boot(hk_rows, rng)
    depths = {s: hk_depth(s, linked, hk_all, data, strengths) for s in ("2024", "2025")}
    print(f"Hong Kong: 10th eligible medal team at rank {depths} (2026 rule replayed)")

    teams = [(k, t) for k, t in strengths.items() if k[0] == "2026" and school_q in t["school"]]
    for (_, _, _), t in sorted(teams, key=lambda kv: -kv[1]["x"]):
        if team_q not in ("*", t["team"]):
            continue
        x = t["x"]
        print(f"\n{t['team']} (online ranks {t['ranks']}, geometric mean #{math.exp(-x):.0f}); "
              f"P(qualify | attends), 10-90% over model uncertainty:")
        for site in sorted(ec.CAP_2026, key=lambda s: -ec.CAP_2026[s]):
            n = FIELD_2026[site]
            p = sum(wk * prob(w, x, k, n) for k, wk in K_2026.items())
            draws = [sum(wk * prob(b, x, k, n) for k, wk in K_2026.items()) for b in boots]
            lo, hi = np.percentile(draws, [10, 90])
            print(f"  {site:9s} field {n}: {p:5.1%}  ({lo:.1%}-{hi:.1%}); at K=70 {prob(w, x, 70, n):.1%}, "
                  f"K=80 {prob(w, x, 80, n):.1%}")
        n = FIELD_2026["hongkong"]
        ds = [d for d in depths.values() if d]
        p = np.mean([prob(w_hk, x, d, n) for d in ds])
        draws = [np.mean([prob(b, x, d, n) for d in ds]) for b in boots_hk]
        lo, hi = np.percentile(draws, [10, 90])
        print(f"  hongkong  field {n}: {p:5.1%}  ({lo:.1%}-{hi:.1%}); needs rank <= {ds}")


if __name__ == "__main__":
    main()
