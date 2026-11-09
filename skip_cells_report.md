# Skipped cells as missing data

2026-11-08; second test (`skip_mirror`) 2026-11-09. Follow-up to `problem_rating_audit.md`. Code: `arch_b/skip_cells.py`;
tests: `tests/test_skip_cells.py`. Research only.

## Pre-registered rules and pass criteria (written before any run)

A cell is *skipped* when, within the cells being fitted:
- the row made no submission to the problem;
- more of the board solved that problem than solved the row's own hardest
  solved problem.

Skip status is recomputed from the cells each fit may use: training
appearances only, or a stability view's active rows.

| Rule | Skipped cells treated as missing |
|---|---|
| `base` | none (selected `hier_binary`: σ 300, τ 800, σ_b 600, τ_b 400) |
| `skip_all` | in every row (the audit's diagnostic) |
| `skip_partial` | only in rows that submitted to ≤ 2 problems |

The setting is fixed and nothing is reselected. A rule **passes** only if all
four of these hold:
1. **Hand panel** (72 problems from the audit):
   - EC sign-in |bias| ≤ 150;
   - no other group's RMSE worse than `base` by more than 50.
2. **CF accuracy:** on full fields (nested LOCO map), the rule − `base` RMSE
   interval (paired contest bootstrap) does not lie entirely above 0.
3. **Team prediction:** on held-out appearances (splits 1 and 2), scored on
   the cells no rule touches, the log-loss difference interval does not lie
   entirely above 0 on either split.
4. **Stability:** on the 9 reserved views, drift vs the full view is no larger
   than `base`'s on at least 5.

The recorded-date forward replay is not run: its panel has no attempt counts.

## Verdict

**`skip_partial` passes all four criteria; `skip_all` fails criterion 4
(stability).** `skip_partial` is the better data rule for the hierarchical
candidate. Nothing shipped changed, and the selected `hier_binary` outputs are
untouched.

| Criterion | `skip_all` | `skip_partial` |
|---|---|---|
| 1. EC sign-in bias (base +387) | +71 ✓ | +148 ✓ |
| 1. worst other-group RMSE change | +38 (anchors) ✓ | +27 (EC online) ✓ |
| 2. full-field CF RMSE − base | −0.9 [−6.1, +3.9] ✓ | −1.9 [−5.4, +0.9] ✓ |
| 3. log loss − base, split 1 / 2 (×10⁻⁴) | −0.7 [−7.9, +6.7] / +6.7 [−0.7, +14.5] ✓ | −6.0 [−10.0, −2.2] / −3.6 [−7.2, 0.0] ✓ |
| 4. reserved views with drift ≤ base | 3 of 9 ✗ (2 of 8, see correction below) | 8 of 9 ✓ (7 of 8) |

## Results

**Cells.**
- `skip_all` treats 19,201 cells in 12,583 rows as missing.
- `skip_partial` treats 2,717 cells in 1,383 rows as missing.
- Full-data CF maps: base 0.907 b + 515; `skip_all` 0.867 b + 618;
  `skip_partial` 0.896 b + 540.

**Hand panel** (bias / RMSE vs the audit's hand ratings):

| Group | DE | base | `skip_all` | `skip_partial` |
|---|---|---|---|---|
| EC sign-ins (18) | +209 / 273 | +387 / 448 | +71 / 185 | +148 / 225 |
| 2025 EC online (22) | +118 / 168 | +3 / 115 | −31 / 140 | −21 / 142 |
| 2023 Nanjing (13) | +185 / 223 | +153 / 177 | +119 / 201 | +141 / 180 |
| Mid-Atlantic 2024 (11) | +469 / 536 | +315 / 369 | +287 / 337 | +307 / 359 |
| EUC 2025 easy (5) | −171 / 207 | −257 / 290 | −221 / 249 | −248 / 282 |
| CF anchors checked (3) | +13 / 52 | +105 / 147 | +135 / 185 | +111 / 154 |
| all 72 | +182 / 288 | +160 / 296 | +64 / 212 | +90 / 225 |

The EC solve-rate table (mean − DE) changes only at the floor:

| Rule | >95% solved | 70–95% | 5–70% |
|---|---|---|---|
| base | +140 | −16 | −10 … +7 |
| `skip_all` | −53 | −55 | −23 … −11 |
| `skip_partial` | −3 | −45 | −12 … +8 |

Sign-in examples (hand / DE / base / `skip_partial`):

| Problem | hand | DE | base | `skip_partial` |
|---|---|---|---|---|
| 2025 Nanjing C | 850 | 1198 | 1433 | 899 |
| EC-Final 2022 M | 1200 | 1327 | 1608 | 1181 |
| Shenyang 2022 D | 800 | 858 | 1203 | 877 |

Both rules still overcorrect 2025 EC Online II D (hand 1650; base 1472,
`skip_partial` 1211).

**CF accuracy.**
- **Full fields:** base 229.5, `skip_all` 228.5, `skip_partial` 227.6, DE
  225.6. Base reproduces `hier_binary` exactly.
- **Other views:** no `skip_partial` − base difference has an interval
  excluding 0. `skip_all` is worse on the reserved half: +5.7 [+2.1, +9.6].
- **Weak / strong halves:** `skip_partial` 332.5 / 374.6, base 332.6 / 373.3.

**Team prediction** (held-out appearances, 20% whole-appearance splits):
- **Non-skipped cells:** `skip_partial` is better on both splits, by −6.0 and
  −3.6 ×10⁻⁴ log loss.
- **All cells**, including the skipped ones: both rules lose, by construction.
  They predict skipped cells as likely solves, but those cells are recorded as
  zeros.
  - `skip_partial`: +17 / +21 ×10⁻⁴;
  - `skip_all`: +63 / +73 ×10⁻⁴.
- **Not a pre-registered criterion: linked rank-pair accuracy.** It is slightly
  worse for both rules:
  - `skip_partial` −0.17 / −0.10 pp, intervals excluding 0;
  - `skip_all` −0.33 / −0.27 pp.

  Ranks come from all cells, skipped ones included, so this is the same
  bookkeeping cost.
- **CF-rated teams (54):** RMSE base 218, `skip_partial` 219, `skip_all` 236.

**Stability.**
- **Drift vs the full view:** `skip_partial` is at or below base on every
  reserved view except the reserved half (84.8 vs 84.3). Its order reversals
  equal base's within 1 everywhere.
- **`skip_all`:** drifts more on 6 of 9, and its reversals rise from 3 to 9 on
  the reserved half.
- **Team θ drift at a quarter:** `skip_partial` 103.9 vs base 103.1 (RMS).

## Limits

- **The hand panel is not independent.** One reviewer wrote it after seeing
  the base and DE numbers, and its sign-in group motivated the rule.
  Criterion 1 is therefore a consistency check, not a test.
- **Development data.** The CF anchors, views and splits are the same data
  every earlier choice used. A fresh confirmation set is still needed.
- **Not run:** the recorded-date forward replay. Its panel has no attempt
  counts.
- **The partial rule is a heuristic.** Rows with ≤ 2 submissions include
  genuinely weak teams that tried little. It does not fix every floor problem
  (2025 EC Online II D).

## Second test: `skip_mirror` (2026-11-09, pre-registered before its run)

**Why.** 2025 EC Online II D (`2524 D`) is the easiest problem on its board:
1,629 of 1,788 non-zero rows solved it. `skip_partial` treats 124 of its 159
failures as missing, which makes D read like a sign-in (1211 vs hand 1650).
- 123 of those 124 rows are official registrations (QOJ team id
  `$DEFAULT…`).
- 86 of them solved only C and never submitted D.
- They solved C late (median minute 164, against 90 for all C solvers), and
  D's median solve time is 125, later than C's.

So these are weak teams that read D and failed it, not mirror accounts. On the
18 EC sign-ins, by contrast, the skipped rows are almost all unofficial `id:`
accounts. Overall, 643 of the 2,717 `skip_partial` cells sit in official rows,
and 123 of those are 2524 D.

**Rule.** `skip_mirror` is `skip_partial`, but only in rows that are not
official registrations (`official_of_row` false). It changes nothing on the 28
boards with no official flag, which hold 1,242 rows.

**Criteria.** The same four, against `base`. `skip_mirror` replaces
`skip_partial` as the preferred rule only if both hold:
- it passes all four;
- its 2025 EC online hand RMSE is below `skip_partial`'s (142).

The hand panel motivated this rule as well, so 2524 D is a consistency check,
not evidence.

### Result: `skip_mirror` fails criterion 1; `skip_partial` stays preferred

The rerun reproduced `base` and `skip_partial` exactly.

| Measure | base | `skip_partial` | `skip_mirror` |
|---|---|---|---|
| cells treated as missing | 0 | 2,717 (1,383 rows) | 2,074 (921 rows) |
| 1. EC sign-in bias / RMSE | +387 / 448 | +148 / 225 ✓ | **+174 / 236 ✗** |
| 1. 2025 EC online bias / RMSE | +3 / 115 | −21 / 142 | −9 / 115 |
| 2025 EC Online II D (hand 1650) | 1472 | 1211 | 1458 |
| all-72 hand RMSE | 296 | 225 | 224 |
| 2. full-field CF RMSE − base | — | −1.9 [−5.4, +0.9] ✓ | −2.0 [−5.3, +0.6] ✓ |
| 3. log loss − base, non-skipped, split 1 / 2 (×10⁻⁴) | — | −6.0 / −3.6 ✓ | −5.7 [−8.9, −2.5] / −3.4 [−6.8, −0.1] ✓ |
| log loss − base, all cells (×10⁻⁴) | — | +17 / +21 | +13 / +17 |
| 4. reserved views with drift ≤ base | — | 7 of 8 ✓ | 7 of 8 ✓ |
| CF-rated teams RMSE (54) | 218 | 219 | 219 |

- **Why it fails.** Official rows also skip sign-ins: 3 of 7 skipped rows on
  Shenyang 2022 D (1096 D), and 2 of 13 on EC-Final 2022 M (1197 M). Keeping
  them puts those two back at 1094 (hand 800) and 1373 (hand 1200).
- **The tradeoff.** "Official" does not cleanly separate mirror accounts from
  weak teams. The cases differ in a different way:
  - on 2524 D the skipped problem is only slightly easier than the row's
    hardest solve: 1,629 vs 1,423 solves;
  - on a sign-in it is far easier.

  A margin rule would target that difference. It is not tested: it would be
  the third rule fitted to the same hand panel, and it needs fresh boards.
- **Decision.** Under the pre-registered decision rule, `skip_partial` stays
  preferred. 2524 D remains a known `skip_partial` error.

**Correction to the first test's criterion 4.**
- `strength_pool` is the drift reference for the `strong` and `weak` views,
  so its own drift is 0 for every rule and it counts as a trivial "win".
- The real counts over the 8 views with a drift are:
  - `skip_partial` 7 of 8;
  - `skip_all` 2 of 8.

  The table above said 8 of 9 and 3 of 9. The verdicts do not change.

Reproduce: `PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.skip_cells 8`.
It takes ~4 min with 8 workers and needs the `hier_binary all` view cache in
`hier_binary_run/`. Output: `output/skip_cells.json`.
