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
appear on neither judge. For each yardstick we join to our problems by normalized
title and report the per-region Spearman rank correlation with our difficulty.

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
OURS = os.path.join(OUT, "problem_ratings_survival.json")    # best CF agreement (details.md)
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


def main(refresh=False):
    contests = json.load(open(os.path.join(DATA, "tagged.json")))
    region_of = {c["contest_id"]: c["region"] for c in contests}
    ours = {(r["contest_id"], r["problem_label"]): r["difficulty"]
            for r in json.load(open(OURS))}
    # our problems indexed by (contest_id, norm_name) -> difficulty, plus name list per contest
    our_by_name = {}
    for c in contests:
        for p in c["problems"]:
            d = ours.get((c["contest_id"], p["problem_label"]))
            if d is not None:
                our_by_name[(c["contest_id"], _norm(p["problem_name"]))] = d

    # ---- Codeforces ----
    cf_ids = [int(m.group(1)) for line in open(CF_LIST)
              for m in [re.search(r"contest/(\d+)", line)] if m]
    rating = _cf_problemset(refresh)
    cf_names = defaultdict(list)
    for (cid, nm) in rating:
        cf_names[cid].append(nm)

    cf_pairs = defaultdict(list)   # region -> [(ours, cf)]
    print(f"{'CF':>5} {'qoj':>6} {'region':<18}{'n':>4}{'Spearman':>10}  mapping")
    for cid in cf_ids:
        names = cf_names.get(cid, [])
        if not names:
            print(f"{cid:>5} {'-':>6} {'(unrated/absent)':<18}")
            continue
        # vote: which of our contests do these CF problem names belong to?
        votes = Counter()
        for ocid in {oc for (oc, nm) in our_by_name if nm in names}:
            votes[ocid] = sum((ocid, nm) in our_by_name for nm in names)
        if not votes or votes.most_common(1)[0][1] < MIN_MATCH * len(names):
            print(f"{cid:>5} {'-':>6} {'(no qoj match)':<18}{len(names):>4}")
            continue
        qoj = votes.most_common(1)[0][0]
        reg = region_of[qoj]
        o, c = [], []
        for nm in names:
            if (qoj, nm) in our_by_name:
                o.append(our_by_name[(qoj, nm)]); c.append(rating[(cid, nm)])
        cf_pairs[reg].extend(zip(o, c))
        print(f"{cid:>5} {qoj:>6} {reg:<18}{len(o):>4}{_spearman(o, c):>10.3f}")

    # ---- Kattis ----
    kat = {_norm(v["name"]): v["difficulty"] for v in json.load(open(KATTIS)).values()}
    kat_pairs = defaultdict(list)
    for c in contests:
        for p in c["problems"]:
            d = ours.get((c["contest_id"], p["problem_label"]))
            k = kat.get(_norm(p["problem_name"]))
            if d is not None and k is not None:
                kat_pairs[c["region"]].append((d, k))

    # ---- per-region summary ----
    print(f"\n{'region':<20}{'CF n':>6}{'CF Spearman':>13}{'Kattis n':>10}{'Kattis Spearman':>17}")
    allcf, allkat = [], []
    for reg in sorted(set(cf_pairs) | set(kat_pairs)):
        cf, kt = cf_pairs.get(reg, []), kat_pairs.get(reg, [])
        allcf += cf; allkat += kt
        cf_s = f"{_spearman([a for a, _ in cf], [b for _, b in cf]):+.3f}" if len(cf) >= 4 else "-"
        kt_s = f"{_spearman([a for a, _ in kt], [b for _, b in kt]):+.3f}" if len(kt) >= 4 else "-"
        print(f"{reg:<20}{len(cf):>6}{cf_s:>13}{len(kt):>10}{kt_s:>17}")
    pcf = f"{_spearman([a for a, _ in allcf], [b for _, b in allcf]):+.3f}" if len(allcf) >= 4 else "-"
    pkt = f"{_spearman([a for a, _ in allkat], [b for _, b in allkat]):+.3f}" if len(allkat) >= 4 else "-"
    print(f"{'POOLED':<20}{len(allcf):>6}{pcf:>13}{len(allkat):>10}{pkt:>17}")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
