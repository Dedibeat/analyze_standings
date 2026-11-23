# How much solve history should count?

We ran a 5 × 5 search for lower deadline-solve log loss. Each cell is a separately fitted player-history model. All 25 share the previous model's player eligibility, problem calibration, chronological history and held-out handles. The incumbent is an additional control outside the grid.

## What each experiment changes

- **History retention per eligible appearance** is 0.65, 0.80, 0.90, 0.95 or 0.98. These values give a past round half its original weight after roughly 1.6, 3.1, 6.6, 13.5 or 34.3 further appearances. Inactivity between appearances does not decay the history.
- **Number of predicted-probability bands** is 1, 2, 4, 8 or 16. Bands have equal width on the probability scale. An 8-band model, for example, can use a different correction for a problem with a 5% chance of solution than for one with a 20% chance.
- Each player has two predictors available before the round: historical excess solves on easier tasks and on harder tasks. We start each challenger with the previous model's frozen coefficients. For each band we estimate an additive coefficient for each predictor using one Newton update on 2024 training handles, with a ridge penalty of 100 on the information diagonal. Aggregating the gradient and information from the finest partition gives the exact same update as accumulating directly within each coarser band.

## Selection and verification

Build histories from completed rounds starting in 2021. Fit the corrections with 2024 training handles. Evaluate every variant in 2025, choose the lowest opportunity-weighted mean loss, and score only that choice on the available 2026 rounds. The 2025 winner's loss is a selection score. The 2026 period was already examined for the incumbent in an earlier experiment, but the grid and winner-selection rule did not use the challengers' 2026 losses. The 95% interval resamples whole rounds with replacement 10,000 times.

Reproduce from the populated CF caches:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/cf_history_sweep.py
```

## All 25 selection scores

The incumbent scored **0.19789978** on 630,677 opportunities in 56 rounds. Lower is better.

| History retention | 1 band | 2 bands | 4 bands | 8 bands | 16 bands |
|---:|---:|---:|---:|---:|---:|
| 0.65 | 0.19831219 | 0.19830282 | 0.19828898 | 0.19821664 | 0.19809960 |
| 0.80 | 0.19800686 | 0.19800925 | 0.19800218 | 0.19793603 | 0.19783502 |
| 0.90 | 0.19780802 | 0.19780631 | 0.19780489 | 0.19775216 | 0.19766859 |
| 0.95 | 0.19777568 | 0.19774199 | 0.19773957 | 0.19769625 | **0.19762614** |
| 0.98 | 0.19784598 | 0.19775999 | 0.19775163 | 0.19771412 | 0.19765252 |

Sixteen variants improved on the incumbent. All five short-history models at 0.65 lost, even with the finest bands. Sixteen bands gave the lowest loss at every retention tested. Pushing retention from 0.95 to 0.98 gave back a little of the gain.

## Later-period result

| Period | Opportunities | Incumbent | Selected model | Relative reduction | Rounds improved |
|---|---:|---:|---:|---:|---:|
| 2025 selection | 630,677 | 0.19789978 | 0.19762614 | 0.14% | 43/56 |
| 2026 through November | 427,752 | 0.20235232 | 0.20198121 | 0.18% | 34/43 |

The selected model retained 95% of history per appearance and used 16 probability bands. Its later-period reduction was 0.00037111, with a paired round-bootstrap 95% interval of 0.00026128–0.00048160 for incumbent minus challenger. This is incremental improvement over the previous best on the same rows. Scores use other participants' outcomes to calibrate each current problem; pre-contest prediction for an unseen problem remains a separate task.
