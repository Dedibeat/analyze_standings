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
