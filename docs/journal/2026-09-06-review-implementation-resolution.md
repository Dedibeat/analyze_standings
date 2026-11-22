# Review implementation resolution (2026-09-06)

The concrete correctness defects that could be fixed from the repository's
available evidence are now repaired:

- `llm_crosscontest.analyse` no longer reads held-out CF labels while constructing
  predictions. Each fold learns a BT-minus-survival contest feature and its
  coefficient from training contests only. Mutating held-out labels leaves both
  plain and adjusted predictions unchanged. Reanalysis of the existing responses
  gives **245.43 plain / 246.78 adjusted LOCO RMSE**; the wider paid run remains
  unjustified.
- Every Spearman helper and the AUC rank-sum now use average ranks for ties. The
  metric rejects non-finite primary/guard values, requires exactly **185 problems
  / 15 contests** of anchor coverage, and uses the corrected raw ceiling
  **251.9 = 246.9 + 5**. The Kattis guard now accepts only unique titles with at
  least three matches corroborating the source contest: 427 pooled matches,
  survival Spearman **+0.795**.
- `predict_eval` now loads the same 260-contest joint configuration as the shipped
  fit, assigns repeated resolved team/problem responses to one side of the split,
  and derives contest duration from training solves only. It is explicitly an
  imputation check for retained appearances, not a future-contest forecast. The
  corrected run has 923,842 cells / 920,158 response groups; binary is log-loss
  **0.2040**, Brier **0.0623**, AUC **0.9727**, and survival is **0.2329 / 0.0701 /
  0.9674**.
- The loader preserves `(contest_id, source_row)` as a participation identifier.
  The virtual calculator keys rank-derived performance by this identifier, so
  two rows merged to one ability identity no longer overwrite each other.
- CF-prior roster completeness now requires every rating history to be
  corroborated on that exact standing row, not merely present globally. Coverage
  is **54 identities / 295 rows** after the correction (previously 57 identities).
- Binary and survival fits reject non-finite or unconverged results and verify
  that the final objective is not below its initial value. The full suite passes
  **42 tests**.
- The calibrated artifacts now call the quadrature of conditional fit SE and
  contest-level SD `difficulty_cf_partial_se`; the ambiguous
  `difficulty_cf_se` field was removed. This fixes the claim/label, not the
  missing statistical work needed for calibrated CF prediction intervals.

The full survival metric remains **245.4 calibrated / 246.9 raw CF RMSE**, with
all guards passing; the binary control is **256.0 / 248.1**. Still open because
the required evidence is absent or the work is a new experiment: adjudicating
identity unions, collecting recorded contest durations/dates, constructing fresh
frozen forecast and regional-transfer sets, estimating full joint/calibration
uncertainty, and reconstructing the missing raw gym/campaign snapshots.
