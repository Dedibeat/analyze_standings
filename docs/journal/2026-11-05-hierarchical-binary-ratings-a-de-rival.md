# Hierarchical binary ratings: a DE rival (2026-11-05, third entry)

**Request.** Find a reasonable candidate that rivals DE: stable ratings,
better accuracy, and team ratings that predict better. Full write-up:
`hier_binary_report.md`; code `arch_b/hier_binary.py`; tests
`tests/test_hier_binary.py` (6); results `output/hier_binary.json` and
`output/hier_binary_ratings.json` (every problem: hierarchical CF next to
shipped DE). Research only; nothing shipped changed.

**Idea.** DE's solve-rate coefficient is positive: at a fixed fitted
difficulty, a problem more of its board solved gets a higher CF rating. That
points at the flat N(2000, 400²) ability prior. It shrinks every team seen
once toward 2000, so strong boards' abilities and difficulties are pulled
down, and DE repairs this after the fact, which is why it moves with the
field. The candidate fixes it in the fit:
- a board-level ability mean μ_c (average board 2000);
- a set-level difficulty mean ν_c (hyper-mean free);
- one affine CF map for problems and teams. Binary abilities and difficulties
  share a CF slope of ≈ 1.

On top of the hierarchical difficulty, none of DE's features helps any more
(nested LOCO stays at 231–233).

**Optimizer.** Block-coordinate Newton stops up to 121 points short at eps 0.5
along board-wide shifts, so the fit uses Newton steps solved by
preconditioned conjugate gradients: ~11 steps, ~8 s. With the hierarchy off
it reproduces `model.fit` within 4 points inside [800, 4000].

**Selection, no CF labels.**
1. Settings within 1% of the best held-out team log loss (split 0 of a 20%
   whole-appearance hold-out).
2. Among those, the least latent-difficulty drift across the DE stability
   experiment's six training views.

Selected: σ 300, τ 800, σ_b 600 (the grid's edge), τ_b 400; map
CF = 0.907 b + 515.

**Results.**

| | DE / shipped | hierarchical |
|---|---|---|
| CF RMSE, full fields | 225.6 | 229.5 (+3.9 [−8.1, +14.5]) |
| strong − weak half, mean error | 224 apart | 1 apart |
| weak half / reserved eighth / small event field | 451 / 354 / 310 | 333 / 315 / 287 |
| drift vs full, 9 reserved views | — | lower than DE in 8 |
| held-out appearance log loss (splits 1 / 2) | binary 0.252 / 0.255, survival 0.278 / 0.282 | 0.237 / 0.242 |
| linked rank-pair accuracy | binary 79.4 / 79.8%, survival 80.0 / 80.1% | 80.7 / 81.1% |
| forward replay, all pairs with member priors | 71.45% | 71.80% (+0.35 pp [+0.19, +0.55]) |
| 54 CF-rated teams, CF RMSE | survival 348 | 218 |

- The held-out team metrics beat both engines with intervals excluding 0.
  Forward history pairs are level (+0.09 pp [−0.11, +0.38]).
- Order reversals within contests are about half of DE's in every view.

**Weak spots.**
- A board cut to a quarter or an eighth floats up (+52 / +65 mean error), and
  its kept teams' ratings move with it (RMS 103 at a quarter, flat binary 63).
  Neither looser hyperpriors nor a region layer fixed it; the region layer was
  removed.
- The strong half drifts more than DE's (175 vs 136).
- The reserved half is +8.2 [−9.3, +27.2] behind DE.
- EC online rounds read ~140 easier than DE, consistent with the known +102
  online advantage being inherited through linking teams. Unverified either
  way, since no CF anchor exists online.
- The strong invitation fields read harder: UCup Finals +294, THUPC 2022 +283.

**Honest record of the iterations.**
1. The first version anchored ν at 2000 and split the scale's level; freed
   and rerun.
2. Selection by log loss alone picked σ_b 300, which failed the stability
   criterion (reserved half +19.4 [+0.4, +42.1], strong half +34.7).
3. The label-free stage 2 was designed after seeing that.

All of this is development evidence on long-inspected data; a fresh
confirmation set is the next step.

Run (~75 min with 10 workers):
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.hier_binary all 10`.
Cache: gitignored `hier_binary_run/`. Full suite: **226 tests pass** (system
Python 3.11).
