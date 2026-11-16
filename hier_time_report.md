# Solve time in the hierarchical fit, and a release candidate

2026-11-16. Follow-up to `hier_binary_report.md` and `skip_cells_report.md`.
Code: `arch_b/hier_time.py`; tests: `tests/test_hier_time.py`. Research only:
shipped DE stays the shipped rating until someone decides to switch.

## Verdict

**The release candidate is the hierarchical fit with solve-time slices and
`skip_partial` (`time_skip`): 5 slices at weight 0.25.** It passes all four
pre-registered criteria and has the lowest hand-panel error. Its ratings for
all 3,409 problems are in `output/problem_ratings_hier.json`, in the shipped
file's layout.

Two labels documented as wrong are left out of every CF map and RMSE below
(see "Amendment"): the anchor Uniform Chemistry and the blind hand rating of
Wuhan 2025 F.

| Check | DE (shipped) | `base` (hier_binary) | `time_skip` |
|---|---|---|---|
| CF RMSE, full fields (184 anchors, nested LOCO) | 207.0 | 211.5 | **205.9** (vs DE −1.1 [−11.7, +9.0]) |
| CF RMSE, weak half / strong half / reserved eighth | 451 / 369 / 354 ¹ | 319 / 360 / 309 | **288 / 289 / 280** |
| Drift vs full field, 8 reserved views | — | — | lower than `base` on 8 of 8 |
| Hand panel, 72 problems: bias / RMSE | +185 / 290 | +164 / 296 | **+73 / 196** |
| EC sign-ins (18): bias | +206 | +385 | **−1** |
| Fresh blind panel, 31 problems: RMSE | 343 | 379 | **282** |
| Held-out log loss, untouched cells (splits 1 / 2) | binary 0.234 / 0.239 | 0.2184 / 0.2232 | 0.2189 / 0.2237 (+0.2%) |
| Linked rank-pair accuracy (splits 1 / 2) | survival 80.3 / 80.5% | 81.0 / 80.9% | **81.2 / 81.4%** |
| 2026 regionals, never seen: rank-pair accuracy | binary 81.4%, survival 81.3% | 82.2% | **82.7%** (+0.45 pp [+0.28, +0.63]) |
| 54 CF-rated teams, CF RMSE of the team rating | — | 221 | 217 |

¹ From the 2026-11-05 stability run: other team samples, older data, and the
wrong anchor still counted.

- **What time adds.** It rates problems that nearly everyone solved by *when*
  they were solved, where solved/unsolved says nothing. Sign-ins come down and
  late "easy" problems on strong boards go up.
- **What it costs.** Held-out log loss on final results is 0.6% worse without
  the skip rule (all in teams with no other appearance), and within-contest
  order reversals under field cuts about double.
- **Fresh evidence.** The five 2026 regionals arrived after the `hier_binary`
  setting was frozen. On them the frozen fit beats flat binary by +0.87 pp
  [+0.44, +1.29] in rank-pair accuracy, and the time term adds +0.39 pp
  [+0.24, +0.54]. No new CF-rated board exists yet.
- **Four loader bugs were fixed on the way** and the shipped DE fit was
  re-released (see "Bugs fixed").

## Protocol (written and committed before the formal run)

### Model

