# Rating model: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## Run

Requires Python 3 + numpy (`pypinyin` for the Hong Kong modules). A project venv is used:

```bash
python3 -m venv .venv
./.venv/bin/pip install numpy pypinyin
./.venv/bin/python -m arch_a.run
```

This writes `output/problem_ratings.json` (one record per problem with its
estimated `difficulty` on a Codeforces-like [800, 4000] scale) and prints
verification stats. Standing rows that solved no problems are dropped before the
fit (see the zero-solve decision in `docs/journal/`). QOJ omits unattempted problem
labels; the loader treats those cells as censored non-solves rather than dropping
them from the likelihood. If a standings row contains a label absent from that
contest's parsed problem list, that unknown solve is ignored for row retention
because its problem metadata is unavailable.

`run` fits the full `data/tagged.json` **anchored to the Universal Cup scale**:
it first fits the UCup seasons (`ucup_s3` + `ucup_s4`) on their own, then uses
each UCup team's ability as that team's prior when fitting tagged, so the two
sit on one comparable scale (see `arch_a/anchor.py`). Without the anchor the
tagged fit floats ~440 pts above UCup for the 5.8k shared teams; anchoring cuts
that scale gap roughly in half. Tune the pull with `estimate_anchored(anchor_weight=…)`.

## Architecture B (joint item-response model)

```bash
./.venv/bin/python -m arch_b.run
```

Fits the joint **Rasch** item-response model by MAP (`strat.tex` §4): each solve
is a Bernoulli draw on `sigma((θ_t − b_p)/s)`, and the shared `θ_t` links contests
automatically. Writes `output/problem_ratings_b.json` — same record format plus a
`difficulty_se` (Laplace standard error) per problem, a distinct file so
Architecture A's output is left untouched. Reuses arch_a's data layer and fits
**one joint MAP** over tagged.json, the supplemental standings, and the Universal
Cup seasons (`arch_b.joint`) — the two-phase UCup prior was retired on
2026-08-21 after it measured as a no-op here; tune the prior with
`estimate_joint(sigma_theta=…, sigma_b=…)`
(looser → wider scale but more easy problems pinned to the floor). The Gaussian
prior keeps solved-by-none/all problems finite, so no boundary smoothing is
needed. See `docs/journal/` for the Rasch-vs-2PL scope and the shrinkage-vs-arch_a
comparison.

Architecture B also loads 71 standings-only supplemental QOJ contests:
14 Asia East ICPC regionals from 2020–2021 and 57 Petrozavodsk camp contests
from 2022–2026. They add cross-contest team evidence without using statements
or editorials. The current joint fit has calibrated LOCO RMSE 245.4 CF
points (244.2 was the earlier two-phase fit; 261.6 also predates the
omitted-non-attempt-cell correction).

Add `--survival` to fit the **solve-time survival model** (`strat.tex` §5) instead,
which also uses *when* each problem was solved (writes
`output/problem_ratings_survival.json`):

```bash
./.venv/bin/python -m arch_b.run --survival
```

It distinguishes problems with identical solve counts that the binary model cannot
(e.g. it correctly separates two APAC problems both solved by 76 teams), and gives
tighter uncertainty.

Both `run` modes drop short-format contests (warm-ups / 3 h rounds) by default
(`MIN_SOLVE_HOURS`). `load` also offers `season_key=True` to separate recurring
rosters by ICPC season — but `arch_b.season_experiment` shows it doesn't improve
difficulty estimates, so it stays off; run that module to reproduce the comparison.

Validate any model against independent opinions from editorial-backed LLM labels,
official Codeforces ratings, Kattis, fixed-ability Codeforces gym mirrors, and
AOJ practice statistics:

