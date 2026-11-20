# Root cause of the performance inflation and deflation (2026-10-13, second entry)

**Request.** Find the root cause of the inflation and deflation in the entry
above, and fix it.

**Method: split the gap into its two parts.** For every fitted row (78,201):
- **Rank inversion:** the shipped performance minus the same binary fit's own
  problem-implied rating. That rating is the MLE from the row's solve count on
  the fit's `b`, mapped with the same `to_cf`.
- **Problem calibration:** that MLE minus the shipped DE problem-implied
  rating.
- **Banding:** by team ability, not by performance. Banding by performance
  builds in a regression-to-the-mean stretch.
- **Ranks ruled out:** board ranks agree with the fitted rows. Board rank − 1
  minus the rows ranked above is 0 at the median and 90th percentile in every
  group.

**Root cause 1: merged QOJ boards mix two events played under different
conditions.** This explains (a) the field-size effect and most of (c), the
stretch.
- **What a merged board is.** Most QOJ boards of onsite contests hold three
  populations:
  - the event's own official rows (domjudge ids `$DEFAULT_DAT_PREFIX_*`);
  - UCup teams (`ucup-team*`);
  - individual QOJ accounts.

  171 of the fit's boards are mixed this way. The 2023–2025 EC regional
  boards hold 68–295 UCup rows and 57–591 account rows beside 309–548 onsite
  rows.
- **Mirror entries finish far above the same teams onsite.**
  - On ICPC regional boards, at equal ability, UCup rows solve like teams
    +43 to +86 CF stronger, while onsite rows sit at −43 to +2 (by
    ability band).
  - The same team in both roles (47 teams): as a UCup mirror entry it rates
    **+82** higher by solves than onsite (95% CI +6 to +160).
  - The DE audit's paired online-minus-onsite offset, +102 [+88, +117]
    binary points, is the same effect.
- **Why it inflates and deflates.**
  - Rank-based performance ranked an onsite row against the whole board. The
    mirror entries beat onsite teams more often than their abilities predict,
    so onsite performances were pulled down in proportion to the board's
    mirror share.
  - Large onsite fields have relatively few mirror entries. Wuhan 2025 has
    512 onsite rows and 68 UCup rows; Chengdu 2024 has 309 and 290. That is
    the "big fields read high" pattern.
- **Where it sits.** For the same-team field-size slope (onsite result placed
  on the QOJ board, 2,616 pairs, 440- vs 300-team field, by band
  < 2500 / 2500–2800 / 2800+):

  | part | slope |
  |---|---|
  | performance − own MLE | −1 / +26 / +60 |
  | own MLE − DE | 0 / +7 / +2 |

  Within the fit's own rows, a board-size effect is absent (−4 / +8 / −8 for
  a 1,000- vs 400-row board). The effect comes from the population mix, not
  from board size.
- **Ranking onsite results against the onsite rows removes it.**

  | rivals | same-team slope | gold line − consensus vs log field |
  |---|---|---|
  | whole board | −0 / +23 / +65 | r +0.55 |
  | onsite rows | −20 / −23 / +3 | r −0.12 |

  - Adding the UCup rows back restores it (+57); the solo accounts alone give
    +47.
  - Against the rating-free referees (17 regionals): reliability
    0.84 → 0.89, r with CCPC 0.80 → 0.86, r with online 0.79 → 0.82.
  - Treating mirror rivals as δ stronger does not work. With every row kept,
    δ = +150 still leaves r +0.34 and a slope of +42. The mirror advantage
    grows with strength, so a constant shift cannot absorb it.
- **The problem side carries the same contamination.** With event-field
  performance, the top onsite teams read above the problem-implied rating
  from whole-board difficulties. At ICPC regionals by ability band:
  −10 / +25 / +54 / +81 / +109.
  - Refit each merged board's problem difficulties on the event's own rows,
    with abilities fixed. The gap becomes flat: +29 / +22 / +24 / +35 /
    +45. CCPC: +9 / +14 / +11 / +37 / +46.
  - The remaining ~+25 is the uniform rank-vs-solves offset seen at every
    contest type.
  - So inside the event's field, rank and solves agree. The whole-board
    difficulties are pulled down by mirror entries, who solve the hard
    problems more easily.

**Root cause 2: the EC-Final (−73) and online-round (+89) offsets are in the
DE problem ratings, not in performance.**
- **Performance agrees with the fit's own problem ratings at every contest
  type.** Performance minus own MLE (median): regionals +22, CCPC +25,
  EC-Final +15, online rounds +21.
- **The gap is own MLE − DE:** EC-Final −104, online rounds +61, regionals
  −15.
- **DE minus the binary fit's own map, per problem (median):** EC-Final
  **+127**, online −39, regionals +2, CCPC −26.
- **DE terms** (ridge coefficient per SD: survival−binary disagreement +251,
  solve rate +227, conditional SE −87, log field size −34, raw b +53):
  - **EC-Final:** the survival affine puts EC-Final problems 84 above the
    regional level relative to the binary map (+33 vs −51). The survival fit
    reads its timing differently. The disagreement term adds +51 (+234 vs
    +183).
  - **Online rounds:** the solve-rate term pulls their problems 73 lower
    (−204 vs −131), because huge weak fields have low solve rates.
  - **Field size:** the anchors span 78–324 teams, so the term is clipped
    for 97–100% of EC problems.
- **Not fixed here.** DE is the shipped problem calibration, chosen by its
  own anchor audit. Its contest-type shifts come from field-dependent
  features (solve rate) and survival timing. No anchor is an EC-Final or
  an online round, so DE extrapolates there.
  - **Next step:** re-audit DE with field-independent features, or with an
    online/onsite offset in the fit.
  - The fix below leaves (b) as it was: official rows read EC-Final −94 and
    online +90.

