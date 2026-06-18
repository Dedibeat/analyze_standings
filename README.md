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

### Interactive viewer

```bash
./.venv/bin/python -m arch_a.export_viewer
```

Writes a self-contained `output/ratings_viewer.html` — just open it in a browser
(no server needed). Pick a contest to see its problems ranked by difficulty and
its teams with their estimated `θ`; click any column to sort, and filter teams by
name/member/affiliation.

Module self-checks:

```bash
./.venv/bin/python -m arch_a.elo         # worked-example unit tests
./.venv/bin/python -m arch_a.load        # data summary
./.venv/bin/python -m arch_a.fixedpoint  # convergence trace
```

## Layout

- `data/standing_added.json` — input standings (43 contests).
- `arch_a/` — Architecture A implementation (`load`, `elo`, `fixedpoint`, `run`),
  plus `export_viewer` + `viewer_template.html` for the HTML viewer.
- `output/problem_ratings.json` — generated ratings.
- `output/ratings_viewer.html` — generated interactive viewer.
- `details.md` — design notes, key decisions, and follow-ups.

See `details.md` for the no-Codeforces-data anchoring choice, the `$DEFAULT`
team-id handling, and what's deliberately out of scope (Architecture B, the
solve-time survival model).
