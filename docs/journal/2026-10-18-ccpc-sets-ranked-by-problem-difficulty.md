# CCPC sets ranked by problem difficulty (2026-10-18)

**Request.** Rank the CCPC contests by problem difficulty (for example, by
the number of problems rated ≤ 2400), show the ranking only, without stats
or spoilers, and say whether each is harder than a regional at bronze,
silver and gold. Script `scripts/ccpc_difficulty_rank.py`; report
`output/ccpc_difficulty_rank.md` (ranks and verdicts only); tests
`tests/test_ccpc_difficulty_rank.py` (4 pass).

**Sets.** The 9 CCPC contests with a full problem list in the fit (shipped
DE ratings, `output/problem_ratings_calibrated.json`):
- 2024 stations Harbin 1817, Jinan 1843, Zhengzhou 1873; 2025 stations
  Zhengzhou 2661, Jinan 2693, Chongqing 3387 (all UCup mirrors);
- the 10th Final 2036 (UCup "Guangzhou", May 2025) and the 11th Final 3727
  (UCup "Nanyang", April 2026); both editorials are titled CCPC Final;
- the 2017 Qinhuangdao station 1807 (UCup S3, identified 2026-10-10).
- **Missing:** 10th Chongqing (QOJ 1840, not in the data), 11th Harbin
  (2575, one problem), all 8th–9th (2022–2023) stations, the 2026
  invitationals and the 12th CCPC (Changchun is on 10-18). QOJ 3588
  "Shenzhen" (UCup S4) has no editorial and no identification, so it is left
  out. QOJ 1894 / 3295 ("China") are EC-Finals, not CCPC.

**Rank.** Problems rated ≤ 2400 CF, fewer = harder. Ties go to the set where
a 2400-rated team expects fewer solves (CF formula on the same ratings).
- Ranking by the median problem instead swaps only ranks 2 and 3. Ranks 4
  and 5 are nearly tied on the tie-break.

**Two verdicts per tier**, against the 18 mainland ICPC regionals of
2023–2025. "harder" / "easier" means above / below the middle half of the
regionals' own values; otherwise "same".
- **Medal.** The last bronze / silver / gold medallist's performance, placed
  among the board's onsite rows (`contest_quality.performance`; silver added
  here as rank gold + silver). Field and problems together.
  - Regional medians: gold 2779, silver 2417, bronze 2040 (IQR 2736–2799,
    2393–2428, 2018–2064).
  - **All six stations are harder at every tier.** Every line is above the
    regionals' upper quartile, and above at least 16 of the 18 regionals.
    This agrees with the rating-free linked-team result of 2026-10-12: a
    CCPC medal is about one notch harder at every tier.
  - n/a for the two finals and 2017. They have no onsite XCPCIO board in the
    pipeline, and the CCPC Final medal rule is not recorded here. The 2017
    teams also appear in no other fitted contest.
- **Problems.** At each tier's median regional line, the rating a team needs
  on this set to expect the median regional set's solves, minus the line.
  The problem side alone, no field.

**Result** (rank 1 = hardest):

| rank | contest | medal harder? B / S / G | problems harder? B / S / G |
|---|---|---|---|
| 1 | 11th CCPC Final (Apr 2026) | n/a | harder / harder / harder |
| 2 | 10th CCPC Final (May 2025) | n/a | harder / harder / harder |
| 3 | 11th Zhengzhou (2025) | harder ×3 | harder / harder / harder |
| 4 | 11th Jinan (2025) | harder ×3 | harder / harder / harder |
| 5 | 10th Zhengzhou (2024) | harder ×3 | harder / harder / harder |
| 6 | 10th Jinan (2024) | harder ×3 | same / same / same |
| 7 | 11th Chongqing (2025) | harder ×3 | easier / same / same |
| 8 | 10th Harbin (2024) | harder ×3 | easier / easier / easier |
| 9 | CCPC 2017 Qinhuangdao | n/a | easier / easier / easier |

