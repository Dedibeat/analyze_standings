# Experiment 3: member priors and a fixed random walk

2026-11-05. Continues [experiments 0–2](rating_rethink_experiments.md).
Protocol: [member_forecast_plan.md](member_forecast_plan.md).
Results and cutoff manifests: [output/member_forecast.json](output/member_forecast.json).
Research only; shipped fits, calibration, ratings and viewers are unchanged.

**Member history survives the stricter development replay.** On matched future
pairs involving a new roster, accuracy rises from **60.30% to 69.87%** and pair
log loss falls from **0.64492 to 0.56052**. The fixed q=50 random walk adds no
useful log-loss gain on repeated rosters. These are development results, not
fresh confirmation or a verified real-time backtest.

## What changed from October

The old `dynamic_rating` experiment used full-panel identity, proxy dates,
full-data problem difficulties for its solve score and member-prior targets
measured on that ruler. This experiment does not use those scores or targets.

- Train separately at each recorded event start, on contests that **ended
  strictly earlier**, including all their available response cells.
- Fit binary Rasch using only that history. Target responses never measure
  training problems, fit member weights or affect identity.
- Identify a team by its exact normalized three-person roster. Two-member
  overlap transfers evidence without making the rosters the same identity.
  No account-ID, university-rank or transitive roster linking is used.
- Use only imported QOJ rows that match the existing XCPCIO official-team
  matcher. Account and UCup mirror rows are excluded, avoiding the unknown
  attempt dates in the broader dataset.
- Predict rank order directly, with the historical pair scale 1.25 × Elo.S.
  There is no target-field level fitting or held-out solve-probability claim.

For a new roster, each known member supplies their latest completed earlier
roster's static rating. Missing members supply MU0. Average the three ratings
and shrink its deviation from MU0 by a weight chosen from {0, 0.5, 1, 1.5}.
Repeated members from one old roster share one evidence source; their values
are not treated as independent precision contributions. This estimates a team
point forecast, not individual ability or posterior uncertainty.

Choose the weight on **2023 only**, minimizing contest-balanced log loss for
pairs involving a cold roster. Four tuning contests supply 109,982 pairs:

| Weight | Contest-balanced tuning log loss |
|---|---:|
| 0 | 0.64974 |
| 0.5 | 0.55551 |
| **1** | **0.52161** |
| 1.5 | 0.52681 |

Freeze weight 1 for evaluation from 2024 onward. The random walk is a separate
q=50 points/√year challenger on history rows; it is not combined with members
or selected from a sweep. Both fits use convergence tolerance 0.01. Tightening
the default 0.5 tolerance left the member conclusion unchanged and avoids
reading tiny optimization differences as a dynamics improvement.

## Coverage and missing evidence

There are **26 dated boards, 9,127 retained rows**, spanning 2022–2025:

| Calendar year | Boards | Retained training/target rows | Rows with forecasts |
|---|---:|---:|---:|
| 2022, initial history | 5 | 2,640 | 886 |
| 2023, tuning | 8 | 2,275 | 1,012 |
| 2024, evaluation | 6 | 1,898 | 1,196 |
| 2025, evaluation | 7 | 2,314 | 1,303 |

The 2022 forecasts are archived for audit, not used for weight selection or
reported evaluation scores. Of 2,499 evaluation forecast rows, 1,133 have exact
roster history and 1,366 are cold rosters with member history. Twelve boards
provide evaluation pairs; Xi'an 2025 has no forecastable retained roster.

- Recorded-date configs for QOJ **1522 and 1894 are missing**. They are excluded,
  not dated by interpolation. Other unmapped boards are also listed explicitly.
- 12,517 rows fail the imported/official panel restriction. Another 133
  zero-solve rows are dropped, matching the existing model's participation
  filter. These results are conditional on solving something; they do not
  validate forecasts for zero-solve participants or all registrations.
- 1,310 retained rows lack a complete three-person roster. They help measure
  training sets under isolated identities but cannot receive roster forecasts.
- Hong Kong 2024 has only **3 forecast rows / 3 ordered-outcome pairs**. Hong
  Kong 2025 has 32 forecast rows. Contest-balanced metrics give the small 2024
  sample a full contest's weight; pair-weighted metrics are therefore also
  reported. This is not a well-powered Hong Kong-specific validation.
- Normalized names are not audited person IDs. Official name matching is the
  inherited heuristic, not a new one-to-one identity adjudication.
