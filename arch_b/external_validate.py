"""Per-region external validation against two independent numeric yardsticks.

The LLM difficulty (arch_b.validate) is a single, statement-based opinion that can
itself be regionally biased. To tell a real per-region model bias from LLM noise we
need *numeric* opinions that are independent of our standings AND of each other:

  * Codeforces problemset ratings, for the ICPC contests mirrored on CF. The mirror
    contest ids are listed in ``data/cf_team_contests.txt``; ratings come from the
    public ``problemset.problems`` API (no login needed -- the cookie some notes
    mention is unnecessary). Covers Asia Pacific / Northern Eurasia / Europe.
  * Kattis difficulty (1.0-9.x, Elo-style, from open.kattis's practice population),
    scraped once into ``data/kattis_difficulty.json``. Covers North America (~88%)
    and Europe (~53%) -- precisely the regions CF does not mirror.

Together they reach every region except Asia East / West Continent, whose problems
appear on neither judge. We join each yardstick to our problems by normalized title
and report the per-region Spearman rank correlation for **all three trained models**
(arch A, arch B binary, arch B survival), plus the LLM-bucket Spearman, side by side.

CF contests are auto-mapped to our qoj contests by problem-name vote, so an
unmappable mirror (e.g. a Russian regional we don't carry) or an *unrated* mirror
(0 CF ratings, e.g. SWERC 2021-22) simply drops out. The title join can mis-match a
generic name; the aggregate Spearman is robust to a few, but a per-problem
calibration would want a contest-scoped join.

    python -m arch_b.external_validate            # uses cached CF ratings if present
    python -m arch_b.external_validate --refresh  # refetch the CF problemset
"""

import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
CF_LIST = os.path.join(DATA, "cf_team_contests.txt")
CF_CACHE = os.path.join(DATA, "cf_problemset.json")          # gitignored under data/
KATTIS = os.path.join(DATA, "kattis_difficulty.json")
MODELS = [("arch A", "problem_ratings.json"),
          ("arch B bin", "problem_ratings_b.json"),
          ("arch B surv", "problem_ratings_survival.json")]
BUCK = {"easy": 0, "medium": 1, "hard": 2, "very_hard": 3}   # LLM difficulty buckets
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MIN_MATCH = 0.6   # a CF contest maps to our contest only if >=60% of its names match


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])


