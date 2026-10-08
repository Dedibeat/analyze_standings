#!/usr/bin/env python3
"""EC-Final chance at each regional of a past season, from that season's online results.

A result typed in for each online round (e.g. a virtual run) is ranked in the
official online ranking of that round, giving online strength x.  Each
mainland site's real qualifying rank K comes from replaying that season's
round-robin (``ecfinal_cutoff``: 2025 had 239 mainland seats, 2024 is taken
as 240).  P(rank <= K) uses the online-only model of ``ecfinal_chance``
(2023-2025 linked mainland teams) twice: as known before the season (one
number per K), and with the site's actual field (a per-contest intercept
fitted at K with the slopes fixed).  Hong Kong uses the Hong Kong model at the
depth of its 10 places under the 2026 rule.

    python scripts/ecfinal_retro.py 2025 7/626 5/890
"""
import collections
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import ecfinal_chance as ch  # noqa: E402
import ecfinal_cutoff as ec  # noqa: E402

og, hk = ch.og, ch.hk


def online_rank(data, season, rnd, solved, penalty):
    ranked = [r for r in data["online_teams"] if r["season"] == season and r["round"] == rnd and r["rank"]]
    return 1 + sum(int(r["solved"]) > solved or (int(r["solved"]) == solved and int(r["penalty"]) < penalty)
                   for r in ranked)


def site_depths(season):
    """Real qualifying rank per mainland site: the deepest rank the walk examined there."""
    order, _, taken = ec.admits_by_depth(season)
    last = taken[(239 if season == "2025" else 240) - 1]
    k = int(last["official_rank"])
    return {s: k if order.index(s) <= order.index(last["site"]) else k - 1 for s in order}


def site_offset(rows, w, k):
    eta = np.array([ch.design(r["x"], k) @ w for r in rows])
    y = np.array([r["rank"] <= k for r in rows])
    d = 0.0
    for _ in range(30):
        z = og.sigmoid(eta + d)
        d += float(np.sum(y - z)) / float(np.sum(z * (1 - z)))
    return d


def main():
    season, results = sys.argv[1], sys.argv[2:]
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    ranks = [online_rank(data, season, str(i + 1), *map(int, res.split("/"))) for i, res in enumerate(results)]
    x = -float(np.mean(np.log(ranks)))
    print(f"{season} online ranks {ranks} (geometric mean #{math.exp(-x):.0f})")

    official, _ = ch.official_ranks()
    linked = og.link_regionals(data, strengths)
    rows = [dict(r, rank=official[k][0], h=ch.NO_HISTORY) for r in linked
            if r["season"] in og.MODEL_SEASONS and r["site"] not in og.EXCLUDED_SITES and r["link"]
            and (k := (r["season"], r["site"], r["school"], r["team"])) in official]
    w = ch.fit(rows, use_h=False)
    boots = ch.fit_boot(rows, np.random.default_rng(1))
    by_site = collections.defaultdict(list)
    for r in rows:
        if r["season"] == season:
            by_site[r["site"]].append(r)
    print(f"{'site':9s} {'K':>3s}  before the season (10-90%)   with the site's actual field")
    for site, k in sorted(site_depths(season).items(), key=lambda kv: -len(by_site[kv[0]])):
        p = ch.prob(w, x, k)
        lo, hi = np.percentile([ch.prob(b, x, k) for b in boots], [10, 90])
        d = site_offset(by_site[site], w, k)
        print(f"{site:9s} {k:3d}  {p:5.1%} ({lo:.1%}-{hi:.1%})          {float(og.sigmoid(ch.logit(p) + d)):5.1%}"
              f"  (offset {d:+.2f})")

    hk_all = [r for r in hk.link_hk(data, strengths) if r["site"] == "hongkong"]
    hk_rows = [dict(r, rank=int(r["official_rank"]), h=ch.NO_HISTORY) for r in hk_all if r["x"] is not None]
    depth = ch.hk_depth(season, linked, hk_all)
    p_hk = ch.prob(ch.fit(hk_rows, l2=1e-2, use_h=False), x, depth)
    print(f"hongkong  {depth:3d}  {p_hk:5.1%} (Hong Kong model; depth of 10 places under the 2026 rule)")


if __name__ == "__main__":
    main()
