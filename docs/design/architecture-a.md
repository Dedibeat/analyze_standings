# Architecture A (`arch_a/`)

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

## Key decisions

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

## Results (current run)

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

## Caveat introduced by the stronger normalization

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