```bash
./.venv/bin/python -m arch_b.validate           # LLM buckets, all models
./.venv/bin/python -m arch_b.gym_difficulty     # fixed-θ difficulty from CF gym mirrors
./.venv/bin/python -m arch_b.aoj --refresh      # rebuild the matched AOJ validation artifact
./.venv/bin/python -m arch_b.external_validate  # Codeforces + Kattis + gym + AOJ, all models
./.venv/bin/python -m arch_b.predict_eval       # held-out response imputation (binary vs survival)
./.venv/bin/python -m arch_b.calibrate     # DE problem ratings in Codeforces points
./.venv/bin/python -m arch_b.metric        # THE optimization metric: LOCO CF-point RMSE + guards
./.venv/bin/python -m arch_b.data_influence # explain supplemental-contest effects
```

All three architectures agree closely with both opinions. After the full-cell mask
correction, the LLM-bucket Spearman values are +0.908 (arch A), +0.908 (binary),
and +0.911 (survival); the pooled CF values are +0.913, +0.937, and +0.942.
On the corrected joint response-group imputation check, binary scores AUC 0.9727
versus survival 0.9674; this check favours binary, while the survival model remains
the shipped choice because it uses solve-time information and leads the broader
external CF/Kattis validation. This is not a future-contest forecast because row
retention occurs before the split.

`gym_difficulty` turns the scraped CF **gym-mirror** attempts
(`data/cf_gym_mirrors.json` — real timed attempts whose solvers carry their own
time-accurate Codeforces rating, trust-weighted by rated-contest count) into an
independent per-problem difficulty on the CF scale, fit with ability *fixed* at
each solver's rating. It is the third yardstick in `external_validate` and the
first external numeric anchor for **Asia East Continent** (230 problems), where
all three models validate at +0.95–0.98. `--certify` checks the instrument itself
(vs official CF ratings: Spearman +0.976, affine slope ≈1.2).

`arch_b.aoj --refresh` fetches the live AOJ problem catalog and writes
`data/aoj_difficulty.json` with source time, raw IDs, match method, accepted
matches, and rejected candidates. A match is used only when its normalized title
is unique in both datasets and at least three problems corroborate the same
contest. The current artifact accepts 45 problems from four Japan regionals and
keeps 26 isolated title matches rejected. `external_validate` compares
`submissions / solvedUser` only by within-contest rank; AOJ never enters training.

## The optimization metric

`arch_b.metric` is the single number model improvements are judged by:
**calibrated leave-one-contest-out RMSE in CF points** against the official
ratings of all 15 CF-mirrored contests (185 anchor problems — every rated
mirror the dataset has; an exhaustive sweep found no more). It refits the
survival model from source, applies the locked shipped gym shape, and prints
`METRIC calibrated_loco_cf_rmse=…` as its last line (current baseline
**245.4** for the joint fit; lower is better). It exits nonzero if any external
guard regresses (gym
Asia-East-Continent / gym pooled / Kattis / AOJ within-contest Spearman,
solve-count sanity) or if raw affine LOCO rises above 251.9 (the corrected 246.9
baseline plus five points). Anchor coverage and every metric must also be finite.
`program.md` at the
repo root is the matching
instruction file for auto-research loops: verify contract, what code is fair
game, hard anti-gaming rules, and a prioritized idea list. A 2026-07-03 auto-research campaign (Claude Fable 5 + DeepSeek v4 Pro, 25
iterations) found that the only repeatable improvements were data-side identity
fixes (−2.2 RMSE to 288.0, AUC-corroborated). That finite search predates major
data/model corrections and does not establish that model improvements are
exhausted (see the current review). A 2026-07-23 data-side campaign added the supplemental standings
and fixed an over-broad World Finals affiliation join; original-cell held-out
AUC also improved 0.885761 → 0.886000.
Those campaign numbers predate the full-cell mask correction; the corrected
row-by-row retest of `autoresearch/loop-260723-1333/classic-results.tsv` is
recorded in `docs/journal/`. The deeper [supplemental-contest influence audit](../reports/rating/data_influence.md)
finds that the corrected 1.065-CF gain is almost entirely Petroz-to-Northern-
Eurasia transfer, is not corroborated by the current original-cell holdout, and
does not justify a metric-selected contest subset. A strict no-link control
degrades LOCO from 244.2 to 333.5, confirming that shared-team normalization is
essential even though merely maximizing the number of new links is not useful.

