# DE release audit on the roster-fixed fit (2026-09-28)

**Candidate:** the DE calibration on the survival/binary pair refit with the EC
online-round rosters attached. DE is `raw_b` plus binary-minus-survival,
conditional SE, solve rate and `log1p` field size. The roster fix is
`scripts/attach_online_rosters.py`. It is not yet applied to `data/tagged.json`.

**Verdict.** DE holds up in every development check I could run, and the roster fix
does not change that. The independent CF-gym population also agrees with DE's
contest levels better than with the shipped map. A global switch still needs
three decisions from you:

1. **No fresh confirmation set exists.** On 2026-09-28 I fetched a fresh CF
   problemset. It adds 159 newly rated problems in 26 contests, but none of them
   is in our data. The 15 anchor contests are still the only CF labels. The
   repo's own release gate ([shipped_fit_update_plan.md](shipped_fit_update_plan.md))
   requires a fresh set, so a release now would rest on development evidence
   plus the gym-population check below.
2. **225 appearances are outside any field-size evidence.** The CF anchors
   cover fields of 77–323 teams, and the gym data covers 31–1,083.
   - Below that range: 137 appearances in 16 contests, mostly partial North
     America boards with 1–25 rows.
   - Above it: 88 appearances in 7 contests, including every EC online round.

   DE moves these by **+188** and **−143** points on average. Clipping DE's
   features to the anchor range costs nothing on any check and bounds those
   moves (+55 / −34). I recommend it; see "Safer DE".
3. **Online-round ratings rest on an assumption that is false.** Verified teams
   perform better online than onsite (next section), and the fit cannot
   separate that effect from the online problems' difficulty. DE then moves
   the online-round problems −196 points from their shipped values, mostly
   through the field-size term; the roster fix alone moves them −51. I recommend marking online-round appearances as a separate scale
   rather than presenting them as onsite-equivalent.

The implementation requirements already listed in the update plan are
unchanged: one versioned calibration artifact for every consumer, no DE for team
abilities or medal bars, and no reuse of the gym-based uncertainty fields.

Reproduce (about 25 minutes; nothing in `output/` other than the two JSON files
changes):

```bash
python3 scripts/attach_online_rosters.py data/tagged.json /tmp/tagged_rosters.json
python3 -m arch_b.de_release_audit /tmp/tagged_rosters.json     # output/de_release_audit.json
python3 -m arch_b.fit_mechanism_audit /tmp/tagged_rosters.json  # output/fit_mechanism_audit.json
```

## Provenance and a determinism bug

- A fresh baseline fit reproduces `output/problem_ratings_{b,survival}.json`
  exactly (the module stops if it does not).
- **Bug fixed:** `calibrate._gym_shape` sorted tied one-decimal difficulties
  with numpy's unstable default sort.
  - On Windows (numpy 1.26) a rerun would move 2,949 of 3,159 shipped
    ratings by up to 17.2 points.
  - It is also why the documented gym LOCO (245.4277) did not reproduce here.
  - A stable sort reproduces the shipped ratings and every documented number
    exactly; all 108 tests pass.

## DE on the candidate (nested, task-purged; same protocol as `calibration_ablation`)

| RMSE (CF points) | raw affine | gym (shipped map) | DE | DET |
|---|---:|---:|---:|---:|
| LOCO, shipped fit | 246.91 | 245.43 | 226.57 | 229.63 |
| LOCO, roster-fixed fit | 246.93 | 246.13 | **226.32** | 229.40 |
| LORO, roster-fixed fit | 248.67 | 246.67 | **225.69** | 227.97 |

- The adaptive selector picks DE in all 15 contest folds.
- DE beats the gym map in 10 of 15 contests (9 before).
- The non-OOF proxy guards are unchanged: gym pooled .978, gym Asia East .982,
  Kattis .775, AOJ .564.
- The roster fix alone shifts the shipped gym-map ratings by only
  −1.9 on average. The online-round problems move −51.

## Evidence features and safer variants (issue #6)

Nested LOCO on the candidate. The differences are against DE, with a 15-contest
paired bootstrap using fixed predictions.

