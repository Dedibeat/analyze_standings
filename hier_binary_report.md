# Hierarchical binary ratings: a DE rival

2026-11-05. Research only: no shipped fit, calibration, rating, viewer or app
output changed. Code: `arch_b/hier_binary.py`; results: `output/hier_binary.json`
and `output/hier_binary_ratings.json`; tests: `tests/test_hier_binary.py`.

## Verdict

**A credible rival to DE, not yet a replacement.** One binary Rasch fit with
board-level priors gives both problem and team ratings on one CF map:
- **Full fields:** CF accuracy level with DE within noise.
- **Changed fields:** problem ratings much more stable.
- **Teams:** ratings that predict held-out results clearly better than either
  shipped engine.

It needs a fresh confirmation set before anyone ships it.

| Check | DE / shipped | Hierarchical binary |
|---|---|---|
| CF RMSE, full fields (185 anchors, nested LOCO) | **225.6** | 229.5, **+3.9 [−8.1, +14.5]** |
| Strong − weak half, mean CF error | −22 vs −246: **224 apart** | −18 vs −19: **1 apart** |
| CF RMSE, weak half / reserved eighth / small event field | 450.9 / 353.7 / 310.3 | **332.6 / 315.2 / 287.4** |
| Drift RMS vs full field, 9 reserved views | — | lower than DE in 8 (not the strong half) |
| Within-contest order reversals | 9–31 per view | **3–20** (about half) |
| Held-out appearances, cell log loss (splits 1 / 2) | survival 0.278 / 0.282; binary 0.252 / 0.255 | **0.237 / 0.242** |
| Linked teams, rank-pair accuracy | survival 80.0% / 80.1%; binary 79.4% / 79.8% | **80.7% / 81.1%** |
| Forward replay, combined pairs with member priors | flat binary 71.45% | **71.80%, +0.35 pp [+0.19, +0.55]** |
| 54 CF-rated elite teams, CF RMSE of the team rating | survival on its map: 348 (mean −246) | **218** (mean +79) |

Against the success criteria fixed before the stability and forward results
were seen (Protocol):
1. **Full-field CF not significantly worse than DE: met.** +3.9 [−8.1, +14.5].
   DE still has the better point estimate; it wins 10 of the 15 contests.
2. **Lower CF RMSE and drift than DE on the reserved stress fields: mostly
   met.** Drift is lower on 8 of 9 views (the exception is the strong half,
   175 vs 136). RMSE is lower on 6 of 9, and significantly on the weak half
   (−118 [−158, −78]). It is higher on the reserved half (+8.2 [−9.3, +27.2]),
   the strong half (+3.9) and event-only (+0.3). No view is significantly
   worse.
3. **Team prediction better than both shipped engines, and no worse forward:
   met.** Every held-out metric beats survival and binary with intervals
   excluding 0. Forward, history pairs are level and member-prior pairs better.
4. **External team check better than survival's: met.**

## Why this model

The audits already pinned down three facts:
- Binary Rasch difficulty barely moves with who attempted a problem (+5
  strong − weak, independent selection). DE moves +188, mostly through its
  solve-rate term (`rating_rethink_experiments.md` §4).
- Binary abilities and difficulties both map to CF with slope ≈ 1. Survival
  compresses abilities 2.4× against its own difficulties
  (`de_release_audit.md`).
- DE's solve-rate coefficient is positive: at a fixed fitted difficulty, a
  problem that more of its board solved gets a *higher* CF rating.

The last fact points at a bias in the joint fit, not in the map. The flat
N(2000, 400²) ability prior shrinks every team seen once toward 2000. On a
strong board that pulls its abilities down, and the difficulties fitted
against them follow; on a weak board the reverse happens. Solve rate is how DE
detects and undoes this after the fact, which is also why DE moves when the
field changes. The fix here is at the source: each board gets its own ability
mean.

The evidence for this mechanism: on top of the hierarchical difficulty, none
of DE's features helps any more. Solve rate, SE, field size, survival
disagreement and median solve time each leave nested LOCO at 231–233.

## Model

```text
P(solve)  = logistic((θ_t − b_p) / s)
θ_t ~ N(mean of μ over the team's boards, σ²)     μ_c ~ N(2000, τ²)
b_p ~ N(ν_c(p), σ_b²)                              ν_c ~ N(ν₀, τ_b²), ν₀ flat
problem CF = A · b + B,  team CF = A · θ + B       (one affine map, CF anchors)
selected: σ = 300, τ = 800, σ_b = 600, τ_b = 400;  A = 0.907, B = 515
```

