# Gemini zero-shot × survival experiment

Model: `gemini-3.5-flash`; requests: 2128; problems: 185; contests: 15.
Actual estimated inference cost: **$5.4270** (budget $50.00).

A/B order consistency: 0.816 (868/1064).
BT pairwise accuracy vs official CF ratings: 0.752.
Nested LOCO survival RMSE: 275.68; fused RMSE: 282.31; improvement: -6.63 CF points.
Contest bootstrap probability fusion is worse: 0.733.

## Sparse BT stability

Selected robust sparse schedule: **10 unordered matches/problem** (mean and minimum Kendall both at least 0.90).

| unordered matches/problem target | mean Kendall | minimum Kendall |
|---:|---:|---:|
| 4 | 0.852 | 0.733 |
| 6 | 0.916 | 0.811 |
| 8 | 0.952 | 0.892 |
| 10 | 0.974 | 0.921 |

## Gate result

- `loco_improvement_ge_5`: FAIL
- `bootstrap_worse_lt_10pct`: FAIL
- `order_consistency_ge_80pct`: PASS
- `sparse_kendall_ge_090`: PASS
- `under_budget`: PASS
