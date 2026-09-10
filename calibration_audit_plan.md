# Frozen DE correction and anchor-influence audit

Frozen before execution on 2026-09-10, in response to the request to work
autonomously on prediction improvements. This executes bounded parts of the
2026-09-08 roadmap using existing local data. Target: CF calibration of problem
difficulty after a contest's standings are available. No future forecasting,
production replacement, new labels, paid inference, or TabFM run is included.

## Candidate, provenance, and controls

Keep DE's five features and existing inner alpha/lambda grid unchanged. Controls
are raw affine and the locked gym shape. Rebuild the 185 anchors and all 3,159
problem appearances. Before interpreting predictions, verify the saved ablation
and transfer input hashes, anchor features/labels/membership, and replayed OOF
predictions (absolute tolerance 1e-7 CF points). Record current input, source,
plan, and row-table hashes. Missing inputs and mismatches stop the run.

Audit local source contest/label/task/title joins, unique CF title matches,
survival/binary problem coverage and solve counts, and feature field sizes
against the joint loader. This checks the cached records, not external task
version equivalence, actual duration, or adjudicated team identity. Record those
unavailable facts explicitly rather than inferring them.

## Deterministic correction audit

Select, in order, the top ten OOF absolute DE-minus-raw corrections, the top
ten improvements in absolute CF error, and the top ten deteriorations. Each
list uses descending magnitude then ascending stable row ID; retain unique rows
in their first-selected order and record every selection reason. Wins and losses
must have positive improvement/deterioration respectively.

Separately reconstruct the full-anchor refit through the existing selection
and prediction API, saving all appearance rows with source links, features,
predictions, training-range flags for each DE feature, and explicit non-OOF
labels. Select the ten largest absolute full-refit corrections, with the same
tie rule. Include both Luxor appearances of all five predefined shared task IDs.
For OOF support flags, use only that fold's purged training features. A range
flag is a marginal extrapolation diagnostic, not a calibrated risk probability.
Report within-contest pair order changes separately for OOF and full refits.

## Calibration-label anchor-contest influence

For each of the 15 CF contests in ascending ID order, exclude its entire label
group and canonical tasks. On the remaining cohort rerun outer contest LOCO.
Inside every outer fold select alpha/lambda using only its remaining training
contests, with DE as the sole candidate. Do not reuse settings selected with
the excluded or outer-held labels. Purge canonical tasks at every boundary.
Raw fits, standings, identity mapping, feature construction, and gym shape stay
fixed: this is calibration-label influence, not raw-fit/identity uncertainty.

Compare rerun RMSE to the saved original OOF predictions on exactly the same
remaining rows, as well as to freshly fitted controls. Save held/training IDs,
selected settings, predictions, per-contest scores, and prediction shifts.
No feature-bundle reselection or new candidate search is performed.

## Decision and checks

Source/provenance mismatch blocks result interpretation until repaired. A
deletion that reverses DE's gain over either control, or changes its matched
cohort RMSE by more than 5 CF points, triggers a concentration finding and a
narrower claim. Five points is a practical audit threshold borrowed from the
project's historical keep threshold, not a statistical confidence bound or
promotion rule. Report all deletions regardless of threshold crossings.

Test held/excluded-label mutation invariance, shared-task exclusion, deterministic
selection under row permutation, stale provenance rejection, and non-finite
prediction rejection. Reproduce the original baseline before interpreting
influence. Reused anchors cannot supply fresh confirmation; stable results
advance confirmation design only. Do not retune DE in response to these outcomes.
