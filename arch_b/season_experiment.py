"""Validate season-separated team identity + the short-contest filter.

Tries the data changes the user asked for and measures whether they help:

* ``season_key`` — separate a recurring roster's ability by ICPC season (the map:
  championships/World Finals belong to the previous season); stable ``ucup-*`` ids
  stay season-agnostic as the cross-season backbone.
* ``min_solve_hours`` — drop short-format contests (warm-ups, 3 h rounds).

For each config it runs the UCup-anchored **survival** fit and reports:

* connectivity of the team-sharing contest graph (the risk: keying by season must
  not fragment the single scale into per-season islands — the reason plain
  year-keying was rejected, see details.md);
* agreement with the held-out external opinions — Codeforces ratings (Spearman +
  leave-one-contest-out affine RMSE) and the LLM difficulty buckets.

    python -m arch_b.season_experiment
"""

import json
import os

import numpy as np

from arch_a.load import _UnionFind
from . import survival
from .anchor import estimate_anchored
from .calibrate import CF_REF, _anchors
from .validate import DATA, _llm_labels

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")


def _spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _components(ds):
    """Connected components of the graph: contests linked if they share a team."""
    uf = _UnionFind()
    contests_of_team = {}
    for ti, ci in zip(ds.team_of_row, ds.contest_of_row):
        contests_of_team.setdefault(ti, []).append(ci)
    for ci in range(len(ds.contests)):
        uf.find(ci)
    for cis in contests_of_team.values():
        for c in cis[1:]:
            uf.union(cis[0], c)
    roots = [uf.find(ci) for ci in range(len(ds.contests))]
    _, counts = np.unique(roots, return_counts=True)
    return len(counts), int(counts.max())


def _records(ds, b):
    return [{"contest_id": int(cid), "problem_label": lab, "problem_name": name,
             "difficulty": float(b[p])}
            for p, (cid, lab, pid, name) in enumerate(ds.problems)]


def _evaluate(label, season_key, min_solve_hours, llm):
    ds, theta, b, hist, _ = estimate_anchored(
        fit_fn=survival.fit, season_key=season_key,
        min_solve_hours=min_solve_hours, verbose=False)
    n_comp, biggest = _components(ds)
    recs = _records(ds, b)

    our, cf, grp = _anchors(recs)
    cf_sp = _spearman(our, cf)
    cv = []
    for g in np.unique(grp):
        tr, te = grp != g, grp == g
        s, i = np.polyfit(our[tr], cf[tr], 1)
        cv.append(s * our[te] + i - cf[te])
    cf_cv_rmse = np.sqrt(np.mean(np.concatenate(cv) ** 2))

    bmap = {(r["contest_id"], r["problem_name"]): r["difficulty"] for r in recs}
    lr, ld = [], []
    for (cid, name), lvl in llm.items():
        d = bmap.get((cid, name))
        if d is not None:
            lr.append(lvl); ld.append(d)
    llm_sp = _spearman(lr, ld)

    print(f"{label:22} teams={len(ds.teams):5} contests={len(ds.contests):3}  "
          f"graph: {n_comp} comp (biggest {biggest})  | "
          f"CF Spearman {cf_sp:+.3f} LOCO-RMSE {cf_cv_rmse:3.0f}  | LLM Spearman {llm_sp:+.3f}")


def main():
    tagged = json.load(open(DATA))
    llm = {}
    for c in tagged:  # editorial-backed LLM labels keyed by (contest_id, problem_name)
        ed = c.get("editorial")
        if not (ed and str(ed).strip()):
            continue
        for p in c["problems"]:
            de = p.get("difficulty_estimate")
            if de in ("very_easy", "easy", "medium", "hard", "very_hard"):
                lvl = ("very_easy", "easy", "medium", "hard", "very_hard").index(de)
                llm[(c["contest_id"], p["problem_name"])] = lvl

    print("survival fit, UCup-anchored:\n")
    _evaluate("baseline", False, None, llm)
    _evaluate("+5h filter", False, 3.5, llm)
    _evaluate("+season +5h filter", True, 3.5, llm)


if __name__ == "__main__":
    main()
