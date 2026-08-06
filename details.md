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

`data/tagged_with_official.json` — same 146 contests, with an added `official:
true/false` field on every standing row. Official/unofficial tags are sourced from
**XCPCIO** (`https://board.xcpcio.com`), which hosts the official ICPC scoreboard
data (domjudge-imported onsite teams). For 26 East Asia regional contests (seasons
47th–50th, 2022–2025), XCPCIO's team.json was fetched and teams were matched by
normalized name against QOJ standing rows (see `scripts/add_xcpcio_official.py`).
13 contests carry **explicit** XCPCIO group tags (`"group": ["official"]`); the
other 13 (older 47th/48th seasons where XCPCIO team data lacks per-team group
labels) use the entire XCPCIO team list as the official field — validated by
comparing XCPCIO team counts against domjudge-id row counts (they match exactly).
12 East Asia contests could not be matched (6 online "ICPC" qualifiers, 3 EC-Final
warm-ups, Shanghai 2023 which XCPCIO has no entry for, "China" / "Grand Prix of
China" which lack a city match). Non-EA contests are unaffected.

`data/ucup_s3.json` and `data/ucup_s4.json` are
the two Universal Cup seasons (43 and 33 contests) used to anchor the scale.
Per standing row: `rank`, `team_id`, `members`, `total_solved`, and per-problem
`{solved, score, time_seconds, wrong_attempts}`. This yields the model inputs
`y_tp` (solved), `tau_tp` (solve time), `r_{t,c}` (rank).

`data/icpc_2020_2021.json` adds 14 Asia East ICPC regional contests
(8,487 standing rows, 179 problems), and `data/petroz_2022_2026.json` adds 57
Petrozavodsk Programming Camp contests (9,694 rows, 671 problems). Both were
fetched from QOJ on 2026-07-23 using dashboard problem labels plus unofficial
standings only—no statements, editorials, or solutions. Architecture B loads
these 71 supplemental contests with `tagged.json`; the `MIN_SOLVE_HOURS=3.5`
filter leaves 204 fitted contests total. Their value is extra cross-contest team
evidence: calibrated LOCO improves 264.5 → 261.6, corroborated by an original-cell
holdout (AUC 0.885761 → 0.886000).

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
  anchoring is not available in the shipped fit. A 2026-07-21 feasibility study
  found a sparse external seed set but has not yet been collected or integrated
  (see the participant-rating section below). Instead we anchor with a **constant
  neutral prior `MU0 = 2000`** (a mid Codeforces rating) for every team. This
  replaces the plan's original "center to mean 0", which is incompatible with the
  clamp below (centering would push half the teams under the floor mid-loop).
  Outputs are therefore a relative scale pinned near 2000, *not* certified
  CF-equivalent points.

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
    bare affiliation-key would create. A 2026-07-23 audit found the implementation
    had omitted both guards: it applied the affiliation join to 3,605 no-roster
    rows in 120 non-WF contests and, with season keying disabled, selected one
    globally best roster per university. The fixed join filters to actual World
    Finals and always matches on `season_of(c)` while keeping the identity token
    season-agnostic; 13 no-roster WF rows currently resolve to a roster. This
    correction improves calibrated LOCO 266.4 → 264.5. Example links include
    Universidad de Buenos Aires → "Está en el Corman", Purdue → "Purdue GLD",
    and SUSTech → "Brno".  The WF solve data is not loaded into the fit (WF
    problems differ from the CF-anchor problems and add only noise); only the
    identity links are used.  WF data: `data/wf_tagged_format.json` (fetched
    2026-07-03).

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
  tagged + supplemental-standings fit (others keep `MU0`). The pull strength is
  the single global `sigma_theta`, not per-team UCup evidence (see decision below).
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

The raw scale is *relative* (pinned at the arbitrary MU0=2000) and compressed
vs CF, more so in the hard tail. **Upgraded 2026-07-04** from the original
single global affine on 3 hardcoded contests (LOCO ~252 on that 40-anchor set)
to a **two-leg map** validated on all 15 rated mirrors (185 anchors,
auto-mapped by the `external_validate` name vote):

1. **Shape leg (gym-learned, nonlinear).** A monotone quantile map `f`
   (NBINS=15 binned medians, linearly interpolated/extrapolated, shrunk toward
   its own linear approximation by ALPHA=0.75) fit on the ~660 (our `b`,
   `b_gym`) pairs — the gym yardstick is certified nearly CF-native in scale
   (affine slope 1.23 vs official CF). qoj 2692 (the only gym∩anchor contest)
   is excluded, so `f` shares no problems with the anchors that score it.
   Because `f` is monotone it **cannot reorder our problems** — it consumes
   only the gym population's trustworthy half (scale), none of its noisy half
   (ranking), which is exactly the division the two failed in-fit experiments
   established.
2. **Scale leg (affine).** `cf ≈ A·f(b) + B` fit on the official CF anchors;
   per LOCO fold it is refit on the 14 training contests.

**LOCO validation (survival model): 288.4 → 266.4** (−22). Cluster bootstrap
of the paired difference: mean −22.1, 95% CI [−43.9, −3.4], **P(worse) =
1.05%**; 10/15 contests improve; the cf≥3200 tail improves RMSE 477 → 434.
Controls: a per-fold *quadratic* on the CF anchors alone scores **297** (worse
than affine — the win is the gym information, not flexibility); per-region gym
shapes overfit (298); the result is stable across NBINS 8–25 (271–276 at
α=1) and α 0.5–1.0 (266–271). Hyperparameters were chosen on this same
anchor set (the known residual risk of a fixed anchor pool), but the plateau
is broad and the CI excludes zero. `calibrate` prints both LOCO columns per
model on every run; if `gym_difficulty.json` is absent it falls back to the
plain affine. `difficulty_cf_se` is scaled by the *local* slope of the
composed map (central difference). Note the fit-side metric (`arch_b.metric`)
is untouched and still reads 288.4 — it scores the raw fit's affine
calibratability, and its history stays comparable; the shipped deliverable's
LOCO is the 266.4 figure. Experiment log:
`autoresearch/autoresearch-260704-0150/classic-results.tsv`.

### East-Asia medal badges + lowest-gold analysis (`arch_b.medals`)

ICPC **Asia East Continent** regionals award medals by cumulative percentile of
the official teams that solved ≥1 problem: gold 10%, silver 30%, bronze 60%.
`arch_b.medals` assigns every problem of the medal-awarding EA contests a
**bronze / silver / gold / platinum / star badge** (weakest → hardest) and reports
the **lowest gold-medal team** per regional. Writes `output/medal_badges.json`
(`{"contests": [...], "problems": [...]}`); run
`./.venv/bin/python -m arch_b.medals`.

Key decisions:

- **Official field = XCPCIO team data** (replaced the old domjudge-id-prefix
  heuristic). ``data/xcpcio_ea_official.json`` caches XCPCIO official-team
  identity keys for 28 EA contests (regionals + EC-Finals, 2022–2025), fetched
  via ``scripts/build_xcpcio_official.py``. XCPCIO's team.json carries explicit
  ``"group": ["official"]`` tags for 49th/50th seasons; for older 47th/48th
  seasons the entire XCPCIO team list is the official field (domjudge-imported
  onsite teams). Teams are matched to QOJ standing rows by normalized
  name-matching (exact set intersection of candidate keys: bare name, org-name
  pairs with multiple separators, parenthetical-stripped variants, and
  member-stripped display_name_raw prefixes). Medal cutoffs are ranks
  ⌈0.10 n⌉ / ⌈0.30 n⌉ / ⌈0.60 n⌉ within the XCPCIO-identified official field,
  with ⌈ceil⌉ rounding (the official rounding rule is not in the data).
- **Scope: medal events only** (user decision). The 6 online qualifiers
  (contest_name ``"ICPC"``, 1.3–2.7k teams) and the EC-Final warm-ups award no
  medals and are excluded → 28 contests / 358 problems (2022–2025).  Includes
  EC-Finals (Shanghai 2023 = 48th EC-Final, China 2024 = 49th EC-Final).
- **The medal bar is an empirical 50%-crossing, not an Elo performance
  rating.** The original design compared the fitted difficulty `b_p` against
  `elo.performance_rating` of the cutoff teams. Measured against the cutoff
  cohorts' actual solve rates, that rank-inversion performance is **inflated on
  the Rasch/survival `b` scale** (predicted−actual solve rate +0.10 at the
  bronze cutoff, +0.34 at gold: gold-badged problems were solved by only ~10%
  of the gold band). Even the well-centred alternative — the ability whose
  *expected solve count* matches the cutoff team's (zero mean bias by
  construction) — is miscalibrated exactly at the decision point: where it
  predicts 50%, cutoff cohorts actually solve 57–92%, because EA fields' solve
  curves are far steeper than the global Rasch slope (the 2PL finding: EA
  discrimination ~2.1). So the bar is measured directly: per tier, take the
  ±7-official-rank cohort around the cutoff team, isotonic-regress its
  per-problem solve rates against `b` (PAVA, non-increasing), and set
  `bar_tier` = the `b` where the smoothed rate crosses 0.5. Badge = the weakest
  tier whose bar clears `b_p`, else **platinum** — still a threshold on the fitted
  difficulty, so badges are monotone in `b`, cross-contest comparable, and
  CF-mappable (the `calibrate` two-leg map is monotone, so CF-space badges are
  identical).
