# The optimization metric (`arch_b.metric` + `program.md`)

With validation settled (every anchored region agrees at +0.86–0.98), the open
front is the **scale**, so model improvement is now driven by a single scalar:
the shipped two-leg map's **calibrated leave-one-contest-out RMSE in CF
points**. The verifier refits the model, applies the locked gym-learned monotone
shape (`NBINS=15`, `ALPHA=0.75`, qoj 2692 excluded), then for each CF-rated
mirror contest fits the affine leg on the *other* mirrors, predicts the held-out
one, and pools the errors. This measures the shipped deliverable
(`difficulty_cf`) directly while preventing the loop from retuning calibration
against the same anchors. `metric.py` auto-maps
**all** rated mirrors in `data/cf_team_contests.txt` via the
`external_validate` name-vote machinery: currently **185 problems / 15
contests**. Three mirrors were *added to the list* by sweeping every tagged
contest's problem names against the rated CF problemset (contest-level vote):
CF 2157 ↔ qoj 2692 (found by the gym certification), plus CF 1773 (2022–23
NEF) and CF 1938 (2024 APAC) found by the exhaustive sweep — which also showed
**no further rated mirrors exist** for our 146 contests, so anchor growth now
requires new contests in the fit. After the 2026-08-08 full-cell mask correction,
the current calibrated survival baseline is **244.2**; raw affine LOCO is
**245.2** and remains a guard with ceiling 293.4. The previous 261.6/285.0
figures were the pre-correction baseline, where omitted no-attempt cells were
excluded from the likelihood.

**Noise floor (cluster bootstrap, contests as resampling units):** for the
legacy raw-affine metric, pooled RMSE carried **SE ≈ ±20 points** (95% CI ≈
[251, 327]); the calibrated metric's own sampling SE has not been separately
estimated. Paired comparisons on the same anchors are sharper, but an
auto-research loop must still **treat single-digit improvements as noise**
(`program.md` sets a ~5-point keep threshold, requiring Kattis, AOJ, or
held-out-AUC corroboration for small wins) because repeatedly selecting on a
fixed 185-anchor set overfits it in a way LOCO cannot detect.

**Guards.** The CF anchors cover only AsiaPac / N.Eurasia / Europe, so a loop
optimizing RMSE alone could silently regress the unanchored regions. The same
fit is therefore checked against floors (baseline − noise margin, calibrated to
the survival model): gym **EC** Spearman ≥ 0.93 (the region with *no* CF
anchors), gym pooled ≥ 0.92, Kattis pooled (NA+Europe convention) ≥ 0.75, AOJ
within-contest Spearman ≥ 0.52, and within-contest solve-count sanity ≥ 0.90.
Raw affine LOCO must remain ≤ 293.4 so the nonlinear calibration cannot hide a
material fit regression. Any violation exits nonzero = "discard the change".
Note Asia West needs no exclusion switch: it has no anchor coverage, so it
simply never enters the metric (dropping its contests *from the fit* is
explicitly permitted as an experiment in `program.md`).

**`program.md`** (repo root) is the instruction file for auto-research agents
(karpathy-style `verify`/guard loop): the verify contract (last line
`METRIC calibrated_loco_cf_rmse=…`, exit 1 = discard, ~5 s deterministic
runs), the scope
(fit/likelihood/prior/hygiene code is fair game; `metric.py`, the yardstick
modules, and everything under `data/` are read-only; CF anchor data must never
be read in the fit path), and the prioritized idea list (hard-tail prior,
gym-informed priors, solve-time/hazard refinements, `wrong_attempts`, …).
