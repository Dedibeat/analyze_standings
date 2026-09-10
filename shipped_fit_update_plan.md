# TabFM / DE audit and shipped-fit update preparation — 2026-09-10

**DE remains the candidate; a global default replacement is not ready.** The
managed TabFM result and DE controls replay successfully, but the development
gain does not resolve DE's feature extrapolation, mixed transfer evidence, or
the consumers that currently assume one scalar calibration map.

This task prepares a calibration update on the existing survival/binary fits.
It does not change the joint estimator, data, production ratings, viewers, or
cloud resources. No new TabFM inference or feature/backend search was run.
The starting revision is `b935754`.

## Verified evidence

The new offline command, `arch_b.shipped_fit_audit`, verifies the prior experiment,
ablation, transfer, and DE-audit provenance before reading current features.
It compares the rebuilt managed manifest with the complete archived manifest:
rows, labels, features, row order, training residuals, baselines, prediction
queries, and every outer/inner fold membership all match.

All 225 archived response files have the expected finite prediction rows.
Recomputing every inner shrinkage selection and outer prediction reproduces
the managed result **exactly**. The 225 completed ledger entries match the
reconstructed call/SQL hashes and account for **4,718,592,000 billed bytes**;
the separate two-job smoke ledger adds **41,943,040 bytes**. Both duplicate
feature rows survive in the smoke evidence. This is local archival verification,
not an independent billing invoice or remote dataset-deletion check.

The SQL supplies only seven features and a floating-point residual label to
training; prediction-row IDs occur only in the prediction query. Google's
[AI.PREDICT reference](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-predict)
defines training features by the non-label training columns and permits extra
prediction columns. The local smoke supplies the additional evidence for ID
passthrough. The documented API has no seed/checkpoint controls, so archival
replay does not establish fresh-call reproducibility or reproduce the deferred
local-checkpoint experiment.

DE's 15 outer fits rerun the frozen grouped inner selection and reproduce both
the ablation predictions and the DE control copied into the TabFM artifact.
The full-anchor selection remains **alpha=1, lambda=1**, using `raw_b`,
binary-minus-survival, conditional fit SE, solve rate, and `log1p(field size)`.
All 3,159 full-refit predictions match the earlier DE audit within 1e-7 CF points.
Held-out-label mutation and canonical-task purge checks pass in the test suite.
The underlying standings fits remain fixed, so these are calibration-label
holdouts, not future-contest forecasts.

| Nested contest OOF method | RMSE | MAE |
| --- | ---: | ---: |
| Raw affine | 246.9061 | 177.9281 |
| Shipped gym-shaped affine | 245.4277 | 177.3648 |
| DET ridge | 229.6269 | 163.2777 |
| DE ridge | **226.5661** | **162.4440** |
| Managed TabFM | 231.2865 | 164.3890 |

DE improves RMSE by **18.86 points (7.7%)** against shipped calibration and
4.72 points against managed TabFM. It wins in **9/15 contests against each**;
the aggregate advantage is not universal dominance. For example, CF 1949 is
170.0 gym / 200.2 DE / 140.4 TabFM, and CF 2041 is 180.4 / 223.8 / 208.4.
TabFM is slightly better on the pooled Europe anchors (307.95 versus 310.77
DE); DE is better on Asia Pacific (204.28 versus 207.18) and Northern Eurasia
(176.59 versus 196.03). These subgroup results do not justify selecting a
different backend by region. All labels belong to the reused development set;
there is no fresh confirmation set or new significance claim.

## Concrete candidate versus the actual shipped ratings

[`output/shipped_fit_audit.json`](output/shipped_fit_audit.json) contains one
review row per problem appearance: contest/label/task identity, existing shipped
CF value, unbounded DE prediction, proposed displayed DE value, displayed delta,
and feature-range flags. Proposed display values use the existing [800,4000]
clipping and one-decimal rounding. There is **no new support fallback, correction
cap, or clipping rule chosen from these outcomes**. This file is a research
comparison, not a production-schema ratings file; it supplies no DE uncertainty
estimate.