The binary fit knows only whether a cell was solved. Here a solved cell also
says in which of K equal slices of the contest window it was solved
(u = solve time / T_c; T_c is the board's latest solve, as in `survival`):

```text
P(solved by the end of slice k) = logistic(g − d_k),   g = (θ_t − b_p) / s
d_1 > … > d_K = 0
log-likelihood = (1 − w) · binary + w · slices
```

- The last slice is the binary model, so θ and b keep its scale.
- The thresholds d are global, estimated by maximum likelihood.
- Priors and their settings are the frozen `hier_binary` ones (σ 300, τ 800,
  σ_b 600, τ_b 400). Nothing there is reselected.
- A setting is (K, w, skip). `skip` also applies `skip_partial`. K = 0 is the
  frozen `hier_binary` fit, called `base`.

### What was seen before this protocol

An exploration on the full data and on split 1, with the CF anchors and both
hand panels in view:

- **Pooled data fit the slice form.** At a fixed gap g, the logit of "solved
  by u" sits a constant below the logit of "solved by the end": about −4.4 at
  u = 0.2, −2.1 at 0.5 and −1.1 at 0.7, for g between −1 and 4.
- **Full weight (w = 1) fixes the floor and costs accuracy.**

  | K (w = 1) | EC sign-in bias | all-72 hand RMSE | fresh panel RMSE | anchors, in-sample | split-1 log loss | pair accuracy |
  |---|---|---|---|---|---|---|
  | base | +398 | 302 | 399 | 225.5 | 0.2363 | 80.98% |
  | 2 | +244 | 242 | 332 | 218.7 | 0.2409 | 81.08% |
  | 3 | +163 | 224 | 324 | 223.1 | 0.2436 | 81.13% |
  | 5 | +99 | 222 | 338 | 232.7 | 0.2456 | 81.21% |
  | 10 | +4 | 222 | 346 | 245.4 | — | — |

  Difficulties stretch within a board (SD 723 → 784 at K = 10): teams solve
  easy problems first, and the slices read that as extra ease.
- **A problem-order term did not repair it.** A threshold shift proportional
  to the problem's distance from its set mean came out small (0.02–0.05 per
  logit) and left split-1 log loss at 0.2422 (K = 3).
- **A small weight keeps most of the floor gain at almost no cost.** K = 5,
  w = 0.1: sign-in bias +243, hand RMSE 240, fresh panel 357, nested LOCO
  221.6 (base 229.1), split-1 log loss 0.2366, pair accuracy 81.18%.
  K = 10, w = 0.25: sign-in bias +38, LOCO 234.1, log loss 0.2389.

So the dose (K, w) is chosen below without CF labels or hand ratings, and
split 1, the anchors and both panels are development data for this candidate.
Split 0, split 2, the stability views and the 2026 boards were not looked at.

### Dose selection (no CF label, no hand rating, no reserved view)

The grid is frozen: K ∈ {3, 5, 10} × w ∈ {0.05, 0.1, 0.25, 0.5, 1}, without
`skip`. The two stages are `hier_binary`'s:

1. **Predictive.** Keep the settings whose held-out cell log loss on split 0
   (final results only) is within 1% of the best of the grid and `base`.
2. **Measurement stability.** Among those, take the setting whose latent
   difficulties on the 15 anchor boards move least over the six training
   views (RMS change over the full-view SD).

The winner is `time`. If no setting survives stage 1, the time term is
rejected.

### Evaluation, run once

Four settings: `base`, `skip` (`base` + `skip_partial`), `time`, `time_skip`.

A setting **passes** if all four hold against `base`:

1. **Hand panels.** On the old panel, EC sign-in |bias| ≤ 150 and no other
   group's RMSE worse by more than 50. On the fresh blind panel, a lower RMSE.
2. **CF accuracy.** Full fields, nested LOCO affine map: the RMSE difference
   interval (paired contest bootstrap) is not entirely above 0.
3. **Team prediction.** On splits 1 and 2, held-out log loss no more than 1%
   above `base` (`skip` settings: on the cells no rule touches). A setting
   with a time term must also not lose linked rank-pair accuracy on either
   split.
4. **Stability.** Drift no larger than `base` on at least 5 of the 8 reserved
   views that have a drift.

**Release candidate:** among the passing settings, the lowest RMSE over both
hand panels pooled (104 problems). Settings within 10 of it tie, and a tie
goes to the one with fewer components (`skip`, then `time`, then `time_skip`).
If none passes, `base` stays.

Also reported, without a pass rule:

- **DE.** Nested-LOCO DE on the current shipped fit, paired on full fields.
  DE is not refit on the stability views: the 2026-11-05 view results used
  other team samples.
- **Fresh boards.** The five 2026 EC regionals were added on 2026-11-15, after
  the `hier_binary` setting was frozen. Fit without the 17 contests added
  that day, then score rank-pair accuracy among each regional's linked teams
  for flat binary, survival and the four settings.
- **CF-rated teams** (54) on each setting's own map.

No fresh CF-rated board exists: on 2026-11-16 the newest ICPC mirror on
Codeforces is contest 2206, already an anchor.

## Amendment after the run: two wrong labels left out

