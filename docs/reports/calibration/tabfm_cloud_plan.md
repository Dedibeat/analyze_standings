# TabFM experiment directly in BigQuery

Status: proposed research experiment, 2026-09-10. The user requested **BigQuery
and a $10 total spending limit**. No cloud resources, paid queries, or TabFM
inference were launched while preparing this plan.

## Decision

Run **managed TabFM through BigQuery `AI.PREDICT`**, orchestrated by a small local
Python script. Keep features, fold membership, predictions, and SQL evaluation
in BigQuery. No VM, GPU, downloaded checkpoint, or separately hosted model is
needed. Google announced the native integration on September 1, 2026; see the
[official announcement](https://cloud.google.com/blog/products/data-analytics/tabfm-adds-predictive-ml-to-bigquery).

The earlier proposed CPU-VM approach is superseded by this plan. This is a new
managed-backend comparison, not execution of the deferred pinned local model.
The function's documented arguments do not expose checkpoint revision, seed,
ensemble count, or context-size controls. Preserve our statistical protocol,
record the service/date/job metadata, and report those backend settings as
unexposed rather than claiming equivalence to the local checkpoint. The API
supports up to 20 features; our seven fit. Its prediction input can include
extra columns, while every non-label training column becomes a feature. See the
[`AI.PREDICT` reference](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-predict).

Use an on-demand BigQuery dataset, provisionally in `us-central1`, with seven-day
table expiration. The region is a planning choice, not a confirmed requirement;
verify native-function availability and project pricing there before execution.
Only small derived experiment tables need uploading; source standings and local
checkpoints remain local. Managed-service terms apply to this route; the local
weights' separate license acknowledgment is not evidence of managed-service
terms, nor a reason to download weights for this experiment.

## Cost and the $10 limit

The user's supplied pricing is confirmed by Google's current documentation:
before **October 30, 2026**, Preview uses ordinary BigQuery compute billing
(bytes for on-demand, slots for Enterprise/Enterprise Plus). From that date,
TabFM input/output tokens are additionally priced at **$0.05/$0.20 per million**,
with ordinary compute billing for the rest of the query. Current on-demand
pricing includes 1 TiB/month free, then $6.25/TiB at the planning location;
storage has a 10 GiB monthly free allowance. See
[BigQuery pricing, including TabFM](https://cloud.google.com/bigquery/pricing).

Do not assume the free allowance is unused or that the user's actual credit
balance is $300. Budget gross usage before promotional credits, across all jobs,
retries, and retained tables. The expected tiny-table spend should be well below
$10, potentially $0 within the remaining free allowance. It is an estimate, not
an observed bill.

| Resource | Proposed bound | Gross allowance before credits |
| --- | --- | ---: |
| Inference | 225 nested calls, plus up to 10 smoke/diagnostic calls | Included in Preview query compute |
| All query jobs | At most 300 total, each capped at 1 GiB billed | At most about $1.84 at $6.25/TiB |
| Logical table storage | At most 0.1 GiB, seven-day expiration | Allow $0.10 |
| Planned allowance | Before taxes; excludes no assumed free allowance | About $1.94 |
| User's total ceiling | All experiment costs including contingency | **$10.00** |

The query estimate is `300 / 1024 * $6.25 = $1.8311`. The 300-job limit includes
inference, evaluation, verification, and retries; upload/export jobs are logged
separately. Batch-load small local NDJSON files, download small result files,
and use no paid hosting, storage bucket, slots reservation, or scheduled jobs.

For reference after the pricing change, the present task-purged 225-call schedule
has 36,260 training-row appearances and 2,775 prediction-row appearances. With
seven features plus one residual label, the published formula gives:

```text
input_tokens  = (36,260 * 8 + 2,775 * 7) * E = 309,505 * E
output_tokens = 2,775 * E
model_cost    = $0.01603025 * E
```

Thus E=8 would be about $0.1282 for model tokens, plus ordinary query compute.
**E is not exposed in the current documented API**; this is an illustration,
not an asserted service default or complete future quote. Reprice before any
run on/after October 30; query byte caps must not be treated as token-charge caps.
The row totals above were calculated locally from the current anchor table,
without inference.

Enforce the following before execution:

1. Submit one query at a time under one recorded project/location. Dry-run each
   query and set `maximum_bytes_billed=1073741824` on every executable query.
   Require the synthetic smoke to confirm this setting works with `AI.PREDICT`;
   if billing cannot be bounded this way, stop and report before the full run.
2. A persistent local submission ledger reserves one of the 300 query slots
   before submission, recording a deterministic job ID, query/input hashes,
   purpose, timestamps, bytes billed, and result location. Recover an existing
   job by ID after a connection failure; do not blindly resubmit and pay twice.
3. Configure a project daily query quota of 0.1 TiB if supported. It is an
   approximate extra safeguard and resets daily, so keep the aggregate 300-job
   limit across every day and restart. See
   [query byte limits](https://docs.cloud.google.com/bigquery/docs/best-practices-costs)
   and [custom quota limitations](https://docs.cloud.google.com/bigquery/docs/custom-quotas).
4. Set project-scoped budget alerts at $2, $5, and $8, calculated before
   promotional credits. Stop submissions if projected total usage plus retention
   and taxes reaches $8, leaving $2 for reporting lag. Alert-only budgets are
   not automatic spending stops; see
   [billing budget behavior](https://docs.cloud.google.com/billing/docs/how-to/budgets).
5. Abort on quota/billing/schema failures instead of raising limits. Cancel a
   stalled job and stop after a four-hour orchestration window, retaining its
   job ID and status. Runtime is unmeasured; the local CPU timing is not a
   managed-service runtime estimate. Cancellation alone is not a cost guarantee.
6. Archive results locally, expire tables after seven days, verify cleanup and
   final gross costs. Use a dedicated dataset with logical billing and an
   explicit expiration; see [dataset settings](https://docs.cloud.google.com/bigquery/docs/datasets).

These limits keep the proposed workload comfortably inside $10. They do not
claim an instant, universal Google Cloud billing cutoff. If an account-specific
rate or restriction invalidates the estimate, revise the plan before spending.

## Frozen scientific protocol

Question: can managed TabFM improve the CF-point map for completed contests,
beyond our strongest simple regression control, on identical held-out contests?

| Method | Existing contest-LOCO CF RMSE | Role |
| --- | ---: | --- |
| Raw affine | 246.9061 | Basic control |
| Locked gym-shape affine | 245.4277 | Shipped-map control |
| Seven-feature ridge (DET) | 229.6269 | Same-feature control |
| Five-feature ridge (DE) | 226.5661 | Strongest existing development candidate |
| Managed TabFM residual | Not measured | Proposed candidate |

Freeze all 185 anchors across 15 CF contests through
`arch_b.calibration_experiment.build_anchor_table`. Freeze source hashes, raw
survival/binary fits, cached CF labels, gym shape, canonical tasks, and row order.
Do not refresh external sources or refit the standings model for this pilot.

Use the same ordered seven features as the existing experiment:
`raw_b`, `binary_minus_survival`, `conditional_fit_se`, `solve_rate`,
`log_field_size`, `log_median_solve_seconds`, `timing_missing`.
IDs, names, regions, calibrated outputs, and held-out CF labels are excluded
from the model feature projection.

For each outer held-out CF contest:

1. Remove its labels and purge its canonical tasks from training.
2. Within the remaining 14 contests, hold out each inner contest in turn and
   repeat the task purge. Fit the raw affine map on inner training rows only.
3. Form training residuals `cf - affine(raw_b)` on those training rows. Send only
   their seven features and residual target to `AI.PREDICT`; send inner-test
   features and a prediction-only alignment identifier, without any test label.
4. Cache inner residual predictions. Choose shrinkage lambda from
   `(0, .25, .5, .75, 1)` by pooled inner MSE of
   `affine(raw_b) + lambda * predicted_residual`; exact ties retain listed order.
   Each inference result is reused for all five lambdas.
5. Refit the affine map/residual context on all eligible outer training rows,
   predict the outer contest once, and apply the chosen lambda. Evaluate its
   held-out labels only after the prediction is fixed.

This requires `15 * (14 + 1) = 225` managed inference calls. No automated feature,
seed, ensemble, backend, or model search is included. Do not replace grouped
folds with a random SQL split or use automatic evaluation that changes our splits.

Reproduce the raw/gym/DET controls locally using the existing code. Import DE
OOF predictions from `output/calibration_ablation.json` only after verifying
exact row IDs, labels, features, purged folds, and provenance. Its protocol is
nested DE-only alpha/lambda selection; the older experiment runner emits DET,
not DE. Do not reimplement ridge in BigQuery ML and silently change the control.
All comparisons remain development evidence on repeatedly inspected anchors;
DE's past selection is not fresh confirmation.

## BigQuery tables and inference query

Use explicit schemas and run-specific keys. Build derived data locally, then
batch-load it into a dedicated dataset such as `tabfm_research`.

| Table | Required contents |
| --- | --- |
| `anchors` | Run/row IDs, row order, CF and source contest IDs, canonical task, region, CF label, seven FLOAT64 features |
| `fold_membership` | Run ID, outer/inner contest, row ID, role (`train`, `test`, `purged`); NULL inner contest denotes outer fit |
| `contexts` | Call ID, training-row ID, seven features, FLOAT64 residual target; training rows only |
| `queries` | Call ID, prediction-only `prediction_row` INT64, seven features; mapping to canonical row ID is kept separately |
| `predictions` | Run/row ID, method, outer contest, region, CF, prediction, lambda, `is_oof` |
| `runs` | Protocol/source/input hashes, service/date/config, status, job ledger and result-file references |

Use the following SQL pattern per call, with project and call parameters filled
by the future wrapper. The training projection is deliberately explicit:

```sql
SELECT *
FROM AI.PREDICT(
  (SELECT raw_b, binary_minus_survival, conditional_fit_se, solve_rate,
          log_field_size, log_median_solve_seconds, timing_missing,
          CAST(residual AS FLOAT64) AS residual
   FROM `PROJECT_ID.tabfm_research.contexts`
   WHERE call_id = @call_id),
  (SELECT prediction_row, raw_b, binary_minus_survival, conditional_fit_se,
          solve_rate, log_field_size, log_median_solve_seconds, timing_missing
   FROM `PROJECT_ID.tabfm_research.queries`
   WHERE call_id = @call_id),
  label_col => 'residual'
);
```

Expect `predicted_residual`; verify prediction-only `prediction_row` survives in
the output and maps one-to-one to the requested rows. **Do not rely on SQL row
order or join on feature equality:** the 185 anchors currently contain only
184 distinct seven-feature vectors. The reference's output prose is ambiguous
about returned input columns, so identifier passthrough is a required smoke
check. If it fails, report the missing behavior instead of inventing IDs as
training features or silently changing to one-row calls.

Scores can be independently recomputed with:

```sql
SELECT method,
       COUNT(*) AS n,
       COUNT(DISTINCT cf_contest) AS contests,
       SQRT(AVG(POW(prediction - cf, 2))) AS rmse,
       AVG(ABS(prediction - cf)) AS mae,
       AVG(prediction - cf) AS signed_bias
FROM `PROJECT_ID.tabfm_research.predictions`
WHERE run_id = @run_id AND is_oof
GROUP BY method;
```

Reject duplicate keys, NULL/non-finite values, missing methods, or incomplete
coverage before scoring. The final OOF table contains 925 rows: 185 per method
across five methods. Pooled RMSE is computed over problems, not averaged from
contest RMSEs. Also report per-contest/per-region errors, paired differences to
DE/DET, chosen lambdas, and within-contest order reversals. Require SQL/Python
metric agreement within `1e-6` CF points.

## Preparation, execution gates, and deliverables

1. **Local preparation:** implement a separate managed-backend wrapper, schema
   exporter, bounded job ledger, and SQL templates. Reuse the existing affine,
   split, residual, and scoring logic. Save a new
   `output/calibration_tabfm_bigquery.json`; preserve baseline and production
   hashes. Test held-label mutation, both task purges, explicit feature
   projections, duplicate-feature row alignment, and resume-by-job-ID behavior
   using a fake service before paid work. Commit the execution snapshot.
2. **Cloud smoke:** within the ten-call diagnostic allowance, test synthetic
   regression with all seven feature columns, two prediction rows having
   identical features but different prediction IDs, finite outputs, identifier
   passthrough, byte caps, and job statistics. Repeat identical input once to
   measure service repeatability; record any variation rather than asserting a
   fixed seed. Verify that changing locally held evaluation labels leaves the
   submitted training/prediction tables and SQL unchanged.
3. **Control/provenance gate:** confirm all source hashes, 185/15 coverage,
   complete fold manifests, exact uploaded features and IDs, and baseline OOF
   replay within `1e-6`. Require DE artifact alignment before interpreting a
   TabFM score. No result-based protocol adjustment is allowed after this gate.
4. **Nested run:** submit the 225 calls sequentially. Persist each response and
   selected settings with its input hash, job ID, bytes, and timing immediately.
   Resume only from verified completed calls; a changed input/backend protocol
   is a new run. Infer inner contexts separately so no other fold's labels can
   enter the current prediction.
5. **Report and clean up:** save raw responses, context/fold manifests, OOF
   predictions, SQL, local environment, code/plan hashes, query ledger, elapsed
   time, and estimated/settled gross costs. Publish a repository research report
   and update README/details. Verify existing production and experiment files
   are unchanged and remove temporary tables after local archival.

An optional paired contest bootstrap of the saved OOF error differences can use
10,000 draws and seed `20260910`, retaining every problem from each sampled
contest. It describes fixed-error variability, not uncertainty accounting for
historical model selection. Successful execution and lower RMSE are separate
outcomes. If TabFM fails to beat DE, report the negative result and stop this
pilot. A win motivates fresh confirmation, not a production switch.

The latest audit found 1,840/3,159 full-refit appearances outside at least one DE
feature range, especially field size (anchor fields contain 77–323 teams).
Fresh confirmation should cover evidence/field-size regimes as well as regions
and difficulty bands. No such labels are available yet. This pilot does not
establish regional transfer, solve-probability calibration, or valid prediction
intervals. Five-feature TabFM, regional holdouts, stability sweeps, and
full-population predictions require a separate prespecified follow-up.

## Missing information and current verification

Before execution, record the intended GCP project/billing account, credit balance
and expiry/eligibility, available BigQuery permissions, required region, and
Preview access. The user's $10 ceiling is known; the pasted $300 example does
not establish their remaining balance. If access/region or output alignment is
unsupported, report it rather than switching services. `gcloud` 583.0.0 and `bq`
are installed locally; cloud account access has not been checked.

This task authorizes planning. The managed wrapper and cloud smoke are not yet
implemented/run; the earlier local-checkpoint run remains deferred. Ordinary
`python -m arch_b.calibration_experiment --tabfm` still selects the local CPU
backend and overwrites its default research artifact, so it is not the command
for this managed plan.

Read-only planning checks matched all 11 baseline input hashes and the existing
experiment source hash, reconstructed the 225-call fold counts/token arithmetic,
and found the duplicate feature vector noted above. Official native-function and
pricing documentation was verified on 2026-09-10. Existing model artifacts were
not modified, and no managed or local TabFM inference was performed.
