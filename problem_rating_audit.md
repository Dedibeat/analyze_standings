# Problem ratings checked by hand

2026-11-05. **Request:** debug the problem ratings by hand, from the statements,
editorials and solutions rather than from the fit. EC and UCup-EC boards come
first, then the CF anchors with the largest errors, then the problems where DE
and the hierarchical binary fit (`hier_binary_report.md`) disagree most.
Research only: no shipped rating, export or viewer changed.

Code: `scripts/problem_rating_audit.py`. Output: `output/problem_rating_audit.json`.
CF mirror solve counts were fetched from the CF API on 2026-11-05 into
`data/cf_mirror_solves.json`.

## How the hand ratings were made, and how far to trust them

- **Method.** For each problem I read the statement (`data/tagged.json` holds
  the PDF text), worked out the intended solution, and gave a CF-scale rating.
  I also looked at who solved it and when.
- **Panel.** 72 problems:
  - 18 EC sign-in problems;
  - all of 2025 EC Online (I) and (II) (22 problems; the two zero-solve problems
    are left out);
  - all of 2023 Nanjing (13);
  - Mid-Atlantic USA 2024 (11), a weak field;
  - the easy end of EUC 2025 (5), a strong field;
  - 3 CF anchors.
- **Precision.** Each rating is one reviewer's judgment, accurate to roughly
  ±200, or about ±100 for sign-in problems. They were written after seeing the
  models' numbers. Treat them as a sanity panel, not labels. Only gaps well
  beyond ±200 count as findings.

| Panel group | n | DE bias / RMSE | hierarchical | hierarchical, skipped cells missing |
|---|---|---|---|---|
| EC sign-in problems | 18 | +209 / 273 | **+387 / 448** | +71 / 185 |
| 2025 EC Online I + II | 22 | +118 / 168 | **+3 / 115** | −31 / 140 |
| 2023 Nanjing (onsite + UCup mirror) | 13 | +185 / 223 | +153 / 177 | +119 / 201 |
| Mid-Atlantic USA 2024 (weak field) | 11 | **+469 / 536** | +315 / 369 | +287 / 337 |
| EUC 2025 easy end (strong field) | 5 | −171 / 207 | −257 / 290 | −221 / 249 |
| all 72 | 72 | +182 / 288 | +160 / 296 | +64 / 212 |

"DE" here is the shipped full-data rating; "hierarchical" is the selected
`hier_binary` fit on the same affine map. The last column is the diagnostic
fit described under finding 1.

## EC and UCup-EC boards

The two models agree in the middle and part in the tails. Mean hierarchical −
DE by solve rate, over 689 EC problems:

| Board | <0.5% | 0.5–5% | 5–30% | 30–70% | 70–95% | >95% |
|---|---|---|---|---|---|---|
| EC online | −347 | −217 | −47 | −23 | −68 | +24 |
| EC regional / UCup-EC | −129 | −118 | −10 | +3 | −16 | **+141** |
| EC-Final / UCup Finals | +93 | −6 | +92 | +89 | +88 | +257 |

The "EC online rounds read ~140 easier" gap in `hier_binary_report.md` is
therefore a tail effect, not a level shift. Between 5% and 95% solved, the two
models differ by under 70 on average.

### 1. EC sign-in problems: inflated by skipped cells (both models; hierarchical worst)

By hand, these are CF 800–1200 problems:
- 2022 Shenyang D, count T vs D: DE 858, hierarchical 1203;
- 2023 Hefei F, majority string: 1118 / 1431;
- 2022 Nanjing I, n − max letter count: 1087 / 1352;
- 2023 Jinan D: 1281 / 1492;
- 2025 Nanjing (UCup) C: 1198 / 1433;
- 2022 EC-Final M: 1327 / 1608.

The hierarchical fit is +387 high on the 18 sign-ins and DE +209.

**Cause, from the boards.**
- Zero-solve rows are dropped, as in every fit. A sign-in solved by 99% of its
  board is then "failed" only by a handful of non-zero rows.
- Those rows almost never submitted to the problem.
  - Shenyang 2022 D: 7 such rows, 0 attempts.
  - EC-Final 2022 M: 13 rows, 0 attempts.
- They are QOJ/UCup mirror accounts that submitted one or two other problems.
  One of them is a well-known strong individual (`tarjen`).
