"""Build a self-contained HTML viewer of the estimated ratings.

    python -m arch_a.export_viewer           # full UCup-anchored tagged fit
    python -m arch_a.export_viewer --ucup    # the UCup-only anchor fit (s3 + s4)

Runs the UCup-anchored Architecture A fit over the full tagged.json, then bundles
per-contest problem difficulties and team abilities (with human-readable names)
into output/ratings_viewer.html. The data is embedded directly in the page, so it
opens from disk with no web server. With --ucup it instead shows the Phase-1
UCup-only fit (the anchor itself) and writes output/ratings_viewer_ucup.html.
"""

import json
import os
import sys

import numpy as np

from .elo import LO, HI
from .anchor import TAGGED, UCUP, estimate_anchored
from .fixedpoint import estimate
from .load import dedupe_contests, load, member_identity, row_solved_any, team_key

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "viewer_template.html")


def build_data(ucup_only=False):
    if ucup_only:
        raw = []
        for p in UCUP:
            with open(p) as f:
                raw.extend(json.load(f))
        raw = dedupe_contests(raw)
        uf = member_identity(raw)
        ds = load(UCUP, uf=uf)
        theta, b, rho, _ = estimate(ds)
    else:
        with open(TAGGED) as f:
            raw = json.load(f)
        raw = dedupe_contests(raw)
        ds, theta, b, rho, _, uf = estimate_anchored()
    key_to_idx = {k: i for i, k in enumerate(ds.teams)}

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

    # rho is per ds row, built in the same raw iteration order as load(); a
    # running counter therefore aligns each standing row with its performance.
    contests = []
    row = 0
    for c in raw:
        cid = c["contest_id"]
        teams = []
        for s in c["standings"]:
            if not row_solved_any(s):
                continue  # dropped from the fit; keep viewer aligned with rho
            idx = key_to_idx[team_key(cid, s["team_id"], s.get("members"), uf)]
            teams.append({
                "rank": int(s["rank"]),
                "name": s.get("team_name") or "(unnamed)",
                "affiliation": s.get("affiliation") or "",
                "theta": round(float(theta[idx]), 0),
                "performance": round(float(rho[row]), 0),
                "solved": int(s.get("total_solved") or 0),
                "contests": int(np.sum(ds.team_of_row == idx)),
            })
            row += 1
        if not teams:
            continue  # contest had no solvers at all; nothing to show
        problems = prob_by_contest.get(cid, [])
        contests.append({
            "contest_id": int(cid),
            "name": c.get("contest_name") or str(cid),
            "year": c.get("year"),
            "region": c.get("region") or "",
            "url": c.get("contest_url") or "",
            "n_teams": len(teams),
            "n_problems": len(problems),
            "mean_theta": round(float(np.mean([t["theta"] for t in teams])), 0) if teams else 0,
            "problems": problems,
            "teams": teams,
        })

    assert row == len(rho), "performance/row alignment mismatch"
    contests.sort(key=lambda c: (-(c["year"] or 0), c["name"]))
    return {"scale": {"lo": LO, "hi": HI}, "contests": contests}


def main():
    ucup_only = "--ucup" in sys.argv
    data = build_data(ucup_only=ucup_only)
    with open(TEMPLATE) as f:
        template = f.read()
    html = template.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    name = "ratings_viewer_ucup.html" if ucup_only else "ratings_viewer.html"
    out_path = os.path.join(OUT_DIR, name)
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {os.path.normpath(out_path)}  "
          f"({len(data['contests'])} contests, {len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
