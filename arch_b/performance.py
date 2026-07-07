"""Post-virtual-contest performance calculator vs the EA official fields.

    python -m arch_b.performance <contest_id> --solved A,C,E [--penalty <minutes>]

After a virtual run of one of the EA medal contests (the 28 contests in
``output/medal_badges.json`` — run ``arch_b.medals`` first), pass the problems
you solved (and optionally your ICPC penalty in minutes) to get:

  * your rank / percentile / medal within that contest's official field —
    rank insertion by solved count, then penalty when given (without a
    penalty the rank is a best–worst range over the equal-solved block);
  * a badge scorecard: every problem with its badge and a solved marker,
    calling out missed problems at gold+ grade or below (the must-solve
    set for gold);
  * your **performance bar** — the difficulty at which your solve indicator
    crosses 50%, the same isotonic crossing that defines the medal bars,
    so it is directly comparable to them (raw + CF points);
  * a medal projection across all EA medal contests: your bar vs each
    contest's medal-cutoff bars (gold if it clears the gold+ edge, etc.).

Everything is read from ``output/medal_badges.json`` plus the raw standings
and the XCPCIO official-team cache — no model fit at runtime. The projection
carries the usual caveat: one contest gives ~13 binary observations, so the
bar is a coarse estimate; penalty/speed within an equal-solved block is only
used where you provide it.
"""

import argparse
import json
import math
import os

from arch_a import elo
from .medals import BADGE_ORDER, MEDAL_PCT, _cohort_bar, _is_official, \
    _load_xcpcio_cache, medal_contests

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
BADGES_JSON = os.path.join(OUT, "medal_badges.json")

# medal <- the hardest "+" edge the performance bar clears
MEDAL_EDGE = [("gold", "gold+"), ("silver", "silver+"), ("bronze", "bronze+")]


def _load_badges():
    with open(BADGES_JSON) as f:
        data = json.load(f)
    contests = {c["contest_id"]: c for c in data["contests"]}
    probs = {}
    for p in data["problems"]:
        probs.setdefault(p["contest_id"], []).append(p)
    for ps in probs.values():
        ps.sort(key=lambda p: p["difficulty"])
    return contests, probs


def _officials(raw_contest, xcpcio_set):
    """The contest's official solving teams, by rank (same rule as medals)."""
    return sorted((r for r in raw_contest["standings"]
                   if _is_official(r, xcpcio_set) and r["total_solved"] >= 1),
                  key=lambda r: r["rank"])


def _insert_rank(officials, solved, penalty_s):
    """Best and worst official rank for a (solved, penalty) result.

    Beats an official on more solves, or equal solves and strictly lower
    penalty; an official with an unknown penalty is assumed ahead. Without a
    penalty the result is the (best, worst) range over the equal-solved block.
    """
    ahead_more = sum(1 for r in officials if r["total_solved"] > solved)
    equal = [r for r in officials if r["total_solved"] == solved]
    if penalty_s is None:
        return ahead_more + 1, ahead_more + len(equal) + 1
    lost = sum(1 for r in equal
               if not isinstance(r.get("penalty_seconds"), (int, float))
               or r["penalty_seconds"] < penalty_s)
    return ahead_more + lost + 1, ahead_more + lost + 1


def _medal_at(rank, n):
    for tier, pct in MEDAL_PCT:
        if rank <= math.ceil(n * pct):
            return tier
    return None


def _global_cf_map(probs_by_cid):
    """Piecewise-linear raw-b -> CF map sampled at every badged problem."""
    pts = sorted((p["difficulty"], p["difficulty_cf"])
                 for ps in probs_by_cid.values() for p in ps)
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]

    def to_cf(b):
        if b <= xs[0]:
            return ys[0]
        if b >= xs[-1]:
            return ys[-1]
        for i in range(1, len(xs)):
            if b <= xs[i]:
                if xs[i] == xs[i - 1]:
                    return ys[i]
                t = (b - xs[i - 1]) / (xs[i] - xs[i - 1])
                return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return to_cf


def _user_bar(solved_labels, probs):
    """The 50% isotonic crossing of the user's own solve indicator."""
    row = {"problems": {lab: {"solved": 1} for lab in solved_labels}}
    return _cohort_bar([row], [p["difficulty"] for p in probs],
                       [p["problem_label"] for p in probs])


def _grade(bar, bars):
    """Hardest badge grade whose bar the performance bar clears."""
    g = None
    for tier in BADGE_ORDER[:-1]:
        if tier in bars and bar >= bars[tier]:
            g = tier
    return g