The current shipped CF values reproduce the gym map applied to the saved
survival fit at the existing rounding. Coverage is 3,159 problem appearances
in **259 rated contests**. The joint loader contains 260 contest entries;
contest 1120 contributes no rated problems. These counts describe different
objects and should not be interchanged in release checks.

| Effect of the displayed DE candidate | Result |
| --- | ---: |
| Mean change from shipped CF | +75.98 |
| Median absolute change | 113.9 |
| 90th / 95th percentile absolute change | 296.4 / 347.2 |
| Maximum absolute change | 559.9 |
| Appearances changing by at least 100 / 200 / 400 | 1,737 / 848 / 52 |
| Unbounded predictions below 800 / above 4000 | 13 / 3 |
| Outside at least one anchor feature range | 1,840 (58.2%) |
| Outside anchor field-size range, 77–323 teams | 1,610 |
| Changed displayed order or new tie, among non-tied shipped pairs | 105 / 18,142 |

The largest displayed change is Aobayama 1965 H, *12 Grid*: **2151.5 → 2711.4**
(+559.9), in a 50-team field below anchor support. This differs from the earlier
audit's maximum +534.3 correction because that audit compared unbounded DE to
**raw affine**, whereas this table compares the proposed display with the
**shipped gym calibration**. Likewise, the earlier 103 full-refit order changes
were unbounded comparisons with raw; the 105 here include display clipping and
rounding. Neither count is the two OOF anchor order reversals.

The existing cached **non-OOF**, unbounded DE transfer diagnostics have matching
input provenance:

| Proxy | Shipped monotone ordering | DE | Existing guard floor |
| --- | ---: | ---: | ---: |
| Gym pooled, n=667 | .9691 | .9780 | .92 |
| Gym East Asia, n=230 | .9774 | .9823 | .93 |
| Kattis NA/Europe, n=427 | .7955 | .7760 | .75 |
| AOJ within-contest, n=45 | .5685 | .5642 | .52 |
| Median solve-count sanity | — | .9986 | .90 |

DE clears these existing floors, but the Kattis/AOJ declines remain relevant.
The current `arch_b.metric` guards evaluate raw model difficulties, whose order
the gym map preserves. They would **not detect** a regression introduced by a
new DE layer. Candidate and displayed-output guards must be evaluated explicitly
before a release. Passing these development floors would still not supply fresh
confirmation or validate the 1,840 extrapolated appearances.

## Findings that affect implementation

1. **A JSON-only replacement would leave conflicting ratings.**
   `calibrate.py`, `export_viewer.py`, `export_ucup_only.py`,
   `export_virtual_calc.py`, and `medals.py` independently construct the gym map.
   Several exporters also refit at full precision while JSON calibration uses
   rounded saved raw values. A release needs one versioned problem-calibration
   artifact and an appearance-keyed consumer path, with documented rounding.
   Match on `(contest_id, problem_label)` and corroborate `problem_id`; task ID
   alone merges distinct shared-task appearances such as the Luxor pair.
2. **DE is not a scalar ability/performance map.** It needs problem-specific
   disagreement, SE and solve rate. Those inputs are undefined for an arbitrary
   team theta, virtual performance, or medal threshold. Preserve the existing
   scalar map for those quantities and explicitly distinguish the axes if DE
   problem ratings are introduced. Never insert DE values into the raw survival
   likelihood or silently substitute problem features for team features. Medal
   badges are defined on raw fitted order; DE's reordered CF values no longer
   guarantee the old monotone badge/CF-threshold interpretation.
3. **Existing uncertainty fields cannot simply accompany DE predictions.**
   `difficulty_cf_fit_se` uses the gym map derivative and
   `difficulty_cf_level_sd` comes from the gym-based hierarchical residual model.
   Their partial quadrature is already not a calibrated prediction interval.
   A DE release must either supply separately justified uncertainty or explicitly
   mark it unavailable; copying the old fields would misattribute uncertainty.
   Full joint/calibration uncertainty remains missing.