- **Reading it.** A CCPC medal is harder than a regional medal even where the
  problems are not harder (Jinan 2024, Chongqing 2025, Harbin 2024). There,
  the stronger field makes the medal harder.
- **Caveats.**
  - The CCPC ratings come from the mirrors. The 2026-10-12 problem-implied
    check found them on the onsite scale (+23).
  - The problem verdicts use DE ratings, which carry contest-type offsets
    (2026-10-13): DE minus the binary fit is −26 per problem on CCPC
    mirrors and +2 at regionals. Shifting the CCPC sets up by 28 changes
    one verdict: Chongqing 2025 at bronze goes from a marginal "easier" to
    "same". The medal verdicts use the joint fit, not DE.

Run (~15 s once the boards are cached; on Windows set `PYTHONUTF8=1`):
`python scripts/ccpc_difficulty_rank.py`. Tests:
`python -m unittest tests.test_ccpc_difficulty_rank`.

## 2022–2023 stations added, rated from the onsite boards (2026-10-18 follow-up)

**Request.** Easy CCPC sets are needed. Add the 2022–2023 stations (8th–9th
CCPC) to the ranking, without changing the existing ratings.

**No QOJ fetch.** QOJ shows contest pages only when logged in.
`QOJ_USERNAME` / `QOJ_PASSWORD` are not set, and the browser pane is not
signed in. The onsite XCPCIO boards of all 16 CCPC stations of 2022–2025
were already cached (used by `ccpc_icpc_medals` and `contest_quality`), so
those are used instead. This also covers 10th Chongqing and 11th Harbin,
which were missing before. So 10 stations are added (`ONSITE`); the table
now has 19 sets.

**Method** (`scripts/ccpc_difficulty_rank.py`):
- **Abilities.** Each onsite team (official, ≥ 1 solve) is linked to a fitted
  team by the fit's own identity rule: rosters sharing two members are one
  team (`member_pairs`, `link`; ties dropped). Coverage: 91–96% on the 10 new
  boards; ~100% on boards already in the fit. Xi'an 2023 lists no members,
  so it is skipped.
- **Problem ratings.** For each problem, the MAP difficulty with the linked
  teams' abilities held fixed: the fit's Rasch model and its 2000 / 400 prior
  (`fixed_difficulty`, bisection). It is then mapped to CF with the fit's
  `to_cf`.
- **Onto the shipped scale.** A linear map, shipped DE ≈ 229 + 0.898 × onsite,
  is fitted on the boards that have both: the 17 reference regionals with
  members plus the 6 rated stations. Problems solved by none or all linked
  teams are left out. Over 239 problems, r = 0.982 and the residual SD is
  109.
- **Medal lines.** The last medallist's performance, ranked among the board's
  linked onsite teams (`onsite_lines`). It is compared with the 17 regionals
  measured the same way. The 9 sets of the first entry keep their
  QOJ-placement verdicts.
- `contest_quality.performance` gained `fit=` so the joint fit runs once.

**Held-out check (scratch).** The joint fit was rerun without the six rated
stations' cells (`model.fit(obs=…)`). The six were then rated from their
onsite boards with those held-out abilities and an ICPC-only map
(150 + 0.929 ×), and compared with the shipped ratings:
- per problem: mean −20, SD 138; per set, mean offsets −70 … +5;
- problems ≤ 2400: the same count for 5 of 6 (one off by 1);
- a 2400-rated team's expected solves: within ±0.22;
- the same difficulty order of the six.

So the method reads slightly easy (~20) and ranks sets well.

**Medal measure check.** On the 23 boards with both measures, onsite minus
QOJ placement is +25 at gold (SD 29), +11 at silver (31) and +7 at bronze
(31), with r 0.87 / 0.78 / 0.73. The largest gaps are Hefei 2023 (+129 …
+152) and Xi'an 2025 (+32 … +68), not investigated. Under the onsite measure,
the existing stations stay "harder" except at bronze: 10th Harbin and 11th
Zhengzhou become "same". Bronze verdicts near the edge depend on the measure.