- The binary likelihood counts each skipped cell as a failed attempt by a
  capable solver. That makes the trivial problem look hard. The hierarchical
  fit trusts linked abilities more, so it inflates most.

**Diagnostic fit.** A cell counts as *skipped* when:
- the row made no submission to the problem;
- more of the board solved that problem than solved the row's own hardest
  solved problem.

That covers 19,201 cells (1.9%) in 12,583 rows. Refitting the selected
hierarchical setting with skipped cells treated as missing gives:
- sign-in bias +387 → **+71**; whole panel 296 → **212** RMSE;
- in-sample anchor RMSE unchanged (225.7 → 224.9); map 0.867 b + 618.

It overcorrects some easy problems, though:
- 2025 EC Online II D: 1213 vs hand 1650;
- 2023 Nanjing I: 1026 vs 1400;
- 2025 Xi'an G: 884 vs 1100.

So the rule is a diagnosis, not a fix. A narrower rule (only partial or mirror
rows) still has to be judged by the full `hier_binary` protocol: LOCO,
held-out team appearances and stability. It must not ship from this panel.

### 2. EC online middle: both fine; DE runs high in the hard tail

- **2025 EC Online I and II, mid-range.** From 5% to 95% solved, every problem
  is within ~150 of the hand rating in both models. Examples (hand / DE /
  hierarchical):
  - Teleporter 2050 / 2067 / 2072;
  - Tree Shuffling 2100 / 2137 / 2137;
  - Reconstruct the tree 2500 / 2597 / 2548.
- **Hard tail.** DE goes far past the CF scale:
  - cover 3780, Square Permutation II 3579, Square Permutation I 3992 (0
    solves), tetrart 3964 (0 solves);
  - the hierarchical values are 3440, 3275, 3771 and 3722.
- **Hand view of the tail.** Problems that 3–25 of the ~20 elite teams solve
  sit at CF 3100–3400. On the online panel, hierarchical is +3 / 115 and DE
  +118 / 168.
- **Zero-solve problems** have no information in either model. Their ratings
  (3700–4000) are prior extrapolation.

### 3. Hard tail at onsite regionals: not decidable by hand

At ≤5% solved, DE is 100–300 above the hierarchical fit. 2023 Nanjing B, J, H
and E, by hand 3000–3400, read DE 3267–3739 and hierarchical 3173–3623. Both
are high, and the gap is inside my error. The 2020–2021 EC boards carry no
problem names or statements in the repo, so they could not be checked.

### 4. Board-data flags

- **2026 EC Online (I) E, "LCM Permutation".** The only solver is the rank-963
  team, with 5 solves in total, at minute 207. None of the 960 teams above it
  solved the problem.
  - This is either an easily guessed pattern or a leak.
  - The statement is behind a QOJ login, and no editorial was found online.
    **Missing: the 2026 EC online statements** (QOJ login or the problem PDF).
  - Its rating (DE 3872, hierarchical 3480) is unreliable either way.
- **Other weak solvers.** 2023 EC Online (I) C was solved by the rank-42 and
  rank-86 teams (8 solves each). 2024 EC Online (II) B was solved by the rank-76
  team. Both are plausible, but they pull those problems down in the
  hierarchical fit.
- **Missing names.** `output/problem_ratings.json` has no problem names for the
  2026 EC online rounds, though `data/tagged.json` has them. That export
  predates the names.

## CF anchors with the largest errors

1. **Uniform Chemistry (SWERC 2022 B, CF 1776K, CF 3200).**
   - Models: DE 1945, hierarchical 1966 (LOCO).
   - By hand it is a first-hitting-time DP with n ≤ 100, about **2000**.
   - The board agrees: 78 of 157 solved, the first at 14 minutes. That is more
     than Another Wine Tasting Event (CF 2100, 54 solved).
   - On the CF mirror, where it was the 11th problem, 222 accounts solved it,
     fewer than Parmigiana With Seafood (546, CF 3000).
   - Its letter is genuinely B in the official statement, so this is not a
     labelling bug. The CF label measures a different audience.
   - **This one anchor is 16% of both models' squared error.** Without it, LOCO
     is DE 206.4 vs hierarchical 211.3 (225.6 / 229.5 with it). The ranking does
     not change.