- **Star tier above platinum (the champion bar).** The badge ladder is
  bronze < silver < gold < **platinum** < **star** — platinum/star are *above* gold,
  not below bronze (a recurring misreading; the viewer spells it out). With
  only four tiers, "platinum" was 52% of all problems and lumped "just above the
  gold bar" with "solved by nobody", so one more crossing was added, anchored
  at the **champion cohort** (`TOP_COHORT = 5`, the top-5 official teams, exact
  cohort — no window): **platinum** = above the gold bar but the champions still
  solve it at even odds (it decides ranking *within* gold), **star** = beyond
  even the champions. This split the 200 platinum problems into **119 platinum + 81
  star**; star problems almost all have 0–2 official solves (a scarcity rule
  "≤2 official solves" selects a nearly identical set of 82, cross-validating
  the bar). A champion cohort that solves everything at ≥50% pins its bar to
  4000 → that contest has no star problems (HK & Macau 2022, Shenyang 2022 —
  correct: their top-5 were world-class). *Caveat:* 5 teams is the noisiest
  cohort of the four bars; in small/weak fields the star bar can sit close to
  the gold bar (Hong Kong 2024 gets 7 star problems, one solved by 11 teams).
- **Sanity badge: band majority.** A model-free column badges each problem with
  the weakest medal *band* (gold ranks 1..g / silver g+1..s / bronze s+1..z)
  where ≥50% of official teams solved it; if none, the top-5 majority splits
  platinum (≥50%) from star. Agreement with the model badge is
  **74%** (282/383) and the disagreements are almost all one step in the
  expected direction: the band's *median* team is stronger than the boundary
  team, so the band-majority badge skews one tier easier. The medal-bar badge
  is primary because the medal semantics is about the boundary ("what you
  needed to solve to reach the tier").

Results (current run): badge totals **86 bronze / 36 silver / 40 gold / 92
platinum / 104 star** (28 contests, 358 problems). Internal consistency:
the non-platinum badge count per contest ≈ the lowest gold team's solve count
(e.g. Jinan 2022: 6 solves, badges BBBSGG; Wuhan 2025: 6, BBBGGG). The **gold
bar in CF points** spans [2137, 2932], median **2601**: hardest golds at
EC-Final 2024 "China" (2932) and EC-Final 2023 "Shanghai" (2897); softest at
Grand Prix of Shenyang 2025 (2137). The lowest gold team solves 4–8 problems
and its classic Elo rank-inversion performance sits at 2184–2502.

**Viewer (`arch_b.export_medal_viewer` + `medal_viewer_template.html`).**
`output/medal_viewer.html` is the interactive presentation of the analysis —
self-contained (data embedded, no server, vanilla JS/SVG), light/dark aware via
`prefers-color-scheme`. Sections: a season filter scoping everything below; a
KPI row (contest/problem counts, median gold bar, model↔empirical agreement,
badge-distribution stacked bar); a dot-range chart of the three medal bars per
contest in CF points (sorted by gold bar, hover tooltips showing all three
cutoff-team details, click-to-open, URL hash `#<contest_id>` like the other
viewers); a contest detail view (three cutoff-team panels for gold/silver/bronze
with solved count, penalty, full-field rank, and Elo performance; problems
as lettered lollipop dots on the difficulty axis against the medal-bar
threshold lines and a shaded platinum zone, plus a per-problem table with band
solve-rate meters and a † marker where the empirical badge differs); and a
sortable gold-cutoff-team table. The detail strip shades both the platinum zone
(gold bar → star bar) and the star zone (beyond the star bar), the table
carries a Top-5 (champion) solve-rate column, and a star bar pinned at the
scale ceiling renders as "— (champions solve all)". Design notes: badge colors
are medal-semantic (bronze/silver-blue/gold/violet platinum/red star) and were
**validated with the dataviz palette checker in both modes** (5 slots, worst
adjacent CVD ΔE ≥ 58; the gold hue is
sub-3:1 on the light surface, mitigated by letter labels on every chip and the
table views); all dynamic text is inserted via `textContent` (team names in
the data contain raw HTML fragments, which the exporter also strips). One
bug worth remembering: the per-row transparent SVG hit-rect must be appended
*last* in its group — appended first, the row's dots/line/label paint above it
and swallow every click (SVG hit-tests in paint order).

### Regional medal-cutoff chooser (`arch_b.medal_predict`)

The default command now answers the decision question directly: rank the eight
ordinary 2026 Asia East regional sites by the predicted gold cutoff.  `--target
silver|bronze` changes the medal target, `--cities ...` compares a supplied
shortlist, `--city` prints all three bars for one host, and `--report` retains
the descriptive city/time analysis.  Lower bar = historically softer cutoff;
it is not a probability that a particular team medals.

**Shipped model.**  Prediction uses the 25 ordinary regionals from 2022–2025
only.  For each medal tier, city `c` with `n_c` observations is partially
pooled with one overall-mean pseudo-contest:

`pred(c) = (sum(city bars) + overall regular-regional mean) / (n_c + 1)`.

An unseen city receives the overall mean.  Gold, silver, and bronze are fitted
directly rather than imposing average gaps.  EC Finals are excluded from every
ordinary-city baseline (the old code mixed the 2023 Shanghai EC Final into the
Shanghai regional estimate and then added an EC-Final premium again).  A
requested EC Final uses the separate two-final mean.  Year, temporal order,
and field size are deliberately excluded from future recommendations: order
varies inconsistently by season, field size is uninformative, and extrapolating
the small year coefficient made the 2026 estimates artificially easy.

**Decision-metric validation.**  A rolling-origin check trains strictly on
earlier seasons and predicts the 19 regular regionals in 2023–2025.  The
shipped one-pseudo-contest city model achieves **131.7 CF RMSE**, **92.7 CF
MAE**, and **77.1% correct within-season pair ordering** (48 pairs).  The prior
raw-city + order/year formula, reevaluated after fixing the host label below,
gets 172.4 RMSE / 125.5 MAE / 66.7% pair ordering.  Each CLI interval is
explicitly labelled a historical RMSE band, not a 68% confidence or medal
probability.

**2026 choice.**  [ICPC Global](https://icpc.global/regionals/results) listed
Chengdu, Hong Kong, Nanchang, Nanjing, Shanghai, Shenyang, Wuhan, and Xi'an as
the ordinary 2026 Asia East sites on 2026-07-27.  Dates/order were still blank;
online rounds and the EC Final are
not selectable ordinary medal regionals and are excluded.  For gold, the point
leaders are Shenyang 2458, Hong Kong 2465, and Nanjing 2473 CF, but their gaps
are tiny relative to the 132-CF forward error and every candidate's band
overlaps.  The output therefore presents a ranking plus evidence counts and
warns that travel/cost, school quotas, eligibility, registration limits, and
this year's applicant strength remain outside the model.  The candidate list
is source-dated in code instead of silently assuming unpublished dates.

**QOJ archive audit (not shipped).**  The user identified QOJ's 2015–2021 Asia
East category archive as a possible way to add signal.  The 2015–2016 regional
mirrors are incomplete (zero official teams and only 2–11 practice rows), so
they are unusable.  The 18 ordinary 2017–2019 mirrors are complete five-hour
standings, and for every 2017–2021 stored regional QOJ's server-side
official-only set equals the `$DEFAULT...` team-id set exactly; no
official-field guess is needed.  Nevertheless, adding the 6.8 MB 2017–2019
solve data is neutral/slightly worse on the global fit (calibrated LOCO 261.6
→ 261.8 CF, all guards pass), and using all 2017–2021 medal bars worsens the
same 2023–2025 decision holdout to **160.9 CF RMSE / 51.0% pair ordering**.
Older Nanjing/Shanghai fields do not transfer well enough to the recent regime,
so neither the archive data nor its bars are added merely to increase sample
size.

**Host correction.**  QOJ category 460 names contest 1099 “The 2022 ICPC Asia
Hong Kong Regional Contest,” while the medal artifact's shortened contest name
is “Hong Kong & Macau.”  The old substring loop encountered `Macau` first and
misclassified it.  `CONTEST_CITY` now maps 1099 explicitly to Hong Kong; a test
locks the source-backed correction.

Run: `./.venv/bin/python -m arch_b.medal_predict`.  The older interactive
`output/medal_predict_viz.html` remains a descriptive city/time view; it is not
the 2026 recommendation interface.

### XCPCIO ← QOJ matching

XCPCIO board data (`https://board.xcpcio.com`) hosts the official ICPC scoreboard
for East Asia regionals.  ``scripts/build_xcpcio_official.py`` fetches
``team.json`` for each matched contest and caches normalized official-team
identity keys in ``data/xcpcio_ea_official.json`` (28 contests, 2022–2025
regionals + EC-Finals — seasons 47th–50th).  Teams are matched to QOJ standing
rows by set-intersection of candidate keys: bare name, org-name pairs with
``-`` / ``: `` separators, parenthetical-stripped variants (XCPCIO bilingual
orgs like `北京航空航天大学(Beihang University)` → stripped to Chinese-only),
and member-stripped ``display_name_raw`` prefixes (QOJ domjudge rows append
`` - member1, member2, ...``).

**Coverage.**  28 of 30 EA medal contests are matched (the 6 online ``"ICPC"``
qualifiers and EC-Final warm-ups are excluded by scope, not by matching failure).
Two EA contests have no XCPCIO entry: Grand Prix of China (QOJ 3295) and
Metropolis (QOJ 1913).  Matching quality is generally high (80–100% of XCPCIO
teams found in QOJ); two contests have low match rates due to naming
differences: Xi'an 2023 (~10%, bilingual org names) and Xi'an 2025 (~50%, i18n
name dicts).  For older seasons (47th–48th) XCPCIO team data lacks per-team
``"group": ["official"]`` tags, so the entire XCPCIO team list is treated as
the official field; this is validated by comparing XCPCIO team counts against
QOJ domjudge-id row counts (they match exactly).

### Official-field validation of fitted difficulties

The fitted survival-model difficulties are validated against **XCPCIO
official-field solve rates** — the subset of teams actually competing for medals.
This is an independent check: XCPCIO data was not used in the fit.

**Per-contest Spearman(difficulty, official solve rate): median −0.962**
over the 28 contests (range −0.657 to −1.000).  The equivalent full-field
correlation is median −0.978 — the official-field agreement is slightly
looser because the official field is smaller (median 335 vs 809 teams),
but the 0.016 gap is noise-level.  Overall Spearman over all 358 rated EA
problems: −0.940 (official) vs −0.972 (full field).  The model predicts
official solve rates nearly as well as full-field rates.

**Where unofficial teams distort the signal.**  20 of 358 problems (5.6%)
have a solve-rate gap ≥ 0.15 between officials and unofficials.  Direction
is inconsistent: on some contests unofficial star teams (often stronger,
e.g. UCup squads) find hard problems easier; on others (e.g. Hong Kong &
Macau 2022) the unofficial field is *weaker* and finds easy problems harder.
Both directions are local noise, not systematic bias.  The two outlier
contests in per-contest correlation are Xi'an 2023 (ρ = −0.657, only 36
official teams matched) and Grand Prix of Hong Kong 2025 (ρ = −0.804,
126 officials) — both have very small official fields where a handful of
solves determines the rate.

**Why not fit on official-only.**  Restricting the fit to XCPCIE-identified
official teams would discard 54% of EA solving rows (9,568 of 20,635) and
55% of cross-contest linking edges (162 of 364).  The unofficial entries
(UCup teams and rosters competing unofficially in regional mirrors) are the
cross-contest bridges that put every contest on one scale — the same
mechanism documented in the main unofficial-participants decision above.
Weighted approaches (downweighting unofficial observations) were also tested
and found decisively harmful (+17 RMSE; see the contest-link weighting
experiment).  The current strategy — all teams for fitting, XCPCIO for medal
cutoffs — is the correct split.

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
the shipped two-leg map's **calibrated leave-one-contest-out RMSE in CF
points**. The verifier refits the model, applies the locked gym-learned monotone
shape (`NBINS=15`, `ALPHA=0.75`, qoj 2692 excluded), then for each CF-rated
mirror contest fits the affine leg on the *other* mirrors, predicts the held-out
one, and pools the errors. This measures the shipped deliverable
(`difficulty_cf`) directly while preventing the loop from retuning calibration
against the same anchors. `metric.py` auto-maps
**all** rated mirrors in `data/cf_team_contests.txt` via the
`external_validate` name-vote machinery: currently **185 problems / 15
contests**. Three mirrors were *added to the list* by sweeping every tagged
contest's problem names against the rated CF problemset (contest-level vote):
CF 2157 ↔ qoj 2692 (found by the gym certification), plus CF 1773 (2022–23
NEF) and CF 1938 (2024 APAC) found by the exhaustive sweep — which also showed
**no further rated mirrors exist** for our 146 contests, so anchor growth now
requires new contests in the fit. After the 2026-07-23 data-expansion campaign
below, the current calibrated survival baseline is **261.6**; raw affine LOCO is
**285.0** and remains a guard with ceiling 293.4.

**Noise floor (cluster bootstrap, contests as resampling units):** for the
legacy raw-affine metric, pooled RMSE carried **SE ≈ ±20 points** (95% CI ≈
[251, 327]); the calibrated metric's own sampling SE has not been separately
estimated. Paired comparisons on the same anchors are sharper, but an
auto-research loop must still **treat single-digit improvements as noise**
(`program.md` sets a ~5-point keep threshold, requiring Kattis, AOJ, or
held-out-AUC corroboration for small wins) because repeatedly selecting on a
fixed 185-anchor set overfits it in a way LOCO cannot detect.

**Guards.** The CF anchors cover only AsiaPac / N.Eurasia / Europe, so a loop
optimizing RMSE alone could silently regress the unanchored regions. The same
fit is therefore checked against floors (baseline − noise margin, calibrated to
the survival model): gym **EC** Spearman ≥ 0.93 (the region with *no* CF
anchors), gym pooled ≥ 0.92, Kattis pooled (NA+Europe convention) ≥ 0.75, AOJ
within-contest Spearman ≥ 0.52, and within-contest solve-count sanity ≥ 0.90.
Raw affine LOCO must remain ≤ 293.4 so the nonlinear calibration cannot hide a
material fit regression. Any violation exits nonzero = "discard the change".
Note Asia West needs no exclusion switch: it has no anchor coverage, so it
simply never enters the metric (dropping its contests *from the fit* is
explicitly permitted as an experiment in `program.md`).

**`program.md`** (repo root) is the instruction file for auto-research agents
(karpathy-style `verify`/guard loop): the verify contract (last line
`METRIC calibrated_loco_cf_rmse=…`, exit 1 = discard, ~5 s deterministic
runs), the scope
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
the identity fixes above). **0 fit-side iterations kept; the WF identity
linking was kept as a correctness change** — the model is confirmed at a
robust local optimum.

