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
mixed ICPC + Universal Cup set). The file *originally* held **213 contest entries**:
67 were exact duplicates of an earlier entry (the same `contest_id` repeated up to
6×, with identical standings but an empty problem list). These have been **dropped
from the source file** (146 unique contests remain); the loader still dedupes
defensively in case the data is regenerated (see the deduplication decision).
`data/ucup_s3.json` and `data/ucup_s4.json` are
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
  UCup-anchored `estimate_anchored()` fit** over the full `tagged.json` (146
  unique contests after dedup), so the viewer's `theta`/difficulties/performances
  match `run.py`. (Previously it ran a plain unanchored `estimate()` on
  `ucup_s4.json` alone.) `--ucup` instead builds the Phase-1 UCup-only fit (s3 + s4,
  76 contests — the anchor itself) to `output/ratings_viewer_ucup.html`.
  Both viewer templates group the contest dropdown by `year` (sorted newest-first),
  show the year and a link to the qoj contest in the header, colour-key legend, and
  remember the open contest in the URL hash (`#<contest_id>`) for shareable links.

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

  - **World Finals → regional top-team linking (`load._link_wf_top_team`).**
    Four World Finals contests (2022–2025, 534 teams, fetched from QOJ via
    `qoj-intergration/qoj.py`) are included in the union-find build.  Most WF
    teams carry a university affiliation but no members, so roster-based identity
    cannot link them.  ``_link_wf_top_team`` maps each (university, season) to
    the best-ranked regional team (lowest rank percentile in its contest) from
    the same university and season, then links the WF identity to that team's
    roster.  This is safe because the WF team *is* the university's top team for
    that season — only the single best-ranked roster per (university, season) is
    linked, avoiding the ~2,900 same-university-multiple-teams collisions that a
    bare affiliation-key would create.  9 new cross-contest links are created
    (e.g. Universidad de Buenos Aires → "Está en el Corman", Purdue → "Purdue
    GLD", SUSTech → "Brno").  The WF solve data is not loaded into the fit (WF
    problems differ from the CF-anchor problems and add only noise); only the
    identity links are used.  WF data: `data/wf_tagged_format.json` (gitignored,
    fetched 2026-07-03).

- **Granularity:** per resolved identity (roster where available, else stable id).
  True individual-level modelling (strat Remark on roster changes) is a follow-up.

- **Deduplicate repeated contest entries (`load.dedupe_contests`).** `tagged.json`
  originally repeated 50 contests (213 entries → 146 unique `contest_id`s, 67
  extras): in every group the first entry carried the problem list and the rest
  were byte-identical standings with an empty `problems` list. The loader's second
  pass replays *standings* once per entry, so a 6×-repeated contest counted each of
  its standing rows 6×, inflating the likelihood/observation counts and every
  team's contest count `N_t` (hence its reliability weight `w_t`). **The duplicates
  were removed from the source file**, so the data is the single clean source of
  truth. `dedupe_contests` (keep the first entry per `contest_id` — the one with
  problems) is *also* kept as a cheap idempotent guard right after the files are
  read — in `load`, in both anchors' shared-union-find build, and in the
  viewers/graph exporters — so the bug cannot silently return if the gitignored
  data is ever regenerated upstream. Measured effect of
  the fix: arch A difficulty mean 2605 → 2216, and its agreement with the
  independent LLM ranking **jumps from Spearman +0.792 to +0.908** (the
  double-counting had been the largest drag on arch A); arch B is barely moved
  (LLM unchanged, CF within noise) because its MAP is dominated by well-observed
  cells rather than raw row counts.

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
  The larger `data/tagged.json` spans 5 seasons (2022–2026, 146 unique contests). We
  keep identity season-agnostic — appending the contest `year` to the key would
  **fragment the single scale into per-year islands**. Measured on the contest-
  linking graph (nodes = contests, edge = ≥1 shared identity): current keying
  leaves **6 components, the largest 141/146 contests** — essentially one scale;
  year-appended keying gives **11 components of sizes 36/35/34/32/…** — roughly
  the per-year contest counts, with only thin inter-year threads. Year-keying
  deletes precisely the cross-year bridges (1,405 rosters and 579 ucup ids that
  recur across seasons) that calibrate the years onto one comparable scale.
  Year turnover is already handled by the roster: of 11,697 distinct rosters only
  1,405 (12%) span >1 year — the other 88% already differ because members
  graduated, so they are already separate identities. The real residual cost is
  that a same-roster-multiple-seasons team gets a single ability blended across
  seasons. `arch_a/export_graph.py` renders both keyings as an interactive graph
  (`output/contest_graph.html`). **Update — season-keying tried and measured
  (`arch_b.season_experiment`, see below):** a *map-corrected* season key (with
  stable `ucup-*` ids left season-agnostic as the backbone) avoids the
  fragmentation — connectivity is unchanged (still one dominant component) — but it
  does **not** improve difficulty estimates (CF agreement slightly *worse*, LLM
  unchanged), because splitting a roster per season gives each identity less data.
  So season-keying stays an opt-in `load(season_key=True)` flag, off by default; a
  time-varying `theta_{team,season}` with a smoothing prior (keeping one identity)
  remains the better follow-up than a hard key split.

- **Keep unofficial participants (`tagged.json` includes them).** The qoj extractor
  can refetch official-only standings (`get_standings(cid)`, the default — unofficial
  excluded server-side); we deliberately *do not* use that view. Measured by
  rebuilding `tagged.json` official-only (`backfill_standings`, no unofficial): rows
  drop 55,654 → 41,488, and **22 contests collapse to zero rows** (they are entirely
  unofficial fields). Worse, the contest-linking graph **shatters from 6 components
  (largest 141) to 69 (largest 51/124)** — the unofficial entries (Universal Cup
  teams and rosters competing unofficially in regional mirrors) are precisely the
  cross-contest bridges that put every contest on one scale (same mechanism as the
  no-year decision above). So unofficial rows stay in: they carry the linking graph.

### Results (current run)

- Converges in ~7 iterations, monotone decreasing `max|dtheta|` < 0.5.
- `theta` ≈ [1369, 3680], mean ~2007 (zero-solve rows dropped + contests deduped).
- `b` ≈ [986, 4000], mean ~2216; boundary-smoothed (see decision), so
  solved-by-all problems clear the 800 floor and most solved-by-none spread below
  4000 (only at-ceiling and empty-contest problems remain pinned).
- Per-contest Spearman(difficulty, solve_count) median **−0.993** (harder
  problems were solved by fewer teams, as expected).