def _cf_problemset(refresh=False):
    """All rated CF problems as {(contestId, norm_name): rating}; cached locally."""
    if refresh or not os.path.exists(CF_CACHE):
        req = urllib.request.Request("https://codeforces.com/api/problemset.problems",
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        assert data["status"] == "OK", data.get("comment")
        json.dump(data["result"]["problems"], open(CF_CACHE, "w"))
    probs = json.load(open(CF_CACHE))
    rating = {}
    for p in probs:
        if "rating" in p:
            rating[(p["contestId"], _norm(p["name"]))] = p["rating"]
    return rating


def _cf_mapping(contests, region_of, rating):
    """Map each listed CF mirror to a qoj contest by problem-name vote.

    Returns [(cf_id, qoj, region, matched_norm_names)]. Unrated mirrors (no CF
    ratings) and unmappable ones (<MIN_MATCH names found in any qoj contest) are
    skipped; both are printed for transparency. Independent of model output.
    """
    qoj_names = defaultdict(set)
    for c in contests:
        for p in c["problems"]:
            qoj_names[c["contest_id"]].add(_norm(p["problem_name"]))
    cf_ids = [int(m.group(1)) for line in open(CF_LIST)
              for m in [re.search(r"contest/(\d+)", line)] if m]
    cf_names = defaultdict(list)
    for (cid, nm) in rating:
        cf_names[cid].append(nm)

    print(f"{'CF':>5} {'qoj':>6} {'region':<18}{'n':>4}  mapping")
    mapping = []
    for cid in cf_ids:
        names = cf_names.get(cid, [])
        if not names:
            print(f"{cid:>5} {'-':>6} {'(unrated/absent)':<18}")
            continue
        votes = Counter({oc: sum(nm in qoj_names[oc] for nm in names)
                         for oc in qoj_names})
        qoj, hits = votes.most_common(1)[0]
        if hits < MIN_MATCH * len(names):
            print(f"{cid:>5} {'-':>6} {'(no qoj match)':<18}{len(names):>4}")
            continue
        matched = [nm for nm in names if nm in qoj_names[qoj]]
        mapping.append((cid, qoj, region_of[qoj], matched))
        print(f"{cid:>5} {qoj:>6} {region_of[qoj]:<18}{len(matched):>4}")
    return mapping


def _pairs(model_diff, contests, mapping, rating, kat):
    """For one model output, build (region -> [(ours, yardstick)]) for CF and Kattis."""
    by_name = {}   # (qoj, norm_name) -> our difficulty
    for c in contests:
        for p in c["problems"]:
            d = model_diff.get((c["contest_id"], p["problem_label"]))
            if d is not None:
                by_name[(c["contest_id"], _norm(p["problem_name"]))] = d
    cf, ka = defaultdict(list), defaultdict(list)
    for cid, qoj, reg, matched in mapping:
        for nm in matched:
            if (qoj, nm) in by_name:
                cf[reg].append((by_name[(qoj, nm)], rating[(cid, nm)]))
    for c in contests:
        for p in c["problems"]:
            d = model_diff.get((c["contest_id"], p["problem_label"]))
            k = kat.get(_norm(p["problem_name"]))
            if d is not None and k is not None:
                ka[c["region"]].append((d, k))
    return cf, ka


def _s(pairs):
    """Spearman over a pair list, or None if too few."""
    if len(pairs) < 4:
        return None
    return _spearman([a for a, _ in pairs], [b for _, b in pairs])


def main(refresh=False):
    contests = json.load(open(os.path.join(DATA, "tagged.json")))
    region_of = {c["contest_id"]: c["region"] for c in contests}
    rating = _cf_problemset(refresh)
    kat = {_norm(v["name"]): v["difficulty"] for v in json.load(open(KATTIS)).values()}
    mapping = _cf_mapping(contests, region_of, rating)

    # LLM buckets (editorial-backed problems) keyed (contest_id, label)
    llm = {(c["contest_id"], p["problem_label"]): BUCK[p["difficulty_estimate"]]
           for c in contests if c.get("editorial_url") for p in c["problems"]
           if p.get("difficulty_estimate") in BUCK}

    def f(v):
        return f"{v:+.3f}" if v is not None else "   -  "

    print(f"\n{'model':<13}| {'CF pld':>7} {'AsiaPac':>8} {'N.Eur':>7} {'Europe':>7} | "
          f"{'Kat pld':>8} {'N.Am':>7} {'Europe':>7} | {'LLM':>7}")
    print("-" * 86)
    for name, fname in MODELS:
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            continue
        md = {(r["contest_id"], r["problem_label"]): r["difficulty"]
              for r in json.load(open(path))}
        cf, ka = _pairs(md, contests, mapping, rating, kat)
        cf_all = [x for v in cf.values() for x in v]
        ka_pld = ka["North America"] + ka["Europe"]
        llm_pairs = [(d, llm[k]) for k, d in md.items() if k in llm]
        print(f"{name:<13}| {f(_s(cf_all)):>7} {f(_s(cf['Asia Pacific'])):>8} "
              f"{f(_s(cf['Northern Eurasia'])):>7} {f(_s(cf['Europe'])):>7} | "
              f"{f(_s(ka_pld)):>8} {f(_s(ka['North America'])):>7} "
              f"{f(_s(ka['Europe'])):>7} | {f(_s(llm_pairs)):>7}")
    print(f"\nn: CF pooled={len(cf_all)}, Kattis pooled={len(ka_pld)}, "
          f"LLM={len(llm_pairs)} (editorial-backed)")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
