# Details

## Goal

Rate ICPC-style problems by difficulty from contest standings alone (no native
contestant rating, unlike Codeforces/AtCoder). Strategy is described in
`strat.tex` (concise) and `strat_detailed.tex` (gentle long-form). This repo
implements both **Architecture A — the alternating fixed point** (strat.tex §3,
`arch_a/`) and **Architecture B — the joint item-response (Rasch) MAP model**
(strat.tex §4, `arch_b/`).

## Data

`data/tagged.json` — 146 contests, 99,754 standing rows, 1,668 problems (the full
mixed ICPC + Universal Cup set). `data/ucup_s3.json` and `data/ucup_s4.json` are
the two Universal Cup seasons (43 and 33 contests) used to anchor the scale.
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
  update (eq. update)} to a fixed point, then rate problems (eq. bp). The
  per-contest performance solve (`_bisect_contest`) shares the monotone term
  `G(b) = sum_j pi(theta_j, b)` across all teams in a contest: it is sampled on a
  grid once per contest (O(N·grid)) and read back by interpolation during the
  bisection, instead of rebuilding the dense N×N matrix `pi(theta_j, b_i)` on
  every bisection step. This cut a full `estimate()` from ~36 min to ~1 min
  (per-iteration `_performance_ratings` 93 s → ~2.8 s) with results unchanged
  (grid error ~1e-3 ELO, far below the `eps=0.5` convergence threshold).
- `anchor.py` — two-phase anchored fit: fit the Universal Cup seasons alone, then
  fit the full `tagged.json` with each UCup team's ability fed back as its prior
  (see the anchoring decision below). `estimate_anchored` returns the shared
  union-find alongside `(ds, theta, b, rho, history)` so callers can map raw
  standing rows back to `ds.teams`.
- `run.py` — wires it together (now the anchored fit), writes
  `output/problem_ratings.json`, runs the verification checks.
- `export_viewer.py` — builds `output/ratings_viewer.html` from the **same
  UCup-anchored `estimate_anchored()` fit** over the full `tagged.json` (213
  contests), so the viewer's `theta`/difficulties/performances match `run.py`.
  (Previously it ran a plain unanchored `estimate()` on `ucup_s4.json` alone.)
  `--ucup` instead builds the Phase-1 UCup-only fit (s3 + s4, 76 contests — the
  anchor itself) to `output/ratings_viewer_ucup.html`.

Run with the project venv:

    ./.venv/bin/python -m arch_a.run

### Key decisions

- **Scale anchor / no Codeforces data.** The strat's recommended anchor and
  bootstrap (eq. cfprior) use the Codeforces ratings of team members. **The data
  contains no CF ratings, and `members` are real names, not handles**, so CF
  anchoring is not available. Instead we anchor with a **constant neutral prior
  `MU0 = 2000`** (a mid Codeforces rating) for every team. This replaces the
  plan's original "center to mean 0", which is incompatible with the clamp below
  (centering would push half the teams under the floor mid-loop). Outputs are
  therefore a relative scale pinned near 2000, *not* certified CF-equivalent
  points.

- **Evidence-weighted prior (deviation from strat eq. update).** The strat blends
  `0.5*(rho + theta_prior)` per contest. With a *constant* MU0 that 0.5 weight
  never washes out — even a 40-contest team stays pinned halfway to MU0 — which
  flattens every contest's mean ability toward MU0 and defeats cross-contest
  normalization. We instead treat MU0 as a single pseudo-contest of strength
  `PRIOR_STRENGTH = 1.0`:
  `theta = (w_t*sum_c rho_c + PRIOR_STRENGTH*MU0) / (w_t*N_t + PRIOR_STRENGTH)`.
  A one-contest team leans on MU0 (cold start); a veteran is driven by its own
  performances (tourist: 2722 → 3634). Measured effect on normalization: with the
  old 0.5 blend, removing *all* cross-contest linking barely moved ratings
  (corr 0.99, mean shift 73 pts) — the prior did the anchoring. With the
  evidence-weighted prior, an unlinked contest collapses to exactly MU0
  (per-contest mean-theta std 3.7), and linking lifts small elite fields by
  300–480 pts (mean rating shift 267 pts): the **shared teams now drive
  normalization**, which is the whole point of the linking graph (§6).

