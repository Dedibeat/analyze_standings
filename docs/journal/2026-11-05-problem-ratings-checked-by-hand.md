# Problem ratings checked by hand (2026-11-05, fourth entry)

**Request.** Debug problem ratings by hand, from statements, editorials and
solutions. EC and UCup-EC boards first, then the CF anchors with the largest
errors and the largest DE vs hierarchical gaps. Report:
`problem_rating_audit.md`; script `scripts/problem_rating_audit.py` (~3 min);
output `output/problem_rating_audit.json`. CF mirror solve counts were fetched
from the CF API on 2026-11-05 into `data/cf_mirror_solves.json`. Research
only; nothing shipped changed.

**Hand panel.** 72 problems, rated on the CF scale (about ±200, ±100 for
sign-ins), written after seeing the model numbers:
- 18 EC sign-ins;
- 2025 EC Online I+II (22);
- 2023 Nanjing (13);
- Mid-Atlantic 2024 (11, a weak field);
- the EUC 2025 easy end (5, a strong field);
- 3 CF anchors.

| Group | DE bias / RMSE | hierarchical | hierarchical, skipped cells missing |
|---|---|---|---|
| EC sign-ins | +209 / 273 | +387 / 448 | +71 / 185 |
| 2025 EC online | +118 / 168 | +3 / 115 | −31 / 140 |
| 2023 Nanjing | +185 / 223 | +153 / 177 | +119 / 201 |
| Mid-Atlantic 2024 | +469 / 536 | +315 / 369 | +287 / 337 |
| EUC 2025 easy | −171 / 207 | −257 / 290 | −221 / 249 |
| all 72 | +182 / 288 | +160 / 296 | +64 / 212 |

**Findings.**
- **The middle is sound.** Between 5% and 95% solved, the two models differ by
  under 70 on EC boards and match the hand ratings within error. The
  "EC online ~140 easier" gap is a tail effect: −347 below 0.5% solved, −23 at
  30–70%.
- **Sign-ins are inflated.** Zero-solve rows are dropped, so a sign-in's
  "failures" are a few non-zero rows that never submitted to it:
  - Shenyang 2022 D: 7 rows, 0 attempts;
  - EC-Final 2022 M: 13 rows, 0 attempts;
  - these are QOJ/UCup mirror accounts that tried one or two other problems
    (one is `tarjen`).

  Diagnostic: cells with no submission on a problem more of the board solved
  than the row's hardest solve are treated as missing (19,201 cells, 1.9%;
  12,583 rows).
  - sign-in bias +387 → +71;
  - anchor in-sample RMSE 225.7 → 224.9;
  - but it overcorrects some easy problems (2025 EC Online II D 1213 vs hand
    1650).

  A diagnosis only; any rule must pass the full `hier_binary` protocol.
- **EC online, hard tail.** DE goes far beyond the CF scale: 3600–4000 for 1–3
  solves. The hand panel sides with the hierarchical fit here.
- **Board flag.** 2026 EC Online (I) E "LCM Permutation" was solved only by the
  rank-963 team (5 solves) at minute 207: either a guessable pattern or a
  leak.
- **CF anchors.**
  - **Uniform Chemistry** (SWERC 2022 B / CF 1776K, CF 3200): about 2000 by
    hand (a hitting-time DP). Onsite 78/157 solved it, the first at 14 min; on
    the CF mirror only 222, fewer than a CF 3000 problem. It is 16% of both
    models' squared error. LOCO without it: DE 206.4, hierarchical 211.3
    (with it: 225.6 / 229.5).
  - **Venue-order conflicts:** Urban Planning, Palindromic Parentheses, Grid
    Game 3-angle.
  - **Top-end labels out of line with CF's own solve counts:** Deformed
    Balance CF 2900 with the fewest CF solvers on its board; Symmetric
    Boundary CF 2800 vs 3500 for problems with the same solve counts.
  - **Floor labels:** Bento Box 1300 vs 800 by hand.
  - **EUC 2025 easy problems:** the CF labels are right by hand, and both
    models are ~300 low (strong-board floor).
- **Mid-range DE vs hierarchical gaps.**
  - Weak NA fields: the hand ratings favour the hierarchical fit (Perfect
    Squares, by hand ~1850: DE 2905, hierarchical 2618).
  - Strong invitation boards (THUPC 2022, UCup Finals) read 230–365 harder in
    the hierarchical fit. Not checkable: no statements in the repo.

**Missing (not guessed):**
- the 2026 EC online statements (QOJ needs a login; no editorial found online);
- statements or problem names for the 2020–2021 EC boards and for
  THUPC / UCup Finals / Petrozavodsk;
- `output/problem_ratings.json` lacks names for the 2026 EC online rounds,
  although `data/tagged.json` has them.

**Next.**
1. Test a narrow skipped-cell rule (partial or mirror rows only) in the full
   `hier_binary` protocol.
2. Get the 2026 EC online statements.
3. Report the anchor RMSE with and without Uniform Chemistry.