- Cross-contest normalization is now carried by the shared teams (see the
  evidence-weighted-prior decision): per-contest mean ability spreads to std≈110
  vs ≈3.7 with linking removed.

### Caveat introduced by the stronger normalization

Because an unlinked contest now collapses to MU0, a contest's absolute scale
depends entirely on its *linked* teams (those that recur across contests), so a
region carried by a thin minority of linkers sits on a noisier scale than a
densely cross-linked one. **Measured linking by region** (share of appearances by
multi-contest teams / UCup-anchored teams; median linker share per contest):

| region              | % multi-contest | % UCup-anchored | median % linkers/contest |
|---------------------|-----------------|-----------------|--------------------------|
| Asia East Continent | 47%             | 30%             | 65%                      |
| Northern Eurasia    | 43%             | 7%              | 43%                      |
| North America       | 18%             | 3%              | 46%                      |
| Asia Pacific        | 30%             | 10%             | 29%                      |
| Europe              | 13%             | 3%              | 10%                      |

The weakly-linked regions are **Europe** (13% multi-contest, 3% UCup, half its
contests are ~90% one-off national teams) and Asia Pacific — *not* the large Asia
East Continent regionals, which are in fact the **best-linked** in the dataset
(strong Chinese teams play many EC regionals *and* the Universal Cup; ~half the EC
rows are still domjudge-isolated one-offs, but the other half link richly and 30%
anchor to UCup). The graph is fully connected and every contest has linked teams,
so this is a quality gradient, not a break — but it is the price of letting the
shared teams, rather than the prior, set the scale. *(Note: this linking gradient
does not line up with the small per-region offsets vs the LLM yardstick — EA +14
yet best-linked, Europe −24 yet worst-linked — so weak linking is not a
demonstrated source of difficulty bias; per-team prior dependence is also uniform
across regions at ~26%. Confirming any regional offset needs a second independent
per-region anchor beyond the LLM.)*

**How the contest-linking graph is carried: ICPC qualifiers and championships.**
The graph of 146 contests sharing ≥1 resolved team has 2,849 edges.  Two contest
types are the primary bridges connecting otherwise-isolated regions:

| Bridge | Contests | Edges | Shared teams | Avg teams/edge | Contests reached |
|--------|----------|-------|-------------|----------------|-----------------|
| EC online qualifiers ("ICPC") | 6 (2022–2025) | 235 (8%) | 4,474 | **19.0** | 90 |
| Championships (APAC, Europe, NEF, LAC, NAC) | 12 | 593 (21%) | 3,055 | 5.2 | 90 |
| UCup + regionals (everything else) | 128 | 2,046 (72%) | 27,234 | 13.3 | — |

The six "ICPC" contests (the Asia East Continent online qualifiers, 1,272–2,669
teams each) are the **thickest edges** in the graph: 19 shared teams per edge on
average, vs 5 for championships.  When an ICPC qualifier connects to a regional
contest, it does so through many teams simultaneously, making those links
robust.  Of 2,666 distinct EC teams in the qualifiers, 1,385 (52%) link to 90
other contests, carrying the full bridging load for the EC region.  The
remaining 1,281 (48%) are one-off university B/C-teams with valid rosters that
never appear elsewhere — they are genuine single-contest teams, not linking
failures (e.g. 中山大学 alone fields 30 teams in regionals and 16 in ICPC,
almost entirely disjoint rosters).

The 12 championship contests (APAC ×3, Europe ×2, LAC ×2, NAC ×1, NEF ×4)
create more edges (593, 21%) but thinner ones (5 teams/edge).  Championships
bridge 90 contests that would otherwise be disconnected from each other, and 11
contests would fall out of the main component entirely without them.  Linking
rates: APAC/Europe/NAC/LAC championships link 83–100% of their teams at 7–12
cross-appearances each; NEF links only 42–58% (150+ one-off teams per NEF
contest from Russian universities).

The graph remains a single connected component even without championships (106
of 106 linkable contests stay connected via UCup + regionals).  The EC
qualifiers and championships supplement the UCup backbone by bridging the
long-tail of sparsely-linked regional contests.

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
- `survival.py` — the solve-time survival variant (strat §5; see decision below).
  Same MAP / block-coordinate Newton as `model.py`, drop-in via
  `estimate_anchored(fit_fn=survival.fit)`; run with `arch_b.run --survival`.
- `validate.py` — external validation against the LLM `difficulty_estimate` in
  `tagged.json` (written by the sibling `llm-integration` tagger from the problem
  statement — independent of standings). Trusts only **editorial-backed** problems
  and reports per-bucket medians + Spearman for all three model outputs.
- `external_validate.py` — per-region check of **all three models** against three
  independent numeric yardsticks: official **Codeforces** problemset ratings (the
  CF-mirror contests in `data/cf_team_contests.txt`), **Kattis** difficulty
  (`data/kattis_difficulty.json`), and the **gym-mirror fixed-θ difficulty**
  (`output/gym_difficulty.json`, when present); `--contest <cfid>` prints a
  per-problem table with Spearman + Pearson for one contest (see results below).
  Replaces the old single-contest `sanity_cf.py`.
- `gym_difficulty.py` — fixed-θ Rasch difficulty from the CF gym-mirror
  population (`data/cf_gym_mirrors.json`): each gym solver's own time-accurate CF
  rating fixes θ, so only `b_p` is fit (1-D concave MAP per problem). Writes
  `output/gym_difficulty.json`; `--certify` checks the instrument itself against
  official CF ratings + Kattis and compares team-reduction rules (see the section
  below).
- `metric.py` — **the north-star metric** for model optimization: refits the
  survival model from source and prints one scalar, the leave-one-contest-out
  RMSE in CF points over all mapped rated mirrors, plus guard checks (gym EC /
  gym pooled / Kattis pooled Spearman, solve-count sanity) that exit nonzero on
  violation. Built as the verify command for auto-research loops; `program.md`
  at the repo root is the matching agent instruction file (see the section
  below).
- `predict_eval.py` — internal held-out solve-prediction check: train on a random
  80% of observed cells, score predicted solve probability on the held-out 20%
  (log-loss / Brier / AUC + a calibration table). Both fitters accept an ``obs=``
  train split for this (see results below).
- `calibrate.py` — fit + apply the affine map from our scale to **Codeforces
  points**, using the 3 CF-mirrored contests as anchors; writes
  `output/problem_ratings_calibrated.json` (see results below).
- `season_experiment.py` — tries + validates season-separated identity and the
  short-contest filter (`load(season_key=, min_solve_hours=)`); see results below.
