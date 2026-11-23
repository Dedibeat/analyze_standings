# Architecture B (`arch_b/`)

Treat each solve as a Bernoulli response governed by the ability--difficulty gap:
`Pr(y_tp=1) = sigma((theta_t - b_p)/s) = pi(theta_t, b_p)` (the Rasch model, strat
§4 eq. rasch). The same `theta_t` appears in the likelihood of every contest team
`t` entered, so contests sharing a team are linked **automatically** — there is no
explicit ability-update step as in Architecture A; the coupling lives in the
shared parameter. The estimate is the maximum-a-posteriori point (eq. map) of the
log-likelihood (eq. loglik) plus Gaussian priors on `theta` and `b` (eq. priors).

- `model.py` — `fit(ds, prior_mu, sigma_theta, sigma_b, mu_b)`: the MAP fit.
  `_observations` flattens `solve_mask` into 1-D `(obs_team, obs_prob, obs_y)`
  arrays (one entry per observed competitor–problem cell, 774,639 after including
  censored no-attempt cells in tagged plus supplemental standings). The
  objective is strictly concave (concave log-likelihood + strictly concave
  Gaussian prior) so the MAP is unique; it is solved by **block-coordinate
  Newton** — one closed-form, vectorized Newton step over all `theta` (given `b`),
  then one over all `b` (given the new `theta`), each accumulated with `np.add.at`.
  Numpy only, **no learning rate** (scipy is not installed), and it echoes arch_a's
  alternating style. Converges in ~25 iters / ~5 s on the full tagged fit.
  `laplace_se(ds, theta, b)` returns per-parameter Laplace standard errors (see
  the uncertainty decision below).
- `survival.py` — the solve-time survival variant (strat §5; see decision below).
  Same MAP / block-coordinate Newton as `model.py`, drop-in via
  `estimate_anchored(fit_fn=survival.fit)`; run with `arch_b.run --survival`.
- `validate.py` — external validation against the LLM `difficulty_estimate` in
  `tagged.json` (written by the sibling `llm-integration` tagger from the problem
  statement — independent of standings). Trusts only **editorial-backed** problems
  and reports per-bucket medians + Spearman for all three model outputs.
- `aoj.py` — reproducible AOJ collector and conservative problem matcher. Writes
  `data/aoj_difficulty.json` with source provenance, accepted matches, and
  rejected candidates. Unique normalized titles are accepted only when at least
  three matches corroborate a contest; the practice statistic is ranked within
  contest and is never a fit input.
- `external_validate.py` — per-region check of **all three models** against four
  independent numeric yardsticks: official **Codeforces** problemset ratings (the
  CF-mirror contests in `data/cf_team_contests.txt`), **Kattis** difficulty
  (`data/kattis_difficulty.json`), and the **gym-mirror fixed-θ difficulty**
  (`output/gym_difficulty.json`, when present), plus within-contest **AOJ**
  practice ranks (`data/aoj_difficulty.json`); `--contest <cfid>` prints a
  per-problem table with Spearman + Pearson for one contest (see results below).
  Replaces the old single-contest `sanity_cf.py`.
- `gym_difficulty.py` — fixed-θ Rasch difficulty from the CF gym-mirror
  population (`data/cf_gym_mirrors.json`): each gym solver's own time-accurate CF
  rating fixes θ, so only `b_p` is fit (1-D concave MAP per problem). Writes
  `output/gym_difficulty.json`; `--certify` checks the instrument itself against
  official CF ratings + Kattis and compares team-reduction rules (see the section
  below).
- `metric.py` — **the north-star metric** for model optimization: refits the
  survival model from source and prints one scalar, the shipped two-leg
  calibrated leave-one-contest-out RMSE in CF points over all mapped rated
  mirrors, plus guard checks (raw affine LOCO, gym EC / gym pooled / Kattis
  pooled / AOJ within-contest Spearman, solve-count sanity) that exit nonzero
  on violation. Built as the verify command for auto-research loops; `program.md`
  at the repo root is the matching agent instruction file (see the section
  below).
- `predict_eval.py` — internal held-out response-imputation check on the shipped
  joint inputs. Repeated resolved team/problem responses stay in one split and
  survival duration uses training events only. It reports log-loss / Brier / AUC
  plus calibration; because row retention precedes the split, it is not a
  future-contest forecast (see the 2026-09-06 resolution below).
- `calibrate.py` — fit + apply the affine map from our scale to **Codeforces
  points**, using 15 rated CF-mirrored contests as anchors; writes
  `output/problem_ratings_calibrated.json` (see results below).
- `season_experiment.py` — tries + validates season-separated identity and the
  short-contest filter (`load(season_key=, min_solve_hours=)`); see results below.
- `export_viewer.py` + `viewer_template.html` — self-contained HTML viewer of the
  survival fit on **Codeforces-equivalent points** (difficulty ±SE, team θ/perf);
  writes `output/ratings_viewer_b.html`, published via GitHub Pages.
