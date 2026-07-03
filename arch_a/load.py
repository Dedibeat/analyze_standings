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
import re
import unicodedata
from dataclasses import dataclass
from itertools import combinations

import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "ucup_s4.json")

# ICPC season vs calendar year: continental *Championships* and the World Finals
# are held the calendar year *after* the regional season they belong to (see the
# season map in details.md), so their season is ``year - 1``; everything else is
# its calendar year. Used only when ``season_key`` separates teams by season.
_CHAMPIONSHIP = re.compile(r"championship|world final", re.I)


def season_of(contest):
    """ICPC season of a contest: year-1 for championships/World Finals, else year."""
    y = contest.get("year")
    if y is None:
        return None
    return y - 1 if _CHAMPIONSHIP.search(contest.get("contest_name") or "") else y


def dedupe_contests(raw):
    """Drop duplicate contest entries sharing a ``contest_id``.

    ``tagged.json`` repeats some contests (up to 6x): the first entry carries the
    problem list, the rest are byte-identical standings with an empty ``problems``
    list. Replaying them would count every standing row multiple times (inflating
    the fit and each team's contest count), so we keep the first entry per
    ``contest_id`` (the one with the problems)."""
    seen = set()
    out = []
    for c in raw:
        cid = c["contest_id"]
        if cid in seen:
            continue
        seen.add(cid)
        out.append(c)
    return out


def _max_solve_seconds(contest):
    """Latest observed solve time in a contest (a proxy for its duration)."""
    m = 0
    for s in contest["standings"]:
        for p in (s.get("problems") or {}).values():
            if p.get("solved") and p.get("time_seconds"):
                m = max(m, p["time_seconds"])
    return m