Requested after the results were seen ("remove the documented obvious wrong
rating from the RMSE"). Both labels were documented as wrong before this
work:
- **Uniform Chemistry** (SWERC 2022 B, CF 1776K): CF 3200, about 2000 by hand
  (`problem_rating_audit.md`). Every setting here rates it 1970–1984. It was
  16% of the anchor squared error. It is now out of the CF maps, the nested
  LOCO folds and DE's comparison fit, which leaves 184 anchors.
- **Wuhan 2025 F** in the fresh blind panel: rated 2200 by hand, solved by 779
  of 835 rows (`skip_cells_report.md`). The panel has 31 problems now.

What it changes:

| | 185 anchors, 32 fresh (as pre-registered) | 184 anchors, 31 fresh |
|---|---|---|
| full-field CF RMSE: DE / `base` / `time_skip` | 225.3 / 229.1 / 224.0 | 207.0 / 211.5 / 205.9 |
| EC sign-in bias: `skip` / `time` / `time_skip` | +160 / +160 / +10 | +146 / +146 / −1 |
| settings that pass all four criteria | `time_skip` | `skip`, `time`, `time_skip` |
| release candidate | `time_skip` | `time_skip` |

- The wrong anchor tilted the map: without it the slope rises (`base` 0.910 →
  0.916) and easy problems read about 13 lower. That moves `skip` and `time`
  from 10 over the sign-in limit to 4 under it.
- The release candidate is the same either way. The dose selection uses no
  label and is untouched.
- Shipped DE itself is still trained on all 185 anchors.

## Results

The formal run was done once on 185 anchors. It was repeated after two timing
bugs it exposed were fixed in the loader, and rescored after the amendment.
The selection and the release candidate never changed. The tables show the
final state.

### Dose selection

| Setting | split-0 log loss | within 1% | relative drift, training views |
|---|---|---|---|
| `base` | 0.23644 | — | 0.1326 |
| K 3, w 0.05 / 0.1 / 0.25 | 0.23634 / 0.23642 / 0.23717 | yes | 0.1252 / 0.1209 / 0.1128 |
| K 5, w 0.05 / 0.1 / 0.25 | 0.23640 / 0.23668 / 0.23801 | yes | 0.1229 / 0.1169 / **0.1066** |
| K 10, w 0.05 / 0.1 | 0.23654 / 0.23709 | yes | 0.1202 / 0.1119 |
| K 10, w 0.25; every w ≥ 0.5 | 0.23879 … 0.24673 | no | — |

- **Selected: K = 5, w = 0.25.** More time information always moved the
  difficulties less when the field was cut; the 1% log-loss limit caps it.
- **Thresholds** (full data): 4.30, 2.44, 1.38, 0.63 logits. Solving within
  the first fifth of the window is as hard as solving a problem 747 latent
  points (about 660 CF points) harder by the end; within two fifths, 424;
  three, 240; four, 109.
- **CF maps:** `base` 0.916 b + 488; `time` 0.886 b + 560; `time_skip`
  0.867 b + 605. `skip` treats 2,860 cells as missing.

### The four criteria

| Criterion | `skip` | `time` | `time_skip` |
|---|---|---|---|
| 1. EC sign-in bias, limit ±150 (`base` +385) | +146 ✓ | +146 ✓ | **−1 ✓** |
| 1. worst other-group RMSE change, limit +50 | +25 ✓ | +23 ✓ | +23 ✓ |
| 1. fresh panel RMSE (`base` 379) | 301 ✓ | 315 ✓ | **282 ✓** |
| 2. full-field CF RMSE − `base` | −2.3 [−6.3, +0.6] ✓ | −5.7 [−21.4, +11.3] ✓ | −5.6 [−21.3, +11.4] ✓ |
| 3. log loss / `base`, splits 1 / 2, limit 1.01 | 0.997 / 0.997 ✓ | 1.0065 / 1.0063 ✓ | 1.0022 / 1.0023 ✓ |
| 3. linked pair accuracy − `base` (time settings) | (−0.17 / −0.02 pp) | +0.32 / +0.49 pp ✓ | +0.19 / +0.49 pp ✓ |
| 4. reserved views with drift ≤ `base`, of 8 | 5 ✓ | 8 ✓ | 8 ✓ |
| **passes** | yes | yes | yes |
| both hand panels pooled (103): RMSE (`base` 323, DE 307) | 251 | 249 | **225** |

- **`time_skip` is the release candidate:** lowest pooled hand RMSE, 24 below
  the next setting (the tie band is 10).
- `skip` and `time` each remove about 240 of the +385 sign-in bias; together
  they remove all of it.

### Hand panels (bias / RMSE)

| Group | DE | `base` | `skip` | `time` | `time_skip` |
|---|---|---|---|---|---|
| EC sign-ins (18) | +206 / 271 | +385 / 447 | +146 / 224 | +146 / 204 | **−1 / 111** |
| 2025 EC online (22) | +117 / 168 | +14 / 115 | −8 / 141 | +42 / 138 | +34 / 139 |
| 2023 Nanjing (13) | +189 / 227 | +161 / 184 | +150 / 188 | +133 / 191 | +128 / 201 |
| Mid-Atlantic 2024 (11) | +477 / 544 | +315 / 371 | +306 / 361 | +307 / 376 | +298 / 367 |
| EUC 2025 easy (5) | −153 / 192 | −257 / 290 | −246 / 280 | −92 / 153 | **−89 / 150** |
| CF anchors checked (3) | +20 / 55 | +102 / 137 | +108 / 144 | +13 / 41 | +13 / 36 |
| all 72 | +185 / 290 | +164 / 296 | +95 / 226 | +114 / 215 | **+73 / 196** |
| fresh blind, 16 most-solved | +279 / 351 | +329 / 410 | +156 / 294 | +234 / 318 | +154 / 268 |
| fresh blind, 15 second | +256 / 333 | +254 / 343 | +218 / 309 | +236 / 313 | +215 / 296 |
| Latin America 2023, blind (13) | +490 / 581 | +344 / 455 | +223 / 379 | +309 / 423 | +207 / 356 |

- The 2025 EC online and Nanjing groups get slightly worse RMSE (+24 and +17)
  while their bias moves little. Both stay inside the criterion's allowance.
- Weak North American and Latin American boards still read about 200–300 too
  hard. Time does not touch that; it stays the open question of
  `problem_rating_audit.md`.

### Problems that moved, checked one by one

| Problem | solved | hand or CF | DE | `base` | `skip` | `time` | `time_skip` |
|---|---|---|---|---|---|---|---|
| Shenyang 2022 D (sign-in) | 1076/1083 | 800 | 852 | 1198 | 871 | 860 | 800 |
| EC-Final 2022 M (sign-in) | 687/700 | 1200 | 1328 | 1608 | 1178 | 1319 | 1120 |
| 2025 EC Online II D | 1629/1788 | 1650 | 1606 | 1475 | **1215** | 1645 | 1584 |
| Ōokayama L | 62/68 | 2300 | 2512 | 2273 | **1701** | 2341 | 2255 |
| EC-Final 2021 A "DFS Order" | 606/620 | 1200 | 1252 | 1676 | 1648 | 1374 | 1344 |
| EC-Final 2021 I "Future Coder" | 611/620 | 1350 | 1260 | 1605 | 1497 | 1356 | 1300 |
| THUPC 2022 Final M | 156/157 | — | 1001 | 1769 | 1627 | 1512 | 1452 |
| EUC 2025 F "Mascot Naming" | 98/98 | CF 1900 | 1724 | 1610 | 1623 | 1893 | 1894 |
| EUC 2025 C "Ads" | 97/98 | CF 2100 | 1906 | 1785 | 1796 | 2052 | 2056 |
| APAC 2026 J "Worldwide Playlist" | 113/113 | CF 1700 | 1637 | 1473 | 1484 | 1848 | 1849 |
| Uniform Chemistry (left out) | 78/148 | CF 3200, hand 2000 | 1970 | 1977 | 1984 | 1973 | 1980 |

- **The two known `skip_partial` over-corrections are repaired** (bold): with
  solve times, a problem that weak teams reach late is not a sign-in. 2025 EC
  Online II D comes back to 1584 and Ōokayama L to 2255.
- **Strong-board floors** come down about 300 on EC-Final 2021 A and I.
- **Solved by everyone, but late.** Three CF-labelled problems solved by a
  whole strong board move up 270–380, to within 150 of their labels. Binary
  data cannot separate these from sign-ins.
- **By CF band, in-sample bias** (`base` → `time_skip`): 800–1300 (11
  anchors) +144 → +29; 1300–1900 +46 → +48; 1900–2500 +1 → +63; 2500–3000
  +84 → +82; 3000+ −156 → −191. The flatter map pushes the middle up and the
  top down by 35–60.
- Against `base`, 522 problems move by more than 100 and 143 by more than 200
  (mean −27, SD 86). 32 problems sit at the 800 floor (`base` 9, DE 12).
  Against DE: mean −31, SD 103, Spearman 0.990. No within-board inversions.

### Team prediction (whole appearances held out)

| split 1 / split 2 | survival | binary | `base` | `time` | `time_skip` |
|---|---|---|---|---|---|
| cell log loss, all cells | 0.2766 / 0.2798 | 0.2504 / 0.2548 | **0.2356 / 0.2403** | 0.2371 / 0.2418 | 0.2391 / 0.2436 |
| cell log loss, untouched cells | 0.2611 / 0.2645 | 0.2338 / 0.2386 | **0.2184 / 0.2232** | 0.2191 / 0.2239 | 0.2189 / 0.2237 |
| linked-team log loss, untouched cells | 0.2285 / 0.2299 | 0.1966 / 0.1985 | 0.1896 / 0.1918 | 0.1890 / 0.1911 | **0.1877 / 0.1897** |
| solve-count RMSE per appearance | 1.722 / 1.742 | 1.612 / 1.638 | 1.519 / 1.545 | **1.510 / 1.536** | 1.513 / 1.539 |
| linked rank-pair accuracy | 80.28 / 80.46% | 79.85 / 79.64% | 81.02 / 80.90% | **81.34 / 81.39%** | 81.20 / 81.38% |

- **`time` − `base`:** log loss +0.0015 [+0.0007, +0.0023] / +0.0015 [+0.0008,
  +0.0022]; linked log loss −0.0001 / −0.0004 (intervals include 0); pair
  accuracy +0.32 pp [+0.19, +0.44] / +0.49 pp [+0.34, +0.63].
- **Where the loss is.** Teams with no other appearance: their cells go from
  0.290 to 0.295. They are predicted from the board mean alone, and the time
  term widens the difficulty spread they are scored against.
- **`time_skip` − `base`, untouched cells:** log loss +0.0005 [−0.0003,
  +0.0013] / +0.0005 [−0.0002, +0.0012]; linked log loss −0.0019 / −0.0021
  (intervals exclude 0); pair accuracy +0.19 pp [−0.03, +0.37] / +0.49 pp
  [+0.24, +0.69].
- **`hier_binary` on the changed data:** `base` still beats flat binary by
  0.0148 / 0.0145 log loss and survival by 0.74 / 0.44 pp pair accuracy, as
  on 2026-11-05.

### Fresh boards: the five 2026 EC regionals

Fit without the 17 contests added on 2026-11-15; rank the teams of each
regional that have earlier results. Intervals resample the linked rows of
each board.

| Board (linked rows / rows) | binary | survival | `base` | `skip` | `time` | `time_skip` |
|---|---|---|---|---|---|---|
| Xi'an (150 / 689) | **82.17%** | 79.67% | 81.74% | 81.21% | 81.76% | 81.29% |
| Chengdu (456 / 657) | 81.96% | 81.69% | 83.20% | 83.34% | 83.58% | **83.77%** |
| Wuhan (444 / 541) | 81.21% | 81.44% | 82.09% | 82.07% | **82.39%** | 82.38% |
| Nanjing (323 / 367) | 82.08% | 82.21% | 82.20% | 82.22% | **82.70%** | 82.69% |
| Shenyang (369 / 413) | 79.96% | 80.14% | 81.05% | 81.10% | 81.57% | **81.67%** |
| pooled (333,089 pairs) | 81.36% | 81.31% | 82.23% | 82.26% | 82.62% | **82.68%** |

- `base` − binary: **+0.87 pp [+0.44, +1.29]**; `base` − survival: +0.91 pp
  [+0.40, +1.45]. This is the first confirmation of `hier_binary`'s team
  result on boards that did not exist when its setting was frozen.
- `time` − `base`: **+0.39 pp [+0.24, +0.54]**; `time_skip` − `base`: +0.45 pp
  [+0.28, +0.63]. `time` is at or above `base` on all five boards.
- Xi'an is the exception for `base`: only 150 of its 689 rows link (its
  organisers published no member names), and flat binary is ahead there.
