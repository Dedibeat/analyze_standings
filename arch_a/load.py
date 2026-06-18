"""Load standings JSON into flat arrays for the fixed-point estimator.

Team identity note: ``$DEFAULT_DAT_PREFIX_*`` ids come from domjudge and are
local to a single contest (the same id denotes different teams in different
contests). We namespace them by contest id so each is a distinct, single-contest
team. Stable ids (``ucup-*`` and bare ids) are kept as-is so a team recurring
across contests carries one identity -- the linking signal.
"""

import json
import os
from dataclasses import dataclass

import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "standing_added.json")


def team_key(contest_id, team_id):
    """Canonical team identity. Per-contest namespace for domjudge placeholders."""
    if team_id.startswith("$DEFAULT"):
        return f"{contest_id}::{team_id}"
    return team_id


@dataclass
class Dataset:
    teams: list                # team_key per team index
    contests: list             # contest_id per contest index
    problems: list             # (contest_id, problem_label, problem_id, name) per problem index

    team_of_row: np.ndarray    # row -> team index
    contest_of_row: np.ndarray # row -> contest index
    rank_of_row: np.ndarray    # row -> finishing rank (int)

    y: np.ndarray              # (n_rows, n_problems) bool solved, NaN-free; valid only where mask
    solve_mask: np.ndarray     # (n_rows, n_problems) bool: problem belongs to that row's contest
    tau: np.ndarray            # (n_rows, n_problems) solve time seconds; NaN where not solved
    contest_of_problem: np.ndarray  # problem index -> contest index

    contest_order: np.ndarray  # contest indices sorted by contest_id (for experience weights)
    raw_solved_count: np.ndarray  # problem index -> problem_solved_in_contest (reported)


def load(path=DATA_PATH):
    with open(path) as f:
        raw = json.load(f)

    team_index = {}
    contest_index = {}
    problems = []
    problem_index = {}  # (contest_idx, label) -> problem idx
    contest_of_problem = []
    raw_solved_count = []

    # First pass: register contests, problems, teams.
    for c in raw:
        cid = c["contest_id"]
        if cid not in contest_index:
            contest_index[cid] = len(contest_index)
        ci = contest_index[cid]
        for p in c["problems"]:
            key = (ci, p["problem_label"])
            if key not in problem_index:
                problem_index[key] = len(problems)
                problems.append((cid, p["problem_label"], p["problem_id"], p["problem_name"]))
                contest_of_problem.append(ci)
                raw_solved_count.append(p.get("problem_solved_in_contest"))
        for s in c["standings"]:
            tk = team_key(cid, s["team_id"])
            if tk not in team_index:
                team_index[tk] = len(team_index)

    contests = [None] * len(contest_index)
    for cid, ci in contest_index.items():
        contests[ci] = cid
    teams = [None] * len(team_index)
    for tk, ti in team_index.items():
        teams[ti] = tk

    n_problems = len(problems)

    team_of_row, contest_of_row, rank_of_row = [], [], []
    y_rows, mask_rows, tau_rows = [], [], []

    for c in raw:
        cid = c["contest_id"]
        ci = contest_index[cid]
        # which problem columns belong to this contest
        cols = {p["problem_label"]: problem_index[(ci, p["problem_label"])] for p in c["problems"]}
        for s in c["standings"]:
            assert s.get("rank") is not None, f"missing rank in contest {cid}"
            ti = team_index[team_key(cid, s["team_id"])]
            team_of_row.append(ti)
            contest_of_row.append(ci)
            rank_of_row.append(int(s["rank"]))

            y = np.zeros(n_problems, dtype=bool)
            mask = np.zeros(n_problems, dtype=bool)
            tau = np.full(n_problems, np.nan)
            for label, pdata in (s.get("problems") or {}).items():
                col = cols.get(label)
                if col is None:
                    continue  # standings problem not in problem list; skip defensively
                mask[col] = True
                if pdata.get("solved"):
                    y[col] = True
                    t = pdata.get("time_seconds")
                    assert t is not None, f"solved cell without time in contest {cid}"
                    tau[col] = t
            y_rows.append(y)
            mask_rows.append(mask)
            tau_rows.append(tau)

    contest_order = np.array(
        sorted(range(len(contests)), key=lambda ci: contests[ci]), dtype=int
    )

    return Dataset(
        teams=teams,
        contests=contests,
        problems=problems,
        team_of_row=np.array(team_of_row, dtype=int),
        contest_of_row=np.array(contest_of_row, dtype=int),
        rank_of_row=np.array(rank_of_row, dtype=int),
        y=np.array(y_rows),
        solve_mask=np.array(mask_rows),
        tau=np.array(tau_rows),
        contest_of_problem=np.array(contest_of_problem, dtype=int),
        contest_order=contest_order,
        raw_solved_count=np.array(
            [x if x is not None else -1 for x in raw_solved_count], dtype=int
        ),
    )


if __name__ == "__main__":
    ds = load()
    print(f"contests: {len(ds.contests)}")
    print(f"teams:    {len(ds.teams)}")
    print(f"problems: {len(ds.problems)}")
    print(f"rows:     {len(ds.team_of_row)}")
    namespaced = sum(1 for t in ds.teams if "::" in t and "$DEFAULT" in t)
    print(f"per-contest namespaced (domjudge) teams: {namespaced}")