2. **Venue-order conflicts.** Three more problems are much easier onsite than
   their CF solve order implies:
   - Urban Planning (EUC 2025 B, CF 3100, 80% solved onsite);
   - Palindromic Parentheses (Jakarta 2023 L);
   - Grid Game 3-angle (Jakarta 2024 F).

   No board-based rating can match those labels. By hand, Urban Planning is
   ~2700, so the label is high and the models (2300) are low.
3. **CF labels out of line with CF's own solve counts.**
   - **Deformed Balance** (APAC 2026 M): CF 2900, but the fewest CF solvers on
     its board (65). The models give 3351–3398.
   - **Symmetric Boundary** (APAC 2024 I): CF 2800 with 92 CF solvers. Problems
     with 88–107 solvers on that board are labelled 3500. No onsite solves;
     the models give 3532–3576.

   In both cases the label, not the model, is the outlier. On APAC 2025, Hold
   the Star (CF 3500, 14 onsite solves) and Cactus Connectivity (CF 2700, 12
   onsite solves) have nearly the same boards. CF labels near the top carry
   ±400 of noise.
4. **Floors.**
   - **The Bento Box Adventure** (Taiwan A, CF 1300): find the missing number
     of 1..5, so 800 by hand. The CF label is +500; DE (634, LOCO) is below
     the floor; hierarchical gives 1020.
   - **Expansion Plan 2** (SWERC 2025 E, CF 900): a Minkowski-shape check with
     prefix counts, ~1400 by hand. The models' ~1500 is closer than the label.
5. **Strong field under-rated.** EUC 2025's easy problems (Mascot Naming, Wine
   Tasting, Ads: CF 1900–2100) are about right by hand. Both models put them
   ~300 lower:
   - DE −171 on the panel group, hierarchical −257;
   - this is the strong-board floor again: the few failures on an elite board
     set the rating.

## Largest DE vs hierarchical gaps (mid-range, 5–95% solved)

- **Weak fields: the hierarchical fit is right.** On Mid-Atlantic USA 2024,
  hand ratings say both models are high and DE far higher:
  - DE +469, hierarchical +315 bias;
  - Perfect Squares, whose statement gives the needed number theory, ~1850 by
    hand: DE 2905, hierarchical 2618;
  - City Bike ~2000: DE 2723, hierarchical 2486.

  This confirms on hand-read problems the weak-field failure of DE seen in
  `field_transport` and `hier_binary` (weak half 451 vs 333 RMSE).
- **Strong invitation boards** (THUPC 2022, 3rd UCup Finals, Petrozavodsk):
  the hierarchical fit reads them 230–365 harder. Their statements are not in
  the repo, so they were not checked. The EC-Final 2022 sign-in (hand 1200,
  hierarchical 1608) is the one checkable case, and DE is closer there.
- **Tiny boards** (Mid-Atlantic and Mid-Central 2022, 5–8 teams): gaps of 230–330
  are noise from 5–8 teams.

## What this means

- **Mid-range ratings (5–95% solved) are sound in both models.** Their
  disagreement is small, and hand checks cannot separate them.
- **Floors are the weakest part of every rating.** A problem solved by almost
  everyone is rated from a handful of failing rows. On EC mirror-merged boards
  those rows are mostly mirror accounts that skipped it. Ignoring skipped
  cells fixes sign-ins but overcorrects some easy problems. A properly
  evaluated rule is the next step.
- **Ceilings above CF 3500 are extrapolation in both models**, and DE's run
  further: 3600–4000 at 1–3 solves.
- **Anchor labels have errors too.** One anchor (Uniform Chemistry) is 16% of
  the anchor MSE. Several top-end labels disagree with CF's own solve counts.
  The anchor RMSE of ~226 includes a label-noise floor; it is not all model
  error.