def main():
    ap = argparse.ArgumentParser(
        description="performance + medal estimate after a virtual EA contest")
    ap.add_argument("contest_id", type=int)
    ap.add_argument("--solved", default="",
                    help="comma-separated problem labels, e.g. A,C,E")
    ap.add_argument("--penalty", type=float, default=None,
                    help="ICPC penalty in minutes (optional)")
    args = ap.parse_args()

    contests, probs_by_cid = _load_badges()
    if args.contest_id not in contests:
        print(f"contest {args.contest_id} is not an EA medal contest; pick one of:")
        for cid, c in sorted(contests.items(), key=lambda kv: (kv[1]["year"], kv[0])):
            print(f"  {cid:>5}  {c['year']}  {c['contest_name']}")
        raise SystemExit(1)
    c = contests[args.contest_id]
    probs = probs_by_cid[args.contest_id]

    labels = {p["problem_label"] for p in probs}
    solved = [s.strip().upper() for s in args.solved.split(",") if s.strip()]
    unknown = [s for s in solved if s not in labels]
    if unknown:
        print(f"unknown problem label(s) {unknown}; contest {args.contest_id} has "
              f"{' '.join(sorted(labels))}")
        raise SystemExit(1)
    solved = set(solved)
    penalty_s = args.penalty * 60 if args.penalty is not None else None

    raw = medal_contests()[args.contest_id]
    xc = _load_xcpcio_cache()[args.contest_id]
    officials = _officials(raw, xc["official_set"])
    n = len(officials)

    print(f"=== {c['contest_name']} ({c['year']}) — virtual result: "
          f"{len(solved)} solved"
          + (f", penalty {args.penalty:.0f}m" if args.penalty is not None else "")
          + f" ===")

    # 1. placement in this contest's official field
    lo, hi = _insert_rank(officials, len(solved), penalty_s)
    cuts = c["cutoff_ranks_official"]
    if lo == hi:
        medal = _medal_at(lo, n)
        print(f"\nofficial-field rank {lo} of {n} "
              f"(top {lo/n:.0%}) -> medal: {medal or 'none'}")
    else:
        m_lo, m_hi = _medal_at(lo, n), _medal_at(hi, n)
        rng = m_lo if m_lo == m_hi else f"{m_hi or 'none'}–{m_lo or 'none'}"
        print(f"\nofficial-field rank {lo}–{hi} of {n} (top {lo/n:.0%}–{hi/n:.0%}, "
              f"no penalty given -> range over the {hi-lo}-team equal-solved "
              f"block) -> medal: {rng}")
    print(f"cutoff ranks G/S/B: {cuts['gold']} / {cuts['silver']} / {cuts['bronze']}; "
          f"cutoff teams solved "
          + " / ".join(f"{c['cutoff_teams'][t]['solved']}"
                       for t in ("gold", "silver", "bronze")))

    # 2. badge scorecard
    print("\nbadge scorecard (sorted by difficulty):")
    for p in probs:
        mark = "x" if p["problem_label"] in solved else "."
        print(f"  [{mark}] {p['problem_label']:>2} {p['badge']:<8} "
              f"{p['difficulty_cf']:>6.0f} CF  {p['problem_name']}")
    must = [p for p in probs
            if BADGE_ORDER.index(p["badge"]) <= BADGE_ORDER.index("gold+")
            and p["problem_label"] not in solved]
    if must:
        print("  missed must-solve problems for gold: "
              + ", ".join(f"{p['problem_label']} ({p['badge']})" for p in must))
    else:
        print("  swept every problem at gold+ grade or below.")

    # 3. the performance bar (same crossing as the medal bars)
    to_cf = _global_cf_map(probs_by_cid)
    bar = _user_bar(solved, probs)
    if bar >= elo.HI:
        print(f"\nperformance bar: pinned at the scale ceiling "
              f"(solved everything) — every projection below is gold")
    elif bar <= elo.LO:
        print(f"\nperformance bar: pinned at the scale floor — solve at least "
              f"the easiest problem to get a meaningful projection")
    else:
        print(f"\nperformance bar: {bar:.0f} raw / {to_cf(bar):.0f} CF "
              f"(your 50% solve-odds difficulty; the medal bars are the same "
              f"crossing for the cutoff cohorts)")

    # 4. projection across all EA medal contests
    print(f"\nmedal projection across the {len(contests)} EA medal contests "
          f"(your bar vs each contest's medal-cutoff bars, CF points):")
    print(f"  {'year':>4} {'contest':<32} {'bronze':>6} {'silver':>6} "
          f"{'gold':>6}  {'grade':<8} medal")
    tally = {}
    rows = sorted(contests.values(),
                  key=lambda k: -k["medal_bar_cf"]["gold+"])
    for k in rows:
        mb = k["medal_bar"]
        medal = next((m for m, edge in MEDAL_EDGE if bar >= mb[edge]), None)
        grade = _grade(bar, mb)
        tally[medal] = tally.get(medal, 0) + 1
        cf = k["medal_bar_cf"]
        mark = " *" if k["contest_id"] == args.contest_id else ""
        print(f"  {k['year']:>4} {k['contest_name'][:32]:<32} "
              f"{cf['bronze+']:>6.0f} {cf['silver+']:>6.0f} {cf['gold+']:>6.0f}  "
              f"{grade or 'below':<8} {medal or '—'}{mark}")
    total = len(rows)
    print("\nprojected medals: "
          + ", ".join(f"{m or 'none'} in {tally[m]}/{total}"
                      for m in ("gold", "silver", "bronze", None) if m in tally))
    print("(* = the contest you virtualed — its direct rank insertion above is "
          "authoritative; the bar projection quantizes on one contest's "
          "solve/miss pattern and ignores penalty)")


if __name__ == "__main__":
    main()
