# analyze_standings

Estimate ICPC-style **problem difficulties from contest standings** — there is no
native contestant rating to invert (unlike Codeforces), so the ability layer is
built from the standings themselves.

The method (`strat.tex`, long-form `strat_detailed.tex`): a problem's difficulty
is the skill level at which solving it is a coin flip. Abilities and difficulties
define each other, so they are solved by an alternating fixed point
(**Architecture A**), and teams recurring across contests link everything onto one
scale.

## Run

Requires Python 3 + numpy. A project venv is used:

```bash
python3 -m venv .venv
./.venv/bin/pip install numpy
./.venv/bin/python -m arch_a.run
```

This writes `output/problem_ratings.json` (one record per problem with its
estimated `difficulty` on a Codeforces-like [800, 4000] scale) and prints
verification stats.

`run` fits the full `data/tagged.json` **anchored to the Universal Cup scale**:
it first fits the UCup seasons (`ucup_s3` + `ucup_s4`) on their own, then uses
each UCup team's ability as that team's prior when fitting tagged, so the two
sit on one comparable scale (see `arch_a/anchor.py`). Without the anchor the
tagged fit floats ~440 pts above UCup for the 5.8k shared teams; anchoring cuts
that scale gap roughly in half. Tune the pull with `estimate_anchored(anchor_weight=…)`.

### Interactive viewer

```bash
./.venv/bin/python -m arch_a.export_viewer
```

Writes a self-contained `output/ratings_viewer.html` from the same UCup-anchored
fit as `run` (the full `tagged.json`, all 213 contests) — just open it in a
browser (no server needed). Pick a contest to see its problems ranked by difficulty and
its teams with both their overall ability `θ` and their **performance** in that
contest (the rating implied by their final rank, eq. perf) — the gap shows who
over- or under-performed. Click any column to sort, and filter teams by
name/member/affiliation.

To view just the UCup-only anchor fit (Phase 1: seasons s3 + s4, 76 contests)
instead of the full anchored tagged fit:

```bash
./.venv/bin/python -m arch_a.export_viewer --ucup
```

This writes a separate `output/ratings_viewer_ucup.html` (the main viewer is
left untouched).

### Contest-linking graph

```bash
./.venv/bin/python -m arch_a.export_graph
```

Writes a self-contained `output/contest_graph.html`: each node is a contest, an
edge joins contests that share team identities (the links that put every contest
on one scale). Toggle between the current roster/id keying and a year-appended
keying to see that adding the season to the team key fragments the single scale
into per-year islands. Runs on the 5-season `data/tagged.json`.

Module self-checks:

```bash
./.venv/bin/python -m arch_a.elo         # worked-example unit tests
./.venv/bin/python -m arch_a.load        # data summary
./.venv/bin/python -m arch_a.fixedpoint  # convergence trace
```

## Layout

- `data/tagged.json` — full input standings (146 contests); `data/ucup_s3.json`,
  `data/ucup_s4.json` — the Universal Cup seasons used to anchor the scale.
- `arch_a/` — Architecture A implementation (`load`, `elo`, `fixedpoint`,
  `anchor`, `run`), plus `export_viewer` + `viewer_template.html` for the viewer.
- `output/problem_ratings.json` — generated ratings.
- `output/ratings_viewer.html` — generated interactive viewer.
- `details.md` — design notes, key decisions, and follow-ups.

See `details.md` for the no-Codeforces-data anchoring choice, the `$DEFAULT`
team-id handling, and what's deliberately out of scope (Architecture B, the
solve-time survival model).
