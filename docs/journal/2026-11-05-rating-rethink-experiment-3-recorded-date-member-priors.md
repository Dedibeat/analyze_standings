# Rating rethink, experiment 3: recorded-date member priors (2026-11-05)

**Request.** Finish Claude's work and continue the experiment. The user
clarified that this means rating experiments after 0–2, rather than the latest
team/Codeforces review. The existing checkout was clean; no experiment process
was still running. The earlier team download was checked: all 179 submissions
have code, and all 21 cached contest dashboards have statement text for every
listed problem. No additional team downloads were needed for this experiment.

**Protocol and implementation.** `member_forecast_plan.md` was written before
scoring. `arch_b/member_forecast.py` builds a separate regional panel from
imported QOJ rows matching the existing XCPCIO official-team matcher, dated by
cached numeric start/end times. At every target start it fits binary Rasch
only on contests whose recorded end is strictly earlier. No proxy dates,
full-data problem ruler, future union-find or target responses enter training.
Identity is an exact normalized three-person roster; changed rosters can borrow
member history without merging. Rows without full rosters are isolated.

Cold-roster forecasts average the three members' latest earlier team ratings,
using MU0 for missing members. Their deviation from MU0 is multiplied by one
weight from {0, 0.5, 1, 1.5}, selected solely on 2023 contest-balanced pair log
loss involving cold rosters. Multiple members from an earlier roster share a
source and do not contribute independent posterior precision. Same-time
conflicting member histories supply no evidence. This is a point forecast,
not a fitted model of individual abilities or uncertainty.

The fixed q=50 random walk is tested separately on repeated rosters, using
`dynamic_rating.smooth_fit`. The historical pair scale 1.25 × Elo.S is frozen.
Both models use tolerance 0.01, tightened from the default 0.5 to avoid treating
tiny optimizer differences as a dynamics gain. There is no dynamics grid search
or member/dynamics combination.

**Coverage.** 26 boards, 9,127 retained rows in 2022–2025. 2022 supplies initial
history; four informative 2023 boards select weight **1**. The 2024–2025 replay
has 2,499 forecast rows (1,133 history, 1,366 cold with member history), with
pairs on 12 boards. 12,517 nonpanel rows and 133 zero-solve official rows are
excluded. Another 1,310 retained rows lack full rosters: useful for training
problem measurement, but not forecastable. Missing EC-Final date configs
**1522/1894** remain excluded. Every exclusion and cutoff is archived.

**Results.** `output/member_forecast.json`; interpretation in
`member_forecast_report.md`. Same rows/pairs within each comparison:

| population | pairs | static accuracy → member accuracy | static pair log loss → member |
|---|---:|---:|---:|
| cold only | 96,905 | 50.00% → 66.93% | 0.69315 → 0.59336 |
| history plus cold | 313,789 | 64.32% → 71.45% | 0.60261 → 0.53969 |
| cold-involving (primary) | 233,879 | 60.30% → 69.87% | 0.64492 → 0.56052 |

Primary paired contest-bootstrap differences: +9.57 [+8.17, +10.92] percentage
points accuracy; −0.08441 [−0.09163, −0.07664] log loss. Contest-balanced log
loss falls 0.64842 → 0.54866. Every scored board and every one/two/three-known-
member subgroup improves in point estimate. First evaluation appearance per
roster leaves 154,462 pairs, log loss 0.66311 → 0.57609; the difference interval
still excludes zero. Calendar-season resampling is saved, but only has two
blocks and is descriptive.

**Dynamics.** 79,910 history pairs on 11 boards: static log loss 0.478753,
q=50 0.478757, difference +0.000004 [−0.000120, +0.000130]. Contest-balanced
difference −0.000123 [−0.000315, +0.000045]. No useful incremental gain.

**Limits / decision.** Member priors remain the next forecast candidate;
retain static history control. This is a stricter development replay, not an
untouched confirmation: these seasons were already inspected. Normalized
names/official matches remain heuristic, and cached rosters lack publication
timestamps, so availability at historical cutoffs is not certified. Results
exclude zero-solvers and omit online/UCup history. Hong Kong 2024 has only
three forecast rows/pairs; do not infer a precise Hong Kong validation from it.
Freeze the prior and collect rosters before future results for confirmation.
Appearance effects, timing (experiment 4), canonical task linking (experiment 5)
and the remaining experiment-0 provenance work are still open. No production
fit, calibration, rating, viewer or app artifact changed.

**Verification.** Seven new tests cover target/future-response isolation,
changed-roster identity, overlapping/same-end contests, ambiguous member
histories, normalization/time units, ties and contest/pair weighting. Full
suite: **205 tests pass** (existing resource/empty-slice warnings remain).
The JSON records source/code hashes, exact training contest manifests,
convergence, row forecasts and per-contest scores. Cached configs are
gitignored; missing caches explicitly reduce the recorded panel coverage.
A second frozen replay reproduced the saved JSON byte-for-byte. All 35
source/code hashes and all 26 strict training cutoffs were verified.

Run: `OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.member_forecast`,
then `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.