- `anchor.py` — `estimate_anchored(sigma_theta)`: the same two-phase UCup anchor as
  `arch_a.anchor`, under one shared union-find. Fit UCup (s3+s4) alone, then feed
  each UCup team's `theta_u` back as its Gaussian **prior mean** `mu_t` in the
  tagged + supplemental-standings fit (others keep `MU0`). The pull strength is
  the single global `sigma_theta`, not per-team UCup evidence (see decision below).
- `run.py` — wires it (the anchored fit), writes `output/problem_ratings_b.json`
  (a **distinct** file; arch_a's `problem_ratings.json` is untouched) with a
  `difficulty_se` per problem, runs the same Spearman / top-team verification as
  `arch_a.run`.

Run with the project venv:

    ./.venv/bin/python -m arch_b.run

## Key decisions (Architecture B)

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

- **`sigma_theta` / `sigma_b` are the regularization knobs; default 400** (both,
  exposed on `estimate_anchored`). The prior is weakly informative: it regularizes
  sparse teams/problems (cold start) while letting a well-observed team's own
  likelihood dominate. The scale spread is set by `sigma` — this is MAP shrinkage,
  not a structural cap: a looser prior recovers the full [800, 4000] range, but it
  also pins more *easy* problems to the 800 floor and eventually erodes the
  external validation. Sweeping both `sigma`s together (editorial-backed LLM-bucket
  Spearman, see below):

  | sigma | b range       | floor-pinned @800 | LLM-Spearman |
  |-------|---------------|-------------------|--------------|
  | 200   | [893, 2725]   | 0                 | +0.864       |
  | **400** | [800, 3161] | 14                | **+0.874**   |
  | 800   | [800, 3703]   | 89                | +0.874       |
  | 1600  | [800, 4000]   | 120               | +0.865       |

  Agreement peaks/plateaus at 400–800 then falls; we pick **400** — it gives peak
  agreement and a reasonably wide top (~3161) while collapsing only 14 easy
  problems onto the floor (89 at 800, a 5% loss of easy-end resolution). So `sigma`
  trades easy-end floor-pinning for a wider hard end; arch B stays a touch more
  shrunk than arch_a by choice, in exchange for keeping the easy end resolved.

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
  much-solved problem is pinned tight (`b` SE down to ~10), while a solved-by-none/
  all problem has no data and its SE relaxes to the prior sd `sigma_b` (=400) —
  "we know only the prior." Reported in `output/problem_ratings_b.json` as
  `difficulty_se` (range ~[10, 400], median ~81). A calibrated joint interval
  (full-Hessian Laplace, or MCMC / VI) remains a follow-up.

- **Solve-time survival model (`survival.py`, strat §5).** The binary Rasch fit
  discards *when* a problem was solved. The survival variant models solving as a
  constant-hazard process over the contest window with proportional hazards in the
  ability–difficulty gap (eq. hazard); a solve at `tau` contributes the event
  density, a non-solve a right-censored survival to `T_c` (eq. survlik). **Fixed
  baseline (deviation from strat):** the strat leaves `lambda0` free, but it is
  globally confounded with the level of `b` (shifting all `b` by δ ≡ scaling
  `lambda0`), so we fix it per contest at `lambda0_c = ln2 / T_c`. That both
  removes the confounding *and* calibrates difficulty exactly as the binary model
  (at `theta=b`, P(solve within the window)=½), so the two `b` scales are
  comparable. The cumulative hazard then collapses to `Lambda = ln2 · exp((θ−b)/s)
  · rho` with `rho = tau/T_c` (solved) or 1 (censored) — so `T_c` enters only as
  the fraction of the window a solve used (it cancels for non-solves), making the
  fit robust to `T_c`. `T_c` per contest is the latest observed solve time (no
  duration field exists; observed maxima cluster at 5 h, the ICPC standard). The
  estimator is the same strictly-concave block-coordinate Newton, with the
  Poisson-GLM residual `y − Lambda` and curvature `Lambda` replacing `y − pi` and
  `pi(1−pi)`. It converges slower (~70 iters, the likelihood is stiffer) but still
  in seconds, and yields **tighter** uncertainty (`b` SE median ~28 vs binary ~81)
  because solve times add information. Its decisive advantage: it **distinguishes
  problems with identical solve counts** that the binary model rates identically
  (see the APAC J/K example below).

## Results (Architecture B, current run)

- The corrected full-cell fit uses 774,639 observations. Binary converges in 53
  anchor and 48 tagged iterations; `theta` ≈ [1117, 3538], mean ~1975, and
  `b` ≈ [800, 3759], mean ~2332. Survival converges in 163 anchor and 137
  tagged iterations; `theta` ≈ [1385, 2915], mean ~1963, and `b` ≈ [1182,
  3251], mean ~2209.
- Per-contest Spearman(difficulty, solve_count) median **−1.000** (binary) /
  **−0.995** (survival) over 197 contests. Looser than arch_a's −0.995 *by design*:
  arch_a difficulty is a near-monotone transform of the solve count given the
  field, whereas IRT difficulty also depends on **which** teams solved a problem
  (a problem cleared by weak teams rates easier than one cleared by equally many
  strong teams) — the deviation from pure solve-count ordering is exactly the extra
  signal IRT buys.
- **Survival fit:** `b` SE median remains ~28 (tighter than binary) because solve
  times add information.
