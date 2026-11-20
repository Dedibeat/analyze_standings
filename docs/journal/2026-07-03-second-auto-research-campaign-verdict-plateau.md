# Second auto-research campaign (2026-07-03, DeepSeek v4 Pro): verdict PLATEAU

A second 25-iteration campaign (`program.md`) probed data-side identity
improvements and model hyperparameters at the new **288.0** baseline (after
the identity fixes above). **0 fit-side iterations kept; the WF identity
linking was kept as a correctness change** — the model is confirmed at a
robust local optimum.

**Gym-informed difficulty prior: kept, then reverted on review.** The
campaign's iteration 1 soft-anchored ~667 problem difficulties toward
`output/gym_difficulty.json` (N(b_gym, 400²) prior mean; commit `80afc92`,
implemented post-campaign — review found the original "KEPT" log entry had
never actually been committed). Metric 288.4 → 288.0 (−0.4, far under the
±5 noise floor), so the keep leaned on guard corroboration — but the
corroborating guards (gym EC +0.962 → +0.969, gym pooled +0.954 → +0.959)
are **circular** for this change: pulling `b` toward `b_gym` mechanically
raises Spearman against `b_gym`. The genuinely independent signals did not
corroborate (held-out AUC flat at 0.8858; Kattis pooled *down* 0.795 →
0.790), the change carried a mild target leak (qoj 2692 is both
gym-covered and a CF anchor contest, where `b_gym` correlates +0.976 with
the official CF ratings), and it had a structural cost: with `b_gym` baked
into the fit prior, the gym guards stop being an independent watchdog for
the unanchored regions. Reverted (`3fb0eca`). The principled home for the
gym signal is the calibration layer (per-region CF map on `b_gym` anchors)
or the likelihood via merged gym *observations*, not a prior on `b`.
Campaign-log caveat: several phase-3 TSV sweep rows compare against 286.3
— a *discarded* σ_θ=500 config — rather than the 288.0 incumbent, so those
deltas are not baseline-relative.

**Everything else was within noise or worse.** sigma_θ sweeps (300→600)
best at 500 (−1.7 RMSE but AUC regressed 0.8858→0.8849, discarded per
corroboration rule).  Data-side changes — script-mismatch linking
(Chinese↔English names, 60 teams), last-name-only matching (30 teams),
name-order-robust tokenisation — all within ±0.7 points of baseline.
Tighter per-problem gym priors (σ_b ~ gym SE) blew up the metric to 306
(kattis guard nearly failed).  Wrong-attempt penalty in the survival
likelihood regresses at any α > 0.  min_solve_hours variations have
no effect (CF anchors are a fixed set).  A World Finals affiliation
bridge (4 WF contests fetched, 33/36 WF rosters already matched) was
neutral.

**WF → regional linking (KEPT).** Four World Finals contests (2022–2025,
534 teams) were fetched via `qoj-intergration/qoj.py` and saved to
`data/wf_tagged_format.json`.  ``load._link_wf_top_team`` maps each
(university, season) to the best-ranked regional team and links the WF
identity to that team's roster — the WF team *is* the university's top
team for that season.  9 new cross-contest links are created (e.g.
Universidad de Buenos Aires → "Está en el Corman", Purdue → "Purdue
GLD").  The gym EC guard improved (+0.960 → +0.962) confirming better
Asia East Continent connectivity, though the CF-RMSE metric is blind
to these links (the linked universities don't appear in the 15
CF-anchor contests).  Only the identity links are used; WF solve
data is not loaded into the fit (WF problems differ from CF-anchor
problems).

**wrong_attempts wired.** The `wrong_attempts` field (present in
`tagged.json` but previously unused) is now loaded into
`Dataset.wrong` for future model use, though the tested penalty
models (multiplicative Lambda scaling) did not improve the metric.

Full per-iteration log in `autoresearch/autoresearch-260703-1838/classic-results.tsv`.
