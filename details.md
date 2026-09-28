# Details

**Current review (2026-09-05):** [experiment_review.md](experiment_review.md)
audits the implementation and historical conclusions at `8a351e0`. In particular,
the cross-contest LLM LOCO improvement recorded below uses held-out CF labels and
is invalid as generalization evidence. Historical results remain for provenance;
the review and the 2026-09-06 implementation resolution at the end of this file
supersede those claims.

**Jev feasibility review (2026-09-17; no API run):** TypeSafe AI's early-access
Jev is a typed decision model (`Choice`, `Score`, `Noul`), not a text generator.
Its cleanest experiment in this repository is a shadow implementation of the
already-frozen `llm_crosscontest` mirror protocol: ask which of two sanitized
statements is harder, retain both orientations, and fit probability-weighted
Bradley--Terry rather than discarding the returned distribution. This is a
cheap instrument test, not a production proposal; it must beat the existing
Gemini cross-contest baselines on pairwise accuracy, order consistency, global
BT correlation, and leak-free LOCO before expansion. Jev should not replace the
survival, DE/ridge, or calibration arithmetic: its own model notes warn about
numeric precision and multi-step reasoning. A secondary research use is to turn
sanitized statements into a small frozen set of semantic features (insight,
proof, implementation, and standard-technique burden) for the existing nested
contest-held-out residual harness. Identity/entity matching is suitable only
for audit triage, never automatic roster union. No request was sent, no output
artifact changed, and no implementation was added.

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

- **Treat omitted problem entries as censored non-solves (`load.solve_mask`).**
  QOJ omits a problem from a standing row when the team never attempted it. The
  loader now marks every problem belonging to the row's contest in
  `solve_mask`, leaving an omitted entry as `y=0` with right-censoring at the
  contest end. Before this fix, the model silently excluded no-attempt cells.
  The Shenyang 2023 audit made the error visible: QOJ reports B=148 and M=185
  solves, but the old likelihood saw only B=148/178 and M=185/233 among
  attempted cells (the official subset likewise has M ahead, 111 vs 84). With
  all 633 retained nonzero-solve teams included for both problems, the corrected
  survival fit rates raw B=2265 and M=2226; the shipped calibrated output is
  B=2577.4 and M=2479.7. A regression test covers the mask semantics in
  `tests/test_load.py`.

- **Do not retain rows using unknown problem labels (`load.row_solved_any`).**
  A few QOJ exports have standing labels that are absent from the parsed contest
  problem list. The loader cannot rate those problems without inventing their
  metadata, so a row is retained only when it solved at least one listed problem.
  Before this guard, Petroz contest 2575 listed only `M`, but 610 rows that solved
  only omitted labels were retained as censored non-solves of `M`. The fit now
  keeps the 44 rows that actually solved `M`; viewers use the same filter for
  performance-row alignment. A regression test covers this case.

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

- Converges in 8 iterations, monotone decreasing `max|dtheta|` < 0.5.
- `theta` ≈ [1372, 3698], mean ~2011 (zero-solve rows dropped + contests deduped).
- `b` ≈ [951, 4000], mean ~2230; boundary-smoothed (see decision), so
  solved-by-all problems clear the 800 floor and most solved-by-none spread below
  4000 (only at-ceiling and empty-contest problems remain pinned).
- Per-contest Spearman(difficulty, solve_count) median **−0.995** (harder
  problems were solved by fewer teams, as expected).
- Cross-contest normalization is now carried by the shared teams (see the
  evidence-weighted-prior decision): per-contest mean ability spreads to std≈110
  vs ≈3.7 with linking removed.

**2026-08-08 current fit after the full-cell mask correction:** Arch A is
`theta=[1372,3698]`, mean 2011, `b=[951,4000]`, mean 2226, with median
within-contest Spearman −0.995. Arch B uses 774,639 observations after adding
the censored no-attempt cells: binary `theta=[1117,3538]`, `b=[800,3759]`,
mean `b=2332`, and survival `theta=[1385,2915]`, `b=[1182,3251]`, mean
`b=2209`; their solve-count Spearman medians are −1.000 and −0.995.

### Caveat introduced by the stronger normalization

A full catalog of inflation/deflation mechanisms (by pipeline stage, with
measured directions) lives in `rating_bias.md`; the Nanjing 2022 audit that
prompted it is summarized in the bottom-line section there.

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
earlier seasons and predicts the 19 regular regionals in 2023–2025.  With the
corrected full-cell ratings, the shipped one-pseudo-contest city model achieves
**105.0 CF RMSE**, **86.5 CF MAE**, and **47.9% correct within-season pair
ordering** (48 pairs).  The RMSE is useful as a broad uncertainty scale, but
the pair ordering is weak in this snapshot, so the ranking is only a rough
shortlist. Each CLI interval is explicitly labelled a historical RMSE band,
not a 68% confidence or medal probability.

