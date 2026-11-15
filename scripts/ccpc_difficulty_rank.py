#!/usr/bin/env python3
"""CCPC sets ranked by problem difficulty, and whether each is harder than an ICPC EC regional at
bronze, silver and gold.  Spoiler-free: the report holds ranks and verdicts only, no numbers.

Sets:

* ``SETS``: the CCPC contests with a full problem list in the fit (QOJ mirrors), rated by the
  shipped CF difficulties (``output/problem_ratings_calibrated.json``).
* ``ONSITE``: CCPC stations with an onsite XCPCIO board but no full problem list in the fit (the
  2022-2023 stations, 10th Chongqing, 11th Harbin).  Their onsite teams are linked to fitted teams by
  the fit's own identity rule (two shared members), and each problem gets a MAP difficulty with those
  abilities fixed (the fit's Rasch model and prior), mapped to CF.  A linear map fitted on the boards
  that have both puts it on the shipped scale.  The fit and the shipped ratings are not changed.

Rank: problems rated <= 2400 CF (fewer = harder); ties go to the set where a 2400-rated team expects
fewer solves (CF formula).

Two verdicts per medal tier, against the mainland ICPC regionals of 2023-2025:

* ``medal``: the CF performance of the last medallist of the tier.  ``SETS``: placed in the contest's
  QOJ board among the onsite rows (``contest_quality.performance``), against the 18 regionals placed
  the same way; the finals and the 2017 set have no onsite board.  ``ONSITE``: ranked among the
  board's linked onsite teams, against the regionals ranked the same way (17: Xi'an 2023 lists no
  members).
* ``problems``: the rating a team needs on this set to expect as many solves as on the median
  regional set, at the tier's median regional line, minus that line.  Problems only, no field.

"harder" / "easier" when the value is above / below the middle half of the regionals' own values,
otherwise "same".

    python3 scripts/ccpc_difficulty_rank.py      # writes output/ccpc_difficulty_rank.md

Needs numpy + pypinyin; the joint fit takes ~15 s.
"""
import collections
import json
import os
import sys
from itertools import combinations

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_a import elo  # noqa: E402
from arch_a.load import _norm_member, dedupe_contests  # noqa: E402
from arch_b import export_virtual_calc as ev  # noqa: E402
from arch_b.joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF  # noqa: E402
from arch_b.model import MU0, SIGMA_B  # noqa: E402
import contest_quality as cq  # noqa: E402

# QOJ id -> (label, XCPCIO link of the onsite board or None)
SETS = {
    1807: ("CCPC 2017 Qinhuangdao", None),
    1817: ("10th CCPC Harbin (2024)", "ccpc/10th/harbin"),
    1843: ("10th CCPC Jinan (2024)", "ccpc/10th/jinan"),
    1873: ("10th CCPC Zhengzhou (2024)", "ccpc/10th/zhengzhou"),
    2036: ("10th CCPC Final (May 2025)", None),
    2661: ("11th CCPC Zhengzhou (2025)", "ccpc/11th/zhengzhou"),
    2693: ("11th CCPC Jinan (2025)", "ccpc/11th/jinan"),
    3387: ("11th CCPC Chongqing (2025)", "ccpc/11th/chongqing"),
    3727: ("11th CCPC Final (Apr 2026)", None),
}
# XCPCIO link -> (label, QOJ id if confirmed): rated from the onsite board
ONSITE = {
    "ccpc/8th/guilin": ("8th CCPC Guilin (2022)", None),
    "ccpc/8th/weihai": ("8th CCPC Weihai (2022)", None),
    "ccpc/8th/guangzhou": ("8th CCPC Guangzhou (2022)", None),
    "ccpc/8th/mianyang": ("8th CCPC Mianyang (2022)", None),
    "ccpc/9th/qinhuangdao": ("9th CCPC Qinhuangdao (2023)", 1411),  # UCup S2 stage 9
    "ccpc/9th/guilin": ("9th CCPC Guilin (2023)", None),
    "ccpc/9th/harbin": ("9th CCPC Harbin (2023)", None),
    "ccpc/9th/shenzhen": ("9th CCPC Shenzhen (2023)", None),
    "ccpc/10th/chongqing": ("10th CCPC Chongqing (2024)", None),
    "ccpc/11th/harbin": ("11th CCPC Harbin (2025)", None),
}
EASY = 2400
TIERS = ("bronze", "silver", "gold")
MIN_LINKED = 30  # an onsite board needs this many linked teams
OUT = cq.OUT.parent / "ccpc_difficulty_rank.md"


def expected(b, r):
    """Expected solves of an r-rated team on problems rated b (CF formula)."""
    return float((1 / (1 + 10 ** ((np.asarray(b, float) - r) / 400))).sum())


