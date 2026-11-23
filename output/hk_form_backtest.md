# NUM-R^3: does practice predict onsite, and what to expect in Hong Kong

Field: `icpc_hk_macau_public_teams_20261122.xlsx`. Scale: `hk_shenyang_rank` (hier_time performances). Single-result spread within a team (pooled, 174 dof): **182**.

## Every 2026 result

| result | date | perf | Shenyang-eq. |
|---|---|---|---|
| 2023 EC Online (I) virtual | 2026-08-20 | 2364 | 77 |
| 2024 EC Online (I) virtual | 2026-08-22 | 2745 | 22 |
| EC Online 2 (official) | 09 | 2319 | 90 |
| EC Online 1 (official) | 09 | 2156 | 143 |
| 2025 EC Online (I) virtual | 2026-09-03 | 2605 | 35 |
| 2025 EC Online (II) virtual | 2026-09-09 | 2392 | 70 |
| 2024 EC Online (II) virtual | 2026-09-10 | 2306 | 93 |
| 2022 The 2022 ICPC Asia Xi'an Regiona virtual | 2026-10-01 | 2440 | 59 |
| 2022 Hangzhou virtual | 2026-10-02 | 2872 | 13 |
| 2022 Jinan virtual | 2026-10-08 | 2501 | 49 |
| 2022 Shenyang virtual | 2026-10-09 | 2484 | 52 |
| 2025 Grand Prix of Jinan virtual | 2026-10-11 | 2408 | 67 |
| 2025 Grand Prix of Zhengzhou virtual | 2026-10-16 | 2210 | 123 |
| 2025 第十一届中国大学生程序设计竞赛 哈尔滨站（CCPC 2025 H virtual | 2026-10-23 | 2397 | 69 |
| Xi'an 2026 virtual #86 | 2026-10-25 | 2406 | 67 |
| Chengdu 2026 virtual #35 | 2026-11-01 | 2592 | 35 |
| CCPC Changchun virtual #29 (2 members, 3:15) | 2026-11-08 | 2512 | 47 |
| Shenyang 2026 onsite #87 | 2026-11-15 | 2327 | 87 |
| Wuhan 2026 virtual #53 | 2026-11-21 | 2478 | 54 |

## Backtest: predicting Shenyang (actual #87, perf 2327) from results before 11-15

| rule | predicted perf | predicted Shenyang rank | error (perf) |
|---|---|---|---|
| Online rounds (official) mean | 2238 | 113 | -90 |
| All virtuals before Shenyang, mean | 2482 | 52 | +155 |
| … −100 | 2382 | 73 | +55 |
| Recency-weighted virtuals (half-life 14 d) | 2477 | 54 | +150 |
| … −100 | 2377 | 74 | +50 |
| Last 3 virtuals (Xi'an, Chengdu, Changchun) mean | 2503 | 49 | +176 |
| Chengdu virtual repeated | 2592 | 35 | +264 |
| Online + all virtuals, mean | 2453 | 57 | +126 |

Measured virtual → onsite gap (Shenyang − recency-weighted virtuals): **-150** (one onsite result; its own uncertainty is about ±182).

## Hong Kong: candidate form estimates

Monte Carlo: gold = top round(10%) of the attending field; NUM-R^3's own strength sd 105 (= spread/√3). 'online ×2' doubles the strength uncertainty of the 30 online-only registrants.

| estimate | perf | Shenyang-eq. | HK position | model gold | MC gold: Reviewed | MC: all | MC Reviewed, online ×2 |
|---|---|---|---|---|---|---|---|
| Shenyang onsite repeated | 2327 | 87 | 19 | 19% | 10% (top 11 of 112) | 13% (top 13 of 126) | 9% (top 11 of 112) |
| Shenyang + change in virtual form since (Wuhan − earlier weighted virtuals) | 2327 | 87 | 19 | 19% | 10% (top 11 of 112) | 13% (top 13 of 126) | 9% (top 11 of 112) |
| All virtuals (incl. Wuhan) recency-weighted, + measured gap | 2327 | 87 | 19 | 19% | 10% (top 11 of 112) | 13% (top 13 of 126) | 9% (top 11 of 112) |
| All virtuals recency-weighted −100 | 2377 | 74 | 16 | 25% | 15% (top 11 of 112) | 18% (top 13 of 126) | 14% (top 11 of 112) |
| Chengdu virtual repeated | 2592 | 35 | 8 | 62% | 47% (top 11 of 112) | 53% (top 13 of 126) | 45% (top 11 of 112) |
| Mean of the 15 QOJ virtuals (Changchun left out) | 2480 | 53 | 13 | 42% | 29% (top 11 of 112) | 34% (top 13 of 126) | 27% (top 11 of 112) |