**Gym-informed difficulty prior: kept, then reverted on review.** The
campaign's iteration 1 soft-anchored ~667 problem difficulties toward
`output/gym_difficulty.json` (N(b_gym, 400²) prior mean; commit `80afc92`,
implemented post-campaign — review found the original "KEPT" log entry had
never actually been committed). Metric 288.4 → 288.0 (−0.4, far under the
±5 noise floor), so the keep leaned on guard corroboration — but the
corroborating guards (gym EC +0.962 → +0.969, gym pooled +0.954 → +0.959)
are **circular** for this change: pulling `b` toward `b_gym` mechanically
raises Spearman against `b_gym`. The genuinely independent signals did not
corroborate (held-out AUC flat at 0.8858; Kattis pooled *down* 0.795 →
0.790), the change carried a mild target leak (qoj 2692 is both
gym-covered and a CF anchor contest, where `b_gym` correlates +0.976 with
the official CF ratings), and it had a structural cost: with `b_gym` baked
into the fit prior, the gym guards stop being an independent watchdog for
the unanchored regions. Reverted (`3fb0eca`). The principled home for the
gym signal is the calibration layer (per-region CF map on `b_gym` anchors)
or the likelihood via merged gym *observations*, not a prior on `b`.
Campaign-log caveat: several phase-3 TSV sweep rows compare against 286.3
— a *discarded* σ_θ=500 config — rather than the 288.0 incumbent, so those
deltas are not baseline-relative.

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