- `export_viewer.py` + `viewer_template.html` — self-contained HTML viewer of the
  survival fit on **Codeforces-equivalent points** (difficulty ±SE, team θ/perf);
  writes `output/ratings_viewer_b.html`, published via GitHub Pages.
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

### Results (Architecture B, current run)

- Converges in ~25 iterations / ~5 s (block-coordinate Newton), `max(|dtheta|,
  |db|)` monotone below 0.5.
- `theta` ≈ [953, 3209], mean ~2008; `b` ≈ [800, 3161], mean ~1963. The scale is
  **a touch shrunk toward MU0 vs arch_a** ([1720, 3777]) — MAP shrinkage at the
  chosen `sigma=400` (a looser prior would widen it; see the knob above). It is a
  different, Bayesian scale, not a defect.
- Per-contest Spearman(difficulty, solve_count) median **−0.951** (binary) /
  **−0.973** (survival) over 134 contests. Looser than arch_a's −0.993 *by design*:
  arch_a difficulty is a near-monotone transform of the solve count given the
  field, whereas IRT difficulty also depends on **which** teams solved a problem
  (a problem cleared by weak teams rates easier than one cleared by equally many
  strong teams) — the deviation from pure solve-count ordering is exactly the extra
  signal IRT buys.
- **Survival fit:** `b` ≈ [1209, 3030], mean ~2035; `b` SE median ~28 (tighter than
  binary). Converges in ~70 iters / ~6 s.

### External validation vs the LLM difficulty (`arch_b.validate`)

`tagged.json` carries an LLM `difficulty_estimate` (easy / medium / hard /
very_hard) per problem, written by the sibling `llm-integration` tagger from the
problem **statement** — independent of the standings both estimators use. We trust
it only on **editorial-backed** contests (128 of 146 contests, 1066 of the rated
problems): the LLM label is reliable enough to validate against only where an
editorial shipped. All three architectures' difficulty rises monotonically across
every bucket:

| LLM bucket | n   | arch A | arch B binary | arch B survival |
|------------|-----|--------|---------------|-----------------|
| easy       | 317 | 1618   | 1440          | 1782            |
| medium     | 230 | 2058   | 1942          | 2032            |
| hard       | 247 | 2382   | 2210          | 2153            |
| very_hard  | 272 | 2948   | 2535          | 2318            |
| **Spearman** |   | **+0.908** | **+0.874**  | **+0.880**      |
*(medians per bucket; Spearman over all 1066 problems)*

After the contest deduplication, **arch A now agrees most** with the
editorial-informed ranking (+0.908) — removing the double-counted rows sharpened
its solve-count-driven estimate substantially (it was +0.792 before the fix). The
two IRT fits are essentially unchanged (the duplicates barely moved their MAP) and
remain close behind, with the survival model (which also uses solve *times*) ahead
of the binary Rasch. So on the LLM check arch A leads, while on the Codeforces
numeric checks below the IRT fits stay ahead — the architectures are now closely
matched rather than IRT dominating. (Restricting to editorial-backed problems
*raised* binary arch B's agreement from +0.844 on the full set to +0.874 — the
no-editorial labels are genuinely noisier.)
Run: `./.venv/bin/python -m arch_b.validate`.

### External validation vs Codeforces ratings (`arch_b.external_validate --contest 2206`)

The 2026 ICPC Asia Pacific Championship (qoj contest 3747, 13 problems) was
mirrored on Codeforces (contest 2206), where each problem carries an official CF
problemset rating — an authoritative *numeric* opinion, independent of our
standings. All three models match it strongly (this single-contest per-problem view,
formerly `arch_b.sanity_cf`, is now `external_validate --contest 2206`):

| model           | Spearman vs CF | Pearson vs CF |
|-----------------|----------------|---------------|
| arch A          | +0.945         | +0.938        |
| arch B binary   | **+0.962**     | +0.933        |
| arch B survival | +0.956         | **+0.947**    |

All ~0.95+ on a 13-problem contest is a strong cross-check of the whole approach.
The survival model has the best *linear* calibration (Pearson). **The decisive
case is J/K:** "Worldwide Playlist" (J) and "Time Display Stickers" (K) were each
solved by exactly 76 teams, so the binary model rates them *identically* (1172 =
1172); the survival model separates them by solve time (J 1826 > K 1714) and CF
agrees (J 1700 > K 1300) — a clean illustration of the signal solve times add.
(Caveat: all models still over-shrink the very hardest problems — the three
1-solver problems A/L/M land near ~2400–2650 vs CF's 2900–3500 — since a single
solve barely constrains the top of the scale. Ranking holds; the absolute scale is
addressed by the affine calibration below.)

### Scale calibration to Codeforces points (`arch_b.calibrate`)

The raw scale is *relative* (pinned at the arbitrary MU0=2000). Three of our
contests were mirrored on Codeforces with official problem ratings — the 2026 APAC
(CF 2206), the 2025 Northern Eurasia Finals (CF 2181 = our 2785), and an ICPC
Taiwan contest (CF 2172 = our 2657) — giving **40 anchor problems spanning CF
800–3500**. We fit one global affine map `cf ≈ slope·b + intercept` and validate it
**leave-one-contest-out** (fit on two contests, predict the third):

| model           | Spearman vs CF | affine slope | fit-RMSE | LOCO-CV-RMSE |
|-----------------|----------------|--------------|----------|--------------|
| arch A          | +0.935         | 1.00         | 293      | 372          |
| arch B binary   | +0.898         | 1.29         | 335      | 422          |
| arch B survival | **+0.954**     | **2.41**     | **236**  | **252**      |

The survival model is best and its map **generalizes**: CV-RMSE (252) barely exceeds
fit-RMSE (236), so predicting an unseen contest's CF ratings from the other two is
good to ~250 pts. The slope 2.41 quantifies the compression — the survival scale is
~2.4× narrower than CF. `arch_b.calibrate` applies the survival map to all problems
and writes `output/problem_ratings_calibrated.json` with `difficulty_cf` (clipped to
[800,4000]) and a slope-scaled `difficulty_cf_se`; these are the best estimate of
CF-equivalent points. (Anchors are 3 strong contests; the global affine map is the
simplest correction, not a per-region one. Many more CF-mirrored contests are now
available as anchors — see the per-region validation below — so a richer per-region
or piecewise map is a natural extension.)

### Per-region external validation (`arch_b.external_validate`)

The LLM difficulty (`arch_b.validate`) is a single statement-based opinion that can
*itself* be regionally biased, so a small per-region offset against it (e.g. EA +14,
Europe −24) cannot by itself prove a model bias. To separate real bias from LLM noise
we validate against two **numeric** yardsticks that are independent of our standings
*and* of each other, and report agreement **per region**:

