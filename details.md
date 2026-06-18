# Details

## Goal

Rate ICPC-style problems by difficulty from contest standings alone (no native
contestant rating, unlike Codeforces/AtCoder). Strategy is described in
`strat.tex` (concise) and `strat_detailed.tex` (gentle long-form). This repo
implements **Architecture A — the alternating fixed point** (strat.tex §3).

## Data

`data/standing_added.json` — 43 contests, 11,621 standing rows, 568 problems.
Per standing row: `rank`, `team_id`, `members`, `total_solved`, and per-problem
`{solved, score, time_seconds, wrong_attempts}`. This yields the model inputs
`y_tp` (solved), `tau_tp` (solve time), `r_{t,c}` (rank).

## Architecture A (`arch_a/`)

Abilities `theta_t` and difficulties `b_p` define each other, so they are solved
by alternation, then problems are rated with the converged abilities.

- `load.py` — parse JSON into flat numpy arrays + index maps.
- `elo.py` — the Elo-inversion primitive: logistic `pi(theta,b)` (s≈173.7) and
  `weighted_rating` (bisection, strat Def. 1). Also `performance_rating`.
- `fixedpoint.py` — Algorithm 1: loop {performance rating (eq. perf) → ability
  update (eq. update)} to a fixed point, then rate problems (eq. bp).
- `run.py` — wires it together, writes `output/problem_ratings.json`, runs the
  verification checks.

Run with the project venv:

    ./.venv/bin/python -m arch_a.run

### Key decisions

- **Scale anchor / no Codeforces data.** The strat's recommended anchor and
  bootstrap (eq. cfprior) use the Codeforces ratings of team members. **The data
  contains no CF ratings, and `members` are real names, not handles**, so CF
  anchoring is not available. Instead we anchor with a **constant neutral prior
  `MU0 = 2000`** (a mid Codeforces rating) used as `theta_prior` for every team.
  The blend toward `theta_prior` in eq. update fixes the global shift on the
  Codeforces scale. This replaces the plan's original "center to mean 0", which
  is incompatible with the clamp below (centering would push half the teams under
  the floor mid-loop). Outputs are therefore a relative scale pinned near 2000,
  *not* certified CF-equivalent points.

- **`theta` / `b` clamp `[800, 4000]`** (close to the Codeforces range). This is
  also the floor/ceiling the strat prescribes in §3.2: problems solved by all (and
  rank-1 teams) have no finite root and pin to the relevant bound; problems solved
  by none pin to 4000. (Difficulty and performance map to the bounds in opposite
  directions, since rank 1 is the *best* result.)

- **`$DEFAULT_DAT_PREFIX_*` team ids are per-contest, not stable identities.**
  These come from domjudge and are local to each contest: of 475 such ids that
  recur across contests, 472 carry a different team name each time, so the same id
  denotes different teams. We namespace them by contest id (`contest_id::team_id`)
  so each is a distinct, single-contest team. `ucup-*` ids are stable (581/586
  name-consistent) and carry the cross-contest linking signal. With DEFAULT ids
  excluded from linking, all 43 contests still form a single connected component
  (k=3 shared teams), so the whole dataset is on one comparable scale.

- **Granularity:** per `team_id` (after the namespacing above). Member-level
  modelling (strat Remark on roster changes) is a follow-up.

- **Experience weight** `w_{t,c} = 1 - 0.9^(n+1)` with `n` = prior appearances,
  ordering contests by `contest_id` (most `year` fields are null).

### Results (current run)

- Converges in ~9 iterations, monotone decreasing `max|dtheta|` < 0.5.
- `theta` ≈ [1500, 3000], mean ~1977 (anchored near MU0).
- `b` ≈ [1230, 4000]; 17 zero-solve problems pin to 4000.
- Per-contest Spearman(difficulty, solve_count) median **−0.995** (harder
  problems were solved by fewer teams, as expected).
- Most-recurring UCup teams land high (e.g. ucup-team1878 θ≈2721).

## Out of scope / follow-ups

- **Architecture B** — joint Rasch / 2PL item-response model (strat §4) with
  Gaussian priors and uncertainty (MAP / MCMC / VI).
- **Solve-time survival likelihood** (strat §5) — uses `tau_tp` and contest
  length `T_c`; currently `tau` is loaded but unused.
- **Member-level identity** and entity resolution across sources (strat
  Remarks), to densify linking and handle roster changes.
- **External validation** against problems with a known editorial difficulty or
  a rated-judge mirror.
- **CF anchoring** if member→handle→rating data becomes available, to turn the
  relative scale into true Codeforces-equivalent points.
