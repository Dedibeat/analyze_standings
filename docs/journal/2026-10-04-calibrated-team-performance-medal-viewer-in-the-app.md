# Calibrated team performance; medal viewer in the app (2026-10-04)

**Request.** Improve the team performance rating on the app's Contests page
using the right version from the analyzer, preferably calibrated. Then update
the medal viewer and ship it into the app. Choices put to the user and
accepted: binary-fit performance; in the medal viewer, add only a calibrated
cutoff-team performance; add a "Medals" nav link in the app.

**Problem.** `export_virtual_calc` (and so the app) ranked a result against the
**survival** fit's abilities and mapped the result through the survival
**difficulty** map. The DE audit found that the survival fit compresses
abilities (CF ≈ 2.85 × θ_survival but 1.65 × b_survival), while the binary fit
maps both axes to CF at slope ~0.98. It concluded that team-ability outputs
must not reuse the survival difficulty map.

**Check** (scratch script, both fits as shipped, same 77,770 rows):

| | survival (old) | binary (new) |
|---|---|---|
| CF team abilities (`cf_prior`, 54 teams): CF − mapped θ | +205 | −91 |
| same: slope / Pearson / RMSE | 1.46 / .750 / 313 | 0.91 / .803 / 222 |
| DE-implied performance vs performance: slope / RMSE | 0.80 / 233 | 0.97 / 141 |
| median performance − DE-implied, weakest → strongest band | −231 → +79 | +59 → +91 |

"DE-implied" is the rating at which the CF formula,
`1/(1+10^((R−P)/400))`, gives the row's actual solve count on the shipped
DE ratings of its contest's problems. Rows with zero or all problems solved
are skipped. So the new performance agrees with the problem ratings the app
shows and does not drift with team strength.

**Change.**
- `export_virtual_calc.performance_fit()` (new) returns the binary joint fit,
  the gym-shape + affine CF map of its difficulties, and every row's CF
  performance keyed by participation. `build_data` uses it. Problem rows stay
  the shipped DE ratings.
- `medals`: every cutoff team gains `performance_cf`, read from the same
  lookup, so it equals the calculator's value for that row.
  `performance_elo`, θ, bars and badges are unchanged (survival).
- `medal_viewer_template.html`: the cutoff panels and the lowest-gold table
  show `performance_cf` ("perf … CF", "Perf (CF)") instead of the raw Elo
  value.
- **Not changed:** `export_viewer` still shows survival-map abilities and
  performances, so `ratings_viewer_b.html` and the calculator now disagree on
  team performance. `medal_predict`/`online_gold` read only the bars.

**Effect.**
- **Calculator** (69,519 team rows; contests, problems and rows otherwise
  identical): mean performance 2117 → 2225, SD 600 → 513. Median |change|
  is 109 and the maximum 645. By old band the change is +271 (< 1600), +132,
  +68, +24 and +4 (≥ 2800).
- **Gold cutoff teams:** median 2687 CF (range 2376–2977). The 84 cutoff
  values all equal the calculator's row values.
- **App check:** EC Online (II) 2026, 5 solved with a 600-minute penalty:
  rank 134 of 2,534, performance 2807 (was 2895). This is identical to the
  same computation run here.
- All 132 tests pass. No pinned number changed.

Run (Windows: `PYTHONUTF8=1`): `python3 -m arch_b.export_virtual_calc`,
`python3 -m arch_b.medals`, `python3 -m arch_b.export_medal_viewer`. Then,
in `../my-react-app`, run `python3 scripts/export_contest_fields.py` and copy
`output/medal_viewer.html` to `data/medal_viewer.html`.
