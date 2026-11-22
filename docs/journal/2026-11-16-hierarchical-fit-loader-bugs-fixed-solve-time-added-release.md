# Hierarchical fit: loader bugs fixed, solve time added, release candidate (2026-11-16)

**Request.** Continue the hierarchical binary experiment and improve it for
shipping; fix the bugs; try combining solve time in a problem rating. Later in
the session: leave the documented wrong rating out of the RMSE. Full write-up:
`hier_time_report.md`. Code: `arch_b/hier_time.py`, `arch_b/hier_binary.py`
(`fit` only), `arch_a/load.py`; tests `tests/test_hier_time.py` (9) and
`tests/test_load.py` (+1). **244 tests pass** (Python 3.13; `pypinyin` had to
be installed for `hk_link`).

**Assumptions stated, not asked.**
- "For shipping" was read as: make the candidate shippable and write its
  ratings in the shipped layout. DE is still the shipped problem rating; the
  switch is a decision left open.
- "Fix the bugs" was read as the decision the 2026-11-10 hand-off asked for
  on the loader bug: fix it at the source and re-release the shipped fit.
- "The documented obvious wrong rating" was read as both labels on record as
  wrong: the CF anchor Uniform Chemistry and the fresh-panel hand rating of
  Wuhan 2025 F.

**Loader bugs (all `arch_a/load.py`; shipped fit re-released twice).**
1. `row_solved_any` kept a row only if it solved a *listed* problem, which
   selects on the outcome where a problem list is incomplete. Rows that solved
   only unlisted problems now stay as failures of the listed ones. Shipped DE:
   CCPC Harbin 2025 M 1961 → 2811; Greater New York 2023 E, J, K, L
   +110 … +152; Rocky Mountain 2022 B, G and Pacific Northwest 2022 L down;
   every other problem by at most 19.
2. Rocky Mountain 2023 (1483): its 53 official rows store solve times in
   minutes (at most 295), the 17 others in seconds. `MINUTE_BOARDS` converts
   on load. Shipped DE there: −236 … +167. A scan of every data file found no
   other such board.
3. Xi'an 2026: one row's only solve is dated 11.5 days before the start.
   `_solved` no longer counts a negative-time solve.
4. Pacific Northwest 2022 (1120) lists no problem. After fix 1 it would have
   kept ten rows without cells; a board that lists none keeps no row.

- The guard keeps its `(standing, problem_labels)` signature, so its eight
  callers are unchanged. The viewers and the calculator index rows through the
  same guard and stay aligned.
- `arch_b.metric`: 246.3 → 246.4 (fix 1) → 246.7 (fixes 2–4); all guards pass.
- Pins moved: `test_calibration_experiment` raw 248.1847 / gym 246.7115,
  `CONTROL_DET_RMSE` 229.9593327750, `test_medal_predict` Shanghai 2490.8.
  `output/calibration_experiment.json` and `output/calibration_ablation.json`
  were regenerated as on 2026-11-15.
- Regenerated: `problem_ratings{,_b,_survival,_calibrated}.json`,
  `problem_calibration.json`, the three viewers, `virtual_calc.html`,
  `ucup_only_ratings.json`, `medal_badges.json`, `medal_viewer.html`.
- Not fixed: the raw `data/tagged.json` still holds the minute values;
  `data/qoj_ccpc.json` (not in the fit) has 2,350 negative solve times in CCPC
  Online 2024; `data/de_stability_inputs.json` still describes the 2026-11-05
  inputs; the app copy in `../my-react-app` lags.

**Solve time in the fit.**
- A solved cell also says in which of K equal slices of the window it was
  solved: `P(solved by slice k) = logistic(g − d_k)`, `d_K = 0`, so the last
  slice is the binary model and the scale is kept. Thresholds are global and
  fitted by maximum likelihood, alternating with the fit.
- The slice likelihood enters at weight w next to the binary one at 1 − w.
- `hier_binary.fit` gained `cuts`, `cut_weight`, `start` and returns `x` and
  `b_se`. Its default path computes the same numbers as before.

**Explored first (development data, recorded in the report).**
- Full weight fixes the floor (sign-in bias +398 → +4 at K = 10) but stretches
  difficulties within a board and costs held-out log loss (0.2363 → 0.2456 at
  K = 5): teams solve easy problems first.
- A problem-order term (threshold shift proportional to the distance from the
  set mean) came out at 0.02–0.05 per logit and did not repair that. Dropped.
- A small weight keeps most of the floor gain at almost no log-loss cost.

