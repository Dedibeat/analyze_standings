"""Build the interactive virtual-contest performance calculator.

    python -m arch_b.export_virtual_calc

For a team that solved a past contest "virtually" (outside the official
window), estimate the Codeforces-equivalent performance rating they would
have earned from a manually entered solved-count + penalty (standard ICPC
scoring, same as any real team's line in the standings). Method: standard
ICPC tie-break (most solved, then lowest penalty) inserts the virtual team
into the contest's real final standings to get a hypothetical rank, then the
classic Elo rank-inversion primitive (``arch_a.elo.performance_rating``,
already used for every real team's ``performance_elo`` in ``arch_b.medals``)
converts that rank + the real field's fitted abilities into a performance
rating. This reuses the same UCup-anchored survival fit and CF calibration as
``arch_b.export_viewer``, just bundled differently: real teams carry their
*internal* ability (not CF-mapped) plus their solved/penalty, so the
rank-insertion and Elo bisection can run against the same scale the fit was
made on, and a dense ``to_cf`` lookup table lets the browser map the
resulting rho to CF points itself (the shape+affine map from
``arch_b.calibrate`` cannot be re-fit client side, so it is sampled once here
instead of re-derived in JS). Every real team also carries its own calibrated
performance (from its actual rank, ``arch_a.fixedpoint._performance_ratings``)
so the standings table shows CF-equivalent performance for real and virtual
teams side by side.

Writes output/virtual_calc.html: self-contained, no server, one page per
contest picked from a dropdown (same grouping as ratings_viewer_b.html).
"""

import json
import os

import numpy as np

from arch_a import elo
from arch_a.fixedpoint import _performance_ratings
from arch_a.load import _max_solve_seconds, dedupe_contests, row_solved_any
from . import survival
from .joint import PETROZ, TAGGED, UCUP, estimate_joint
from .calibrate import _anchors, _gym_shape
from .run import MIN_SOLVE_HOURS

# Contest sources offered in the picker: the tagged.json regionals, the
# standings-only Petrozavodsk camp contests, and the Universal Cup seasons.
# All three are part of the single joint fit (arch_b.joint.estimate_joint's
# shipped inputs), so ds/theta/b cover every one of them on one scale -- only
# the raw standings need reloading here to build each contest's team list.
SOURCES = [TAGGED, PETROZ] + UCUP

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "virtual_calc_template.html")

LOOKUP_STEP = 5.0  # CF-point granularity of the embedded to_cf sample table


def _cf_map(records):
    """The composed internal-scale -> CF-points map from arch_b.calibrate."""
    shape = _gym_shape(records)
    if shape is None:
        shape = lambda t: np.asarray(t, float)  # noqa: E731
    our, cf, _ = _anchors(records)
    slope, intercept = np.polyfit(shape(our), cf, 1)
    return lambda t: float(np.clip(slope * shape(np.array([t]))[0] + intercept,
                                    elo.LO, elo.HI))


def _performance_lookup(ds, rho, to_cf):
    """Map each source participation to its own fitted performance."""
    return {
        participation: (int(ds.team_of_row[row]), round(to_cf(rho[row]), 0))
        for row, participation in enumerate(ds.participation_of_row)
    }


def _contests_from(ds, theta, b, to_cf, paths):
    """Build the picker's contest list for the fit (ds/theta/b) from its raw
    standings ``paths``. Contest ids repeated across ``paths`` (17 UCup rounds
    are also tagged.json entries) are deduplicated the same way the fit
    deduplicates them, so each contest is listed once."""
    prob_by_contest = {}
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        prob_by_contest.setdefault(int(cid), []).append({
            "label": label, "name": name,
            "difficulty_cf": round(to_cf(b[p]), 0),
        })

    # each real team's own calibrated performance in that contest, from its
    # actual rank (same eq. perf primitive as export_viewer.py / medals.py).
    # Keyed by the source participation rather than resolved team identity.
    # Identity is intentionally shared across contests (and can collide inside
    # one contest after roster unioning), while every standings row has its own
    # rank-derived performance.
    rows_by_contest = [np.where(ds.contest_of_row == ci)[0] for ci in range(len(ds.contests))]
    rho = _performance_ratings(theta, ds, rows_by_contest)
    row_lookup = _performance_lookup(ds, rho, to_cf)

    raw = []
    for path in paths:
        with open(path) as f:
            raw.extend(json.load(f))
    raw = dedupe_contests(raw)  # match load(): drop repeated contest entries
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]  # match load()
    contests = []
    for c in raw:
        cid = c["contest_id"]
        labels = {p["problem_label"] for p in c["problems"]}
        teams = []
        for source_row, s in enumerate(c["standings"]):
            if not row_solved_any(s, labels):
                continue
            hit = row_lookup.get((cid, source_row))
            assert hit is not None, f"missing participation {source_row} in contest {cid}"
            idx, perf = hit
            teams.append({
                "rank": int(s["rank"]),
                "name": s.get("team_name") or "(unnamed)",
                "affiliation": s.get("affiliation") or "",
                "solved": int(s.get("total_solved") or 0),
                "penalty": int(s.get("penalty_seconds") or 0),
                "theta": round(float(theta[idx]), 2),
                "performance": perf,
            })
        if not teams:
            continue
        teams.sort(key=lambda t: t["rank"])
        problems = prob_by_contest.get(cid, [])
        contests.append({
            "contest_id": int(cid),
            "name": c.get("contest_name") or str(cid),
            "year": c.get("year"),
            "region": c.get("region") or "",
            "url": c.get("contest_url") or "",
            "duration_minutes": round(_max_solve_seconds(c) / 60),
            "problems": problems,
            "teams": teams,
        })
    return contests


def build_data():
    ds, theta, b, _, _uf = estimate_joint(
        fit_fn=survival.fit, min_solve_hours=MIN_SOLVE_HOURS, verbose=False)

    records = [{"contest_id": int(cid), "problem_label": lab, "problem_name": name,
                "difficulty": float(b[p])}
               for p, (cid, lab, pid, name) in enumerate(ds.problems)]
    to_cf = _cf_map(records)

    # dense lookup table so the browser can map rho -> CF points without
    # re-deriving the shape+affine calibration itself
    xs = np.arange(elo.LO, elo.HI + LOOKUP_STEP, LOOKUP_STEP)
    ys = [round(to_cf(x), 1) for x in xs]

    contests = _contests_from(ds, theta, b, to_cf, SOURCES)

    contests.sort(key=lambda c: (-(c["year"] or 0), c["name"]))
    return {"scale": {"lo": elo.LO, "hi": elo.HI},
            "to_cf": {"lo": elo.LO, "step": LOOKUP_STEP, "ys": ys},
            "contests": contests}


def main():
    data = build_data()
    with open(TEMPLATE) as f:
        template = f.read()
    html = template.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "virtual_calc.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {os.path.normpath(out_path)}  "
          f"({len(data['contests'])} contests, {len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
