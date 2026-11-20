# Rating rethink reviewed; experiments 0–2 run (2026-11-04, second entry)

**Request:** review the last rating_rethink audit (written by GPT-6 astra) and
run its experiments. Full report:
[rating_rethink_experiments.md](../reports/rating/rating_rethink_experiments.md). Research only;
no shipped fit, calibration, rating or export changed.

**Review.**
- **Every reproducible claim holds.** The audit JSON and `predict_eval`
  reproduce exactly. Fresh `estimate_joint` fits reproduce both saved fits
  record for record.
- **Calibration metadata.** The `problem_calibration.json` hashes match neither
  the 09-28 nor the 10-04 committed fits; the cause was not found.
- **Gap.** The proposed pooled mirror offset is not identified by within-team
  evidence. For single-context teams the shared ability prior sets it.
  - Only 135 identities have both event rows and UCup mirror rows, and 2 have
    event and account mirror rows.
  - The naive estimates are +167 pooled, UCup +270, and an account slope of
    2.23 (nine prior SDs). They measure who enters mirrors.

**Experiment 1** (`arch_b/context_fit.py` → `output/context_experiment.json`).
Offsets apply to all teams (naive), multi-context teams, or onsite bridges.

| Teams carrying the offset | Mirror offset at σθ 400 / 800 / 1600 |
|---|---|
| naive UCup | +270 / +227 / +205 |
| multi-context (776 teams) | +300 / +247 / +217 |
| onsite bridges (137 teams) | **+89 / +75 / +70** |

- **Per-team gap**, b fixed: +51 [+9, +89]. The slope is +12 per 400 of
  ability.
- **Whole-appearance hold-out**, three seeds, linked cells:
  - naive −5.6e-4 [−7.6, −3.4] (a population mean for mirror entrants);
  - onsite −0.05e-4 [−1.2, +1.2].
- **Event-field transfer** (identity-safe folds):
  - onsite −0.85e-4 [−1.61, −0.02];
  - multi-context +738e-4 on teams seen only as mirrors.
- **Split-half spacing:** unchanged.
- **Mixed-board difficulties** sit within −3 … +30 of an event-only refit;
  context terms move them by at most 11.
- **Verdict:** no mirror term in the fit.
- **Incidental:** binary affine LOCO is about 232 at σθ = 800/1600 in every
  variant, against 247 at 400. This is a lead only.

**Experiment 2** (`arch_b/field_transport.py` → `output/field_transport.json`).
Boards are re-measured with outside-fold abilities, drawn by team, with an
identity-safe target and a non-target survival window.
- **Strong − weak, independent selection** (mean CF, 966 problems):
  - DE **+188** (solve rate +209, survival b −170, disagreement +80, SE +69);
  - binary b +5, survival b −95;
  - blend −72, DE_reference −107;
  - noise floor about ±3.
- **Pool − quarter:** DE +65, others +24 … +29.
- **Anchor RMSE, contest-held-out:**
  - DE leads only on full fields (228 vs 247–255);
  - it ties on random halves;
  - it is worse on quarter (−28 … −31) and weak fields (−40 … −70); those
    intervals exclude 0.
- **Deployed-like joint refit** of the 15 anchor boards:
  - DE leads on the full and event-only boards (+16 … +27 over the others);
  - on a small event-only field it errs by −116 mean (RMSE 321 vs 276–288);
  - between that field and an equally small mirror-heavy one, DE moves 98 CF
    and the blend 4.
- **On the anchors, field-independent calibrators cost 15–18 LOCO points:**
  blend 240.67; DE_reference 243.21, +17.6 [+1.7, +34.8].
- **Verdict:** keep DE shipped, but treat difficulties outside its anchors'
  field support (EC online, EC-Final, small boards) as extrapolation.
  Choose any replacement on a fresh confirmation set.

**Defects found and fixed before the final runs.** An interim Codex review
and my own checks found these:
- an oscillating per-problem Newton refit (now bisection,
  `context_fit.solve_decreasing`);
- same-team rows crossing splits;
- target solve times setting the survival window;
- a reference population fit on all data.

Not run: the audit's experiments 3–5. Metadata was not regenerated.

**Reproduce:**
- `./.venv/bin/python -m arch_b.context_fit`: 49 fits, 30–60 min.
- `./.venv/bin/python -m arch_b.field_transport`: about 15 min.

Both JSONs carry input and code sha256 hashes. Tests:
- `tests/test_context_fit.py` (8) and `tests/test_field_transport.py` (7) are
  new.
- The full suite passes: 196 tests.
- `.venv` lacked `pypinyin` and `openpyxl`, which 8 existing test modules
  import. Both were installed with pip.

## Hand-off: population control in progress (2026-11-04)

A second Codex review asked for qualified wording and a control model.
- **Wording (points 2–4)** is fixed in `rating_rethink_experiments.md` only:
  - the per-team (+51 [+9, +89]) and joint (+89) estimates are reported
    separately, as associations;
  - the transfer gain gets a multiple-comparisons caveat;
  - "aggregate log loss" replaces "predictions";
  - cell and contest coverage is given for the large losses.
- **Control (point 1), coded, not yet run.** `context_fit` gains M4 and M5:
  - M4 estimates a prior mean per entry-type group (`GROUPS`, `entry_groups`,
    `fit(group=...)`) with no within-team offset;
  - M5 is M4 plus the onsite-bridge offset;
  - 2 new tests; `tests/test_context_fit.py` passes (10).
- **The committed `output/context_experiment.json` predates M4/M5.**

Next:
1. Run `./.venv/bin/python -m arch_b.context_fit`. It takes about 15–20 min
   with nothing else running; on Windows set `PYTHONUTF8=1`.
2. Compare M4 with M1_naive (linked hold-out −5.6e-4).
   - If M4 matches, the naive gain is a population-structure effect.
   - Then rewrite the Experiment 1 "Reading" bullet and verdict in the report,
     and carry points 1–4 into this entry and `README.md`.
3. Run the full suite and commit. A fresh `.venv` may need `pypinyin` and
   `openpyxl`.