- **For EC online rounds, the hand panel sides with the hierarchical fit**
  (+3 vs DE's +118 bias). That is the opposite of the worry in
  `hier_binary_report.md`, though only for the 2025 rounds checked.

## Follow-up checks (2026-11-09)

These were done by hand from scratch scripts (not kept) on the full-data
fits. The hand panel is unchanged, so the published scores stay reproducible.

- **2025 EC Online II D "Arcane Behemoths" (2524 D): why the skip rules
  overcorrect.**
  - D is the board's easiest problem: 1,629 of 1,788 non-zero rows solved it.
  - `skip_partial` treats 124 of its 159 failures as missing:
    - 123 of those rows are official registrations (`$DEFAULT…` ids);
    - 86 solved only C and never submitted D.
  - These teams solved C late (median minute 164; for all C solvers, 90).
    D's median solve time, 125, is later than C's, which fits the hand view
    that the two are close (C 1700, D 1650).
  - So the dropped cells are real failures by weak teams, not mirror
    accounts. The rule needs only "more solves than the row's hardest solve",
    and 1,629 > 1,423 qualifies.
  - The official-rows-excluded variant is in `skip_cells_report.md`. It fixes
    D (1458) but fails the sign-in criterion.
- **Strong-board floors (hierarchical only).** Two near sign-ins on strong
  boards read far harder in `base` than in DE. The failing rows are a strong
  board's bottom one-solve teams, so no skip rule touches them:
  - **EC-Final 2021 (1041):**
    - A "DFS Order": min position = depth, max = n − subtree size + 1, about
      CF 1200 by hand. Base 1676, DE 1252.
    - I "Future Coder": count pairs with (a−1)(b−1) < 1, about 1350 by hand.
      Base 1605, DE 1260.
    - The failing rows, the bottom 1-solve official teams, get θ ≈ 1872. The
      board's median θ is 2377: σ = 300 around the board level compresses the
      bottom of a strong board.
  - **THUPC 2022 Final (955) M:** 156 of 157 solved it, base 1768, DE 1000.
    The one failure is an official team that solved only I (67 solves). The
    statement is not in the repo.
  - **Not systematic.** Over all boards, problems solved by more than 95% read
    only +26 to +62 above DE in every tercile of board level. These are
    single cases.
- **Rating-order check.** No board has an inversion in base, `skip_partial`
  or DE: no problem with at least 10% of the field (and 5 rows) more solves
  is rated more than 100 harder.
- **Rare solves by low-ranked rows.** Only four problems on boards of ≥ 100
  rows were solved (1–3 times) only by rows outside the top quarter:
  - 2026 EC Online I E "LCM Permutation". Its lone solver, `id:sg78276397`,
    is an **unofficial** account. It solved F and M at minutes 13/19, E at 208
    after 3 wrong tries, then C and A. That fits a strong mirror account
    better than a leak; still unverifiable without the statement.
  - NWERC 2023 B "Brickwork": rank 60/144, 8 wrong tries;
  - Petrozavodsk W22 D2 K "Fake Plastic Trees 2": rank 53/134;
  - Petrozavodsk W24 D4 C "Comedy’s Not Omnipotent" (2 solves, ranks 29 and 74 of 105).

  None of these looks like a data error.
- **Tiny North American boards (data limitation).** 17 boards have fewer than
  30 non-zero rows. They are mostly NA regionals and the 2022–2025 NAQ, whose
  QOJ copies hold 13–27 rows.
  - Mid-Atlantic 2022 (1119) has 2 standings rows, and only its 5 solved
    problems are listed.
  - Shipped DE publishes ratings for 20 problems from boards with < 5 rows and
    45 from 5–9 rows.
  - Its `difficulty_se` there (median 117, about 150–180 on 1119) understates
    the uncertainty: 1119's five ratings (1836–2244) come from one team's solve
    times.
  - The legacy Architecture A file `output/problem_ratings.json` also lists
    13 contests the fit does not have. Problems on 0–2-row boards there are
    shown as 4000, a placeholder, not a rating.
- **Hand-panel correction (not applied).** 2025 EC Online I B "Creating
  Chaos" (hand 1100; DE 1438, base 1317): its median solve minute is 83,
  against 32 for that round's sign-in G. The contiguous-block insight is not
  sign-in level, so about 1300 is a better hand rating.

  The frozen panel keeps 1100, so the skip tests stay comparable.

## Next steps

1. ~~Evaluate a skipped-cell rule through the full protocol.~~ Done:
   `skip_partial` passes (`skip_cells_report.md`); `skip_mirror` fails the
   sign-in criterion. A margin-based rule would need fresh boards.
2. Get the 2026 EC online statements to check "LCM Permutation" and the rest
   of those rounds.
3. Report the CF RMSE with and without Uniform Chemistry from now on. Do not
   drop it silently: the selection is post hoc.
4. Flag or withhold ratings from boards with < 10 non-zero rows in the shipped
   file, or widen their `difficulty_se` (not done: it changes shipped output).

Reproduce: `PYTHONUTF8=1 ./.venv/Scripts/python -m scripts.problem_rating_audit`,
about 3 minutes. It prints the panel scores; the JSON records input hashes.
