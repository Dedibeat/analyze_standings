"""Build the ratings viewer with the released hierarchical binary-with-time fit.

    python -m arch_b.export_viewer

Problems, team abilities and rank-derived performances share the released CF map.
Writes the self-contained output/ratings_viewer_b.html.
"""

import json
import os

import numpy as np

from arch_a.elo import HI, LO
from arch_a.fixedpoint import _performance_ratings
from arch_a.load import _max_solve_seconds, dedupe_contests, row_solved_any, team_key
from .joint import TAGGED
from .calibrate import problem_cf
from .run import MIN_SOLVE_HOURS

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "viewer_template.html")


def build_data():
    from .shipped import shipped_fit, to_cf
    from .export_virtual_calc import _rank_official_within_event
    ds, theta, b, _, uf = shipped_fit()
    rows_by_contest = [np.where(ds.contest_of_row == ci)[0] for ci in range(len(ds.contests))]
    rho = _performance_ratings(theta, ds, rows_by_contest)
    rho = _rank_official_within_event(theta, ds, rows_by_contest, rho)

    # Problems and teams share the released hierarchical-with-time scale.
    cf_of = problem_cf(ds.problems)
    prob_by_contest = {}
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        solved = int(ds.solved_count[p])
        prob_by_contest.setdefault(int(cid), []).append({
            "label": label, "name": name,
            "difficulty": round(cf_of[(int(cid), label)], 0),
            "solved": solved,
        })

    with open(TAGGED) as f:
        raw = json.load(f)
    raw = dedupe_contests(raw)  # match load(): drop repeated contest entries
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]  # match load()
    key_to_idx = {k: i for i, k in enumerate(ds.teams)}

    contests = []
    # ``rho`` also contains the supplemental contests used by the fit.  The
    # viewer displays only tagged.json, which is the first source loaded and
    # therefore the prefix of the rho array.
    row = 0
    tagged_row_count = sum(
        1 for c in raw
        for s in c["standings"]
        if row_solved_any(s, {p["problem_label"] for p in c["problems"]})
    )
    for c in raw:
        cid = c["contest_id"]
        labels = {p["problem_label"] for p in c["problems"]}
        teams = []
        for s in c["standings"]:
            if not row_solved_any(s, labels):
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

    assert row == tagged_row_count, "tagged performance/row alignment mismatch"
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
