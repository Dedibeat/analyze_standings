# Multi-metric search on Codeforces standings

Keep the previous 0.95-retention, 16-band winner as the incumbent. Reproduce its loss on the original rows before interpreting the comparisons. Fit residual logistic corrections using only 2024 training handles. Search weights on 2025 held-out handles. Read 2026 metrics only after selection.

Six correction families will test recent vs long-run solve history, nonlinear responses to player history, reliability as a function of history depth, a smooth recalibration of the final probability, calibration by problem position, and calibration by the current problem's average predicted difficulty. Each family is fitted separately around the incumbent using a ridge-stabilized Newton update. Search discrete additive weights 0, 0.5, 1, 1.5 and 2. Starting at all zero, try every one-family weight change, including removals. Accept the largest reduction in 2025 log loss of at least 0.00001 whose Brier score also stays level or improves. Repeat until all neighbors fail; that is the stopping condition for this search space.

Report opportunity-weighted log loss, Brier score, pooled expected calibration error (20 fixed equal-width probability bins), and within-problem AUC averaged over problem entries with both outcomes. Use a paired round bootstrap for the final loss difference. ECE and AUC are diagnostics. The previously inspected 2026 period is a later-period check, not a pristine blind holdout.

After the single-family search, check the whole 5⁶ grid for a simultaneous move that meets the same loss threshold and Brier constraint. A lower bound avoids scoring clearly inferior combinations. For each cell take the minimum curvature of logistic loss over its attainable logit interval. Sum the resulting quadratic lower bounds around a continuous reference fit. Any grid point that could still pass is scored exactly. The bound is valid for any reference point, independently of optimizer convergence. On ten small synthetic grids the stopping condition was also verified by scoring every combination directly.

Brier score is the mean squared probability error. Calibration error is the weighted mean absolute difference between predicted and observed solve rates in the 20 bins. Within-problem AUC asks whether the model ranks a randomly chosen solver above a randomly chosen non-solver of the same problem, awarding half credit to ties. Problems with only one outcome have no such pairs and are excluded from AUC alone.

## Results

| Period and model | Opportunities | Log loss ↓ | Brier ↓ | Calibration error ↓ | Within-problem AUC ↑ |
|---|---:|---:|---:|---:|---:|
| 2025 incumbent | 630,677 | 0.19762614 | 0.06048974 | 0.00155261 | 0.87281953 |
| 2025 selected | 630,677 | 0.19755138 | 0.06046434 | 0.00122228 | 0.87281935 |
| 2026 incumbent | 427,752 | 0.20198121 | 0.06141786 | 0.00154597 | 0.87009956 |
| 2026 selected | 427,752 | 0.20186242 | 0.06137247 | 0.00107532 | 0.87001156 |

The first accepted change added the short-minus-long solve-history correction at weight 1 (2025 loss 0.19757013). The second added smooth recalibration at half strength. None of the other four families passed the advancement rule. After 72 single-family neighbor evaluations the global lower bound ruled out all 15,625 combinations at the 0.00001 improvement threshold. Smaller gains and other model families remain possible.

The final model improved loss in 38/56 selection rounds and 31/43 later rounds. Paired 95% intervals for selected minus incumbent loss were [−0.00011510, −0.00003500] in 2025 and [−0.00018495, −0.00005344] in 2026. AUC covered 335 and 277 problem entries respectively. Calibration improved in both periods while within-problem ranking slipped slightly. Both models use other contestants' responses to calibrate the current problem.

Reproduce with `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/cf_metric_search.py` using the same populated CF caches as the earlier experiments.