4. **The managed runner is unsafe to reuse with changed labels.**
   `build_manifest()` hashes only feature values into `run_id`;
   `BigQueryService.upload()` derives load-job IDs from that ID and recovers
   conflicting jobs without checking uploaded contents. Thus changing labels
   keeps the same upload IDs, although residual contexts change. The prediction
   job hash also lacks the full uploaded context content. Before any future
   managed run, bind immutable uploads and predictions to full input-content
   hashes (labels, memberships, order and residuals included), reject mismatched
   recovered jobs, and isolate datasets by run. Preserve the completed historical
   archive instead of retroactively relabelling it. This risk does not invalidate
   the current result: its complete rebuilt manifest matches the saved archive.
   The runner was audited, not rewritten or rerun in this task.

## Prepared update sequence and acceptance checks

1. **Freeze the release contract and confirmation cohort.** Keep DE's features,
   alpha/lambda selection protocol and existing display bounds fixed. Obtain
   fresh labels covering small/large fields and disagreement/SE regimes as well
   as regions and raw difficulty. Specify promotion thresholds before inspecting
   those labels. No such cohort is present today. The fallback for extrapolated
   cases and the treatment of uncertainty/badges are explicit release decisions
   still to be made; this audit does not invent those policies.
2. **Build an opt-in problem-calibration artifact.** Store method/version,
   training/source hashes, feature order and definitions, affine coefficients,
   training-only standardization, ridge coefficients, selected alpha/lambda,
   display rules and support ranges. Preserve raw survival/binary artifacts.
   Verify serialized predictions against the staged 3,159-row table within 1e-7
   before display rounding. Missing features, mismatched raw-fit provenance,
   duplicate appearances and non-finite results must stop the build.
3. **Integrate every problem-rating consumer together.** Main calibrated JSON,
   Architecture B viewer, UCup-only export and virtual-calculator problem rows
   must agree on overlapping appearance keys at their declared display precision.
   Keep team performance and medal-bar semantics explicit as described above.
   The documented sibling `../my-react-app` consumer is a separate release
   dependency; its current ingestion/schema and deployment were not audited
   here. Verify them before publishing a coordinated update.
4. **Validate the proposed release, then promote.** Rerun nested calibration
   evaluation, raw-fit guards, DE and displayed-output transfer guards, feature
   coverage and the frozen fresh-confirmation checks. Add integration coverage
   for exporter parity, raw probability invariance, missing uncertainty, and
   virtual/medal behavior. Keep OOF scores separate from full-anchor refit values.
   Update the metric's meaning and documentation together with any default change.
5. **Publish and rollback as one artifact set.** Record exact raw-fit and
   calibration versions in every export. Retain the current gym outputs and their
   hashes (snapshotted in this audit) so rollback restores the complete set,
   including UCup/viewer/calculator and downstream app data. Do not rerun cloud
   inference or retrain the estimator as part of this calibration-only release.

## Reproduction and limits

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  ./.venv/bin/python -m arch_b.shipped_fit_audit
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  ./.venv/bin/python -m unittest discover -s tests
```

The audit writes only `output/shipped_fit_audit.json` and verifies every existing
output's hash before publication. It requires the gitignored
`tabfm_bigquery_run/tabfm_61dfe4abe56d461e/` archive; if absent, restore that
archive from the original run. A missing archive is an error, never permission
to rerun paid inference. The tracked result records archive/input/source hashes
and contains the full review table, so the conclusions remain inspectable
without cloud access. All **72 tests pass**, including five new offline replay
tests for missing/corrupt responses, prediction IDs, duplicate identities,
selection and metrics. Existing cache-reader ResourceWarnings are unrelated.

Fresh confirmation labels, recorded contest durations, adjudicated roster/task
context, DE uncertainty, and the release policies above remain missing. The
completed audit and review artifact prepare the next implementation decision;
they do not establish that global promotion is warranted.
