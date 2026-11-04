# Rating rethink: review and experiments 0–2

Date: 2026-11-04. Reviews [rating_rethink.md](rating_rethink.md), written by
another model (GPT-6 astra) at `2212261`, and runs the first three
experiments it proposes. Research only: no shipped fit, calibration, rating,
viewer or app output changed.

## Summary

- **The audit's reproducible claims hold.** The audit JSON reproduces exactly,
  and so does the binary/survival imputation check. A fresh joint fit
  reproduces all 3,185 saved binary and survival records. The calibration
  metadata hashes are stale as stated: they match neither the 09-28 nor the
  10-04 committed fits.
- **The audit's first experiment is not identified as written.** A pooled
  mirror offset in the binary fit is not pinned down by within-team evidence.
  For the many teams seen in one context only, the shared ability prior sets
  it. Mirror entrants are stronger than average, and most appear only as
  mirrors. Only 135 identities appear both as event rows and as UCup mirror
  rows; only 2 appear both as event rows and as account mirror rows. The naive
  offset therefore mixes three things: who enters mirrors, UCup mirror stages
  versus original UCup stages, and any same-team effect. The data here do not
  split it cleanly among them.
- **Same-team association, small in aggregate.** The two estimates of the
  onsite → mirror gap are reported separately:
  - per-team weighted gap +51 [+9, +89] (team bootstrap);
  - joint bridge-model offset +89, falling to +75 and +70 under weaker
    ability priors.

  Both are associations under the model and ID-based labels, not a verified
  causal conversion. They change aggregate held-out log loss by at most about
  1e-4; individual probabilities can move more. A mirror term in the shipped
  likelihood is not justified, and the 10-13 event-field ranking fix already
  handles the ranking side.
- **Binary Rasch difficulties transport across field composition; DE does
  not.**
  - Measured on the strong half of a board rather than the weak half, with
    abilities fixed from independent data, a problem's binary difficulty
    moves +5. The survival difficulty moves −95.
  - Shipped DE moves **+188 CF**, mostly through its solve-rate term.
  - In a deployed-like joint refit, DE keeps its ~20-point lead on full fields.
    It becomes the worst calibrator on small or weak fields (event-only
    quarter-size boards: 321 vs 276–288 RMSE, interval excludes 0).
- **Implication.** DE's development-anchor advantage is partly a match between
  its features and the anchors' kind of field. It is not evidence for fields
  unlike the anchors: EC online rounds, EC-Final, small boards. The October
  EC-Final/online offsets fit this pattern.

## 1. Review of the audit

**Verified** against code, data and `details.md`:
- **Dataset counts:** 262 contests, 78,201 rows, 991,268 cells, 232
  `$DEFAULT`-mixed boards, 448 repeated contest/identity groups, 11,867 dropped
  zero-solve rows (2,105 with wrong attempts).
- **Calibration scores:** the 225.61 nested DE LOCO and the cached
  affine/gym scores.
- **Cache inventory:** 59 XCPCIO configs and 38 run logs.
- **Code claims:**
  - `arch_b.metric` scores the survival gym map;
  - `export_viewer` uses the survival fit;
  - `dynamic_rating` builds identity once on all data, uses a full-data `b0`
    ruler, and fits member-prior targets on that ruler.
- **Cited history:** the PIT 0.49 → 0.82 figure and the forecast table match
  their sources.

**Gaps and corrections:**
1. **Prior leakage in the context offset.** The audit notes that a
   board-level context is confounded with that board's difficulties, a point
   the September fit-mechanism audit had already shown. It misses the
   team-level version.
   - For a team seen in one context only, any offset gives the same
     likelihood. The N(2000, 400²) prior then prefers the offset that pulls
     strong mirror-only teams toward 2000.
   - The naive pooled offset (+167) and its by-kind and slope versions (UCup
     +270; account slope 2.23, about nine prior SDs from zero) cannot be read
     as what mirroring does to a team.
   - Part of each estimate depends on the prior. Part does not: UCup is still
     +205 at σθ = 1600, carried by the item 2 bridges.
   - The audit's "add a mirror-by-ability slope" step inherits the problem.