- Five boards refreshed on 2026-11-15 (more unofficial rows) stay in the
  training data; that cannot be undone from the stored files.

### Problem CF accuracy and field stability

Full fields, nested LOCO, 184 anchors: DE 207.0, `base` 211.5, `skip` 209.1,
`time` 205.8, `time_skip` 205.9. Against DE: `base` +4.5 [−11.9, +17.9],
`time_skip` −1.1 [−11.7, +9.0].

| View | `base` | `time_skip` | `time_skip` − `base` [95%] | mean error `base` / `time_skip` | drift `base` → `time_skip` | reversals |
|---|---:|---:|---|---|---|---|
| full | 211.5 | 205.9 | −5.6 [−21.3, +11.4] | +1 / 0 | — | — |
| half_reserved | 223.8 | 209.5 | −14.2 [−28.3, +1.3] | +21 / +12 | 84 → 66 | 3 → 7 |
| quarter_reserved | 253.2 | 228.7 | **−24.4 [−38.3, −11.7]** | +54 / +35 | 151 → 125 | 12 → 20 |
| eighth_reserved | 309.0 | 279.5 | **−29.5 [−40.8, −17.0]** | +82 / +56 | 244 → 207 | 18 → 30 |
| event_only | 228.7 | 222.3 | −6.4 [−20.9, +10.4] | +14 / +8 | 76 → 60 | 8 → 20 |
| event_small | 267.2 | 240.7 | **−26.4 [−42.5, −11.8]** | +31 / +20 | 154 → 131 | 12 → 24 |
| mirror_balanced | 241.9 | 210.7 | **−31.2 [−45.9, −17.3]** | +38 / +24 | 125 → 101 | 11 → 18 |
| strength_pool | 274.9 | 237.2 | **−37.7 [−50.9, −24.3]** | −14 / −12 | — | — |
| strong half | 359.8 | 289.2 | **−70.6 [−95.4, −43.8]** | −3 / −14 | 170 → 118 | 6 → 22 |
| weak half | 319.4 | 288.1 | **−31.3 [−42.1, −19.4]** | +2 / +3 | 142 → 127 | 10 → 25 |
| training halves (4) | 215–225 | 202–217 | −9 … −13 | | 65–80 → 51–64 | 3–12 → 9–21 |
| training quarters (2) | 241 / 233 | 226 / 214 | **−14.7 / −19.5** | | 128 / 120 → 107 / 96 | 21 / 8 → 32 / 19 |

