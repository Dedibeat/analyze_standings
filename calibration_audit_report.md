# DE prediction audit and anchor-contest influence — 2026-09-10

DE's development gain survives removal of each individual anchor contest, but
its feature support is much narrower than the deployment population. This run
adds reproducible research predictions and evidence about their limitations;
it finds no cached-data defect and establishes no new accuracy gain or global
replacement. The production calibration remains unchanged.

The [protocol](calibration_audit_plan.md) was written before execution. The
[implementation](arch_b/calibration_audit.py) and
[machine-readable result](output/calibration_audit.json) execute the roadmap's
largest-correction audit and calibration-label contest-influence study. DE's
feature bundle and inner alpha/lambda grid were unchanged throughout.

## What was verified

All 3,159 survival/binary appearances agree with the joint loader and local source
records on task IDs, titles, solve counts, and field sizes. All 185 CF anchors
have unique cached contest-scoped title matches and matching cached labels.
Input hashes from the prior ablation and transfer artifacts match. The original
OOF predictions replay within 7.74e-12 CF points; saved values are retained for
the original-OOF comparison. Coverage remains 260 contests / 73,023 appearances
of teams / 185 anchors in 15 CF contests.

This verifies local cached joins and feature provenance. It does not adjudicate
roster unions, independently verify external task versions, or supply missing
recorded durations or new confirmation labels. Links in the row tables point
to source tasks; no new online collection or manual external version audit was
performed. Missing region values remain missing.

## Anchor-contest influence

Original nested LOCO RMSE is **246.9061 raw affine / 245.4277 locked gym /
226.5661 DE**. Each row below removes an entire CF contest's labels and canonical
tasks, then repeats outer contest LOCO on the remaining cohort. DE alpha/lambda
selection happens again strictly inside each remaining outer training set.
There are 210 new outer fits; the underlying standings fits stay fixed.

The last column compares refitted DE with the **original OOF predictions on
exactly the same remaining rows**. It isolates refitting from simply removing
an easy or hard contest from the score. Results across deletions are dependent
sensitivity checks, not independent replications or confidence intervals.

| Excluded CF contest | Remaining anchors | Raw RMSE | Gym RMSE | DE RMSE | DE refit change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1773 | 173 | 244.88 | 242.90 | 227.73 | +0.06 |
| 1776 | 173 | 231.89 | 229.03 | 209.85 | -0.13 |
| 1906 | 172 | 249.52 | 246.36 | 229.63 | +0.68 |
| 1912 | 173 | 252.86 | 249.83 | 233.83 | +1.50 |
| 1938 | 172 | 246.14 | 246.77 | 226.20 | +0.12 |
| 1949 | 174 | 251.33 | 249.67 | 228.18 | +0.05 |
| 2041 | 171 | 250.28 | 250.37 | 224.89 | -1.91 |
| 2045 | 172 | 250.79 | 248.49 | 228.62 | -0.08 |
| 2052 | 172 | 252.92 | 250.77 | 229.85 | -0.46 |
| 2068 | 174 | 235.09 | 233.44 | 216.90 | -2.91 |
| 2073 | 172 | 242.36 | 242.39 | 225.44 | +0.04 |
| 2157 | 177 | 244.01 | 242.71 | 222.83 | -0.63 |
| 2172 | 171 | 255.11 | 253.49 | 234.52 | +1.43 |
| 2181 | 172 | 248.37 | 247.98 | 228.65 | -0.08 |
| 2206 | 172 | 249.74 | 248.82 | 230.12 | +1.80 |

DE beats both controls after every deletion. Its matched-cohort RMSE shift is
-2.91 to +1.80 points; no deletion crosses the prespecified 5-point audit
threshold or reverses the gain. Individual predictions can still move by up
to 117.9 points (when CF 2041 is removed). Thus aggregate stability does not
make individual corrections precise, and this reused development set cannot
validate regional transfer.

## Feature support is the principal new finding

The training anchors span **77–323 retained teams per contest**. A marginal
range check against each applicable training set gives:

| DE feature outside training range | Original OOF (185) | Full refit, not OOF (3,159) |
| --- | ---: | ---: |
| raw_b | 2 | 94 |
| binary_minus_survival | 2 | 447 |
| conditional_fit_se | 2 | 267 |
| solve_rate | 0 | 0 |
| log_field_size | 26 | 1610 |
| **Any feature** | **31** | **1,840** |