- **Universal Cup anchor (`anchor.py`).** With only the constant MU0 prior, each
  dataset's scale floats on its own: a tagged-only fit sits ~440 pts above a
  UCup-only fit for the 5,835 teams they share (RMSE 519, corr 0.67 — the
  *ordering* agrees, the *scale* does not). The Universal Cup is a densely
  cross-linked league, so we treat its fit as the trusted scale. Two phases,
  under **one shared union-find** (a roster's `team_key` root depends on union
  order, so both datasets must resolve identity together):
  1. fit the UCup seasons (`ucup_s3 + ucup_s4`) alone → ability `theta_u` per team;
  2. fit `tagged.json` with each shared team's prior replaced by `theta_u`,
     folded with the standing MU0 pseudo-contest:
     `s_a = anchor_weight * w_u*N_u`,
     `mu = (PRIOR_STRENGTH*MU0 + s_a*theta_u)/(PRIOR_STRENGTH + s_a)`,
     `strength = PRIOR_STRENGTH + s_a`.
  Anchor strength is the team's *UCup evidence* `w_u*N_u`: many UCup rounds → pinned
  hard, a one-off → only nudged (still gets the MU0 cold start). The linking graph
  then carries the UCup scale to non-UCup teams. Measured at `anchor_weight=1.0`:
  shared-team RMSE vs UCup drops 519 → 301. Raising `anchor_weight` pins harder;
  this is the one knob. *Note:* both fits are still only MU0-anchored in absolute
  terms, so this buys **cross-fit consistency**, not certified CF-equivalent points.

- **Reliability weight from total contests (deviation from strat eq. weight).**
  The strat's experience weight `1 - 0.9^(n+1)` grows with accumulated history n.
  We use a single per-team weight from its *total* contest count,
  `w_t = 1 - 0.9^(N_t)` (one-off team → 0.1, veteran → ~1), applied in both the
  ability update and the difficulty estimate. Simpler, and needs no contest
  ordering (most `year` fields are null anyway).
  *Trade-off:* `N_t` is the team's total count over the whole dataset, so it is
  **non-causal/look-ahead** — a team's first appearance is weighted using
  contests that came later. That is fine for this one-shot batch rating but makes
  it unsuitable as-is for online/streaming use, and unlike the strat's
  chronological weight it does not discount a veteran's unsettled early-career
  results (all of a team's contests carry the same weight).

- **`theta` / `b` clamp `[800, 4000]`** (close to the Codeforces range). This is
  also the floor/ceiling the strat prescribes in §3.2: problems solved by all (and
  rank-1 teams) have no finite root and pin to the relevant bound; problems solved
  by none pin to 4000. (Difficulty and performance map to the bounds in opposite
  directions, since rank 1 is the *best* result.)

- **Boundary smoothing of difficulties (`SMOOTH`, `_rate_problems`).** Solved-by-all
  and solved-by-none problems otherwise collapse onto the bound (was 66 at 800, 98
  at 4000), discarding how strong the field was. We add two dummy teams of weight
  `SMOOTH=0.5` to every problem's pool: a strong (HI) phantom that *solved* it
  (target < total → all-solved root just above LO) and a weak (LO) phantom that
  *failed* (none-solved root just below HI). This is additive smoothing with two
  pseudo-observations at the extremes — gentle by construction (placing them at the
  bounds, not at a neutral 2000, barely moves the values; α washes out against a
  real field). Effect: 800-pins 66 → 0 (min now ~1028), 4000-pins 98 → 59 (the
  remainder are the 6 empty contests plus problems a *large strong* field still all
  failed, legitimately at-ceiling; the rest spread down to ~3229). Interior
  problems are essentially unchanged; `α` is the one knob.

- **Team identity = roster (member set), resolved by union-find.** Two id
  regimes exist: stable ids (`ucup-*`, a few bare ids) that denote one team
  across contests, and `$DEFAULT_DAT_PREFIX_*` ids from domjudge (the 35 official
  ICPC regional standings) that are **local to each contest** — of 475 recurring
  DEFAULT ids, 472 carry a different team name each time, so the same id is
  different teams. The roster is the reliable identity:

  - ~1,000 domjudge teams play 2+ regionals (up to 6); keying by member set links
    **2,716 appearances** that the DEFAULT ids leave as isolated islands.
  - team_name is *not* reliable — 33% of these teams vary their display name
    across regionals (punctuation, transliteration, renames), while the roster is
    constant (e.g. `0_GB_RAM` across 6 regionals; one Chinese team appears as
    `兄弟,我想拿牌` / `兄弟，我想拿牌` / `量大一队-…`).
  - 60–63 domjudge teams also recur in the Universal Cup, so roster-keying welds
    regional appearances onto rich UCup histories (e.g. *Rubikun*).

  `load.member_identity` builds a union-find over {stable id, roster token},
  unioning the two whenever they co-occur in a row. A row resolves to: its
  roster's component if it has **≥2 members** (the ≥2 guard avoids merging
  distinct teams on a single shared name — 72 one-member rows); else, for a
  domjudge id, an isolated per-contest key (1,476 no-member + 72 one-member rows
  that nothing identifies); else the stable id's component. This keeps a UCup
  team together even when its roster is missing from some rounds. Result: 7,902
  raw team keys collapse to **6,164 identities** (4,354 roster-identified, 1,598
  multi-contest; 1,548 domjudge-isolated). All 43 contests remain one connected
  component.

