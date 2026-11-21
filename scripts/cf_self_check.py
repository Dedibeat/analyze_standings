#!/usr/bin/env python3
"""Is one Codeforces player improving, net of the AI-era deflation of the field?

    ./.venv/bin/python scripts/cf_self_check.py Dedibeat     # ~2 min

Reads the cache of scripts/cf_ai_deflation.py (data/cf_ai/). The base half-year is 2024H2, the last
one before the January 2025 onset. For every later half-year the player's change since the base is
compared with peers: accounts with >= 10 rated contests before the base half-year whose base rating
level was within +-50 of the player's.

- Rating level: mean internal rating after the account's rated contests of a half-year (>= 3 contests).
- Solve level: the rating x at which the account's in-contest solves are 50% likely under Codeforces'
  curve 1 / (1 + 10^((R - x) / 400)), fitted on every rated problem of its rated rounds in that
  half-year (where the rating level exists; standings since 2021, Div. 3/4 list trusted participants
  only; problems still unrated when fetched are left out). It uses
  what was solved, not the rank, so other contestants move it only through the problem ratings, and
  the peers solve on that same scale.
- AI era: base 2024H2. Pre-AI: bases 2021H1, 2021H2 and 2022H1, followed for the same number of
  half-years (all end by 2024H1). Their mean is the normal drift of a player at that level.
- vs peers = own change - AI-era peer mean. Net of deflation = own change - (AI-era peer mean -
  pre-AI peer mean), i.e. vs peers + pre-AI drift.
- Peer sets: all established accounts, and "young" ones (new accounts first rated within 12 months
  before the base half-year), because young accounts improve faster.

Output: output/cf_self_check_<handle>.json and tables on stdout.
"""
import gzip
import json
import sys
from datetime import datetime, timezone

import numpy as np

import cf_ai_deflation as cfd

BASE_AI, BASES_PRE, STEPS = 13, (6, 7, 8), 4  # half-year index (year - 2018) * 2 + half: 2024H2; 2021H1..2022H1
MIN_N, TOL, YOUNG = 3, 50, 365 * 86400
GRID = np.arange(600, 3601, 10.0)


def hy_name(i):
    return f"{2018 + i // 2}H{1 + i % 2}"