def needed(b, solves):
    """The rating whose expected solves on b equal ``solves`` (bisection)."""
    lo, hi = -2000.0, 6000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if expected(b, mid) < solves else (lo, mid)
    return (lo + hi) / 2


def rank(diffs):
    """Set keys, hardest first."""
    return sorted(diffs, key=lambda c: (sum(d <= EASY for d in diffs[c]), expected(diffs[c], EASY)))


def verdict(value, reference):
    lo, hi = np.percentile(reference, [25, 75])
    return "harder" if value > hi else "easier" if value < lo else "same"


def problem_gaps(b, reference_sets, line):
    """Rating needed on b to match the median reference set's expected solves at ``line``, minus it."""
    target = float(np.median([expected(r, line) for r in reference_sets]))
    return needed(b, target) - line


def last_medallists(field, counts):
    """{tier: the last row of the tier}."""
    out = {}
    for tier, last in (("gold", counts[0]), ("silver", counts[0] + counts[1]), ("bronze", sum(counts))):
        out[tier] = max((r for r in field.values() if r["official_rank"] <= last), key=lambda r: r["official_rank"])
    return out


def medal_lines(c, perf):
    field, counts, *_ = cq.results(c)
    return {t: perf(cq.QOJ[c["link"]], r["solved"], r["penalty_minutes"])
            for t, r in last_medallists(field, counts).items()}


# ------------------------------------------------------------------ onsite boards

def _pairs(members):
    return combinations(sorted({_norm_member(m) for m in members} - {""}), 2)


def member_pairs(ds):
    """{member pair: fitted team index}, from every fitted row with >= 2 members.  The fit unions
    rosters sharing two members (``arch_a.load.member_identity``), so a pair names one team."""
    row_of = {p: r for r, p in enumerate(ds.participation_of_row)}
    raw = []
    for path in [TAGGED, OLDER_ICPC, PETROZ, WF] + UCUP:
        with open(path, encoding="utf-8") as f:
            raw += json.load(f)
    pairs = {}
    for c in dedupe_contests(raw):
        for i, s in enumerate(c["standings"]):
            r = row_of.get((c["contest_id"], i))
            if r is not None:
                for p in _pairs(s.get("members") or []):
                    pairs.setdefault(p, int(ds.team_of_row[r]))
    return pairs


def link(members, pairs):
    """The fitted team sharing the most member pairs with this roster; None if none or tied."""
    top = collections.Counter(pairs[p] for p in _pairs(members) if p in pairs).most_common(2)
    if not top or (len(top) == 2 and top[0][1] == top[1][1]):
        return None
    return top[0][0]


def fixed_difficulty(theta, y, mu=MU0, sd=SIGMA_B):
    """MAP difficulty of one problem from solves y with the abilities theta fixed: the log posterior's
    derivative falls in b, so its root is found by bisection on the fit's [LO, HI] range."""
    lo, hi = elo.LO, elo.HI
    for _ in range(60):
        b = (lo + hi) / 2
        lo, hi = (b, hi) if (elo.pi(theta, b) - y).sum() / elo.S - (b - mu) / sd ** 2 > 0 else (lo, b)
    return (lo + hi) / 2


def onsite(c, theta, pairs):
    """A board's field with the linked teams' abilities: field, counts, [(team id, ability)], solved
    problem ids per team, {problem id: label}."""
    field, counts, problems, solved, *_ = cq.results(c)
    linked = [(tid, link(r["members"].split("|"), pairs)) for tid, r in field.items() if r.get("members")]
    base = cq.bd.CACHE / "xcpcio" / (c["board"] if c["kind"] == "icpc" else c["link"]).replace("/", "_")
    labels = {str(p["id"]): p["label"] for p in json.loads((base / "config.json").read_text(encoding="utf-8"))["problems"]}
    return dict(field=field, counts=counts, linked=[(tid, float(theta[t])) for tid, t in linked if t is not None],
                solved=solved, labels={pid: labels[pid] for pid in problems})


def onsite_ratings(board, to_cf):
    """{label: (CF difficulty, solvers)} over the linked teams."""
    th = np.array([a for _, a in board["linked"]])
    out = {}
    for pid, label in board["labels"].items():
        y = np.array([pid in board["solved"][tid] for tid, _ in board["linked"]], float)
        out[label] = (to_cf(fixed_difficulty(th, y)), int(y.sum()))
    return out


def calibration(points):
    """(alpha, beta) with shipped rating ~ alpha + beta * onsite rating over (onsite, shipped) points."""
    x, y = np.array(points, float).T
    beta, alpha = np.polyfit(x, y, 1)
    return alpha, beta