* **Codeforces** problemset ratings for the ICPC contests mirrored on CF (mirror ids
  in `data/cf_team_contests.txt`; ratings via the public `problemset.problems` API —
  no login needed). CF contests are auto-mapped to our qoj contests by problem-name
  vote, so an unmappable mirror (CF 2038, a Russian regional we don't carry) or an
  *unrated* mirror (CF 1662 = SWERC 2021-22, 0 CF ratings) drops out automatically.
  **9 contests / 112 problems** map, covering Asia Pacific, Northern Eurasia, Europe.
* **Kattis** difficulty (1.0–9.x, Elo-style, from open.kattis's practice population),
  scraped once into `data/kattis_difficulty.json` (the listing 403s `WebFetch` but is
  curl-able with a browser UA). Covers **North America (88%)** and **Europe (53%)** —
  exactly the regions CF does not mirror.

| region              | CF n | CF Spearman | Kattis n | Kattis Spearman |
|---------------------|------|-------------|----------|-----------------|
| Asia Pacific        | 80   | **+0.939**  | 7        | (n too small)   |
| Northern Eurasia    | 38   | **+0.970**  | 6        | (n too small)   |
| Europe              | 34   | **+0.858**  | 188      | **+0.761**      |
| North America       | —    | —           | 258      | **+0.821**      |
| **Asia East/West Continent** | — | **none** | ~27/2 | **none** |
| **POOLED**          | 152  | **+0.926**  | 489      | +0.732          |
*(our survival difficulty vs each yardstick over 12 CF-mirror contests; small-n
cells are cross-posted stragglers, not real coverage. Spearman, scale-free.)*

**Verdict on the regional-bias question.** No region shows a difficulty breakdown
against independent numeric truth (+0.86 to +0.98 everywhere measurable), and on the
Kattis check our standings-based difficulty agrees with Kattis **better than the LLM
does** (NA +0.821 vs LLM-Kattis +0.700; Europe +0.761 vs +0.655) — i.e. the LLM is the
noisier referee, so the small per-region LLM offsets were largely LLM-labelling noise,
**not** a model bias. The residual gap — **Asia East Continent had no external numeric
anchor at all** (mirrored on neither CF nor Kattis) — is now closed by the gym-mirror
yardstick below: EC validates at **+0.95 to +0.98** for all three models (230 problems),
the *strongest* region in the gym column, so EC calibration is externally confirmed.
Run: `./.venv/bin/python -m arch_b.external_validate` (`--refresh` refetches CF).

**All three models, side by side** (the module scores every `output/problem_ratings*`
file; this **supersedes** `arch_b.sanity_cf`, which checked a single 13-problem contest
— that per-problem view is now `external_validate --contest <cfid>`, e.g. `--contest 2206`
reproduces the old APAC table with Spearman *and* Pearson):

| model           | CF pooled (n=185) | AsiaPac | N.Eur | Europe | Kattis pooled (n=446) | N.Am | Europe | Gym pooled (n=667) | AsiaEC | Europe | AsiaPac | LLM (n=1090) |
|-----------------|-------------------|---------|-------|--------|-----------------------|------|--------|--------------------|--------|--------|---------|--------------|
| arch A          | +0.912            | +0.914  | **+0.971** | +0.866 | +0.692           | +0.674 | +0.722 | **+0.957**       | **+0.981** | +0.939 | **+0.941** | **+0.905** |
| arch B binary   | +0.880            | +0.866  | +0.940 | +0.883 | +0.758            | +0.781 | +0.758 | +0.919           | +0.951 | +0.886 | +0.914  | +0.871     |
| **arch B survival** | **+0.923**    | **+0.924** | +0.960 | **+0.886** | **+0.793**     | **+0.821** | **+0.761** | +0.950       | +0.962 | **+0.953** | +0.935 | +0.882 |

*(CF n grew 152 → 185 as three unlisted rated mirrors were found and added to
`data/cf_team_contests.txt`: CF 2157 ↔ qoj 2692 via the gym certification, then
CF 1773 (2022–23 NEF) and CF 1938 (2024 APAC) via an exhaustive problemset
sweep of all tagged contests — see the metric section.)*

**arch B survival is the most robust model**: it leads on *both* independent numeric
yardsticks — CF (+0.910) and Kattis (+0.793) — which are the hardest checks (independent
of our standings *and* of the statements), and the solve-time signal makes survival ≥
binary on CF, Kattis, *and* LLM. **arch A wins only the LLM column** (+0.905), but that
is the noisiest, coarsest referee (4 buckets) and aligns with arch A's near-monotone
solve-count difficulty; against the broad 446-problem Kattis set arch A drops to **+0.692**,
clearly behind both IRT models, so its LLM edge does not generalize. (Caveat: per-region
n is modest — Europe CF 34, N.Eur 25 — so single-region orderings can flip on noise, and
Kattis Europe carries some title-collision contamination; the pooled columns are the
reliable read.) In the **Gym column** arch A narrowly leads (+0.957) with survival right
behind (+0.950) — expected, since a fixed-θ Rasch difficulty is close to a monotone
transform of the (ability-weighted) solve rate, the same signal arch A leans on; the
column's real payload is the EC cell, not the model ordering.

### Gym-mirror fixed-θ difficulty (`arch_b.gym_difficulty`)

Consumes `data/cf_gym_mirrors.json` (see the data bullet under follow-ups for how it
was scraped). Every gym solver arrives with a **known ability on the true CF scale**
(`cf_rating_at_attempt`), so unlike both main architectures there is no joint fit:
θ is fixed and each problem's `b_p` is an independent 1-D strictly concave MAP
(the `b` Newton block of `model.py` with per-observation weights, prior
`N(2000, 400²)`). Converges in a handful of iterations; Laplace SE median ~43.
Writes `output/gym_difficulty.json` (700 problems, 57 contests, 23,243 rated team
attempts), which `external_validate` picks up as the third yardstick column.

Key decisions:

- **Trust policy (clist.by-style), since rating & contest count are time-relative.**
  A rating backed by few rated contests is noisy, so each member's likelihood
  weight is the repo's reliability convention `w = 1 − 0.9^n` with
  `n = cf_rated_contests_at_attempt` (1 contest → 0.1, 10 → 0.65, 30 → ~0.96);
  members with no rating yet are excluded, and a team with no rated member is
  dropped (~3% of attempts). Removing the trust weighting entirely barely moves
  the certification numbers, so the policy is cheap insurance, not load-bearing.
- **Team reduction = `lse`:** `θ_team = s·log Σ exp(r_i/s)` — the single solver
  equivalent to the members solving independently (in the hard-problem limit
  P(team solves) ≈ Σ exp((r_i−b)/s)); an equal duo → max+120, trio → max+191.
  Team weight = softmax-contribution-weighted member trust. The obvious
  alternative (`max`: strongest member) certifies identically (ties on all
  yardsticks), so `lse` is kept for the principled team-strength story;
  `--certify` sweeps both.
- **Join by problem name; 5 of the 62 scraped gyms were wrong events.** Gym
  problem *names* come from `data/gym_checkpoints/api_standings.json` and join to
  our problems by normalized title within the contest. All five
  `labels_aligned: false` contests turned out to match **zero** problem names —
  the city/season keyword matching had picked a *different event* in the same
  region/season (four Taiwan contests, e.g. our qoj 2657 is the CF-2172-mirrored
  round but the gym is a separate 2025 Taiwan online round; the Iranian contest's
  qoj names are in Farsi so alignment is unverifiable) — so they are dropped
  wholesale (57 contests / 700 of 763 problems survive). Consequence: the two
  planned certification overlaps with `cf_team_contests.txt` (qoj 2657, 3297)
  were among the bogus five, which forced the certification below onto a
  contest-scoped name vote instead.

**Certification (`--certify`)** — is `b_gym` itself trustworthy?

- **vs official CF ratings:** a contest-level problem-name vote against the rated
  CF problemset (a flat name join is dominated by coincidental generic titles —
  it produced Spearman +0.22 from collisions like "Quick Sort"/"Flowers")
  found one genuine rated mirror among the 57: **qoj 2692 ↔ CF 2157** (not in
  `cf_team_contests.txt`). On its 8 shared problems: Spearman **+0.976**,
  Pearson +0.974, affine slope **1.23** (icept −448, RMSE 213) — i.e. `b_gym`
  is *nearly on the true CF scale already* (compare the survival scale's 2.4×
  compression), which is its main promise as a future calibration anchor.
- **vs Kattis, head-to-head with the survival model on the same 223 problems:**
  gym +0.673 vs survival +0.727 pooled; the gap persists within-contest
  (median +0.824 vs +0.882 over 17 contests), so it is not a cross-contest scale
  artifact. Sweeping the fit knobs (reduction, trust off, solo-only,
  `sigma_b` 400→800, dropping zero-solve attempts — only 1% here) moves nothing
  by more than ~0.01. So the gym population is a **decent but not gold-standard
  referee**: good enough to validate regions (its within-contest ordering vs
  solve rate is near-perfect, median −1.000), authoritative on *scale* (CF check
  above), but a bit noisier than our own survival fit at fine-grained ranking —
  likely virtual-participation effects (solvers who have seen a famous problem
  before) that no fit knob can remove.

**Payload:** the per-region Gym column in the validation table above — in
particular the first external numeric anchor for **Asia East Continent**
(18 contests / 230 problems, all three models +0.95 to +0.98), closing the gap the
regional-bias investigation left open. Run:
`./.venv/bin/python -m arch_b.gym_difficulty` (then `-m arch_b.external_validate`);
`--certify` reproduces the instrument checks.

### The optimization metric (`arch_b.metric` + `program.md`)

With validation settled (every anchored region agrees at +0.86–0.98), the open
front is the **scale**, so model improvement is now driven by a single scalar:
**leave-one-contest-out RMSE in CF points** — for each CF-rated mirror contest,
fit the affine map `cf ≈ slope·b + icept` on the *other* mirrors, predict the
held-out one, pool the errors. Chosen over the alternatives because it measures
the shipped deliverable (`difficulty_cf`) directly in interpretable units, is
sensitive to ranking *and* scale (Spearman is blind to compression), works for
all architectures (each gets its own map), and LOCO punishes anchor overfitting.
Unlike `arch_b.calibrate` (which hardcodes 3 contests), `metric.py` auto-maps
**all** rated mirrors in `data/cf_team_contests.txt` via the
`external_validate` name-vote machinery: currently **185 problems / 15
contests**. Three mirrors were *added to the list* by sweeping every tagged
contest's problem names against the rated CF problemset (contest-level vote):
CF 2157 ↔ qoj 2692 (found by the gym certification), plus CF 1773 (2022–23
NEF) and CF 1938 (2024 APAC) found by the exhaustive sweep — which also showed
**no further rated mirrors exist** for our 146 contests, so anchor growth now
requires new contests in `tagged.json`. Baselines (2026-07-03): **survival
290.2**, binary 344.3. (The old "RMSE ~252" was on the 40-problem / 3-contest
anchor set; the rises to 279 then 290 are the test getting *harder and more
trustworthy* as anchors grew — e.g. CF 1938 alone contributes RMSE 384 — not
model regressions.)

**Noise floor (cluster bootstrap, contests as resampling units):** the pooled
RMSE carries **SE ≈ ±20 points** (95% CI ≈ [251, 327]); per-contest RMSE spreads
160–420 with no single contest dominating. Paired comparisons on the same
anchors are sharper — binary-vs-survival (+54) separates at P<0.001 — but an
auto-research loop must still **treat single-digit improvements as noise**
(`program.md` sets a ~5-point keep threshold, with guard/AUC corroboration for
small wins) because repeatedly selecting on a fixed 185-anchor set overfits it
in a way LOCO cannot detect.

**Guards.** The CF anchors cover only AsiaPac / N.Eurasia / Europe, so a loop
optimizing RMSE alone could silently regress the unanchored regions. The same
fit is therefore checked against floors (baseline − noise margin, calibrated to
the survival model): gym **EC** Spearman ≥ 0.93 (the region with *no* CF
anchors), gym pooled ≥ 0.92, Kattis pooled (NA+Europe convention) ≥ 0.75,
within-contest solve-count sanity ≥ 0.90. Any violation exits nonzero =
"discard the change". Note Asia West needs no exclusion switch: it has no
anchor coverage, so it simply never enters the metric (dropping its contests
*from the fit* is explicitly permitted as an experiment in `program.md`).

**`program.md`** (repo root) is the instruction file for auto-research agents
(karpathy-style `verify`/guard loop): the verify contract (last line
`METRIC loco_cf_rmse=…`, exit 1 = discard, ~5 s deterministic runs), the scope
(fit/likelihood/prior/hygiene code is fair game; `metric.py`, the yardstick
modules, and everything under `data/` are read-only; CF anchor data must never
be read in the fit path), and the prioritized idea list (hard-tail prior,
gym-informed priors, solve-time/hazard refinements, `wrong_attempts`, …).

### Auto-research campaign on the metric (2026-07-03): verdict PLATEAU

A 25-iteration autoresearch loop (`program.md`) attacked `loco_cf_rmse`
(baseline **290.2**) with one structural change per iteration. The loop ran in
two phases: iterations 1–15 by **Claude Fable 5**, iterations 16–25 by
**DeepSeek v4 Pro** (after a session handoff). **2 iterations kept, 23
discarded** — the model is at a robust local optimum; further gains need new
anchor data rather than fit changes. Final metric **288.0** (−2.2, under the
±5-point threshold but held-out AUC corroborated: 0.8810 → 0.8858). Full
per-iteration log in `autoresearch/autoresearch-260703-1733/classic-results.tsv`.

The only successful changes were **data-side identity fixes** (both by Fable):
the roster token was normalized (Unicode NFKD + strip case/punctuation) and
rosters sharing ≥2 members were unioned (~3.7k near-miss pairs resolved), then
domjudge rows with no roster were linked across contests by trusted recurring
team names (~5.3k names × ~13k appearances). Together they cut RMSE from 290.2
to 288.0 while improving survival held-out AUC from 0.8810 to 0.8858 and
lifting the gym-pooled guard from 0.950 to 0.954.

**Everything else was within noise or worse** (range 286.8–321.9; best single
improvement −1.2 from the new baseline at σ_θ=600, but AUC regressed to 0.8838
so it was discarded per the corroboration rule). The deepseek phase (10
iterations) retried the most promising fable-era ideas on the improved identity
graph (σ_θ=500/600, Weibull k=1.25, per-contest hazard intercept, evidence-
scaled priors, time-varying θ, anchor weight) — all either regressed AUC or
landed within noise. Two additional identity experiments (lower name threshold,
1-member rosters) made things worse. A data-driven per-problem prior (solve-rate
→ μ_b) blew up to 305.9 — confirming the Rasch likelihood alone is better than
any heuristic prior.

**Where the error lives** (unchanged from the original report — identity fixes
don't touch the hard tail because 0–1 solver problems have no linking data to
improve): the cf[3200,3600) bucket carries ~41% of pooled MSE (n=28, RMSE
~476, bias −321) — nothing in standings data distinguishes CF 2900 from CF 3500
when at most one team solved. Per-contest offsets contribute ~13%; the rest is
within-contest variance. Progress needs new anchor data: more CF-rated mirrors
in `tagged.json`, ideally gym-covered, or member→CF-handle data for true
ability anchoring.

### Second auto-research campaign (2026-07-03, DeepSeek v4 Pro): verdict PLATEAU

A second 25-iteration campaign (`program.md`) probed data-side identity
improvements and model hyperparameters at the new **288.0** baseline (after
the identity fixes above). **1 iteration kept, 24 discarded** — the model
is confirmed at a robust local optimum.

**The one kept change:** gym-informed difficulty prior — soft-anchoring
problem difficulties toward `output/gym_difficulty.json` estimates
(N(b_gym, 400²) prior mean) for ~300 gym-covered problems.  Metric
288.0 → 287.5 (−0.5, within the ±5 point noise floor), but both gym
EC Spearman (+0.960 → +0.967) and gym pooled Spearman (+0.954 → +0.959)
improved, so it was kept on the guard-corroboration rule.  Held-out AUC
was unchanged (0.8858).

**Everything else was within noise or worse.** sigma_θ sweeps (300→600)
best at 500 (−1.7 RMSE but AUC regressed 0.8858→0.8849, discarded per
corroboration rule).  Data-side changes — script-mismatch linking
(Chinese↔English names, 60 teams), last-name-only matching (30 teams),
name-order-robust tokenisation — all within ±0.7 points of baseline.
Tighter per-problem gym priors (σ_b ~ gym SE) blew up the metric to 306
(kattis guard nearly failed).  Wrong-attempt penalty in the survival
likelihood regresses at any α > 0.  min_solve_hours variations have
no effect (CF anchors are a fixed set).  A World Finals affiliation
bridge (4 WF contests fetched, 33/36 WF rosters already matched) was
neutral.

**WF → regional linking (KEPT).** Four World Finals contests (2022–2025,
534 teams) were fetched via `qoj-intergration/qoj.py` and saved to
`data/wf_tagged_format.json`.  ``load._link_wf_top_team`` maps each
(university, season) to the best-ranked regional team and links the WF
identity to that team's roster — the WF team *is* the university's top
team for that season.  9 new cross-contest links are created (e.g.
Universidad de Buenos Aires → "Está en el Corman", Purdue → "Purdue
GLD").  The gym EC guard improved (+0.960 → +0.962) confirming better
Asia East Continent connectivity, though the CF-RMSE metric is blind
to these links (the linked universities don't appear in the 15
CF-anchor contests).  Only the identity links are used; WF solve
data is not loaded into the fit (WF problems differ from CF-anchor
problems).

**wrong_attempts wired.** The `wrong_attempts` field (present in
`tagged.json` but previously unused) is now loaded into
`Dataset.wrong` for future model use, though the tested penalty
models (multiplicative Lambda scaling) did not improve the metric.

Full per-iteration log in `autoresearch/autoresearch-260703-1838/classic-results.tsv`.

### Internal validation: held-out solve prediction (`arch_b.predict_eval`)

Complementary to the external ranking checks: train on a random 80% of observed
cells, predict the solve probability on the held-out 20%, score with proper rules.
Both arch B fits predict the same quantity on a held-out cell — P(solve within the
contest) — so this isolates the value of the solve-time signal the survival model
uses in training. (Architecture A has no per-cell likelihood, so it is not in this
comparison.)

| model           | log-loss | Brier  | AUC    |
|-----------------|----------|--------|--------|
| arch B binary   | 0.3173   | 0.1001 | 0.8710 |
| arch B survival | **0.3169** | **0.0990** | **0.8810** |

The survival model generalizes **better** on every metric — the AUC lift
(0.871 → 0.881) is the clearest sign that training on solve *times* sharpens the
latent abilities/difficulties. Trade-off: the binary model's probabilities are
very well calibrated (predicted ≈ empirical in every bin), whereas the survival
model is mildly **under-confident** in the 0.5–0.9 range (better ranking, slightly
worse probability calibration — the expected effect of scoring a hazard-model
solve probability against a binary outcome; a recalibrated link is a follow-up).

### Season-separated identity + short-contest filter (`arch_b.season_experiment`)

Two data options were tried and validated on the UCup-anchored survival fit:

* `load(season_key=True)` — separate a recurring roster's ability by ICPC season,
  using the **map** (championships / World Finals belong to the *previous* season:
  `load.season_of`); stable `ucup-*` ids stay season-agnostic as the cross-season
  backbone, so the scale does not fragment.
* `load(min_solve_hours=3.5)` — drop short-format contests (warm-ups, 3 h rounds)
  whose latest solve is under 3.5 h (a duration proxy; 4.5 h would wrongly drop
  small 5 h regionals whose last solve happened early). Now the **default in
  `arch_b.run`**.

| config             | teams | contests | graph (comp / biggest) | CF Spearman | CF LOCO-RMSE | LLM Spearman |
|--------------------|-------|----------|------------------------|-------------|--------------|--------------|
| baseline           | 33991 | 146      | 9 / 138                | +0.954      | 252          | +0.880       |
| +5 h filter        | 33186 | 133      | 3 / 131                | +0.954      | 252          | +0.880       |
| +season +5 h       | 34117 | 133      | 3 / 131                | +0.949      | 270          | +0.880       |

The **5 h filter is a clean hygiene win** — identical external agreement while
removing 13 noisy short contests and *improving* connectivity (9→3 components), so
it is on by default. **Season-keying is validated as not worth it**: it preserves
connectivity (the map + stable-ucup backbone avoids the per-season islands that
sank plain year-keying) but slightly *worsens* CF agreement and leaves LLM
unchanged — the +929 per-season roster splits each carry less data, and that cost
cancels the time-varying benefit for *difficulty*. It stays an opt-in flag.

### 2PL per-problem discrimination, by region (`arch_b.twopl` / `arch_b.twopl_region`)

Motivated by the observation that in some regions the solve rate almost *determines*
difficulty (e.g. the large **Asia East Continent** online qualifiers) while others
(**Asia Pacific** / Japan) show much more spread at the same solve rate. That is the
signature of per-problem **discrimination** `a_p` (strat eq. twopl) — the one thing
the shipped 1-parameter Rasch fit cannot represent (it fixes every logistic slope at
`1/s`). So 2PL was prototyped to ask: does discrimination vary by region, and is it
worth modelling?

- **Model / fitter (`twopl.py`).** Keep `theta`, `b` on the ELO scale and add a
  dimensionless multiplier `alpha_p` (Rasch ≡ `alpha_p=1`):
  `pi = sigma(alpha_p·(theta−b)/s)`. Fit `g_p = log alpha_p` with a Gaussian prior
  `g_p ~ N(0, sigma_g^2)` that both regularizes sparse problems back to Rasch *and*
  (with the existing `theta` prior) fixes the 2PL scale indeterminacy
  (`theta→c·theta, b→c·b, alpha→alpha/c`). Same block-coordinate Newton as
  `model.py` with a third block: `theta`/`b` blocks are unchanged in form (they enter
  `eta` linearly), the `g` block uses **Fisher scoring** (expected information, since
  its observed Hessian can be indefinite). The joint objective is **non-convex** (the
  `alpha·theta` interaction), so it **warm-starts from a Rasch basin** (`alpha=1` for
  the first `warmup` iters). Converges in ~65 iters / ~6 s.

- **Finding 1 — discrimination does track region, in-sample.** UCup-anchored
  (`sigma_g=0.5`), median `alpha` by region: **Asia East Continent 2.14**, Europe
  1.98, Northern Eurasia 1.91, Asia Pacific 1.68, **North America 1.35**. EA's huge
  homogeneous fields produce the sharpest-discriminating problems; tiny-field NA
  (median field 16) the dullest. So the observation is *representable*. **Caveat: this
  is confounded with field size** (EA median field 198 vs NA 16) — a large field makes
  the logistic transition look sharp, so per-region `alpha` is partly a field-size
  artifact, not a pure intrinsic-problem property. (And the within-region
  `b ~ logit(solve_rate)` residual SD did **not** cleanly fall as `alpha` rose, so
  "discrimination = tightness" is not a clean 1:1.)

- **Finding 2 — but 2PL does not generalize; it overfits.** On the held-out
  solve-prediction check (80/20, identical cells), 2PL is **worse than Rasch at every
  regularization level** — even shrunk almost to Rasch (`sigma_g=0.15`, median
  `alpha≈1.08`):

  | model | log-loss | Brier | AUC |
  |-------|----------|-------|-----|
  | Rasch | **0.3173** | **0.1001** | **0.8710** |
  | 2PL `sg=0.15` | 0.368 | 0.106 | 0.853 |
  | 2PL `sg=0.50` | 0.410 | 0.111 | 0.853 |

  A handful of problems escape to the `alpha` clamp (4.48) regardless of the prior and
  make over-confident, rank-wrong held-out predictions (AUC drops, not just
  calibration). The **LLM-bucket Spearman also falls** to **+0.856** (vs shipped Rasch
  +0.874, survival +0.880, arch A +0.908), and difficulties move materially
  (`corr 0.979` to Rasch but 895/1579 problems shift >100). So the extra parameter
  buys nothing on either the internal predictive check or the external ranking.

- **Verdict.** 2PL *captures* the regional discrimination signal but as prototyped it
  **overfits and degrades validation**, so the shipped fit stays **Rasch** (the
  original scope decision now has evidence behind it). To make 2PL pay off would need
  a field-size-aware discrimination prior (decoupling `alpha` from sheer field size),
  a tighter clamp / heavier-tailed `g` prior, and ideally a 2PL re-derivation of the
  *survival* likelihood rather than the binary one. `twopl.py` is kept as a runnable
  prototype (`python -m arch_b.twopl_region` reproduces all numbers above).

## Out of scope / follow-ups

- **2PL discrimination** `a_p` (strat §4) on top of the Rasch fit in `arch_b`
  (**prototyped — overfits, see the 2PL section above; not shipped**),
  plus a calibrated joint posterior (full-Hessian Laplace / MCMC / VI) beyond the
  per-parameter Laplace SE already emitted as `difficulty_se`.
- **Per-contest `T_c` from real durations** — the survival model infers `T_c` as
  the latest solve time (a slight underestimate); a true duration field (e.g. from
  the qoj extractor) would sharpen the solved-cell time fractions.
- **Member-level identity** and entity resolution across sources (strat
  Remarks), to densify linking and handle roster changes.
- **Time-varying ability** `theta_{team,season}` with a season-to-season smoothing
  prior — keeping **one** identity (unlike the hard `season_key` split, which was
  tried and slightly hurt difficulty, see above) but letting ability drift, so a
  recurring roster neither collapses to one blended value nor loses data to a split.
  A dedicated team-performance prediction eval (not just difficulty) is the right
  way to measure its benefit.
- **Richer CF calibration.** The affine map to CF points (`arch_b.calibrate`) is
  fit on 40 anchors from 3 contests and validated leave-one-contest-out (RMSE
  ~250). **9 more CF-mirrored contests / 112 problems are now wired up**
  (`arch_b.external_validate`, see the per-region validation above), spanning Asia
  Pacific / Northern Eurasia / Europe — enough to fit a *per-region* or piecewise map
  and shrink the residual (open). The 1-solver hard-end ordering the map can't fix
  (A/L/M) would also benefit from a heavier-tailed difficulty prior in-model.
- **No external anchor for Asia West Continent.** ~~Asia East Continent~~ — **closed**:
  the gym-mirror yardstick (`arch_b.gym_difficulty`) now anchors EC at +0.95–0.98
  for all three models. Asia *West* remains uncovered (its one scraped gym, the
  Iranian contest, was a wrong-event match — see the gym section).
- **Use `b_gym` as calibration anchors / difficulty priors.** `b_gym` sits nearly on
  the true CF scale (certify: affine slope 1.23 vs CF ratings), and covers 700
  problems across 5 regions vs the 40 anchors `arch_b.calibrate` currently uses —
  enough for the per-region / piecewise CF map above, and/or as per-problem prior
  means `N(b_gym, se)` inside the main MAP fit (would have to *earn its place* on
  held-out prediction, since the gym referee is slightly noisier than the survival
  fit at fine ranking — see the certification).
- ~~**Add CF 2157 to `data/cf_team_contests.txt`.**~~ **Done** — the CF columns
  and the metric anchor set now include it (CF pooled n 152 → 160).
- **CF anchoring** if member→handle→rating data becomes available, to turn the
  relative scale into true Codeforces-equivalent points.
- **`data/cf_gym_mirrors.json` — scraped; now consumed by `arch_b.gym_difficulty`
  (see that section).** For contests whose
  problems were also mirrored as a Codeforces **Gym** contest (training replay, not
  the officially-rated rounds `cf_team_contests.txt` uses), CF's own practice
  population gives an independent difficulty signal: solve outcome vs. each
  solver's *own* established Codeforces rating — closer to the strat's originally
  recommended CF-anchor (eq. cfprior) than anything else in the repo, since our own
  contestants have no CF handles (see the roster-identity decision above).
  - **Contest → gym matching (62 of 146 contests mapped).** Matched two ways:
    36 by a distinctive city/country keyword in `contest_name` + season year
    (e.g. "Nanjing" 2023 → the CF gym titled "The 2023 ICPC Asia Nanjing Regional
    Contest"); 26 more (the Europe/North America contests, whose `contest_name` is
    only the broad sub-region label like "Northwestern Europe" — indistinguishable
    from NWERC/BAPC/UKIEPC/GCPC/NCPC by name alone) by the same problem-name-vote
    technique `external_validate._cf_mapping` already uses for CF-rated mirrors,
    pointed at each candidate gym's problem list instead of `problemset.problems`.
    The gym listing itself was scraped through an authenticated browser session
    (`claude-in-chrome`) since CF sits behind a Cloudflare bot check that blocks
    plain `curl`/`WebFetch`; standings and rating history, once a user-supplied CF
    **API key + secret** were available, came from the signed `contest.standings` /
    `user.rating` endpoints directly (`curl`/Python, HMAC-SHA512 `apiSig`, no
    browser needed — gym `contest.standings` returns `"You have to be authenticated"`
    without a signed request even though the contest itself is public).
  - **Upsolvers excluded.** `contest.standings` mixes real timed attempts
    (`participantType: VIRTUAL`/`CONTESTANT`) with open-ended `PRACTICE` rows (no
    time pressure, solved whenever) — 34% of all rows (17,353 of 50,716) were
    `PRACTICE` and are dropped, since unlimited time on a problem is a different
    signal from solving it live and would bias problems toward looking easier than
    they are under real contest conditions. `ghost: true` rows (the original
    onsite field, replayed into the mirror's standings for comparison) already
    contribute nothing — they carry `members: []`, no real CF handle.
  - **Rating and contest count are time-accurate, not "current."** A gym's virtual
    attempt can happen years after the original contest, and a solver's CF rating
    drifts a lot over that span, so using their rating *today* would be
    systematically wrong for older mirrors. Each solver's full rating-change
    history (`user.rating`, one call per handle — not batchable like `user.info`)
    is fetched once, then `cf_rating_at_attempt` / `cf_rated_contests_at_attempt`
    are computed by truncating that history to entries at or before the party's
    own `startTimeSeconds` (bisection on timestamp). A solver with no rated
    contest yet at attempt time gets `cf_rating_at_attempt: null`,
    `cf_rated_contests_at_attempt: 0` (kept, not dropped — 3,016 of 57,695 rows).
  - **Collection notes.** CF's rate limit rejected even 4 concurrent signed
    requests (`"Call limit exceeded"`, HTTP 429) but tolerated a plain serial loop
    at the network's natural ~0.2s/call latency with zero added delay (17,162
    handles in ~64 min, 0 failures). Progress was checkpointed to
    `data/gym_checkpoints/` (gitignored, survives outside `/tmp`) every 200
    handles and the fetch resumes from there, since `/tmp` does not survive a
    machine restart.
  - **Schema.** Keyed by our `qoj_contest_id`; each entry has `gym_id`/`gym_url`,
    `gym_problem_labels` vs. `our_problem_labels` (5 of the 62 mismatch — different
    problem subset between the mirror and our record — flagged via
    `labels_aligned` rather than dropped, so a consumer must join by problem
    *name*, not letter, when false), and `teams`: one entry per team **attempt**
    (`participant_id`, `team_name`, `rank`, `attempt_time`, the shared `solved`
    letter list — since solving is per-team, not per-member — and `members`,
    each with `handle`, `cf_rating_at_attempt`, `cf_rated_contests_at_attempt`).
    Kept grouped by team rather than flattened, so a consumer can choose how to
    reduce a team to one ability value (max member rating, best-known member,
    etc.) instead of that choice being silently baked into the file
    (25,003 teams / 57,695 member-rows total).
  - **Consumed (2026-07-03).** `arch_b.gym_difficulty` runs exactly the fit this
    bullet anticipated — a fixed-θ Rasch MAP for `b_p` with a trust-weighted
    team reduction — and `external_validate` now reports it as the third
    yardstick column. Note the matching caveat discovered on consumption: the
    five `labels_aligned: false` entries are *wrong gym events* (zero
    problem-name overlap), not merely re-lettered mirrors.