| variant | LOCO | minus DE [95%] |
|---|---:|---|
| DE | 226.32 | — |
| without conditional SE | 228.19 | +1.9 [−7.4, +9.0] |
| without solve rate | 233.17 | +6.8 [−2.2, +15.7] |
| without field size | 226.99 | +0.7 [−4.7, +5.5] |
| survival/binary blend only (w = 0.5–0.7) | 241.15 | +14.8 [−2.0, +33.3] |
| blend + evidence terms | 225.53 | −0.8 [−2.4, +1.1] |
| features clipped to training range | 226.03 | −0.3 [−1.6, +1.3] |
| correction shrunk by Mahalanobis support | 225.61 | −0.7 [−5.0, +4.2] |
| raw affine | 246.93 | +20.6 [+5.6, +35.4] |

- **Blends and the evidence terms.** A plain blend recovers a quarter of DE's gain.
  The evidence terms carry the rest, and "blend + evidence" is DE
  re-parameterized.
- **The evidence features.** Solve rate matters most. Field size adds almost
  nothing on the anchors, yet it is the feature that sends 1,610 appearances
  off support.

**Support stress test.** The three anchor contests at one end of a feature are
held out together and the settings are chosen on the rest (RMSE on the held-out
contests):

| held out | raw | DE | DE clipped | DE shrunk | DE without field | blend |
|---|---:|---:|---:|---:|---:|---:|
| 3 smallest fields | 201.0 | **211.0** | 204.1 | 218.5 | 194.7 | 195.1 |
| 3 largest fields | 179.8 | 160.2 | 159.3 | 163.0 | 164.5 | 174.5 |
| lowest / highest solve rate | 211.6 / 269.5 | 188.3 / 232.1 | 191.2 / 235.8 | 193.4 / 232.1 | 192.1 / 239.7 | 203.5 / 288.6 |
| lowest / highest disagreement | 296.0 / 247.8 | 283.3 / 220.2 | 283.3 / 220.2 | 283.3 / 220.2 | 284.5 / 216.5 | 293.4 / 238.3 |

DE extrapolates badly only toward small fields, and there only on 37 anchors in
three contests.

**Independent check: robust scaling against the CF-gym population.** This
follows Halpin 2022, *Differential item functioning via robust scaling*.
- **Data.** The gym population solved the same problems with known CF
  ratings, and gym difficulties never enter DE. The check uses 655 non-anchor
  problems in 53 contests.
- **Method.** Each method gets one linking line. Then a Tukey-bisquare offset
  per contest measures how far that method's contest levels sit from the gym
  population's (smaller spread is better).

| method | all: RMSE / offset SD | inside anchor ranges | fields < 77 (98 problems) | fields > 323 (219 problems) |
|---|---|---|---|---|
| raw affine | 214.6 / 132.8 | 196.5 / 144.9 | 195.2 / 93.4 | 240.7 / 112.2 |
| shipped gym map (fit on this data) | 190.7 / 119.8 | 182.9 / 133.5 | 190.6 / 91.9 | 197.3 / 98.4 |
| **DE** | 192.3 / **96.4** | 183.2 / **96.8** | 179.7 / 84.2 | 210.4 / 92.2 |
| DE clipped | 193.9 / 101.5 | 183.6 / 96.8 | 188.8 / 73.8 | 209.2 / 89.6 |
| DE without field size | 213.0 / 122.0 | 190.7 / 103.7 | 216.7 / 73.5 | 240.9 / 93.9 |

- **Contest levels.** DE's per-contest levels agree with the gym population much
  better than raw's or the shipped map's, which is direct transfer evidence for
  Asia East contests that have no CF anchors.
- **Field size.** It helps on both sides of the anchor range, so dropping it is
  wrong.
- **Clipping.** It is roughly neutral: slightly worse RMSE on small fields,
  better offsets on both.

**Recommendation:** ship DE with its features clipped to the anchor training
range.
- **Why clipping:** it is parameter-free, not chosen from these scores, costs
  nothing on LOCO (226.03), is neutral on the gym population, and limits the
  worst stress case (204 vs 211).
- **Catalog effect:** mean change from the shipped ratings +70.0 (unclipped
  +77.6); 599 appearances move by 200 or more (900 unclipped).
