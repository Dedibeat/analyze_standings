# Five-hour Codeforces solve-prediction search

The requested window starts at 04:03:54 UTC on 2026-11-19 and ends at 09:03:54 UTC. The primary reference is the model at commit dcc8b87. On 2026 it scored 0.20186242 log loss, 0.06137247 Brier, 0.00107532 twenty-bin calibration error and 0.87001156 within-problem macro AUC. Improvement in all four means strict directional improvement on identical opportunities. Report point estimates and paired round uncertainty separately.

## Discovery and confirmation

1. Extend the historical features to include solve speed, rating history, earlier rank, time away, problem position and overlap with six algorithm-topic families. Queue current results until the round ends. The target problem is already known and its curve is fitted on other contestants, as in the original benchmark.
2. Fit gradient-boosted decision trees on 2024 training handles, using the incumbent logit as the initial prediction. Search full, history and behavior feature subsets, tree sizes, regularization, number of boosting iterations, correction strength and field calibration. Write an atomic checkpoint after each completed trial. Only 2025 development metrics can select models.
3. Prefer candidates improving all four 2025 metrics. Among those maximize the smaller number of improved metrics in the two chronological halves, then minimize full-period log loss. Record the full development comparison for each completed trial. Evaluate a locked finalist on the previously inspected 2026 field and report any metric that regresses. Repeated later-period comparisons are exploratory.
4. Use remaining time for a distinct challenger or a reproducibility check on a different field split. Include uncertainty intervals and inspect where any improvement concentrates. Stop starting new jobs in time to verify and commit the results by the requested deadline.

The reusable panel and model checkpoints live in the ignored CF data cache. The search requires NumPy, SciPy and LightGBM (tested version 4.7.0).

**Additional families and checks specified during discovery.** The field model fits ridge-regularized per-problem coefficients using the training players in the current round. Its field-calibration inputs are scored with two interleaved training folds for the residual correction. The rolling tree model also uses player histories from earlier rated rounds of every available division. It estimates past rank performance against the earlier rating field, tracks decay, volatility, missed easy tasks, hard solves, timing and earlier performance on individual tags. It refits four times per evaluation year, using only training handles in contests that had ended before each cutoff. Features use the cached problem-tag snapshot. Historical tags are not individually timestamped. The estimand is retrospective solve prediction for a known task.

Each alternate handle partition holds out a disjoint range of 51 SHA-256 first-byte values. Its problem curves and history calibration are recomputed using that partition's training field. The primary partition remains the same as in all previous experiments. An alternate-partition replay is a robustness check in the same contests; it is not independent evidence from a new season.

For ensemble selection, lock one 2025 winner per family, then compare 15 quarter-step logit mixtures of the three models at overall strengths 0.65 and 1. The loss finalist follows the preceding selection rule. A second, balanced finalist uses the same full-period and two-half criteria, then maximizes the weakest of the four improvements divided by its paired round-bootstrap standard error. The latter gives calibration a voice when candidate loss improvements are clear but ECE improvements are small. Publish both finalists and retain the original against which they were selected.

## Reproduction

Use the CF standings and rating-change cache described in the README and the repository's problem-set metadata. The CPU runs set `OPENBLAS_NUM_THREADS=1`. The commands below build local caches and search journals; use a future Unix timestamp for each search deadline.

```sh
.venv/bin/python scripts/cf_boost_data.py
.venv/bin/python scripts/cf_boost_data.py --from-year 2022
.venv/bin/python scripts/cf_cross_history.py
.venv/bin/python scripts/cf_field_search.py
.venv/bin/python scripts/cf_factor_search.py
.venv/bin/python scripts/cf_boost_search.py --until "$fixed_search_deadline"
.venv/bin/python scripts/cf_rolling_boost.py --until "$rolling_search_deadline"
.venv/bin/python scripts/cf_confirm_models.py final --freeze
.venv/bin/python scripts/cf_confirm_models.py final --year 2026
```

For a disjoint replication partition, build both panel variants with the same `--fold` (1 through 4), and pass that fold to confirmation. The 2025 and 2026 field-calibration labels come only from the corresponding training handles. As in the earlier benchmark, later field rankings and solve times are never used as current-player features. The all-division rank-performance estimate uses a 99-quantile approximation to the earlier contest rating field.

Before reading any latent-factor results, we added a fourth family to the ensemble grid. This expands it from 15 to 35 possible quarter-step mixtures at each overall strength and includes every original three-model mixture at zero factor weight. The factor model learns multidimensional player profiles from earlier solve patterns. It estimates each current task's factor loadings using the training field and delays each player's history update until the round ends. Dimensions, history retention and ridge strength are selected only on 2025. This tests whether a standings-derived player profile contributes beyond rating, speed and earlier rank.

The rolling winner's training-data, timing, rank and task-specialization ablations reuse the first locked recipe and 2025 opportunities. For the final calibration audit, recombine the five disjoint evaluation folds within each contest and problem before computing macro AUC. Check sensitivity to 10, 20 and 40 reliability bins. A diagnostic estimates the expected finite-sample ECE under independent perfectly calibrated Bernoulli draws using a normal approximation per bin; repeated contestants and correlated tasks make this a reference calculation. Also report loss and Brier for earlier-defined 1000–1599 players on tasks at least 600 points harder and tasks at or below their rating.