def hy_start(i):
    return datetime(2018 + i // 2, 1 + 6 * (i % 2), 1, tzinfo=timezone.utc).timestamp()


def main(handle):
    a, _, _, _, hid = cfd.build()
    me = hid[handle]
    ut, inv = np.unique(a["t"], return_inverse=True)
    hy = (np.array([cfd.month(int(t)) for t in ut]) // 6)[inv]
    cid_hy = dict(zip(a["cid"].tolist(), hy.tolist()))

    # rating level per (account, half-year): mean internal rating after its contests, contests, contests before
    key = a["h"].astype(np.int64) * 64 + hy
    uk, idx, cnt = np.unique(key, return_inverse=True, return_counts=True)
    r_mean = np.bincount(idx, weights=a["new"]) / cnt
    k_before = np.full(len(uk), 1 << 30)
    np.minimum.at(k_before, idx, a["k"])
    first_t = np.full(int(a["h"].max()) + 1, np.iinfo(np.int64).max)
    np.minimum.at(first_t, a["h"], a["t"])
    fresh = np.zeros(len(first_t), bool)
    fresh[a["h"][a["k"] == 0]] = a["fresh"][a["k"] == 0]
    uh, uy = uk // 64, uk % 64

    def rating(h, y):
        """Rating level of accounts h in half-year y, NaN where fewer than MIN_N contests."""
        j = np.clip(np.searchsorted(uk, np.asarray(h, np.int64) * 64 + y), 0, len(uk) - 1)
        ok = (uk[j] == np.asarray(h) * 64 + y) & (cnt[j] >= MIN_N)
        return np.where(ok, r_mean[j], np.nan)

    target = float(rating([me], BASE_AI)[0])
    peers = {}  # (set, base) -> account ids
    for b in (BASE_AI,) + BASES_PRE:
        s = (uy == b) & (cnt >= MIN_N) & (k_before >= cfd.VET) & (np.abs(r_mean - target) <= TOL) & (uh != me)
        young = fresh[uh] & (first_t[uh] >= hy_start(b) - YOUNG)
        peers[("all", b)], peers[("young", b)] = uh[s], uh[s & young]

    # solve level per (account, half-year) from the standings, for the player and every peer
    need = set(np.concatenate(list(peers.values())).tolist()) | {me}
    inv_h = {i: h for h, i in hid.items() if i in need}
    K, R, Y = [], [], []
    for f in sorted(cfd.ST.glob("*.json.gz")):
        d = json.loads(gzip.decompress(f.read_bytes()))
        y = cid_hy.get(d["cid"])
        rated = [(j, r) for j, (_, r) in enumerate(d["problems"]) if r is not None]
        if y is None or not rated or not d["rows"]:
            continue
        for h, _, times in d["rows"]:
            i = hid.get(h)
            if i in inv_h:
                for j, r in rated:
                    K.append(i * 64 + y), R.append(r), Y.append(times[j] >= 0)
    K, R, Y = np.array(K, np.int64), np.array(R, float), np.array(Y, float)
    sk, sidx = np.unique(K, return_inverse=True)
    ll = np.empty((len(GRID), len(sk)))
    for g, x in enumerate(GRID):
        p = 1 / (1 + 10 ** ((R - x) / 400))
        ll[g] = np.bincount(sidx, weights=Y * np.log(p) + (1 - Y) * np.log1p(-p), minlength=len(sk))
    s_level = GRID[ll.argmax(0)]

    def solve(h, y):
        j = np.clip(np.searchsorted(sk, np.asarray(h, np.int64) * 64 + y), 0, len(sk) - 1)
        ok = sk[j] == np.asarray(h) * 64 + y
        return np.where(ok & ~np.isnan(rating(h, y)), s_level[j], np.nan)

    out = {"handle": handle, "base": hy_name(BASE_AI), "tolerance": TOL, "player": {}, "measures": {}}
    for y in range(BASE_AI, BASE_AI + STEPS + 1):
        out["player"][hy_name(y)] = {"rating_level": round(float(rating([me], y)[0]), 1),
                                     "contests": int(((uh == me) & (uy == y)) @ cnt),
                                     "solve_level": float(solve([me], y)[0])}
    for mname, fn in (("rating_level", rating), ("solve_level", solve)):
        own0 = float(fn([me], BASE_AI)[0])
        for pset in ("all", "young"):
            rows = []
            for d in range(1, STEPS + 1):
                own = float(fn([me], BASE_AI + d)[0]) - own0
                p = peers[(pset, BASE_AI)]
                ch = fn(p, BASE_AI + d) - fn(p, BASE_AI)
                ch = ch[~np.isnan(ch)]
                pre = []
                for b in BASES_PRE:
                    q = peers[(pset, b)]
                    c = fn(q, b + d) - fn(q, b)
                    pre.append(float(np.nanmean(c)))
                ai, drift = float(ch.mean()), float(np.mean(pre))
                rows.append({"half_year": hy_name(BASE_AI + d), "own_change": round(own, 1),
                             "peers_n": int(len(ch)), "peers_mean": round(ai, 1),
                             "peers_q25_q75": [round(float(v), 1) for v in np.percentile(ch, [25, 75])],
                             "own_percentile": round(float((ch < own).mean() * 100), 1),
                             "pre_ai_drift": round(drift, 1), "pre_ai_by_base": [round(v, 1) for v in pre],
                             "deflation": round(ai - drift, 1),
                             "vs_peers": round(own - ai, 1), "net_of_deflation": round(own - ai + drift, 1)})
            out["measures"][f"{mname}/{pset}"] = {"own_base": own0,
                                                  "peers_base_n": {hy_name(b): int(len(peers[(pset, b)]))
                                                                   for b in (BASE_AI,) + BASES_PRE},
                                                  "rows": rows}

    print(f"{handle}: half-year levels (internal rating; solve level on CF problem ratings)")
    for y, v in out["player"].items():
        print(f"  {y}: rating {v['rating_level']:.0f} over {v['contests']} contests, solve level {v['solve_level']:.0f}")
    for m, v in out["measures"].items():
        print(f"\n== {m}: change since {out['base']} (base {v['own_base']:.0f}; peers at base {v['peers_base_n']})")
        print("  half-year  own   peers(n, mean, q25..q75)   pct  pre-AI drift  deflation  vs peers  net of deflation")
        for r in v["rows"]:
            print(f"  {r['half_year']}  {r['own_change']:+5.0f}   {r['peers_n']:5d} {r['peers_mean']:+5.0f} "
                  f"{r['peers_q25_q75'][0]:+5.0f}..{r['peers_q25_q75'][1]:+4.0f}   {r['own_percentile']:4.0f}  "
                  f"{r['pre_ai_drift']:+5.0f} {r['pre_ai_by_base']}  {r['deflation']:+5.0f}  {r['vs_peers']:+5.0f}  "
                  f"{r['net_of_deflation']:+5.0f}")
    path = cfd.ROOT / "output" / f"cf_self_check_{handle}.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {path.relative_to(cfd.ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1])
