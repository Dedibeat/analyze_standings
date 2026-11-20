# Shipped ratings flag small boards (2026-11-09, second entry)

**Request.** Flag the shipped ratings that come from tiny boards (previous
entry).

**Change.** `arch_b.calibrate` now adds two fields to every record of
`output/problem_ratings_calibrated.json`:
- `board_rows`: rows with at least one solve on the board, the same field
  count DE's log-field-size feature uses (`_raw_problem_features`);
- `small_board`: `board_rows < SMALL_BOARD_ROWS` (10).

`output/problem_calibration.json` describes the flag.

- **Flagged:** 65 problems on 10 boards: Mid-Atlantic 2022/2024, Mid-Central
  2022/2023, Pacific Northwest 2022/2024, Rocky Mountain and North Central
  2022. They have 1–8 rows each.
- **Ratings unchanged:** on the rerun, all 3,185 records keep every old field
  byte for byte.
- **Meta input hashes refreshed:** the old `inputs_sha256` was stale. It was
  recorded before c877cfd rewrote the survival and binary files (online-round
  names only); the new hashes match the committed blobs.
- **Correction to the previous entry:** `difficulty_se` is the raw survival
  Laplace SE, not a DE standard error; DE has none.

**Tests:** all 232 pass.

**Not updated:**
- the viewer (`export_viewer`) and the virtual calculator, which do not show
  the flag;
- `ucup_only_ratings.json`, which has no small boards;
- the app copy, `../my-react-app/data/problem_rating.json` (another repo): it
  lags the shipped file until it is copied again.

Run: `PYTHONUTF8=1 python -m arch_b.calibrate`.