## Calibrated Codeforces-point ratings

Since 2026-09-28 the shipped **problem** ratings use **DE**
([de_release_audit.md](../reports/rating/de_release_audit.md)). DE is the plain affine on raw survival `b` plus a
residual ridge on binary-minus-survival difficulty, conditional SE, solve rate
and log field size. The ridge features are clipped to the range of the 185 CF
anchors (15 mirror contests), and alpha/lambda are chosen on inner contest folds
(currently 1 / 1). On the roster-fixed fit, nested leave-one-contest-out RMSE is
**226.0** (clipped DE) against 246.1 for the gym map and 246.9 for the plain
affine. `arch_b.calibrate` writes
`output/problem_ratings_calibrated.json` (`difficulty_cf` in [800, 4000]; **no
uncertainty field** — the old gym-map SEs do not describe DE) and
`output/problem_calibration.json` (settings, anchor feature ranges, input
hashes).
- **Small-board flag** (since 2026-11-09): each record also carries
  `board_rows`, the board's rows with at least one solve.
- **`small_board`** is true when `board_rows` < 10:
  - that is 65 problems on 10 small North American boards, some with a single
    row;
  - treat their `difficulty_cf` as unreliable. The viewer, virtual calculator and UCup-only export read problem
ratings from that file (`calibrate.problem_cf`), so all consumers agree.

