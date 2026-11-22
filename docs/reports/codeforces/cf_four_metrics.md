# Can earlier solve times improve all four metrics?

**Success criterion.** Compare with the latest short-history and recalibration model, at full precision, on identical player–problem opportunities. Require lower log loss, Brier score and 20-bin pooled expected calibration error, and higher macro within-problem AUC. Select the lowest-loss qualifying challenger in 2025 before checking the same four directions in 2026. These are point-estimate criteria. The later period has been examined for previous model families.

**New information.** For each completed eligible Div. 2 round, compare each player's solve time with the median time of training-field solvers of the same task. Use log time ratios with a 60-second offset. Track separate discounted speed histories for tasks with predicted solve probability above and below 50%. Also track the player's frequency of solving nothing relative to the independent-task expectation, and time since their last eligible round. Retain 90% of these historical sums per appearance. A player with no such history receives a zero correction.

**Model and selection.** Interact each of these four features with a quadratic function of the incumbent solve probability. Fit one ridge-stabilized Newton correction on 2024 training handles. Try six correction strengths from 0.25 to 1.5 in steps of 0.25. Use only histories from rounds whose scheduled end precedes the target start; current-round times are queued for future rounds. The original problem calibration still uses the other contestants in the current field.

Run `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/cf_four_metrics.py` using the existing CF caches.

The initial six strengths all reduced loss and Brier error and increased AUC in 2025, but none passed calibration: ECE ranged from 0.001244 to 0.002710 versus 0.001222 for the incumbent. No timing-only candidate advanced. Before evaluating a challenger in 2026, we added two field-calibration strengths (0.5 and 1). This step uses the other players in the same round to estimate a smooth residual log-odds adjustment across all rated problem opportunities. The smoothing bandwidth is 0.65 logits and the information penalty is 10. Held-out outcomes do not enter the adjustment.

Neither single-round calibration strength qualified in 2025. We then tested pooling calibration evidence across successive rounds, retaining 90% of the previous gradient and information and resetting at each evaluation year. Each update uses only training handles. Three variants apply the full pooled correction, half of it, or the full correction with a small additional attenuation of extreme logits (0.015 × tanh(logit/2)). Selection continues to use 2025 only.

We also tested transferring the incumbent's training-field logit distribution onto the timing model's player ordering separately per problem, blending that transfer with the raw timing model, fitting task intercepts, and combining task and field calibration. Rank transfer with strength 1.25 was the lowest-loss 2025 qualifier. On the later 2026 period it improved loss, Brier and AUC but raised ECE from 0.001075 to 0.001298. We then tried weighting the timing adjustment by predicted solve probability, its complement, uncertainty, or the problem's training-field solve probability or complement. The same model remained the 2025 winner.

| Period | Model | Log loss | Brier | ECE | Within-problem AUC |
|---|---|---:|---:|---:|---:|
| 2025 | Incumbent | 0.19755138 | 0.06046434 | 0.00122228 | 0.87281935 |
| 2025 | Selected timing model | 0.19698391 | 0.06035228 | 0.00117251 | 0.87579171 |
| 2026 | Incumbent | 0.20186242 | 0.06137247 | 0.00107532 | 0.87001156 |
| 2026 | Selected timing model | 0.20088928 | 0.06116855 | 0.00129765 | 0.87468995 |

The later-period paired 95% interval for challenger minus incumbent ECE was −0.000389 to +0.000640. The other three intervals excluded zero in the favorable direction. The timing model did not meet the all-four criterion on 2026.
