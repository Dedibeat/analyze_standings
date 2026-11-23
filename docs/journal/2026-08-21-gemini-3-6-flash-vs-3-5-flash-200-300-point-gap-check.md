# Gemini 3.6 Flash vs 3.5 Flash: 200/300-point gap check (2026-08-21)

The existing frozen, statement-only Codeforces baseline pairs were reused so
both models saw identical inputs and both A/B orientations. The subset had 46
ordered requests at an exact 200-point rating gap and 52 at an exact 300-point
gap per model (196 requests per model total). The API model IDs
`gemini-3.6-flash` and `gemini-3.5-flash` both returned valid JSON decisions.

Accuracy is the empirical probability of selecting the higher-rated problem;
intervals are two-sided 95% Wilson intervals. The API schema returns only A/B,
so these are benchmark correctness probabilities, not calibrated confidence
scores for individual answers.

| model | gap | correct | accuracy (95% Wilson CI) | A/B order consistency |
|---|---:|---:|---:|---:|
| Gemini 3.5 Flash | 200 | 21/46 | 45.7% [32.2%, 59.8%] | 78.3% |
| Gemini 3.6 Flash | 200 | 16/46 | 34.8% [22.7%, 49.2%] | 82.6% |
| Gemini 3.5 Flash | 300 | 31/52 | 59.6% [46.1%, 71.8%] | 57.7% |
| Gemini 3.6 Flash | 300 | 30/52 | 57.7% [44.2%, 70.1%] | 84.6% |

3.5 has the higher point estimate on both gaps, but the intervals overlap and
paired exact McNemar tests do not establish a model winner (p=0.302 at gap 200;
p=1.000 at gap 300). The notable signal is consistency: 3.6 is much less
sensitive to A/B order, especially at the 300-point gap. The raw predictions
are retained in the gitignored `gemini_gap_run/` directory.
