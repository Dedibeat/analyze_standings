# Skipped cells as missing data: tested (2026-11-08)

**Request.** Test a narrower version of the audit's skipped-cell rule through
the `hier_binary` protocol. Report: `skip_cells_report.md`; code
`arch_b/skip_cells.py`; tests `tests/test_skip_cells.py` (5); output
`output/skip_cells.json`. `hier_binary.team_scores` gained an optional
`cell_mask`; its default is unchanged. Research only; nothing shipped changed.

**Rules and criteria**, frozen before the run:
- `base`: the selected hier_binary fit;
- `skip_all`: skipped cells (no submission, easier than the row's hardest
  solve) are missing in every row;
- `skip_partial`: the same, but only in rows that submitted ≤ 2 problems.

Skip status is recomputed from the cells each fit may use. To pass, a rule
needs:
1. the hand-panel EC sign-in |bias| ≤ 150, with no other group's RMSE worse by
   more than 50;
2. a full-field CF RMSE interval vs base not entirely above 0;
3. log loss on non-skipped held cells not worse on either split;
4. drift ≤ base on at least 5 of the 9 reserved views.

**Verdict: `skip_partial` passes all four; `skip_all` fails stability (3 of
9).**

| Measure | base | `skip_all` | `skip_partial` |
|---|---|---|---|
| cells treated as missing | 0 | 19,201 | 2,717 (1,383 rows) |
| EC sign-in hand bias | +387 | +71 | +148 |
| all-72 hand RMSE | 296 | 212 | 225 |
| full-field CF RMSE (DE 225.6) | 229.5 | 228.5 | 227.6 (−1.9 [−5.4, +0.9]) |
| log loss − base, non-skipped cells (×10⁻⁴) | — | −0.7 / +6.7 | −6.0 / −3.6 |
| reserved views with drift ≤ base | — | 3 of 9 | 8 of 9 |

- **Floor only.** EC problems solved by more than 95% move from +140 to −3 vs
  DE. The middle is unchanged.
- **Overcorrection left.** 2025 EC Online II D stays too easy (1211 vs hand
  1650).
- **Costs:**
  - log loss on *all* held cells is worse (+17 / +21 ×10⁻⁴): the rule
    predicts skipped zeros as likely solves;
  - linked rank-pair accuracy −0.17 / −0.10 pp (not pre-registered);
  - CF-rated-team RMSE is unchanged (219 vs 218).
- **Limits:**
  - the hand panel motivated the rule, so criterion 1 is a consistency check;
  - this is development data;
  - the forward replay was not run (no attempt counts in its panel).

Run (~4 min with 8 workers; needs the `hier_binary all` cache):
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.skip_cells 8`.
