# Calibration residual experiment

Status: research-only baseline/control result, refreshed 2026-09-08. No
production rating artifact or shipped calibration was changed. The full
185-anchor TabFM CF comparison is **not run**: the user explicitly deferred it.
The pinned weights are verified and cached for later, and a synthetic seven-feature
CPU smoke (170 train / 15 test) completed, but it has no TabFM CF score.
The verified runtime is TabFM 1.0.1 from official source `d8678b6`, with
torch 2.12.1+cpu.

The smoke took 8.772 s to load with eight threads and 12.925 s to fit/predict;
four threads took 21.820 s. One process peaked at 12.6 GiB. The nested full run
has 225 calls and is estimated at 45–55 minutes. It remains deferred at the
user's request.

## Question and protocol

Can completed-contest, deployment-available evidence improve the existing
Codeforces-point map? The experiment holds out one of the 15 CF-mirrored
contests at a time (185 anchor problems total). Each outer prediction is fit
without that contest's labels. Within the remaining contests, contest-grouped
folds select both ridge penalty (0.1, 1, 10) and residual shrinkage (0, .25,
.5, .75, 1). Explicit shared canonical tasks are also purged from the matching
training fold.

The fixed seven features are raw survival difficulty, binary-minus-survival
difficulty, conditional fit SE, solve rate, log field size, log median solve
time, and a timing-missing flag. IDs, names, regions, and any calibrated output
are excluded. The gym shape is locked before this experiment.

## Out-of-fold result

| map | CF LOCO RMSE |
| --- | ---: |
| Raw affine | 246.9061 |
| Locked gym-shape affine | 245.4277 |
| Nested ridge residual control | 229.6269 |

The ridge control beats raw affine in 11/15 held-out contests and gym-shaped
affine in 12/15. It loses to raw in CF contests 1949 (+10.6), 2041 (+29.5),
2045 (+2.7), and 2052 (+11.8) RMSE. Its losses to the gym map are instead 1938
(+20.0), 1949 (+8.7), and 2041 (+55.7). Thus the pooled result is not evidence
of uniform transfer.
Per-region RMSE (raw / gym / ridge) is Asia Pacific 219.9 / 211.5 / 208.8,
Europe 332.3 / 335.4 / 311.9, and Northern Eurasia 207.0 / 212.6 / 179.7.

This is still one small, reused external anchor set. It does not establish
regional transfer, probability calibration, uncertainty coverage, or a reason
to replace the shipped affine map.

## Diagnostics and limits

Across OOF anchor predictions, ridge changes only 2 of 1,064 within-contest
pair orders; its CF-order concordance is 969 versus 968 for raw affine. These
are order-preservation checks on the anchor evaluation, not full-fit evidence.

The all-anchor inner selection is alpha 1 and shrinkage .75, but the resulting
full-fit correction is explicitly **not OOF and not deployable**. It covers 94
of 3,159 fitted appearances outside the anchor raw-difficulty range
[1177.9, 2936.1]. Its corrections are descriptive only, including on the Luxor
shared-task panel below.

For the known Luxor shared-task panel, raw-affine to ridge gaps across the two
appearances are respectively 5.1 to 75.3 (8674), 6.3 to 17.6 (8676), 14.5 to
24.6 (8677), 66.0 to 125.3 (8680), and 53.2 to 3.0 (8683). A common task can
legitimately differ by contest context, so this panel is not a target for forced
equality.

### Cached transfer proxies

An existing cached full-fit diagnostic applies the same all-anchor inner choice
(alpha 1, shrinkage .75). It is **not OOF, not fresh confirmation, and not a
selection criterion**; it is included because the mixed transfer matters:

| proxy | n | gym-shape | ridge | interpretation |
| --- | ---: | ---: | ---: | --- |
| Gym pooled | 667 | .9691 | .9769 | improves |
| Gym East Asia Continent | 230 | .9774 | .9817 | improves |
| Kattis | 427 | .7955 | .7848 | worsens |
| AOJ within-contest | 45 | .5685 | .5587 | worsens |
| Gym, non-CF-anchor subset | 655 | .9693 | .9774 | improves |
| Kattis, non-CF-anchor subset | 412 | .7983 | .7900 | worsens |

The metrics are the pre-existing correlation/rank proxies used by their source
validators (not CF-point RMSE and not interchangeable across rows). AOJ has no
anchor overlap, so its row is already non-anchor. The opposite Gym and
Kattis/AOJ movements reinforce that a fresh, frozen transfer evaluation is
needed before any deployment decision.

## Reproduction

```bash
./.venv/bin/python -m arch_b.calibration_experiment --baseline-only
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The first command writes the provenance-hashed research artifact
[`output/calibration_experiment.json`](output/calibration_experiment.json). The
optional TabFM route requires the pinned local checkpoint directory (containing
`regression/model.safetensors` and `regression/config.json`), then verifies the
streamed model SHA-256 before loading it. Use an isolated process:

```bash
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 \
OPENBLAS_NUM_THREADS=8 \
TABFM_CHECKPOINT_DIR=/home/dedibeat/.cache/tabfm_runtime/checkpoints/google-tabfm-1.0.0-pytorch-77cb9cc1b4fd3a9c77fbb9552c218200bb4dab83 \
/home/dedibeat/.cache/tabfm_runtime/venv/bin/python -m arch_b.calibration_experiment --tabfm --tabfm-license-ack
```

A completed TabFM run records the verified model and config hashes. Its output
must be reported separately from the ridge proxy. Do not overwrite the
baseline-only artifact until this deferred full run is intentionally authorized.

## 2026-09-08 follow-up: selected-fit read-only diagnostic

This diagnostic ran no new model variant or hyperparameter search; it
reconstructed the 15 saved outer ridge fits from their saved selected
hyperparameters and feature rows. The saved OOF ridge predictions reproduced to
a maximum absolute error of `4.55e-13` CF points.

In the standardized residual fits, binary-minus-survival is positive in 15/15
outer folds, conditional fit SE is negative in 15/15, solve rate is positive in
15/15, and log field size is negative in 15/15. These are stable coefficient
signs, not feature attributions: binary-minus-survival and solve rate have
anchor-table correlation -0.95, and other prespecified features are also
correlated. In particular, this does not show that binary-minus-survival caused
the ridge gain.

For the 185 saved OOF predictions, 43.6% of ridge-minus-raw correction variance
is between held-out-contest means and 56.4% is within contest. The small count
of changed within-contest orders therefore does not make the correction merely
a contest offset. A per-contest CF-label-derived offset would nevertheless be
unavailable at deployment and is not a valid direction.

The focused next development experiment is prespecified grouped ablations that
separate estimator disagreement, non-time evidence, and timing features, while
retaining the same nested contest protocol. Region/source transfer stress checks
are development diagnostics; fresh frozen confirmation is still required, and
this pilot has no fresh frozen confirmation set. This follow-up reports no ablation
result, does not authorize a full TabFM run or an underlying-fit rewrite, and
does not support deployment.
