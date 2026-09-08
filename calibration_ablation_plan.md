# Focused ridge feature-group ablation

Status: frozen research-only development protocol.  This experiment neither
changes the production calibration nor constitutes fresh confirmation.

## Scope and fixed inputs

The 185 one-to-one CF/QOJ anchors in 15 CF contests are rebuilt through
`arch_b.calibration_experiment.build_anchor_table`.  Feature construction and
all source-contest evidence remain in that module.  Each anchor retains its
canonical `qoj:<problem_id>` task identifier; a held fold's canonical tasks are
purged from its training data.

The residual predictor always contains `raw_b`, plus exactly one nonempty
combination of these fixed groups:

| bundle | added features |
| --- | --- |
| D | `binary_minus_survival` |
| E | `conditional_fit_se`, `solve_rate`, `log_field_size` |
| T | `log_median_solve_seconds`, `timing_missing` |

The seven fixed bundles are evaluated in this order: `D`, `E`, `T`, `DE`,
`DT`, `ET`, `DET`.  `DET` is the existing seven-feature ridge control and must
numerically reproduce its frozen LOCO RMSE, 229.6269246, within normal floating
point tolerance.

## Nested development protocols

1. **Leave-one-CF-contest-out:** for each held CF contest, remove its labels and
   explicitly purge its canonical tasks.  The remaining CF contests are the
   inner grouped folds.
2. **Leave-one-region-out:** for each of the three observed anchor regions,
   remove *all labels* from that region before any affine baseline, scaler,
   residual fit, or inner-contest selection.  Its remaining contests form the
   inner grouped folds.  Canonical held-region tasks are also purged.

For every fixed bundle, the inner folds jointly choose ridge alpha from
`(0.1, 1, 10)` and residual shrinkage lambda from `(0, .25, .5, .75, 1)` by
minimum pooled inner MSE.  Ties use the listed alpha then lambda order.  An
additional adaptive method chooses `(bundle, alpha, lambda)` solely from the
same inner training folds; exact score ties prefer fewer added features, then
the fixed bundle order, then alpha/lambda order.  No outer labels are used for
any selection.

Raw affine and locked-gym-shape affine are recorded controls.  All residual
methods are residual corrections to raw affine, not the gym map.  Preprocessing
(mean and standard deviation) is fit only on the applicable training rows;
zero standard deviations are replaced by one, and all predictions are required
to be finite.

## Outputs and hand-off API

`arch_b.calibration_ablation.py` exposes:

* `fit_predict_fixed(train, test, bundle, alpha, lam)` — training-only affine,
  scaler, and ridge fit for one fixed setting.
* `select_inner_contests(train, bundles=...)` — grouped inner-contest selection
  for all fixed bundles and the adaptive selector.
* `select_full_anchors(rows, bundles=...)` — all-anchor inner selection for
  each fixed bundle and adaptive selector, for transfer diagnostics only.

`output/calibration_ablation.json` records all 185 OOF predictions for every
method and protocol, selected settings, fold membership, per-contest and
per-region RMSE, feature configurations, and SHA-256 hashes of inputs, this
source module, and this plan.  Full-anchor choices are explicitly labelled
not-OOF/not-deployment.

## Verification before result interpretation

The run fails if coverage is not 185 anchors, a canonical task leaks into a
training fold, rows/features/labels are non-finite, regions are not exactly
the observed three, or the `DET` contest-LOCO control differs from
229.6269246.  The transfer-facing API has separate validation tests.  No TabFM
code, import, checkpoint, download, or execution is part of this experiment.
