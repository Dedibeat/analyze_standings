"""How much of each contest's field is made of teams that played an EC regional.

Reference set: every roster in data/ec_online/regional_teams.csv (2022-2025 onsite
East Continent regionals).  A standing row is "matched" when two of its members sat
on the same reference team (the repo's own >=2-member identity rule), so a single
shared common name cannot match.  `pinyin` additionally lets Latin-spelled members
match the reference's Chinese names via pypinyin (surname-first or given-first).

An EC regional mirror is matched against the reference *without* its own
(season, site), otherwise it would trivially match itself.

Usage: python scripts/ec_overlap.py   ->  output/ec_overlap.csv, output/ec_overlap.md
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from itertools import combinations

from pypinyin import lazy_pinyin

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, ROOT)
from arch_a.load import _norm_member  # noqa: E402

DATA = os.path.join(ROOT, "data")
CJK = re.compile(r"[一-鿿]{2,4}")
LATIN = re.compile(r"[a-z]{4,}")
SITE_WORDS = [("hong kong", "hongkong"), ("macau", "macau"), ("hangzhou", "hangzhou"),
              ("hefei", "hefei"), ("jinan", "jinan"), ("nanjing", "nanjing"),
              ("shenyang", "shenyang"), ("xi'an", "xian"), ("chengdu", "chengdu"),
              ("kunming", "kunming"), ("metropolis", "shanghai"), ("wuhan", "wuhan"),
              ("shanghai", "shanghai")]
FILES = ["tagged.json", "ucup_s3.json", "ucup_s4.json", "petroz_2022_2026.json",
         "icpc_2020_2021.json"]


def site_of(contest):
    """(season, site) of an EC onsite regional mirror, else None."""
    name = contest["contest_name"].lower()
    if (contest["region"] != "Asia East Continent" or "online" in name
            or "ec-final" in name or "final contest" in name):
        return None
    for word, site in SITE_WORDS:
        if word in name:
            if site == "shanghai" and contest["year"] == 2023:
                return None  # QOJ 1522 mirrors the 2023 EC-Final, not a regional
            return (str(contest["year"]), site)
    return None


def kind_of(contest):
    name = contest["contest_name"].lower()
    if "online" in name:
        return "EC online"
    if (contest["contest_id"] in (1197, 1522, 1894, 3295) or "ec-final" in name
            or "final contest" in name):
        return "EC final"
    if site_of(contest):
        return "EC regional mirror"
    return contest["region"]


def pinyin_forms(name):
    """Latin spellings of a Chinese name: surname-first and given-first."""
    forms = {"".join(lazy_pinyin(name))}
    for k in {1, 2} if len(name) == 4 else {1}:
        forms.add("".join(lazy_pinyin(name[k:])) + "".join(lazy_pinyin(name[:k])))
    return forms


def load_reference():
    pairs = defaultdict(set)    # frozenset({pid, pid}) -> {(season, site)}
    persons = defaultdict(set)  # pid -> {(season, site)}
    latin = defaultdict(set)    # pinyin form -> {pid}
    with open(os.path.join(DATA, "ec_online", "regional_teams.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["season"], r["site"])
            pids = [_norm_member(m) for m in r["members"].split("|") if m.strip()]
            for p in pids:
                persons[p].add(key)
                if CJK.fullmatch(p):
                    for form in pinyin_forms(p):
                        latin[form].add(p)
            for a, b in combinations(sorted(set(pids)), 2):
                pairs[frozenset((a, b))].add(key)
    return pairs, persons, latin


def candidates(member, persons, latin, use_pinyin):
    """Reference person ids a standing member could be."""
    n = _norm_member(member)
    out = {n} if n in persons else set()
    if use_pinyin and LATIN.fullmatch(n):
        out |= latin.get(n, set())
    return out


def row_match(members, ref, loo, use_pinyin):
    pairs, persons, latin = ref
    cands = [candidates(m, persons, latin, use_pinyin) for m in members]
    any_member = any(any(persons[p] - {loo} for p in c) for c in cands)
    pair = False
    for i, j in combinations(range(len(cands)), 2):
        for a in cands[i]:
            for b in cands[j]:
                if a != b and pairs.get(frozenset((a, b)), set()) - {loo}:
                    pair = True
    return pair, any_member


def contests():
    seen = set()
    for fn in FILES:
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            for c in json.load(f):
                if c["contest_id"] in seen or not c["standings"]:
                    continue
                seen.add(c["contest_id"])
                yield c


def main():
    ref = load_reference()
    out = []
    for c in contests():
        loo = site_of(c)
        rows = c["standings"]
        withroster = [s for s in rows if len(s.get("members") or []) >= 2]
        stats = dict(exact=0, pinyin=0, anym=0)
        top = dict(n=0, hit=0)
        for s in sorted(withroster, key=lambda s: s["rank"]):
            ex, am = row_match(s["members"], ref, loo, False)
            py, _ = row_match(s["members"], ref, loo, True)
            stats["exact"] += ex
            stats["pinyin"] += py
            stats["anym"] += am
            if top["n"] < 50:
                top["n"] += 1
                top["hit"] += py
        n = len(withroster)
        out.append(dict(
            contest_id=c["contest_id"], year=c["year"], name=c["contest_name"],
            kind=kind_of(c), rows=len(rows), with_roster=n,
            roster_cov=round(100 * n / len(rows), 1),
            pair_exact=round(100 * stats["exact"] / n, 1) if n else None,
            pair_pinyin=round(100 * stats["pinyin"] / n, 1) if n else None,
            any_member=round(100 * stats["anym"] / n, 1) if n else None,
            top50_pinyin=round(100 * top["hit"] / top["n"], 1) if top["n"] else None))
    out.sort(key=lambda r: -(r["pair_pinyin"] or -1))
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    with open(os.path.join(ROOT, "output", "ec_overlap.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} contests -> output/ec_overlap.csv")
    return out


if __name__ == "__main__":
    main()
