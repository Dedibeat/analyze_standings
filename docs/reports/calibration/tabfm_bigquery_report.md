# Managed BigQuery TabFM residual experiment

Executed 2026-09-10 on BigQuery `AI.PREDICT` in `us-central1`. This is a
research-only managed-backend comparison on the existing 185 CF anchors in 15
contest-held-out folds; it is not a replay of the local checkpoint and does not
change the shipped calibration.

All 225 prespecified, sequential calls completed. Training and test contexts
used the frozen seven features, task-purged grouped folds, and a training-only
raw-affine residual target. Prediction-row passthrough was verified by a
two-identical-feature smoke test. Every query was dry-run first and capped at
1 GiB; the ledger records 4,718,592,000 billed bytes (4.395 GiB). The dedicated
tables were deleted after local archival.

| Method | OOF RMSE (CF points) |
| --- | ---: |
| Raw affine | 246.9061 |
| Gym-shaped affine | 245.4277 |
| Ridge DET | 229.6269 |
| Ridge DE | **226.5661** |
| Managed TabFM residual | 231.2865 |

TabFM beats raw and gym controls but not the frozen DE control, so this is a
negative pilot result. No production change or follow-up backend/feature search
is justified by it. Full predictions, selected shrinkages, provenance hashes,
and the local archive path are in `output/calibration_tabfm_bigquery.json`.