### Gym-merge experiment (2026-07-04): gym attempts as fit observations — NEGATIVE

The natural follow-up to the reverted gym *prior*: merge the gym-mirror
attempts into the main fit as **likelihood terms** instead — the strat's
original CF anchor (eq. cfprior) realized on the only population with known
CF ratings. `arch_b/gym_merge.py` turns `load_gym()` into fixed-θ Bernoulli
observations (θ = `team_theta` lse reduction, trust-weighted) joined to the
tagged problem indices; `model.fit` / `survival.fit` accept them via
`gym_obs=` and accumulate them in the `b` Newton block only (mixed
binary+survival likelihood, still concave; gym attempts carry no per-problem
times). qoj 2692 — verified as the *only* overlap between the 56 usable gym
contests and the 15 CF-anchor contests — is always excluded (its `b_gym`
correlates +0.976 with the metric target there: a leak). A global weight λ
balances the large gym fields (277k attempts on 688 problems) against the
onsite signal.

**Result: discard at every weight.** The metric moves sub-noise while both
genuinely independent checks degrade monotonically with λ:

| λ    | loco_cf_rmse | Kattis pooled | held-out AUC |
|------|--------------|---------------|--------------|
| 0 (baseline) | 288.4 | 0.795         | 0.8851       |
| 0.1  | 287.2        | 0.773         | —            |
| 0.3  | 286.9        | 0.755         | **0.8771**   |
| 1.0  | 288.8        | 0.736 (guard FAIL) | —       |

