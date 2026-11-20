# Official-field validation of fitted difficulties

The fitted survival-model difficulties are validated against **XCPCIO
official-field solve rates** — the subset of teams actually competing for medals.
This is an independent check: XCPCIO data was not used in the fit.

**Per-contest Spearman(difficulty, official solve rate): median −0.962**
over the 28 contests (range −0.657 to −1.000).  The equivalent full-field
correlation is median −0.978 — the official-field agreement is slightly
looser because the official field is smaller (median 335 vs 809 teams),
but the 0.016 gap is noise-level.  Overall Spearman over all 358 rated EA
problems: −0.940 (official) vs −0.972 (full field).  The model predicts
official solve rates nearly as well as full-field rates.

**Where unofficial teams distort the signal.**  20 of 358 problems (5.6%)
have a solve-rate gap ≥ 0.15 between officials and unofficials.  Direction
is inconsistent: on some contests unofficial star teams (often stronger,
e.g. UCup squads) find hard problems easier; on others (e.g. Hong Kong &
Macau 2022) the unofficial field is *weaker* and finds easy problems harder.
Both directions are local noise, not systematic bias.  The two outlier
contests in per-contest correlation are Xi'an 2023 (ρ = −0.657, only 36
official teams matched) and Grand Prix of Hong Kong 2025 (ρ = −0.804,
126 officials) — both have very small official fields where a handful of
solves determines the rate.

**Why not fit on official-only.**  Restricting the fit to XCPCIE-identified
official teams would discard 54% of EA solving rows (9,568 of 20,635) and
55% of cross-contest linking edges (162 of 364).  The unofficial entries
(UCup teams and rosters competing unofficially in regional mirrors) are the
cross-contest bridges that put every contest on one scale — the same
mechanism documented in the main unofficial-participants decision above.
Weighted approaches (downweighting unofficial observations) were also tested
and found decisively harmful (+17 RMSE; see the contest-link weighting
experiment).  The current strategy — all teams for fitting, XCPCIO for medal
cutoffs — is the correct split.
