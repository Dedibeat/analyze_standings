# Identity fix: no team plays two rows of one contest (2026-11-17, third entry)

**Request.** Fix the identity chaining and run it through the release
protocol.

**Fix** (`arch_a.load.member_identity`). The two-shared-member links are
kept (the July near-miss rule) but applied last, in file order, and a link
is refused when its two components already played a common contest.
Test: `test_two_shared_members_never_merge_rows_of_one_contest` (fails on the
old loader).

**Checked before the formal run** (shipped setting, full data, in-sample):
- rows sharing a team inside one contest 1,062 → 47 (19 teams; exact rosters
  or stable ids, not pair links); teams 37,600 → 37,797; most rows per team
  125 → 93;
- problem ratings against the shipped file: mean −1.1, median |change| 1.0,
  95th percentile 6, max 395;
- anchor RMSE 198.9 → 198.8; CF 1900–2500 bias +63 → +62;
- **Jinan D stays at 2359.** The −54 of the previous entry came from
  dropping every pair link, which also cuts links between rosters that never
  met. That is a model change, not this bug fix, and is not part of it.

**Pass rule, written before the run.** Rerun `hier_time evaluate` (caches
cleared) and `arch_b.metric`. The fix ships if all hold:
1. `time_skip` still passes the four criteria and is still the release
   candidate;
2. its nested-LOCO CF RMSE (184 anchors) is within 5 of the previous 205.9;
3. every `arch_b.metric` guard passes and the metric stays within its 5-point
   band of 246.7.
Otherwise the old loader is restored and nothing is re-released.

**Amendment before the second run: a fitter bug.** The first run stopped in
the selection grid: split 0, `k10_w0.25`, `hier_binary.fit` raised "line
search failed" at Newton step 3. Reproduced with one BLAS thread per worker
(passes with eight):
- gradient norm 2.3e-8; Newton step 9.1e-5, below the 1e-3 tolerance;
  predicted decrease 5e-12 on an objective of 237,016, below its rounding;
- the line search halves to 1e-8 without a provable decrease and raises.

It is a converged fit refused by rounding; thread count changes summation
order, so it is intermittent. Fix: when the line search fails but the whole
Newton step is below the tolerance, the fit has converged. Every fit that
passed before takes the same path. `arch_b.metric` (246.7, all guards pass)
ran before this fix and does not use `hier_binary`. The pass rule is unchanged.

**Result: passes; re-released.**

| | before (b3119a1 run) | after |
|---|---|---|
| dose selected / release candidate | `k5_w0.25` / `time_skip` | same |
| `time_skip` criteria (hand, CF, teams, stability) | all pass, 8/8 views | all pass, 8/8 views |
| nested-LOCO CF RMSE, `time_skip` (184 anchors) | 205.9 (vs DE [−11.7, +9.0]) | 205.7 ([−12.0, +8.8]) |
| hand panels pooled, `time_skip` | 225.4 | 225.3 |
| held-out log loss ratio / pair accuracy, splits 1, 2 | 1.0022, 1.0023 / +0.19, +0.49 pp | 1.0010, 1.0024 / +0.35, +0.40 pp |
| CF-rated teams RMSE, `time_skip` | 217.0 | 218.9 |
| `arch_b.metric` | 246.7, guards pass | 246.7, guards pass |

- Shipped problem ratings: every one of 3,409 moves by at most 13 (median
  1). Jinan 2022 D stays 2359.
- Medal bars and cutoff performances move by at most 7. One cutoff ability
  moves a lot, and it is the bug: Shenyang 2025's last silver (Xiamen
  University, 没能成为人) was one identity with the school's stronger
  随机增量 roster, chained through a member swapped in 2024; the two then
  played side by side on 3295, 4071 and 4113. Ability 2123.5 → 1940.4; it now
  has its own 6 rows (15 before).
- Regenerated: `hier_time.json`, `hier_time_ratings.json`,
  `problem_ratings_hier.json`, `problem_calibration_hier.json`,
  `virtual_calc.html`, `ratings_viewer_b.html`, `medal_badges.json`,
  `medal_viewer.html`. Not regenerated: the historical DE/survival files
  (`problem_ratings_calibrated.json` and kin), the app copy in
  `../my-react-app`.
- Note: since the 2026-11-16 switch, `full_data`'s `de` column in
  `both_panels`/`hand` reads `calibrate.problem_cf`, i.e. the shipped hier
  file, not DE (it reads 225.4 here, 306.9 in the run before the switch).
  `cf_full_fields.DE` is still nested-LOCO DE.

**Tests.** 246 pass except 3 in `test_medal_predict`
(Shanghai city mean 2490.8 pinned, reads 2606.8; ordering; pooling). They
fail identically before this change: `medal_predict` reads only
`medal_badges.json`, which the 2026-11-16 release regenerated without
updating the pins. Left as found. `pypinyin` and `openpyxl` were installed
in the venv for the 10 modules that import them.

**Not done.** Dropping all cross-contest pair links (D 2305, the −54 of the
previous entry) is a separate model change and was not tested in the
protocol. The gym re-fetch is still open.