(The gym EC/pooled guards *rise* with λ — 0.962 → 0.985 at λ=1 — but they are
circular for this change, same source data, and were ignored for the verdict.)
This quantitatively confirms the certification's warning: the gym population
is authoritative on **scale** but noisier than our own survival fit at
fine-grained **ranking** (virtual-participation effects), so injecting it into
the likelihood trades our sharper ordering for its scale — and the LOCO metric,
whose per-fold affine map absorbs scale anyway, can't reward the trade. Same
verdict as the prior-form (80afc92, reverted): the gym signal's home is the
**calibration layer** (per-region CF map on `b_gym` anchors), not the fit.
The machinery stays as an opt-in (`estimate_anchored(gym_merge=λ)` or
`ARCHB_GYM_MERGE=λ`, default off — verified byte-identical baseline when off);
log in `autoresearch/autoresearch-260704-0110/classic-results.tsv`.

### Contest-link weighting experiment (2026-07-04): NEGATIVE

Can the contest-linking graph be *weighted* to improve normalization? In the
IRT fit there is no explicit edge weight — linking is emergent through shared
`theta_t` — so "link weight" can only be parametrized indirectly. The global
and per-team versions were already tested in the campaigns (σ_θ sweeps,
evidence-scaled per-team priors, evidence-scaled anchor weight, per-contest
hazard intercepts — all discarded). The two remaining parametrizations are
per-*observation* weights, now supported by both fitters via ``obs_w=``
(default off, baseline byte-identical) and tested on the exact metric+guards
harness:

