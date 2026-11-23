# ICPC regionals vs CCPC stations: medal difficulty and problem quality (2026-10-12)

**Request.** Are some hard regionals harder than CCPC, and what about problem
quality? No solution spoilers. As before, unseen sets get no problem-level
detail: every number here is per contest (no labels, names, techniques or
per-problem results).

**Data** (`scripts/contest_quality.py` → `output/contest_quality.{md,json}`).
- **Boards.** 44 onsite XCPCIO boards: the 28 ICPC EC regionals of 2022–2025
  and the 16 CCPC stations. Official teams with ≥ 1 solve ("field").
- **Cache.** The ICPC `run.json` files were not cached on this machine. They
  were downloaded into the git-ignored cache.
- **Boards are final.** No board has frozen or pending runs. The 47th ICPC and
  8th CCPC boards report every failure as `REJECTED`, compile errors included.

**1. ICPC medals measured against CCPC (same teams).**
- **Method.** Linked pairs as in the CCPC medal entry above (mainland
  2023–2025). A logistic in logit CCPC percentile, with the pooled slope and
  each regional's own intercept. The result is the CCPC percentile at which a
  team has even odds at that regional; 90% intervals come from the intercept's
  Fisher SE (team clustering ignored, so slightly narrow).
- **Pooled even odds vs the CCPC medal lines (0.10 / 0.30 / 0.60):** ICPC
  gold 0.093, silver or better 0.358, any medal 0.800; rank ≤ 75 at 0.228.