DE needs per-problem features, so it cannot map a team ability. Team
abilities, performances and medal bars keep the scalar map: a monotone
**shape** learned from the ~660 gym-mirror difficulties, then an **affine**
leg fit on the same CF anchors. Team performance in the virtual calculator
(and the medal viewer's cutoff teams) uses that map on the **binary** fit,
whose ability and difficulty axes both track CF at slope ~1; the survival
fit compresses abilities (see the 2026-10-04 calibrated-performance entry in
`docs/journal/`). `arch_b.metric` also still scores that map on
the raw fit (246.3 on the roster-fixed fit). The two axes no longer share one
map.

## Anchoring audit (2026-08-21)

A historical review of every mechanism that pins the scale — the UCup prior, the gym shape,
the CF affine leg, and the LLM opinions — is recorded in the anchoring-audit
section of `docs/journal/`. These measurements precede the implemented structural
shift below; the second-scale bug and dense-memory blocker have since been resolved:

- The Phase-1 **UCup prior-mean anchor is a no-op in Architecture B** (removing
  it moves difficulties by mean −3.6 with sd 0.96 and leaves the metric at
  244.3). Cross-contest normalization is carried by the shared union-find and
  the joint likelihood, not by the prior.
- `output/ucup_only_ratings.json` is **~90 CF points too low**: it rates the
  52 UCup-only contests on the Phase-1 fit but calibrates them with a map fit on
  the tagged-scale fit. Measured on the 305 problems both fits rate,
  `b_ucup ≈ 0.959·b_tagged + 36`.
- Fitting **UCup as ordinary data in one joint fit** costs +1.1 CF points
  (245.4 vs 244.3, all guards unchanged) and puts 684 more problems on the
  shipped scale. It is currently blocked by the dense `rows × n_problems`
  arrays in `arch_a.load` (~11 GB peak at joint size, ~0.35% density).
- **Per-region levels are not identified.** Against the gym yardstick
  Europe − Asia East = +117 ± 42; against the LLM bucket labels the same pair is
  −134 ± 30. Both referees rank well within region and disagree in sign on the
  level, so a per-region offset cannot be learned from either alone.
- The **LLM pairwise instrument pairs only within a contest** (185 problems /
  15 mirrors), i.e. on the axis the fit already gets right. Statements cover
  100% of tagged and UCup problems in every region, so a cross-contest schedule
  is the one anchor candidate with full regional reach — and it can be validated
  against the known per-contest CF offsets before being trusted.
- Only **92 of 207 fitted contests** have any external anchor, and all 185 CF
  anchor problems come from three regions.

The proposed structural shift (sparse data layer → one joint fit → cross-contest
LLM pairwise → hierarchical per-contest/per-region calibration → ability-side CF
anchoring) is written up at the end of `docs/journal/`.

## Structural shift implemented (2026-08-21)

The five steps the audit proposed, as built and measured (baseline metric 244.3):

1. **Sparse data layer.** `arch_a.load` now stores observed cells in COO form
   (`obs_row`/`obs_prob`/`obs_y`/`obs_tau`/`obs_wrong` plus `solved_count`),
   replacing dense `n_rows x n_problems` matrices that were 99.65% empty. Peak
   RSS for `arch_b.run --survival` drops **6,177 MB -> 696 MB** with the metric
   bit-identical at 244.3.
2. **One fit, one scale.** `arch_b/anchor.py` -> `arch_b/joint.py`;
   `estimate_anchored` -> `estimate_joint`. The Universal Cup is ordinary fit
   data and the two-phase prior is gone (`arch_a.anchor` keeps its anchor, which
   there does work). Metric 244.3 -> **245.4**, inside the noise floor; rated
   problems 2,475 -> **3,159**; the UCup-only export now matches
   `problem_ratings_calibrated.json` to within rounding instead of sitting ~79
   CF points low.
3. **Cross-contest LLM comparisons** — `llm_crosscontest.py`, see below.
4. **Hierarchical calibration** (`arch_b/hier_calibrate.py`): `cf = A*f(b) + B +
   u_contest + v_region`, partially pooled. It measures **tau_contest = 72.4**
   and **tau_region = 12.0** CF points. Only three regions inform the latter
   estimate; it cannot establish absence of bias in unanchored regions or prove
   that the gym/LLM disagreement is a referee artifact. LOCO does not improve
   (245.4 vs 248.3), so the
   shipped map stays the plain affine. Until the 2026-09-28 DE release, the
   exported uncertainty components were the conditional fit SE
   (`difficulty_cf_fit_se`) and calibration level SD (`difficulty_cf_level_sd`)
   plus their explicitly partial quadrature; these were not advertised as a
   calibrated prediction interval.
5. **Ability-side CF anchoring** (`arch_b/cf_prior.py`): the CPHoF participant
   ratings as a time-accurate, roster-complete, leak-free prior on team ability.
   Measured **inert** (57 anchored identities, metric moves <= 0.2), so it is
   off by default — but `--validate` gives the repo's first external check of the
   *ability* axis: fitted theta vs CF team ability Pearson **+0.752**, with an
   implied compression of 2.86x against the 1.63x the difficulty map applies.

## Participant Codeforces ratings (research finding)

A 2026-07-21 feasibility test matched exactly one Codeforces handle for 1,168 of
25,656 distinct standing member names (4.6%); only 2.3% of roster rows had every
member resolved.  The official Codeforces API is the right rating/history source,
while CLIST is useful only as secondary identity evidence.  The proposed fit
improvement is a confidence-weighted, time-accurate CF prior on team ability,
starting with fully resolved rosters so missing members are not silently treated
as weak.

The conservative source layer is now implemented:

```bash
./.venv/bin/python scripts/cphof_cf_participants.py --refresh
```

It caches CPHoF's 2021–2025 World Finals rosters/profile pages, accepts only
explicit CPHoF Codeforces profile links, and caches each handle's complete
official `user.rating` history.  `data/cphof_cf_participants.json` contains 346
explicit person→handle identities; requiring a second matching roster member
corroborates 285 people across 1,582 standing-member appearances and leaves 347
unique standing rows with handles for the full roster.  Exact-name-only
appearances and stale/missing handles remain in the artifact as rejected or
review-only evidence.

This data is consumed by the **opt-in** `arch_b.cf_prior` hook described above;
the default fit leaves it off. CPHoF supplies World Finals
calendar dates but no start times, so the artifact includes 470 pre-event rating
observations using a conservative 00:00 UTC cutoff that excludes same-date
rating changes.  Most `tagged.json` regionals have only a year, so the
collector retains full histories but does not invent regional timestamps or
derive priors from them.  See
[`cf_participant_ratings.md`](../reports/codeforces/cf_participant_ratings.md).

## Time-varying team ratings (research, 2026-10-04)

```bash
python3 -m arch_b.dynamic_rating   # ~7 min; writes output/dynamic_rating.{json,md}
```

Tests whether team ratings that move with time predict team performance
better than the shipped one-ability-per-team fit. Every model is refit month
by month on earlier contests only; 2023 tunes and 2024–2026 is scored.

- **Static ratings are too high early and too low late.** Within a team,
  static-fit residuals rise about 15 points/year (about 40 for weak teams).
  CF-anchor residuals trend the same way by contest year.
- **A Codeforces-style per-contest update (Kalman filter) forecasts worse**
  than the static joint fit (pair accuracy −0.004). Each contest's
  difficulties are frozen when it is processed.
- **A joint random-walk fit** (TrueSkill Through Time style) gains a little
  (+0.0005 to +0.0010), mostly for teams with long histories.
- **CF RMSE is unmoved** (q = 25–100, within about 1 point): the north-star
  goes 244.6 → 245.0–245.6, and the shipped DE calibration 225.6 →
  224.6–225.3 (not significant). Nothing shipped changed.
- **Bigger gains:**
  - deflating ratings that rest on EC online rounds when forecasting onsite
    contests (+0.002);
  - giving new rosters a prior from their members' earlier teams. About 26%
    of new rosters have a known member; adding them lifts pair accuracy by
    +0.043 over rating them at the flat 2000.

Details: `docs/journal/` (2026-10-04 entry).

## Bar misses and performance inflation/deflation (2026-10-13)

- **Bar misses: fixed by reading the gold line.**
  - The CF gold bar is a problem threshold, with reliability 0.61 as a gold
    difficulty measure. The gold line (the last gold team's performance)
    scores 0.85.
  - `online_gold.contest_difficulty` now compares the online evidence with
    the line. The bar stays for the badges.
  - With the fix below as well, fit − online is +33 for Shanghai 2025, +9
    for Nanjing 2024, +33 for Kunming 2024 and −53 for Xi'an 2025 (it was
    −118, −114, +156 and +66 on the bar).
- **Inflation and deflation: root cause found, and fixed for performance.**
  - **The cause.** QOJ boards of onsite contests are merged boards: the
    event's own official rows next to UCup teams and QOJ accounts. 171
    boards in the fit are mixed this way.
    - Mirror entries play online and finish far above the same teams onsite.
      The same team rates +82 higher by solves as a UCup entry (47 teams);
      the DE audit's paired offset is +102.
    - Ranked against the whole board, onsite results were dragged down by
      the board's mirror share.
    - Big onsite fields carry relatively few mirror entries. So strong
      teams seemed to read +33 to +62 CF higher at 440-team than at
      300-team regionals.
  - **The fix.** An official row of a merged board is now ranked within its
    own event (`export_virtual_calc.event_field`, at least 30 rows). This
    applies in `performance_fit` and in `contest_quality.performance`.
    - The field-size effect goes (top-team slope +65 → +3).
    - The gold lines agree better with the rating-free referees (reliability
      0.84 → 0.89).
    - The lines rise: gold cutoffs by a median of +66.
    - Within the event's field, performance and problem difficulty agree
      across strengths.
  - **Unchanged:** mirror rows and virtual calculator entries are still
    ranked on the whole board, as online entries.
  - **The EC-Final (−73) and online-round (+89) offsets come from the DE
    problem ratings.** Performance agrees with the fit's own problems at
    every contest type, within +15 to +25. DE's solve-rate and
    survival-timing terms shift whole contest types (EC-Final +127, online
    −39 per problem). DE is unchanged here; re-auditing it is the next step.
  - **Ruled out earlier:** weakly identified rivals and the team-vs-team
    curve (345 in sample, 435–480 out of sample, so 400 stands).

Details: `docs/journal/` (2026-10-13, both entries).
