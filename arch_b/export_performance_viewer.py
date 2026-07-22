"""Build the post-virtual-contest performance calculator web page.

    python -m arch_b.export_performance_viewer

The web version of ``arch_b.performance``, generalized to **every** fitted
contest with standings (not only the 28 EA medal contests): pick a contest,
tick the problems you solved (optional ICPC penalty in minutes), and the page
computes — all client-side —

  * your rank / percentile among the contest's solving teams (full field),
    and, for EA medal contests, your official-field rank + medal;
  * your **performance rating** — the classic Elo rank-inversion
    (``elo.performance_rating``) of your inserted rank against the field's
    fitted abilities, the same number the medal analysis reports for every
    cutoff team — and, as the primary medal projection, that performance vs
    each EA medal contest's cutoff-team performances;
  * the performance bar (the 50% isotonic crossing of your solve indicator,
    the same crossing that defines the medal bars) in raw + CF points, with
    a secondary bar-based projection in the badge-ladder language;
  * the missed must-solve problems (badge gold+ or below, EA contests).

The two channels live on different scales and are never mixed: performance is
compared to cutoff *performances* (both Elo rank-inversions on the raw theta
scale), the bar to the medal *bars* (both difficulty crossings) — the
rank-inversion is measured as inflated against the difficulty scale
(details.md), so cross-channel comparison would be wrong by construction.

Build inputs: the UCup-anchored survival fit (run here once, to get the field
abilities that back the per-contest **rank -> performance curve** embedded in
the page), ``output/problem_ratings_calibrated.json`` (difficulties, all
contests), ``data/tagged.json`` (standings -> per-team [solved, penalty]
pairs of solving teams), ``output/medal_badges.json`` (badges + medal bars +
cutoff performances), and the XCPCIO official cache (official fields). Writes
``output/performance_calculator.html`` — self-contained, no server, nothing
model-side runs at view time.
"""

import json
import os

import numpy as np

from arch_a import elo
from arch_a.load import dedupe_contests
from . import survival
from .anchor import TAGGED, estimate_anchored
from .medals import _is_official, _load_xcpcio_cache, medal_contests
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "performance_viewer_template.html")
RATINGS = os.path.join(OUT_DIR, "problem_ratings_calibrated.json")
BADGES = os.path.join(OUT_DIR, "medal_badges.json")


def _pairs(rows):
    """[solved, penalty_seconds|null] per solving team, best first."""
    out = [[r["total_solved"],
            r["penalty_seconds"] if isinstance(r.get("penalty_seconds"), (int, float))
            else None]
           for r in rows if r["total_solved"] >= 1]
    return sorted(out, key=lambda p: (-p[0], p[1] if p[1] is not None else -1))


def _perf_curve(field_theta, n_ranks):
    """Rank -> Elo rank-inversion performance, for ranks 1..n_ranks."""
    return [round(float(elo.performance_rating(r, field_theta)))
            for r in range(1, n_ranks + 1)]


def main():
    with open(RATINGS) as f:
        ratings = json.load(f)
    with open(BADGES) as f:
        badges = json.load(f)
    with open(TAGGED) as f:
        raw = dedupe_contests(json.load(f))

    # the fit backs the rank -> performance curves (same fit medals.py uses)
    ds, theta, _b, _rho, _uf = estimate_anchored(fit_fn=survival.fit,
                                                 min_solve_hours=MIN_SOLVE_HOURS)
    contest_idx = {cid: ci for ci, cid in enumerate(ds.contests)}

    probs_by_cid = {}
    for r in ratings:
        probs_by_cid.setdefault(r["contest_id"], []).append(r)

    badge_by_key = {(p["contest_id"], p["problem_label"]): p["badge"]
                    for p in badges["problems"]}
    medal_info = {c["contest_id"]: c for c in badges["contests"]}
    xcpcio = _load_xcpcio_cache()
    ea_medal = medal_contests()

    contests = []
    for c in raw:
        cid = c["contest_id"]
        ps = probs_by_cid.get(cid)
        field = _pairs(c["standings"])
        if not ps or len(ps) < 2 or not field:
            continue
        entry = {
            "id": cid,
            "name": c["contest_name"].strip(),
            "year": c.get("year"),
            "region": c.get("region"),
            "problems": sorted(
                ({"l": p["problem_label"], "n": p["problem_name"],
                  "b": p["difficulty"], "cf": p["difficulty_cf"],
                  **({"badge": badge_by_key[(cid, p["problem_label"])]}
                     if (cid, p["problem_label"]) in badge_by_key else {})}
                 for p in ps), key=lambda p: p["b"]),
            "field": field,
        }
        ci = contest_idx.get(cid)
        if ci is not None:
            rows = np.flatnonzero(ds.contest_of_row == ci)
            if len(rows):
                field_theta = theta[ds.team_of_row[rows]]
                entry["perf"] = _perf_curve(field_theta, len(field) + 1)
        if cid in medal_info and cid in ea_medal:
            xc = xcpcio[cid]
            entry["official"] = _pairs(
                r for r in c["standings"] if _is_official(r, xc["official_set"]))
            m = medal_info[cid]
            entry["medal"] = {
                "cuts": m["cutoff_ranks_official"],
                "bars": m["medal_bar"],
                "bars_cf": m["medal_bar_cf"],
                "cut_solved": {t: m["cutoff_teams"][t]["solved"]
                               for t in ("gold", "silver", "bronze")},
                "cut_perf": {t: m["cutoff_teams"][t]["performance_elo"]
                             for t in ("gold", "silver", "bronze")},
            }
        contests.append(entry)

    contests.sort(key=lambda c: (-(c["year"] or 0), c["name"]))

    with open(TEMPLATE) as f:
        html = f.read()
    html = html.replace("/*__DATA__*/null",
                        json.dumps({"contests": contests}, ensure_ascii=False,
                                   separators=(",", ":")))
    out = os.path.join(OUT_DIR, "performance_calculator.html")
    with open(out, "w") as f:
        f.write(html)
    n_medal = sum(1 for c in contests if "medal" in c)
    n_perf = sum(1 for c in contests if "perf" in c)
    print(f"wrote {os.path.normpath(out)} ({len(contests)} contests, "
          f"{n_medal} with medal data, {n_perf} with perf curves, "
          f"{sum(len(c['problems']) for c in contests)} problems, "
          f"{sum(len(c['field']) for c in contests)} field rows)")


if __name__ == "__main__":
    main()