**Fix (shipped): rank an official row within its own event.**
- **`arch_a.load`:** `Dataset.official_of_row` flags rows with a
  `$DEFAULT...` (domjudge) id: the event's own standings.
- **`export_virtual_calc`:**
  - `event_field(official)` returns the official rows when a board also holds
    mirror rows and the official field has at least `MIN_EVENT_FIELD` = 30
    rows; otherwise every row. Below 30, a rank measures little: eq. perf
    pins first and last place to the bounds.
  - `performance_fit` re-ranks those official rows within that field
    (`_rank_official_within_event`, the same bisection). Mirror rows keep the
    whole board, and so does a virtual entry in the calculator: both are
    online mirror entries.
  - 51,400 of 78,201 row performances change.
- **`contest_quality.performance`** places onsite results within the same
  field.
- **Tests:**
  - `test_official_rows_of_a_merged_board_are_ranked_within_their_event`;
  - `test_an_event_below_the_minimum_field_keeps_the_whole_board`;
  - `test_performance_ranks_an_onsite_result_among_the_boards_onsite_rows`.
    The old placement code fails it (2693 vs 2778).
- **Not changed:**
  - the joint fit (θ, b);
  - the shipped DE problem ratings;
  - the medal bars and badges (survival fit);
  - `export_viewer` (survival viewer);
  - performance of mirror rows and virtual entries.

**Effect.**
- **`medal_badges.json`:** only `performance_cf` of the cutoff teams moves
  (82 of 84). Gold median **+66**, silver +36, bronze +19, range −61 to +193.
  Bars and badges are identical.
- **Gold lines** (`contest_quality`):

  | set | before | after |
  |---|---|---|
  | ICPC 2023 | 2529–2775 | **2614–2848** |
  | ICPC 2024 | 2598–2779 | **2687–2844** |
  | ICPC 2025 | 2499–2799 | **2643–2826** |
  | CCPC 2024 | 2765–2811 | **2816–2868** |
  | CCPC 2025 | 2780–2808 | **2852–2867** |

  - Mirror check (same teams, CCPC line minus ICPC line): +9 → **−8**, bands
    −43 to +33.
  - CCPC gold still sits at the level of the hardest regionals.
- **`online_gold` fit − online, on the line** (by regional):

  | regional | before | after |
  |---|---|---|
  | Wuhan 2025 | +108 | **+9** |
  | Kunming 2024 | +81 | +33 |
  | Nanjing 2024 | −64 | +9 |
  | Shenyang 2025 | −40 | +14 |
  | Shanghai 2025 | +24 | +33 |
  | Xi'an 2025 | +4 | −53 |
  | Hefei 2023 | −91 | −78 |
  | Xi'an 2023 | −166 | −157 |

  - RMS 67 → 51 CF; the SD of the line is 84 → 60.
  - Within season, over 16 regionals (without Xi'an 2023): r 0.80 → 0.81,
    Spearman 0.71 → 0.72.
  - With Xi'an 2023 (17 regionals) r drops 0.72 → 0.64. That one regional
    causes all of the drop.
  - **Xi'an 2023 is unresolved.** It is an invitational site with about half
    its seats quota, and it has no CCPC referee.
- **The CCPC Jinan 2025 targets of 2026-10-11 hold.**
  - Medians over the 18 mainland 2023–2025 regionals: gold line 2682 → 2779,
    rank-75 line 2445 → 2479.
  - The onsite rank on CCPC Jinan whose placed performance reaches them moves
    only 38 → 35 (gold) and 73 → 70 (rank 75). Lines and placements move
    together.
  - The virtual run's onsite-equivalent rank (95) is rank-based and
    unchanged: at the EC-Final line, below gold.
- **Calculator semantics.**
  - An official row now shows its performance within its event. A virtual
    entry is ranked on the whole board, like the mirror rows.
  - The same scoreline therefore reads up to ~100 lower as a virtual entry.
    This matches the measured mirror advantage.
  - The app copy in `../my-react-app` is not updated here. Re-run
    `scripts/export_contest_fields.py` there and copy
    `output/medal_viewer.html`, as on 2026-10-04.

Regenerated: `medal_badges.json`, `medal_viewer.html`, `virtual_calc.html`,
`contest_quality.{md,json}` and `online_gold.{md,json}` (the 2026 gold
probabilities are unchanged). Scratch scripts are not kept. Rebuild the
decomposition from `estimate_joint(fit_fn=model.fit)`, `_cf_map`,
`_performance_ratings` and `problem_cf`. Rebuild the population labels from
the standings' `team_id`.

## App sync (2026-10-13 follow-up)

Request: apply the fix to the app's Medals page, Contests page and
performances (`../my-react-app`, commit `d3cd4a7`).
- **`export_virtual_calc`:** each team in `virtual_calc.html`'s DATA carries
  `"event": true` when its performance is ranked within its event
  (`_event_participations`). This covers 47,761 rows in 203 of 243 contests.
  Test: `test_only_official_rows_of_a_merged_board_are_flagged_as_event_rows`.
- **`medal_viewer_template.html`:** the lowest-gold caption now says
  performance is ranked among the contest's official teams, and why.
- **In the app:**
  - The re-exported `contest_fields` rows carry the flag.
  - An official result on an event row shows its rank among the official
    teams ("Rank 14 of 358 official teams", Nanjing 2024).
  - A missing official row is inserted among the official teams.
  - Virtual results still use the whole board and are unchanged.
- **Checked in node over every contest against the old app code:**
  - virtual results and official results outside event fields are unchanged;
  - official event rows reproduce the analyzer's values.
- **Checked on a local dev server** (throwaway account, temporary database
  deleted). The app's DETAILS.md has the rest.