| variant | rmse | guards |
|---------|------|--------|
| baseline (unweighted) | 288.4 | kattis 0.795 |
| A: arch-A-style reliability `w_t = 1−0.9^N_t` per obs | **305.5** | kattis 0.792 |
| B: thick-bridge contests (>1000 rows: 5 EC qualifiers + Shenyang/Metropolis/Xi'an) ×0.25 / ×0.5 / ×2.0 | 288.3–288.4 | unchanged |

**A is decisively harmful (+17):** one-off teams' observations carry essential
within-contest difficulty evidence, and the Bayesian machinery already
discounts their unreliable *ability* via the θ prior — arch A's `w_t` hack done
properly. Downweighting their observations discounts twice and starves `b`.
**B is perfectly flat in both directions:** the CF anchors don't cover EC (the
qualifiers' linking load), and even the gym EC guard doesn't move, so the
thick bridges are neither a noise source nor an untapped lever. Verdict:
evidence weighting inside the likelihood is a solved problem in the MAP model;
the linking graph is not a knob. Log:
`autoresearch/autoresearch-260704-0130/classic-results.tsv`.

### Data-side auto-research campaign (2026-07-23): 261.6 LOCO

A 46-iteration campaign focused on standings and identity data after earlier
model-side searches had plateaued. **3 changes were kept, 43 discarded.** The
calibrated metric improves **266.4 → 261.6** (−4.8 CF points), while raw affine
LOCO improves **288.4 → 285.0** and every guard passes. Full log:
`autoresearch/loop-260723-1333/classic-results.tsv`.

The first keep fixes `_link_wf_top_team`: the purported WF-only,
season-matched affiliation join was actually touching thousands of regional
no-roster rows and ignoring season when the main identity key was
season-agnostic. Restricting it to World Finals and separating competition
season from identity-token season improves calibrated LOCO **266.4 → 264.5**;
Kattis also rises 0.795 → 0.796 and held-out AUC stays 0.8858.

The other two keeps add standings-only QOJ data: 14 Asia East ICPC contests from
2020–2021 and 57 Petrozavodsk camp contests from 2022–2026. Together they add
18,181 rows and 850 problems, improving **264.5 → 261.6**. A held-out transfer
test scored the same original `tagged.json` cells with and without all 71
supplemental contests: log-loss **0.312411 → 0.311973**, Brier
**0.097557 → 0.097385**, and AUC **0.885761 → 0.886000**. This corroborates
that the new standings improve linked team abilities rather than merely fitting
the 185 CF anchor problems. Collection used only QOJ category/dashboard labels
and unofficial standings; statements, editorials, and solutions were never
requested.

Notable discards: a conservative full-roster CF prior using only ratings known
before January 1 of each contest year moved LOCO just −0.1; live QOJ refresh
added 482 later virtual-replay rows and moved −1.0 without independent
corroboration; removing account-like replay rows was decisively harmful
(LOCO 282.8, raw guard 306.6, Kattis guard 0.707); zero-solve inclusion, stricter
identity links, duration thresholds, Asia West exclusion, and qualifier removal
were neutral or worse. A refreshed cookie made the standings audit possible,
but QOJ's historical dashboard exposes no exact start timestamp, so the
participant-prior experiment stayed on the conservative January 1 cutoff.

The continuation tested every other QOJ training-camp family separately:
ByteDance/Moscow Workshops, JAG, ICPCCamp, Moscow International Workshops,
Moscow Pre-Finals, HDU multi-university training, Osijek, and 130 older
Petrozavodsk entries. After contest-id deduplication this was 196 unique
contests (192 with standing rows). No family cleared the 5-point threshold.
The best narrow combination, HDU + pre-finals, moved LOCO only
**261.6 → 261.0** and failed the independent original-cell holdout:
log-loss **0.312698 → 0.313261** and AUC **0.885327 → 0.884989**.
Combining all camp families was harmful (**264.0**, gym pooled 0.953,
solve-count sanity 0.951). `scripts/fetch_qoj_supplemental.py` reproduces these
standings-only collections from a QOJ category while skipping already-loaded
contest ids; it never requests statements, editorials, submissions, or
solutions.

XCPCIO was also tested as a direct fit source rather than only as the official
team-label source used by the medal analysis. Its hosted `config.json`,
`team.json`, `organizations.json`, and `run.json` provide exact duration,
official groups, member rosters, and run timestamps. The resumable
`scripts/fetch_xcpcio_standings.py` converts those files to the project schema,
handles second/millisecond/minute timestamp declarations, and assigns stable
negative ids so they cannot collide with QOJ contests. A 2022–2026 sample
covered **56 provincial contests / 14,134 rows** (13,258 explicitly official;
8,188 with rosters). Individual years were neutral except 2023 (261.9);
combining all years regressed **261.6 → 262.5**, including when restricted to
official teams, and the Asia-East gym guard slipped 0.961 → 0.960. Five
official 9th CCPC boards were neutral (261.6). Existing XCPCIO East Asia
regionals were not re-imported because those same contests are already loaded
from QOJ and XCPCIO already supplies their official-team labels. The direct
XCPCIO datasets therefore remain discarded experiments, not shipped fit input.

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

### Participant Codeforces ratings: feasibility study (2026-07-21)

A live test confirmed that **some** standing members can be mapped to
Codeforces, but the bottleneck is identity rather than rating retrieval.  The
official Codeforces `user.ratedList` snapshot contained 958,447 rated accounts.
Exact normalized full-name matching against `data/tagged.json` found one distinct
handle for **1,168 of 25,656 unique member names (4.6%)** and for 4,839 of 65,588
member appearances (7.4%); 302 additional names were ambiguous.  At team level,
3,241 of 24,709 rows with rosters (13.1%) had at least one unique match, but only
560 (2.3%) had every member matched.  This is a useful sparse anchor set, not a
complete participant-rating layer.

**Source decision:** Codeforces is authoritative once a handle is known:
`user.info` supplies current records and `user.rating` supplies the history needed
to select the last rating known before each ICPC contest.  CLIST unified coder
profiles are useful secondary evidence for account identity, but the v4 account
API is handle/resource-oriented and cannot bulk-resolve arbitrary real names.
Neither current rating nor `maxRating` is valid for an old contest.

**Fit direction:** add trusted, time-accurate CF data as a confidence-weighted
prior on **team ability `theta`**, not as a prior on problem difficulty.  Start
with fully resolved rosters only and reduce member ratings with the same `lse`
team rule used by `arch_b.gym_difficulty`; ignoring an unmatched member would
bias partial rosters downward.  Architecture B should accept per-team prior
precision so verified veterans pull more strongly than weak/name-only matches;
the Gaussian MAP remains strictly concave.  This should improve cold starts,
weakly linked contest normalization, and 0–1-solver problems by identifying the
actual strength of their field.

Validation must use historical ratings only, treat the gym column as circular
(it also uses CF user ratings), and require corroboration from held-out solve
prediction and Kattis.  A CF-prior team holdout should test whether the scale
transfers through the contest graph.  Full methodology, examples, equations,
risks, and implementation order are in
[`cf_participant_ratings.md`](cf_participant_ratings.md).

**Source layer implemented 2026-07-23.**  The reproducible
`scripts/cphof_cf_participants.py` collector now caches CPHoF's 2021–2025 World
Finals standings and relevant profile pages, follows only explicit CPHoF
Codeforces profile links, and fetches complete histories from the official
Codeforces `user.rating` API.  Raw responses live in the resumable, gitignored
`data/cphof_cache/`; the provenance-rich
`data/cphof_cf_participants.json` artifact is committed.

The current snapshot has 415 exact-name CPHoF candidates, 346 explicit
person→handle identities with available API histories, and 285 people whose
appearance in `tagged.json` is corroborated by at least one additional matching
roster member.  Those conservative links cover 1,582 standing-member
appearances; 347 unique standing rows have explicit handles for every roster
member.  Another 537 name-only appearances remain review candidates and do not
count as trusted links.  Nine stale CPHoF handles fail the official API and are
retained as rejected evidence rather than repaired by guessing.

The artifact stores 29,425 rating changes and computes 470 historical ratings
before the CPHoF World Finals calendar dates.  CPHoF does not publish a start
time on those pages, so the collector uses 00:00 UTC at the start of each date:
a conservative cutoff that excludes same-date changes rather than risk
look-ahead.  It deliberately does not derive regional priors:
`tagged.json` provides only `year`, not the exact contest start timestamp
required to choose a non-leaking historical rating.
Fit-side per-team precision, full-roster `lse` reduction, and regional date
collection therefore remain follow-ups.

### External data-source audit (2026-07-21)

**Implemented 2026-07-23:** AOJ is now a reproducible validation-only dataset
and metric guard (45 accepted problems across four Japan regionals; survival
within-contest Spearman +0.576).  The CPHoF→Codeforces identity/history source
layer described above is also implemented; fit-side participant priors remain
deferred because exact regional timestamps and per-team prior precision are
still missing.  CP-Ranking alone remains insufficient because it lacks the
member-level histories needed to use its 22 identity seeds without leakage.

A broader live-source audit identified three concrete additions beyond the
initial CLIST/XCPCIO pass.  First, CPHoF World Finals rosters and external-profile
links provide a higher-confidence real-name→handle bridge: its 2021–2025 ICPC
pages yielded 426 unique exact-name candidates in the current standings, covering
2,485 member appearances before roster/institution verification.  The prepared
CP-Ranking data gives a smaller immediately conservative seed—22 exact
year+institution+team identities appearing in 57 standing rows—but an
institution-only join is invalid because it would assign one finalist roster's
rating to unrelated teams from the same university.

Second, public ICPC Contest API / DOMjudge endpoints can provide the true contest
duration, stable team/person IDs, and submission/judgement event history.  True
duration directly closes the `T_c = latest solve` approximation; event feeds
could later distinguish no-attempt cells from failed-attempt histories.  Endpoint
access is contest-specific and must be measured rather than assumed.

Third, AOJ is now a permanent independent difficulty guard. The reproducible
collector found 71 unique exact-title candidates and accepts 45 of 46 Japan
Regional problems from 2022–2025; the other 26 candidates are retained with a
rejection reason because fewer than three titles corroborate their contest.
Current within-contest Spearman is +0.587 (Architecture A), +0.650 (binary), and
+0.576 (survival). The north-star metric floors the survival AOJ guard at +0.52.
AtCoder Problems produced no unique exact matches and is lower priority;
solved.ac remains promising but should be cached because its BOJ integration
ended in 2026. Source URLs, matching policy, leakage rules, measurements, and
the staged experiment order are documented in
[`external_data_sources.md`](external_data_sources.md).

## Out of scope / follow-ups

- **2PL discrimination** `a_p` (strat §4) on top of the Rasch fit in `arch_b`
  (**prototyped — overfits, see the 2PL section above; not shipped**),
  plus a calibrated joint posterior (full-Hessian Laplace / MCMC / VI) beyond the
  per-parameter Laplace SE already emitted as `difficulty_se`.
- **Per-contest `T_c` from real durations** — the survival model infers `T_c` as
  the latest solve time (a slight underestimate); public ICPC Contest API /
  DOMjudge metadata is now the preferred source for a true duration field (see
  `external_data_sources.md`).
- **Member-level identity** and entity resolution across sources (strat
  Remarks), to densify linking and handle roster changes.  CPHoF external-profile
  links are the first high-confidence bridge to harvest; CLIST remains secondary
  corroboration (see `external_data_sources.md`).
- **Time-varying ability** `theta_{team,season}` with a season-to-season smoothing
  prior — keeping **one** identity (unlike the hard `season_key` split, which was
  tried and slightly hurt difficulty, see above) but letting ability drift, so a
  recurring roster neither collapses to one blended value nor loses data to a split.
  A dedicated team-performance prediction eval (not just difficulty) is the right
  way to measure its benefit.
- ~~**Richer CF calibration.**~~ **Done (2026-07-04)** — `arch_b.calibrate` now
  ships the gym-shaped two-leg map on all 185 auto-mapped anchors (LOCO 288 →
  266, see the calibration section). Per-region maps were tried and overfit
  (298); the 1-solver hard-end *ordering* remains data-limited (the shape
  improves the tail's scale, RMSE 477 → 434, but cannot reorder 0–1-solver
  problems).
- **No external anchor for Asia West Continent.** ~~Asia East Continent~~ — **closed**:
  the gym-mirror yardstick (`arch_b.gym_difficulty`) now anchors EC at +0.95–0.98
  for all three models. Asia *West* remains uncovered (its one scraped gym, the
  Iranian contest, was a wrong-event match — see the gym section).
- ~~**Use `b_gym` as calibration anchors.**~~ **Done (2026-07-04)** — the
  gym-learned shape leg in `arch_b.calibrate` (see the calibration section) is
  exactly this, and it is the one use of the gym signal that survived
  validation. The two *in-fit* uses tested **negative**: per-problem prior
  means (80afc92, reverted — circular guard corroboration, Kattis down) and
  merged fixed-θ likelihood terms (`gym_merge` — Kattis and held-out AUC
  degrade monotonically with weight). Scale-half of the signal: used; noisy
  ranking-half: discarded, by construction of the monotone map.
- ~~**Add CF 2157 to `data/cf_team_contests.txt`.**~~ **Done** — the CF columns
  and the metric anchor set now include it (CF pooled n 152 → 160).
- **CF participant anchoring — source data collected, fit integration not
  implemented.**  The CPHoF/official-API artifact supplies 346 explicit
  identities and 347 roster-complete standing rows, while name-only matches
  remain excluded.  The proposed first fit experiment still needs exact target
  contest timestamps and per-team prior precision; see
  [`cf_participant_ratings.md`](cf_participant_ratings.md) and the feasibility
  section above.
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

## Codeforces pairwise Gemini pilot (2026-08-05)

This experiment is intentionally separate from the standings fit. Codeforces
ratings supply the supervised truth because the deployed operation is itself a
binary comparison. Training directly on rating classes would add an unnecessary
absolute-calibration problem, while Vertex managed SFT does not expose a custom
pairwise loss. Each JSONL target is therefore only `{"harder":"A"}` or
`{"harder":"B"}`.

Key leakage and evaluation decisions:

- Google's Gemini 3.5 Flash knowledge cutoff is documented only as January
  2025, so 2025-02-01 is the first unambiguously post-cutoff date.
- The newest 600 usable, exact-statement-deduplicated pre-cutoff problems form
  the stage-two pool. The first pilot stratifies 200 of them by rating and draws
  400 comparisons: 25% exact-200, 35% exact-300, and 40% at least 400 points,
  with A/B truth balanced.
- February–March 2025 supplies tuning validation and the zero-shot baseline.
  April 1–May 21 supplies 96 problems in a frozen final test. Final-test
  statements and labels are never uploaded with the tuning job.
- Every baseline unordered pair is sent in both orientations. This measures
  order bias as well as accuracy. The final small Flash prefix contains 200
  requests; the Pro sanity check contains 20 requests and is not powered for a
  close model comparison.
- Tuning uses two epochs and automatic adapter selection. The tokenizer gate
  rejected the original 500-pair plan ($16.38 training and $26.38 including the
  reserve) and accepted 400 pairs ($12.99 training, $22.99 planned total).
  This preserves the two-epoch pilot while staying below the local $25 cap and
  well below the user's $100 ceiling.

Collection found 600/600 usable pre-cutoff statements and 227/248 usable rated
post-cutoff statements. Missing statement pages remain missing rather than being
filled from guessed or weak sources. The resulting partitions are 600 train
problems across 82 contests, 131 validation problems across 21 contests, and 96
test problems across 15 contests.

The frozen zero-shot results are: Gemini 3.5 Flash with minimal thinking, 69.0%
overall, 41.3% at exact 200, 55.8% at exact 300, 77.3% at gaps of at least 300,
88.2% at gaps of at least 400, and 84.0% swapped-order consistency; Gemini 3.1
Pro Preview with low thinking, 80.0% overall and 100% order consistency on only
20 requests. Capacity returned repeated 429s, so resumable checkpoints were
served across global, US, and EU endpoints; each prediction records its request
location. The Flash alias, prompt, temperature, schema, and thinking level were
unchanged.

Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/2518784060365471744`
was submitted with 400 training examples, 150 validation examples, and two
epochs. It completed successfully on 2026-08-05 and produced tuned endpoint
`projects/703166210069/locations/us/endpoints/432767776692633600`.

The 2026-08-06 tuned evaluation reused all 200 frozen ordered validation
requests. All calls returned valid predictions. Tuned accuracy was 70.0%
overall, 37.0% at exact gap 200, 65.4% at exact gap 300, 79.9% at gaps of at
least 300, 87.3% at gaps of at least 400, and 94.0% swapped-order consistency.
Against the paired base results this is +1.0, -4.3, +9.6, +2.6, -1.0, and +10.0
percentage points respectively. Across all requests, tuning corrected 12 base
errors but changed 10 base successes to errors; at exact gap 300 those counts
were 8 and 3. Exact paired tests are not significant (all requests p=0.832;
gap 300 p=0.227), and the two orientations of each unordered problem pair are
correlated. Phase 1 therefore shows a promising 300-gap and order-consistency
signal, not a confirmed generalization gain. The tuned run used 319,416 prompt
tokens and 1,200 output tokens, estimated at $0.808 at the tuned non-global
rate. Estimated training plus both base and tuned validation inference is
$14.35. The untouched final test remains unevaluated.

### Phase 2 statement-plus-editorial preparation (2026-08-06)

Phase 2 is a fresh-base-model experiment, not continuation tuning. Each side
of a comparison will contain `[Statement]`, `[Editorial]`, and optionally the
first scoped author reference-solution block. The intended comparison is
statement-only base versus editorial-only base versus editorial-tuned, with the
code variant admitted only after its exact token preflight. Titles, ratings,
tags, contest identifiers, and problem indices remain excluded from model
input. A new preparation command uses 400 quota-balanced pairs while ensuring
every selected training problem appears at least once. Its tuning-validation
and development sets are contest-disjoint; the final test is not enriched,
uploaded, or evaluated.

The integration captured 623/731 non-empty tutorials and 469/731 code-bearing
records for the original training-plus-validation pool. That count was not
accepted as evidence of usable editorials. A random manual audit of
`1975E`, `1986C`, `1989E`, `1991A`, `1999C`, `2002G`, `2032F`, `2072A`,
`2077E`, and `2081B` checked each statement against its saved Codeforces
problem and tutorial URLs. All ten tutorial headings/entities matched the
correct task; six contained substantive task-specific prose (`1975E`, `2002G`,
`2032F`, `2072A`, `2077E`, `2081B`). The other four (`1986C`, `1989E`,
`1991A`, `1999C`) were title-only or video-only captures and are excluded.

Accordingly, a tutorial is now substantive only when it has at least 200
characters after whitespace normalization and is not a video-editorial marker.
Under that rule the original split has 423/600 substantive training records and
112/131 substantive validation records. We collected 150 older exact-statement
candidates (750 pre-cutoff statement candidates total), completed their
resumable enrichment, and deduplicated exact statements again. The user
explicitly accepted the resulting 561 substantive pre-cutoff problems rather
than requiring 600. All 561 occur in the 400 quota-balanced training pairs;
458 have an extracted first author-solution block. The 75 tuning-validation
pairs and 100 swapped-order development requests are contest-disjoint.

Three independent 10-record manual audits then checked saved statement text,
tutorial text, task identifiers, and saved Codeforces problem/tutorial URLs.
All 30 were task-matched and substantive; no title/video-only capture or
cross-problem contamination was found. Live Codeforces verification remains
Cloudflare-blocked, so this is a source-metadata and content identity audit,
not a fresh-page fetch.

Exact global `countTokens` preflights on the same 400 training pairs returned
1,043,341 tokens/epoch and $20.86682 for two editorial-only epochs, versus
1,390,192 tokens/epoch and $27.80384 with code. On the clean 100-request
development ablation, base Flash with editorial-only input was 80.0% overall,
70.0% at gap 200, 72.5% at gap 300, and 76.0% order-consistent. Adding code was
77.0%, 70.0%, 65.0%, and 82.0% respectively. Code therefore added cost and
hurt the target 300-gap metric, so the submitted Phase 2 training data is
editorial-only. Actual ablation usage was 269,318 input/1,200 output tokens
for editorial-only ($0.456 estimated) and 341,994/1,200 for code
($0.576 estimated at the base rate).

The verified Cloud Storage uploads are
`gs://gctc-vertex-batch-703166210069/cf-pairwise-20260805/phase2-editorial-v1/phase2_editorial_train.jsonl`
(3,530,316 bytes) and `phase2_editorial_validation.jsonl` (754,934 bytes).
Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/3895319841782890496`
was submitted with two epochs on 2026-08-06 and completed successfully. Its
endpoint is
`projects/703166210069/locations/us/endpoints/8084383543595106304`.

The tuned editorial endpoint was evaluated on the identical 100 clean
development requests: 84.0% overall, 73.3% at exact gap 200, 80.0% at exact
gap 300, 88.6% at gaps of at least 300, 100.0% at gaps of at least 400, and
84.0% swapped-order consistency. Relative to editorial-only base, these are
increases of 4.0, 3.3, 7.5, 4.3, 0.0, and 8.0 percentage points. Tuning corrected
eight base errors while losing four base successes; at gap 300 those counts
were four and one. Exact paired tests are not significant (overall p=0.388;
gap 300 p=0.727), and swapped orientations are correlated, so this is a
positive development signal rather than a final generalization claim. The
tuned evaluation used 269,318 prompt and 600 output tokens, estimated at
$0.675. The $15 evaluation reserve makes the Phase 2 planned total $35.86682
before the already-observed $1.032 base ablation, still below the overall $100
envelope. The final test remains unenriched, unuploaded, and unevaluated.

An additional paired close-gap check used 10 new unordered validation pairs
(five at a 200-point gap and five at 300), sent in both orientations to both
models. On these 20 new requests, Flash scored 12/20 (60%) and Pro 11/20 (55%):
both were 4/10 at gap 200, while Flash was 8/10 and Pro 7/10 at gap 300. Combining
these with the earlier paired close-gap requests gives 28 matched ordered
comparisons: both models are 6/14 (42.9%) at gap 200; Flash is 12/14 (85.7%) and
Pro 9/14 (64.3%) at gap 300. This is still only 14 unordered problems represented
twice, and order consistency on the new close-gap subset was 60% for Flash and
70% for Pro, so the apparent 300-gap advantage remains a pilot signal rather
than a reliable model-ranking claim.