- Cached rosters have no publication timestamps. Their availability at each
  historical cutoff cannot be certified. Event dates are recorded; roster
  information remains a retrospective snapshot.

## Matched-population results, 2024–2025

Forecast ties count half; pairs tied in finishing rank are excluded. All models
within a comparison score the same rows and pairs.

| Population | Contests / pairs | Accuracy: neutral → member prior | Pair log loss: neutral → member prior |
|---|---:|---:|---:|
| Cold rosters with known members | 12 / 96,905 | 50.00% → **66.93%** | 0.69315 → **0.59336** |
| History plus cold | 12 / 313,789 | 64.32% → **71.45%** | 0.60261 → **0.53969** |
| **Pairs involving a cold roster (primary)** | **12 / 233,879** | **60.30% → 69.87%** | **0.64492 → 0.56052** |

For the primary population, paired contest-bootstrap 95% intervals for member
minus neutral are **+9.57 [+8.17, +10.92] percentage points** accuracy and
**−0.08441 [−0.09163, −0.07664]** pair log loss. Contest-balanced accuracy rises
59.63% → 70.32%; contest-balanced log loss falls **0.64842 → 0.54866**, difference
**−0.09976 [−0.12386, −0.07877]**. Every evaluable board has a lower point-estimate
log loss. The small Hong Kong samples do not account for the pair-weighted gain.

**Known-member subgroups.** Each row compares that cold subgroup against itself
and the history pool; cross-subgroup cold pairs are omitted. Subgroup pair counts
therefore do not sum to the primary total.

| Known members | Cold rows | Pair log loss: neutral → members |
|---|---:|---:|
| 1 | 554 | 0.63187 → **0.58798** |
| 2 | 445 | 0.61808 → **0.54292** |
| 3, reshuffled from multiple rosters | 367 | 0.62988 → **0.49760** |

The saved artifact also separates one, two and three distinct earlier-roster
sources; all three improve in point estimate. There are 785 cold rows with one
source, 480 with two and 101 with three. No additional weights were selected for
these subgroups.

**Dependence checks.** Keeping only each roster's first evaluation appearance
leaves 154,462 primary pairs. Accuracy rises 56.81% → 68.56%; log loss falls
0.66311 → 0.57609, difference **−0.08703 [−0.09385, −0.07936]**. This removes
repeated exact-roster targets but not dependence through shared members.
Calendar-season resampling is saved too, but has only **two blocks** and must be
read as a sensitivity check, not a reliable interval for new seasons.

## Random walk: no useful incremental evidence

On 11 boards / 79,910 history-only pairs:

| Model | Pair accuracy | Pair log loss | Contest-balanced log loss |
|---|---:|---:|---:|
| Static exact-roster Rasch | 76.091% | **0.478753** | 0.459996 |
| Fixed q=50 | 76.107% | 0.478757 | **0.459873** |

Pair log-loss difference is **+0.000004 [−0.000120, +0.000130]**. Contest-balanced
log-loss difference is −0.000123 [−0.000315, +0.000045]. The accuracy changes
are tiny. There is no reason here to add dynamics to the production estimator
or search more random-walk settings on this evaluation period.

## Decision and remaining work

Carry member-informed cold-roster priors forward as the next forecast candidate.
Keep static Rasch as the history control. The narrower panel supports the
direction of October's member-history finding, but its effect sizes are not
comparable: the sources, identity rules and forecast populations differ.

Do not ship from this replay. These 2024–2025 seasons were already examined;
2023 tuning has only four informative boards. Next freeze the chosen prior and
scale, archive registration rosters before results, and evaluate a genuinely
untouched later field, including zero-solve participation once verified. Resolve
member-name collisions and source-backed roster availability before calling it
a prospective test. Appearance effects remain untested; timing (experiment 4)
and version-checked task linking (experiment 5) remain separate work.

## Reproduction and checks

```bash
OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.member_forecast
./.venv/bin/python -m unittest tests.test_member_forecast
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The artifact includes code/source hashes, every cutoff's training contest list,
convergence checks, row forecasts, coverage exclusions and per-contest scores.
The XCPCIO config cache is gitignored; a checkout without it will explicitly
report excluded configs and will not reproduce this panel's coverage. Seven
new regression checks cover future/target-response isolation, exact-roster
separation, overlapping contests, conflicting member histories, time units and
pair ties/weighting. The full suite passes **205 tests**.
A second frozen replay reproduces the saved JSON byte-for-byte; all 35
source/code hashes and all 26 strict cutoff manifests were checked.