2. **Bridges are mostly not onsite.** Of the 776 identities seen in two or
   more contexts, only 137 have an onsite event row. The rest link through
   rows on boards without an event field, mostly UCup original stages.
   Identifying the offset from them compares "UCup stage that mirrors a
   regional" with "original UCup stage". That is a different question, and its
   level is again prior-dependent (+300 → +217 as σθ goes 400 → 1600).
3. **Experiment 2 needs an independent selection.** Halves chosen by noisy
   outside ability regress to the mean. That alone produced a +87 strong −
   weak shift in binary difficulty, which vanishes (+5) with independent
   selection.
4. **The fixed-ability design is not the deployed estimator.** The shipped
   joint fit estimates unlinked teams from the same board, so a deployed-like
   joint refit is needed as well (§4).
5. **Stale metadata.** `problem_calibration.json`'s hashes match neither
   committed fit version. The cause was not found; the shipped
   `difficulty_cf` values still reproduce from the current fits.

## 2. Experiment 0: provenance (partial)

- `scripts.rating_rethink_audit` output is identical to the saved JSON.
  `arch_b.predict_eval` reproduces binary 0.1994 / 0.0609 / 0.9737 and survival
  0.2289 / 0.0690 / 0.9684.
- Fresh `estimate_joint` fits reproduce `problem_ratings_b.json` and
  `problem_ratings_survival.json` record for record (difficulty, SE, solves).
- Both new outputs record sha256 of the standings inputs, the saved fits they
  read, and their own code.
- **Not done:** exact dates, source-backed mode labels, canonical task
  versions, split manifests, metadata regeneration. Context labels below are
  ID-based (`$DEFAULT` / `ucup-team*` / other on boards with ≥ 30 official
  rows), not verified exposure.

## 3. Experiment 1: participation context in the binary fit

`arch_b/context_fit.py` → `output/context_experiment.json`.

**Model.** `logit = (θ + δ_k + γ_k(θ − 2000) − b)/s`, with k = reference /
mirror_ucup / mirror_account. Rows: 57,823 / 9,816 / 10,562; 221 mixed boards.
Offsets apply to a chosen set of teams:
- `naive`: every team, as proposed;
- `multi`: teams seen in two or more contexts;
- `onsite`: teams with both an event row and a mirror row.

Other teams' abilities stay in their own context. They are converted only when
predicted in a context they were never seen in.

### Offsets (binary points; ability prior SD 400 / 800 / 1600)

| Teams carrying the offset | Mirror offset |
|---|---|
| naive, pooled | +167 |
| naive, UCup / account | +270 / +76 → +227 / +73 → +205 / +105 |
| multi-context (776 teams) | +300 → +247 → +217 |
| **onsite bridges (137 teams)** | **+89 → +75 → +70** |
| onsite + ability slope | +68 at 1800, +80 at 2200, +91 at 2600, +103 at 3000 |
| naive + slope (UCup / account) | +129 → +686 from 1800 to 3000 / account slope 2.23 |

- **Per-team check**, a second estimator rather than an interval for the
  joint offset. Fix b from the onsite fit. Fit each bridge team's ability
  separately on its event rows and on its mirror rows. Weighted mean gap:
  **+51 [+9, +89]**, team bootstrap; median +77.
- **Earlier same-team estimates agree:** +82 [+6, +160] (10-13, 47 teams). The
  DE audit's +102 [+88, +117] is online minus onsite, a different contrast.
- **Strength dependence is weak where the offset is identified:** +12 points
  per 400 of ability. The October "advantage grows with strength" pattern
  mostly does not survive restricting the identification.

### Prediction

**Whole-appearance hold-out.** 20% of contest × identity groups, three seeds,
594,227 held-out cells. Δ log loss vs pooled M0, ×10⁻⁴, with a paired contest
bootstrap. Linked = the team has training rows.