- **CF accuracy is better on every cut view**, with intervals excluding 0 on
  7 of the 9 reserved views. The strong half gains most: there the kept teams
  solve almost everything, and only the solve times tell the problems apart.
- **Composition invariance holds:** strong − weak mean error is 17 points
  apart (`base` 5).
- **Team ratings on a cut board move less:** RMS 91 against 99 latent points
  at a quarter, 146 against 155 at an eighth.
- **Weakness: order reversals about double** (for example 12 → 20 of the
  within-contest pairs at a quarter). The time term gives separate ratings to
  problems that `base` leaves nearly tied near the floor, and those small
  gaps flip when the field is cut. The 2026-11-05 run had DE at 9–31
  reversals on its views.
- `skip` alone changes little here (drift ≤ `base` on 5 of 8).

## Bugs fixed

All four are in `arch_a/load.py`, so they changed the shipped fit. It was
re-released twice on 2026-11-16 (`arch_b.metric` 246.3 → 246.4 → 246.7, inside
its 5-point noise band; every guard passes).

1. **Rows selected on the outcome** (known since 2026-11-10). A row was kept
   only if it solved a *listed* problem. On boards with incomplete problem
   lists that keeps the solvers and drops the failures. Rows that solved only
   unlisted problems now stay as failures of the listed ones.
   - CCPC Harbin 2025 M: 44 of 44 solved → 44 of 654; shipped DE 1961 → 2811.
   - Greater New York 2023 E, J, K, L: +110 … +152. Rocky Mountain 2022 B, G
     and Pacific Northwest 2022 L move down (6 and 2 rows; flagged small).
   - Every other problem moves by at most 19.
