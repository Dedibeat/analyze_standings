"""Build a self-contained HTML viewer of the estimated ratings.

    python -m arch_a.export_viewer

Runs Architecture A, then bundles per-contest problem difficulties and team
abilities (with human-readable names) into output/ratings_viewer.html. The data
is embedded directly in the page, so it opens from disk with no web server.
"""

import json
import os

import numpy as np

from .elo import LO, HI
from .fixedpoint import estimate
from .load import DATA_PATH, load, member_identity, team_key

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "viewer_template.html")


def build_data():
    with open(DATA_PATH) as f:
        raw = json.load(f)

    ds = load()
    uf = member_identity(raw)
    key_to_idx = {k: i for i, k in enumerate(ds.teams)}
    theta, b, _ = estimate(ds)

    # problem difficulties + actual solve count among ranked teams, per contest
    prob_by_contest = {}
    for p, (cid, label, pid, name) in enumerate(ds.problems):
        ci = ds.contest_of_problem[p]
        rows = np.where(ds.contest_of_row == ci)[0]
        solved = int(np.sum(ds.y[rows, p] & ds.solve_mask[rows, p]))
        prob_by_contest.setdefault(int(cid), []).append({
            "label": label,
            "name": name,
            "difficulty": round(float(b[p]), 0),
            "solved": solved,
        })

    contests = []
    for c in raw:
        cid = c["contest_id"]
        teams = []
        for s in c["standings"]:
            idx = key_to_idx[team_key(cid, s["team_id"], s.get("members"), uf)]
            teams.append({
                "rank": int(s["rank"]),
                "name": s.get("team_name") or "(unnamed)",
                "affiliation": s.get("affiliation") or "",
                "theta": round(float(theta[idx]), 0),
                "solved": int(s.get("total_solved") or 0),
                "contests": int(np.sum(ds.team_of_row == idx)),
            })
        problems = prob_by_contest.get(cid, [])
        contests.append({
            "contest_id": int(cid),
            "name": c.get("contest_name") or str(cid),
            "region": c.get("region") or "",
            "url": c.get("contest_url") or "",
            "n_teams": len(teams),
            "n_problems": len(problems),
            "mean_theta": round(float(np.mean([t["theta"] for t in teams])), 0) if teams else 0,
            "problems": problems,
            "teams": teams,
        })

    contests.sort(key=lambda c: c["name"])
    return {"scale": {"lo": LO, "hi": HI}, "contests": contests}


def main():
    data = build_data()
    with open(TEMPLATE) as f:
        template = f.read()
    html = template.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "ratings_viewer.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {os.path.normpath(out_path)}  "
          f"({len(data['contests'])} contests, {len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
