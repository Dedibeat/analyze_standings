#!/usr/bin/env python3
"""Named techniques in ICPC Asia East regionals, a 2026 forecast, and a CCPC test.

Techniques are the named-technique extraction of ../llm-integration
(``extract_techniques.py``, Gemini; 128-id taxonomy in
``techniques_taxonomy.md``), as embedded in the Technique Atlas
``../my-react-app/data/techniques_viewer.html``.  ``--snapshot`` copies it to
``data/techniques_atlas.json`` (ids, tiers, confidences; evidence text dropped).
A technique "appears" in a problem when it is a primary or secondary tag;
freeform ``named_extras`` are not counted.  About half the problems carry no
named technique (``no_match``): the extractor leaves out ambient basics
(generic dp/greedy, sorting, plain binary search, modular arithmetic).

The named techniques have no general tags (graph, dp, ...).  General
categories are therefore *derived* from the taxonomy's category of each named
technique, the same way for ICPC and CCPC.  The DeepSeek general tags
(``primary_tags`` in data/tagged.json) exist for ICPC only and are reported
separately, together with how much of each general tag the derived category
catches.

Forecast: P(technique appears in a regional) is a recency-weighted presence
rate shrunk toward its taxonomy category's mean rate,

    p_k = (sum_c w_c y_ck + alpha * m_cat(k)) / (sum_c w_c + alpha),
    w_c = decay ** (last_season - season_c),

with alpha and decay tuned on 2022-2023 -> 2024 and tested on
2022-2024 -> 2025 ICPC and on the CCPC 2024-2025 sites and finals.

    python scripts/technique_forecast.py --snapshot ../my-react-app/data/techniques_viewer.html
    python scripts/technique_forecast.py   ->  output/technique_forecast.md, .json
"""
import argparse
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
ATLAS = os.path.join(DATA, "techniques_atlas.json")

# QOJ id -> (season, site); names checked against QOJ's category pages
# (ICPC > Regionals > Asia East Continent, CCPC > 第十/十一届) on 2026-10-10.
REGIONALS = {
    1051: (2022, "Xi'an"), 1053: (2022, "Jinan"), 1071: (2022, "Hangzhou"),
    1093: (2022, "Nanjing"), 1096: (2022, "Shenyang"), 1099: (2022, "Hong Kong"),
    1435: (2023, "Nanjing"), 1440: (2023, "Hefei"), 1449: (2023, "Shenyang"),
    1459: (2023, "Macau"), 1472: (2023, "Jinan"), 1516: (2023, "Hangzhou"),
    1784: (2023, "Xi'an"),
    1821: (2024, "Chengdu"), 1828: (2024, "Nanjing"), 1865: (2024, "Shenyang"),
    1871: (2024, "Kunming"), 1885: (2024, "Hong Kong"), 1893: (2024, "Hangzhou"),
    1913: (2024, "Shanghai"),
    2562: (2025, "Xi'an"), 2567: (2025, "Chengdu"), 2581: (2025, "Nanjing"),
    2609: (2025, "Wuhan"), 2641: (2025, "Shenyang"), 2908: (2025, "Shanghai"),
    3169: (2025, "Hong Kong"),
}
# 10th CCPC = 2024 season (its final was held May 2025), 11th = 2025.
# Not in the data: 2024 Chongqing (QOJ 1840), 2025 Harbin (2575, 1 problem),
# and all 2022-2023 CCPC contests.
CCPC = {1817: (2024, "Harbin"), 1843: (2024, "Jinan"), 1873: (2024, "Zhengzhou"),
        2036: (2024, "Final"), 2661: (2025, "Zhengzhou"), 2693: (2025, "Jinan"),
        3387: (2025, "Chongqing"), 3727: (2025, "Final")}
SITES_2026 = ["Xi'an", "Chengdu", "Wuhan", "Nanjing", "Shenyang", "Shanghai",
              "Hong Kong", "Nanchang"]
