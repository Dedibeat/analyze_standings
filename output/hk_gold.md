# Hong Kong gold chances from online strength and field history

`arch_b.hk_gold`. Linked = tied to an online-qualifier result by `arch_b.hk_link` (members only exist
on the 2024-2025 boards). Online rank = exp(mean log rank) over the rounds entered.

## Field

| contest | official | golds | local | non-local schools | multi-team | top-50 / top-100 schools | returning schools | linked (golds) | gold line (online rank) | coin flip (online rank) | linked golds with an earlier mainland gold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 hongkong | 115 | 12 | 21 | 51 | 30 | 17 / 24 | - | 6 (1) | - | - | - |
| 2023 macau | 82 | 8 | 15 | 59 | 8 | 22 / 33 | 26 | 7 (1) | - | - | - |
| 2024 hongkong | 149 | 15 | 14 | 107 | 28 | 31 / 49 | 40 | 118 (13) | 66.4 | 80.1 | 11 / 13 (teams: 14) |
| 2025 hongkong | 126 | 13 | 15 | 110 | 1 | 33 / 58 | 66 | 97 (12) | 53.0 | 74.1 | 9 / 12 (teams: 13) |

Mainland coin-flip online ranks (same shared slope): 2023 hangzhou 96.4, 2023 hefei 88.4, 2023 jinan 78.3, 2023 nanjing 91.2, 2023 shenyang 94.9, 2023 xian 86.5, 2024 chengdu 98.8, 2024 hangzhou 108.5, 2024 kunming 98.0, 2024 nanjing 96.9, 2024 shanghai 104.4, 2024 shenyang 81.6, 2025 chengdu 78.8, 2025 nanjing 89.1, 2025 shanghai 85.2, 2025 shenyang 133.9, 2025 wuhan 95.0, 2025 xian 127.2.

## Can the field be predicted? (train one season, test the other)

| train → test | attendance AUC | schools exp. / act. | top-50 schools exp. / act. | gold line actual | simulated (80%) | same as train | abs log error sim. / same |
|---|---|---|---|---|---|---|---|
| 2024 → 2025 | 0.872 | 121.5 / 107 | 34.4 / 33 | 53.0 | 70.0 (52.4–101.6) | 66.4 | 0.278 / 0.226 |
| 2025 → 2024 | 0.758 | 91.2 / 101 | 33.1 / 31 | 66.4 | 39.5 (25.0–62.6) | 53.0 | 0.52 / 0.226 |

## Gold models (train one season, test the other)

| model | 2024 log loss (exp. golds) | 2025 log loss (exp. golds) |
|---|---|---|
| mainland_online_only | 0.1026 (14.7 / 13) | 0.1227 (14.1 / 12) |
| mainland_oracle_line | 0.1036 (11.1 / 13) | 0.1258 (9.4 / 12) |
| hk_online_only | 0.1007 (12.3 / 13) | 0.1165 (12.6 / 12) |
| hk_earlier_mainland_gold | 0.088 (12.5 / 13) | 0.1119 (12.3 / 12) |
| hk_members_prev_gold | 0.1165 (11.6 / 13) | 0.1219 (12.4 / 12) |

## 2026 forecast (conditional on attending; 2027-01-09)

Hong Kong-only model fit on 2024 + 2025 linked teams: coin flip at online #76.7. Harder / easier field = the coin flip moved by one SD (0.253 in log rank, 7 consecutive-season mainland pairs) of the mainland year-to-year change. The last two columns use the model with an earlier mainland gold, for the update once 2026 mainland results are in.

| online rank | P(gold) | 90% CI | harder field | easier field | no mainland gold | won a mainland gold |
|---|---|---|---|---|---|---|
| 10 | 99.4% | 97.5%–99.9% | 98.9% | 99.7% | 96.9% | 99.5% |
| 25 | 94.3% | 85.4%–98.8% | 89.8% | 96.9% | 81.8% | 96.4% |
| 50 | 74.5% | 57.2%–88.9% | 60.8% | 84.6% | 50.6% | 86.1% |
| 75 | 51.4% | 34.7%–69.4% | 36.0% | 66.6% | 30.2% | 72.3% |
| 100 | 34.0% | 20.5%–49.5% | 21.5% | 49.3% | 19.0% | 58.5% |
| 150 | 15.8% | 7.3%–24.0% | 9.0% | 26.1% | 9.0% | 37.3% |
| 200 | 8.4% | 3.1%–13.4% | 4.6% | 14.7% | 5.1% | 24.3% |
| 300 | 3.2% | 0.8%–5.7% | 1.7% | 5.9% | 2.2% | 11.9% |
| 500 | 0.9% | 0.2%–2.0% | 0.5% | 1.7% | 0.8% | 4.4% |

### 蒙古国立大学 (2026 online teams)

| team | online ranks | P(gold) | 90% CI | harder / easier field |
|---|---|---|---|---|
| NUM-R^3 | 544/349 | 1.3% | 0.2%–2.7% | 0.7% / 2.4% |
| NUM-MNM | 585/981 | 0.3% | 0.0%–0.9% | 0.2% / 0.6% |
| NUM-B2D | 1171 | 0.1% | 0.0%–0.4% | 0.1% / 0.2% |
| NUM-XOX | 837/2095 | 0.1% | 0.0%–0.3% | 0.0% / 0.2% |
| NUM-SEA | 1425/1530 | 0.1% | 0.0%–0.2% | 0.0% / 0.1% |
| NUM-BSB | 1507/1515 | 0.1% | 0.0%–0.2% | 0.0% / 0.1% |
| NUM-SOTS | 1523/1779 | 0.0% | 0.0%–0.2% | 0.0% / 0.1% |
| NUM-BTsCh | 1975/1811 | 0.0% | 0.0%–0.1% | 0.0% / 0.1% |
| NUM-GZB | 2406 | 0.0% | 0.0%–0.1% | 0.0% / 0.0% |
| NUM-GBZ | 2407 | 0.0% | 0.0%–0.1% | 0.0% / 0.0% |
