# Scale calibration to Codeforces points (`arch_b.calibrate`)

The raw scale is *relative* (pinned at the arbitrary MU0=2000) and compressed
vs CF, more so in the hard tail. **Upgraded 2026-07-04** from the original
single global affine on 3 hardcoded contests (LOCO ~252 on that 40-anchor set)
to a **two-leg map** validated on all 15 rated mirrors (185 anchors,
auto-mapped by the `external_validate` name vote):

1. **Shape leg (gym-learned, nonlinear).** A monotone quantile map `f`
   (NBINS=15 binned medians, linearly interpolated/extrapolated, shrunk toward
   its own linear approximation by ALPHA=0.75) fit on the ~660 (our `b`,
   `b_gym`) pairs — the gym yardstick is certified nearly CF-native in scale
   (affine slope 1.23 vs official CF). qoj 2692 (the only gym∩anchor contest)
   is excluded, so `f` shares no problems with the anchors that score it.
   Because `f` is monotone it **cannot reorder our problems** — it consumes
   only the gym population's trustworthy half (scale), none of its noisy half
   (ranking), which is exactly the division the two failed in-fit experiments
   established.
2. **Scale leg (affine).** `cf ≈ A·f(b) + B` fit on the official CF anchors;
   per LOCO fold it is refit on the 14 training contests.

**LOCO validation (survival model): 288.4 → 266.4** (−22). Cluster bootstrap
of the paired difference: mean −22.1, 95% CI [−43.9, −3.4], **P(worse) =
1.05%**; 10/15 contests improve; the cf≥3200 tail improves RMSE 477 → 434.
Controls: a per-fold *quadratic* on the CF anchors alone scores **297** (worse
than affine — the win is the gym information, not flexibility); per-region gym
shapes overfit (298); the result is stable across NBINS 8–25 (271–276 at
α=1) and α 0.5–1.0 (266–271). Hyperparameters were chosen on this same
anchor set (the known residual risk of a fixed anchor pool), but the plateau
is broad and the CI excludes zero. `calibrate` prints both LOCO columns per
model on every run; if `gym_difficulty.json` is absent it falls back to the
plain affine. `difficulty_cf_se` is scaled by the *local* slope of the
composed map (central difference). Note the fit-side metric (`arch_b.metric`)
is untouched and still reads 288.4 — it scores the raw fit's affine
calibratability, and its history stays comparable; the shipped deliverable's
LOCO is the 266.4 figure. Experiment log:
`autoresearch/autoresearch-260704-0150/classic-results.tsv`.
