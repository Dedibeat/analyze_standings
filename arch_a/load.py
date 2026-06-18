"""Load standings JSON into flat arrays for the fixed-point estimator.

Team identity. Two id regimes appear in the data:

* Stable ids (``ucup-*`` and a few bare ids) denote the same team across
  contests -- the cross-contest linking signal.
* ``$DEFAULT_DAT_PREFIX_*`` ids come from domjudge (official ICPC regional
  standings) and are local to a single contest: the same id denotes different
  teams in different contests, so they cannot link on their own.

The roster (member set) is a far more reliable identity than either id: ~1000
domjudge teams play several regionals, and 63 of them also recur in the
Universal Cup, often under varying display names. We therefore resolve identity
by **union-find** over {stable id, member-set} (``member_identity``): every row
whose id and roster co-occur unions them, so member-keyed rows, id-keyed rows,
and domjudge regional rows of the same roster collapse into one team. This also
keeps a Universal Cup team together when its roster is missing from some rounds.

Resolution rule per row:

* roster of >=2 members present -> the roster's component (links everywhere);
* else domjudge id -> isolated per-contest key (nothing identifies it);
* else stable id -> the id's component.
"""

import json
import os
from dataclasses import dataclass

import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "ucup_s4.json")


def _roster_token(members):
    """Identity token for a roster, or None if too small to trust (>=2 members)."""
    if members and len(members) >= 2:
        return "mem:" + "|".join(sorted(members))
    return None


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def member_identity(raw):
    """Build union-find resolver over stable ids and rosters (see module docstring)."""
    uf = _UnionFind()
    for c in raw:
        for s in c["standings"]:
            tid = s["team_id"]
            stable = None if tid.startswith("$DEFAULT") else "id:" + tid
            roster = _roster_token(s.get("members"))
            if stable is not None:
                uf.find(stable)
            if roster is not None:
                uf.find(roster)
                if stable is not None:
                    uf.union(stable, roster)
    return uf


def team_key(contest_id, team_id, members, uf):
    """Canonical team identity for a standing row, resolved through ``uf``."""
    roster = _roster_token(members)
    if roster is not None:
        return uf.find(roster)
    if team_id.startswith("$DEFAULT"):
        return f"dj:{contest_id}::{team_id}"  # isolated: nothing identifies it
    return uf.find("id:" + team_id)


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

    raw_solved_count: np.ndarray  # problem index -> problem_solved_in_contest (reported)


def load(path=DATA_PATH, uf=None):
    """Load one file (str path) or several (list of paths) into one Dataset.

    Pass a prebuilt ``uf`` to resolve team identity against a *shared* union-find
    so team keys are comparable across separate ``load`` calls (the anchor fit
    needs the UCup and tagged datasets to agree on who is who). When omitted, the
    union-find is built from this call's own rows.
    """
    paths = [path] if isinstance(path, str) else list(path)
    raw = []
    for p in paths:
        with open(p) as f:
            raw.extend(json.load(f))

    if uf is None:
        uf = member_identity(raw)

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
            tk = team_key(cid, s["team_id"], s.get("members"), uf)
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
            ti = team_index[team_key(cid, s["team_id"], s.get("members"), uf)]
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
        raw_solved_count=np.array(
            [x if x is not None else -1 for x in raw_solved_count], dtype=int
        ),
    )


if __name__ == "__main__":
    import numpy as np

    ds = load()
    print(f"contests: {len(ds.contests)}")
    print(f"teams:    {len(ds.teams)}")
    print(f"problems: {len(ds.problems)}")
    print(f"rows:     {len(ds.team_of_row)}")

    counts = np.zeros(len(ds.teams), dtype=int)
    np.add.at(counts, ds.team_of_row, 1)
    roster = sum(1 for t in ds.teams if t.startswith("mem:"))
    isolated = sum(1 for t in ds.teams if t.startswith("dj:"))
    multi = int(np.sum(counts > 1))
    print(f"roster-identified teams: {roster}  (multi-contest: {multi})")
    print(f"domjudge isolated (no usable roster) teams: {isolated}")
