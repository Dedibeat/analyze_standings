#!/usr/bin/env python3
"""Hidden cycles and patterns in the techniques of ICPC Asia East regionals.

Same data as scripts/technique_forecast.py: named techniques, their derived
categories, DeepSeek general tags (ICPC only), CCPC 2024-2025 as a
replication.  Every test is a permutation test (fixed seed); p-values are
two-sided and Holm-adjusted within each family.

1. Season structure.  Similarity of two regionals by how many seasons apart
   they are: same season vs one apart, drift (slope over the gap) and a
   two-season cycle (gap 2 above the line through gaps 1 and 3).  Also each
   tag's zigzag: lag-1 autocorrelation of its per-season mean.  Null: season
   labels shuffled across contests.
2. Balancing inside a problem set.  Per-contest counts of a tag against
   problems dealt at random to the contests of the same season (contest sizes
   kept): variance ratio < 1 means more even than chance.  Also techniques
   used by two or more problems of one set.
3. Site style.  Same-site pairs (always different seasons) against
   different-site pairs from different seasons.  Null: site labels shuffled
   within each season.
4. ICPC and CCPC of the same season against different seasons (2024-2025).
   Null: season labels shuffled within each circuit.
5. Position.  Mean difficulty percentile of a tag's problems inside their
   contests (0 = easiest).  Null: positions shuffled inside each contest.

    python scripts/technique_patterns.py   ->  output/technique_patterns.md, .json
"""
import json
import math
import os
import random
from collections import Counter, defaultdict

import technique_forecast as tf

N = 4000
SEED = 2026


def p2(obs, null):
    """Two-sided permutation p: twice the smaller tail, at most 1."""
    lo = sum(x <= obs + 1e-12 for x in null)
    hi = sum(x >= obs - 1e-12 for x in null)
    return min(1.0, 2 * (min(lo, hi) + 1) / (len(null) + 1))


