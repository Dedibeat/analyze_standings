# Two Codeforces standings experiments

## Does participation explain the hard-solve increase?

1. For each February from 2022 through 2025, compare the preceding August–January with February–July. The 2025 date comes from exploratory analysis. Earlier dates serve as season-matched placebos.
2. Use individual rated participants with at least ten earlier cached rated contests and a pre-round rating of 1000–1599. Join the standings and rating changes by contest and handle. For each problem at least 600 above a player, count observed solves and sum the Elo solve probabilities. Repeat on problems at or below the player's rating as a control.
3. Restrict to rounds explicitly labeled Div. 2 without Div. 1, comparing educational and other rounds separately in the weighting. Group participants by 200-point rating band and experience (10–29 or 30+ prior rounds). For each period compute observed / expected by stratum, then average using the earlier period's expected solves as weights on common strata. Compare with the pooled raw ratio.
4. Repeat for handles with eligible standings on both sides. Participation frequency can still change within this cohort. Check that the hard-gap change exceeds the historical placebo changes and compare with the easy control. This measures changes in solves conditional on published difficulty. It cannot identify AI use or establish a causal effect on contestant ratings.

## Which problem rating predicts a later field?

1. Inventory problem identifiers, durations, standings, rating histories, timestamped CF and CLIST estimates and independent timed attempts. An evaluation row needs a player, pre-event rating, problem, known opportunity to solve, outcome and a common contest deadline.
2. Fit one difficulty per problem to the original field by maximizing Bernoulli likelihood with fixed player ratings and the Elo slope. Use weak regularization to handle zero or perfect solve rates. Freeze parameters and all three rating snapshots before the evaluation event.
3. Match an independent timed field on identical tasks and deadlines. Audit selection, earlier exposure, task ordering and missing ratings. Report matched coverage. Solve-only practice records cannot supply the denominator.
4. Evaluate on identical rows. Report mean log loss, calibration by player band and paired differences with intervals resampling evaluation contests. Learn any baseline scale conversion on separate contests. Claim an improvement only if both baseline comparisons favor the candidate with intervals excluding zero. If historical snapshots are missing, start prospective collection once an authorized rating source and eligible evaluation field are available.

## First results

Each cell below gives the before and after ratios standardized to the earlier field. A value of 0.658 means 65.8 observed solves per 100 expected solves. The window is six months on each side, including for the placebos.

| February split | All eligible, hard | Returning, hard | All eligible, easy | Returning, easy |
|---|---:|---:|---:|---:|
| 2022 | .311 → .296 | .249 → .263 | 1.048 → 1.046 | 1.054 → 1.044 |
| 2023 | .306 → .276 | .204 → .279 | 1.044 → 1.043 | 1.049 → 1.046 |
| 2024 | .193 → .315 | .147 → .283 | 1.058 → 1.082 | 1.066 → 1.086 |
| 2025 | .412 → .658 | .296 → .568 | 1.075 → 1.070 | 1.086 → 1.075 |

The 2025 comparison includes 56,475 distinct eligible handles, of whom 18,728 competed in both windows. Before standardization the hard ratios were .412 → .673 for all eligible players and .296 → .517 for returners. Adjusting for measured participation differences leaves a larger absolute hard-gap increase in 2025 than at any of the three placebo dates. The 2024 increase was already substantial. These overlapping before/after comparisons give descriptive evidence only. Problem choices, contest composition within strata and selective return remain possible explanations.

**Difficulty pilot.** We used the 2025 cached Div. 2 rounds and held out about one fifth of handles using a stable hash. The remaining established players determined each fitted difficulty, with one half-solve at rating 1500 as regularization. Across 56 rounds, 372 rated problem entries and 630,677 held-out opportunities (225,033 solves), mean log loss was **0.20424 fitted vs 0.21915 official**. Lower is better. The official comparator uses its published rating directly in the same Elo curve. These outcomes share the original contest setting, the official ratings may use those outcomes, and each round has its own deadline. A calibrated official comparator and a later independent field are still needed.