def _norm_member(name):
    """Normalize a member name for identity matching: strip case, punctuation,
    whitespace and diacritics, which vary across a team's contest appearances
    (the same person is spelled differently by different registration systems)."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    return re.sub(r"[\s.\-_,']+", "", name.lower())


def _roster_token(members, season=None):
    """Identity token for a roster, or None if too small to trust (>=2 members).

    When ``season`` is given the token is season-scoped, so a roster that recurs in
    a later season resolves to a *separate* identity (time-varying ability).
    """
    if members and len(members) >= 2:
        tok = "mem:" + "|".join(sorted(_norm_member(m) for m in members))
        return f"{tok}|s{season}" if season is not None else tok
    return None


def row_solved_any(standing):
    """True if this standing row solved at least one problem (else it is dropped)."""
    return any(p.get("solved") for p in (standing.get("problems") or {}).values())


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


def _trusted_names(raw):
    """Normalized team names usable as identity for rows without a roster.

    A name is trusted only if it never appears twice within any single contest
    (a repeated name cannot distinguish the teams carrying it), recurs across
    >=2 contests (else it links nothing), and is >=5 chars normalized (very
    short names are too generic to trust).
    """
    per_contest = {}
    contests_of = {}
    for c in raw:
        cid = c["contest_id"]
        seen = per_contest.setdefault(cid, {})
        for s in c["standings"]:
            nm = _norm_member(s.get("team_name") or "")
            if len(nm) >= 5:
                seen[nm] = seen.get(nm, 0) + 1
                contests_of.setdefault(nm, set()).add(cid)
    dup = {nm for seen in per_contest.values() for nm, k in seen.items() if k > 1}
    return {nm for nm, cs in contests_of.items() if len(cs) >= 2 and nm not in dup}


def member_identity(raw, season_by_cid=None):
    """Build union-find resolver over stable ids and rosters (see module docstring).

    When ``season_by_cid`` (contest_id -> season) is given, roster tokens are
    season-scoped so a recurring roster splits per season; the stable ``ucup-*``/id
    keys are left season-agnostic on purpose, so they remain the cross-season
    backbone that keeps the whole scale connected.

    Rows with no usable roster and a per-contest domjudge id would be isolated
    islands; when such a row carries a *trusted* recurring team name
    (``_trusted_names``), its isolated ``dj:`` key is unioned to a ``tn:<name>``
    node so the name links its appearances across contests (like stable ids,
    names stay season-agnostic).
    """
    trusted = _trusted_names(raw)
    uf = _UnionFind()
    pair_root = {}  # (member-pair, season) -> first roster token carrying it
    for c in raw:
        season = None if season_by_cid is None else season_by_cid[c["contest_id"]]
        for s in c["standings"]:
            tid = s["team_id"]
            stable = None if tid.startswith("$DEFAULT") else "id:" + tid
            roster = _roster_token(s.get("members"), season)
            if stable is not None:
                uf.find(stable)
            if stable is None and roster is None:
                nm = _norm_member(s.get("team_name") or "")
                if nm in trusted:
                    uf.union(f"dj:{c['contest_id']}::{tid}", "tn:" + nm)
            if roster is not None:
                uf.find(roster)
                if stable is not None:
                    uf.union(stable, roster)
                # Rosters sharing >=2 members are the same team whose third
                # member was respelled or substituted: an exact-token identity
                # would split them (measured: ~3.7k such near-miss pairs).
                mem = sorted({_norm_member(m) for m in s["members"]})
                for pair in combinations(mem, 2):
                    key = (pair, season)
                    first = pair_root.setdefault(key, roster)
                    if first != roster:
                        uf.union(first, roster)
    return uf


def team_key(contest_id, team_id, members, uf, season=None):
    """Canonical team identity for a standing row, resolved through ``uf``."""
    roster = _roster_token(members, season)
    if roster is not None:
        return uf.find(roster)
    if team_id.startswith("$DEFAULT"):
        # per-contest key; resolves through uf so a trusted team name can link
        # it across contests (member_identity), else it stays isolated
        return uf.find(f"dj:{contest_id}::{team_id}")
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
    wrong: np.ndarray          # (n_rows, n_problems) wrong attempts; 0 where mask is False
    contest_of_problem: np.ndarray  # problem index -> contest index

    raw_solved_count: np.ndarray  # problem index -> problem_solved_in_contest (reported)


def load(path=DATA_PATH, uf=None, season_key=False, min_solve_hours=None):
    """Load one file (str path) or several (list of paths) into one Dataset.

    Pass a prebuilt ``uf`` to resolve team identity against a *shared* union-find
    so team keys are comparable across separate ``load`` calls (the anchor fit
    needs the UCup and tagged datasets to agree on who is who). When omitted, the
    union-find is built from this call's own rows.

    Standing rows that solved no problems are dropped (``row_solved_any``): they
    are excluded from the fit, so a team's contest count ``N_t`` is the number of
    contests where it actually solved something. ``uf`` is still built over *all*
    rows, so identity links carried only by a zero-solve row are preserved.

    ``season_key`` separates recurring rosters by ICPC season (``season_of``), so a
    roster gets a fresh ability each season; stable ids stay season-agnostic (the
    cross-season backbone). ``min_solve_hours`` drops short-format contests whose
    latest solve falls below that many hours (a duration proxy: no duration field
    exists). When a shared ``uf`` is passed it must already be built with the same
    ``season_key`` setting.
    """
    paths = [path] if isinstance(path, str) else list(path)
    raw = []
    for p in paths:
        with open(p) as f:
            raw.extend(json.load(f))
    raw = dedupe_contests(raw)

    if min_solve_hours is not None:
        raw = [c for c in raw if _max_solve_seconds(c) >= min_solve_hours * 3600]

    season_by_cid = {c["contest_id"]: season_of(c) for c in raw} if season_key else None
    if uf is None:
        uf = member_identity(raw, season_by_cid)

    def _key(cid, s):
        season = None if season_by_cid is None else season_by_cid[cid]
        return team_key(cid, s["team_id"], s.get("members"), uf, season)

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
            if not row_solved_any(s):
                continue  # zero-solve rows are dropped from the fit
            tk = _key(cid, s)
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
    y_rows, mask_rows, tau_rows, wrong_rows = [], [], [], []

    for c in raw:
        cid = c["contest_id"]
        ci = contest_index[cid]
        # which problem columns belong to this contest
        cols = {p["problem_label"]: problem_index[(ci, p["problem_label"])] for p in c["problems"]}
        for s in c["standings"]:
            if not row_solved_any(s):
                continue  # zero-solve rows are dropped from the fit
            assert s.get("rank") is not None, f"missing rank in contest {cid}"
            ti = team_index[_key(cid, s)]
            team_of_row.append(ti)
            contest_of_row.append(ci)
            rank_of_row.append(int(s["rank"]))

            y = np.zeros(n_problems, dtype=bool)
            mask = np.zeros(n_problems, dtype=bool)
            tau = np.full(n_problems, np.nan)
            wrong = np.zeros(n_problems, dtype=int)
            for label, pdata in (s.get("problems") or {}).items():
                col = cols.get(label)
                if col is None:
                    continue  # standings problem not in problem list; skip defensively
                mask[col] = True
                wrong[col] = int(pdata.get("wrong_attempts", 0))
                if pdata.get("solved"):
                    y[col] = True
                    t = pdata.get("time_seconds")
                    assert t is not None, f"solved cell without time in contest {cid}"
                    tau[col] = t
            y_rows.append(y)
            mask_rows.append(mask)
            tau_rows.append(tau)
            wrong_rows.append(wrong)

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
        wrong=np.array(wrong_rows, dtype=int),
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