**Protocol, committed before the formal run** (`ea09e59`).
- Dose grid K ∈ {3, 5, 10} × w ∈ {0.05, 0.1, 0.25, 0.5, 1}; `hier_binary`'s two
  label-free stages (split-0 log loss within 1%, then least latent drift over
  the training views). Selected: **K = 5, w = 0.25** (relative drift 0.1066
  against 0.1326 for `base`).
- Four settings: `base`, `skip` (`skip_partial`), `time`, `time_skip`; four
  pass criteria against `base` (hand panels, full-field CF, held-out teams,
  drift on the reserved views).

**Amendment: wrong labels left out** (requested after the results). Uniform
Chemistry (SWERC 2022 B; CF 3200, about 2000 by hand, 1970–1984 in every
setting) is out of every CF map and RMSE in `hier_time`, leaving 184 anchors;
Wuhan 2025 F is out of the fresh panel (31 problems). Shipped DE is still
trained on all 185. As pre-registered (185 / 32), only `time_skip` passed:
`skip` and `time` read +160 on the sign-ins against a limit of 150. Without
the wrong anchor they read +146 and all three pass. The candidate is the same.

**Results** (184 anchors).

| | DE | `base` | `time_skip` |
|---|---|---|---|
| full-field CF RMSE, nested LOCO | 207.0 | 211.5 | 205.9 (vs DE −1.1 [−11.7, +9.0]) |
| weak half / strong half / reserved eighth | — | 319 / 360 / 309 | 288 / 289 / 280 |
| reserved views with lower drift than `base` | — | — | 8 of 8 |
| EC sign-in bias | +206 | +385 | −1 |
| hand panel (72) / fresh blind (31), RMSE | 290 / 343 | 296 / 379 | 196 / 282 |
| held-out log loss, untouched cells, splits 1 / 2 | — | 0.2184 / 0.2232 | 0.2189 / 0.2237 |
| linked rank-pair accuracy, splits 1 / 2 | — | 81.02 / 80.90% | 81.20 / 81.38% |
| 2026 regionals, linked rank pairs | binary 81.36% | 82.23% | 82.68% |

- **Release candidate: `time_skip`.** Lowest pooled hand RMSE (225, against
  251 for `skip` and 249 for `time`).
- With all 185 anchors: DE 225.3, `base` 229.1, `time_skip` 224.0.
- The two known `skip_partial` over-corrections are repaired: 2025 EC Online
  II D 1215 → 1584 (hand 1650); Ōokayama L 1701 → 2255 (about 2300).
- Problems a whole strong board solved late move up to their CF labels: EUC
  2025 F 1610 → 1894 (CF 1900), C 1785 → 2056 (CF 2100), APAC 2026 J
  1473 → 1849 (CF 1700).
- **Fresh confirmation, team side.** The five 2026 EC regionals were added
  after the `hier_binary` setting was frozen. Fit without the 17 contests of
  2026-11-15: `base` − flat binary +0.87 pp [+0.44, +1.29]; `time` − `base`
  +0.39 pp [+0.24, +0.54]. Xi'an (150 of 689 rows linked) is the one board
  where flat binary leads.
- **No fresh CF board.** Checked the Codeforces contest list on 2026-11-16:
  the newest ICPC mirror is 2206, already an anchor.

**Costs and limits.**
- `time` alone loses 0.6% held-out log loss, all in teams with no other
  appearance (0.290 → 0.295).
- Order reversals under field cuts about double (12 → 20 at a quarter).
- The flatter map moves the 1900–2500 band up 60 and the top band down 35.
- T_c is the latest solve; on eight boards with at most 25 rows it is under
  4.3 hours. Thresholds are global.
- Weak, weakly linked boards still read 200–300 too hard by hand (Latin
  America 2023 +207, Mid-Atlantic 2024 +298).
- The anchors, both hand panels and split 1 are development data. The run
  was done once, repeated after loader fixes 2–4, and rescored after the
  amendment; the selection and the candidate never changed.
- Not rerun: `hier_binary all`, `skip_cells`, the member-prior forward replay
  (no solve times in its panel), DE on the stability views.

**Outputs.**
- `output/hier_time.json` (selection, criteria, every table);
- `output/hier_time_ratings.json` (every problem under the four settings and
  DE);
- `output/problem_ratings_hier.json` and `output/problem_calibration_hier.json`
  (release candidate; records carry the shipped fields plus
  `difficulty_cf_se`; map 0.867 b + 605).

**To ship** (not done): point `calibrate.problem_cf` at the new file, rerun
the exporters, decide separately whether team ratings follow, copy to the app.

Run:
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m arch_b.hier_time evaluate 4`
(~25 min on 4 cores; caches `hier_binary_run/time_*.json.gz`, delete them
after a data change), then `python -m arch_b.hier_time release` (~1 min).