| Subset (M0 log loss) | naive | multi | onsite | onsite + slope |
|---|---|---|---|---|
| linked (0.21690) | **−5.6 [−7.6, −3.4]** | +0.9 [−2.2, +4.5] | −0.05 [−1.2, +1.2] | −0.4 [−1.4, +0.8] |
| linked event rows (0.18505) | **−6.0 [−8.1, −3.5]** | −0.0 [−2.9, +4.2] | −0.3 [−0.8, +0.4] | −0.4 [−0.9, +0.3] |
| linked mirror rows (0.26741) | **−4.6 [−8.7, −0.7]** | +1.4 [−4.0, +7.1] | −0.3 [−2.0, +1.5] | +0.1 [−1.5, +1.8] |
| team's context unseen in training (4,052 cells, 79 contests) | −0.2 [−52, +57] | **+149 [+10, +332]** | +34 [−59, +138] | −1 [−82, +83] |

**Event-field transfer.** Four folds over the 221 mixed boards. A fold's event
rows leave training, together with those teams' other rows on the same board.
Same units.

| Subset (M0 log loss) | naive | multi | onsite | onsite + slope |
|---|---|---|---|---|
| linked event rows (0.22317; 419,539 cells) | −3.9 [−16.3, +8.3] | −4.0 [−9.5, +2.4] | **−0.85 [−1.61, −0.02]** | **−0.90 [−1.65, −0.12]** |
| teams seen only as mirrors (615 cells, 13 contests) | +59 [−159, +291] | **+738 [+330, +1394]** | −22 [−168, +123] | −56 [−176, +46] |
| split-half, all event rows (701,914 cells) | +3.1 [−2.9, +9.2] | −1.8 [−4.6, +1.3] | −0.2 [−0.5, +0.1] | −0.2 [−0.5, +0.2] |

**Reading.**
- The naive model's small gain is a population mean for mirror entrants (a
  hierarchical-prior effect). It is not evidence of same-team context.
- The identified onsite term touches only 137 teams. Its aggregate effect is
  about −1e-4 log loss.
- Its one interval excluding zero (transfer, −0.85 [−1.61, −0.02]) came after
  looking at four variants and several subsets. That is a reason for a fresh
  test, not for promotion.
- Converting by +300 (multi-context) is badly wrong on the few rows where it
  applies: 615 cells in 13 contests, and 4,052 cells in 79 contests for unseen
  contexts in the hold-out.
- No model changes the spacing of event-field difficulties (split-half ≈ 0).

**Difficulties.** On mixed boards, M0's difficulties sit within −3 … +30 of an
event-rows-only refit with the same abilities in every band:
- +30 below 1600, +9 at 1600–2000, −3 and −2 at 2000–2800, +13 above 2800.
- Context terms change these by at most 11, except naive + slope (+40 above 2800).

**CF guard.** Binary affine LOCO is 246.8 for M0 and 244.8–246.7 with context
terms.

**Incidental lead.** Every σθ = 800/1600 variant gives about 232 binary-affine
LOCO, whatever its context terms. This is the prior, not context. It is
untested with DE or out of sample. Earlier σθ = 300–600 sweeps moved the
survival north-star by under 2 points.

**Verdict.**
- Do not add a mirror offset to the shipped fit.
- Keep the onsite-bridge model as a research candidate. Any forecast use of the
  same-team gap needs a fresh test.
- Test a prior mean by entry type separately, as a forecasting prior.

## 4. Experiment 2: does calibration survive a change of field?

`arch_b/field_transport.py` → `output/field_transport.json`.

**Fixed-ability design.**
- **Abilities:** each board is re-measured with abilities fixed from five
  contest folds that exclude it (binary and survival).
- **Rows used:** linked rows only; 175 boards, 50,676 rows.
- **Grouping and target:** samples are drawn by team identity, and 30% of
  teams are a fixed target. The survival window comes from non-target solves.