Full-refit extrapolation affects 58.2% of appearances; field size alone flags
1,610. Looking only at raw difficulty's 94 tail appearances misses 1,746
additional appearances outside some other DE feature range. These are marginal
ranges: being inside every range does not establish joint-distribution support,
and a flag is neither an error verdict nor a calibrated uncertainty estimate.

Seven of the ten largest full-refit corrections belong to **Aobayama (QOJ
1965), with 50 retained teams**. All its raw difficulties are within the anchor
raw range, but its field size is below training support. Its largest correction
is +534.3 CF points. This is a concrete confirmation-design gap: an improvement
on medium-sized anchored fields cannot certify these smaller/larger fields.

## Deterministic OOF examples

The top-ten correction, improvement, and deterioration lists select 23 unique
anchors. Order below follows their first selection; overlapping reasons and all
features are saved in the artifact. Error change is DE absolute error minus raw
absolute error, so negative values improve. Source links identify the cached CF
match. These are selected diagnostic examples, not a representative evaluation
sample.

| CF task | CF rating | Raw OOF | DE OOF | Error change |
| --- | ---: | ---: | ---: | ---: |
| [Football](https://codeforces.com/contest/1773/problem/F) | 800 | 1417.1 | 1074.0 | -343.1 |
| [Make Triangle](https://codeforces.com/contest/1949/problem/K) | 2800 | 2428.3 | 2741.7 | -313.4 |
| [LOL Lovers](https://codeforces.com/contest/1912/problem/L) | 800 | 1081.7 | 779.7 | -261.4 |
| [Funny or Scary?](https://codeforces.com/contest/1949/problem/D) | 2600 | 2558.8 | 2844.7 | +203.5 |
| [Dating](https://codeforces.com/contest/1949/problem/F) | 2200 | 2041.4 | 2325.8 | -32.7 |
| [Amanda the Amoeba](https://codeforces.com/contest/1949/problem/J) | 2600 | 2605.1 | 2880.9 | +275.8 |
| [Scooter](https://codeforces.com/contest/1949/problem/G) | 2300 | 2133.0 | 2401.4 | -65.6 |
| [Number Maze](https://codeforces.com/contest/2172/problem/E) | 1200 | 1265.9 | 999.0 | +135.1 |
| [Minesweeper String](https://codeforces.com/contest/2206/problem/F) | 2400 | 2252.6 | 2483.6 | -63.8 |
| [Parallel Sums](https://codeforces.com/contest/2206/problem/E) | 2500 | 2233.8 | 2461.1 | -227.3 |
| [Statues](https://codeforces.com/contest/2068/problem/H) | 2700 | 2343.2 | 2545.1 | -201.9 |
| [Urban Planning](https://codeforces.com/contest/2068/problem/B) | 3100 | 2157.8 | 2331.4 | -173.7 |
| [Condorcet Elections](https://codeforces.com/contest/2068/problem/A) | 2300 | 1964.1 | 2135.2 | -171.1 |
| [Easy as ABC](https://codeforces.com/contest/1906/problem/A) | 1000 | 1185.4 | 1019.4 | -166.0 |
| [Walking Boy](https://codeforces.com/contest/1776/problem/A) | 800 | 1090.0 | 924.9 | -165.0 |
| [Amusement Park Rides](https://codeforces.com/contest/2068/problem/K) | 3000 | 2762.7 | 2924.8 | -162.1 |
| [Crossing the Railways](https://codeforces.com/contest/1776/problem/E) | 3500 | 3479.6 | 3274.2 | +205.5 |
| [Reflect Sort](https://codeforces.com/contest/2206/problem/H) | 1800 | 1863.3 | 2064.0 | +200.7 |
| [Aquatic Dragon](https://codeforces.com/contest/2045/problem/D) | 3500 | 3419.0 | 3226.0 | +193.0 |
| [Damage per Second](https://codeforces.com/contest/1949/problem/E) | 2900 | 3033.6 | 3223.0 | +189.5 |
| [Mascot Naming](https://codeforces.com/contest/2068/problem/F) | 1900 | 1801.9 | 1634.1 | +167.8 |
| [The Ultimate Wine Tasting Event](https://codeforces.com/contest/2068/problem/J) | 2000 | 1793.1 | 1630.3 | +162.9 |
| [Railway Construction](https://codeforces.com/contest/2041/problem/N) | 3300 | 3256.6 | 3109.5 | +147.1 |

Six selected examples each come from the 2024 and 2025 Europe Championships;
both contain wins and losses. There are two DE order changes among 1,063
non-tied raw within-contest pairs (1,064 total pairs). Low reorder counts do
not imply that the correction is a constant contest offset.

## Separate full-refit examples — not OOF

These are predictions from all-anchor refits, with no CF outcome comparison.
The complete 3,159-row table includes features, source references, support flags,
and raw/gym/DE predictions; it is explicitly a research artifact.

| QOJ task | Field size | Raw refit | DE refit | Correction |
| --- | ---: | ---: | ---: | ---: |
| [1965 L: Square Connection](https://qoj.ac/contest/1965/problem/L) | 50 | 2280.7 | 2815.0 | +534.3 |
| [1965 H: 12 Grid](https://qoj.ac/contest/1965/problem/H) | 50 | 2180.0 | 2711.4 | +531.4 |
| [1965 N: Palindromic Path](https://qoj.ac/contest/1965/problem/N) | 50 | 2486.0 | 3010.2 | +524.2 |
| [1997 K: Search For Mafuyu](https://qoj.ac/contest/1997/problem/K) | 765 | 1589.5 | 1072.8 | -516.7 |
| [1965 O: Twin Contests](https://qoj.ac/contest/1965/problem/O) | 50 | 2257.0 | 2772.8 | +515.9 |
| [1965 M: Divide Digit String](https://qoj.ac/contest/1965/problem/M) | 50 | 2475.2 | 2987.2 | +512.0 |
| [1965 D: Swap Counter](https://qoj.ac/contest/1965/problem/D) | 50 | 2616.4 | 3111.4 | +495.0 |
| [1954 J: Max Mod](https://qoj.ac/contest/1954/problem/J) | 63 | 2379.8 | 2867.7 | +487.9 |
| [1780 F: Stage: Agausscrab](https://qoj.ac/contest/1780/problem/F) | 531 | 1444.9 | 957.2 | -487.7 |
| [1965 C: 2-Power Rush](https://qoj.ac/contest/1965/problem/C) | 50 | 2710.5 | 3190.1 | +479.5 |

## Fixed Luxor appendix — not OOF

Both cached appearances of every predefined shared QOJ task are retained. Field
sizes are 137 and 154, inside the anchor range. The task/title consistency check
passes; external version/context equivalence remains unverified in this run.
The listed gaps are descriptive, with no requirement that they be zero.

| Shared task | Raw absolute gap | DE absolute gap |
| --- | ---: | ---: |
| 8674: Riddle of the Sphinx | 5.1 | 101.0 |
| 8676: Three Kinds of Dice | 6.3 | 24.7 |
| 8677: Carl’s Vacation | 14.5 | 37.8 |
| 8680: Turning Red | 66.0 | 145.3 |
| 8683: Bridging the Gap | 53.2 | 18.0 |

For Riddle of the Sphinx, binary-minus-survival disagreement is -345.3 versus
-225.0 despite very similar raw difficulties and solve rates. The full feature
vectors in the artifact make the 101.0-point DE gap reviewable, but this is not
proof of a flawed identity or a causal attribution to that feature. The full
refit has 103 changed orders among 18,142 non-tied within-contest pairs overall.

## Issue log and next decision

| Finding | Evidence and action |
| --- | --- |
| Cached source/feature defect | None reproduced; all coverage, joins, counts and field checks pass. No data correction is justified by this audit. |
| Single-anchor-contest dependence | No aggregate threshold crossing; keep DE fixed as the development candidate. Individual shifts remain material. |
| Feature extrapolation | 1,840 appearances flagged. A confirmation set must cover small and large fields, estimator disagreement and conditional-SE ranges, in addition to raw difficulty and regions. |
| Shared-task context | Two Luxor gaps widen substantially; preserve both appearances and obtain version/context evidence before any pooling change. |
| Missing confirmation evidence | No fresh held-out label set or external task-version adjudication was assembled. Production promotion remains unsupported, especially with the prior mixed Kattis/AOJ results. |

The supported next step is a frozen confirmation design stratified by field
size and the other DE evidence features. This audit does not justify clipping
corrections, removing field size, choosing a support threshold to improve the
same score, changing identity unions, or another hyperparameter search.

## Reproduction

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  ./.venv/bin/python -m arch_b.calibration_audit
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  ./.venv/bin/python -m unittest discover -s tests
```

The artifact records source/input/plan hashes, canonical input-table and output
row-table hashes, deterministic selection lists, every exclusion/held/training
membership, all nested settings, and predictions. A stale prior input or a
changed input during execution stops publication. This command writes only
`output/calibration_audit.json`; prior experiment and production outputs are
unchanged. The test suite passes 64 tests, including excluded/held-label
mutation, canonical task purges, deterministic selection, stale provenance,
training-only support ranges, and non-finite control rejection.