2. **Minutes stored as seconds.** The 53 official rows of Rocky Mountain 2023
   (QOJ 1483) carry solve times in minutes (at most 295); its 17 other rows
   are in seconds. Converted on load. Shipped DE on that board moves by
   −236 … +167 (hard problems down; A, C and J up). No other board has this.
3. **A solve from before the start.** One Xi'an 2026 row's only solve is dated
   11.5 days before the contest. A solve with a negative time is no longer a
   contest result.
4. **A board without a problem list** (Pacific Northwest 2022, QOJ 1120) would
   have kept ten rows without cells after fix 1. A board that lists no problem
   keeps no row.

Bugs 2 and 3 were found by auditing solve times for this model; the first
formal run used the data before them.

Not fixed, recorded:
- `data/qoj_ccpc.json` (research only, not in the fit): CCPC Online 2024 has
  2,350 solves with negative times. Convert or drop them before fitting it.
- The raw `data/tagged.json` still holds the minute values; only the loader
  converts them. Code that reads solve times from the raw file sees minutes.
- `data/de_stability_inputs.json` still describes the 2026-11-05 inputs. The
  frozen DE stability experiment cannot be rerun on the current data.

## Shipping

`python -m arch_b.hier_time release` writes:
- `output/problem_ratings_hier.json`: one record per fitted problem with the
  fields of `problem_ratings_calibrated.json` (`difficulty_cf`, `board_rows`,
  `small_board`, …) in the same order, plus `difficulty_cf_se`;
