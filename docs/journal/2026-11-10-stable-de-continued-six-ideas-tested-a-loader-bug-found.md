# Stable DE, continued: six ideas tested, a loader bug found (2026-11-10)

**Request.** Continue the stable DE experiment: propose ideas, test them, check
ratings by hand against statements, and chase unusual ratings. Research only;
nothing shipped changed. Write-up of the skip tests: `skip_cells_report.md`
(third and fourth tests). The other experiments are the scripts in
`scripts/stable_de_explore/`; their numbers are recorded in this entry.

**Ideas tested on the hierarchical candidate.**

| Idea | Result |
|---|---|
| σ_b beyond the grid edge (800–1600) | Worse on both selection stages (log loss 0.23931 → 0.23958 at 800; relative drift 0.136 → 0.137 → 0.161 at 1600). **600 is an interior optimum.** |
| Cut-board level float, re-measured over 8 random quarter cuts | Mean drift **+11 (SE 7)**, not +52: the reserved view was one draw. What is real is tail compression: >95% solved +196, <2% solved −129. No prior strength (τ, τ_b, σ, σ_b) changes it. |
| Per-board ability spread (empirical Bayes, 243–548) | Log loss −0.0001…−0.0002 (intervals include 0); strong-board floors unchanged (EC-Final 2021 A 1676 → 1695). Negative. |
| Timing term at the floor | Nested LOCO 230–232 vs 229.5. Negative. |
| Curved CF map | 229.2–230.7 vs 229.5; the affine map is calibrated conditional on the prediction (within ±35 between 1400 and 3400). Negative. |
| `skip_margin`, `skip_early` | Both fail their pre-registered criteria; `skip_partial` stays preferred. |

**Fresh blind hand panel** (`FRESH` in `scripts/problem_rating_audit.py`): the
two most-solved problems of 16 EC boards the old panel does not touch, rated
before any model number was seen. It confirms the sign-in inflation: `base`
+328 on the 16 most-solved, `skip_partial` +155. One hand rating is wrong
(Wuhan 2025 F, 2200 by hand, solved by 93%).

**Bugs and unusual ratings chased.**
- **Loader selection bug (affects shipped ratings; not fixed).** 14 contests
  have incomplete problem lists. `row_solved_any` keeps only rows that solved
  a *listed* problem, which selects on the outcome.
  - CCPC Harbin 2025 (2575) lists only M: the fit sees M as 44 of 44 solved,
    but 44 of 654 teams solved it. Shipped DE 1947, hierarchical 1847; with
    the 610 rows kept as failures of M it is **2805**.
  - Also moved: Rocky Mountain 2022 G +265, B +82; Greater New York 2023 K
    +178, L +29, J +19; Pacific Northwest 2022 L +92. Every other problem
    moves by at most 6, and the anchor RMSE is unchanged (225.7 → 225.8).
  - A fix changes `arch_a/load.py`, one of the frozen hashed inputs, and needs
    a re-release. It is left for a decision.
- **Board means are not board levels.** On boards where every team has many
  other boards, μ_c is a regression coefficient: Aobayama 4562 and Ōokayama
  4161 against median abilities of 2672 and 2522. Problem ratings there are
  fine (−24, +3 vs DE), but μ must not be read or exported as the board level.
- **World Finals boards:** fitted solves exceed QOJ's counts by 12–29%. These
  are 13–48 mirror rows per board (the known context effect), not an error.
- **Ōokayama L** (see `skip_cells_report.md`): a `skip_partial` over-correction.
- **Weak, weakly linked boards read too hard (open).** Latin America 2023
  (383 rows, 12 linking rows), 13 problems rated blind: DE **+486**, base
  +349, `skip_partial` +236. This matches Mid-Atlantic 2024 (+469 / +316).
  - Not the estimator: a parametric simulation on the real design recovers the
    board within −13…+13 (Mid-Atlantic +25…+95, the top only with a 1.8×
    wider ability spread).
  - Not the hyperpriors (free τ, τ_b: +341) and not unofficial rows'
    untouched problems (dropping them all: +238 vs +236).
  - With every link cut the board reads +455, so the 12 linking rows pull it
    down by about 100 and agree with the fitted level (expected 54.7 solves,
    actual 51). Eight are unofficial QOJ accounts.
  - CF labels cannot settle it: the weak anchor boards (μ 1430–1680) are
    well linked and show no trend when held out (−128…+194).
  - So either the hand scale is about 300 low on weak fields, or these
    linking accounts under-perform there. It needs outside data: CF handles of
    some Latin American or Mid-Atlantic teams.

**Code and checks.**
- The exploratory scripts are kept in `scripts/stable_de_explore/` (25 files;
  its `README.md` maps each script to its finding). They were ported from the
  session's scratch folder; six were rerun from the repository root and
  reproduce the numbers above (`base_fit`, `map_curvature`, `floor_anchors`,
  `loader_unlisted_rows`, `problem_failures`, `float_seeds`). The other 19
  were not rerun after the port.
- The Latin America blind ratings are the `latam` dictionary in
  `scripts/stable_de_explore/latam_*.py`; the table is in
  `problem_rating_audit.md`.
- Full suite: **234 tests pass** (system Python 3.11); 2 are new
  (`skip_margin`, `skip_early`).

**Hand-off: where to continue.**
1. **Loader bug (decision needed).** Keep rows that solved only unlisted
   problems as failures of the listed ones, or drop the 4 selected boards'
   problems (2575 M; 1482 E, J, K, L; 1115 B, G; 1121 L). Either way
   `arch_a/load.py` changes, so `data/de_stability_inputs.json` hashes, the
   `test_unknown_problem_solve_does_not_retain_row` test, the shipped fit and
   the app copy must follow. Check first:
   `python scripts/stable_de_explore/loader_unlisted_rows.py`.
2. **Weak-board level (open question).** Get CF handles for 20–30 Latin
   American or Mid-Atlantic teams and compare their CF ability with the
   fitted team ratings (`cf_prior.team_abilities` does this for the 54 elite
   teams). That decides between "hand scale 300 low" and "level 300 high".
3. **Skip rule.** `skip_partial` is still the preferred rule and is still not
   folded into `hier_binary`'s defaults. Two panels have now shaped rules; a
   fifth rule needs a third, untouched panel.
4. **Not worth repeating:** σ_b above 600, per-board ability spread, a timing
   term at the floor, a curved CF map, the stability penalty.
5. **Still waiting on data:** CF-rated 2026 regionals for a fresh confirmation
   (none were in the data on 2026-11-10); the 2026 EC online statements.

Run the scripts from the repository root, `base_fit.py` first:
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=. ./.venv/Scripts/python scripts/stable_de_explore/base_fit.py`.
Their caches go to the gitignored `hier_binary_run/explore/`.