- **Refit:** each sample refits binary and survival difficulties (bisection
  MAP per problem) and recomputes every DE feature.
- **Calibrators:** frozen, trained on the 185 shipped anchors:
  - shipped DE (clipped);
  - survival affine;
  - binary affine;
  - the survival/binary blend without evidence terms;
  - `DE_reference`: raw b + disagreement + the solve rate of a fixed external
    N(2000, 400²) population.
- **Independent selection:** strong/weak halves are chosen with abilities from
  one half of the outside contests, and measured with abilities from the
  other half (145 boards).

### Shift of a problem's calibrated difficulty (mean CF; problems solved by some but not all in both fields)

| Contrast | DE | survival affine | binary affine | blend | DE_reference | latent binary b | latent survival b |
|---|---|---|---|---|---|---|---|
| **strong − weak, independent** (966) | **+188** | −157 | +5 | −72 | −107 | +5 | −95 |
| noise: random half − half (7,173) | +1 | +3 | +3 | +3 | +3 | +3 | +2 |
| strong − weak, naive selection (1,170) | +280 | −130 | +85 | −16 | −62 | +87 | −79 |
| pool − quarter of it (8,481) | +65 | +24 | +29 | +27 | +24 | +29 | +15 |
| mirror − event teams, equal size (822) | +42 | −73 | −7 | −38 | −54 | −7 | −44 |

**DE's +188 by feature:**
- solve rate +209 (Δ solve rate +0.34);
- survival b −170;
- disagreement +80;
- conditional SE +69;
- field size 0.

**Its +65 size shift:** SE +62, field size −30, survival b +26.

**Binary difficulty is composition-invariant** once selection noise is
independent. Survival difficulty is not: strong fields make problems look
easier, since timing carries strength-dependent behavior.

### CF error of anchor problems by field (contest-held-out calibrators)

RMSE; X − DE [95% interval] by paired CF-contest bootstrap. The main design
covers 98 anchors in 8 CF contests; the independent design 50 anchors in 4.

| Field | DE | survival affine | blend | DE_reference |
|---|---|---|---|---|
| pool (full) | **228** | 253, +26 [−6, +57] | 247, +20 [−9, +52] | 248, +20 [−10, +52] |
| random half | 261 | 264, +3 [−27, +33] | 263, +2 [−24, +31] | 262, +0 [−27, +30] |
| quarter | 318 | **287, −31 [−59, −7]** | **290, −28 [−49, −7]** | **288, −31 [−55, −7]** |
| weak half | 339 | **291, −48 [−79, −15]** | **299, −40 [−65, −16]** | **297, −42 [−72, −15]** |
| strong half | 320 | 279, −40 [−101, +19] | 278, −41 [−86, +7] | 275, −44 [−94, +9] |
| independent weak | 335 | **265, −70 [−97, −22]** | **271, −64 [−84, −26]** | **265, −70 [−91, −28]** |
| independent random | 260 | **237, −23 [−44, −4]** | **240, −20 [−34, −4]** | **235, −25 [−38, −6]** |

### Deployed-like check: joint refit with the 15 anchor boards cut down

The whole joint model (binary + survival) is refit. Every anchor board is
reduced at once, by team, with an ID-based composition only. Features follow
the shipped definitions. The full refit reproduces the shipped anchor features
within 0.1 (rounding). 185 anchors, 15 CF contests.