- **Granularity:** per resolved identity (roster where available, else stable id).
  True individual-level modelling (strat Remark on roster changes) is a follow-up.

- **Drop zero-solve standing rows (`load.row_solved_any`).** A standing row that
  solved no problem is removed before the fit (13.2% of tagged rows, 6.8%/4.7% of
  UCup s3/s4). Rationale: such rows are dominated by the MU0 prior — a one-off
  zero-solve team is pulled to ~1900 despite solving nothing — which inflates the
  apparent strength of the field. Consequences: a team's `N_t` (hence reliability
  weight) is now its count of contests *where it solved something*; the surviving
  population is stronger (mean theta 2018 → 2165) and absolute difficulties shift
  up (mean b 2462 → 2605) while the within-contest difficulty ordering is
  unchanged (Spearman still −0.993). The shared `uf` is still built over all rows,
  so identity links carried only by a zero-solve row survive. Contests left with
  no solvers at all (6 in tagged) drop out of the viewer; their problems were
  solved by nobody so they pin to 4000 (`_rate_problems` guards the empty pool).
  *Trade-off:* 73% of dropped rows are real teams' off-days, not non-participants,
  so this discards genuine low-end performances and is the reason difficulties
  drift up rather than down.

- **No year in the team key (decision on the multi-season `tagged.json`).**
  The larger `data/tagged.json` spans 5 seasons (2022–2026, 213 contests). We
  keep identity season-agnostic — appending the contest `year` to the key would
  **fragment the single scale into per-year islands**. Measured on the contest-
  linking graph (nodes = contests, edge = ≥1 shared identity): current keying
  leaves **6 components, the largest 206/213 contests** — essentially one scale;
  year-appended keying gives **11 components of sizes 54/52/51/45/…** — exactly
  the per-year contest counts, with only thin inter-year threads. Year-keying
  deletes precisely the cross-year bridges (1,405 rosters and 579 ucup ids that
  recur across seasons) that calibrate the years onto one comparable scale.
  Year turnover is already handled by the roster: of 11,697 distinct rosters only
  1,405 (12%) span >1 year — the other 88% already differ because members
  graduated, so they are already separate identities. The real residual cost is
  that a same-roster-multiple-seasons team gets a single ability blended across
  seasons; the principled fix is a **time-varying `theta_{team,year}`** with a
  smoothing prior (a model change, not a key change), recorded as a follow-up.
  `arch_a/export_graph.py` renders both keyings as an interactive graph
  (`output/contest_graph.html`).

### Results (current run)

- Converges in ~17 iterations, monotone decreasing `max|dtheta|` < 0.5.
- `theta` ≈ [1720, 3777], mean ~2165 (zero-solve rows dropped; see decision).
- `b` ≈ [1028, 4000], mean ~2613; boundary-smoothed (see decision), so
  solved-by-all problems clear the 800 floor and most solved-by-none spread below
  4000 (only at-ceiling and empty-contest problems remain pinned).
- Per-contest Spearman(difficulty, solve_count) median **−0.993** (harder
  problems were solved by fewer teams, as expected).
- Cross-contest normalization is now carried by the shared teams (see the
  evidence-weighted-prior decision): per-contest mean ability spreads to std≈110
  vs ≈3.7 with linking removed.

### Caveat introduced by the stronger normalization

Because an unlinked contest now collapses to MU0, a contest's absolute scale
depends entirely on its *linked* teams. Contests dominated by domjudge-isolated
teams (the large 500+-team Chinese regionals, where many rows have no usable
roster) are anchored by their minority of multi-contest teams, so their scale is
noisier than a UCup-heavy contest's. The graph is fully connected and every
contest has linked teams, so this is a quality gradient, not a break — but it is
the price of letting the shared teams, rather than the prior, set the scale.

## Architecture B (`arch_b/`)

