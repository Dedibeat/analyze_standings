# Rethinking performance and problem ratings (2026-11-04)

**Request:** reconsider the whole approach and suggest improvements,
experiments and replacements. “Performance” is interpreted as team contest
performance. The review is [rating_rethink.md](../reports/rating/rating_rethink.md), based on
code at `872b3cc`, the earlier reviews, and fresh local checks.

**Recommendation:** test a context-aware binary item-response model, with
separate timing and member-informed roster priors. Keep survival + DE as the
problem-calibration benchmark. First separate verified event/mirror conditions
inside the likelihood; then test calibration under changes in field composition.
Member carry-over precedes more elaborate dynamics. Distinguish observed contest
performance, current team strength, and problem difficulty under stated conditions.

**Fresh evidence** (`scripts/rating_rethink_audit.py`, read-only; saved JSON in
`output/rating_rethink_audit.json`):

- Joint data: 262 contests, 35,862 identities, 78,201 appearances, 3,185 problem
  appearances, 991,268 cells. There are 122 zero-solve and 106 one-solve problems.
- 11,867 zero-solve rows are dropped in fitted contests; 2,105 have wrong attempts.
  448 contest/identity groups have repeated rows (475 excess rows).
- 232 boards mix `$DEFAULT...` and other IDs. This is an ID-prefix inventory,
  not verified onsite/mirror coverage; official online rounds also use imported
  rows. Participation conditions require explicit source-backed labels.
- Cached-fit CF LOCO: clipped nested DE **225.6073**; survival affine/gym
  **246.6616 / 244.3776**; binary affine/gym **246.7795 / 257.5344**. The same
  185 anchors / 15 contests remain development data. These cached, rounded-fit
  scores are not a fresh raw-fit `arch_b.metric` run.
- Every shipped rounded DE point reproduces exactly. Both raw-fit hashes in
  `problem_calibration.json` are stale, although its feature ranges match the
  current anchors. The audit records actual hashes and flags the mismatch;
  production metadata is unchanged in this research task.
- 1,636 appearances fall outside the anchor field-size range and 453 outside
  the disagreement range (overlapping counts). Clipping is not evidence of
  successful transport to these populations.
- XCPCIO cache: 59 config directories with numeric start/end times, 38 with
  submission logs, 38 distinct run-file hashes. This makes a local timing and
  participation pilot possible after joins/completeness are audited. These are
  directory counts, not a verified count of usable unique contests.

**Fresh imputation check** (`arch_b.predict_eval`, refitted from source):
792,936 training / 198,332 held-out cells, grouped by resolved team/problem.
Binary log loss / Brier / AUC = **0.1994 / 0.0609 / 0.9737**;
survival = **0.2289 / 0.0690 / 0.9684**. This remains retained-row imputation,
not forecasting; the probability win does not by itself replace DE calibration.

**Evaluation changes proposed:** separate completed-contest rating, whole-appearance
prediction, prospective rank prediction and historical performance scorecards.
`dynamic_rating` resolves identity on all data, uses approximate dates, and
uses full-data `b0` in its solve score and member-prior targets. Pair ranking
does not directly use that ruler, but needs the date/identity audit too. The
next forecast test should rebuild identities at each cutoff, use recorded dates
where possible, and avoid target-outcome-derived difficulty rulers. Existing
forecast results remain research evidence, not a new untouched test.

**Missing:** audited mode/exposure/mirror dates for much of the dataset, broad
external ability coverage, fresh confirmation data, canonical task-version
checks, and `data/gym_checkpoints/api_standings.json`. None was invented.

**Reproduce:** `./.venv/bin/python -m scripts.rating_rethink_audit` and
`./.venv/bin/python -m arch_b.predict_eval`. No candidate model, shipped rating,
viewer or external app changed. The new audit asserts DE point reproduction
and serializes only finite results; its output includes input hashes.
Validation: 15 statistics/release-audit tests pass; the audit script compiles,
report links resolve, all recorded input hashes still match, and `git diff
--check` passes.
