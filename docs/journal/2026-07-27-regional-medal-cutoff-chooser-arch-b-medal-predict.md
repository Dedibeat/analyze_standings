# Regional medal-cutoff chooser (`arch_b.medal_predict`)

The default command now answers the decision question directly: rank the eight
ordinary 2026 Asia East regional sites by the predicted gold cutoff.  `--target
silver|bronze` changes the medal target, `--cities ...` compares a supplied
shortlist, `--city` prints all three bars for one host, and `--report` retains
the descriptive city/time analysis.  Lower bar = historically softer cutoff;
it is not a probability that a particular team medals.

**Shipped model.**  Prediction uses the 25 ordinary regionals from 2022–2025
only.  For each medal tier, city `c` with `n_c` observations is partially
pooled with one overall-mean pseudo-contest:

`pred(c) = (sum(city bars) + overall regular-regional mean) / (n_c + 1)`.

An unseen city receives the overall mean.  Gold, silver, and bronze are fitted
directly rather than imposing average gaps.  EC Finals are excluded from every
ordinary-city baseline (the old code mixed the 2023 Shanghai EC Final into the
Shanghai regional estimate and then added an EC-Final premium again).  A
requested EC Final uses the separate two-final mean.  Year, temporal order,
and field size are deliberately excluded from future recommendations: order
varies inconsistently by season, field size is uninformative, and extrapolating
the small year coefficient made the 2026 estimates artificially easy.

**Decision-metric validation.**  A rolling-origin check trains strictly on
earlier seasons and predicts the 19 regular regionals in 2023–2025.  With the
corrected full-cell ratings, the shipped one-pseudo-contest city model achieves
**105.0 CF RMSE**, **86.5 CF MAE**, and **47.9% correct within-season pair
ordering** (48 pairs).  The RMSE is useful as a broad uncertainty scale, but
the pair ordering is weak in this snapshot, so the ranking is only a rough
shortlist. Each CLI interval is explicitly labelled a historical RMSE band,
not a 68% confidence or medal probability.

**2026 choice.**  [ICPC Global](https://icpc.global/regionals/results) listed
Chengdu, Hong Kong, Nanchang, Nanjing, Shanghai, Shenyang, Wuhan, and Xi'an as
the ordinary 2026 Asia East sites on 2026-07-27.  Dates/order were still blank;
online rounds and the EC Final are not selectable ordinary medal regionals and
are excluded.  For gold, the point leaders are Hong Kong 2506, Shanghai 2518,
and Shenyang 2526 CF; their gaps are tiny relative to the 105-CF forward error
and every candidate's band overlaps.  The output therefore presents a ranking
plus evidence counts and warns that travel/cost, school quotas, eligibility,
registration limits, and this year's applicant strength remain outside the
model.  The candidate list is source-dated in code instead of silently assuming
unpublished dates.

**QOJ archive audit (not shipped).**  The user identified QOJ's 2015–2021 Asia
East category archive as a possible way to add signal.  The 2015–2016 regional
mirrors are incomplete (zero official teams and only 2–11 practice rows), so
they are unusable.  The 18 ordinary 2017–2019 mirrors are complete five-hour
standings, and for every 2017–2021 stored regional QOJ's server-side
official-only set equals the `$DEFAULT...` team-id set exactly; no
official-field guess is needed.  Nevertheless, adding the 6.8 MB 2017–2019
solve data is neutral/slightly worse on the global fit (calibrated LOCO 261.6
→ 261.8 CF, all guards pass), and using all 2017–2021 medal bars worsens the
same 2023–2025 decision holdout to **160.9 CF RMSE / 51.0% pair ordering**.
Older Nanjing/Shanghai fields do not transfer well enough to the recent regime,
so neither the archive data nor its bars are added merely to increase sample
size.

**Host correction.**  QOJ category 460 names contest 1099 “The 2022 ICPC Asia
Hong Kong Regional Contest,” while the medal artifact's shortened contest name
is “Hong Kong & Macau.”  The old substring loop encountered `Macau` first and
misclassified it.  `CONTEST_CITY` now maps 1099 explicitly to Hong Kong; a test
locks the source-backed correction.

Run: `./.venv/bin/python -m arch_b.medal_predict`.  The older interactive
`output/medal_predict_viz.html` remains a descriptive city/time view; it is not
the 2026 recommendation interface.