def onsite_lines(board, to_cf):
    """{tier: CF performance of the last medallist, ranked among the linked teams}."""
    th = np.array([a for _, a in board["linked"]])
    res = np.array([(board["field"][tid]["solved"], board["field"][tid]["penalty_minutes"]) for tid, _ in board["linked"]])
    out = {}
    for tier, r in last_medallists(board["field"], board["counts"]).items():
        better = (res[:, 0] > r["solved"]) | ((res[:, 0] == r["solved"]) & (res[:, 1] < r["penalty_minutes"]))
        out[tier] = to_cf(elo.performance_rating(1 + int(better.sum()), th))
    return out


# ------------------------------------------------------------------ report

def shipped_ratings():
    """{QOJ id: {label: CF difficulty}}."""
    out = collections.defaultdict(dict)
    for p in json.loads((cq.cm.og.OUT / "problem_ratings_calibrated.json").read_text(encoding="utf-8")):
        out[p["contest_id"]][p["problem_label"]] = p["difficulty_cf"]
    return out


def main():
    shipped = shipped_ratings()
    by_link = {c["link"]: c for c in cq.contests()}
    regionals = [c for c in by_link.values() if c["kind"] == "icpc" and c["season"] in ("2023", "2024", "2025")
                 and c["site"] not in ("hongkong", "macau")]
    fit = ev.performance_fit()
    ds, theta, to_cf, _ = fit
    perf = cq.performance(set(cq.QOJ.values()), fit=fit)
    reg_lines = [medal_lines(c, perf) for c in regionals]
    reg_sets = [list(shipped[cq.QOJ[c["link"]]].values()) for c in regionals]
    line = {t: float(np.median([x[t] for x in reg_lines])) for t in TIERS}
    reg_gaps = {t: [problem_gaps(b, reg_sets, line[t]) for b in reg_sets] for t in TIERS}

    pairs = member_pairs(ds)
    links = [c["link"] for c in regionals] + [lk for _, lk in SETS.values() if lk] + list(ONSITE)
    boards = {lk: onsite(by_link[lk], theta, pairs) for lk in links}
    boards = {lk: b for lk, b in boards.items() if len(b["linked"]) >= MIN_LINKED}
    rated = {lk: onsite_ratings(b, to_cf) for lk, b in boards.items()}
    alpha, beta = calibration([(x, shipped[cq.QOJ[lk]][label]) for lk, r in rated.items() if lk not in ONSITE
                               for label, (x, n) in r.items() if 0 < n < len(boards[lk]["linked"])])
    reg_onsite = [onsite_lines(boards[c["link"]], to_cf) for c in regionals if c["link"] in boards]

    sets = {cid: list(shipped[cid].values()) for cid in SETS}
    sets |= {lk: [alpha + beta * x for x, _ in rated[lk].values()] for lk in ONSITE}
    rows = []
    for i, key in enumerate(rank(sets), 1):
        if key in SETS:
            (label, lk), qoj = SETS[key], key
            lines, ref = (medal_lines(by_link[lk], perf) if lk else None), reg_lines
        else:
            (label, qoj), lines, ref = ONSITE[key], onsite_lines(boards[key], to_cf), reg_onsite
            label += " *"
        medal = [verdict(lines[t], [x[t] for x in ref]) if lines else "n/a" for t in TIERS]
        probs = [verdict(problem_gaps(sets[key], reg_sets, line[t]), reg_gaps[t]) for t in TIERS]
        rows.append(f"| {i} | {label} | {qoj or '–'} | {' / '.join(medal)} | {' / '.join(probs)} |")
    md = ["# CCPC sets ranked by problem difficulty", "",
          "Generated by `scripts/ccpc_difficulty_rank.py`. Spoiler-free: ranks and verdicts only.", "",
          f"Rank 1 = hardest: fewest problems rated <= {EASY} CF; ties go to the set where a {EASY}-rated "
          "team expects fewer solves. Verdicts compare with the mainland ICPC EC regionals of 2023-2025: "
          "\"harder\" / \"easier\" = outside the middle half of those regionals, else \"same\".", "",
          "- **Medal harder?** The performance of the last bronze / silver / gold medallist (onsite field "
          "and problems together). n/a: no onsite board.",
          "- **Problems harder?** The rating needed to solve as many problems as on a typical regional set, "
          "for a team at that medal's typical regional line (problems only).",
          "- **\\*** Rated from the onsite XCPCIO board: the onsite teams' fitted abilities are held fixed and "
          "mapped onto the shipped scale; the medal line is ranked among the linked onsite teams and compared "
          "with the regionals ranked the same way. QOJ: CCPC category https://qoj.ac/category/205 (2023: "
          "https://qoj.ac/category/275).", "",
          "| rank | contest | QOJ | medal harder? bronze / silver / gold | problems harder? bronze / silver / gold |",
          "|---|---|---|---|---|", *rows, ""]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
