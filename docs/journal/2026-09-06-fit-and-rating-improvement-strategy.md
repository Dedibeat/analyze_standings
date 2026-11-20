# Fit and rating improvement strategy (2026-09-06)

[rating_improvement_strategy.md](../reports/rating/rating_improvement_strategy.md) reviews the
measurement assumptions beyond the existing metrics at `c181982`. Fresh read-only
diagnostics on the shipped joint inputs find 525,259 omitted source problem cells
(56.9% of fitted cells), 2,052 dropped zero-solve rows with recorded wrong attempts,
and 142 fitted identity components whose source rosters have no member common to
all of them. These identify uncertainty about engagement and roster continuity;
they do not establish that every omitted cell or identity merge is wrong.

Five QOJ problem IDs occur in both Luxor World Finals (1661/1662), currently with
separate fitted difficulties. The official ICPC problem books corroborate the
shared tasks; saved CF-mapped ratings for Turning Red are 1844.7 and 1921.4.
This is a small existing panel for testing shared task identity and context,
not a demonstrated large scale error. The official event page also distinguishes
the April 2024 calendar event from the source's 2022/2023 season labels.

Recommended work starts with an audited panel of shared tasks, zero-solve
appearances with submissions, and influential roster chains, followed by separate
common-task and shrunk appearance-effect experiments. The larger model direction
is completion/time/engagement separation; targeted common-task attempts and
controlled hint studies could supply information the standings lack. The report
also distinguishes problem difficulty, team ability and rank performance, and
proposes useful evidence/uncertainty annotations for sparse problems. Sources,
input hashes, limitations and concrete checks are included. This task changed
documentation only; no model gain was measured, ratings regenerated, or paid
inference dispatched.

## Calibration and TabFM assessment (2026-09-06)

