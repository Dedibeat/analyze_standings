# DE release (2026-09-28)

**Request.** Redeploy the ratings with DE in `../my-react-app`. The four open
release choices were put to the user. The answers: use the roster-fixed fit;
clip DE's features to the anchor range; give online-round problems no special
handling; and release DE to every problem-rating consumer. This follows the
release steps at the end of [de_release_audit.md](../reports/rating/de_release_audit.md).

**Data.** `scripts/attach_online_rosters.py` was applied in place to
`data/tagged.json`. The result's SHA-256 (`8c9ddf74…`) is the audited
candidate's, and a second run leaves it unchanged. Only members of online-round
rows change; the serialization is identical.

**Fits.** `arch_b.run` and `arch_b.run --survival` were rerun (3,159 problems
each). On the saved survival file, raw and gym LOCO are 246.9288 and 246.1274,
exactly the audit's candidate. `arch_b.metric` reads **246.3** (245.4 before),
and every guard passes (Kattis .795, AOJ .563, solve count .997, raw LOCO
246.9).

**Calibration** (`arch_b.calibrate`). The shipped `difficulty_cf` is now DE
with clipped features. `full_anchor_fit(..., "clip", DE)` is reused from
`arch_b.de_release_audit` rather than reimplemented. Inner folds select
alpha = 1, lambda = 1, as in the audit.
- **Match with the audit:** the output equals the audit's catalog entry for
  clipped DE exactly. Against the previous shipped ratings the mean change is
  +69.96, the |change| quantiles are 107.7 / 256.6 / 315.5 / 544.3, and
  1,677 / 599 / 44 problems move by ≥100 / 200 / 400. Online-round problems
  move −73.6, and Aobayama 1965 H goes to 2695.8.
- **Range:** 800–3996, mean 2517; 10 problems sit on the 800 floor.
- **No uncertainty field.** The gym-map `difficulty_cf_fit_se`,
  `difficulty_cf_level_sd` and `difficulty_cf_partial_se` do not describe DE,
  and DE has no SE of its own (update plan, finding 3).
- **`output/problem_calibration.json`** (new) records the method, features,
  alpha/lambda, anchor feature ranges, display rule and the raw-fit input
  hashes.
- **`--binary` removed:** DE uses both fits, so a binary-only calibration no
  longer applies.
- Rollback is the previous commit: all outputs are tracked.

**Consumers.** `calibrate.problem_cf(ds.problems)` reads the shipped file keyed
by `(contest_id, problem_label)`, and a `problem_id` mismatch stops the build.
The exporters use it for problem rows; their own full-precision refits no
longer rate problems.
- `export_viewer`: problem difficulty is DE. The ±SE column is gone
  (`chipSe` removed from the template), and so is the now-unused Laplace SE
  call.
- `export_virtual_calc`: the reference problems table is DE.
- `export_ucup_only`: `ucup_only_ratings.json` is now a filtered copy of the
  shipped file, so the script no longer fits anything.
- **Parity check:** 1,579 viewer, 2,934 calculator and 684 UCup-only problem
  rows all equal the shipped values at their display precision (0
  mismatches).

**Kept on the scalar gym-shape map** (update plan, finding 2): team abilities
and performances in the viewer, the calculator's performance lookup, and
`arch_b.medals`. `medals` and `export_medal_viewer` were rerun on the new fit;
the Shanghai gold city mean moves 2474.2 → 2471.2. The difficulties in
`medal_badges.json` stay on the gym map, so they differ from the shipped DE
ratings. This is by design: badges are defined on the raw fitted order. The
metric also still scores the gym map on the raw fit, so it measures the fit
rather than the shipped DE calibration.

**Tests.** Pins moved to the new fit:
- `test_calibration_experiment`: raw 246.9288, gym 246.1274.
- `calibration_ablation.CONTROL_DET_RMSE`: 229.4028153.
- `test_medal_predict`: Shanghai 2471.2.

`output/calibration_experiment.json` was regenerated with `--baseline-only`
(DET 229.4028), so the DET-reproduction test compares against the current
fit. All 108 tests pass.

**Not regenerated** (historical or unaffected):
- Architecture A outputs;
- the research artifacts (`calibration_ablation*.json`,
  `calibration_audit.json`, `shipped_fit_audit.json`, `data_influence.json`,
  `de_release_audit.json`, `fit_mechanism_audit.json`), which record their own
  runs;
- `online_gold.json`, whose rating-fit comparison reads `medal_badges.json`
  and so is a few CF points stale;
- `medal_predict_viz.html`, which has no generator.

**App deploy.** `../my-react-app/data/problem_rating.json` is a byte copy of
the shipped file; the app's `DETAILS.md` has the details.

Run: `python3 scripts/attach_online_rosters.py data/tagged.json data/tagged.json`,
`arch_b.run`, `arch_b.run --survival`, `arch_b.calibrate`, then the exporters,
`arch_b.medals`, `arch_b.export_medal_viewer` and `arch_b.metric` (on Windows
set `PYTHONUTF8=1`).