- **Still unresolved:** Aobayama 1965 H (2151.5 → ~2,700) is inside the field
  range. Disagreement and solve rate drive its correction, and no evidence
  settles it.

## Online vs onsite (issue #1)

**Samples:**

| class | rows | how identified |
|---|---:|---|
| verified official online | 8,231 | attached rosters, solved counts equal to the PKU ranking |
| onsite, 2024–25 | 4,427 | QOJ regional-board rows whose roster matches an XCPCIO onsite team |
| mirror | 3,016 | roster rows on the same boards that match none |

The regional boards are assigned to their site when that site's rosters are at
least 40% of the board. A Universal Cup stage and the 2023 online round had first
been mis-assigned and were excluded.

**Design:**
- 2,013 teams have both verified online and verified onsite rows; they are split
  into 5 folds.
- For each fold, one kind of row is hidden and the fit is rerun. The hidden
  appearances are then predicted from the rest.
- Hiding evidence shrinks predictions the same way in both directions, so the
  paired difference isolates the context effect.

| hidden rows, then predicted | survival: residual solves / offset | binary: residual solves / offset |
|---|---|---|
| online (ability from onsite + other) | **+0.35** [+0.31, +0.39] / +44 | **+0.29** [+0.25, +0.32] / +68 |
| onsite 2024–25 (ability from online + other) | −0.11 [−0.16, −0.07] / −12 | −0.20 [−0.24, −0.16] / −42 |
| mirror rows (929 teams) | +0.95 [+0.84, +1.05] / +100 | +0.44 [+0.38, +0.51] / +83 |
| **paired online − onsite offset, per team** | **+69** [+62, +76] | **+102** [+88, +117] |