POSITIONS = [(1, 3), (4, 6), (7, 9), (10, 99)]  # rank by calibrated difficulty within a contest
SEED = 2026
ALPHAS = (1, 2, 4, 8, 16, 32, 64)
DECAYS = (0.25, 0.5, 0.75, 1.0)
EPS = 1e-4


def snapshot(html_path):
    """Copy the Technique Atlas data (minus evidence text) to data/techniques_atlas.json."""
    with open(html_path, encoding="utf-8") as f:
        text = f.read()
    dec = json.JSONDecoder()
    data, _ = dec.raw_decode(text, text.index("const DATA = ") + len("const DATA = "))
    tax, _ = dec.raw_decode(text, text.index("const TAXONOMY = ") + len("const TAXONOMY = "))
    slim = lambda tags: [{"id": t["id"], "confidence": t.get("confidence")} for t in tags]
    out = {
        "source": os.path.relpath(html_path, ROOT).replace(os.sep, "/"),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "taxonomy": [{"id": t["id"], "tier": t["tier"], "category": t["category"]} for t in tax],
        "problems": [{"contest_id": p["contest_id"], "problem_id": p["problem_id"],
                      "label": p["label"], "name": p["name"], "region": p["region"],
                      "year": p["year"], "primary": slim(p["primary"]),
                      "secondary": slim(p["secondary"]), "extras": p["extras"],
                      "no_match": p["no_match"]} for p in data],
    }
    with open(ATLAS, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {ATLAS}: {len(out['problems'])} problems, {len(out['taxonomy'])} taxonomy ids")


def load():
    """Problems of the regionals and CCPC contests, plus the taxonomy.

    Each problem: kind, season, site, cid, label, name, tech (primary or
    secondary ids), primary, cats (derived categories), general (DeepSeek
    primary_tags, ICPC only), diff (calibrated CF-scale difficulty).
    """
    with open(ATLAS, encoding="utf-8") as f:
        atlas = json.load(f)
    category = {t["id"]: t["category"] for t in atlas["taxonomy"]}
    with open(os.path.join(DATA, "tagged.json"), encoding="utf-8") as f:
        general = {(c["contest_id"], p["problem_id"]): p.get("primary_tags") or []
                   for c in json.load(f) for p in c["problems"]}
    with open(os.path.join(OUT, "problem_ratings_calibrated.json"), encoding="utf-8") as f:
        diff = {r["problem_id"]: r["difficulty_cf"] for r in json.load(f)}
    kinds = [("regional", REGIONALS), ("ccpc", CCPC)]
    problems = []
    for p in atlas["problems"]:
        for kind, table in kinds:
            if p["contest_id"] in table:
                season, site = table[p["contest_id"]]
                tech = {t["id"] for t in p["primary"] + p["secondary"]}
                problems.append({
                    "kind": kind, "season": season, "site": site, "cid": p["contest_id"],
                    "label": p["label"], "name": p["name"], "tech": tech,
                    "primary": {t["id"] for t in p["primary"]},
                    "cats": {category[t] for t in tech},
                    "general": general.get((p["contest_id"], p["problem_id"])) if kind != "ccpc" else None,
                    "diff": diff.get(p["problem_id"]),
                })
    for kind, _ in kinds:
        for ps in contests(problems, kind).values():
            for i, p in enumerate(sorted(ps, key=lambda p: p["diff"]), 1):
                p["pos"] = i
    return problems, atlas["taxonomy"], atlas["problems"]


def contests(problems, kind, seasons=None):
    """{cid: [problems]} of one kind, optionally limited to some seasons."""
    out = defaultdict(list)
    for p in problems:
        if p["kind"] == kind and (seasons is None or p["season"] in seasons):
            out[p["cid"]].append(p)
    return dict(out)


def presence(contest_problems, ids):
    """1 if any problem of the contest uses the technique."""
    used = set().union(*(p["tech"] for p in contest_problems))
    return {k: int(k in used) for k in ids}


def fit(train, ids, category, alpha, decay):
    """Recency-weighted presence rate per technique, shrunk toward its category mean."""
    last = max(ps[0]["season"] for ps in train.values())
    w = {c: decay ** (last - ps[0]["season"]) for c, ps in train.items()}
    wsum = sum(w.values())
    rate = {k: 0.0 for k in ids}
    for c, ps in train.items():
        for k, y in presence(ps, ids).items():
            rate[k] += w[c] * y
    raw = {k: rate[k] / wsum for k in ids}
    by_cat = defaultdict(list)
    for k in ids:
        by_cat[category[k]].append(raw[k])
    m = {g: sum(v) / len(v) for g, v in by_cat.items()}
    return {k: (rate[k] + alpha * m[category[k]]) / (wsum + alpha) for k in ids}


def logloss(pred, test, ids):
    """Mean per-(contest, technique) log loss and Brier score."""
    ll = br = n = 0
    for ps in test.values():
        for k, y in presence(ps, ids).items():
            q = min(max(pred[k], EPS), 1 - EPS)
            ll -= math.log(q if y else 1 - q)
            br += (q - y) ** 2
            n += 1
    return ll / n, br / n


def coverage(pred, test, top_n):
    """Share of test problems with a named primary technique that has one in the top-N list."""
    top = set(sorted(pred, key=lambda k: -pred[k])[:top_n])
    need = [p for ps in test.values() for p in ps if p["primary"]]
    return sum(bool(p["primary"] & top) for p in need) / len(need), len(need)


def uniform(train, ids):
    """Every technique gets the mean presence rate (ignores which technique it is)."""
    rate = sum(sum(presence(ps, ids).values()) for ps in train.values()) / (len(train) * len(ids))
    return {k: rate for k in ids}


def random_coverage(test, top_n, n_ids):
    """Expected coverage of a random top-N list."""
    need = [p for ps in test.values() for p in ps if p["primary"]]
    miss = lambda m: math.comb(n_ids - m, top_n) / math.comb(n_ids, top_n)
    return sum(1 - miss(len(p["primary"])) for p in need) / len(need)


def tune(problems, ids, category):
    """(alpha, decay) with the lowest log loss on 2022-2023 -> 2024 regionals."""
    train = contests(problems, "regional", {2022, 2023})
    val = contests(problems, "regional", {2024})
    grid = {(a, d): logloss(fit(train, ids, category, a, d), val, ids)[0]
            for a in ALPHAS for d in DECAYS}
    return min(grid, key=grid.get), grid


def boot_gain(base, model, test, ids, rng, n=2000):
    """Mean log-loss gain (base - model) per cell, with a 90% bootstrap over test contests."""
    gains = [logloss(base, {c: ps}, ids)[0] - logloss(model, {c: ps}, ids)[0] for c, ps in test.items()]
    means = sorted(sum(rng.choice(gains) for _ in gains) / len(gains) for _ in range(n))
    return sum(gains) / len(gains), means[int(0.05 * n)], means[int(0.95 * n)]


def calibration(pred, test, ids, cuts=(0.05, 0.1, 0.2, 1.01)):
    """Mean forecast vs observed presence rate in forecast bins."""
    bins = defaultdict(lambda: [0, 0.0, 0])
    for ps in test.values():
        for k, y in presence(ps, ids).items():
            b = next(c for c in cuts if pred[k] < c)
            bins[b][0] += 1
            bins[b][1] += pred[k]
            bins[b][2] += y
    return [(c, n, f / n, y / n) for c, (n, f, y) in sorted(bins.items())]


def site_test(problems, ids, category, alpha, decay, betas=(2, 4, 8, 16)):
    """Pooled forecast vs one shrunk toward the site's own past regionals (beta = prior weight)."""
    rows = []
    for train_s, test_s in (({2022, 2023}, 2024), ({2022, 2023, 2024}, 2025)):
        train = contests(problems, "regional", train_s)
        test = contests(problems, "regional", {test_s})
        pooled = fit(train, ids, category, alpha, decay)
        hist = {c: ps for c, ps in test.items()
                if any(t[0]["site"] == ps[0]["site"] for t in train.values())}
        row = {"season": test_s, "sites": sorted(ps[0]["site"] for ps in hist.values()),
               "pooled": logloss(pooled, hist, ids)[0]}
        for b in betas:
            total = 0.0
            for c, ps in hist.items():
                own = [presence(t, ids) for t in train.values() if t[0]["site"] == ps[0]["site"]]
                pred = {k: (sum(o[k] for o in own) + b * pooled[k]) / (len(own) + b) for k in ids}
                total += logloss(pred, {c: ps}, ids)[0]
            row[f"beta={b}"] = total / len(hist)
        rows.append(row)
    return rows


def counts(group, fn):
    return [sum(fn(p) for p in ps) for ps in group.values()]


def mean(xs):
    return sum(xs) / len(xs)


def trend(group, fn, rng, n=4000):
    """OLS slope of per-contest count on season; permutation p (seasons shuffled across contests)."""
    xs, ys = [ps[0]["season"] for ps in group.values()], counts(group, fn)
    my = mean(ys)

    def slope(x):
        mx = mean(x)
        return sum((a - mx) * (b - my) for a, b in zip(x, ys)) / sum((a - mx) ** 2 for a in x)
    obs = slope(xs)
    hits = sum(abs(slope(rng.sample(xs, len(xs)))) >= abs(obs) - 1e-12 for _ in range(n))
    return obs, (hits + 1) / (n + 1)


def diff_test(a, b, fn, rng, n=4000):
    """Per-contest means of a and b; permutation p for the difference."""
    ya, yb = counts(a, fn), counts(b, fn)
    obs, pool, hits = mean(ya) - mean(yb), ya + yb, 0
    for _ in range(n):
        rng.shuffle(pool)
        hits += abs(mean(pool[:len(ya)]) - mean(pool[len(ya):])) >= abs(obs) - 1e-12
    return mean(ya), mean(yb), (hits + 1) / (n + 1)


def holm(ps):
    """Holm-adjusted p-values, in input order."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def features(problems, taxonomy):
    """(name, fn) pairs: derived categories, '(no named technique)', and general tags."""
    cats = sorted({t["category"] for t in taxonomy})
    out = [(g, lambda p, g=g: g in p["cats"]) for g in cats]
    out.append(("(no named technique)", lambda p: not p["tech"]))
    general = Counter(t for p in problems if p["kind"] == "regional" for t in p["general"])
    gen = [(f"general:{t}", lambda p, t=t: t in p["general"]) for t, n in general.most_common() if n >= 10]
    return out, gen


def position_profile(group, top=8):
    rows = []
    for lo, hi in POSITIONS:
        ps = [p for v in group.values() for p in v if lo <= p["pos"] <= hi]
        if not ps:
            continue
        gen = Counter(t for p in ps for t in (p["general"] or []))
        diffs = sorted(p["diff"] for p in ps)
        rows.append({
            "positions": f"{lo}-{hi}" if hi < 99 else f"{lo}+",
            "per_contest": len(ps) / len(group),
            "median_cf": diffs[len(diffs) // 2],
            "named_share": sum(bool(p["tech"]) for p in ps) / len(ps),
            "general": [(t, n / len(group)) for t, n in gen.most_common(top)],
            "techniques": Counter(k for p in ps for k in p["tech"]).most_common(top),
            "categories": Counter(g for p in ps for g in p["cats"]).most_common(),
        })
    return rows


def forecast_rows(train, taxonomy, alpha, decay):
    ids = [t["id"] for t in taxonomy]
    category = {t["id"]: t["category"] for t in taxonomy}
    pred = fit(train, ids, category, alpha, decay)
    seen, probs, pos = Counter(), Counter(), defaultdict(list)
    for ps in train.values():
        for k, y in presence(ps, ids).items():
            seen[k] += y
        for p in ps:
            for k in p["tech"]:
                probs[k] += 1
                pos[k].append(p["pos"])
    n, sites = len(train), len(SITES_2026)
    rows = [{"id": t["id"], "category": t["category"], "tier": t["tier"], "p": pred[t["id"]],
             "expected_regionals_of_8": sites * pred[t["id"]],
             "p_any_of_8": 1 - (1 - pred[t["id"]]) ** sites,
             "seen_regionals": seen[t["id"]], "of": n, "problems": probs[t["id"]],
             "median_position": sorted(pos[t["id"]])[len(pos[t["id"]]) // 2] if pos[t["id"]] else None}
            for t in taxonomy]
    return sorted(rows, key=lambda r: (-r["p"], r["id"]))


def fmt_p(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--snapshot", metavar="HTML", help="refresh data/techniques_atlas.json from the atlas page")
    args = ap.parse_args()
    if args.snapshot:
        snapshot(args.snapshot)
        return
    rng = random.Random(SEED)
    problems, taxonomy, _ = load()
    ids = [t["id"] for t in taxonomy]
    category = {t["id"]: t["category"] for t in taxonomy}
    reg = lambda s=None: contests(problems, "regional", s)
    ccpc = lambda s=None: contests(problems, "ccpc", s)
    (alpha, decay), grid = tune(problems, ids, category)

    # Held-out tests: one model fitted on 2022-2024 regionals, two test sets.
    train = reg({2022, 2023, 2024})
    model, base = fit(train, ids, category, alpha, decay), uniform(train, ids)
    cat_only = fit(train, ids, category, 1e9, decay)
    seen = set().union(*(p["tech"] for ps in train.values() for p in ps))
    test_rows = []
    for name, test in (("ICPC regionals 2025", reg({2025})), ("CCPC 2024-2025", ccpc())):
        need = [p for ps in test.values() for p in ps if p["primary"]]
        ll, br = logloss(model, test, ids)
        ll_u, br_u = logloss(base, test, ids)
        test_rows.append({
            "test": name, "contests": len(test), "problems": sum(len(ps) for ps in test.values()),
            "named_problems": len(need),
            "novel_share": sum(not (p["primary"] & seen) for p in need) / len(need),
            "logloss_model": ll, "logloss_uniform": ll_u,
            "logloss_category_only": logloss(cat_only, test, ids)[0],
            "brier_model": br, "brier_uniform": br_u,
            "gain_vs_uniform": boot_gain(base, model, test, ids, rng),
            "coverage": {n: (coverage(model, test, n)[0], random_coverage(test, n, len(ids)))
                         for n in (10, 20, 30)},
            "calibration": calibration(model, test, ids),
        })
    with_ccpc = dict(train)
    with_ccpc.update(ccpc({2024}))
    added = {"logloss_icpc_only": test_rows[0]["logloss_model"],
             "logloss_icpc_plus_ccpc2024":
                 logloss(fit(with_ccpc, ids, category, alpha, decay), reg({2025}), ids)[0]}
    sites = site_test(problems, ids, category, alpha, decay)

    # Profiles, trends and ICPC-vs-CCPC differences.
    all_reg = reg()
    feats, gen = features(problems, taxonomy)
    trend_rows = [(name, *trend(all_reg, fn, rng)) for name, fn in feats + gen]
    trend_adj = holm([r[2] for r in trend_rows])
    window = reg({2024, 2025})
    diff_rows = [(name, *diff_test(window, ccpc(), fn, rng)) for name, fn in feats]
    diff_adj = holm([r[3] for r in diff_rows])
    by_season = {name: [mean(counts(reg({s}), fn)) for s in (2022, 2023, 2024, 2025)]
                 for name, fn in feats + gen}
    per_regional = {name: mean(counts(all_reg, fn)) for name, fn in feats + gen}
    flat = [p for ps in all_reg.values() for p in ps]
    overlap = []
    for g, tags in (("graph", ["graphs", "trees", "shortest-paths", "flows", "matching",
                               "dfs-and-similar", "dsu"]),
                    ("dp", ["dynamic-programming"]), ("data-structures", ["data-structures"]),
                    ("math", ["math", "number-theory", "combinatorics", "probabilities"]),
                    ("string", ["strings", "hashing"]), ("geometry", ["geometry"])):
        tagged = [p for p in flat if set(p["general"]) & set(tags)]
        derived = [p for p in flat if g in p["cats"]]
        both = sum(g in p["cats"] for p in tagged)
        overlap.append((g, "/".join(tags), len(tagged), len(derived),
                        both / len(tagged), both / len(derived)))
    profile = {"ICPC regionals 2022-2025": position_profile(all_reg),
               "CCPC 2024-2025": position_profile(ccpc())}
    rows = forecast_rows(all_reg, taxonomy, alpha, decay)

    write_report({
        "alpha": alpha, "decay": decay, "grid": grid, "test_rows": test_rows, "added": added,
        "sites": sites, "trend_rows": trend_rows, "trend_adj": trend_adj, "diff_rows": diff_rows,
        "diff_adj": diff_adj, "by_season": by_season, "per_regional": per_regional,
        "overlap": overlap, "profile": profile, "rows": rows, "n_reg": len(all_reg),
        "n_reg_problems": len(flat), "n_window": len(window), "n_ccpc": len(ccpc()),
    })


def write_report(v):
    rows, test_rows, n_reg = v["rows"], v["test_rows"], v["n_reg"]
    L = []
    w = L.append
    w("# Techniques in ICPC Asia East regionals: 2022-2025 and a 2026 forecast\n")
    w(f"Generated by `scripts/technique_forecast.py`. Data: {n_reg} ICPC EC regionals "
      f"(2022-2025, {v['n_reg_problems']} problems) and {v['n_ccpc']} CCPC contests (2024-2025 "
      "sites and finals). Named techniques: Gemini extraction (`data/techniques_atlas.json`, "
      "128-id taxonomy; primary or secondary tag). General tags: DeepSeek `primary_tags` (ICPC "
      "only; the CCPC problems have none). Difficulty: calibrated CF-scale `difficulty_cf`; "
      "*position* = rank by difficulty inside the contest (1 = easiest).\n")

    w("**Key numbers**\n")
    per, none = v["n_reg_problems"] / n_reg, v["per_regional"]["(no named technique)"]
    first = v["profile"]["ICPC regionals 2022-2025"][0]
    w(f"- A regional has {per:.1f} problems; {none:.1f} ({none / per:.0%}) use no named technique. "
      f"Only {first['named_share']:.0%} of positions {first['positions']} need one.")
    for r in test_rows:
        g, lo, hi = r["gain_vs_uniform"]
        m, x = r["coverage"][20]
        w(f"- {r['test']}: log loss {r['logloss_model']:.4f} vs uniform {r['logloss_uniform']:.4f} "
          f"(gain {g:.4f}, 90% CI {lo:.4f} to {hi:.4f}); the top-20 list covers {m:.0%} of named "
          f"problems (random list {x:.0%}).")
    site_wins = sum(x < r["pooled"] for r in v["sites"] for k, x in r.items() if k.startswith("beta"))
    site_n = sum(k.startswith("beta") for r in v["sites"] for k in r)
    w(f"- No trend survives Holm (smallest Holm p {fmt_p(min(v['trend_adj']))}), nor any ICPC-vs-CCPC "
      f"difference ({fmt_p(min(v['diff_adj']))}). Site-specific forecasts beat the pooled one in "
      f"{site_wins} of {site_n} (season, beta) cases.")
    rec = {o[0]: o[4] for o in v["overlap"]}
    w(f"- Derived categories catch {rec['dp']:.0%} of DeepSeek's dp problems and {rec['math']:.0%} of "
      "its math problems, so general dp / greedy / math are not compared with CCPC.")
    w("- 2026, most likely per regional: " + ", ".join(f"{r['id']} {r['p']:.0%}" for r in rows[:5]) + ".\n")

    w("## 1. What a regional looks like (2022-2025)\n")
    w("Problems per regional with the tag. Derived categories come from named techniques; "
      "`general:` tags from DeepSeek. Trend = OLS slope per season with a permutation p "
      f"(Holm-adjusted over {len(v['trend_rows'])} tests).\n")
    w("| tag | 2022 | 2023 | 2024 | 2025 | all | slope/season | p | Holm p |")
    w("|---|---|---|---|---|---|---|---|---|")
    for (name, slope, p), adj in zip(v["trend_rows"], v["trend_adj"]):
        s = v["by_season"][name]
        w(f"| {name} | {s[0]:.2f} | {s[1]:.2f} | {s[2]:.2f} | {s[3]:.2f} | "
          f"{v['per_regional'][name]:.2f} | {slope:+.2f} | {fmt_p(p)} | {fmt_p(adj)} |")

    w("\n### Derived categories miss most dp and math problems\n")
    w("The named-technique tags carry no general tags (graph, dp, ...). Mapping each named "
      "technique to its taxonomy category recovers part of them. On ICPC regionals, against "
      "DeepSeek's general tags (recall = share of DeepSeek-tagged problems the derived category "
      "catches; precision = share of derived problems DeepSeek also tags):\n")
    w("| derived category | DeepSeek tags | DeepSeek problems | derived problems | recall | precision |")
    w("|---|---|---|---|---|---|")
    for g, tags, ng, nd, rec, prec in v["overlap"]:
        w(f"| {g} | {tags} | {ng} | {nd} | {rec:.2f} | {prec:.2f} |")
    w("\nCCPC is therefore compared with ICPC on named techniques and derived categories only, "
      "not on general dp / greedy / math / constructive.\n")

    w("### By position in the contest\n")
    for name, prof in v["profile"].items():
        w(f"**{name}**\n")
        w("| positions | per contest | median CF | needs a named technique | "
          "top general tags (problems per contest) | top named techniques (problems) |")
        w("|---|---|---|---|---|---|")
        for r in prof:
            gen = ", ".join(f"{t} {x:.2f}" for t, x in r["general"][:6]) or "n/a"
            tech = ", ".join(f"{k} {n}" for k, n in r["techniques"]) or "-"
            w(f"| {r['positions']} | {r['per_contest']:.1f} | {r['median_cf']:.0f} | "
              f"{r['named_share']:.0%} | {gen} | {tech} |")
        w("")

    w("## 2. Held-out tests\n")
    a, d, grid = v["alpha"], v["decay"], v["grid"]
    w(f"Model: recency-weighted presence rate per technique, shrunk toward its category's mean "
      f"rate. Tuned on 2022-2023 -> 2024: alpha = {a}, decay = {d} (log loss {grid[(a, d)]:.4f}; "
      f"over decay {DECAYS[0]}-{DECAYS[-1]} at this alpha it spans "
      f"{min(grid[(a, x)] for x in DECAYS):.4f}-{max(grid[(a, x)] for x in DECAYS):.4f}, so "
      "recency hardly matters). Then fitted on the 2022-2024 regionals and scored on every "
      "(contest, technique) cell of both test sets. Uniform = one rate for every technique; "
      "category-only = each technique gets its category's mean rate.\n")
    w("| test | contests | log loss model | category-only | uniform | gain vs uniform (90% CI) "
      "| Brier model / uniform | named problems whose techniques were unseen in training |")
    w("|---|---|---|---|---|---|---|---|")
    for r in test_rows:
        g, lo, hi = r["gain_vs_uniform"]
        w(f"| {r['test']} | {r['contests']} | {r['logloss_model']:.4f} | "
          f"{r['logloss_category_only']:.4f} | {r['logloss_uniform']:.4f} | "
          f"{g:.4f} ({lo:.4f} to {hi:.4f}) | {r['brier_model']:.4f} / {r['brier_uniform']:.4f} | "
          f"{r['novel_share']:.0%} of {r['named_problems']} |")
    w("\nCoverage: share of test problems with a named primary technique that is in the "
      "model's top-N list (a random top-N list in brackets).\n")
    w("| test | top 10 | top 20 | top 30 |")
    w("|---|---|---|---|")
    for r in test_rows:
        w(f"| {r['test']} | " + " | ".join(f"{m:.0%} ({x:.0%})" for m, x in r["coverage"].values()) + " |")
    w("\nCalibration (forecast bin: cells, mean forecast vs observed rate):\n")
    for r in test_rows:
        w(f"- {r['test']}: " + "; ".join(f"< {c:.2f}: {n} cells, {f:.3f} vs {y:.3f}"
                                         for c, n, f, y in r["calibration"]))
    ad = v["added"]
    w(f"\nAdding CCPC 2024 to the 2022-2024 training set changes the ICPC 2025 log loss "
      f"{ad['logloss_icpc_only']:.4f} -> {ad['logloss_icpc_plus_ccpc2024']:.4f}.\n")
    w("Site effect: log loss on test regionals whose site hosted before, pooled forecast vs "
      "one shrunk toward the site's own past regionals (beta = weight of the pooled forecast):\n")
    for r in v["sites"]:
        w(f"- {r['season']} ({', '.join(r['sites'])}): pooled {r['pooled']:.4f}; " +
          ", ".join(f"{k} {x:.4f}" for k, x in r.items() if k.startswith("beta")))

    w("\n## 3. ICPC vs CCPC (same seasons, 2024-2025)\n")
    w(f"Problems per contest, {v['n_window']} ICPC regionals vs {v['n_ccpc']} CCPC contests; "
      f"permutation p, Holm-adjusted over {len(v['diff_rows'])} tests.\n")
    w("| derived category | ICPC | CCPC | p | Holm p |")
    w("|---|---|---|---|---|")
    for (name, ma, mb, p), adj in zip(v["diff_rows"], v["diff_adj"]):
        w(f"| {name} | {ma:.2f} | {mb:.2f} | {fmt_p(p)} | {fmt_p(adj)} |")

    w("\n## 4. 2026 forecast (per regional, the same for every site)\n")
    w(f"Fitted on all {n_reg} regionals 2022-2025. P = chance that a given 2026 regional has "
      f"at least one problem using the technique. 8 sites: {', '.join(SITES_2026)}; "
      "\"any of 8\" assumes independent sites. Median position = where its problems sat in "
      "their contests (1 = easiest).\n")
    w("| # | technique | category | tier | P per regional | expected regionals of 8 | "
      "P in any of 8 | seen (regionals) | problems | median position |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows[:30], 1):
        w(f"| {i} | {r['id']} | {r['category']} | {r['tier']} | {r['p']:.0%} | "
          f"{r['expected_regionals_of_8']:.1f} | {r['p_any_of_8']:.0%} | "
          f"{r['seen_regionals']}/{r['of']} | {r['problems']} | {r['median_position'] or '-'} |")
    unseen = [r for r in rows if r["seen_regionals"] == 0]
    w(f"\n{len(unseen)} of {len(rows)} taxonomy techniques never appeared in a 2022-2025 regional; "
      f"their category priors give them {min(r['p'] for r in unseen):.1%}-"
      f"{max(r['p'] for r in unseen):.1%} each.\n")
    w("Expected problems per 2026 regional (the 2022-2025 mean):\n")
    w(", ".join(f"{n} {x:.1f}" for n, x in sorted(v["per_regional"].items(), key=lambda t: -t[1])) + "\n")

    with open(os.path.join(OUT, "technique_forecast.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    keep = {"alpha": a, "decay": d,
            "tuning_grid": [{"alpha": x, "decay": y, "logloss": z} for (x, y), z in grid.items()],
            "tests": test_rows, "ccpc_added_to_training": ad, "site_test": v["sites"],
            "trends": [{"tag": n, "slope": s, "p": p, "holm_p": h}
                       for (n, s, p), h in zip(v["trend_rows"], v["trend_adj"])],
            "icpc_vs_ccpc": [{"tag": n, "icpc": x, "ccpc": y, "p": p, "holm_p": h}
                             for (n, x, y, p), h in zip(v["diff_rows"], v["diff_adj"])],
            "derived_vs_general": [dict(zip(("category", "deepseek_tags", "deepseek_problems",
                                             "derived_problems", "recall", "precision"), o))
                                   for o in v["overlap"]],
            "per_regional_2026": v["per_regional"], "forecast_2026": rows, "positions": v["profile"]}
    with open(os.path.join(OUT, "technique_forecast.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=1)
    print("wrote output/technique_forecast.md and output/technique_forecast.json")


if __name__ == "__main__":
    main()