Treat each solve as a Bernoulli response governed by the ability--difficulty gap:
`Pr(y_tp=1) = sigma((theta_t - b_p)/s) = pi(theta_t, b_p)` (the Rasch model, strat
§4 eq. rasch). The same `theta_t` appears in the likelihood of every contest team
`t` entered, so contests sharing a team are linked **automatically** — there is no
explicit ability-update step as in Architecture A; the coupling lives in the
shared parameter. The estimate is the maximum-a-posteriori point (eq. map) of the
log-likelihood (eq. loglik) plus Gaussian priors on `theta` and `b` (eq. priors).

- `model.py` — `fit(ds, prior_mu, sigma_theta, sigma_b, mu_b)`: the MAP fit.
  `_observations` flattens `solve_mask` into 1-D `(obs_team, obs_prob, obs_y)`
  arrays (one entry per observed competitor–problem cell, ~256k for tagged). The
  objective is strictly concave (concave log-likelihood + strictly concave
  Gaussian prior) so the MAP is unique; it is solved by **block-coordinate
  Newton** — one closed-form, vectorized Newton step over all `theta` (given `b`),
  then one over all `b` (given the new `theta`), each accumulated with `np.add.at`.
  Numpy only, **no learning rate** (scipy is not installed), and it echoes arch_a's
  alternating style. Converges in ~25 iters / ~5 s on the full tagged fit.
  `laplace_se(ds, theta, b)` returns per-parameter Laplace standard errors (see
  the uncertainty decision below).
- `validate.py` — external validation against the LLM `difficulty_estimate` in
  `tagged.json` (written by the sibling `llm-integration` tagger from the problem
  statement — independent of standings). Trusts only **editorial-backed** problems
  and reports per-bucket medians + Spearman for both architectures.
- `anchor.py` — `estimate_anchored(sigma_theta)`: the same two-phase UCup anchor as
  `arch_a.anchor`, under one shared union-find. Fit UCup (s3+s4) alone, then feed
  each UCup team's `theta_u` back as its Gaussian **prior mean** `mu_t` in the
  tagged fit (others keep `MU0`). The pull strength is the single global
  `sigma_theta`, not per-team UCup evidence (see decision below).