| Condition (rows; mean solve rate) | DE RMSE / mean err | survival affine | blend | DE_reference | DE shift vs full |
|---|---|---|---|---|---|
| full (2,457; .409) | **223** / +0 | 246, +22 [+9, +36] | 241, +17 [+3, +34] | 243, +20 [+6, +36] | 0 |
| random half A (1,227) | 236 / −26 | 246, +10 [−2, +22] | 243, +7 [−6, +23] | 245, +9 [−4, +24] | −25 |
| random half B (1,230) | 240 / −27 | 252, +12 [−7, +32] | 251, +11 [−6, +30] | 251, +11 [−6, +30] | −23 |
| event rows only (2,034; .388) | **243** / −15 | 259, +16 [+7, +26] | 259, +16 [+5, +27] | 261, +18 [+7, +29] | −16 |
| mirror-heavy (846; .466) | 271 / −18 | 265, −6 [−29, +17] | 263, −8 [−31, +16] | 263, −7 [−30, +16] | −12 |
| event-only, small (708; .390) | 321 / −116 | **276, −44 [−65, −23]** | **288, −32 [−57, −8]** | **285, −36 [−60, −11]** | **−110** |

The two small fields differ in composition (mirror-heavy vs event-only).
Between them DE moves **98 CF**, survival affine 27, binary affine 34, blend 4
and DE_reference 8.

On the shipped anchors, the field-independent calibrators cost 15–18 points of
nested LOCO:
- blend 240.67;
- DE_reference 243.21, +17.6 [+1.7, +34.8] vs DE's 225.61.

**Verdict.**
- DE is the best calibrator for fields like its anchors' (full regional
  boards, event-only boards). Its accuracy does not transport.
- On weak, small or composition-shifted fields it is 30–70 RMSE worse than the
  simpler maps.
- It shifts difficulty by ~100–190 CF for the same problem, depending on who
  attempted it.
- The blend and `DE_reference` are nearly composition-invariant in the
  deployed-like check, but give up ~15–20 points on full fields.

## 5. What to do next

1. **Keep DE shipped, but stop trusting it outside its anchors' field
   support.**
   - Flag or shrink its evidence correction on boards whose field size or
     solve-rate profile is unlike the anchors'. `de_release_audit` already has
     a Mahalanobis `shrink` variant.
   - Treat EC online and EC-Final difficulties as extrapolations. Any
     replacement must be chosen on a fresh confirmation set, not on these 185
     anchors again.
2. **Prefer transport-invariant inputs for any new calibrator.** Binary
   difficulty is invariant in these tests; the survival timing term and the
   solve-rate/SE evidence terms are not. A per-board correction should use
   field information that does not move with who attempted.
3. **No universal mirror correction** (+167 or +300) in the joint fit. The
   onsite-bridge model (joint +89; per-team +51 [+9, +89]) stays a research
   candidate for the 137 teams that bridge contexts, pending a fresh test.
4. **The σθ = 800 binary-affine lead (≈ 232 vs 247)** deserves a pre-registered
   check with DE and on held-out data before anyone reads it as a gain.
5. **Not run here:** experiments 3–5 of the audit (strict-protocol member
   prior, timing pilot on the XCPCIO logs, canonical task linking).

## Implementation notes

An interim review by Codex, and my own checks, found five defects in the first
versions of these experiments. All are fixed; the results above come only from
the final code.
- **Oscillating per-problem refit.** A Newton step from 2000 bounced between
  the 800/4000 bounds when curvature vanished. Replaced by vectorized
  bisection (`context_fit.solve_decreasing`), with a test of the failing case.
- **Repeated identities across the split.** Same-team rows crossed the
  target/training split, and a same-board mirror row of a held-out event team
  stayed in training. Samples are now drawn by team, and transfer drops those
  rows.
- **Exposure leakage.** The survival window used target solve times; it now
  uses non-target solves only.
- **Reference population.** It came from a full-data fit; it is now the fixed
  N(2000, 400²).

## Reproduce

```bash
./.venv/bin/python -m arch_b.context_fit       # 49 joint fits; 30–60 min
./.venv/bin/python -m arch_b.field_transport   # 37 fits + per-board refits; ~15 min
./.venv/bin/python -m unittest tests.test_context_fit tests.test_field_transport
```

Both write JSON with input and code sha256 under `"sha256"`. Seeds are fixed;
two consecutive runs of `field_transport` gave identical results.