- **CCPC gold is harder than an average ICPC gold** (corrected in the third
  2026-10-12 entry; this bullet first said "about equal", comparing the 47%
  below with 50% instead of with the ICPC benchmark). A team right at the
  CCPC gold line has a 47% chance of ICPC gold. A team right at an ICPC gold
  line has only 34% at another regional (teams regress to the mean); its even
  odds sit at percentile 0.070, not at its own 0.10 line. An average ICPC gold
  line is worth about CCPC percentile 0.135 (rank ~35 of 260, 10–90%
  0.127–0.142), the top of CCPC silver. The entry above ("about one notch
  harder") stands for every tier.
- **Regionals whose gold was about as hard as a CCPC gold** (gold even near
  the 0.070 benchmark):

  | regional | even odds (90%) | ≈ rank at a 260-team station |
  |---|---|---|
  | Shenyang 2024 | 0.059 (0.046–0.076) | 15 |
  | Shanghai 2025 | 0.070 (0.054–0.090) | 18 |
  | Chengdu 2025 | 0.077 (0.061–0.098) | 20 |

  No regional is clearly harder: every interval includes 0.070.
- **Easier golds:** the other 14. Most extreme: Xi'an 2025 0.151
  (0.125–0.181) and Shenyang 2025 0.129 (0.104–0.158). The other 12 sit at
  0.087–0.105.
- **Rank ≤ 75** is hardest at the largest fields: Kunming 2024 0.155, Wuhan
  2025 0.166 and Hangzhou 2023 0.180 (434–444 teams). Easiest are Xi'an 2025
  and Shenyang 2023 at ~0.30, which is the CCPC silver line.
- **Not covered:** Xi'an 2023 (its board lists members for 2 of 418 teams),
  the 2022 season, and Hong Kong / Macau.

**2. Medal lines in CF-equivalent performance.**
- **Method.** The last gold / bronze medallist's (solved, penalty) is placed in
  the contest's QOJ board in the joint fit (`performance_fit`), as the
  virtual calculator does.
- **Corrected** (third 2026-10-12 entry). The first run read 15 boards from
  the wrong copy and overstated their lines by 70–290. The numbers below are
  the corrected ones.
- **ICPC gold lines:**
  - 2024: Shenyang 2779, Kunming 2737, Shanghai 2684, Hangzhou 2682, Hong
    Kong 2622, Chengdu 2615, Nanjing 2598.
  - 2025: Chengdu 2799, Wuhan 2774, Hong Kong 2735, Shanghai 2722, Nanjing
    2688, Xi'an 2567, Shenyang 2499.
  - 2023: 2529–2704 (Macau 2775).
  - Seasons sit at similar levels; median 2680 / 2683 / 2722.
- **CCPC gold lines are higher:** 2765–2811 (2024–2025, the six sets on
  QOJ). Only Chengdu 2025, Shenyang 2024 and Wuhan 2025 reach them. This
  agrees with the linked-team benchmark: CCPC gold is the harder gold.
- **Agreement with the even odds is good** within a season: Spearman +0.81
  over 16 regionals (third entry).

**Mirror check.**
- **Corrected** (third 2026-10-12 entry). The first run reported −184; that
  came from the board bug.
- **Corrected result: no gap.** CCPC sets are in the fit only as UCup mirrors,
  while ICPC boards hold the onsite teams. Over 2,363 linked same-team,
  same-season pairs, the CCPC result placed on its mirror reads **+9** against
  the ICPC result on its board. Banded by the mean of the two, every band is
  within ±25.
- **So mirror and onsite lines are comparable**, and the 2026-10-11 Jinan
  targets need no mirror correction.

**3. Problem difficulty** (CF rating of the set's median / upper-quartile problem).
- **CCPC vs ICPC (2024–2025, the seasons with CCPC ratings):** CCPC 2768 /
  3243, ICPC 2653 / 3173. The differences, −115 (−247 … +16) and −70, are
  not significant. The CCPC ratings come from the mirrors, which agree with
  the onsite boards (problem-implied check, third entry).
- **Hardest median problem:** CCPC Zhengzhou 2025 3002, CCPC Jinan 2025 2902,
  ICPC Shanghai 2024 2898.
- **Easiest:** ICPC Chengdu 2025 2429 and Xi'an 2022 2253.

**4. Problem quality, from the onsite standings.**
- **Measures.**
  - Mean per-problem discrimination: the AUC of the rest score, solvers vs
    non-solvers. Ties count half, so it is read relatively.
  - "Flat" problems: AUC < 0.80, about the lowest 10%.
  - Problems no official team solved.
  - The share of the field on the gold line's solve count.
  - Rejected runs per accepted run.
  - Consistency: Spearman with the same teams' percentiles at the season's
    other contests.
- **ICPC = CCPC on every measure** (2023–2025, 18 vs 12 contests; no 90%
  interval excludes zero):

  | measure | ICPC | CCPC |
  |---|---|---|
  | discrimination | 0.889 | 0.889 |
  | flat problems per set | 0.8 | 0.5 |
  | unsolved problems per set | 1.9 | 1.8 |
  | share of field at the gold line's solve count | 7.8% | 8.7% |
  | rejected runs per accepted run | 2.32 | 2.08 |
  | consistency | 0.72 | 0.72 |

- **Cleanest ladders:** CCPC Harbin 2024 (0.930, no flat problem, 5% at the
  gold line), then Hong Kong 2025, Jinan 2023, Xi'an 2025, Hangzhou 2024 and
  Chengdu 2025 (0.916–0.925).
- **Weakest:** CCPC Guangzhou 2022 (0.839, 4 flat), Shenyang 2025 (0.844),
  Wuhan 2025 (0.859, 3 flat), then Shanghai 2025, Xi'an 2023, CCPC Chongqing
  2025, CCPC Qinhuangdao 2023 and CCPC Jinan 2025 (0.862–0.867).
- **The signals barely agree.** Across 41 contests, consistency goes with only
  two measures, neither surviving Holm over six tests (≈ .08):
  - the crowd at the gold line (ρ −0.39, permutation p = .013);
  - field size (ρ −0.37, p = .016).

  Discrimination, flat and unsolved counts and the rejection rate show
  nothing.
- **Not measurable from standings:** originality, statement clarity, test
  strength and how instructive a set is. Write-ups that judge these discuss
  solutions, so none were read.

**Unseen CCPC sets on QOJ (set-level only).**
- Harbin 2024 (QOJ 1817) has the cleanest ladder.
- Jinan 2024 (1843) and Zhengzhou 2024 (1873) are average.
- Zhengzhou 2025 (2661) is the highest-rated set, with the most rejected runs of any
  CCPC set (3.54 per accepted run).
- Chongqing 2025 (3387) discriminates below average but has no flat problem.

Run (~15 s once boards are cached; on Windows set `PYTHONUTF8=1`):
`python scripts/contest_quality.py`. Tests: `python -m unittest tests.test_contest_quality`.
