# Candidate 2: stability-penalized DE

Prepared 2026-11-05, before this experiment's evaluation. This is candidate #2
from `de_successors.md`, not a rerun of rating-rethink experiment 2. No production
ratings, models or calibration are changed. Run the full experiment on the PC.

## Frozen experiment

Use the shipped joint standings and the same 185 CF anchors / 15 CF contests.
For every view, refit the whole binary and survival model. Retain the existing
zero-solve filtering and identity; these are completed-contest calibration
experiments, not future-contest forecasts. Infer survival windows from retained
training cells. The default MAP tolerance is 0.5, matching the DE benchmark.

**Training views:** full field, two seeded pairs of disjoint random halves, and
two random quarters, sampled by resolved team identity. A repeated identity's
rows always move together. All 15 anchor boards change simultaneously; other
boards stay in the joint fit. Seeds 20261105 and 20261106.

**Reserved stress views:** random half, quarter and eighth with seed 20261205;
event-only, equally sized event-small / mirror-balanced samples with the same
seed. Event/mirror labels are the existing ID heuristic, not verified exposure.
Conditions with no rows on an anchor board are excluded for that board, with
coverage recorded, never silently interpreted as a measured difficulty.

**Independent strength stress:** split non-anchor contests into A/B with seed
20261305. Fit binary abilities on A for selecting strong/weak halves of anchor
boards. In the pool/strong/weak joint measurements, exclude A entirely, so
measurement uses B plus the selected anchor rows. Restrict to identities seen
in both A and B. Compare strong/weak changes against this block's own pool,
not against the all-data full fit. This remains a development stress test.

Represent each task by the five existing DE features; use full-training-anchor
means, scales and clipping ranges only. A survival affine baseline is fitted
on full-training anchors. Add an intercept and ridge residual correction.
Penalize changes in the **whole final prediction**, including the affine
baseline's change, not just changes in the residual correction.

The candidate minimizes:

```
mean_over_tasks_and_training_views((prediction - CF_label)^2)
+ beta * mean_over_tasks_and_nonfull_views((prediction_view - prediction_full)^2)
+ alpha / number_of_tasks * squared_norm(residual_feature_coefficients)
```

Each task has total weight one regardless of its number of views; views are
repeated measurements, not independent labels. The intercept is not penalized.
Fixed grids: alpha = {0.1, 1, 10}; beta = {0, 0.1, 1, 10}. All views of a held
CF contest/canonical task leave both supervised fitting and stability fitting.
Choose alpha/beta by inner-contest mean squared CF error averaged across the
training views, with tasks equally weighted. Ties prefer smaller beta, then
smaller alpha. Reserved stress views never choose settings.

Controls: unchanged clipped DE (its existing alpha/lambda grid and full-field
inner selection); augmented ridge with beta fixed at zero; binary affine.
The beta-zero control distinguishes resampling from the stability penalty.

## Scorecard and decision

Outer task-purged leave-one-CF-contest-out predictions for every method/view:
CF RMSE and mean error, both problem-weighted and contest-balanced; per-contest
errors and matched coverage. Field drift: signed mean, median absolute and RMS
change for the same problem relative to the corresponding full/pool view.
Paired contest-bootstrap intervals compare CF RMSE with DE and augmented ridge.
Also report within-contest order reversals against full-field predictions and
CF target spread/predicted spread to expose a falsely stable flattened map.

Do not pick a new winner on the reserved views. A successor needs meaningful
transport improvement with acceptable CF accuracy, supported across contests.
If selected beta is zero or it does not improve over augmented ridge, do not
claim a stability-penalty gain. Inspect tail and region regressions. All these
contests were previously inspected: this is development, never fresh confirmation.
No automated promotion or arbitrary numerical release threshold is specified.

## PC handoff (Linux or WSL)

Everything required is tracked in Git; no QOJ/CF login, external config cache,
GPU package or artifact transfer is required. Cache generation is CPU NumPy.
Independent views can run in parallel. Each worker loads its own dataset;
start with two workers if RAM capacity is unknown. The 4070 is unused.

```bash
git pull --ff-only origin master
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements-de-stability.txt
./.venv/bin/python -m unittest tests.test_de_stability

# Verify frozen source hashes, expected anchor count and cache status.
./.venv/bin/python -m arch_b.de_stability check

# Expensive step, resumable; increase jobs only if RAM permits.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  ./.venv/bin/python -m arch_b.de_stability prepare --jobs 2

# Cheap relative to refits; resumes use the cache without any new refits.
OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.de_stability evaluate
```

Run from the repo root. Cache and outputs live under gitignored
`de_stability_run/`. Each completed view is atomic and reusable. Interrupted
views are recomputed; source/plan hash changes reject stale caches. For a
limited pipeline check use `prepare --view full --jobs 1`; `evaluate` deliberately
refuses an incomplete cache. The final JSON and generated Markdown are research
artifacts to inspect on the PC before deciding whether to commit results.

At handoff, only tests, preflight and the full-view pipeline check are run here;
the full candidate evaluation is intentionally left for the PC. Missing files,
hash mismatches and missing view coverage must be reported, not guessed.