The strategy document now includes a [calibration/TabFM follow-up](../reports/rating/rating_improvement_strategy.md#calibration-and-googles-tabfm-2026-09-06-follow-up).
The current saved-record map comparison reproduces **246.9061 affine / 245.4277
gym-shaped CF LOCO RMSE**, with 185 anchors across 15 contests. Their raw
difficulty range is [1177.9, 2936.1]; 94 fitted appearances lie outside it.
Google's TabFM is recommended for a bounded research comparison as a conditional
residual correction using fit/evidence features, with simple calibration and
regularized-regression controls. Its potential value is learning when the scalar
fit needs correction; neither synthetic pretraining nor a lower development
error establishes regional transfer, probability calibration or valid intervals.
The report specifies contest-grouped selection, timing of feature availability,
context-sampling checks and the current weights' research-use restrictions.
At that time no TabFM inference or model changes were made. README's existing
strategy link continues to point to the expanded assessment.

## Nested calibration residual control (2026-09-08)

`arch_b.calibration_experiment` now records a bounded, research-only comparison
on the same 185 CF anchors in 15 contest-held-out folds. The outer contest's
labels are absent from every map and inner selection step; explicit canonical
shared tasks are purged from matching training folds. The prespecified features
are raw survival difficulty, binary-minus-survival difficulty, conditional fit
SE, solve rate, log field size, log median solve time, and a missing-time flag;
there are no IDs, regions, names, or calibrated-output inputs. Inner
contest-grouped selection covers ridge alpha {0.1, 1, 10} and residual shrinkage
{0, .25, .5, .75, 1}.

The refreshed baseline-only artifact reports **246.9061 raw affine / 245.4277
locked gym shape / 229.6269 nested ridge residual** CF LOCO RMSE. Ridge wins over
raw in 11/15 outer contests and gym in 12/15. The four losses to raw are CF
1949 (+10.6), 2041 (+29.5), 2045 (+2.7), and 2052 (+11.8); the three losses to
gym are instead 1938 (+20.0), 1949 (+8.7), and 2041 (+55.7). Per-region
raw/gym/ridge RMSE is Asia Pacific 219.9/211.5/208.8, Europe
332.3/335.4/311.9, and Northern Eurasia 207.0/212.6/179.7. The OOF anchor-order
check has 2 reversals among 1,064 within-contest pairs and CF concordance 968
raw -> 969 ridge; it is distinct from the non-OOF full-fit diagnostic. Cached,
non-OOF transfer proxies are mixed: gym pooled .9691 -> .9769 (n=667), gym EC
.9774 -> .9817 (n=230), Kattis .7955 -> .7848 (n=427), and AOJ .5685 -> .5587
(n=45); the non-anchor gym/Kattis subsets show the same directions. The full
detail, provenance hashes, and explicit non-OOF diagnostics are in
[calibration_experiment_report.md](../reports/calibration/calibration_experiment_report.md) and
`output/calibration_experiment.json`.

This measures only the regularized control on the reused anchor set; it does
not establish regional transfer, probability calibration, interval coverage, or
a production replacement. A pinned-weight, seven-feature CPU smoke completed
on synthetic 170-train/15-test inputs, but has no TabFM CF score. The full
185-anchor comparison is **not run** because the user explicitly deferred it;
the cached baseline-only artifact remains unchanged. With eight threads its
smoke load was 8.772 s and fit/predict 12.925 s (four threads: 21.820 s), while
one process reached 12.6 GiB; the 225-call nested comparison is estimated at
45–55 minutes. The verified runtime is TabFM 1.0.1 from official source
`d8678b6` with torch 2.12.1+cpu. The existing survival, binary, and calibrated
output artifacts were not regenerated.

The eventual isolated command is:

```bash
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 \
TABFM_CHECKPOINT_DIR=/home/dedibeat/.cache/tabfm_runtime/checkpoints/google-tabfm-1.0.0-pytorch-77cb9cc1b4fd3a9c77fbb9552c218200bb4dab83 \
/home/dedibeat/.cache/tabfm_runtime/venv/bin/python -m arch_b.calibration_experiment --tabfm --tabfm-license-ack
```

The local checkpoint contains `regression/model.safetensors` and
`regression/config.json`; the model SHA-256 is verified before loading and the
completed-run artifact records actual model/config hashes. It does not silently
download a model, and it must not overwrite the baseline-only artifact unless the
deferred run is deliberately authorized.

## Calibration selected-fit read-only diagnostic (2026-09-08 follow-up)

No new model variant or hyperparameter search was run; existing selected fits
were reproduced. Reconstructing all 15 saved outer ridge fits from the saved
selections and rows reproduced the saved OOF ridge predictions within
**4.55e-13 CF points**. In the standardized residual
fits, binary-minus-survival is positive in 15/15 folds, conditional fit SE is
negative in 15/15, solve rate is positive in 15/15, and log field size is
negative in 15/15. This is not causal or unique-feature evidence:
binary-minus-survival and solve rate correlate -0.95 across the anchor table,
with further correlation among the prespecified inputs.

Across the 185 saved OOF predictions, ridge-minus-raw correction variance is
**43.6% between held-out-contest means and 56.4% within contest**. Thus the two
changed orders among 1,064 pairs do not imply a pure contest-offset correction;
nor would a per-contest offset learned from held-out CF labels be deployable.

The bounded next development direction is prespecified, same-protocol grouped
ridge ablations separating estimator disagreement, non-time evidence, and
timing features, plus region/source transfer stress checks explicitly labelled
development diagnostics. They require fresh frozen confirmation before a
deployment decision; this pilot has no fresh frozen confirmation set. These diagnostics do not
claim ablation results, prove that the disagreement feature caused the gain,
authorize the deferred full TabFM comparison, or justify an underlying-fit
rewrite.

## Frozen calibration feature-group ablation (2026-09-08)

The approved research-only ablation is recorded in
`output/calibration_ablation.json`, with the frozen protocol in
[`calibration_ablation_plan.md`](../reports/calibration/calibration_ablation_plan.md). It retains
`raw_b` in every ridge residual fit and separately tests disagreement (D),
non-time evidence (E), and timing (T), including all seven nonempty D/E/T
bundles. Nested 15-contest LOCO RMSE is **246.9061 raw / 245.4277 gym / 241.7094
D / 238.2049 E / 247.3457 T / 226.5661 DE / 245.2137 DT / 241.1893 ET /
229.6269 DET**; the inner-only adaptive selector also scores **226.5661** and
selected DE in every outer contest fold. The retained DET control reproduces
every old ridge OOF prediction exactly and its selected settings exactly.

The separate calibration-label leave-one-region-out diagnostic gives **248.6523
raw / 246.0305 gym / 243.4531 D / 237.5236 E / 248.6584 T / 225.7640 DE /
243.2424 DT / 242.2078 ET / 228.3597 DET / 226.9881 adaptive**. Its adaptive
choice is DET (Asia Pacific) and DE (Europe, Northern Eurasia). This holds only
completed-contest standings/raw fits fixed while excluding all labels from the
held region before baselines, preprocessing, and inner contest selection; it
is a calibration-label transfer stress check, not a future-contest forecast.

Both protocols are exploratory development on the reused anchors, not fresh
confirmation or a production-promotion decision. No TabFM import, download, or
run occurred, and the existing production artifacts and baseline experiment
artifact remain unchanged.

The concise result and transfer caveats are in
[calibration_ablation_report.md](../reports/calibration/calibration_ablation_report.md). Full-anchor
transfer refits are explicitly non-OOF and mixed: DE improves cached pooled gym
Spearman (.9691 to .9780; n=667) but is lower on Kattis (.7955 to .7760; n=427)
and AOJ within-contest (.5685 to .5642; n=45). Removing only canonical anchor
tasks gives non-anchor gym/Kattis counts 659/416; the stricter whole-anchor
contest plus task purge gives 655/412, reproducing the historical reported
counts. These are distinct subset definitions, not confirmation of a global
replacement.

## Proposed experiment roadmap (2026-09-08)

[experiment_roadmap.md](../reports/rating/experiment_roadmap.md) records proposed, not-run
diagnostics and later research directions. It recommends retaining DE unchanged
as the candidate for a prospective confirmation design, distinguishes OOF,
full-refit, and fresh-confirmation evidence, and requires provenance/identity/
context audits before any model change. It does not authorize a model or data
run, production promotion, or the explicitly deferred TabFM comparison.

## Autonomous DE prediction audit and anchor influence (2026-09-10)

The request to work autonomously on prediction improvement led to a bounded
execution of the roadmap's correction/source audit and calibration-label
contest-influence study. The protocol was written before execution in
[calibration_audit_plan.md](../reports/calibration/calibration_audit_plan.md); implementation is
`arch_b.calibration_audit`, with full findings in
[calibration_audit_report.md](../reports/calibration/calibration_audit_report.md) and research predictions
in `output/calibration_audit.json`. No candidate features or production map changed.

All 3,159 survival/binary problem appearances agree with the joint loader and
cached sources on task/title/solve-count/field-size provenance. All 185 anchors
have unique cached contest-scoped CF matches. Previous artifact input hashes
match, and OOF prediction replay differs by at most 7.74e-12 CF points. The
baseline remains **246.9061 raw / 245.4277 gym / 226.5661 DE** LOCO RMSE.

Each of the 15 CF anchor contests was removed in turn, with its canonical tasks
purged before rerunning nested DE-only selection on the remaining cohort
(210 outer fits). DE beats raw and gym in all 15 deletions. Comparing to the
original OOF predictions on exactly the same remaining rows, refitting changes
DE RMSE by **-2.91 to +1.80 points**, below the frozen 5-point audit threshold.
Individual predictions can still move by 117.9 points. This is calibration-label
sensitivity with the raw fits fixed, not independent replication or uncertainty.

The largest-correction audit selects 23 unique OOF anchors and separately saves
all 3,159 full-refit rows with source links, features, predictions, and marginal
training-range flags. **1,840 appearances (58.2%) exceed at least one DE feature
range**, including 1,610 outside the anchor field-size range of **77–323 teams**;
only 94 exceed the raw-difficulty range. Seven of the ten largest full-refit
corrections are in Aobayama's 50-team field, with a maximum +534.3-point shift,
although its raw difficulties are within anchor support. These are extrapolation
diagnostics, not proof of errors or calibrated risk probabilities.

Both Luxor appearances of all five shared tasks pass cached identity/title
checks. Riddle of the Sphinx's gap is 5.1 raw / 101.0 DE, and Turning Red's
is 66.0 / 145.3; external task-version/context equivalence remains unverified.
No source defect was reproduced, so no data or identity correction was made.
Fresh confirmation labels, actual recorded durations, and adjudicated roster
identity remain missing. The next confirmation design needs small/large fields
and other evidence-feature regimes in addition to regions/raw-difficulty bands.

All 64 tests pass, including label-mutation leakage checks, task purges,
deterministic example selection, training-only support flags, stale provenance,
and finite predictions. Prior experiment and production artifacts are unchanged;
TabFM remains deferred. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.calibration_audit`.

## BigQuery and Google Cloud TabFM plan (2026-09-10)

The user requested a cloud experiment plan, specified **BigQuery and a $10
total spending limit**, and pointed out native TabFM availability through
`AI.PREDICT`. [tabfm_cloud_plan.md](../reports/calibration/tabfm_cloud_plan.md) now plans that managed
route directly, superseding the initially considered CPU VM. Official Google
Cloud documentation confirms Preview compute billing and token pricing starting
October 30, 2026. No VM, GPU, or checkpoint deployment is needed.

The plan preserves seven features, task-purged nested contest folds, residual
shrinkage selection, and 225 inference calls, comparing managed TabFM against
raw/gym affine, DET ridge, and the newer DE ridge OOF control. The managed API
exposes no checkpoint/seed/ensemble/context controls in its documented signature,
so the result must be labelled as a managed-backend comparison, not a replay of
the pinned local checkpoint. A separate bounded wrapper remains to be implemented.

The Preview plan limits all query jobs to 300, each capped at 1 GiB, for about
$1.84 query compute before free allowances/credits at the provisional
`us-central1` rate, plus a small storage allowance. It specifies job accounting,
alerts, a stop margin, table expiration, and cleanup within the user's $10
ceiling. The project, credit details, region requirements, and Preview access
remain unverified; cloud execution is pending.

Read-only checks matched the 11 baseline input hashes and experiment-source
hash. The exact nested schedule contains 36,260 training-row appearances and
2,775 prediction-row appearances, corresponding to $0.01603025 per ensemble
in future model-token charges, excluding query compute. Ensemble count is
unexposed, so that is an illustration rather than a service quote. There are
184 distinct seven-feature vectors among 185 anchors; the plan therefore
requires verified prediction-ID passthrough instead of joining on feature values.

`gcloud`/`bq` are installed. No paid queries, cloud resources, TabFM inference,
or production changes were made. README links the plan, and prior experiment
artifacts remain unchanged. The separate local-checkpoint run stays deferred.

## Managed BigQuery TabFM execution (2026-09-10)

The planned managed experiment was executed in `test-gemeni-501216`,
`us-central1`, after a native smoke test verified finite prediction-ID
passthrough for two identical feature vectors. A project-scoped, gross-spend
budget alert was created at $2/$5/$8; every executable query was dry-run first
and capped at 1 GiB. The seven-feature, task-purged nested protocol completed
all **225** calls with a persistent deterministic job ledger. It records
4,718,592,000 billed bytes (4.395 GiB); the dedicated dataset was deleted after
local archival.

Managed TabFM residual OOF RMSE is **231.2865 CF points**, versus 246.9061 raw,
245.4277 gym, 229.6269 DET, and **226.5661 DE**. It improves the affine controls
but loses to DE, so this is a negative research pilot: no production calibration,
rating, feature, or backend search changed. The result is
`output/calibration_tabfm_bigquery.json`; the concise report is
[tabfm_bigquery_report.md](../reports/calibration/tabfm_bigquery_report.md). The local pinned-checkpoint
run remains separate and deferred.

## TabFM / DE audit and shipped-fit update preparation (2026-09-10)

[shipped_fit_update_plan.md](../reports/rating/shipped_fit_update_plan.md) records the audit and
concrete calibration-release dependencies at `b935754`.
`arch_b.shipped_fit_audit` verifies prior provenance, reconstructs the entire
managed manifest, and replays all 225 archived responses, inner shrinkage choices,
and outer predictions exactly. The experiment ledger accounts for 4,718,592,000
billed bytes; the separate two-job smoke adds 41,943,040 bytes. This checks local
evidence, not an independent invoice or remote-cleanup confirmation. DE's nested
selection and full refit reproduce the existing artifacts; its full-anchor
settings remain alpha=1, lambda=1. No new inference or model search occurred.

Development RMSE remains **245.4277 shipped gym / 226.5661 DE / 231.2865 managed
TabFM**. DE wins 9/15 contests against each, while TabFM is slightly better on
the pooled Europe anchors. There is no fresh-confirmation or significance claim.

The new research artifact `output/shipped_fit_audit.json` stages all 3,159
appearance-level DE values beside the actual shipped ratings, using the existing
[800,4000] bounds and one-decimal display policy. There are 259 rated contests;
the loader's 260th entry, contest 1120, has no rated problems. Proposed changes
average +75.98 points, have median absolute change 113.9, and move 1,737 ratings
by at least 100 points. Aobayama 1965 H moves 2151.5 -> 2711.4 (+559.9). These
are comparisons with shipped gym calibration, not the earlier raw-affine
correction audit. The display comparison has 105 changed orders/new ties among
18,142 previously non-tied within-contest pairs; 1,840 appearances remain outside
at least one anchor feature range. No support fallback was introduced.

The update plan identifies duplicated scalar-map construction in calibration,
viewers, UCup export, virtual calculation and medals. DE has no defined
problem-feature vector for team abilities or medal bars, and existing gym-based
uncertainty fields cannot simply accompany DE predictions. Current raw-order
metric guards also do not test a DE postprocessing layer. Fresh confirmation,
extrapolation/uncertainty/badge policies and downstream app integration remain
release requirements. The managed runner's feature-only run ID and recovered
load jobs also require content binding before any changed-label rerun; the
current archived manifest matches, so this is a future reuse defect rather than
evidence that the completed pilot used wrong inputs.

All **72 tests pass**, including five new offline replay corruption/missing-input
checks. Every existing output's hash is verified unchanged before the audit
artifact is written. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.shipped_fit_audit`;
the gitignored original managed archive is required and missing files cause an
error rather than new cloud inference. Production fit, calibration and exports
are unchanged; the audit prepares a reviewable update but does not promote DE.

## Explaining DE / TabFM and proposing next work (2026-09-10)

[calibration_interpretation.md](../reports/calibration/calibration_interpretation.md) explains the
existing results and records the user's requested future plan. The reproducible
diagnostic `arch_b.calibration_interpretation` reconstructs the selected DE
coefficients and saves `output/calibration_interpretation.json`; it performs no
new candidate search, production refit, or TabFM inference.

The full DE fit expands to approximately **0.934742 survival_b + 0.876768
binary_b + evidence terms + intercept**: its difficulty component is a roughly
52/48 survival/binary blend with rescaling. Disagreement/SE/solve-rate/field-size
coefficient signs are stable across all 15 outer folds, but they are correlated
inputs, not independent causal effects. Disagreement and solve rate correlate
**-0.952** on anchors. For Aobayama's 12 Grid they instead reinforce the
correction, contributing +155.7 and +282.0 points relative to anchor means;
small field size contributes +70.5 of the +531.4 raw-affine correction.
This highlights joint feature support, beyond individual range flags. Across
all appearances the disagreement term contributes +60.06 of the average
+73.35 DE-minus-raw shift. OOF correction variance is 40.8% between contest
means and 59.2% within contests.

The survival MAP first-order condition implies
`SE(b) = [k/s² + (b-MU0)/(s*sigma_b²) + 1/sigma_b²]^(-1/2)` for interior,
unweighted default fits, where k is solve count. This reconstructs saved SEs
with median error 0.0247 and maximum 0.0508, consistent with rounding and finite
convergence. SE therefore mainly contributes nonlinear solve-count information
to E; including it as a predictor does not calibrate prediction uncertainty.

Managed TabFM used seven features; the matched DET ridge control is 229.63
RMSE versus TabFM 231.29, while five-feature DE is 226.57. Their OOF correction
correlation is .722; selected TabFM shrinkages are .75 in nine folds and .5 in
six. A descriptive paired 15-contest bootstrap of fixed predictions (20,000
resamples, seed 20260910) gives 2.5–97.5 percentile RMSE-difference ranges
**[-34.45,-2.27] DE-minus-gym**, **[-13.94,+6.48] DE-minus-TabFM**, and
**[-9.76,+7.63] DET-minus-TabFM**. These do not refit or adjust for benchmark
selection and are not fresh confirmation. TabFM has not demonstrated a gain;
its inferiority to ridge is not established.

The proposed sequence is a fixed-panel decomposition of estimator disagreement,
three prespecified leave-one-E-feature-out controls, fresh confirmation covering
joint feature regimes and regions, then coordinated opt-in integration and
scope-limited promotion if supported. Missing durations, adjudicated context,
fresh labels and uncertainty remain explicit. These are proposals only; all
earlier experiment/production artifacts remain unchanged. Reproduce with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ./.venv/bin/python -m arch_b.calibration_interpretation`.