def variance(xs):
    m = tf.mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def cosine(a, b):
    dot = sum(v * b[k] for k, v in a.items() if k in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


MEASURES = {
    "technique Jaccard": lambda a, b: jaccard(a["tech"], b["tech"]),
    "category cosine": lambda a, b: cosine(a["cats"], b["cats"]),
    "general-tag cosine": lambda a, b: cosine(a["general"], b["general"]),
}


def profile(ps):
    """Named-technique set, derived-category counts and general-tag counts of one contest."""
    return {"tech": set().union(*(p["tech"] for p in ps)),
            "cats": Counter(g for p in ps for g in p["cats"]),
            "general": Counter(t for p in ps for t in (p["general"] or []))}


def pair_sims(group, measure, pairs=None):
    prof = {c: profile(ps) for c, ps in group.items()}
    cs = sorted(group)
    pairs = pairs or [(a, b) for i, a in enumerate(cs) for b in cs[i + 1:]]
    return {(a, b): MEASURES[measure](prof[a], prof[b]) for a, b in pairs}


def gap_means(sim, season):
    """Mean pair similarity by season gap."""
    tot, n = Counter(), Counter()
    for (a, b), s in sim.items():
        g = abs(season[a] - season[b])
        tot[g] += s
        n[g] += 1
    return {g: tot[g] / n[g] for g in sorted(n)}


def gap_stats(m):
    """(same season - one apart, slope over gaps, gap 2 - mean of gaps 1 and 3)."""
    gs = sorted(m)
    mg, mv = tf.mean(gs), tf.mean([m[g] for g in gs])
    slope = sum((g - mg) * (m[g] - mv) for g in gs) / sum((g - mg) ** 2 for g in gs)
    return m[0] - m[1], slope, m[2] - (m[1] + m[3]) / 2


def shuffled(labels, rng, within=None):
    """labels {contest: value} shuffled, optionally only among contests with the same `within` key."""
    blocks = defaultdict(list)
    for c in sorted(labels):
        blocks[within[c] if within else 0].append(c)
    out = {}
    for cs in blocks.values():
        vals = [labels[c] for c in cs]
        rng.shuffle(vals)
        out.update(zip(cs, vals))
    return out


def season_gaps(group, rng, n=N):
    season = {c: ps[0]["season"] for c, ps in group.items()}
    rows = []
    for name in MEASURES:
        sim = pair_sims(group, name)
        obs = gap_means(sim, season)
        null = [gap_means(sim, shuffled(season, rng)) for _ in range(n)]
        o, ns = gap_stats(obs), [gap_stats(m) for m in null]
        rows.append({"measure": name, "by_gap": obs,
                     "null_by_gap": {g: tf.mean([m[g] for m in null]) for g in obs},
                     "stats": [(s, o[i], p2(o[i], [x[i] for x in ns]))
                               for i, s in enumerate(("same season - 1 apart", "drift per season",
                                                      "2-season cycle"))]})
    return rows


def lag1(xs):
    m = tf.mean(xs)
    den = sum((x - m) ** 2 for x in xs)
    return sum((a - m) * (b - m) for a, b in zip(xs, xs[1:])) / den if den else 0.0


def zigzag(group, feats, rng, n=N):
    """Lag-1 autocorrelation of each tag's per-season mean count."""
    cs = sorted(group)
    cnt = {c: [sum(fn(p) for p in group[c]) for _, fn in feats] for c in cs}
    seasons = sorted({ps[0]["season"] for ps in group.values()})

    def series(season):
        by = defaultdict(list)
        for c in cs:
            by[season[c]].append(cnt[c])
        return [[tf.mean([r[i] for r in by[s]]) for s in seasons] for i in range(len(feats))]
    season = {c: group[c][0]["season"] for c in cs}
    obs_series = series(season)
    obs = [lag1(x) for x in obs_series]
    null = [[lag1(x) for x in series(shuffled(season, rng))] for _ in range(n)]
    pooled = (tf.mean(obs), p2(tf.mean(obs), [tf.mean(r) for r in null]))
    rows = [{"tag": f[0], "by_season": obs_series[i], "lag1": obs[i],
             "null_mean": tf.mean([r[i] for r in null]), "p": p2(obs[i], [r[i] for r in null])}
            for i, f in enumerate(feats)]
    return rows, pooled


def flags(group, feats):
    return {id(p): [i for i, (_, fn) in enumerate(feats) if fn(p)] for ps in group.values() for p in ps}


def deal(group, rng):
    """Problems dealt at random to the contests of the same season, contest sizes kept."""
    by = defaultdict(list)
    for c in sorted(group):
        by[group[c][0]["season"]].append(c)
    out = {}
    for cs in by.values():
        pool = [p for c in cs for p in group[c]]
        rng.shuffle(pool)
        for c in cs:
            out[c], pool = pool[:len(group[c])], pool[len(group[c]):]
    return out


def balance(group, feats, rng, n=N):
    fl = flags(group, feats)

    def stats(g):
        cnt = []
        dup = 0
        for ps in g.values():
            row = [0] * len(feats)
            for p in ps:
                for i in fl[id(p)]:
                    row[i] += 1
            cnt.append(row)
            dup += sum(v - 1 for v in Counter(k for p in ps for k in p["tech"]).values())
        return ([sum(r[i] > 0 for r in cnt) / len(cnt) for i in range(len(feats))],
                [variance([r[i] for r in cnt]) for i in range(len(feats))], dup)
    cover, var, dup = stats(group)
    null = [stats(deal(group, rng)) for _ in range(n)]
    rows = []
    for i, (name, _) in enumerate(feats):
        nv = [x[1][i] for x in null]
        if not tf.mean(nv):
            continue
        rows.append({"tag": name, "per_contest": tf.mean([sum(fl[id(p)].count(i) for p in ps)
                                                           for ps in group.values()]),
                     "cover": cover[i], "null_cover": tf.mean([x[0][i] for x in null]),
                     "var_ratio": var[i] / tf.mean(nv), "p": p2(var[i], nv)})
    nd = [x[2] for x in null]
    return rows, {"repeats": dup, "null_repeats": tf.mean(nd), "p": p2(dup, nd)}


def site_style(group, rng, n=N):
    season = {c: ps[0]["season"] for c, ps in group.items()}
    site = {c: ps[0]["site"] for c, ps in group.items()}

    def stat(sim, site):
        same = [v for (a, b), v in sim.items() if site[a] == site[b]]
        other = [v for (a, b), v in sim.items() if site[a] != site[b] and season[a] != season[b]]
        return tf.mean(same) - tf.mean(other), tf.mean(same), tf.mean(other)
    rows = []
    for name in MEASURES:
        sim = pair_sims(group, name)
        d, same, other = stat(sim, site)
        null = [stat(sim, shuffled(site, rng, season))[0] for _ in range(n)]
        per_site = {s: tf.mean([v for (a, b), v in sim.items() if site[a] == site[b] == s])
                    for s, k in Counter(site.values()).items() if k >= 2}
        rows.append({"measure": name, "same_site": same, "different_site": other, "diff": d,
                     "p": p2(d, null), "per_site": per_site})
    return rows


def same_season(icpc, ccpc, rng, n=N):
    group = {**icpc, **ccpc}
    season = {c: ps[0]["season"] for c, ps in group.items()}
    kind = {c: ps[0]["kind"] for c, ps in group.items()}
    pairs = [(a, b) for a in sorted(icpc) for b in sorted(ccpc)]

    def stat(sim, season):
        same = [v for (a, b), v in sim.items() if season[a] == season[b]]
        other = [v for (a, b), v in sim.items() if season[a] != season[b]]
        return tf.mean(same) - tf.mean(other), tf.mean(same), tf.mean(other)
    rows = []
    for name in ("technique Jaccard", "category cosine"):
        sim = pair_sims(group, name, pairs)
        d, same, other = stat(sim, season)
        null = [stat(sim, shuffled(season, rng, kind))[0] for _ in range(n)]
        rows.append({"measure": name, "same_season": same, "different_season": other,
                     "diff": d, "p": p2(d, null)})
    return rows


def position(group, feats, rng, n=N):
    fl = flags(group, feats)
    ps_list = list(group.values())
    pct = [[(p["pos"] - 1) / (len(ps) - 1) for p in ps] for ps in ps_list]

    def sums():
        tot = [0.0] * len(feats)
        for ps, xs in zip(ps_list, pct):
            for p, x in zip(ps, xs):
                for i in fl[id(p)]:
                    tot[i] += x
        return tot
    obs = sums()
    null = []
    for _ in range(n):
        for xs in pct:
            rng.shuffle(xs)
        null.append(sums())
    count = Counter(i for ps in ps_list for p in ps for i in fl[id(p)])
    return [{"tag": name, "problems": count[i], "mean_percentile": obs[i] / count[i],
             "p": p2(obs[i], [x[i] for x in null])}
            for i, (name, _) in enumerate(feats) if count[i]]


def with_holm(rows, key="p"):
    for r, h in zip(rows, tf.holm([r[key] for r in rows])):
        r["holm_p"] = h
    return rows


def main():
    rng = random.Random(SEED)
    problems, taxonomy, _ = tf.load()
    feats, gen = tf.features(problems, taxonomy)
    reg, ccpc = tf.contests(problems, "regional"), tf.contests(problems, "ccpc")
    gaps = season_gaps(reg, rng)
    flat = [{"measure": g["measure"], "stat": s, "value": v, "p": p} for g in gaps for s, v, p in g["stats"]]
    zz, pooled = zigzag(reg, feats + gen, rng)
    bal = {"ICPC regionals 2022-2025": balance(reg, feats + gen, rng),
           "CCPC 2024-2025": balance(ccpc, feats, rng)}
    pos = {"ICPC regionals 2022-2025": with_holm(position(reg, feats + gen, rng)),
           "CCPC 2024-2025": with_holm(position(ccpc, feats, rng))}
    v = {"gaps": gaps, "gap_tests": with_holm(flat), "zigzag": with_holm(zz), "zigzag_pooled": pooled,
         "balance": {k: (with_holm(rows), dup) for k, (rows, dup) in bal.items()},
         "sites": with_holm(site_style(reg, rng)),
         "icpc_ccpc": with_holm(same_season(tf.contests(problems, "regional", {2024, 2025}), ccpc, rng)),
         "position": pos, "n_reg": len(reg), "n_ccpc": len(ccpc)}
    write_report(v)


def write_report(v):
    L = []
    w = L.append
    fp = tf.fmt_p
    w("# Hidden cycles and patterns in EC regional techniques\n")
    w(f"Generated by `scripts/technique_patterns.py` on the data of `technique_forecast.py`: "
      f"{v['n_reg']} ICPC Asia East regionals 2022-2025, {v['n_ccpc']} CCPC contests 2024-2025. "
      f"Permutation tests ({N} draws, seed {SEED}), two-sided; Holm p is adjusted within each "
      "table. With 4 seasons a cycle must be strong to show.\n")

    hits = [f"{fam}: {r.get('tag') or r.get('measure')}" + (f" ({r['stat']})" if "stat" in r else "")
            for fam, rows in (("season", v["gap_tests"]), ("zigzag", v["zigzag"]),
                              ("site", v["sites"]), ("ICPC-CCPC", v["icpc_ccpc"]))
            for r in rows if r["holm_p"] < 0.05]
    hits += [f"balance, {k}: {r['tag']}" for k, (rows, _) in v["balance"].items()
             for r in rows if r["holm_p"] < 0.05]
    hits += [f"position, {k}: {r['tag']}" for k, rows in v["position"].items()
             for r in rows if r["holm_p"] < 0.05]
    w("**Holm p < 0.05:** " + ("; ".join(hits) if hits else "none") + "\n")

    w("## 1. Season structure: drift, fashion, cycles\n")
    w("Mean similarity of two regionals by how many seasons apart they are (null mean in brackets).\n")
    w("| measure | same season | 1 apart | 2 apart | 3 apart |")
    w("|---|---|---|---|---|")
    for g in v["gaps"]:
        w(f"| {g['measure']} | " + " | ".join(f"{g['by_gap'][k]:.3f} ({g['null_by_gap'][k]:.3f})"
                                             for k in sorted(g["by_gap"])) + " |")
    w("\n| measure | test | value | p | Holm p |")
    w("|---|---|---|---|---|")
    for r in v["gap_tests"]:
        w(f"| {r['measure']} | {r['stat']} | {r['value']:+.4f} | {fp(r['p'])} | {fp(r['holm_p'])} |")
    po, pp = v["zigzag_pooled"]
    w(f"\nZigzag per tag: lag-1 autocorrelation of the per-season mean (negative = alternates "
      f"up/down; the null mean is negative too, since 4 points are demeaned). All tags pooled: "
      f"{po:+.3f}, p {fp(pp)}.\n")
    w("| tag | 2022 | 2023 | 2024 | 2025 | lag-1 | null mean | p | Holm p |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(v["zigzag"], key=lambda r: r["p"]):
        s = r["by_season"]
        w(f"| {r['tag']} | {s[0]:.2f} | {s[1]:.2f} | {s[2]:.2f} | {s[3]:.2f} | {r['lag1']:+.2f} | "
          f"{r['null_mean']:+.2f} | {fp(r['p'])} | {fp(r['holm_p'])} |")

    w("\n## 2. Balancing inside a problem set\n")
    w("Against problems dealt at random to the same season's contests. Cover = share of contests "
      "with at least one; variance ratio < 1 = spread more evenly than chance.\n")
    for k, (rows, dup) in v["balance"].items():
        w(f"**{k}**: problems repeating a named technique already used in the same set: "
          f"{dup['repeats']} (chance {dup['null_repeats']:.1f}), p {fp(dup['p'])}.\n")
        w("| tag | per contest | cover | cover by chance | variance ratio | p | Holm p |")
        w("|---|---|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: r["p"]):
            w(f"| {r['tag']} | {r['per_contest']:.2f} | {r['cover']:.0%} | {r['null_cover']:.0%} | "
              f"{r['var_ratio']:.2f} | {fp(r['p'])} | {fp(r['holm_p'])} |")
        w("")

    w("## 3. Site style\n")
    w("Same-site pairs vs different-site pairs from different seasons.\n")
    w("| measure | same site | different site | difference | p | Holm p |")
    w("|---|---|---|---|---|---|")
    for r in v["sites"]:
        w(f"| {r['measure']} | {r['same_site']:.3f} | {r['different_site']:.3f} | {r['diff']:+.3f} | "
          f"{fp(r['p'])} | {fp(r['holm_p'])} |")
    gen = next(r for r in v["sites"] if r["measure"] == "general-tag cosine")
    w("\nSame-site general-tag cosine by site: " +
      ", ".join(f"{s} {x:.2f}" for s, x in sorted(gen["per_site"].items(), key=lambda t: -t[1])) +
      f" (different sites {gen['different_site']:.2f}).\n")

    w("## 4. ICPC and CCPC in the same season\n")
    w("ICPC regionals 2024-2025 vs CCPC 2024-2025: pairs from the same season vs different seasons.\n")
    w("| measure | same season | different season | difference | p | Holm p |")
    w("|---|---|---|---|---|---|")
    for r in v["icpc_ccpc"]:
        w(f"| {r['measure']} | {r['same_season']:.3f} | {r['different_season']:.3f} | {r['diff']:+.3f} | "
          f"{fp(r['p'])} | {fp(r['holm_p'])} |")

    w("\n## 5. Position in the problem set\n")
    w("Mean difficulty percentile of the tag's problems inside their contest (0 = easiest, "
      "0.5 = anywhere).\n")
    for k, rows in v["position"].items():
        w(f"**{k}**\n")
        w("| tag | problems | mean percentile | p | Holm p |")
        w("|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: r["mean_percentile"]):
            w(f"| {r['tag']} | {r['problems']} | {r['mean_percentile']:.2f} | {fp(r['p'])} | "
              f"{fp(r['holm_p'])} |")
        w("")

    with open(os.path.join(tf.OUT, "technique_patterns.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    with open(os.path.join(tf.OUT, "technique_patterns.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
    print("wrote output/technique_patterns.md and output/technique_patterns.json")


if __name__ == "__main__":
    main()