- `output/problem_calibration_hier.json`: the setting, thresholds, CF map
  (0.867 b + 605, from 184 anchors) and input hashes.

What a switch would take:
1. Point `calibrate.problem_cf` at the new file and rerun the exporters
   (`export_viewer`, `export_virtual_calc`, `export_ucup_only`).
2. Decide the team side separately. Team abilities, performances and medal
   bars use the survival fit and its gym-shape map today. This fit's map
   serves teams too (54 CF-rated teams: RMSE 217, mean error +63), but no
   exporter reads it yet.
3. Copy the result to the app (`../my-react-app`).

What the new standard error is: the spread of a difficulty with the teams
held fixed, on the CF scale (median 45, 90th percentile 123). It ignores map
error and board-level error, so it is a lower bound.

## Limits

- **Development data.** The anchors, both hand panels and split 1 were seen
  while the model was designed. Split 2, the stability views and the 2026
  boards were not, and they agree.
- **No fresh CF board.** Problem accuracy on the CF scale has no new
  confirmation; team prediction has one.
- **The weight is a robustness device, not a model.** Full weight misfits:
  teams solve easy problems first. The 0.25 was set by a label-free rule, not
  derived.
- **One window per board.** T_c is the latest solve. On eight boards, all
  with at most 25 rows, it is under 4.3 hours, which makes their solves look
  late. Seven of them are flagged `small_board`.
- **Global thresholds.** Boards with a different rhythm (6-hour Universal Cup
  semifinal, online rounds) share them.
- **Order reversals** under field cuts rise (above).
- **Weak, weakly linked boards** still read 200–300 too hard by hand.
- **The forward replay with member priors** was not rerun: its panel carries
  neither solve times nor attempt counts.

## Next steps

1. Decide whether to ship `time_skip` for problems, and whether teams follow.
2. Confirm on the first CF-rated 2026 board (NERC or a 2027 championship
   mirror), scored against shipped DE with nothing refit.
3. Weak boards: CF handles for 20–30 Latin American or Mid-Atlantic teams.
4. A per-board window from the contest's real duration would remove the T_c
   proxy; the data has no duration field today.

## Reproduce

```bash
PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m arch_b.hier_time evaluate 4   # ~25 min on 4 cores
PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m arch_b.hier_time release      # ~1 min
python -m unittest tests.test_hier_time
```

`evaluate` runs the selection first and caches every stage under the
gitignored `hier_binary_run/` (`time_*.json.gz`); delete those after a data
change. It needs `output/problem_ratings_calibrated.json` for the DE column,
not the `hier_binary all` cache. Results: `output/hier_time.json`; every
problem under the four settings: `output/hier_time_ratings.json`.
