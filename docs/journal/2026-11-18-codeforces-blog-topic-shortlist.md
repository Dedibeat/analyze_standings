# Codeforces blog topic shortlist (2026-11-18)

- AI-era rating changes. Follow up the January–February 2025 break in
  cf_ai_deflation.md by reweighting rounds to a common division, pre-round
  rating and experience mix. Repeat with returning players and placebo dates
  in earlier years. This tests sensitivity to participation changes. Standings
  alone do not identify who used AI.
- Problem difficulty. Ask which rating predicts an independent group's
  timed solves best. Fit a standings-based rating on one field and evaluate
  the same problems in a later independent field, if such data can be found.
  Freeze all three ratings before evaluation. Compare against Codeforces and
  CLIST on the same players and problems using log loss, calibration by
  player rating, and paired uncertainty by contest. Verify CLIST coverage,
  rating timestamps, and independent evaluation data before claiming a win.

The [standings follow-up](../reports/codeforces/cf_standings_experiments.md) ran both first-stage experiments. Among 18,728 returning players in Div. 2, the standardized hard-gap observed/expected ratio rose .296 → .568 across February 2025. The 2024 placebo also rose (.147 → .283). In 56 rounds the difficulty pilot scored 0.20424 vs 0.21915 official mean log loss on held-out handles. A later timed field and dated CLIST ratings remain missing.

The ICPC 2PL transfer improved the CF pilot on the same 630,677 held-out opportunities. A learned slope per problem reduced log loss from 0.204245 to 0.201600 and improved 55/56 rounds, versus 0.203582 for a shared round slope. See the [protocol and paired intervals](../reports/codeforces/cf_standings_experiments.md#transfer-of-the-icpc-two-parameter-experiment).

A player-strength correction trained on 2024 rating histories reduced 2025 held-out solve log loss from 0.201600 to 0.201037 on the identical 630,677 opportunities, improving 44/56 rounds. Coefficients, timing assumptions and reproduction command are in the [player experiment](../reports/codeforces/cf_standings_experiments.md#modelling-pre-round-player-strength).

The [larger-history experiment](../reports/codeforces/cf_standings_experiments.md#searching-the-larger-history-for-lower-solve-log-loss) improved every evaluated Div. 2 round. Local curve calibration plus discounted player solve residuals reduced held-out loss 0.201037 → 0.197900 in 2025 and 0.206862 → 0.202352 in the later 2026 cache. Training coefficients used 2024 training handles only.

The [25-model history search](../reports/codeforces/cf_25_experiments.md) selected 0.95 retention and 16 probability bands on 2025. It reduced loss from 0.19789978 to 0.19762614 in selection and from 0.20235232 to 0.20198121 on the later 2026 rounds (34/43 improved). The report includes every selection score.

The [multi-metric search](../reports/codeforces/cf_metric_search.md) exhausted a six-family, 15,625-combination grid at a minimum gain of 0.00001. Recent history and calibration lowered later-period loss from 0.20198121 to 0.20186242 and improved Brier and calibration error. Within-problem AUC slipped by 0.000088.

The [timing-history experiments](../reports/codeforces/cf_four_metrics.md) improved all four metric point estimates in selection, but later-period calibration error went up. Solve-speed history was informative for ranking and loss. Weighting the correction by estimated solve probability did not change the winner.

An extended [five-hour CF search](../reports/codeforces/cf_five_hour_search.md) is testing cross-contest trees, per-problem field corrections and chronological refits. The protocol retains the four metrics and the original held-out population.


The five-hour all-metric search has completed. Five disjoint held-out handle partitions pool 2.16M predictions across the 2026 rounds. The loss-selected model improves all four point metrics over the incumbent. Its calibration-error interval includes zero, while loss, Brier and AUC intervals favor the new model. See [experiment design and full results](../reports/codeforces/cf_five_hour_search.md).