**Data audit.** The standings cache stores official contestant rows only. The pairwise cache contains problem metadata and statements, and the Gym mirrors cover ICPC team events. We found no timestamped CLIST problem ratings or matched later evaluation field for this pilot in the repository. An anonymous request to the CLIST v4 problem endpoint returned HTTP 401. A dated CLIST export or authenticated source with verified coverage and prospective timed evaluation rows are the outstanding inputs for the three-way test.

**Reproduction.** Populate the CF cache using the README fetch commands. In a Python environment with numpy, pandas and scipy, run:

```sh
python scripts/cf_participation_check.py
python scripts/cf_difficulty_pilot.py
```

The first command prints year, cohort and distinct handles followed by hard and easy results. Each group contains raw before, raw after, adjusted before and adjusted after.

## Transfer of the ICPC two-parameter experiment

The ICPC experiment in `arch_b/twopl.py` estimated both team abilities and problem response curves. Its per-problem slopes worsened held-out log loss. Here pre-round Codeforces ratings anchor the player axis directly. A fitted intercept sets the solve probability at 1500, and a positive slope determines how fast the log odds increase with rating. The implied problem difficulty is the player rating at which the predicted solve probability reaches 50%.

We reran the 2025 pilot with its original handle split, same pre-round inputs and same half-solve pseudo-observation. We compared one learned slope per round with one per problem. Both use the ICPC log-slope prior SD of 0.5 around the Elo slope, with log multipliers bounded to [−2, 2]. Each fit sees only training handles. Intervals below resample the 56 rounds together with their paired predictions 10,000 times, preserving opportunity weighting. The test set has already been used for development. The intervals describe between-round variability within this benchmark.

| Solve curve | Mean log loss | 95% interval for loss change vs fixed slope | Rounds improved vs fixed slope |
|---|---:|---:|---:|
| Fixed Elo slope, fitted difficulty | 0.204245 | reference | — |
| Shared slope within round | 0.203582 | −0.000955 to −0.000412 | 43/56 |
| Separate slope per problem | 0.201600 | −0.003108 to −0.002227 | 55/56 |

Allowing each problem its own slope reduced loss by 1.29% relative to the fitted pilot. The shared-slope control recovered about a quarter of the absolute improvement. These scores evaluate an entire solve curve. They do not establish that the 50% difficulty alone is a better scalar problem rating.

## Modelling pre-round player strength

We kept the per-problem slope model and changed its player input. The candidate starts at the official pre-round rating and adds two learned corrections. The first uses an exponentially weighted average of earlier rating changes (20% weight on the latest change, initialized at zero and skipping the first six appearances to avoid promotional bonuses). The second uses log experience relative to 30 prior cached rated contests. This lets two players at the same official rating receive different estimates based on their histories. Experience counts start with the rating cache in 2018.

The two coefficients minimize solve log loss on 2024 training handles with the fitted 2024 problem curves held fixed. We freeze the coefficients before scoring 2025. Player histories update from rated contests whose scheduled end precedes the target start. The historical replay assumes earlier rating changes were available by then. In each 2025 round we refit problem intercepts and slopes separately for each player model using the same training field. Held-out handles contribute no solve labels to either fit. Their own earlier published rating history is available as a prediction input.

Reproduce with `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/cf_player_rating.py` after populating the standings and rating-change caches.

In rating points, the fitted player estimate is approximately **official rating − 1.207 × recent mean rating change − 12.05 × ln(prior contests / 30)**. On exactly the previous 630,677 opportunities the baseline reproduced 0.201600 mean log loss. The player adjustment scored **0.201037**, a 0.28% relative reduction and an improvement in 44 of 56 rounds. The paired 95% interval for adjusted minus baseline loss, resampling rounds 10,000 times, was −0.000739 to −0.000392. This tests the combined adjustment; it does not isolate the contribution of either feature.