**Result** (rank 1 = hardest; * = rated from the onsite board):

| rank | contest | medal harder? B / S / G | problems harder? B / S / G |
|---|---|---|---|
| 1 | 11th CCPC Final (Apr 2026) | n/a | harder / harder / harder |
| 2 | 10th CCPC Final (May 2025) | n/a | harder / harder / harder |
| 3 | 8th Guangzhou (2022) * | harder ×3 | harder / harder / harder |
| 4 | 11th Zhengzhou (2025) | harder ×3 | harder / harder / harder |
| 5 | 11th Jinan (2025) | harder ×3 | harder / harder / harder |
| 6 | 10th Zhengzhou (2024) | harder ×3 | harder / harder / harder |
| 7 | 8th Guilin (2022) * | harder ×3 | easier / same / same |
| 8 | 8th Mianyang (2022) * | harder ×3 | easier / same / same |
| 9 | 9th Guilin (2023) * | harder ×3 | harder / harder / same |
| 10 | 9th Harbin (2023) * | harder ×3 | same / harder / harder |
| 11 | 9th Shenzhen (2023) * | harder / harder / same | same / same / same |
| 12 | 10th Jinan (2024) | harder ×3 | same / same / same |
| 13 | 11th Chongqing (2025) | harder ×3 | easier / same / same |
| 14 | 9th Qinhuangdao (2023) * | harder ×3 | easier / same / harder |
| 15 | 10th Harbin (2024) | harder ×3 | easier / easier / easier |
| 16 | 11th Harbin (2025) * | same / same / same | easier / easier / easier |
| 17 | 8th Weihai (2022) * | harder ×3 | easier / easier / easier |
| 18 | 10th Chongqing (2024) * | same / same / harder | easier / easier / easier |
| 19 | CCPC 2017 Qinhuangdao | n/a | easier / easier / easier |

- **Easy sets** (problems easier at every tier): 10th Chongqing, 8th Weihai,
  11th Harbin, 10th Harbin and the 2017 set.
  - 10th Chongqing and 8th Weihai are easier by far more than the method's
    held-out error.
  - 11th Harbin's "easier" at gold is within it.
  - 11th Harbin and 10th Chongqing are also the only stations whose medals
    are no harder than a regional's.
- The 9 sets of the first entry keep their order and verdicts.
- **Caveats.**
  - Abilities are constant over time in the fit, so a 2022–2023 team is
    rated partly on its later seasons. The 2022–2023 medal lines read above
    the 2024–2025 ones, most at bronze, which may partly be this drift.
    Measured the same way, the 9th CCPC lines are still above the 2023
    regionals'.
  - The onsite method reads ~20 easy (held-out check).

**QOJ ids.** The only one confirmed is 9th Qinhuangdao = QOJ 1411 (UCup S2
stage 9). It was found by web search, because QOJ pages need a login.
- QOJ 1244 is the 8th CCPC Final (UCup S1 stage 17 "Guangzhou"), not the
  Guangzhou station.
- The Universal Cup site lists 9th Guilin, 9th Harbin and 9th Shenzhen as
  UCup S2 stages 8, 10 and 25. Their QOJ ids are not mapped. No 2022
  station was found as a UCup stage.
- The candidates 1833, 1493, 1303, 1480, 1412, 1404, 1540 and 1596
  (2026-10-10) remain unmapped. The report links QOJ's CCPC categories
  (205; 2023: 275).

Run: `python scripts/ccpc_difficulty_rank.py` (~1 min; on Windows set
`PYTHONUTF8=1`). Tests: `python -m unittest tests.test_ccpc_difficulty_rank`
(8 pass).