- **μ_c** is the board's ability mean. It is learned from that board's own
  teams and from teams linking it to other boards, so a strong field no longer
  drags its difficulties down.
- **ν_c** pools a problem set toward its own mean. A problem solved by no one
  or by one team is shrunk toward its set, not toward 2000.
- **Level.** Only the ability side anchors the scale: the average board mean is
  exactly 2000 (the repo's MU0 convention), and ν₀ is estimated. A first
  version anchored ν at 2000 too. That split the level (average team ≈ 1800,
  average problem ≈ 2200) and made the forward test's 2000 default for new
  rosters wrong; see Protocol.
- **One map for problems and teams.** A team rated R and a problem rated R
  give a 50% solve. The shipped system uses DE for problems and a different
  scalar map on survival abilities for teams.
- **Optimizer.** Block-coordinate Newton converges very slowly along
  board-wide shifts: at eps 0.5 it stopped up to 121 points short. The fit
  instead uses Newton steps solved by preconditioned conjugate gradients on
  all parameters, with a line search: ~11 Newton steps, ~8 s on the full data.
  With the hierarchy off it reproduces `model.fit` within 4 points on every
  difficulty inside [800, 4000]. It does not clip while fitting.

## Results

### Team prediction (whole appearances held out)

20% of (contest, identity) appearances leave training with all their cells
and replay rows. A team with no other appearance gets its prior mean (the
board's μ). Splits 1 and 2 were never used for selection. Intervals are
paired contest bootstraps.

| split 1 / split 2 | survival | binary | hierarchical |
|---|---|---|---|
| cell log loss | 0.2783 / 0.2819 | 0.2523 / 0.2550 | **0.2368 / 0.2418** |
| Brier | 0.0827 / 0.0836 | 0.0769 / 0.0775 | **0.0719 / 0.0730** |
| linked-team log loss | 0.2451 / 0.2479 | 0.2165 / 0.2172 | **0.2110 / 0.2105** |
| solve-count RMSE per appearance | 1.735 / 1.762 | 1.616 / 1.638 | **1.516 / 1.554** |
| linked rank-pair accuracy | 80.04% / 80.06% | 79.40% / 79.75% | **80.70% / 81.06%** |

- **Hierarchical − binary:** log loss −0.0155 [−0.0223, −0.0093] /
  −0.0132 [−0.0193, −0.0079]; linked log loss −0.0056 / −0.0067; pair
  accuracy +1.30 / +1.31 pp (intervals exclude 0).
- **Hierarchical − survival:** log loss −0.042 / −0.040; pair accuracy
  +0.66 [+0.26, +1.10] / +1.00 [+0.58, +1.37] pp.
- **Flat control:** σ 400 with only the set-level difficulty mean (the best
  flat setting) is within 0.001 of shipped binary. The gain comes from the
  board-level ability mean.

### Forward forecasts (recorded-date replay)

`member_forecast`'s panel: 26 regional boards, fit only on boards that ended
earlier, scoring 2024 onward. The member-prior weight was tuned on 2023 per
model (flat 1.0, hierarchical 1.5).

| pairs (2024–2025) | flat binary | hierarchical | difference |
|---|---|---|---|
| history teams, 79,910 | 76.09% | 76.18% | +0.09 pp [−0.11, +0.38] |
| new roster involved, with member priors, 233,879 | 69.87% | 70.30% | **+0.44 pp [+0.24, +0.68]** |
| all, with member priors, 313,789 | 71.45% | 71.80% | **+0.35 pp [+0.19, +0.55]** |
| new roster involved, bare 2000 default | 60.30% | 60.04% | −0.25 pp [−0.53, −0.05] |

Pair log loss moves the same way (history −0.003 [−0.009, +0.002]). The bare
default is not how a new roster would be rated; member priors are.

### External yardstick: 54 CF-rated elite teams

Each model's team ratings are put through its own problem→CF map and compared
with the teams' CF ability (members combined by `cf_prior`):

| | survival | binary | hierarchical |
|---|---|---|---|
| CF RMSE [95%] | 348 [293, 398] | 220 [186, 254] | **218 [180, 251]** |
| mean error | −246 | +86 | +79 |
| Pearson | 0.752 | 0.798 | 0.798 |

Survival abilities do not share its difficulty scale (CF ≈ 2.85 θ for teams,
but 1.65 b for problems). Both binary fits do: one map serves both axes. The
panel is 54 World-Finals-level teams only.

### Problem CF accuracy, full fields

| | DE | binary affine | flat + set mean | hierarchical |
|---|---:|---:|---:|---:|
| nested LOCO RMSE | **225.6** | 246.8 | 242.3 | 229.5 |
| Asia Pacific / Europe / N. Eurasia | 202 / 310 / 178 | — | — | 205 / 319 / 177 |
| CF ≥ 2800 tail | 290 | 282 | 287 | 293 |

The map is affine with no tuned settings; the fit's settings never saw a CF
label. Better than DE on 5 of 15 contests.

### Field stability (16 deployed-like joint refits)

| view (rows kept) | DE | binary | hierarchical | hier − DE [95%] | drift DE → hier | mean error DE / hier |
|---|---:|---:|---:|---|---|---|
| full | 225.6 | 246.8 | 229.5 | +3.9 [−8.1, +14.5] | — | −1 / +1 |
| half_reserved | 234.9 | 259.7 | 243.1 | +8.2 [−9.3, +27.2] | 95 → 84 | −23 / +20 |
| quarter_reserved | 276.8 | 279.2 | 267.5 | −9.3 [−27.5, +11.3] | 186 → 150 | −66 / +52 |
| eighth_reserved | 353.7 | 317.6 | 315.2 | −38.5 [−89.7, +20.5] | 298 → 241 | −142 / +65 |
| event_only | 245.0 | 270.4 | 245.3 | +0.3 [−14.8, +15.9] | 76 → 75 | −17 / +16 |
| event_small | 310.3 | 309.4 | 287.4 | −22.9 [−60.3, +15.7] | 207 → 156 | −95 / +33 |
| mirror_balanced | 264.6 | 273.9 | 263.9 | −0.7 [−18.0, +15.9] | 150 → 127 | −20 / +35 |
| strength_pool | 304.8 | 313.9 | 289.6 | −15.2 [−28.9, +0.0] | — | −72 / −24 |
| strong half | 369.4 | 386.9 | 373.3 | +3.9 [−18.4, +25.5] | 136 → 175 | −22 / −18 |
| weak half | 450.9 | 381.8 | **332.6** | **−118.3 [−157.8, −78.2]** | 232 → 155 | −246 / −19 |
| quarter0 / quarter1 (training) | 295.4 / 282.5 | 291.3 / 276.8 | **255.3 / 253.8** | **−40.1 / −28.7** | 206 → 130 / 182 → 122 | |

- **Composition-invariant.** The strong and weak halves end 1 point apart in
  mean error (DE: 224; binary: 72).
- **Ordering.** Order reversals within contests are about half of DE's in
  every view. The predicted spread shrinks less on small fields (SD 600 vs 537
  at a quarter).
- **Weakness 1: board level floats up when a board is cut hard.** Mean error
  is +52 at a quarter and +65 at an eighth. It does not come from the
  hyperpriors (τ, τ_b = 4000 leave it unchanged), and a region-level layer for
  the board means changed nothing; that layer was removed. It is tied to how
  many linking teams survive the cut.
- **Weakness 2: team ratings on a cut board move with it.** The kept teams'
  ratings move by RMS 103 (mean +49) at a quarter, against 63 for flat binary
  and 28 for survival in its compressed units. This is ratings for the *same*
  results when three quarters of the board are deleted, so it is a stress
  limit, not an everyday drift.

### Where it disagrees with DE

Over all 3,185 problems the two agree closely: mean difference −2.6, SD 106,
Spearman 0.991. The largest board-level differences (mean hierarchical − DE):
- **Rated harder:** strong invitation fields outside DE's anchor support. The
  3rd Universal Cup Finals +294; THUPC 2022 +283; Petrozavodsk 2022 days 3 / 6
  +264 / +220; EC-Final +48 on average.
- **Rated easier:** EC online rounds, −138 on average (2026 rounds 4071 / 4113:
  −169 / −199), and Mid-Atlantic USA −162…−189.

The EC online gap is the main open question. The same teams perform about
+102 [+88, +117] better in EC online rounds than onsite (`de_release_audit.md`;
mirror entries show a smaller same-team gap, +51 [+9, +89],
`rating_rethink_experiments.md`). Without the flat prior's pull toward 2000,
the hierarchical fit follows the linking teams and inherits that online
advantage, so its online-round difficulties are on an "as if onsite
performance were equal" scale. Neither
model is verified there: no CF anchor exists for an online round. A
context term (the onsite-bridge offset) would be needed for onsite-equivalent
online ratings.

## Protocol

**Success criteria, stated before the stability and forward results were
seen:**
1. CF accuracy on full fields not significantly worse than DE (paired
   contest-bootstrap interval of the RMSE difference includes 0).
2. On the reserved stress fields (small, event/mirror, strong/weak), lower CF
   RMSE and lower drift than DE.
3. Team prediction better than both shipped engines (survival, which the
   viewer uses, and binary, which the calculator uses) on held-out
   appearances, with intervals excluding 0; no worse than flat binary in the
   recorded-date forward replay.
4. On the 54 CF-rated elite teams, team ratings on the shared map closer to
   CF team ability than survival's.

**Selection never uses a CF label or a reserved view.** It has two stages over
a frozen grid (σ ∈ {250, 300, 400, 600}, τ ∈ {400, 800}, σ_b ∈ {300, 400, 600},
τ_b ∈ {0, 200, 400}, plus 12 flat settings):
1. **Predictive.** Keep settings within 1% of the best held-out cell log loss
   on split 0 of the appearance hold-out (36 of 72 qualify; every σ ≤ 300).
2. **Measurement stability.** Among those, pick the one whose latent
   difficulties of all 189 problems on the 15 anchor boards move least across
   the six *training* views of the DE stability experiment (half and quarter
   cuts). The score is RMS change over the full-view SD. σ_b decides it: 0.136
   at σ_b 600 vs 0.165 at 300; σ, τ and τ_b change it by under 0.003.
   **σ_b = 600 is the grid's edge**; larger values were never tried.

Then everything is evaluated once: splits 1–2, the forward replay, the CF
anchors, the reserved views and the external panel.

**What was seen first, honestly.**
- An exploration on the CF anchors showed the hierarchy closes most of
  binary's gap to DE (227–236 nested LOCO across the grid).
- The first selection used stage 1 alone (lowest log loss) and picked
  σ_b = 300. It met criteria 1, 3 and 4 and failed 2: the reserved half
  +19.4 [+0.4, +42.1], the strong half +34.7 [+12.7, +55.1], and drift above
  flat binary's.
- Diagnosis on the stress views showed σ_b was the lever: a tight problem prior
  shrinks difficulties toward the set mean as fields shrink. That is why
  stage 2 was added. It is label-free, but it was designed after seeing those
  views, so the reserved-view results for the final setting are less
  independent than the table suggests.
- Before that, the team-side selection was first run with ν anchored at 2000.
  The forward smoke test exposed the level defect, ν₀ was freed, and every
  stage was rerun from scratch.

**Field stability** reuses the 16 deployed-like views of the DE stability
experiment: whole joint refits with every anchor board cut down by team, with
the same seeds and selection code. The kept rows match the DE run's exactly,
and the binary refit reproduces its cached features exactly. The CF map is fit
on the full-view anchors of the other 14 contests (task-purged) and applied to
each view, the same protocol as DE there.

**Forward replay** reuses `member_forecast`'s recorded-date panel: for every
board, fit only boards that ended earlier; 2023 tunes the member-prior weight
per model, and 2024 onward is scored. Flat binary there is `model.fit` at
tolerance 0.01, as in experiment 3.

## Limits

- The 185 anchors in 15 CF contests, the joint dataset and the forward panel
  have all been inspected many times, and this candidate was iterated on them.
  This is development evidence, not a fresh confirmation.
- Abilities are static per resolved identity. Event/mirror labels in the
  stress views are the ID heuristic.
- The external team check covers 54 World-Finals-level teams only.
- Solve times are not used. They carry penalty and tie information that a
  later timing component could add (survival still ranks linked pairs better
  than flat binary, 80.0% vs 79.4%).
- Online rounds: see "Where it disagrees with DE".

## Next steps

1. **Freeze this setting and confirm it on fresh data:** the 2026 regionals as
   their boards and CF ratings appear, scored against shipped DE without any
   refitting choices.
2. **Fix the cut-board level float**, for example member-level linking so that
   fewer teams are unlinked, before ratings for very small boards are trusted.
3. **Add an onsite-bridge context term** if online-round difficulties should
   be onsite-equivalent.

## Reproduce

```bash
PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.hier_binary all 10
./.venv/Scripts/python -m unittest tests.test_hier_binary
```

The run uses CPU NumPy. With 10 workers the whole run takes about 75 minutes
on an i7-14700KF: 86 selection fits, 252 stage-2 fits, 16 views × 4 models,
26 forward fits. Intermediate results are cached under the gitignored
`hier_binary_run/`. The stability stage reads `output/de_stability_evaluation.json`
for DE's predictions on the same views.