**2026 choice.**  [ICPC Global](https://icpc.global/regionals/results) listed
Chengdu, Hong Kong, Nanchang, Nanjing, Shanghai, Shenyang, Wuhan, and Xi'an as
the ordinary 2026 Asia East sites on 2026-07-27.  Dates/order were still blank;
online rounds and the EC Final are not selectable ordinary medal regionals and
are excluded.  For gold, the point leaders are Hong Kong 2506, Shanghai 2518,
and Shenyang 2526 CF; their gaps are tiny relative to the 105-CF forward error
and every candidate's band overlaps.  The output therefore presents a ranking
plus evidence counts and warns that travel/cost, school quotas, eligibility,
registration limits, and this year's applicant strength remain outside the
model.  The candidate list is source-dated in code instead of silently assuming
unpublished dates.

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
requires new contests in the fit. After the 2026-08-08 full-cell mask correction,
the current calibrated survival baseline is **244.2**; raw affine LOCO is
**245.2** and remains a guard with ceiling 293.4. The previous 261.6/285.0
figures were the pre-correction baseline, where omitted no-attempt cells were
excluded from the likelihood.

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
tags, contest identifiers, and problem indices are not interpolated from their
structured fields. The official tutorial is inserted verbatim, however; the
later high-thinking audit found that many tutorials contain their own identifier
and title header, so the effective prompt does not satisfy this intended
metadata exclusion (see the forensic follow-up below). A new preparation command
uses 400 quota-balanced pairs while ensuring every selected training problem
appears at least once. Its tuning-validation and development sets are
contest-disjoint; the final test is not enriched, uploaded, or evaluated.

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

### Phase 3: larger pairwise supervision (completed 2026-08-06)

Phase 3 is intentionally a fresh `gemini-3.5-flash` base-model run, not an
attempt to continue the Phase 2 endpoint. That isolates the change from 400 to
600 diverse comparisons instead of confounding additional data with repeated
epochs on the old 400-pair signal. It retains Phase 2's 561 substantive,
exact-statement-unique pre-cutoff problems, editorial-only prompt, two epochs,
75 tuning-validation pairs, and frozen 100-request development set.

The first 600-pair draft was sparse but had a degree range of 1--8. Before any
upload, the sampler was corrected to track pair-bucket allocation separately
from problem degree. The submitted set has no duplicate unordered pair, covers
all 561 problems, has degree distribution 26 once / 431 twice / 104 three
times (mean 2.14, max 3), and preserves 150 exact-200, 210 exact-300, and 240
at-least-400 gap pairs. The correction is regression-tested.

The corrected global `countTokens` preflight returned 1,608,024 tokens per
epoch and $32.16048 estimated training cost for two epochs ($47.16048 with the
$15 evaluation reserve). Verified uploads are in
`gs://gctc-vertex-batch-703166210069/cf-pairwise-20260805/phase3-editorial600-v1/`:
the train file is 5,438,197 bytes and the validation file 754,934 bytes. Vertex
job `projects/703166210069/locations/us-central1/tuningJobs/8563467981319831552`
completed successfully, as shown by the Vertex tuning monitor. The monitor's
training and tuning-validation curves do not show the usual visual signature of
overfitting: validation accuracy rises with training accuracy and validation
loss does not turn upward. This is not an independent generalization result,
however—the 75-pair validation set was used by the tuning job, and the curves
reach nearly perfect accuracy/near-zero loss. The final test remains
unenriched, unuploaded, and unevaluated at that point in the phase-completion
record; the authorized evaluation is recorded below.

The final evaluation was subsequently authorized after the development decision.
All 96 frozen final-test problems were editorial-enriched from the sibling
Codeforces scraper and verified against the manifest hashes. The test contains
500 unordered pairs in both orientations, for 1,000 ordered requests. The
input mode was editorial-only: each prompt contained the statement and official
tutorial, with no author solution code. Problem `2086A` had a short but genuine
official tutorial, so it was included under an explicit final-test exception
rather than silently falling back to statement-only input.

The base requests were completed by batch job
`projects/703166210069/locations/us/batchPredictionJobs/7631252811556061184`;
the tuned requests used endpoint
`projects/703166210069/locations/us/endpoints/4697676623812493312`. All 1,000
responses on each side parsed as valid `{"harder":"A"|"B"}` predictions.
The paired results were:

| Metric | Base | Tuned | Change |
|---|---:|---:|---:|
| Overall | 82.3% | **85.2%** | **+2.9 pp** |
| Exact gap 200 | 67.7% | 70.0% | +2.3 pp |
| Exact gap 300 | 77.0% | 82.3% | +5.3 pp |
| Gap at least 300 | 88.6% | 91.7% | +3.1 pp |
| Gap at least 400 | 97.3% | 98.8% | +1.3 pp |
| Swapped-order consistency | 77.8% | 89.2% | +11.4 pp |

Usage was 3,030,230 prompt and 12,000 output tokens for base, and 3,030,230
prompt and 6,000 output tokens for tuned (plus 15,870 cached-content tokens
reported by the tuned endpoint). At the evaluator's non-global list-rate
estimate, this was $5.118679 for base and $7.588919 for tuned. These are final
test results, not tuning-validation results. They support a positive Phase 3
result on the current unsanitized editorial input, while the forensic audit below
means they do not establish metadata-free intrinsic-difficulty generalization.

### High-thinking reasoning audit (2026-08-07)

To inspect whether additional reasoning changed the comparison, a deterministic
50-pair exploratory sample was drawn from the already-used final-test pool:
15 unordered pairs at gap 200, 15 at gap 300, and 20 at gaps at least 400.
Both orientations were evaluated, giving 100 requests per model. The prompt
remained editorial-only; `thinkingLevel=HIGH` and Vertex's
`thinkingConfig.includeThoughts=true` were enabled. The evaluator stores the
returned thought text with each prediction, while the final JSON decision is
parsed separately. Google's REST schema documents `includeThoughts` as the
switch that returns thoughts when available.

| Metric | Base | Tuned | Change |
|---|---:|---:|---:|
| Overall | 84.0% | 81.0% | -3.0 pp |
| Exact gap 200 | 60.0% | 70.0% | +10.0 pp |
| Exact gap 300 | 90.0% | 73.3% | -16.7 pp |
| Gap at least 300 | 94.3% | 85.7% | -8.6 pp |
| Gap at least 400 | 97.5% | 95.0% | -2.5 pp |
| Swapped-order consistency | 88.0% | 86.0% | -2.0 pp |

All 200 responses were valid. Thought text was returned on 98/100 requests for
each model. Usage was 321,452 prompt, 157,497 thought, and 1,185 output tokens
for base; tuned used 321,452 prompt, 168,434 thought, and 600 output tokens.
The evaluator's non-global list-rate estimates were $2.101348 and $3.305749,
respectively. Because this audit reuses final-test problems and has only 50
unordered pairs, it is diagnostic evidence rather than a replacement for the
1,000-request final result.

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

#### Forensic follow-up: reasoning behavior and prompt contamination

Joining the high-thinking audit back to the minimal-thinking final predictions
separates the sample effect from the reasoning setting:

| Same 50 unordered pairs / 100 requests | Base | Tuned | Tuning change |
|---|---:|---:|---:|
| Minimal thinking | 81.0% | 81.0% | 0.0 pp |
| High thinking | 84.0% | 81.0% | -3.0 pp |

At the unordered-pair cluster level, the high-thinking tuning change has an
approximate 95% interval of **-12.0 to +6.0 points**. High thinking changed
13/100 base decisions and 18/100 tuned decisions; it corrected eight and lost
five base decisions, while correcting and losing nine tuned decisions. It cost
$2.101348 base and $3.305749 tuned, versus $0.542276 and $0.804504 under minimal
thinking on the same requests (**3.9x / 4.1x**). Incorrect high-thinking answers
were also much longer on average than correct ones (base 2,355 vs 1,426 thought
tokens; tuned 2,498 vs 1,494). These are diagnostic associations on a small
sample, not evidence that length causes errors, but they show no return from the
extra reasoning budget. The large minimal-thinking final comparison remains
+2.9 points (an approximate paired-pair 95% interval of **+0.9 to +4.9**) with
the much stronger 77.8% to 89.2% order-consistency gain.

The trace audit also found a contract violation in the *effective* prompt. The
prompt builder omits structured title, ID, index, and rating fields and tells the
model not to use them, but `editorial_text` passes the official tutorial through
verbatim. Many tutorials start with text such as `2096E - Wonderful Teddy Bears`
or `Problem G1 - BAUDELAIRE (Easy Version)`:

- 192/561 Phase 3 training problems contain their literal problem ID in the
  rendered editorial input and 247/561 contain title text. Across the submitted
  600 training comparisons, 352 have at least one literal ID (71 have two).
- All 75 tuning-validation pairs expose at least one literal ID (47 expose both).
- 51/96 final-test problems expose a literal ID and 66/96 expose title text.
  Thus 816/1,000 ordered final requests contain at least one literal ID; the
  high-thinking audit contains 82/100.

The returned reasoning uses exactly this forbidden channel: problem letters,
supposed contest placement, and numerical-rating guesses appear repeatedly. A
representative tuned failure is `2084F` versus `2106G1` (true ratings 2900 vs
2200). The high-thinking base chose `2084F` in both orientations from the
algorithmic burden. The tuned trace chose `2106G1` in both, incorrectly asserted
that the two were from the same round, and treated the later `G1` position as
decisive. On `2096E` versus `2109C3`, the base trace reversed its semantic
judgment when A/B order was swapped, alternately prioritizing a rare one-trick
discovery and a longer invariant proof. This is label/order-sensitive narrative,
not stable difficulty comparison.

The existing +2.9-point result is therefore valid only as an operational score
for **unsanitized tutorial inputs**. It cannot establish that tuning improves the
intended metadata-free, inherent-difficulty judgment, even though the observed
gain is not confined to the simplest literal-ID subgroup. At the time of this
audit the clean test was still missing: tutorials needed to be sanitized (with
regression checks against IDs, contest/index markers, and titles), training and
tuning validation regenerated, a fresh base model tuned, and evaluation run on
an untouched temporal test. Cleaning only the current endpoint's evaluation
would introduce a train/eval distribution shift, and the existing final pool has
already been evaluated repeatedly.

### Metadata-sanitized base reasoning check (2026-08-07)

`cf_pairwise.editorial_text` now sanitizes tutorial and optional reference-solution
text before it is used for hashes, tuning JSONL, or evaluation prompts. It removes
problem-ID tokens (including IDs mentioned in a tutorial), URLs, title/header
lines, author/analysis/credit attribution, and the Codeforces rating footer. The
prompt path raises if an ID, URL, or source problem title survives. The tests cover
the `2084F`-style header, the `Problem G1` header, parenthesized attribution, and
reference-solution preservation. The cached-source audit found 845 non-empty
metadata-free tutorials; 17 records contain only metadata headers and remain
excluded. Rebuilding the editorial dataset gives 558 substantive pre-cutoff
training problems (the old unsanitized build had 561), 400 training pairs, 75
contest-disjoint tuning-validation pairs, and a 100-request contest-disjoint
development pool.

As a small base-model diagnostic, 20 unordered development pairs were sent in
both orientations (40 requests per setting) to `gemini-3.5-flash` with the same
clean editorial prompts and captured thoughts:

| setting | accuracy | exact-300 | ≥300 | ≥400 | swapped consistency | estimated inference cost |
|---------|---------:|----------:|-----:|-----:|---------------------:|--------------------------:|
| minimal | 80.0% | 68.2% | 80.6% | 100.0% | 70.0% | $0.184028 |
| high | 82.5% | 68.2% | 80.6% | 100.0% | 85.0% | $0.800352 |

High reasoning changed 5 of the 20 unordered-pair outcomes relative to minimal
(three improved, two worsened), so this sample suggests a +2.5-point accuracy
and +15-point order-consistency difference but is too small for a model-setting
claim. It cost about 4.35× as much. All 40 responses in each setting were valid.

Manual prompt inspection found no problem-ID token in the 400 training, 75
tuning-validation, or 40 evaluated development prompts, and neither member of
an evaluated pair's title appeared in the other prompt's editorial snippet. No
Codeforces ID appeared in the 40 high-thinking traces. Some high-thinking traces
guessed or reconstructed titles/divisions despite their absence from the prompt;
that is model behavior or pretraining, not input leakage, and is a reason to keep
the system instruction prohibiting external metadata. This check does not make
the old 2026-08-05/06 final result clean: that final pool was already evaluated
with unsanitized tutorials. A fresh tuned checkpoint and a new untouched temporal
test are still required for a clean tuning claim.

### Frozen-artifact transfer protocol (2026-08-06)

The raw Codeforces cache and pairwise run directories are intentionally excluded
from Git: `data/cf_pairwise/problems/`, `pairwise_tuning_run/`,
`pairwise_phase2_run/`, and `pairwise_phase3_run/`. They must be copied to
resume or audit the existing experiments, because a new collection re-scrapes
mutable live statement/editorial pages and is not an exact reproduction.

`scripts/sync_pairwise_artifacts.sh pull USER@HOST` transfers all four roots
from a matching checkout at the fixed default source path, resuming partial
transfers through `rsync`. `push` reverses the direction; set
`PAIRWISE_ARTIFACT_REPO` when the remote checkout uses another path. After any
transfer, `scripts/sync_pairwise_artifacts.sh verify` checks all copied files
against the tracked `data/cf_pairwise/artifact_snapshot.json`. That snapshot
records the 3f58b08 artifact set: 29 pilot-run files, 15 Phase-2 files, 9
Phase-3 files, and 978 cached problem records. A future frozen set requires an
intentional snapshot update and commit; it must never silently replace the
published verification target.

## Planned zero-shot LLM × survival integration (2026-08-07)

The integration requested after reading arXiv:2512.14220 is documented in
[`llm_survival_plan.md`](llm_survival_plan.md). The fixed scope is the base Vertex publisher model
`gemini-3.5-flash` with zero-shot, minimal-thinking, statement-only pairwise
comparisons. No tuned endpoint is involved. Knowledge cutoff is deliberately not
a selection constraint: the operational isolation rule is that prompts contain
no title/index/contest metadata, solve counts or times, existing labels,
survival outputs, CF ratings, tags, or medal data.

The proposed first dispatch is a separately approved 13-problem protocol pilot
on qoj 3747 / CF 2206: full round-robin in both orientations, 156 requests. If
its parsing, order-consistency, and cost checks pass, the evidence experiment
expands to all 15 rated mirrors (185 problems, 2,128 ordered requests). Gemini
comparisons are aggregated with Bradley--Terry, then enter an uncertainty-aware
MAP fusion as pairwise likelihood terms around the survival difficulty/SE prior.
Nested contest-level LOCO keeps held-out CF ratings out of the fit. Shipping
requires at least a 5-point improvement over calibrated LOCO 261.6, favorable
contest-cluster bootstrap evidence, and every existing metric guard unchanged.
Otherwise Gemini remains limited to provisional no-standings ratings or
disagreement QA. No repository problem statement or fitted rating was sent to
Gemini while preparing the plan.

### Executed zero-shot run (2026-08-07)

The plan was then executed under the user's $50 budget with the base
`gemini-3.5-flash` publisher model in Vertex `global`. The pilot used 156
ordered requests (13 problems, both orientations), all responses parsed, with
85.9% orientation consistency. The full run used 185 problems across 15 mapped
contests and 2,128 ordered requests. It completed with 2,128 valid responses;
two transient 429 responses were retried, and no malformed response remained.

This was a strict statement-only run. The sanitizer read each problem's
`statement` field and removed title/index/contest furniture, URLs, page
markers, and limits. A contest-level `editorial` field (which contains the
editorials for all problems) was never read or serialized into a prompt. The
run also excluded solve counts/times, tags, survival estimates, CF ratings, and
medal data. Knowledge cutoff was not used as a selection criterion.

Count-Tokens preflight estimated $6.3221 for the full dispatch; successful
response usage estimates total inference cost at **$5.4270**, within the $50
budget. The raw manifest, sanitized statements, checkpoints, and report remain
in the local gitignored `llm_survival_run/` directory; the resumable runner and
tests are tracked in `llm_survival.py` and `tests/test_llm_survival.py`.

The independent Gemini BT ranking reached 0.752 pairwise accuracy against CF
ratings and 0.816 orientation consistency. After the full-cell correction, the
local nested contest-level analysis gives survival-only RMSE **275.68** and
fused RMSE **282.31** (fusion worse by 6.63 points), with contest bootstrap
probability fusion was worse **0.733**. The smallest sparse graph stable in both
mean and worst-contest Kendall correlation remains 10 unordered matches/problem
(0.974 mean, 0.921 minimum). The two fusion gates therefore fail; the order,
sparse-graph, and budget checks pass. `arch_b.metric` remains unchanged and all
existing guards pass, so survival remains the default and no shadow rating
fields were added.

### Post-fix retest of the DeepResearch experiments (2026-08-08)

The earlier experiment logs were rechecked after the censored full-cell fix
(`76a458c`) and the unknown-problem-label retention fix (`c783db6`). No input
data or external ratings were changed. The regression suite passes **29/29**
tests. The main corrected fit uses 774,639 Architecture B observations after
including omitted no-attempt cells.

The current optimization results are:

| fit / check | result |
|---|---:|
| Architecture A median solve-count Spearman | −0.995 |
| Architecture B binary calibrated LOCO / raw LOCO | 254.2 / 248.3 CF |
| Architecture B survival calibrated LOCO / raw LOCO | **244.2 / 245.2 CF** |
| survival guards: Gym EC / Gym pooled / Kattis / AOJ / solve sanity | +0.978 / +0.969 / +0.772 / +0.568 / +0.995 |

The external validation retest gives the following pooled/per-region values:

| model | CF pooled | AsiaPac | N. Eur. | Europe | Kattis pooled | Gym pooled | LLM |
|---|---:|---:|---:|---:|---:|---:|---:|
| arch A | +0.913 | +0.920 | +0.973 | +0.861 | +0.692 | +0.960 | +0.907 |
| arch B binary | +0.937 | +0.942 | +0.974 | +0.896 | +0.755 | +0.971 | +0.908 |
| arch B survival | **+0.942** | **+0.944** | +0.972 | **+0.902** | **+0.771** | +0.969 | **+0.911** |

The conclusions that survive the correction are:

- The season experiment remains neutral for the 5-hour filter and slightly
  disfavors hard season splitting: baseline `245` CF LOCO, `+5h` `245`, and
  `+season +5h` `246`; the corresponding LLM Spearman is +0.911 for all three.
  Its harness had a stale unused `CF_REF` import, which was removed so the
  documented command runs again.
- The 2PL regional probe still overfits. The corrected held-out check is Rasch
  AUC **0.9733** versus 2PL **0.9724**; corrected median alpha is 2.56 in Asia
  East, 2.47 in Europe, 2.40 in Northern Eurasia, 2.02 in Asia Pacific, and
  1.55 in North America. The prototype harness now discards the anchor's
  unused `gym_obs=None` argument.
- The corrected held-out tagged-only solve check has 598,205 cells. Binary is
  better on this split (log-loss/Brier/AUC `0.2009/0.0615/0.9733`) than survival
  (`0.2309/0.0699/0.9673`), so the old claim that survival wins this internal
  check is no longer current. Survival remains the shipped model because it
  adds solve-time structure and wins the broader external ranking checks.
- Re-running `arch_b.medals` produces **85 bronze / 41 silver / 40 gold / 88
  platinum / 104 star**; gold bars span **[2316, 2828] CF** with median **2540**.
  The regional chooser still reports the same top three 2026 cities:
  Hong Kong, Shanghai, and Shenyang, with 105 CF historical forward RMSE.
- The frozen zero-shot Gemini responses were analysed locally again against the
  corrected survival ratings; no inference was dispatched. Nested LOCO is
  survival **275.68** versus fusion **282.31** CF (fusion worse by 6.63), with
  bootstrap probability fusion is worse **0.733**. This reinforces the prior
  decision not to integrate the pairwise model into standings. Pairwise
  accuracy remains 0.752, order consistency 0.816, and the stable sparse
  schedule remains 10 matches/problem.

The specific keep/control rows from
`autoresearch/loop-260723-1333/classic-results.tsv` were also rerun where the
source inputs are present:

| TSV experiment/control | corrected calibrated LOCO | conclusion |
|---|---:|---|
| current WF links + older ICPC + Petroz | **244.2** | baseline |
| no WF identity links | 244.2 | metric-neutral; keep for correctness |
| include WF solve rows | 244.3 | discard |
| omit older ICPC | 244.3 | addition is only −0.1, below noise |
| omit Petroz | 245.9 | addition is −1.7, below the 5-point keep threshold |
| `sigma_theta=300 / 500 / 600` | 243.8 / 243.5 / 242.9 | sub-noise; survival AUC 0.9674 / 0.9670 / 0.9666 |
| latest solve threshold 3.0 / 4.0 / 4.5 h | 244.2 / 244.1 / 244.0 | sub-noise; 4.5 h lowers Kattis slightly |
| exclude Asia West / exclude online qualifiers | 242.1 / 243.5 | sub-noise; no independent corroboration |
| all zero-solve / stable-ID zero-solve rows | 245.7 / 245.9 | discard |
| trusted-name minimum length 6 / recurrence in 3 contests | 243.9 / 243.9 | sub-noise |
| disable trusted names / scope names by affiliation / scope roster pairs by affiliation | 246.7 / 243.6 / 244.1 | no improvement; discard |

Thus none of the discarded rows becomes a justified new keep under the corrected
contract. The three historical keeps remain defensible as data-quality choices,
but their numeric gains are now smaller than the campaign's noise threshold;
the WF change is retained because it fixes an over-broad identity join, not
because this scalar metric moves.

Rows for the time-causal participant prior, refreshed live-QOJ replay rows, and
the additional camp/XCPCIO collections were not rerun individually: the prior
experiment patch is not part of the shipped code, the refreshed replay snapshot
is not present, and those candidate collection files are not tracked in this
checkout. Their TSV values remain historical results, not post-fix measurements.

The gym-merge experiment could not be rerun from this checkout because its
loader requires the missing, gitignored
`data/gym_checkpoints/api_standings.json`; the tracked gym difficulty artifact
does not contain the raw standings needed to reconstruct fixed-ability gym
observations. Its historical negative result is therefore retained as
pre-fix evidence, not relabeled as a post-fix measurement. The unrelated
Codeforces pairwise-tuning experiments do not consume `solve_mask` and were not
rerun.

### Supplemental-contest influence audit (2026-08-09)

`arch_b.data_influence` now explains the corrected effect instead of reporting
only the scalar ablation. Tagged-only calibrated LOCO is 245.253; older ICPC
alone is worse at 245.887, Petroz alone improves to 244.285, and the shipped
combination is 244.188. The same direction holds under a custom equal-contest
LOCO (249.592 → 248.560), and all ordinary guards pass, but the total 1.065-CF
gain remains well below the 5-point keep threshold.

A strict no-link control assigns every standing row its own theta and disables
UCup prior transfer, preserving all within-contest cells but sharing no ability
between contests. Calibrated LOCO degrades **244.188 → 333.469** and raw LOCO
degrades **245.192 → 330.307**, failing the raw guard. Solve-count sanity remains
+0.995 because within-contest ordering survives; what is lost is the absolute
cross-contest scale. Linking is therefore structurally essential even though
the marginal value of an arbitrary new link is not monotonic.

The causal decomposition shows that supplemental identity unions without solve
evidence move only −0.069 CF. Keeping only supplemental rows whose identities
already occur in tagged retains −0.827 of the −1.065 gain; the remaining −0.238
comes from unlinked opponents calibrating the new contests' problem scales.
Petroz supplies 4,736 linked rows and 2,976 UCup-team appearances, versus older
ICPC's 1,100 and 201. Its direct CF-anchor overlaps are overwhelmingly Northern
Eurasian (3,411, vs 307 Europe and 296 Asia Pacific), matching the observed
regional change: Northern Eurasia LOCO improves 220.13 → 214.28 while Asia
Pacific slightly regresses 208.99 → 209.73 and Europe is flat 332.48 → 332.54.
Seven of the 15 CF contests improve and eight regress.

A mutation control removed the five highest-link supplemental contests whose
individual deletion happened to improve LOCO. The post-selected metric reaches
243.646, but a fixed 117,634-cell original-`tagged.json` holdout rejects it:
tagged-only / all-supplemental / mutation log-loss is 0.229876 / 0.230252 /
0.230105, and AUC is 0.967638 / 0.967626 / 0.967593. The mutation is therefore
an example of selection overfit, not a shipped change. The full rationale and
per-contest artifact are in `data_influence.md` and
`output/data_influence.json`; run `./.venv/bin/python -m arch_b.data_influence`.

## Virtual contest performance calculator (2026-08-18)

`arch_b.export_virtual_calc` writes `output/virtual_calc.html`, an interactive
tool for a team that solved a past contest *virtually* (outside the official
window) to estimate the Codeforces-equivalent performance rating they would
have earned. Design was discussed with the user (four `AskUserQuestion`
rounds) before building; the agreed shape:

- **Contest source**: an existing contest already in the fit (not a freeform
  problem set), so the virtual team can be ranked against a real field.
- **Rating method**: the classic **Elo rank-inversion** primitive
  (`arch_a.elo.performance_rating`, eq. perf) — not a fresh Rasch MLE fit from
  the solve pattern. This is the same primitive `arch_b.medals` already uses
  for every real team's `performance_elo`, so the virtual number sits on a
  precedented scale rather than a new one.
- **Input granularity**: full ICPC-clock detail — solved/unsolved, minutes
  into the contest, and wrong-attempt count per problem, matching how
  `penalty_seconds` is actually computed in the source data.
  Penalty = `floor(time_seconds/60) + 20*wrong_attempts`, summed only over
  *solved* problems (standard ICPC rule; wrong attempts on unsolved problems
  don't count).
- **Interface**: a self-contained HTML page (open from disk, no server),
  following the exact convention of `ratings_viewer_b.html` /
  `medal_viewer.html` — contest picker grouped by year, `/*__DATA__*/null`
  placeholder swapped for embedded JSON, URL-hash deep links.

Mechanics: the virtual team's (solved, penalty) is compared against every
real team's (solved, penalty_seconds) in that contest using the standard ICPC
tie-break (more solved wins; ties broken by lower penalty) to get a
hypothetical rank. `elo.performance_rating(rank, rival_thetas)` then converts
that rank plus the real field's **internal-scale** fitted abilities (same
UCup-anchored survival fit as `arch_b.export_viewer`) into an internal-scale
rho. The rank-insertion and Elo bisection are reimplemented in vanilla JS
(`pi`, `weightedRating`, `performanceRating` in `virtual_calc_template.html`
directly port `arch_a/elo.py`) since they must run live against whatever the
user types.

Mapping rho to CF points reuses the same `arch_b.calibrate` gym-shape +
affine composition as `_cf_map` in `arch_b.medals`, but that map can't be
re-fit in the browser (no gym data or CF anchors shipped client-side), so
`export_virtual_calc.build_data()` samples it once into a dense lookup table
(every 5 CF points across [800, 4000], ~641 points) and the page does linear
interpolation. This is exact enough for display purposes and avoids
duplicating the shape-fitting math in JS.

Bundled per contest: problems (label, name, `difficulty_cf` only — no SE,
since it's just reference context while filling the form) and every real
team (rank, name, affiliation, solved, `penalty_seconds`, internal `theta`).
Teams with zero solves are already absent from the fit (dropped at the loader
level, `README.md`), matching `arch_b.medals`'s convention of restricting
rivals to solving teams. Scope is the 189 contests that survive
`MIN_SOLVE_HOURS` filtering: the 132 tagged.json regionals `arch_b.export_viewer`
also uses, plus all 57 standings-only Petrozavodsk camp contests
(`arch_b.anchor.PETROZ`) — not the UCup-anchor-only seasons, the older-ICPC
supplement, or World Finals, since those either lack full problem/statement
metadata (unlike Petroz, which does carry problem names) or aren't a natural
"your contest" target. Both sources are already part of the shipped fit by
default (`estimate_anchored`'s supplemental inputs), so no extra fitting is
needed to add Petroz — only its raw standings had to be reloaded and folded
into the same contest-building loop as tagged.json.

The picker also accepts a **qoj contest id** directly (a text box + Go
button, `goToContestId` in the template), not just the year-grouped
dropdown — useful once Petroz's 57 similarly-named "Petrozavodsk ... Day N ...
Contest" entries are mixed in. An unknown id shows an inline error rather
than a blocking `alert()`; the existing `#<contest_id>` URL-hash deep link
now routes through the same lookup.

Verified with headless Chrome (`google-chrome --headless=new --dump-dom`,
plus a scripted harness that checks boxes and calls `recompute()` directly)
rather than by inspection alone: this caught a real bug (`$(...).forEach is
not a function` — `$` is `querySelector`, singular; needed `$$` /
`querySelectorAll` for the per-row solve loop) that silently broke every
computation before the fix. Post-fix, spot checks on the 2026 ICPC Asia
Pacific Championship (77 real teams) match expectations: zero solves → rank
78/78, performance floor 800; solving all 13 problems fastest → rank 1/78,
performance ceiling 4000; a mid-pack 6-of-13 solve pattern → rank 38/78,
performance ≈2383 CF, consistent with the field's ~2340 mean θ. The Petroz
addition and contest-id lookup were re-verified the same way: a bad id shows
the inline error and clears on a valid one, `goToContestId(819)` lands on
"Petrozavodsk Winter 2022. Day 1. Kyoto U Contest 2" (147 teams), and a
5-of-13 partial solve there gives a plausible mid-field rank/performance.

### Revision: manual solved/penalty entry + calibrated standings performance (2026-08-18)

Two follow-up changes, both user-requested same day:

1. **Input switched from per-problem detail to direct solved-count +
   penalty entry.** The original design (above) had the user check off each
   problem with a time and wrong-attempt count, and the page summed those
   into solved/penalty itself. The user asked to enter solved/penalty
   directly instead — the two numbers actually used for rank-insertion (the
   per-problem breakdown was never itself part of the ranking math, only a
   way to derive the total). `#inSolved`/`#inPenalty` are now editable
   number inputs feeding `recompute()` directly; the problems table lost its
   checkbox/time/wrong-attempt columns and is now pure reference (label,
   name, `difficulty_cf`) for judging what a plausible solved/penalty pair
   would be. This is a strict simplification, not a scope change — the
   rank-insertion and Elo-inversion math are untouched.
2. **Standings table gains a calibrated Performance column** for every real
   team, not just the virtual one. Reuses `arch_a.fixedpoint.
   _performance_ratings` exactly as `arch_b.export_viewer` does (each real
   team's rho from its *actual* rank), then the same `to_cf` map already
   built for the virtual team's own number. The row→(contest, team) mapping
   needed to attach the right rho to the right team is looked up by
   `(contest_id, team index)` from `ds.contest_of_row`/`ds.team_of_row`
   directly, rather than by an incrementing counter over raw-JSON row order
   (the trick `export_viewer.py` uses, which only works because it reads
   *exactly* the fit's first source in the fit's own concatenation order).
   That trick would silently misalign here: this module's `SOURCES` is
   `[TAGGED, PETROZ]`, but the actual fit's supplemental order is
   `[OLDER_ICPC, PETROZ, WF]` — older-ICPC's rows sit between tagged's and
   Petroz's in the row array this module never reads. The `(contest_id, team
   index)` lookup sidesteps that fragility entirely and is asserted non-None
   for every team the picker builds.

Verified with headless Chrome again: default load has solved/penalty
inputs at 0/0 (rank last, performance floor); setting them to 8 solved / 900
min penalty on a 150-team contest recomputes live to rank 46/150, performance
2658 CF; the standings table now renders 5 columns per row, the top real team
shows the 4000 ceiling performance, and the highlighted "YOU" row's
Performance cell matches the summary stat exactly.
"Petrozavodsk Winter 2022. Day 1. Kyoto U Contest 2" (147 teams), and a
5-of-13 partial solve there gives a plausible mid-field rank/performance.

### Revision: Universal Cup contests added to the picker (2026-08-19)

User asked why UCup contests (e.g. `qoj.ac/contest/2921`, "Grand Prix of
Ōokayama") weren't showing up in the virtual calc. Root cause: `SOURCES =
[TAGGED, PETROZ]` never included `ucup_s3.json`/`ucup_s4.json` — UCup was
loaded only for the Phase-1 anchor fit inside `estimate_anchored`, and its
resulting UCup-only `theta_u`/`b_u` were discarded (`_`) rather than
returned, so the raw standings were never reloaded for the picker either.
(Separately: SEERC 2023–2025 aren't in the picker for an unrelated reason —
they were never fetched from QOJ into any dataset file at all; only the 2022
edition exists, as `tagged.json` contest 2511. That's a data-collection gap,
not a code fix, and is still open.)

Fix: `arch_b.anchor.estimate_anchored` gained an opt-in `return_ucup=False`
flag; when `True` it additionally returns `(ds_ucup, theta_u, b_u)` from the
Phase-1 fit it already runs internally (previously `b_u` was thrown away).
Default behavior/return arity is unchanged for every other caller.
`export_virtual_calc.py` now builds the picker's contest list twice — once
from the tagged-scale fit over `SOURCES` (unchanged), once from the UCup-only
fit over `UCUP_SOURCES = UCUP` — via a shared `_contests_from(ds, theta, b,
to_cf, paths, uf, exclude_ids=())` helper (the previous single inline loop
in `build_data()`, factored out unchanged apart from the new parameter). The
same `to_cf` map (fit once from the tagged-scale records) is reused for both,
since it's a general internal-scale→CF-points affine map, not tied to which
dataset the internal thetas came from.

17 contest ids appear in *both* `tagged.json` and the UCup files (e.g. id
2511 above is not among them, but ids like 1784/2908/3169/... are) — without
handling, they'd be listed twice with two different fits' numbers. Fixed by
passing `exclude_ids={int(cid) for cid in ds.contests}` (the tagged fit's
own contest set) to the UCup pass, so an overlapping contest is shown once,
from the tagged-scale fit only.

Contest count: 189 → 241 (132 tagged + 57 Petroz, unchanged, plus 52 UCup
rounds not already in tagged.json; UCup's raw 76 contests minus the 17
overlaps minus a few dropped by the same `MIN_SOLVE_HOURS`/dedupe filters
`load()` applies). Verified `2921` now appears with real problem
`difficulty_cf` values and team performances, no contest id is duplicated in
the output (`grep`-checked), and `arch_b.export_virtual_calc` still runs
clean end-to-end.

### Revision: export the 52 UCup-only contests for ../my-react-app (2026-08-19)

Follow-up: the user wanted these same 52 UCup-only contests' problems added
to `../my-react-app`'s problemset app, with their calibrated ratings — a
different consumer than the virtual calc, so a separate script,
`arch_b/export_ucup_only.py`, was added rather than reusing
`export_virtual_calc`'s in-memory picker data. It fits the same UCup-only
Phase-1 fit (`estimate_anchored(..., return_ucup=True)`), computes Laplace
SE (`survival.laplace_se`), and calibrates to CF points with the same
shape+affine map as `arch_b.calibrate` (`_gym_shape`/`_anchors`, duplicated
inline rather than importing `calibrate.main`'s internals, since that
function also writes a file and picks between binary/survival models —
more than this script needs). Writes `output/ucup_only_contests.json`
(canonical/tagged.json-shaped, no LLM tag fields) and
`output/ucup_only_ratings.json` (problem_ratings_calibrated.json-shaped).

37 of the 52 contests carry no `year` in the source UCup JSON (`ucup_s3`/
`ucup_s4.json`); the react app's display string is `contest_name + ' ' +
year` verbatim, so those were rendering as e.g. "Grand Prix of Ōokayama
null". Fixed by falling back to each season file's most common non-null
year when a contest's own `year` is missing (2024 for `ucup_s3.json`, 2025
for `ucup_s4.json`, computed dynamically via `Counter.most_common`, not
hardcoded) — only affects the exported `year` field, not the fit itself.

The my-react-app side (`scripts/merge_ucup.py`, `DETAILS.md`) is documented
in that repo.

## Gemini 3.6 Flash vs 3.5 Flash: 200/300-point gap check (2026-08-21)

The existing frozen, statement-only Codeforces baseline pairs were reused so
both models saw identical inputs and both A/B orientations. The subset had 46
ordered requests at an exact 200-point rating gap and 52 at an exact 300-point
gap per model (196 requests per model total). The API model IDs
`gemini-3.6-flash` and `gemini-3.5-flash` both returned valid JSON decisions.

Accuracy is the empirical probability of selecting the higher-rated problem;
intervals are two-sided 95% Wilson intervals. The API schema returns only A/B,
so these are benchmark correctness probabilities, not calibrated confidence
scores for individual answers.

| model | gap | correct | accuracy (95% Wilson CI) | A/B order consistency |
|---|---:|---:|---:|---:|
| Gemini 3.5 Flash | 200 | 21/46 | 45.7% [32.2%, 59.8%] | 78.3% |
| Gemini 3.6 Flash | 200 | 16/46 | 34.8% [22.7%, 49.2%] | 82.6% |
| Gemini 3.5 Flash | 300 | 31/52 | 59.6% [46.1%, 71.8%] | 57.7% |
| Gemini 3.6 Flash | 300 | 30/52 | 57.7% [44.2%, 70.1%] | 84.6% |

3.5 has the higher point estimate on both gaps, but the intervals overlap and
paired exact McNemar tests do not establish a model winner (p=0.302 at gap 200;
p=1.000 at gap 300). The notable signal is consistency: 3.6 is much less
sensitive to A/B order, especially at the 300-point gap. The raw predictions
are retained in the gitignored `gemini_gap_run/` directory.

## Anchoring audit: UCup anchor, gym shape, CF affine, LLM comparisons (2026-08-21)

A review of every mechanism that pins the difficulty scale — the Phase-1
Universal Cup prior, the gym-learned monotone shape, the CF affine leg, and the
LLM opinions — asking where the scale is actually anchored, how consistent it is
across contests and regions, and why the exported UCup ratings disagree with the
shipped fit. All numbers are measured on the current shipped survival fit; the
fit variants A–D are scored on exactly the metric `arch_b.metric` prints (which
reads **244.3** today). No repository code was changed to produce them.

### Finding 1 — the UCup prior-mean anchor is a no-op in Architecture B

`arch_b.anchor` feeds each UCup team's Phase-1 `theta_u` in as its Gaussian
prior *mean* at the single global `sigma_theta=400`. Refitting with that prior
replaced by the flat `MU0` — same union-find, so identity links are held
constant and only the prior mean changes — moves the fit by

    delta b:     mean -3.6, sd 0.96, max |delta| 10.3, corr 0.999997
    delta theta: mean -4.2, sd 4.9,  max |delta| 72.6

and leaves the metric identical (244.3 anchored vs **244.3** unanchored, all
guards unchanged). Two reasons: at `sigma_theta=400` a well-observed team is
dominated by its own likelihood (the documented design intent), and the affine
calibration leg absorbs any global level shift the anchor could produce. What
actually normalizes the scale is the shared union-find plus the joint
likelihood — consistent with the existing no-link control (LOCO 244.2 → 333.5).
Unlike `arch_a.anchor`, whose prior *strength* scales with each team's UCup
evidence, arch B's anchor has no measurable effect on the shipped deliverable.

### Finding 2 — the exported UCup-only ratings sit ~90 CF points too low

`arch_b/export_ucup_only.py` rates the 52 UCup-only contests from the **Phase-1
UCup-only fit** (`b_u`) and then pushes them through the shape+affine map fit on
the **tagged-scale** `b`. Those are two different fits with two different
scales — the very premise the two-phase anchor exists to address. 24 contests
appear in both fits, giving 305 problems rated twice:

    mean b_tagged 2318   mean b_ucup 2260   offset -59
    b_ucup ~ 0.959 * b_tagged + 36   (RMSE 65, corr +0.998, residual sd 23)
    per-contest offset range: -39 .. -70 (all 24 contests negative)

The UCup-only fit is a near-perfectly ranked but systematically compressed and
shifted copy of the tagged scale, so applying the tagged-domain calibration to
it under-rates every exported problem. Correcting `b_u` through the measured
crosswalk before calibration raises `output/ucup_only_ratings.json` by **+90 CF
points on average** (mean 2418 → 2508, max shift 147, largest in the hard tail).
The same mismatch affects the UCup half of the virtual calculator, whose UCup
abilities come from the same Phase-1 fit
(`theta_ucup ~ 0.851*theta_tagged + 261`).

### Finding 3 — one joint fit removes the second scale at no metric cost

Since the anchor is a no-op (Finding 1) and the second scale is the source of
Finding 2, the structurally simpler option is to fit UCup as ordinary data.
Four variants, same union-find construction, same metric and guards:

| variant | fit inputs | prior mean | problems | CAL LOCO | raw LOCO | gym EC | gym all | Kattis | AOJ |
|---------|-----------|------------|---------:|---------:|---------:|-------:|--------:|-------:|----:|
| A (shipped) | tagged+supp | UCup Phase-1 | 2475 | **244.3** | 245.4 | +0.978 | +0.969 | +0.772 | +0.568 |
| B joint | tagged+supp+UCup | MU0 | 3159 | **245.4** | 246.9 | +0.977 | +0.969 | +0.772 | +0.568 |
| C joint+prior | tagged+supp+UCup | UCup Phase-1 | 3159 | 245.9 | 247.2 | +0.977 | +0.969 | +0.771 | +0.568 |
| D no anchor | tagged+supp | MU0 | 2475 | **244.3** | 245.4 | +0.978 | +0.969 | +0.773 | +0.568 |

B costs +1.1 CF points — inside the ±20 bootstrap noise floor and well under
`program.md`'s 5-point keep threshold — while putting 684 more problems on the
shipped scale and removing the Phase-1/Phase-2 mismatch by construction.

**Blocker:** `arch_a.load` materializes dense `rows x n_problems` arrays (`y`,
`solve_mask`, `tau` float64, `wrong` int64). At 94,093 rows x 3,464 problems the
joint fit needs ~2.6 GB for `tau` alone and ~11 GB at peak, which OOMs on a
16 GB machine; variants B/C above were only measurable after temporarily
narrowing `tau` to float32 and `wrong` to int16 (verified neutral: patched
variant A reads 244.3, identical to the unpatched `arch_b.metric` run). Observed
density is ~0.35% (774,639 observed cells out of 223M dense cells), and
`model._observations` flattens the matrices to 1-D anyway, so a per-contest
block or COO layout is a prerequisite for the joint fit, not an optimization.

### Finding 4 — cross-contest offsets are small and bounded

Decomposing the in-sample residual of the shipped map on the 185 CF anchors:

    residual sd 240.3 = between-contest 99.5 + within-contest 218.7
    per-contest constant offsets account for 17.1% of residual variance
    oracle per-contest intercept:        RMSE 240.3 -> 218.7
    oracle per-contest intercept+slope:  RMSE 240.3 -> 207.6

Per-contest offsets run from -161 (CF 1773) to +267 (CF 2068), but the
within-contest slope is stable (mean 0.906, sd 0.105, vs a global 0.909) and
within-contest Spearman is +0.85 to +1.00. So inside the anchored regions the
contest-to-contest inconsistency is real but bounded: perfect per-contest
re-anchoring would buy ~22 CF points, and there is no residual within-contest
compression left for a better map to remove.

### Finding 5 — the per-region level is not identified: the two standings-free referees disagree in sign

Scoring the shipped `difficulty_cf` per region against the **gym** yardstick
mapped onto CF points by its certified transform (`cf ~ 1.23*b_gym - 448`), SEs
clustered by contest:

| region | n | contests | offset (ours - gym) |
|--------|---:|---:|---:|
| Europe | 294 | 24 | +321 ± 32 |
| North America | 24 | 2 | +337 ± 34 |
| Asia West Continent | 21 | 2 | +264 ± 49 |
| Asia East Continent | 230 | 18 | +204 ± 27 |
| Asia Pacific | 98 | 8 | +154 ± 74 |

The pooled level is not interpretable (the gym transform rests on 8 problems),
but the *differences* are, since one transform applies to every region:
Europe − Asia East = **+117 ± 42**, Asia East − North America = **−133 ± 44**,
Asia Pacific − North America = **−183 ± 82**.

Repeating the same measurement against the **LLM bucket** referee (`tagged.json`
`difficulty_estimate`, editorial-backed contests only; each problem's residual
is taken against the global mean `difficulty_cf` of its own bucket — easy 1638,
medium 2225, hard 2675, very_hard 3247):

| region | n | contests | offset (ours - LLM bucket) |
|--------|---:|---:|---:|
| Asia East Continent | 420 | 33 | +65 ± 15 |
| Latin America | 13 | 1 | +18 ± n/a |
| Asia Pacific | 203 | 16 | +5 ± 31 |
| North America | 75 | 7 | −21 ± 32 |
| Europe | 274 | 23 | −69 ± 26 |
| Northern Eurasia | 105 | 9 | −74 ± 45 |

Here Asia East − Europe = **+134 ± 30** and Asia East − North America =
**+86 ± 35** — the **opposite sign** of the gym result on the same pair of
regions. Within-region ranking is excellent against both referees (+0.95 to
+0.98 on gym), so this is purely a level effect; but the two standings-free
referees do not agree on which way the level is wrong.

The conclusion is that a per-region level correction **cannot be estimated from
either referee alone today**. Each carries its own region-specific population
bias: the gym measures who chooses to virtual-participate in which region's
mirror, and the LLM bucket is a 4-level absolute label whose meaning can drift
with statement style, length, and translation quality by region. This retires
the obvious next move (adding per-region offsets learned from the gym) — it
would bake in a bias the other referee reverses.

### Finding 6 — the LLM comparison instrument was pointed at the wrong axis

`llm_survival.py` is the one referee that can be forced into a *direct*
cross-region head-to-head, which is exactly what removes the absolute-scale
drift that spoils the bucket labels in Finding 5. As built, it cannot: the
pilot asserts its scope to the 185 CF-anchored problems in 15 mirrors, and
`_make_requests` groups by `contest_id` and pairs only within a contest, so the
Bradley–Terry scores in `llm_survival_run/analysis.json` are **per contest**
(`bt.per_contest[cid].bt_scores`) with no edges between contests.

That is the axis where the fit is already strongest — within-contest Spearman
vs CF is +0.85 to +1.00 and there is no within-contest compression left
(Finding 4) — which explains why the fusion result was flat-to-negative (nested
contest-level LOCO 275.68 survival vs 282.31 fused). It says nothing about the
cross-contest and cross-region levels, which is the open question.

The instrument is also the only anchor candidate with full regional reach.
Statement coverage is **100% for all 1,668 tagged problems in every region**
(Asia East 466, Europe 356, Asia Pacific 324, North America 300, Northern
Eurasia 140, Asia West 45, Latin America 37) and **100% for all 989 UCup
problems**; only the 850 standings-only supplemental problems (Petroz, 2020–21
ICPC) have none. Compare the current external coverage in Finding 7. The prior
full run was 2,128 requests at an estimated $5.4270 (~$0.0026/request), so a
cross-contest schedule sized for contest-level offsets — order 40 cross-contest
pairs per contest over ~207 contests, both orientations — is roughly 17k
requests, i.e. tens of dollars, not hundreds.

Two design points carried over from the existing experiments: run both A/B
orientations and keep only order-consistent pairs (the within-contest run scored
81.6% consistency), and prefer `gemini-3.6-flash`, which the 2026-08-21 gap
check found markedly more order-consistent than 3.5 (82.6%/84.6% vs
78.3%/57.7%) at indistinguishable accuracy. Crucially the new instrument can be
**validated before it is trusted**: a cross-contest schedule restricted to the
15 CF-mirrored contests can be scored against the known per-contest CF offsets
of Finding 4, so whether cross-contest LLM BT recovers real level differences is
a measurable question answered on existing anchors.

### Finding 7 — anchor coverage, not fit quality, is the binding constraint

Of the 207 fitted contests, **92 (44%)** have any external anchor at all and
only 15 have a CF-rated mirror:

| yardstick | contests |
|-----------|---------:|
| CF rated mirror | 15 |
| gym mirror | 54 |
| Kattis | 45 |
| AOJ | 4 |
| **any** | **92 / 207** |

Unanchored by region: all 75 supplemental contests (896 problems — 36% of the
rated set, contributing links but never checked), 18/36 Asia East, 7/22 Asia
Pacific, 7/11 Northern Eurasia, 4/29 North America, 3/3 Latin America. All 185
CF anchor problems come from just three regions (Asia Pacific 93, Northern
Eurasia 50, Europe 42), so the affine leg is fit on three regions and
extrapolated onto the other five. The exhaustive problemset sweep already
established that no further rated mirrors exist for the current contest set, so
anchor growth requires new contests or a new *kind* of anchor.

The other collected-but-unused source is the ability side:
`data/cphof_cf_participants.json` carries 2,119 roster-corroborated standing
appearances across 89 contests, **1,677 (79%) of them in Asia East Continent** —
precisely the region with no CF problem-level anchor. A time-accurate CF prior
on `theta` pins the scale through the *ability* axis and propagates to `b` in
every contest a matched team played. See `cf_participant_ratings.md` for the
identity layer and its open requirement (exact per-contest timestamps).

### Suggested structural shift

The theme is one the repo already established with the gym shape — **use the
trustworthy half of each signal and discard the noisy half** — applied to the
axis the current pipeline leaves unmodelled. Every referee here is trustworthy
about *ordering within a contest* and suspect about *level across contests*,
while the fit is the reverse. Ordered by dependency, not by expected metric gain
(Findings 1 and 4 say the metric is near its floor inside the anchored regions):

1. **Sparse data layer.** Replace the dense `rows x n_problems` blocks in
   `arch_a.load` with per-contest blocks or COO. Prerequisite for everything
   below; also removes a ~6 GB working set from every current run.
2. **One fit, one scale.** Fold UCup into the main fit as ordinary data and
   retire the Phase-1 prior-mean anchor (measured cost +1.1 CF points; gain: 684
   more problems on the shipped scale and no second scale to reconcile). This
   deletes the class of bug in Finding 2 instead of patching it. If the joint
   fit is deferred, the interim fix is to push `b_u` through the measured
   crosswalk before calibrating `export_ucup_only` and the virtual calc.
3. **A cross-contest LLM pairwise instrument.** Re-point `llm_survival.py` from
   within-contest to cross-contest pairs, first on the 15 CF-mirrored contests
   alone so it can be scored against the known per-contest offsets of Finding 4,
   then — only if it passes — across all statement-bearing contests. This is the
   only path to a referee with full regional coverage that is standings-free
   *and* free of the absolute-scale drift that made the two existing referees
   disagree in Finding 5.
4. **Hierarchical calibration instead of a single global affine.** Model
   `cf_p ~ A*f(b_p) + B + u_contest + v_region` with partially pooled `u`, `v`,
   with the cross-contest LLM BT scores (step 3) as the observation that
   identifies `u` and `v` outside the 15 anchored contests. Anchored contests
   estimate their own offset; unanchored ones shrink to their region, and
   unanchored regions to the global mean. Inside the anchored regions the
   ceiling is modest (240 → 219 in-sample); the real payoff is that the
   per-region level becomes an explicit estimated parameter with an honest
   uncertainty instead of an assumed zero.
5. **Ability-side CF anchoring.** Consume the CPHoF layer as a time-accurate
   Gaussian prior on `theta` for roster-complete rows — the only anchor in the
   repo that reaches Asia East Continent numerically, and a third independent
   opinion on the Finding 5 region question.

**Explicitly not recommended:** per-region gym offsets. Per-region gym *shapes*
were already tried and overfit (298 vs 266), and Finding 5 now shows that even
one offset parameter per region, learned from the gym alone, would encode a
level difference the LLM referee reverses.

## Implementing the structural shift (2026-08-21)

The five steps proposed by the anchoring audit above, as built and measured.
Every number is from `arch_b.metric` (the shipped calibrated LOCO CF-point RMSE
plus its guards) unless stated otherwise; the pre-change baseline is **244.3**.

### 1. Sparse data layer — done

`arch_a.load` stored `y`, `solve_mask`, `tau` (float64) and `wrong` (int64) as
dense `n_rows x n_problems` matrices that were **99.65% empty**: a cell is
observed only where the problem belongs to the row's contest. `Dataset` now
carries the observed cells in COO form — `obs_row`, `obs_prob`, `obs_y`,
`obs_tau` (float32), `obs_wrong` (int32) — in the exact row-major order
`np.nonzero(solve_mask)` produced, plus precomputed `solved_count` and
`field_count` for the per-problem reductions seven call sites were doing by
hand. `model._observations` / `survival._observations` now read the arrays
directly instead of flattening a dense matrix back into them.

| | before | after |
|---|---:|---:|
| peak RSS, `arch_b.run --survival` | 6,177 MB | **696 MB** |
| runtime | 12 s | 10 s |
| `calibrated_loco_cf_rmse` | 244.3 | **244.3** (bit-identical) |

`arch_a.run` reproduces its documented `theta=[1372, 3698]` mean 2011 and median
solve-count Spearman −0.995. This was the prerequisite for step 2: at joint size
(94,093 rows x 3,464 problems) the dense layout needs ~11 GB and OOMs on a 16 GB
machine.

### 2. One fit, one scale — done

`arch_b/anchor.py` became `arch_b/joint.py`, `estimate_anchored` became
`estimate_joint`, and the Universal Cup is now ordinary fit data rather than a
separate Phase-1 anchor. `arch_a.anchor` is untouched: there the prior
*strength* scales with each team's UCup evidence and it does measurably tighten
the scale (shared-team RMSE 519 → 301).

| | before | after |
|---|---:|---:|
| `calibrated_loco_cf_rmse` | 244.3 | **245.4** |
| raw affine LOCO | 245.4 | 246.9 |
| rated problems | 2,475 | **3,159** |
| gym EC / gym pooled / Kattis / AOJ | +0.978 / +0.969 / +0.772 / +0.568 | +0.977 / +0.969 / +0.772 / +0.568 |

The +1.1 cost is inside the ±20 bootstrap noise floor and well under
`program.md`'s 5-point keep threshold. In exchange the second scale is gone:
all 684 UCup-only exported problems now come from the shipped fit and match
`output/problem_ratings_calibrated.json` to within rounding (max |diff| 0.2),
against a **mean +79 CF shift** from the old two-scale export. `external_validate`
is unchanged within noise (CF pooled +0.941, Kattis +0.770, gym +0.969, LLM
+0.911). `export_virtual_calc` no longer needs a second fit or `exclude_ids`
(241 contests, unchanged); `data_influence._fit` always includes UCup so its
supplemental variants stay comparable, and its recorded artifact needs
regenerating.

### 5. Ability-side Codeforces anchoring — done, and inert

`arch_b/cf_prior.py` turns `data/cphof_cf_participants.json` into a
time-accurate Gaussian prior on team ability — `strat.tex` eq. cfprior, and the
only anchor that reaches Asia East Continent (79% of the corroborated
appearances). Conservative by construction: roster-complete rows only, a
leak-free 1-January-of-the-season cutoff (regionals carry no start time), the
`lse` team reduction, trust-weighted precision, and placement *relative* to
`MU0` so no CF level enters the fit. `joint.estimate_joint` gained a `prior`
hook; both fitters already accepted a per-team `sigma_theta` array.

Coverage is 57 team identities from 310 standing rows, and the sweep is flat:

| scale \ cf_sigma | 100 | 200 | 400 |
|---|---:|---:|---:|
| 0.5 | 245.6 | 245.4 | 245.4 |
| 1.0 | 245.6 | 245.4 | 245.4 |

with every guard unchanged. Same mechanism as Finding 1: those 57 teams are
World-Finals-level rosters that play many contests, so their own likelihood
already pins them. It is therefore **off by default**.

Its value is as a yardstick. `python -m arch_b.cf_prior --validate` gives the
repo's first external check of the **ability** axis, which no other yardstick
reaches:

    fitted theta vs CF team ability: Pearson +0.752  Spearman +0.762  (57 teams)
    cf_ability ~ 2.86 * theta - 3699   (sd ratio 3.80, residual sd 220 CF)

That 2.86 is much steeper than the **1.63** slope the shipped difficulty map
applies over the same range, even though `theta` and `b` share one logit scale
by construction — so the compression is not a single global factor, and the
ability axis is compressed more than the difficulty axis where they overlap.
(Caveat: this population is elite and narrow — theta sd 88 against CF sd 334 —
so range restriction and errors in `theta` both inflate the slope estimate.)

### 4. Hierarchical calibration — done; ships as the uncertainty model

`arch_b/hier_calibrate.py` fits `cf = A*f(b) + B + u_contest + v_region` with
partially pooled Gaussian random effects: empirical-Bayes group means
`n_g/(n_g + sigma^2/tau^2) * mean residual`, and method-of-moments variance
components debiased by the sampling variance of a group mean (estimating `tau`
from the *shrunken* means instead collapses it to zero — the first version of
this module did exactly that and reported `tau=0`). An `offsets=` hook accepts
an external per-contest level observation as a weighted pseudo-observation of
`u_c`.

On the survival fit's 185 anchors (15 contests, 3 regions):

    sigma = 228.0    tau_contest = 72.4    tau_region = 12.0   CF points
    per-region level: Asia Pacific +0.0, Europe +3.3, Northern Eurasia -3.4

**This is the substantive result.** Contest-to-contest level varies materially
(tau 72 CF), but the between-*region* level, among three regions as different as
Asia Pacific, Europe and Northern Eurasia, is essentially nil — 12 CF points.
That is direct evidence that the 100+ point region gaps the gym (+117 Europe
over Asia East) and the LLM bucket labels (−134 on the same pair) disagree about
in Finding 5 are **referee artifacts, not fit bias**. It does not prove Asia
East is unbiased — no CF anchor reaches it — but it removes the prior that large
regional level bias is the norm.

LOCO does **not** improve: 245.4 plain vs 248.3 hierarchical. A held-out contest
cannot know its own `u`, and with `tau_region` at the noise floor there is
nothing for the region effect to transfer. The shipped map therefore stays the
plain global affine.

What did change is the reported uncertainty. `difficulty_cf_se` previously
scaled only the Laplace SE of `b` through the map — treating the map itself as
exact. It is now the quadrature sum of that (kept as `difficulty_cf_fit_se`) and
the calibration **level** sd (`difficulty_cf_level_sd`): the posterior sd of its
own offset for the 15 anchored contests (~48 CF), and `sqrt(tau_c^2 + tau_r^2)`
= **73.4 CF** for the 2,970 problems no CF anchor ever saw.

| | median | mean |
|---|---:|---:|
| `difficulty_cf_fit_se` (old meaning) | 46.8 | 61.2 |
| `difficulty_cf_level_sd` | 73.4 | 71.9 |
| `difficulty_cf_se` (new total) | **86.4** | 99.7 |

The level term is larger than the fit term for a typical problem, so the old
figure understated the real uncertainty by about half. `calibrate`,
`export_ucup_only` and the Architecture B viewer all report the same total.

### 3. Cross-contest LLM comparisons — instrument built and validated

**2026-09-05 correction:** the comparisons were collected, but the offset
validation below leaks held-out CF ratings (`llm_crosscontest.py:457`). The
245.4 → 242.8 improvement and offset correlation do not validate a deployable
instrument. See [experiment_review.md](experiment_review.md), finding 1.

`llm_crosscontest.py` pairs problems **across** contests, the axis
`llm_survival.py` never touched (`_make_requests` groups by `contest_id`, and
its scope is asserted to the 185 problems of the 15 rated mirrors). Same
statement-only prompt, same metadata sanitizer, both A/B orientations, a seeded
schedule whose partners are drawn **uniformly from other contests** — never using
our difficulty, a CF rating, or any other target proxy — and resumable
checkpoints behind a hard preflight budget gate. `bt_scores` refits
Bradley--Terry by coordinate Newton in O(edges) per sweep, because
`llm_survival.bt_fit` builds a dense `(n-1)^2` Hessian per iteration, which is
fine for one 13-problem contest and hopeless for a cross-contest graph.
Statements that cannot be made metadata-free are **skipped**, never sent with the
leak (the Phase-3 forensics showed verbatim ids and labels invalidate the
comparison); that costs a handful of problems.

**Validation stage, dispatched.** 185 problems / 15 CF-mirrored contests, 698
cross-contest unordered pairs in both orientations = 1,396 requests to
`gemini-3.5-flash`, exact `countTokens` preflight **$3.5402**, all 1,396
returned valid decisions (2 transient failures retried). The global BT is fitted
over these new cross-contest edges *plus* the 2,128 within-contest predictions
the earlier run already paid for.

The instrument is **not** damaged by crossing contests — raw pairwise accuracy
against official CF ratings is nearly the same either way, with the same
gap profile:

| CF rating gap | cross-contest | within-contest |
|---|---:|---:|
| <= 200 | 0.531 | 0.579 |
| 300-500 | 0.619 | 0.658 |
| 600-1000 | 0.711 | 0.752 |
| > 1000 | 0.899 | 0.895 |
| **all** | **0.717** (n=1,394) | **0.754** (n=2,054) |

A/B order consistency was 0.784, in line with the within-contest run's 0.816.

But as a *global* difficulty estimator it is far behind the standings fit —
Spearman against CF **+0.634** for the cross-contest BT versus **+0.943** for
survival — and the level signal it does carry is weak:

    correlation of BT-implied vs true per-contest offsets:  +0.540  (15 contests)
    optimal shrink factor k:                                 0.453
    LOCO plain 245.4  ->  LOCO + shrunk BT contest offset 242.8   (-2.6)

with `k` and the affine leg both refit inside each fold and the held-out contest
contributing only its own BT offset. **Applying the offsets raw makes things
worse** (247.6): they are about half noise, so they must be shrunk — the first
version of `analyse` skipped that and reported a false negative.

The mechanism is visible in the accuracy table. Contest levels differ by
`tau_contest = 72` CF points (step 4), which is deep inside the <= 200 gap band
where the model runs at 0.53 — barely above chance. The instrument measures the
right quantity on the right axis; its resolution is simply coarser than the
quantity.

**A fixed-position variant is worse, not better.** Holding each problem at our
own calibrated difficulty and fitting one free level per contest — the
`gym_difficulty` pattern, and the better-posed estimator on paper — scores
offset correlation +0.36 to +0.40 across `kappa` in {200, 400, 600}, against
+0.540 for the free BT. Fixing positions forces every disagreement with our
within-contest ranking into the offset as noise; the free BT uses the
within-contest edges to pin positions from the model's *own* view and isolates
the level better. That matters for costing the deployment stage: the validated
estimator **needs within-contest edges too**, not only cross-contest ones.

**Deployment stage: not dispatched.** The full scope is 2,345 statement-bearing
problems over 191 contests (Universal Cup 642, Asia East 458, Europe 442, North
America 312, Asia Pacific 279, Northern Eurasia 140, Latin America 37, Asia West
35 — exactly the regions with no anchor). Cross-contest pairs alone at 4 matches
per problem cost about $21, which fits the remaining budget; but adding the
sparse within-contest schedule the validation showed is necessary (~10 matches
per problem, the density `llm_survival`'s own sparse-schedule analysis selected)
takes the full scope to roughly **$75** — over the approved cap. A targeted
build covering only the unanchored regions plus the 15 anchored mirrors as
bridges (~1,027 problems) is about **$21** and would fit. That scope change was
not pre-approved, so the run is prepared but not dispatched.

## Experiment and implementation review (2026-09-05)

Reviewed the current ICPC/LLM implementation, saved artifacts and historical
campaigns at `8a351e0`; full findings, evidence, limitations, artifact hashes and
recommended experiment order are in [experiment_review.md](experiment_review.md).
This was a documentation-only review: no model fixes, output regeneration or
paid inference were performed.

Reproduced `arch_b.metric`: **245.4 calibrated / 246.9 raw affine CF RMSE**,
all guards pass. The joint dataset has **260 contests, 37,576 identities, 3,159
problems, 73,023 rows and 923,842 observed cells**, including the four World
Finals. Earlier WF-identity-only descriptions and dataset counts are historical.
The unittest suite passes **32/32**. Tagged-only binary/survival log-loss
reproduces at **0.2009/0.2309**, Brier **0.0615/0.0699**, and reported AUC
**0.9733/0.9673**; AUC tie handling needs correction.

Principal corrections:

- The cross-contest LLM held-out offset reads `cf[te]`. Saved artifacts
  reproduce baseline **245.4277** and leaked **242.8481** RMSE. A simple
  deployable BT-minus-survival offset control yields **246.7782**. This is
  diagnostic, not a tuned replacement; the claimed gain cannot justify rollout.
- Rank/AUC ties and NaN guard enforcement need repair. The holdout also
  bypasses the joint configuration, uses outcome-dependent preprocessing,
  and has 284 test cells with the same team/problem key in training.
- Fit-plus-level SE is not validated total CF prediction uncertainty. A LOCO
  interval diagnostic covers **62.2%** of CF ratings within 1.96 SD; this is
  predictive coverage, not a test against latent true difficulty. Three
  anchored regions do not establish absence of bias in unanchored regions.
- There are **281 repeated contest/identity groups** (295 excess rows), so
  the virtual calculator's performance dictionary overwrites nonunique keys.
  Identity resolution needs a separate participation identifier and provenance
  audit. These counts alone do not establish which merges are wrong.
- The CF prior tests cohort-centered relative spacing, not absolute anchoring;
  its roster check also needs row-specific corroboration.
- The gym shape's historical 22-point gain is now **1.48 points** on saved
  joint-fit records. A paired contest bootstrap of fixed LOCO errors gives
  shaped-minus-affine 95% interval **[-9.63, +6.16]** (10,000 draws, seed
  20260905); it does not account for historical model selection.

Keep the sparse/full-cell loader and joint fit. Repair and version evaluation,
freeze task-specific holdouts, rebaseline calibration/uncertainty, then audit
identity/date/ability data before focused model experiments. The historical
finite-search “plateau” is not an established error floor. Missing raw gym
standings and discarded campaign snapshots were not reconstructed by guessing.

## Review implementation resolution (2026-09-06)

The concrete correctness defects that could be fixed from the repository's
available evidence are now repaired:

- `llm_crosscontest.analyse` no longer reads held-out CF labels while constructing
  predictions. Each fold learns a BT-minus-survival contest feature and its
  coefficient from training contests only. Mutating held-out labels leaves both
  plain and adjusted predictions unchanged. Reanalysis of the existing responses
  gives **245.43 plain / 246.78 adjusted LOCO RMSE**; the wider paid run remains
  unjustified.
- Every Spearman helper and the AUC rank-sum now use average ranks for ties. The
  metric rejects non-finite primary/guard values, requires exactly **185 problems
  / 15 contests** of anchor coverage, and uses the corrected raw ceiling
  **251.9 = 246.9 + 5**. The Kattis guard now accepts only unique titles with at
  least three matches corroborating the source contest: 427 pooled matches,
  survival Spearman **+0.795**.
- `predict_eval` now loads the same 260-contest joint configuration as the shipped
  fit, assigns repeated resolved team/problem responses to one side of the split,
  and derives contest duration from training solves only. It is explicitly an
  imputation check for retained appearances, not a future-contest forecast. The
  corrected run has 923,842 cells / 920,158 response groups; binary is log-loss
  **0.2040**, Brier **0.0623**, AUC **0.9727**, and survival is **0.2329 / 0.0701 /
  0.9674**.
- The loader preserves `(contest_id, source_row)` as a participation identifier.
  The virtual calculator keys rank-derived performance by this identifier, so
  two rows merged to one ability identity no longer overwrite each other.
- CF-prior roster completeness now requires every rating history to be
  corroborated on that exact standing row, not merely present globally. Coverage
  is **54 identities / 295 rows** after the correction (previously 57 identities).
- Binary and survival fits reject non-finite or unconverged results and verify
  that the final objective is not below its initial value. The full suite passes
  **42 tests**.
- The calibrated artifacts now call the quadrature of conditional fit SE and
  contest-level SD `difficulty_cf_partial_se`; the ambiguous
  `difficulty_cf_se` field was removed. This fixes the claim/label, not the
  missing statistical work needed for calibrated CF prediction intervals.

The full survival metric remains **245.4 calibrated / 246.9 raw CF RMSE**, with
all guards passing; the binary control is **256.0 / 248.1**. Still open because
the required evidence is absent or the work is a new experiment: adjudicating
identity unions, collecting recorded contest durations/dates, constructing fresh
frozen forecast and regional-transfer sets, estimating full joint/calibration
uncertainty, and reconstructing the missing raw gym/campaign snapshots.

## Fit and rating improvement strategy (2026-09-06)

[rating_improvement_strategy.md](rating_improvement_strategy.md) reviews the
measurement assumptions beyond the existing metrics at `c181982`. Fresh read-only
diagnostics on the shipped joint inputs find 525,259 omitted source problem cells
(56.9% of fitted cells), 2,052 dropped zero-solve rows with recorded wrong attempts,
and 142 fitted identity components whose source rosters have no member common to
all of them. These identify uncertainty about engagement and roster continuity;
they do not establish that every omitted cell or identity merge is wrong.

Five QOJ problem IDs occur in both Luxor World Finals (1661/1662), currently with
separate fitted difficulties. The official ICPC problem books corroborate the
shared tasks; saved CF-mapped ratings for Turning Red are 1844.7 and 1921.4.
This is a small existing panel for testing shared task identity and context,
not a demonstrated large scale error. The official event page also distinguishes
the April 2024 calendar event from the source's 2022/2023 season labels.

Recommended work starts with an audited panel of shared tasks, zero-solve
appearances with submissions, and influential roster chains, followed by separate
common-task and shrunk appearance-effect experiments. The larger model direction
is completion/time/engagement separation; targeted common-task attempts and
controlled hint studies could supply information the standings lack. The report
also distinguishes problem difficulty, team ability and rank performance, and
proposes useful evidence/uncertainty annotations for sparse problems. Sources,
input hashes, limitations and concrete checks are included. This task changed
documentation only; no model gain was measured, ratings regenerated, or paid
inference dispatched.

### Calibration and TabFM assessment (2026-09-06)

The strategy document now includes a [calibration/TabFM follow-up](rating_improvement_strategy.md#calibration-and-googles-tabfm-2026-09-06-follow-up).
The current saved-record map comparison reproduces **246.9061 affine / 245.4277
gym-shaped CF LOCO RMSE**, with 185 anchors across 15 contests. Their raw
difficulty range is [1177.9, 2936.1]; 94 fitted appearances lie outside it.
Google's TabFM is recommended for a bounded research comparison as a conditional
residual correction using fit/evidence features, with simple calibration and
regularized-regression controls. Its potential value is learning when the scalar
fit needs correction; neither synthetic pretraining nor a lower development
error establishes regional transfer, probability calibration or valid intervals.
The report specifies contest-grouped selection, timing of feature availability,
context-sampling checks and the current weights' research-use restrictions.
At that time no TabFM inference or model changes were made. README's existing
strategy link continues to point to the expanded assessment.

### Nested calibration residual control (2026-09-08)

`arch_b.calibration_experiment` now records a bounded, research-only comparison
on the same 185 CF anchors in 15 contest-held-out folds. The outer contest's
labels are absent from every map and inner selection step; explicit canonical
shared tasks are purged from matching training folds. The prespecified features
are raw survival difficulty, binary-minus-survival difficulty, conditional fit
SE, solve rate, log field size, log median solve time, and a missing-time flag;
there are no IDs, regions, names, or calibrated-output inputs. Inner
contest-grouped selection covers ridge alpha {0.1, 1, 10} and residual shrinkage
{0, .25, .5, .75, 1}.

The refreshed baseline-only artifact reports **246.9061 raw affine / 245.4277
locked gym shape / 229.6269 nested ridge residual** CF LOCO RMSE. Ridge wins over
raw in 11/15 outer contests and gym in 12/15. The four losses to raw are CF
1949 (+10.6), 2041 (+29.5), 2045 (+2.7), and 2052 (+11.8); the three losses to
gym are instead 1938 (+20.0), 1949 (+8.7), and 2041 (+55.7). Per-region
raw/gym/ridge RMSE is Asia Pacific 219.9/211.5/208.8, Europe
332.3/335.4/311.9, and Northern Eurasia 207.0/212.6/179.7. The OOF anchor-order
check has 2 reversals among 1,064 within-contest pairs and CF concordance 968
raw -> 969 ridge; it is distinct from the non-OOF full-fit diagnostic. Cached,
non-OOF transfer proxies are mixed: gym pooled .9691 -> .9769 (n=667), gym EC
.9774 -> .9817 (n=230), Kattis .7955 -> .7848 (n=427), and AOJ .5685 -> .5587
(n=45); the non-anchor gym/Kattis subsets show the same directions. The full
detail, provenance hashes, and explicit non-OOF diagnostics are in
[calibration_experiment_report.md](calibration_experiment_report.md) and
`output/calibration_experiment.json`.

This measures only the regularized control on the reused anchor set; it does
not establish regional transfer, probability calibration, interval coverage, or
a production replacement. A pinned-weight, seven-feature CPU smoke completed
on synthetic 170-train/15-test inputs, but has no TabFM CF score. The full
185-anchor comparison is **not run** because the user explicitly deferred it;
the cached baseline-only artifact remains unchanged. With eight threads its
smoke load was 8.772 s and fit/predict 12.925 s (four threads: 21.820 s), while
one process reached 12.6 GiB; the 225-call nested comparison is estimated at
45–55 minutes. The verified runtime is TabFM 1.0.1 from official source
`d8678b6` with torch 2.12.1+cpu. The existing survival, binary, and calibrated
output artifacts were not regenerated.

The eventual isolated command is:

```bash
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 \
TABFM_CHECKPOINT_DIR=/home/dedibeat/.cache/tabfm_runtime/checkpoints/google-tabfm-1.0.0-pytorch-77cb9cc1b4fd3a9c77fbb9552c218200bb4dab83 \
/home/dedibeat/.cache/tabfm_runtime/venv/bin/python -m arch_b.calibration_experiment --tabfm --tabfm-license-ack
```

The local checkpoint contains `regression/model.safetensors` and
`regression/config.json`; the model SHA-256 is verified before loading and the
completed-run artifact records actual model/config hashes. It does not silently
download a model, and it must not overwrite the baseline-only artifact unless the
deferred run is deliberately authorized.

### Calibration selected-fit read-only diagnostic (2026-09-08 follow-up)

No new model variant or hyperparameter search was run; existing selected fits
were reproduced. Reconstructing all 15 saved outer ridge fits from the saved
selections and rows reproduced the saved OOF ridge predictions within
**4.55e-13 CF points**. In the standardized residual
fits, binary-minus-survival is positive in 15/15 folds, conditional fit SE is
negative in 15/15, solve rate is positive in 15/15, and log field size is
negative in 15/15. This is not causal or unique-feature evidence:
binary-minus-survival and solve rate correlate -0.95 across the anchor table,
with further correlation among the prespecified inputs.

Across the 185 saved OOF predictions, ridge-minus-raw correction variance is
**43.6% between held-out-contest means and 56.4% within contest**. Thus the two
changed orders among 1,064 pairs do not imply a pure contest-offset correction;
nor would a per-contest offset learned from held-out CF labels be deployable.

The bounded next development direction is prespecified, same-protocol grouped
ridge ablations separating estimator disagreement, non-time evidence, and
timing features, plus region/source transfer stress checks explicitly labelled
development diagnostics. They require fresh frozen confirmation before a
deployment decision; this pilot has no fresh frozen confirmation set. These diagnostics do not
claim ablation results, prove that the disagreement feature caused the gain,
authorize the deferred full TabFM comparison, or justify an underlying-fit
rewrite.

### Frozen calibration feature-group ablation (2026-09-08)

The approved research-only ablation is recorded in
`output/calibration_ablation.json`, with the frozen protocol in
[`calibration_ablation_plan.md`](calibration_ablation_plan.md). It retains
`raw_b` in every ridge residual fit and separately tests disagreement (D),
non-time evidence (E), and timing (T), including all seven nonempty D/E/T
bundles. Nested 15-contest LOCO RMSE is **246.9061 raw / 245.4277 gym / 241.7094
D / 238.2049 E / 247.3457 T / 226.5661 DE / 245.2137 DT / 241.1893 ET /
229.6269 DET**; the inner-only adaptive selector also scores **226.5661** and
selected DE in every outer contest fold. The retained DET control reproduces
every old ridge OOF prediction exactly and its selected settings exactly.

The separate calibration-label leave-one-region-out diagnostic gives **248.6523
raw / 246.0305 gym / 243.4531 D / 237.5236 E / 248.6584 T / 225.7640 DE /
243.2424 DT / 242.2078 ET / 228.3597 DET / 226.9881 adaptive**. Its adaptive
choice is DET (Asia Pacific) and DE (Europe, Northern Eurasia). This holds only
completed-contest standings/raw fits fixed while excluding all labels from the
held region before baselines, preprocessing, and inner contest selection; it
is a calibration-label transfer stress check, not a future-contest forecast.

Both protocols are exploratory development on the reused anchors, not fresh
confirmation or a production-promotion decision. No TabFM import, download, or
run occurred, and the existing production artifacts and baseline experiment
artifact remain unchanged.

The concise result and transfer caveats are in
[calibration_ablation_report.md](calibration_ablation_report.md). Full-anchor
transfer refits are explicitly non-OOF and mixed: DE improves cached pooled gym
Spearman (.9691 to .9780; n=667) but is lower on Kattis (.7955 to .7760; n=427)
and AOJ within-contest (.5685 to .5642; n=45). Removing only canonical anchor
tasks gives non-anchor gym/Kattis counts 659/416; the stricter whole-anchor
contest plus task purge gives 655/412, reproducing the historical reported
counts. These are distinct subset definitions, not confirmation of a global
replacement.

### Proposed experiment roadmap (2026-09-08)

[experiment_roadmap.md](experiment_roadmap.md) records proposed, not-run
diagnostics and later research directions. It recommends retaining DE unchanged
as the candidate for a prospective confirmation design, distinguishes OOF,
full-refit, and fresh-confirmation evidence, and requires provenance/identity/
context audits before any model change. It does not authorize a model or data
run, production promotion, or the explicitly deferred TabFM comparison.

### Autonomous DE prediction audit and anchor influence (2026-09-10)

The request to work autonomously on prediction improvement led to a bounded
execution of the roadmap's correction/source audit and calibration-label
contest-influence study. The protocol was written before execution in
[calibration_audit_plan.md](calibration_audit_plan.md); implementation is
`arch_b.calibration_audit`, with full findings in
[calibration_audit_report.md](calibration_audit_report.md) and research predictions
in `output/calibration_audit.json`. No candidate features or production map changed.

All 3,159 survival/binary problem appearances agree with the joint loader and
cached sources on task/title/solve-count/field-size provenance. All 185 anchors
have unique cached contest-scoped CF matches. Previous artifact input hashes
match, and OOF prediction replay differs by at most 7.74e-12 CF points. The
baseline remains **246.9061 raw / 245.4277 gym / 226.5661 DE** LOCO RMSE.

Each of the 15 CF anchor contests was removed in turn, with its canonical tasks
purged before rerunning nested DE-only selection on the remaining cohort
(210 outer fits). DE beats raw and gym in all 15 deletions. Comparing to the
original OOF predictions on exactly the same remaining rows, refitting changes
DE RMSE by **-2.91 to +1.80 points**, below the frozen 5-point audit threshold.
Individual predictions can still move by 117.9 points. This is calibration-label
sensitivity with the raw fits fixed, not independent replication or uncertainty.

The largest-correction audit selects 23 unique OOF anchors and separately saves
all 3,159 full-refit rows with source links, features, predictions, and marginal
training-range flags. **1,840 appearances (58.2%) exceed at least one DE feature
range**, including 1,610 outside the anchor field-size range of **77–323 teams**;
only 94 exceed the raw-difficulty range. Seven of the ten largest full-refit
corrections are in Aobayama's 50-team field, with a maximum +534.3-point shift,
although its raw difficulties are within anchor support. These are extrapolation
diagnostics, not proof of errors or calibrated risk probabilities.

Both Luxor appearances of all five shared tasks pass cached identity/title
checks. Riddle of the Sphinx's gap is 5.1 raw / 101.0 DE, and Turning Red's
is 66.0 / 145.3; external task-version/context equivalence remains unverified.
No source defect was reproduced, so no data or identity correction was made.
Fresh confirmation labels, actual recorded durations, and adjudicated roster
identity remain missing. The next confirmation design needs small/large fields
and other evidence-feature regimes in addition to regions/raw-difficulty bands.

All 64 tests pass, including label-mutation leakage checks, task purges,
deterministic example selection, training-only support flags, stale provenance,
and finite predictions. Prior experiment and production artifacts are unchanged;
TabFM remains deferred. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.calibration_audit`.

### BigQuery and Google Cloud TabFM plan (2026-09-10)

The user requested a cloud experiment plan, specified **BigQuery and a $10
total spending limit**, and pointed out native TabFM availability through
`AI.PREDICT`. [tabfm_cloud_plan.md](tabfm_cloud_plan.md) now plans that managed
route directly, superseding the initially considered CPU VM. Official Google
Cloud documentation confirms Preview compute billing and token pricing starting
October 30, 2026. No VM, GPU, or checkpoint deployment is needed.

The plan preserves seven features, task-purged nested contest folds, residual
shrinkage selection, and 225 inference calls, comparing managed TabFM against
raw/gym affine, DET ridge, and the newer DE ridge OOF control. The managed API
exposes no checkpoint/seed/ensemble/context controls in its documented signature,
so the result must be labelled as a managed-backend comparison, not a replay of
the pinned local checkpoint. A separate bounded wrapper remains to be implemented.

The Preview plan limits all query jobs to 300, each capped at 1 GiB, for about
$1.84 query compute before free allowances/credits at the provisional
`us-central1` rate, plus a small storage allowance. It specifies job accounting,
alerts, a stop margin, table expiration, and cleanup within the user's $10
ceiling. The project, credit details, region requirements, and Preview access
remain unverified; cloud execution is pending.

Read-only checks matched the 11 baseline input hashes and experiment-source
hash. The exact nested schedule contains 36,260 training-row appearances and
2,775 prediction-row appearances, corresponding to $0.01603025 per ensemble
in future model-token charges, excluding query compute. Ensemble count is
unexposed, so that is an illustration rather than a service quote. There are
184 distinct seven-feature vectors among 185 anchors; the plan therefore
requires verified prediction-ID passthrough instead of joining on feature values.

`gcloud`/`bq` are installed. No paid queries, cloud resources, TabFM inference,
or production changes were made. README links the plan, and prior experiment
artifacts remain unchanged. The separate local-checkpoint run stays deferred.

### Managed BigQuery TabFM execution (2026-09-10)

The planned managed experiment was executed in `test-gemeni-501216`,
`us-central1`, after a native smoke test verified finite prediction-ID
passthrough for two identical feature vectors. A project-scoped, gross-spend
budget alert was created at $2/$5/$8; every executable query was dry-run first
and capped at 1 GiB. The seven-feature, task-purged nested protocol completed
all **225** calls with a persistent deterministic job ledger. It records
4,718,592,000 billed bytes (4.395 GiB); the dedicated dataset was deleted after
local archival.

Managed TabFM residual OOF RMSE is **231.2865 CF points**, versus 246.9061 raw,
245.4277 gym, 229.6269 DET, and **226.5661 DE**. It improves the affine controls
but loses to DE, so this is a negative research pilot: no production calibration,
rating, feature, or backend search changed. The result is
`output/calibration_tabfm_bigquery.json`; the concise report is
[tabfm_bigquery_report.md](tabfm_bigquery_report.md). The local pinned-checkpoint
run remains separate and deferred.

### TabFM / DE audit and shipped-fit update preparation (2026-09-10)

[shipped_fit_update_plan.md](shipped_fit_update_plan.md) records the audit and
concrete calibration-release dependencies at `b935754`.
`arch_b.shipped_fit_audit` verifies prior provenance, reconstructs the entire
managed manifest, and replays all 225 archived responses, inner shrinkage choices,
and outer predictions exactly. The experiment ledger accounts for 4,718,592,000
billed bytes; the separate two-job smoke adds 41,943,040 bytes. This checks local
evidence, not an independent invoice or remote-cleanup confirmation. DE's nested
selection and full refit reproduce the existing artifacts; its full-anchor
settings remain alpha=1, lambda=1. No new inference or model search occurred.

Development RMSE remains **245.4277 shipped gym / 226.5661 DE / 231.2865 managed
TabFM**. DE wins 9/15 contests against each, while TabFM is slightly better on
the pooled Europe anchors. There is no fresh-confirmation or significance claim.

The new research artifact `output/shipped_fit_audit.json` stages all 3,159
appearance-level DE values beside the actual shipped ratings, using the existing
[800,4000] bounds and one-decimal display policy. There are 259 rated contests;
the loader's 260th entry, contest 1120, has no rated problems. Proposed changes
average +75.98 points, have median absolute change 113.9, and move 1,737 ratings
by at least 100 points. Aobayama 1965 H moves 2151.5 -> 2711.4 (+559.9). These
are comparisons with shipped gym calibration, not the earlier raw-affine
correction audit. The display comparison has 105 changed orders/new ties among
18,142 previously non-tied within-contest pairs; 1,840 appearances remain outside
at least one anchor feature range. No support fallback was introduced.

The update plan identifies duplicated scalar-map construction in calibration,
viewers, UCup export, virtual calculation and medals. DE has no defined
problem-feature vector for team abilities or medal bars, and existing gym-based
uncertainty fields cannot simply accompany DE predictions. Current raw-order
metric guards also do not test a DE postprocessing layer. Fresh confirmation,
extrapolation/uncertainty/badge policies and downstream app integration remain
release requirements. The managed runner's feature-only run ID and recovered
load jobs also require content binding before any changed-label rerun; the
current archived manifest matches, so this is a future reuse defect rather than
evidence that the completed pilot used wrong inputs.

All **72 tests pass**, including five new offline replay corruption/missing-input
checks. Every existing output's hash is verified unchanged before the audit
artifact is written. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.shipped_fit_audit`;
the gitignored original managed archive is required and missing files cause an
error rather than new cloud inference. Production fit, calibration and exports
are unchanged; the audit prepares a reviewable update but does not promote DE.

### Explaining DE / TabFM and proposing next work (2026-09-10)

[calibration_interpretation.md](calibration_interpretation.md) explains the
existing results and records the user's requested future plan. The reproducible
diagnostic `arch_b.calibration_interpretation` reconstructs the selected DE
coefficients and saves `output/calibration_interpretation.json`; it performs no
new candidate search, production refit, or TabFM inference.

The full DE fit expands to approximately **0.934742 survival_b + 0.876768
binary_b + evidence terms + intercept**: its difficulty component is a roughly
52/48 survival/binary blend with rescaling. Disagreement/SE/solve-rate/field-size
coefficient signs are stable across all 15 outer folds, but they are correlated
inputs, not independent causal effects. Disagreement and solve rate correlate
**-0.952** on anchors. For Aobayama's 12 Grid they instead reinforce the
correction, contributing +155.7 and +282.0 points relative to anchor means;
small field size contributes +70.5 of the +531.4 raw-affine correction.
This highlights joint feature support, beyond individual range flags. Across
all appearances the disagreement term contributes +60.06 of the average
+73.35 DE-minus-raw shift. OOF correction variance is 40.8% between contest
means and 59.2% within contests.

The survival MAP first-order condition implies
`SE(b) = [k/s² + (b-MU0)/(s*sigma_b²) + 1/sigma_b²]^(-1/2)` for interior,
unweighted default fits, where k is solve count. This reconstructs saved SEs
with median error 0.0247 and maximum 0.0508, consistent with rounding and finite
convergence. SE therefore mainly contributes nonlinear solve-count information
to E; including it as a predictor does not calibrate prediction uncertainty.

Managed TabFM used seven features; the matched DET ridge control is 229.63
RMSE versus TabFM 231.29, while five-feature DE is 226.57. Their OOF correction
correlation is .722; selected TabFM shrinkages are .75 in nine folds and .5 in
six. A descriptive paired 15-contest bootstrap of fixed predictions (20,000
resamples, seed 20260910) gives 2.5–97.5 percentile RMSE-difference ranges
**[-34.45,-2.27] DE-minus-gym**, **[-13.94,+6.48] DE-minus-TabFM**, and
**[-9.76,+7.63] DET-minus-TabFM**. These do not refit or adjust for benchmark
selection and are not fresh confirmation. TabFM has not demonstrated a gain;
its inferiority to ridge is not established.

The proposed sequence is a fixed-panel decomposition of estimator disagreement,
three prespecified leave-one-E-feature-out controls, fresh confirmation covering
joint feature regimes and regions, then coordinated opt-in integration and
scope-limited promotion if supported. Missing durations, adjudicated context,
fresh labels and uncertainty remain explicit. These are proposals only; all
earlier experiment/production artifacts remain unchanged. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.calibration_interpretation`.

## Online results, slot rules and regional gold chances (2026-09-27)

**Provenance.** A ChatGPT session (shared link, reviewed 2026-09-27) built an
online/slot-rule data layer, bronze-cutoff tweak, online→regional mapping, a
gold model, NUM probabilities, a provisional Hong Kong model and a rating-fit
comparison, but none of it reached GitHub (every push returned 403) and the
share omits all code and tool output. That work was **rebuilt from official
sources**, not copied; GPT's numbers are not reused.

**Data layer** (`scripts/build_ec_online_data.py` → `data/ec_online/`; raw
downloads cached in git-ignored `data/ec_online_cache/`):

- `online_teams.csv` — every team of both official online rounds 2022–2026
  (22,701 rows) from the icpc.pku.edu.cn ranking PDFs. Layouts differ by year
  (centred wrapped cells in 2022–23, left-aligned tables since 2024), so the
  parser reads word coordinates (`pdftotext -tsv`), finds column boundaries at
  the x crossed by the fewest words, anchors rows on the solved-count column
  (2023–24 list zero-solve teams without a rank) and assigns wrapped name
  fragments to rows by a DP that keeps each cell contiguous and centred on its
  row. Every ranked school parses to a school in the official school ranking.
- `online_schools.csv` — per-round and combined school rankings (the combined
  ranking drives slot rules; NFKC fixes the 2026 PDF's CJK radical code points).
- `online_rosters.csv` — registration lists (报名公示) with members for
  2022–2024. **2025–2026 lists exist only on uep.pintia.cn (PTA)**; an
  automated fetch was not possible in this session, so 2025 links rely on names.
- `regional_teams.csv` — every team of the 28 ordinary 2022–2025 regionals from
  XCPCIO: official flag (explicit `group`, or the per-team `official` field on
  47th/48th boards), standings recomputed from `run.json` (ICPC penalty, CE not
  counted), official rank and medal. Medal counts come from the board config,
  which equals ⌈10%⌉ of official solvers for 2024–25 and most of 2023; the 47th
  boards carry a constant 35/70/105 placeholder, so 2022 uses the 10/20/30%
  rule. Solved counts agree with QOJ for ~99% of name-matched teams.
- `slot_rules.json` — hand-encoded 2023–2026 site notices: rank bands on the
  combined school ranking, the "≥3 teams in the top N" clause, per-school caps,
  capacity and approximate non-online quotas. Checked against the one published
  per-school allocation (Shanghai 2025): the band rule reproduces all 178
  schools' online slots exactly. 2022 notices describe online-held contests with
  different rules and are marked, not encoded. Hong Kong/Macau allocate by
  registration (one team per non-local school, ranked by online school rank if
  oversubscribed).

**Linking.** School + team name links only 45–56% of official regional teams
(teams rename after the online rounds); adding roster matches (≥2 shared
members at the same school) raises 2022–2024 to 78–86%. Remaining teams mostly
entered through non-online quotas. 2025 stays name-only (~54%). Hong Kong/Macau
use English names and are unlinked.

**Model (`arch_b.online_gold`).** Online strength `x = −mean(log online rank)`
over the rounds entered (beat best-round and percentile variants overall;
percentiles drift because round sizes vary 1,745–2,500). A site's *rules line*
is the strength of the G-th best rule-admitted team (each school's best k
teams, k = rank-band + team-count slots, capped; G = 10% of official capacity).
`logit P(gold) = c + b·x + d·line`, fit on linked official mainland teams
2023–2025 (4,962 rows).

**Held-out results** (log loss; Δ vs online-only with contest-bootstrap 95% CI;
numbers in this section predate the 2026-09-27 school-name/tie-break fixes —
updated values are in the next section):

| model | 2024 (1,938 teams) | 2025 (1,282 teams) |
|---|---|---|
| online only | 0.1658 | 0.1614 |
| + same-site history | +0.0001 [−0.0008, +0.0010] | **+0.0046** [+0.0005, +0.0097] |
| + rating-fit CF gold bar history | −0.0000 [−0.0006, +0.0005] | **+0.0008** [+0.0001, +0.0017] |
| + rules line | **−0.0004** [−0.0008, −0.0000] | **−0.0013** [−0.0028, −0.0000] |
| + rules line, quota-adjusted (ρ from earlier seasons; shipped) | **−0.0005** [−0.0011, +0.0001] | **−0.0016** [−0.0044, +0.0000] |
| + oracle line (actual attendees) | −0.0017 [−0.0031, −0.0008] | −0.0044 [−0.0114, +0.0003] |

Online strength dominates (held-out gold rate ≈ prediction within ~15 points
in every rank bin). Slot rules add a small, consistent gain, largest where a
site's rules changed (Shenyang 2025: two-slot band 1–50 → 1–100); the fitted
line coefficient is ~20–45% of the strength slope because the nominal field
ignores which sites schools actually choose. Site history and the rating fit's
historical CF bars do not help and hurt in 2025, so they are not combined. A
quadratic strength term was mixed (worse 2024, better 2025) and not adopted.

**Rating fit vs online evidence.** With a shared slope and one intercept per
contest, each regional gets the online rank at which gold is a coin flip.
Across 16 regionals with a CF gold bar, Spearman with the bar is **−0.50**
(agreement; ≈ −358 CF points per unit log rank). The Shenyang swing is
corroborated by data that never touch the ratings: 2024 needed ≈ online #83
(bar 2703), 2025 ≈ #151 (bar 2382, easiest of all). Largest fit-minus-online
disagreements: Kunming 2024 **+151** (fit says much harder), Nanjing 2024
**−118**, Shenyang 2024 +92, Shanghai 2025 −90 — candidates for a
contest-level fit-bias audit, not proven bias (online-to-onsite form and
unlinked quota teams also move the online estimate).

**Quota entrants (measured, not assumed).** Seats the online bands do not
fill go to invitational, WF, host, provincial, girls' and wildcard teams. Per
2023–2025 mainland regional, each school's band slots were given to its
strongest-online teams present and the rest counted as quota entrants
(`quota_split`). Quota entrants win gold at **ρ ≈ 0.44** of band teams' rate,
stable from earlier seasons (0.44 from 2023 alone, 0.40 from 2023–24, 0.44 from
all); their share of golds is 21%/21%/25% by season, while per contest it is
noisy (9–37%, relative rate 0.16–0.89 on 3–15 quota golds), so ρ is pooled,
not per site. Band teams keep G·(1−q)/(1−q+ρq) of the G golds (q = planned
quota seat share = 1 − band slots/capacity); ρ = 0 was the first shipped line
(quota teams never win gold), ρ = 1 the online-slots-only alternative that
reproduces the ChatGPT order. The ρ-adjusted line improves on the ρ = 0 line in
both held-out seasons (table above; intervals just touch zero) and ships.

**2026 forecast** (`output/online_gold.md`, ρ = 0.443): easiest → hardest
Shenyang (line ≈ online #89) > Wuhan (#79) > Xi'an = Shanghai (#74) ≈
Nanchang (#73) > Chengdu = Nanjing (#68: one slot per top-160 school plus the
team-count clause). A team ranked #100 in both rounds: 69% / 65% / 62% / 59%.
Robust across ρ = 0, 0.44, 1 and GPT's order: Shenyang/Wuhan near the top,
Chengdu/Nanjing last; Xi'an/Nanchang move with ρ because of their ~100
invitational seats. The rating-fit chooser (`arch_b.medal_predict`) ranks
Wuhan hardest from its single 2025 contest; its city history did not help
held-out gold prediction.

National University of Mongolia (combined rank 128, one band slot at every
mainland site), conditional on attending: NUM-R^3 (online #544/#349) Shenyang
5.3%, Wuhan 4.5%, Xi'an/Shanghai/Nanchang 4.0%, Chengdu/Nanjing 3.6%; NUM-MNM
0.9–1.4%; the rest ≤ 0.5%. NUM's own record in `regional_teams.csv` points to
the unmodelled site: every NUM silver since 2022 came at Hong Kong/Macau
(official ranks 22–39 of 82–149 teams; 2025 N^3 30th with the gold line at
13th), while its mainland best is bronze (Hangzhou 2024 116th; Nanjing/Wuhan
2025).

**Pre-existing bugs found (not fixed here).** (1) `scripts/build_xcpcio_official.py`
treats every XCPCIO team as official when a board has no `group` field, but the
47th/48th boards carry a per-team `official` flag (e.g. Xi'an 2022: 476 official
+ 46 star, cache uses 522), so `arch_b.medals` includes star teams in 2022–23
medal cutoffs. (2) QOJ 1784 (Xi'an 2023) is mapped to XCPCIO
`48th/xian-invitational` instead of `48th/xian`; its medal bar is computed on a
34-team "official" field (4 golds, bar 2321). (3) `arch_b.medals` excludes QOJ
1197 (EC-Final 2022, named "ICPC") as an online qualifier; latent today because
1197 has no XCPCIO data.

**Limitations.** No 2025/2026 rosters (PTA); Hong Kong/Macau not modelled;
probabilities assume the team attends and the rest of the field follows the
rule-admitted pattern; 2022 excluded as an online-held regime.

Run: `python3 scripts/build_ec_online_data.py` (needs `pdftotext`, network) then
`python3 -m arch_b.online_gold [--school NAME]`.


## Quota entrants: who entered each regional on a quota seat, and why (2026-09-27)

**Question.** The online-gold model treats quota entrants as one pooled group
(ρ ≈ 0.44). Which teams are they, through which channel did each get its seat,
and what patterns do they show?

**Evidence** (`scripts/build_quota_evidence.py` → `data/ec_online/quota_evidence.json`).
Site notices (read in full for 2023–2025) list the non-online channels:
World Finals schools +1 (last three WFs), recent host and problem-setter schools
+2, invitational medal schools +1 (Xi'an, Kunming), non-mainland schools +1,
provincial/local contributors +1–2, girls' teams, and leftover wildcard
rounds. One official source per channel:

- WF schools: 46th/47th from the XCPCIO WF boards (English names mapped to
  Chinese), 48th/49th verbatim from the 50th Xi'an notice. 2023 uses 46th–47th
  (45th not on XCPCIO).
- Hosts: 2025 verbatim from the same notice; 2023–2024 from notices' venue or
  signature lines; a school counts in its hosting season and the next ("近二届").
  Not stated anywhere: 2023 Xi'an/Jinan and 2024 Chengdu hosts, and every
  problem-setter school.
- Invitational medal schools from XCPCIO: Xi'an 2023 (122; the notice says 124)
  and Kunming 2024 (98, exactly the notice's count). The 2025 Shaanxi
  invitational (used by Xi'an 2025) is not on XCPCIO.
- Local: official schools on the site province's XCPCIO provincial board
  (none for Anhui/Yunnan; Sichuan's board includes some guest schools).
- Ground truth: Shanghai's published per-school lists for 2024 and 2025
  (online seats, reward seats, total). These were found by crawling the
  icpc.pku.edu.cn notice index; they are the only per-school allocations
  published centrally.

**Method** (`arch_b.quota_teams`). Each school's band slots
(`online_gold.school_slots`) go to its strongest-online teams at the site; the
rest are quota teams. Quota teams take the school's channels in the order host
(2 seats), WF, invitational, non-mainland, local; girls' flag first; anything
left is *unexplained*. Which of a school's quota teams uses which channel is a
convention; school-level counts are not. Output: one row per official team
(`output/quota_teams.csv`, 6,473 rows) and `output/quota_teams.md`.

**Validation (Shanghai).** Inferred band slots equal the published online
seats for every attending listed school (151/151 in 2024, 159/159 in 2025;
140/146 and 145/152 before the name fix below). WF + host evidence explains
34/35 and 34/36 published reward schools; the rest are 齐鲁工业大学 2024 (0
online + 2 reward, probably a 2023 host) and 北京理工大学/杭州电子科技大学 2025
(2 reward each, presumably setters). Every Shanghai quota team is accounted
for: 2024 = 40 on published reward + 64 from schools not on the list + 39
above their school's published total (the later wildcard rounds); 2025 = 41 +
48 + 38 (sum 127 vs 126: 西北工业大学 sent 5 teams against a capped total of 4
from 2 online + 3 reward, so one team counts in both columns). So roughly 70% of
Shanghai's quota seats were never in the first-round list at all.

**Patterns** (2023–2025 mainland regionals, 18 contests):

| group | teams | gold rate | vs band | median online rank |
|---|---|---|---|---|
| band | 3,954 | 12.8% | 1.00 | 425 |
| WF school extra team | 371 | 18.9% | 1.47 | 360 |
| host extra team | 190 | 11.6% | 0.91 | 719 |
| invitational medal | 191 | 4.2% | 0.33 | 815 |
| non-mainland | 25 | 4.0% | 0.31 | — |
| local / provincial | 294 | 1.0% | 0.08 | 1,032 |
| unexplained (wildcards etc.) | 1,446 | 2.6% | 0.21 | 925 |
| all quota | 2,519 | 5.6% | 0.44 | 853 |

1. Quota seats are large: 39% of official seats (24–51% per contest; the
   invitational sites Xi'an 2023 and Kunming 2024 are ~50%).
2. The pooled ρ = 0.44 averages two different populations. Elite channels
   (WF, host) beat or match band teams; mass channels (invitational, local,
   wildcard) win gold at 0.1–0.3× the band rate.
3. What decides whether a quota team contends is its **school**, not its
   channel: 127 of 142 quota golds (89%) come from schools ranked top-50 in
   the combined online ranking; schools ranked below 100 took 3 golds from
   1,315 quota teams (2 more from 81 teams of unranked schools), and schools
   with no band slot at the site took 4 golds from 1,074. Within top-50 schools, quota teams win gold at 17.7% vs 27.3%
   for their band teams (they are the school's 3rd/4th teams).
4. A handful of schools own the quota golds: 北京大学 32 of 35 quota teams won
   gold, 清华大学 15/17, 浙江大学 14/23 — 61 of 142 (43%) from three schools.
   Host extra teams of non-elite hosts almost never do (南京航空航天大学 0/28,
   杭州师范大学 0/30, 西北工业大学 0/37 over all its quota teams).
5. Channel mix is site-specific: invitational sites fill ~90–100 seats from
   the spring invitational; Hangzhou/Nanjing/Jinan give 18–31 seats to local
   schools; every site gives WF schools ~16–26 seats; wildcard/unexplained is
   the largest group everywhere (Xi'an 2025's 155 includes the ~120 invitational
   seats whose board is missing).
6. Predicting each contest's quota golds leave-season-out (MAE, golds per
   contest): pooled ρ 2.04, by channel 1.78, by school combined online rank
   (≤50 / ≤100 / >100 / none) **1.58**, by the team's own online rank 2.18
   (a third of quota teams never link to an online team). A quota adjustment
   for the rules line would do better by counting a site's quota seats from
   top-50 schools (WF/host seats) than by applying one ρ; not implemented here.

**Fixes to `arch_b.online_gold` found on the way** (both affect quota labels):
(1) `norm_school` stripped parenthesised campus names, merging distinct schools
(哈尔滨工业大学 / (威海) / (深圳), 香港中文大学 / (深圳), 中国石油大学 北京/华东,
山东大学 / (威海), …) and pooling their slots and online teams. It now keeps
the qualifier, strips only 齐鲁工业大学's "(山东省科学院)" long form, and folds a
few traditional characters (香港中文大學). (2) Roster-vote ties in
`link_regionals` were broken by set order, so ρ varied 0.440–0.444 with
`PYTHONHASHSEED`; ties are now broken deterministically. Effect on the shipped
online-gold outputs (regenerated): ρ 0.443 → 0.441; quota-adjusted rules line
Δ log loss 2024 −0.0005 → −0.0003 [−0.0007, +0.0001], 2025 −0.0016 →
−0.0015 [−0.0041, −0.0001]; 2026 order unchanged (Shenyang #89 > Wuhan #79 >
Xi'an #75 > Shanghai #74 ≈ Nanchang #73 > Chengdu = Nanjing #69); a team at
online #100 loses 1–2 points everywhere; NUM-R^3 now 3.4–4.8% (Shenyang
highest). NUM itself did not enter the online rounds in 2023–2025, so its
regional teams in those seasons are correctly non-mainland/wildcard quota
entries.

**Gaps.** No per-school allocation outside Shanghai; setter schools, three
host schools, the 45th WF list and the 2025 Shaanxi invitational are missing;
Hefei/Kunming have no provincial board; Hong Kong/Macau are excluded (their
fields are registration-based).

Run: `python3 scripts/build_quota_evidence.py` (network, `pdftotext`) then
`python3 -m arch_b.quota_teams`. Tests: `tests/test_quota_teams.py`.


## School-rank quota predictor and a TabFM gold table (2026-09-27)

**Request.** Implement the best quota-gold predictor found above (grouping
quota teams by school combined online rank) and prepare rich data for TabFM
prediction.

### School-rank quota model

The per-contest check used the actual quota teams, which are only known after
registration. A forecast needs the number of quota teams from top-50 schools
*before* registration. Candidates were tested leave-season-out. The best is
the top-50 schools' **WF/host entitlement**: each top-50 school's WF + host
seats, capped by its privileged cap minus band slots (`quota_teams.elite_entitlement`),
times a ratio fit on earlier seasons. Forecast vs actual top-50 quota seats:
MAE 4.0, correlation 0.71. The alternatives did worse: share of planned quota
seats MAE 10.3, headroom 7.5, linear fits 6.5–8.2.

`quota_teams.school_rank_quota_model` (all 2023–2025 data): top-50 quota teams
win gold at **ρ_top50 = 1.38×** the band rate, other quota teams at **ρ_rest =
0.065×**, pooled 0.44; top-50 schools fill **κ = 1.39** quota seats per
entitlement seat. `online_gold.rules_line(..., top50_seats, rho_top50)` gives
band teams `G(1−q)/(1−q + ρ_top50·q50 + ρ_rest·(q−q50))` golds, and reduces to
the pooled formula when `top50_seats = 0`.

- **Quota golds per contest, before registration** (leave-season-out): pooled
  rate × planned quota seats MAE 2.52 (corr 0.44) → school-rank model **1.58**
  (corr 0.25). It fixes season-level errors, but its within-season site
  differences are weak: the entitlement is mostly site-independent within a
  season.
- **Held-out gold prediction** (`rules_line_school_rank` variant, Δ log loss
  vs online-only): 2024 −0.00015 [−0.00038, +0.00010], 2025 −0.00166
  [−0.00415, −0.00003]. Paired against the shipped pooled line: 2024
  **+0.00018 [0.00000, +0.00038] (worse)**, 2025 −0.00014 [−0.00057, +0.00010],
  driven by Xi'an alone. The better quota-gold count does not become better
  gold probabilities: the line's coefficient is small and noisy.
- **Decision:** the 2026 forecast keeps the pooled line (numbers unchanged)
  and prints the school-rank line beside it. The school-rank lines are 0–3
  online ranks deeper (Shenyang 86.9, Wuhan 79.3, Xi'an 73.5, Nanchang 73.0,
  Shanghai 70.9, Chengdu/Nanjing 65.8). The order is the same except that
  Shanghai drops below Nanchang.
- **Evidence added for 2026:** the 51st Xi'an notice lists the 50th WF schools
  (16) and the 2026 host schools (11); 2026 counts WF editions 48–50
  (`quota_evidence.json`). 2023–2025 quota labels are unchanged.

### TabFM gold table (`data/tabfm_gold/`, not run)

`AI.PREDICT` docs, re-read 2026-09-27, now allow **up to 50 feature columns**
(the 2026-09-10 plan quoted 20). A BOOL or STRING label makes it classify and
return per-class probabilities (≤10 classes). Every non-label column of the
training query is a feature, so ids must only appear on the prediction side.

`scripts/build_tabfm_gold_data.py` writes one row per official team of the 18
mainland regionals 2023–2025: 6,473 rows, 648 golds, ids `row_id`/season/site/
school/team. It has 45 features in four tiers, all known before the contest:

- **online (11):** the team's online strength, per-round ranks and solves, link
  method, the school's combined and best-round ranks, and its online depth.
- **rules (15):** band slots; WF/host/invitational/local/non-mainland flags;
  capacity, band seats, quota share, caps, two-slot band, team-count clause;
  rules line (no quota adjustment); top-50 entitlement; calendar position
  (XCPCIO dates).
- **history (9):** members' previous-season regional participation, golds,
  best medal and best rank %; the team's earlier regionals this season
  (strictly earlier dates; matched by ≥2 shared members or the same team name
  at the same school, since Xi'an 2023 has no member names); and the school's
  previous-season golds and medals.
- **registration (10):** band/quota, quota channel, the team's order in its
  school, the school's teams, field size, field linked share, the field's
  top-50 quota teams, the field's 10% strength line, the team's strength rank,
  and x minus the line.

Labels are `gold` (BOOL), `medal` (4 classes) and `rank_pct`. No feature uses
the contest's own results or a label-fitted season constant (ρ, κ). History
signal: a team with ≥1 member who won gold the previous season wins gold
43–60% of the time (base 5.5%); a gold at an earlier regional this season,
60%. `schema.json` is the BigQuery load schema. `predict.sql` has four calls:
all features and the 35 pre-registration features, each on train 2023 →
2024 and train 2023–24 → 2025. Each call returns `row_id, p_gold`.

**Local baselines** (`arch_b.tabfm_gold`; L2 logistic, log-rank features,
missing → 0 + indicator, L2 chosen by leave-one-contest-out CV inside the
training seasons; Δ log loss vs online-only, contest-bootstrap CI):

| model | 2024 (2,094 teams) | 2025 (2,231 teams) | 2025 linked / unlinked |
|---|---|---|---|
| online_only | 0.1705 | 0.1885 | 0.1613 / 0.2254 |
| online + rules line | −0.0000 | −0.0004 [−0.0007, −0.0000] | 0.1606 / 0.2254 |
| pre-registration (35) | −0.0019 [−0.0182, +0.0144] | **−0.0201 [−0.0336, −0.0045]** | 0.1663 / 0.1713 |
| all features (45) | +0.0046 [−0.0062, +0.0165] | −0.0064 [−0.0279, +0.0164] | 0.1764 / 0.1900 |

The rich features help the teams that cannot be linked to an online result
(1,507 of 6,473; 2025 links only 57% because its rosters are on PTA). A linear
model loses a little on linked teams, where online strength already
dominates. The registration tier hurts, likely because it shifts with the
seasons' link rates. These are the comparators a TabFM run must beat.
Expectations for TabFM: it can model the interaction (history matters when
online evidence is weak or missing) that the linear baseline cannot. The
2024 split trains on one season (2,148 rows).

**Before any cloud run:** a smoke query must confirm that NULL features are
accepted and how the BOOL label is spelled in `predicted_gold_probs` (`'true'`
assumed). The existing $10 BigQuery budget protocol (`tabfm_cloud_plan.md`)
applies. Four calls on ~6k rows are far below the earlier 225-call run. No
query was sent.

**Also changed:** `online_gold.link_regionals` returns the linked online key
(`online_key`), which the table builder uses for per-round features.

Run: `python3 scripts/build_quota_evidence.py`, `python3 -m arch_b.online_gold`,
`python3 -m arch_b.quota_teams`, `python3 scripts/build_tabfm_gold_data.py`
(network once for contest dates), `python3 -m arch_b.tabfm_gold [--score FILE]`.
Tests: `tests/test_quota_teams.py`, `tests/test_tabfm_gold.py` (99 pass).

### Managed TabFM run on the gold table (2026-09-27)

Run in `test-gemeni-501216` / `us-central1` from this session (gcloud user
login, revoked afterwards). Dataset `tabfm_gold_research` (7-day expiry) was
created, `teams.csv` loaded with `schema.json`, and then deleted after the run.
A smoke query (Hefei 2023 → 4 Chengdu 2024 rows, NULL features included)
confirmed that NULLs are accepted and that the BOOL label comes back as
`'true'`/`'false'` in `predicted_gold_probs`. Then the four `predict.sql` calls ran;
each was dry-run first and capped at 1 GiB billed. Each billed the 10 MiB
minimum (1.6–2.0 MB processed), 55–88 s, 0.9 M slot-ms in total. Total
≈ 50 MiB billed including the smoke query: well under $0.01 on demand, and
before the 2026-10-30 token pricing. The job ledger is
`output/tabfm_gold_predictions/ledger.json`; predictions are
`output/tabfm_gold_predictions/{all_features,pre_registration}.csv`.

Held-out log loss (Δ vs online-only, contest-bootstrap 95% CI):

| model | 2024 | 2025 | 2024 linked / unlinked | 2025 linked / unlinked |
|---|---|---|---|---|
| online_only (logistic) | 0.1705 | 0.1885 | 0.1649 / 0.2398 | 0.1613 / 0.2254 |
| best logistic (pre-registration) | −0.0019 [−0.018, +0.014] | −0.0201 [−0.034, −0.004] | 0.1669 / 0.1896 | 0.1663 / 0.1713 |
| **TabFM, all 45 features** | −0.0102 [−0.019, −0.004] | **−0.0325 [−0.045, −0.019]** | 0.1605 / 0.1579 | 0.1601 / 0.1506 |
| **TabFM, 35 pre-registration** | **−0.0218 [−0.033, −0.013]** | −0.0239 [−0.041, −0.005] | 0.1507 / 0.1222 | 0.1660 / 0.1628 |

TabFM beats online-only in both held-out seasons with intervals excluding
zero, beats the tuned logistic baselines, and, unlike them, improves on
linked teams as well. That is the online-strength × history interaction a
linear model cannot represent. Neither feature set wins both seasons: the
pre-registration set is best in 2024 (one training season), the full set in
2025. This is one managed-backend run with unexposed settings (checkpoint,
seed, ensemble count) and no repeat, so it is a research result. It does not
replace the shipped `online_gold` model, which predicts from online ranks
alone for 2026 teams. A 2026 use would need 2026 rows (history and rules
features exist before registration) and a pre-registered comparison.

### 2026 TabFM forecast (2026-09-27)

`data/tabfm_gold/forecast_2026.csv` has 20,251 rows: every 2026 online team
(2,893) at each 2026 mainland site, asking "gold chance if this team attends". It
uses 28 features: the 35 pre-registration features minus members' history and
earlier-regional results. Those can't be known before the season: 2026 rosters
are only on PTA, a same-name 2025 regional team exists for only 161 teams, and
no 2026 regional has been held. `forecast_2026.sql` backtests this feature set
on both splits, then trains on all 2023–2025 teams and predicts 2026. It ran
in `test-gemeni-501216`: three queries, 10/10/20 MiB billed. The dataset was
deleted and the login revoked afterwards. Jiangxi provincial boards were added
as Nanchang's local evidence. Nanchang's invitational board uses English school
names and marks official teams `icpc`, so it is recorded as a gap.

**Backtest of the 28-feature set** (Δ log loss vs online-only): 2024 −0.0125
[−0.021, −0.006], 2025 −0.0086 [−0.027, +0.014]. On linked teams, the only kind
in the 2026 grid: 2024 0.156 vs 0.165 (better), **2025 0.170 vs 0.161
(worse)**. Removing member and earlier-regional history removes most of
TabFM's advantage. Held-out calibration was good: teams ranked #141–280
online were predicted 19–21% gold and won 18–19%.

**Shift in the 2026 rows.** The grid contains teams that would never attend.
For online ranks #141–280, the 2026 rows come from schools with 3.6 top-100
teams on average, versus 1.6–1.9 in training. These are strong schools' 5th–10th
teams, which are capped out in reality. TabFM gives that band 34% gold. Keeping
each school's strongest `site_school_cap` teams (the report does this) lowers
it to 26%, still above the backtest. The remaining excess is mostly
Shanghai (34%). Its 2026 rules (1–50 ×2, 51–200 ×1, capacity 336) give a rules
line x of −4.45 and a band profile outside the 2023–2025 range, so TabFM is
extrapolating there.

**Result** (`output/tabfm_forecast_2026.md`, within-cap teams; TabFM /
online-gold model at online #100): Shanghai 64/60, Wuhan 63/63,
Shenyang 62/66, Xi'an 60/61, Nanchang 55/60, Nanjing 54/58, Chengdu 54/58.
Apart from Shanghai, TabFM agrees with the rules model's grouping: easier
Wuhan/Shenyang/Xi'an, harder Nanchang/Nanjing/Chengdu. At #200 the two agree
within ~3 points. TabFM is less certain at the top (#10: 92–97% vs 100%).
NUM-R^3 (online #436): Shanghai 10.7%, Nanchang 5.6%, Shenyang 4.9%, other
sites 2.9–4.0%. The Shanghai figure inherits the Shanghai extrapolation.
**Decision:** the online-gold forecast stays the one to use. The TabFM 2026
table is a research comparison and is marked uncalibrated in its report.
Once 2026 registration lists or early-regional results exist, the full
feature sets (which did beat online-only) become usable for the later sites.


## PTA registration lists for 2025–2026 (2026-09-28, review)

**Files** (downloaded by the user from PTA into `data/`, untracked; columns
`team_id, team_name, team_name_en, school_name_cn/en, province, city, leader,
members` (`/`-separated), `coaches, review_status, created_at`):

| file | round | rows (REVIEWED) | created | PKU ranking matched by school + team |
|---|---|---|---|---|
| `icpc_2025_online_1_teams.csv` | 2025 r1 | 2,298 (2,279) | 2025-08-11 – 08-28 | 2,124 / 2,159 |
| `icpc_teams_2025_online_2_fixed.csv` | 2025 r2 | 2,597 (2,575) | 2025-08-11 – 09-03 | 1,723 / 1,745 |
| `icpc_2026_ec_round1_teams.csv` | 2026 r1 | 2,537 (2,535) | 2026-08-10 – 08-26 | 2,478 / 2,486 |
| `icpc_2026_ec_online_round2_teams.csv` | 2026 r2 | 2,640 (2,636) | 2026-08-10 – 09-01 | 2,472 / 2,480 |

`icpc_2025_online_2_teams.csv` is a **byte-identical copy of the 2026 round-2
file** (same MD5, 2026 timestamps) and must not be used; the `_fixed` file
replaces it. Quality: unique ids, no duplicate (school, team), no member on two
teams of one school, leader always among members; 1–2-member teams are ~4%.
Every unmatched ranking team is a school renamed or re-registered on PTA
(信息工程大学 → 中国人民解放军网络空间部队信息工程大学, 绍兴文理学院 → 绍兴大学,
湖州师范学院 → 湖州师范大学, 湖南理工学院 → 湖南理工大学, 常熟理工学院（已改名）,
`…（重复）` duplicates, …), so an alias table is needed on integration. The PKU
2025 rankings list only ≥1-solve teams (QOJ round 2 has 836 zero-solve rows),
which is why registrations exceed ranking rows.

**Online-gold / TabFM (measured by re-running `link_regionals` with the rows
appended to `online_rosters`).** 2025 mainland regional teams linked to an
online result: **1,282 → 2,017 of 2,231 (57% → 90%)**, every site 88–92%;
2025 golds linked 164 → 211 of 233. 2022–2024 (78–86%) are unchanged. This
removes the 2025 gap behind the quota labels (band slots only go to linked
teams), the 2025 online-tier features and the 2025 held-out/training rows. For
2026 the rosters make the member-history tier computable before registration:
of ~2,480 ranked teams per round, ~830 have a member who played a 2025
official regional, 540 a 2025 medallist and 97–104 a 2025 gold medallist
(79–85 of the top 300). That tier carried most of TabFM's backtest gain.
Cross-round renames (≥2 shared members, same school, new name): 84 teams in
2025 and 130 in 2026; `online_strengths` keys by name, so they are currently
split into two one-round teams.

**Rating fit.** QOJ 2513 / 2524 (the 2025 online rounds, in the fitted set)
have members on only 9 / 4 rows, so their teams link to the rest of the fit
only by trusted names, mostly to each other. Attaching roster members to rows
whose name is unique in the round's roster, whose school + name is in the PKU
ranking and whose solved count agrees (2,038 / 1,659 rows; one mismatch) raises
the rows sharing an identity with a non-online contest **240 → 1,432** and
**205 → 1,294** in the `joint.py` union-find. The new links go to the 2025
Wuhan, Shenyang, Nanjing, Shanghai and Chengdu regionals and EC-Final. The
effect on calibrated LOCO is **untested**: identity fixes are the only changes
that have improved it before, but qualifier removal was neutral. The 2026 lists
do not affect the fit yet (no 2026 contest is loaded).

**Status:** the forecast side is integrated in the next section. The fit
attachment is still untested with `arch_b.metric`.


## Forecast experiments redone with the 2025–2026 rosters (2026-09-28)

**Data.** `scripts/add_pta_rosters.py` appends the REVIEWED rows of the four PTA
lists to `data/ec_online/online_rosters.csv` (10,025 rows) and is idempotent.
School aliases are **per season**: the 2025 ranking uses the old names (10
aliases), while the 2026 ranking already uses most new names (only 湖南理工大学 →
湖南理工学院). A single table broke 22 round-1 and 12 round-2 matches in 2026. With the aliases, every
ranked 2025 and 2026 team matches a roster (new test). The raw PTA exports stay
untracked in `data/` because they also carry coach names. The duplicate
`icpc_2025_online_2_teams.csv` is unused.

**Bug fixed: 2026 school names with CJK radicals.** The 2026 school-ranking PDF
prints 西, 民, 长, 门, 青, 齐, 龙, 黄, 车 and 马 as CJK Radicals Supplement code points
(U+2E80–2EFF, e.g. ⻄ U+2EC4). NFKC folds only Kangxi radicals (U+2F00–2FDF), so
the 2026-09-27 note above that NFKC fixes them is wrong. Across the three tables,
84 `online_schools.csv` rows kept the radicals. So **413 of 2,893 2026 online
teams (84 schools, including 西北工业大学, 西安电子科技大学 and 江西师范大学) had no
combined school rank**, and therefore no band slots in any 2026 forecast.
`build_ec_online_data.nfkc` now maps them. The committed CSV was rewritten with
that function (no PDF cache locally), and a test checks that every ranked team's
school has a combined rank. 2022–2025 data are unaffected.

**Online-gold model** (`output/online_gold.md`). 2025 held-out teams linked to
an online result rose from 1,282 to 2,019 (mainland link rate 57% → 90%).

| test | online only | rules line | + quota adjusted (shipped) | school-rank line | oracle line |
|---|---|---|---|---|---|
| 2024 (1,939, unchanged) | 0.1659 | −0.0002 [−0.0006, +0.0001] | −0.0003 [−0.0007, +0.0001] | −0.0001 [−0.0004, +0.0001] | −0.0013 [−0.0022, −0.0006] |
| 2025 (2,019; was 1,282) | 0.1545 | −0.0008 [−0.0017, +0.0001] | −0.0010 [−0.0029, +0.0003] | −0.0011 [−0.0029, +0.0003] | −0.0040 [−0.0078, −0.0003] |

The rules-line gain holds in sign but its 2025 interval now crosses zero. Site
history still hurts (+0.0040). ρ falls from **0.441 to 0.394**: renamed band
teams had been counted as quota entrants, and 12 golds move from quota to band
teams (quota golds 142 → 130; WF 1.47 → 1.36×, host 0.91 → 0.80×). Spearman with
the CF gold bar is −0.479 (was −0.503). **2026 lines** (both fixes): Shenyang
75.7 > Wuhan 73.0 > Xi'an = Shanghai 70.2 > Nanchang 68.6 > Chengdu = Nanjing
68.4, previously 88.7 … 68.6. The radical fix alone moved Shenyang from 88.7 to
75.7, because the dropped strong schools had made every line too easy. A team at
online #100 now has 57/56/55/55/55/54/54% (was 66/63/61/60/60/58/58). The sites
are much closer than before; the order is unchanged. NUM-R^3: 3.3–3.7%.

**Quota model** (`output/quota_teams.md`). The Shanghai validation is unchanged
(151/151, 159/159). 118 of 130 quota golds (91%) come from top-50 schools.
Per-contest quota golds from known quota teams (MAE): pooled 1.75, **by channel
1.49**, by school rank 1.85 (the earlier best), by team rank 2.08. Before
registration, the school-rank model still beats the pooled rate (MAE 1.68 vs
2.27), with ρ_top50 1.26 and ρ_rest 0.05, but it still does not improve
held-out gold prediction.

**TabFM table.** The 2023–2024 rows are unchanged. The 2025 rows gain online
features (NULL `online_x` 1,507 → 770 overall). The 2026 grid adds the four
member-history features: 32 features instead of 28; every team has a roster, 929
have a member from a 2025 regional and 117 a 2025 gold medallist. Local 2025
baselines: online-only improves from 0.1885 to 0.1571, and the rich-feature
logistic gains mostly vanish (pre-registration −0.0017 [−0.0167, +0.0149], was
−0.0201; all −0.0085 [−0.0187, +0.0019]). Those gains had come from standing in
for missing links.

**Managed TabFM run 2** (`test-gemeni-501216`, us-central1, via `bq`; gcloud
already configured). Dataset `tabfm_gold_research` (7-day expiry) was created
and deleted after the run. Eight `AI.PREDICT` jobs: the six backtests, and the
2026 forecast twice (again after the radical fix). Each was dry-run first and
capped at 1 GiB billed. 10 MiB was billed per backtest and 20 MiB per forecast,
≈ 150 MiB with the checks and exports (< $0.001). Ledgers are in
`output/tabfm_gold_predictions/`.

| model | 2024 | 2025 | 2025 linked / unlinked |
|---|---|---|---|
| online_only (logistic) | 0.1705 | 0.1571 | 0.1543 / 0.1828 |
| TabFM, all 45 | −0.0093 [−0.0176, −0.0027] | **−0.0152 [−0.0251, −0.0068]** | 0.1459 / 0.1034 |
| TabFM, 35 pre-registration | −0.0101 [−0.0285, +0.0056] | −0.0042 [−0.0176, +0.0105] | 0.1566 / 0.1174 |
| TabFM, 32 forecast set | **−0.0226 [−0.0335, −0.0133]** | −0.0131 [−0.0259, −0.0012] | 0.1475 / 0.1094 |

**Run-to-run noise.** The 2024 split had byte-identical inputs in both runs
(checked against the uploaded table), so it is a repeat. The all-features call
reproduced (correlation 0.9998, log loss 0.1603 vs 0.1612). **The
pre-registration call did not:** correlation 0.969, mean |Δp| 0.033, max 0.44,
and Δ moved from −0.0218 to −0.0101. The contest bootstrap does not include
this noise, so feature-set rankings from a single managed run are unreliable.
The 32-feature forecast set beating its 35-feature superset in both seasons
fits that noise. In this run, TabFM beats online strength alone with the
all-features and forecast sets in both seasons (intervals exclude zero). That
includes 2025 linked teams, where the old 28-feature set had lost (0.1698 vs
0.1613).

**2026 TabFM forecast** (`output/tabfm_forecast_2026.md`). Within-cap teams
ranked #141–280 average 27% gold (26–29% by site; backtest 20%, actual 18%). The
old run gave 26% with Shanghai at 34%. This run gave 38% before the radical fix,
when 12% of those teams lacked a school rank, a feature that is never missing in
training. At online #100 TabFM and the online-gold model agree within 3 points
at every site (e.g. Shenyang 57/57, Nanjing 56/54, Shanghai 54/55). TabFM barely
separates the sites (top-300 mean 43.4–45.8%) and is higher below #150. Member
history moves it strongly: within the band, teams with no 2025 gold member get
23%, and teams with one or more get 41–48%. NUM-R^3: 3.5–5.0%. **Decision:**
unchanged. The online-gold forecast is the one to use; TabFM is a research
comparison that now agrees with it near #100.

**Tests.** 100 of 101 pass. The failure,
`test_calibration_experiment.test_locked_raw_and_gym_controls_reproduce_documented_loco`
(245.567 vs 245.4277), also fails on the committed state without these changes.

Run: `python3 scripts/add_pta_rosters.py`, then `online_gold`, `quota_teams`,
`build_tabfm_gold_data.py` and `tabfm_gold` as above (on Windows, set
`PYTHONUTF8=1`).

