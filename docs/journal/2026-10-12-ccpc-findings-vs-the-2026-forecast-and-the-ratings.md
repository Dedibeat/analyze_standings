# CCPC findings vs the 2026 forecast and the ratings (2026-10-12, third entry)

**Request.** Can the CCPC findings improve the 2026 forecast, or expose
disagreements and weaknesses in the performance and problem ratings?
Contest-level numbers only, as before.

**Bug fixed first: `contest_quality.performance` read the wrong copy of 15 boards.**
- **Cause.** Some contests are in both `tagged.json` and a UCup file. For
  example, Nanjing 2024 (QOJ 1828) has 1,047 rows in `tagged.json` and 559 in
  `ucup_s3.json`; Shenyang 2025 (2641) has 907 and 536.
  - The fit keeps the first copy (`dedupe_contests`), and `row_lookup`
    indexes that copy's rows.
  - `performance` kept the last copy. So on those boards a result was ranked
    against the wrong field, with abilities from mismatched rows.
- **Check.** Placing a row's own result back into its board should return its
  own performance. Before the fix, Nanjing 2024 read +231 and Shenyang 2025
  +187 on average; Jinan 2023 and the CCPC mirrors read 0. After the fix,
  all read 0.
- **Fix.** The function now uses `dedupe_contests`. The regression test is
  `test_performance_places_a_result_in_the_fits_copy_of_a_repeated_contest`;
  it fails on the old code.
- **Boards affected.** Every 2024–2025 ICPC regional and Xi'an 2023. Their
  gold lines drop by 70–290 and their bronze lines by 140–500.
- **Earlier claims retracted.**
  - The "−184 mirror offset" was this bug. Corrected, it is +9.
  - So was "2022–2023 lines sit ~150 lower".
  - Spearman between gold-line performance and the CCPC even odds goes from
    −0.30 to +0.81 (within season).
  - The second entry above is corrected in place.
- **Not affected.** The other loaders already keep the first copy
  (`calibration_audit`, `calibration_experiment`, `cf_prior`). The
  2026-10-11 targets placed results in QOJ 2693, which exists only in UCup.
  Their cutoffs, gold 2712 and rank-75 2456, agree with the corrected gold
  lines (median 2680–2722).

**1. The ratings, checked against rating-free evidence.**
- **The same teams on CCPC mirrors and ICPC boards** (2,363 same-season
  pairs):
  - Rank-based performance: CCPC minus ICPC **+9**.
  - Problem-implied rating: **+23**. This is the rating at which the CF
    formula, applied to the shipped DE ratings of the set's problems,
    gives the row's solve count.
  - Both stay near 0 in every band: problem-implied +45 below 2200 and −20
    above 2800.
  - Per row, performance minus problem-implied is −3 on CCPC and +10 on ICPC.
  - So the team performances and the problem ratings put mirrors and onsite
    boards on one scale, and the two instruments agree on these boards.
- **Gold difficulty per regional, four measures** (16 mainland regionals of
  2023–2025 that have all four):
  - **The measures.** The fit's CF gold bar (`medal_badges.json`); the
    gold-line performance (corrected); the online rank with even odds of gold
    (`online_gold.contest_difficulty`); and the CCPC percentile with even odds.
    The last two use no ratings.
  - **Spearman within a season** (each measure oriented so + = harder):

  | | bar | performance | online | CCPC |
  |---|---|---|---|---|
  | bar | 1 | +0.81 | +0.54 | +0.56 |
  | performance | +0.81 | 1 | +0.74 | +0.81 |
  | online | +0.54 | +0.74 | 1 | +0.80 |
  | CCPC | +0.56 | +0.81 | +0.80 | 1 |

- **Reading it.**
  - The two rating-free measures agree with each other (+0.80).
  - The fit's gold-line performance tracks them nearly as well.
  - The medal bar tracks them least. The bar is a problem threshold: the
    difficulty the gold-cutoff cohort solves at 50%, on the survival fit's gym
    map. Its RMS z-gap from the rating-free consensus is 0.89, against 0.59
    for performance.
- **Where the bar disagrees** (bar z minus the mean of the other three):
  - **Shanghai 2025, −1.68.** Bar 2482, lowish. Online and CCPC put this gold
    among the hardest of 2025, and its performance line is third (2722).
  - **Nanjing 2024, −1.08.** Bar 2437, the lowest of 2024; the other
    measures say average.
  - **Xi'an 2025, +1.45.** The bar is mid; the other three say easiest or
    nearly.
  - **Kunming 2024, +1.31.** Bar 2716, second highest; the rating-free
    measures say average, and performance sits in between.
  - **Three of these four were already flagged** by `online_gold` as the
    largest fit-minus-online gaps (2026-09-27): Kunming 2024 +151, Nanjing
    2024 −118, Shanghai 2025 −90. The CCPC measure confirms them.
  - **The fourth gap flagged then is not confirmed.** For Shenyang 2024
    (+92), CCPC calls it the hardest gold, siding with the bar.
- **Consequence for the 2026 site chooser.**
  - `medal_predict` ranks cities by their historical bars. Its three easiest
    2026 gold cities are Hong Kong, Shanghai and Nanjing (2026-10-05).
  - The Shanghai and Nanjing bars are the two most understated against the
    rating-free evidence. By CCPC even odds, Shanghai's gold was average in
    2024 (0.092) and among the hardest in 2025 (0.070); Nanjing's was
    average in all three years (0.089–0.094).
  - Site difficulty does not repeat by city either. Shenyang went 0.101 →
    0.059 → 0.129, the same finding as the station offsets and
    `online_gold`'s site history.
  - So no history ranks the 2026 sites. The rules-based `online_gold`
    forecast stays the one to use (decision of 2026-09-27).

