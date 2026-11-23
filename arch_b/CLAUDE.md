# arch_b/: module map

Architecture B: joint item-response fits and everything built on them. Run modules
from the repository root (`python -m arch_b.<module>`). Each module's docstring
gives its commands and outputs. Shared helpers come from `arch_a.load` (standings
loader) and `arch_a.elo`.

## Production (shipped since 2026-11-16)

- `hier_time.py`: hierarchical binary fit with solve-time slices. `release` writes
  `output/problem_ratings_hier.json` and `problem_calibration_hier.json`.
- `hier_binary.py`: hierarchical binary Rasch, the base that `hier_time` extends.
- `skip_cells.py`: the `skip_partial` rule (skipped cells treated as missing).
- `shipped.py`: one cached full-data production fit and its affine map, shared by
  all exporters.
- `calibrate.py`: `problem_cf` lookup of shipped ratings, plus the legacy DE
  calibration CLI.
- `joint.py`: one MAP over tagged, supplemental and Universal Cup contests; also
  defines the fit inputs.
- `model.py`, `survival.py`: binary Rasch and the solve-time survival likelihood
  (the earlier engines).

## Exporters (products)

- `export_virtual_calc.py` + `virtual_calc_template.html`
- `export_viewer.py` + `viewer_template.html`
- `medals.py`, `export_medal_viewer.py` + `medal_viewer_template.html`
- `export_ucup_only.py`

## Metric and validation

- `metric.py`: the north-star metric, calibrated LOCO CF RMSE.
- `validate.py`: checks against the LLM difficulty.
- `external_validate.py`: CF, Kattis, gym mirrors and AOJ, by region.
- `predict_eval.py`: held-out solve prediction.
- `gym_difficulty.py`: fixed-θ difficulty on the gym-mirror population.
- `aoj.py`: AOJ external-difficulty artifact.
- `hier_calibrate.py`: partially pooled per-contest and per-region calibration
  levels (the uncertainty model).

## Forecasts and medals (independent of the rating fit unless noted)

- `online_gold.py`, `online_medals.py`: medal chances at EA regionals from online
  results and slot rules.
- `quota_teams.py`: quota-seat entrants and why they got the seat.
- `hk_link.py`, `hk_gold.py`, `hk_field_2026.py`: the Hong Kong / Macau field and
  its gold chances.
- `medal_predict.py`: medal-cutoff prediction and regional chooser.
- `member_forecast.py`: recorded-date forecasts with member priors.
- `tabfm_gold.py`: TabFM gold-table baselines and scoring.

## Research only (write their own `output/*.json`; never change shipped files)

- **Rating rethink:**
  - `context_fit.py`: mirror/event context in the fit.
  - `field_transport.py`: does calibration survive a change of field.
  - `dynamic_rating.py`: time-varying team ratings.
- **DE line, superseded:**
  - `de_stability.py`, `de_stability_data.py`
  - `de_release_audit.py`
  - `fit_mechanism_audit.py`
  - `shipped_fit_audit.py`
- **Calibration:**
  - `calibration_experiment.py`
  - `calibration_ablation.py`, `calibration_ablation_transfer.py`
  - `calibration_audit.py`
  - `calibration_interpretation.py`
  - `tabfm_bigquery.py`
- **Older experiments:**
  - `cf_prior.py`: ability-side CF anchor (inert).
  - `gym_merge.py`: negative result.
  - `twopl.py`, `twopl_region.py`: 2PL prototype; overfits.
  - `season_experiment.py`
  - `data_influence.py`
- `run.py`: the old end-to-end Architecture B run (binary or `--survival`).

The frozen experiments verify SHA-256 provenance by file path. Don't "fix" a
stale hash by editing a saved output.