- `run.py` — wires it (the anchored fit), writes `output/problem_ratings_b.json`
  (a **distinct** file; arch_a's `problem_ratings.json` is untouched) with a
  `difficulty_se` per problem, runs the same Spearman / top-team verification as
  `arch_a.run`.

Run with the project venv:

    ./.venv/bin/python -m arch_b.run

### Key decisions (Architecture B)

- **Reuse, don't fork, the data layer.** `arch_b` imports `arch_a.load`
  (identity / union-find / zero-solve drop) and `arch_a.elo` (`pi`, scale `s`,
  the `[800, 4000]` clamp) unchanged — only the *estimator* differs between the
  two architectures, so all the team-identity and scale decisions above
  (roster keying, UCup anchor rationale, zero-solve drop, no-year-in-key) carry
  over verbatim.

- **Scope = Rasch (1-parameter), not 2PL.** strat §4 presents the per-problem
  discrimination `a_p` as "an extension," and the MAP objective (eq. map) is
  written purely in terms of `pi(theta, b)` — the Rasch model. The Rasch MAP is
  convex/uniquely solvable; adding `a_p` makes it non-convex (an `a_p·theta`
  interaction). We ship the convex Rasch fit and leave 2PL a follow-up.

- **The Gaussian prior replaces arch_a's boundary-smoothing hack.** A
  solved-by-nobody problem contributes only `sum_t log(1 - pi)`, which pushes
  `b_p` up but is held finite by the `N(mu_b, sigma_b^2)` prior (strat §4) — so the
  `b_p → +inf` of a bare likelihood never occurs and the two `SMOOTH` dummy teams
  arch_a needs are unnecessary here. Solved-by-all is symmetric.

- **`sigma_theta` / `sigma_b` are the regularization knobs; default 200.** The
  prior precision `1/sigma^2 ≈ 2.5e-5` is worth ~3 problem-observations, so it
  regularizes sparse teams/problems (cold start) while letting a well-observed
  team's own likelihood dominate. The knob only controls **scale spread**, not
  ordering: measured on the anchored tagged fit, per-contest Spearman is flat at
  −0.929 / −0.934 / −0.935 for `sigma_theta` = 120 / 200 / 400, while `theta`
  spreads from [1577, 2759] → [1295, 2860] → [1028, 3099]. Looser `sigma` → wider,
  more arch_a-like scale (and `b` starts hitting the 800 floor); tighter → more
  shrinkage toward `MU0`.

- **Anchor pull is the global `sigma_theta`, not per-team UCup evidence.** Unlike
  `arch_a.anchor` (which scales each team's prior *strength* by `w_u·N_u`), arch B
  uses one `sigma_theta` for every team and only sets the prior *mean* to `theta_u`.
  A well-observed UCup team is already pinned by its own likelihood terms, so the
  prior chiefly matters for sparse teams — making a per-team strength schedule
  redundant here. This keeps the Bayesian model to the single, principled
  regularization knob the strat prescribes.

- **Uncertainty = per-parameter Laplace SE (`laplace_se`).** The fit is a MAP
  *point* estimate; the strat frames the estimate as "the MAP point (or the full
  posterior, via MCMC / VI)". The cheapest posterior summary is the Laplace
  approximation — a Gaussian at the MAP with precision = the observed information
  (negative Hessian), which the Newton step **already computes**. So `SE(b_p) =
  1/sqrt(negH_b_p)` is free. It is the *conditional* SE (ignores the theta–b
  cross-curvature), hence approximate, but it captures the dominant effect: a
  much-solved problem is pinned tight (`b` SE down to ~9), while a solved-by-none/
  all problem has no data and its SE relaxes to the prior sd `sigma_b` (=200) —
  "we know only the prior." Reported in `output/problem_ratings_b.json` as
  `difficulty_se` (range ~[9, 200], median ~68). A calibrated joint interval
  (full-Hessian Laplace, or MCMC / VI) remains a follow-up.

### Results (Architecture B, current run)

- Converges in ~25 iterations / ~5 s (block-coordinate Newton), `max(|dtheta|,
  |db|)` monotone below 0.5.
- `theta` ≈ [1295, 2860], mean ~2007; `b` ≈ [893, 2725], mean ~1920. The scale is
  **more shrunk toward MU0 than arch_a** ([1720, 3777]) — the expected effect of
  the informative Gaussian prior (MAP shrinkage); it is a different (Bayesian)
  scale, not a defect.
- Per-contest Spearman(difficulty, solve_count) median **−0.934** over 134
  contests. Slightly looser than arch_a's −0.993 *by design*: arch_a difficulty is
  a near-monotone transform of the solve count given the field, whereas IRT
  difficulty also depends on **which** teams solved a problem (a problem cleared by
  weak teams rates easier than one cleared by equally many strong teams) — the
  deviation from pure solve-count ordering is exactly the extra signal IRT buys.

### External validation vs the LLM difficulty (`arch_b.validate`)

`tagged.json` carries an LLM `difficulty_estimate` (easy / medium / hard /
very_hard) per problem, written by the sibling `llm-integration` tagger from the
problem **statement** — independent of the standings both estimators use. We trust
it only on **editorial-backed** contests (128 of 213 contests, 1066 of the rated
problems): the LLM label is reliable enough to validate against only where an
editorial shipped. Both architectures' difficulty rises monotonically across every
bucket, and Architecture B agrees **more** with the independent ranking:

| LLM bucket | n   | arch A median | arch B median |
|------------|-----|---------------|---------------|
| easy       | 317 | 1889          | 1553          |
| medium     | 230 | 2467          | 1906          |
| hard       | 247 | 2917          | 2084          |
| very_hard  | 272 | 3506          | 2297          |
| **Spearman** |   | **+0.792**    | **+0.864**    |

So IRT's use of *which* teams solved each problem tracks the editorial-informed
opinion better than arch A's solve-count-driven estimate, despite arch B's more
compressed scale. (Restricting to editorial-backed problems *raised* arch B's
agreement from +0.825 on the full set to +0.864 — the no-editorial labels are
genuinely noisier.) Run: `./.venv/bin/python -m arch_b.validate`.

## Out of scope / follow-ups

- **2PL discrimination** `a_p` (strat §4) on top of the Rasch fit in `arch_b`,
  plus a calibrated joint posterior (full-Hessian Laplace / MCMC / VI) beyond the
  per-parameter Laplace SE already emitted as `difficulty_se`.
- **Solve-time survival likelihood** (strat §5) — uses `tau_tp` and contest
  length `T_c`; currently `tau` is loaded but unused.
- **Member-level identity** and entity resolution across sources (strat
  Remarks), to densify linking and handle roster changes.
- **Time-varying ability** `theta_{team,year}` with a season-to-season smoothing
  prior, so same-roster teams that recur across seasons can drift instead of
  collapsing to one blended ability — without losing the cross-year links that
  keep all seasons on one scale (see the no-year-in-key decision above).
- **External validation** — first pass done against the LLM `difficulty_estimate`
  on editorial-backed contests (`arch_b.validate`, see above); still open: a
  rated-judge mirror or numeric editorial difficulty for a calibrated point check.
- **CF anchoring** if member→handle→rating data becomes available, to turn the
  relative scale into true Codeforces-equivalent points.