**2. Correction: CCPC gold is harder than an average ICPC gold.**
- **The benchmark.** The first entry's even odds needed a benchmark for
  regression to the mean, and the second entry compared them with 50%
  instead.
- **ICPC → ICPC** (3,762 ordered pairs, mainland 2023–2025). A team at one
  regional's gold line (percentile 0.101) has a 34% chance of gold at another
  regional. Its even odds sit at 0.070. For rank ≤ 75 they sit at 0.170.
- **CCPC → ICPC.** At the CCPC gold line the chance is 47%, and the even odds
  sit at 0.093. For rank ≤ 75 they sit at 0.228. The CCPC percentile with the
  same 34% is **0.135** (10–90% 0.127–0.142), about rank 35 of 260. That is
  the top of CCPC silver.
- **So CCPC gold is harder than an average ICPC gold.** The first entry's
  "about one notch harder" holds for gold too.
- **Only the hardest regionals reach CCPC gold level.** By linked teams:
  Shenyang 2024, Shanghai 2025 and Chengdu 2025. By performance: Chengdu 2025
  2799, Shenyang 2024 2779 and Wuhan 2025 2774, against CCPC 2765–2811. None
  is clearly harder.
- **Medal tables.** `contest_quality.md` now prints the benchmark
  (`pooled_even_icpc`).

**3. Same-season results as a forecast update** (scratch query, not shipped).
- **Question.** Does a CCPC result from earlier in the season improve
  held-out prediction of gold and of the EC-Final line? This matters for
  2026: all 12th-CCPC stations (Changchun 10-18, Jingzhou 11-08, Leshan
  11-15, Xiamen 11-22) come before Shanghai (12-05), Nanchang (12-19) and
  Hong Kong (2027-01-09).
- **Rows.** 5,703 linked mainland rows from 2023–2025 (`online_gold.model_rows`
  plus `ecfinal_chance` history).
  - **An earlier CCPC** means a linked entry (school + ≥ 2 members) at a
    station whose XCPCIO `start_time` precedes the regional's.
  - **Coverage:** 916 of 1,939 rows in 2024, but only 208 of 2,019 in 2025,
    because the 11th stations ran 11-09 to 11-30.
  - **An earlier ICPC regional** uses the same rule.
- **Model.**
  - **Base:** the shipped features. Gold uses online x plus the quota-adjusted
    rules line; the EC-Final line uses online x plus members' history, at the
    season's real K.
  - **Update:** applied only to teams with an earlier result:
    a + b·logit(percentile) + c·x, fitted with the base logit as an offset.
    Teams without one keep the base prediction.
  - **Why not a plain extra feature?** A plain feature with a has-result flag
    hurt every team in 2025: the flag's meaning shifted when the stations
    moved later.
- **Held-out Δ log loss on the teams with the result** (train on earlier
  seasons; 95% bootstrap):

  | update | 2024 gold | 2024 rank ≤ K | 2025 gold | 2025 rank ≤ K |
  |---|---|---|---|---|
  | earlier CCPC (916 / 208 teams) | −0.016 (−0.036…+0.002) | **−0.021** (−0.041…−0.002) | −0.009 (−0.052…+0.033) | +0.002 (−0.034…+0.042) |
  | earlier ICPC regional (659 / 716) | −0.017 (−0.036…0.000) | **−0.025** (−0.045…−0.006) | −0.007 (−0.020…+0.006) | +0.002 (−0.013…+0.018) |
  | both (1,153 / 761) | **−0.019** (−0.035…−0.003) | **−0.028** (−0.046…−0.010) | −0.008 (−0.022…+0.006) | +0.010 (−0.007…+0.028) |

- **Reading it.**
  - A CCPC result is worth about as much as an earlier ICPC regional.
  - With one, the online-rank slope drops by about 40%: the update's x term
    is −0.7 to −1.0, against 2.0–2.5 in the base.
  - There is a clear gain in 2024 and none in 2025. The 2025 test had few
    teams and wide intervals, and the EC-Final update even leans worse.
  - Not shipped: it helped in one of two test seasons.
- **Side result: members' history in the gold model.** Adding
  `ecfinal_chance`'s h to the gold base gives 2024 −0.0056 (−0.0091…−0.0019)
  and 2025 −0.0011 (−0.0052…+0.0023), over all teams. It is a candidate for
  `online_gold`, untested beyond this.

**4. NUM-R^3 scenario** (same update, fitted on all 2023–2025 rows at
rank ≤ 75; 618 training teams have a CCPC result and an online rank of
#300–600).
- **Online only.** Online #544 / #349 plus members' history gives **10.2%**
  (the shipped multi-K model gives 12.2%).
- **With an onsite CCPC percentile of:**

  | CCPC percentile | P(rank ≤ 75) |
  |---|---|
  | 0.15 | 23.5% |
  | 0.228 | 18.0% |
  | 0.309 (the Jinan virtual's place) | 14.3% |
  | 0.40 | 11.4% |
  | 0.60 | 7.0% |

- **What it means.**
  - Even counted as an onsite result, the Jinan virtual moves the chance from
    ~10% to ~14%, not to the 36% of the CCPC-only model: the online rank
    still carries most of the weight.
  - A real 12th-CCPC finish in the top 15% would roughly double it.
  - This is the only evidence that can arrive before Shanghai, Nanchang and
    Hong Kong.

Scratch scripts are not kept. The rows are rebuilt from
`online_gold.model_rows`, `ecfinal_chance.history`,
`ccpc_icpc_medals.link`/`icpc_pairs` and the XCPCIO `start_time`. Report:
`python scripts/contest_quality.py` (~15 s). Tests:
`python -m unittest tests.test_contest_quality` (7 pass).