Offsets are in each model's rating points; binary points track CF about 1:1
(see #2 below). The robust (bisquare) per-team estimates agree: +75 / +114.

- **By ability.** Split by full-fit ability tertile (weakest to strongest), the
  gap is +16 / +72 / +119 (survival) and −13 / +133 / +188 (binary). It sits in
  the stronger two-thirds. Teams have more online than onsite rows, so the
  full-fit ability leans slightly toward online form, which can inflate the top
  tertile.
- **By season.** The effect holds in both seasons.

**Findings:**
- The online excess is real for official, roster-verified teams. It is not an
  artifact of virtual users.
- Online mirror entrants on regional boards show it most strongly.
- **An online adjustment cannot be estimated inside the fit.** Every row of an
  online round is online, so an offset for them trades one-for-one against those
  problems' difficulty level. The fit moved both about −130 while leaving held-out
  log loss unchanged (Δ −0.0001) and CF LOCO at 226.29.
- **Consequence:** online-round difficulties are identified only by assuming
  equal online and onsite performance, and the data contradict that assumption.
  The online-round problems therefore look easier than an onsite-equivalent
  scale would rate them. This also explains part of the −35 to −54 point shift
  the roster links produced.
- An adjustment would need outside evidence: shared problems, or CF member
  ratings of the online teams (#5).

## What the disagreement measures (issues #2 and #3)

**Frozen-ability refits.** Difficulties were refit with the abilities held at the
other model's values.

| component | share of var(binary − survival) | nested LOCO with it in place of D |
|---|---:|---:|
| path 1: ability-scale part (binary likelihood, θ_B vs θ_S) | 61% | 231.9 |
| path 1: likelihood part (θ_S held, binary vs survival) | 39% | 232.7 |
| both parts as separate features | — | 229.6 |
| path 2: likelihood part (θ_B held) | 82% | 234.0 |
| path 2: ability-scale part (survival likelihood) | 18% | 241.2 |
| D itself (DE) | — | **226.3** |
| no disagreement (evidence only) | — | 238.2 |

Neither mechanism alone carries DE's gain; both halves contribute.

**The ability scales differ:**
- Binary abilities are 2.39× as spread as survival's, and binary difficulties
  1.69×.
- Against roster-complete CF team abilities (54 elite teams), CF ≈ **0.98** ×
  θ_binary [0.80, 1.21] but **2.85** × θ_survival [2.27, 3.55].
- On the anchors, CF ≈ 0.98 × b_binary and 1.65 × b_survival.

So the binary fit's ability and difficulty axes both map to CF with slope 1. The
survival fit compresses abilities relative to difficulties, and team-ability
outputs must not reuse the survival difficulty map.

**Why survival compresses abilities.** For solved cells, the constant-hazard
model implies a solve-time distribution whose PIT should average 0.5.

| k-th solve of a team | 1 | 2 | 3 | 5 | 8 | 10 | 11+ |
|---|---:|---:|---:|---:|---:|---:|---:|
| mean PIT | 0.49 | 0.56 | 0.62 | 0.69 | 0.76 | 0.80 | 0.82 |
| observed mean time (share of window) | 0.12 | 0.24 | 0.36 | 0.52 | 0.67 | 0.74 | 0.79 |
| model's mean time | 0.16 | 0.25 | 0.31 | 0.37 | 0.43 | 0.45 | 0.46 |

- **Queueing.** Teams work through problems one at a time, so later solves come
  late whatever the team's ability. The model reads those late solves as
  weakness.
- **Solve counts at the end.** The fit over-predicts weak rows' final solves
  (observed 1.62 vs predicted 2.42) and under-predicts strong rows'
  (8.45 vs 6.90).
- **What to build.** A coherent replacement (#3) needs a solve-order or queue
  term in the time model. A simpler route is to let the binary part set
  abilities and model time conditional on solving. Neither was built here.

## Team-season and attendance (issue #4)

Abilities get a shrunk team-season offset δ ~ N(0, τ²). Held-out cell log loss,
with the change from τ = 0:

| τ | Asia East cells, survival | Asia East cells, binary | random cells, binary | CF LOCO raw / DE |
|---:|---|---|---|---|
| 0 (shipped) | 0.22020 | 0.18965 | 0.20228 | 246.9 / 226.3 |
| 100 | −0.0026 [−0.0032, −0.0021] | −0.0024 | −0.0025 | 248.4 / 230.0 |
| 200 | −0.0022 | **−0.0032** [−0.0039, −0.0024] | **−0.0034** | 249.9 / 234.1 |
| 400 | −0.0009 | −0.0027 | −0.0028 | 251.2 / 240.7 |

- **Held-out solves.** Team-season offsets clearly improve them, in every
  season. That includes 2022–23, which the season-agnostic roster links had made
  slightly worse.
- **CF-scale difficulty.** They make it worse: DE +3.7 [+0.2, +7.5] at τ = 100.
- **Use.** They belong in team-performance outputs (forecasts, the virtual
  calculator), not in this problem-rating release.
- **Not modelled here:** attendance selection, and the difference between a
  genuine zero-solve row and a team that didn't participate.

## Independent evidence (issue #5)

- **Fresh CF anchors:** none; checked against a fresh problemset fetch on
  2026-09-28.
- **Shared problems:** only the five Luxor World Finals tasks recur inside the fit.
  Same-title matches elsewhere are different problems. DE's Luxor gaps are
  unchanged: 101.9 on task 8674 and 145.8 on 8680.
- **Other population:** the CF-gym robust-scaling check above is the
  independent evidence that exists.
- **Member ratings:** CF member ratings cover only 54 elite teams
  (`cf_prior`).
- **Still missing:** verified shared online/onsite problems, pre-contest member
  ratings for ordinary teams, and recorded contest durations.

## Release steps if you accept the verdict

1. Apply the roster fix: `python3 scripts/attach_online_rosters.py data/tagged.json data/tagged.json`.
2. Rerun `arch_b.run` and `arch_b.run --survival`, then `arch_b.calibrate`, the
   exporters and `arch_b.metric`. The metric reads 246.3 on the candidate
   (245.4 now), and every guard is unchanged.
3. Update the tests that pin the old numbers.
4. Build the DE calibration artifact.
   - Clipping to the anchor range is proposed.
   - Online-round appearances and fields outside 31–1,083 need a separate
     label or a fallback to the gym map; the choice is yours.
   - Follow steps 2–5 of the update plan.
5. Keep team abilities, the virtual calculator and medal bars on their scalar
   maps. Label DE ratings as problem-only.
