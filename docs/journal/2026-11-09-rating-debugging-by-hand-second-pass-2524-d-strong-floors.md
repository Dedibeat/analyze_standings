# Rating debugging by hand, second pass: 2524 D, strong floors, tiny boards (2026-11-09)

**Request.** Keep debugging by hand: chase why 2025 EC Online II D stays
too easy (`skip_partial` 1211 vs hand 1650), and pursue any other odd rating
or bug. Write-ups: `skip_cells_report.md` (second test) and
`problem_rating_audit.md` ("Follow-up checks"). Code:
- `arch_b/skip_cells.py` gained rule `skip_mirror`;
- its cache names now include the rule list.

Tests: `tests/test_skip_cells.py` (6). Research only; nothing shipped changed.

**2524 D cause.**
- D is the most-solved problem on its board (1,629 of 1,788).
  `skip_partial` dropped 124 of its 159 failures:
  - 123 of those are official `$DEFAULT…` registrations;
  - 86 solved only C, late (median minute 164).
- These are real failures by weak teams. The rule fires because 1,629 is
  greater than C's 1,423 solves. On the sign-ins, by contrast, nearly every
  skipped row is an unofficial `id:` account.

**`skip_mirror`** (pre-registered in the report; `skip_partial` on
non-official rows only):
- 2524 D comes back to 1458, and 2025 EC online hand RMSE is 115 (vs 142).
- It **fails criterion 1**: sign-in bias is +174 (> 150). Official rows skip
  sign-ins too: 1096 D 1094 vs hand 800; 1197 M 1373 vs 1200.
- It passes the other three:
  - CF −2.0 [−5.3, +0.6];
  - log loss −5.7 / −3.4 ×10⁻⁴;
  - drift 7 of 8.
- **`skip_partial` stays preferred.** A margin rule (skipped problem much
  easier than the row's hardest solve) is the untested idea. It needs fresh
  boards: the hand panel has already shaped two rules.

**Correction.**
- `strength_pool` is the drift reference for `strong` and `weak`, so its
  drift is always 0. Criterion 4 should count 8 views, not 9:
  - `skip_partial` 7 of 8 (was "8 of 9");
  - `skip_all` 2 of 8 (was "3 of 9").
- The verdicts do not change.

**Other findings.**
- **Strong-board floors (hierarchical only).**
  - EC-Final 2021 A "DFS Order" (hand ~1200): base 1676, DE 1252.
  - EC-Final 2021 I "Future Coder" (~1350): base 1605, DE 1260.
  - THUPC 2022 Final M (156/157 solved): base 1768, DE 1000.

  The failing rows are a strong board's bottom one-solve teams, held at θ ≈
  1872 by the σ = 300 board prior (the board median is 2377). Over all
  boards, >95%-solved problems read only +26 … +62 above DE, so these are
  single cases.
- **No within-board rating inversions** in base, `skip_partial` or DE.
- **"LCM Permutation"** (2026 EC Online I E): its lone solver is an
  unofficial account. The solve sequence (sign-ins at 13 and 19, E at 208
  after 3 wrong tries) fits a strong mirror account better than a leak.
- **Tiny boards.** 17 boards have < 30 non-zero rows, mostly NA regionals
  and the NAQ (13–27 rows on QOJ). Mid-Atlantic 2022 has 2 rows, with only its
  5 solved problems listed.
  - Shipped DE rates 20 problems from boards with < 5 rows and 45 from 5–9
    rows.
  - Its `difficulty_se`, the raw survival Laplace SE (DE has none), is small
    there (median 117), although one row is no evidence.
  - The legacy Arch A `problem_ratings.json` shows 4000 placeholders for
    problems on 0–2-row boards.
  - Flagging these in the shipped file is proposed, not done.
- **Hand-panel note.** 2025 EC Online I B (hand 1100) is likely ~1300: its
  median solve is minute 83 against 32 for the sign-in. The frozen panel is
  unchanged.

Run (~5 min with 8 workers; recomputes every rule):
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.skip_cells 8`.
