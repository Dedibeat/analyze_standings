"""Build the Architecture B viewer: survival ratings on the Codeforces scale.

    python -m arch_b.export_viewer

Runs the UCup-anchored **survival** fit over the filtered tagged.json, maps every
difficulty and ability to Codeforces-equivalent points with the affine calibration
(``arch_b.calibrate``), and bundles per-contest problem difficulties (with their
Laplace standard errors) and team abilities/performances into
output/ratings_viewer_b.html. Self-contained -- opens from disk, no server.

Difficulty is CF-validated; team theta/performance share the same latent scale, so
the *same* affine map is applied to them (an extrapolation, not separately
validated -- the theta-vs-difficulty coin-flip relationship is preserved by it).
"""

import json
import os

import numpy as np

from arch_a.elo import HI, LO
from arch_a.fixedpoint import _performance_ratings
from arch_a.load import _max_solve_seconds, dedupe_contests, row_solved_any, team_key
from . import survival
from .anchor import TAGGED, estimate_anchored
from .calibrate import _anchors
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "viewer_template.html")


def build_data():
    ds, theta, b, _, uf = estimate_anchored(
        fit_fn=survival.fit, min_solve_hours=MIN_SOLVE_HOURS, verbose=False)
    se_theta, se_b = survival.laplace_se(ds, theta, b)

    rows_by_contest = [np.where(ds.contest_of_row == ci)[0] for ci in range(len(ds.contests))]
    rho = _performance_ratings(theta, ds, rows_by_contest)

    # affine map our-difficulty -> Codeforces points, fit on the CF-mirrored anchors
    recs = [{"contest_id": int(cid), "problem_label": lab, "problem_name": name,
             "difficulty": float(b[p])}
            for p, (cid, lab, pid, name) in enumerate(ds.problems)]
    our, cf, _ = _anchors(recs)
    slope, intercept = np.polyfit(our, cf, 1)
    to_cf = lambda x: float(np.clip(slope * x + intercept, LO, HI))  # noqa: E731

    # problem difficulties (CF points) + SE, per contest
    prob_by_contest = {}
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        ci = ds.contest_of_problem[p]
        rows = np.where(ds.contest_of_row == ci)[0]
        solved = int(np.sum(ds.y[rows, p] & ds.solve_mask[rows, p]))
        prob_by_contest.setdefault(int(cid), []).append({
            "label": label, "name": name,
            "difficulty": round(to_cf(b[p]), 0),
            "difficulty_se": round(slope * se_b[p], 0),
            "solved": solved,
        })

    with open(TAGGED) as f:
        raw = json.load(f)
    raw = dedupe_contests(raw)  # match load(): drop repeated contest entries
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]  # match load()
    key_to_idx = {k: i for i, k in enumerate(ds.teams)}

    contests = []
    row = 0  # running counter aligned with rho (same order as load built ds rows)
    for c in raw:
        cid = c["contest_id"]
        teams = []
        for s in c["standings"]:
            if not row_solved_any(s):
                continue
            idx = key_to_idx[team_key(cid, s["team_id"], s.get("members"), uf)]
            teams.append({
                "rank": int(s["rank"]),
                "name": s.get("team_name") or "(unnamed)",
                "affiliation": s.get("affiliation") or "",
                "theta": round(to_cf(theta[idx]), 0),
                "performance": round(to_cf(rho[row]), 0),
                "solved": int(s.get("total_solved") or 0),
                "contests": int(np.sum(ds.team_of_row == idx)),
            })
            row += 1
        if not teams:
            continue
        problems = prob_by_contest.get(cid, [])
        contests.append({
            "contest_id": int(cid),
            "name": c.get("contest_name") or str(cid),
            "year": c.get("year"),
            "region": c.get("region") or "",
            "url": c.get("contest_url") or "",
            "n_teams": len(teams),
            "n_problems": len(problems),
            "mean_theta": round(float(np.mean([t["theta"] for t in teams])), 0),
            "problems": problems,
            "teams": teams,
        })

    assert row == len(rho), "performance/row alignment mismatch"
    contests.sort(key=lambda c: (-(c["year"] or 0), c["name"]))
    return {"scale": {"lo": LO, "hi": HI}, "contests": contests}


def main():
    data = build_data()
    with open(TEMPLATE) as f:
        template = f.read()
    html = template.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "ratings_viewer_b.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {os.path.normpath(out_path)}  "
          f"({len(data['contests'])} contests, {len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
