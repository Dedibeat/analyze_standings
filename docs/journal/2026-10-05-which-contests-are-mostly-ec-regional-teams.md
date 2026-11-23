# Which contests are mostly EC-regional teams? (2026-10-05)

`scripts/ec_overlap.py` → `output/ec_overlap.csv` (268 contests, every contest in
`tagged.json`, both UCup seasons, Petroz and `icpc_2020_2021.json`, deduped by
contest id). **Reference set:** all 10,882 rosters in
`data/ec_online/regional_teams.csv` (2022–2025 onsite EC regionals, official and
unofficial). A standing row is *matched* when two of its members sat on the same
reference team (the repo's ≥2-member rule). The `pinyin` column also lets
Latin-spelled members match the reference's Chinese names (pypinyin, surname-first
or given-first). Share is of rows with a ≥2-member roster. An EC regional mirror is
matched with its own (season, site) removed.

Why pinyin matters: UCup/QOJ boards often romanise Chinese names, so exact match
undercounts badly (Nanjing 2024: 46.7 % exact → 63.7 % pinyin). Control: Russian
onsite contests (NWRRC, Northern Eurasia Finals) stay at 0–4 %.

| group | pair-match (pinyin) |
|---|---|
| EC-Final 2023 / 2025 warm-ups | 92–94 % |
| EC regional mirrors 2023–2025 (own site left out) | 58–70 % |
| EC Online 2023–2025 | 52–61 % |
| EC Online 2026 | 22 % (new 2026 teams have no regional yet) |
| **Non-EC, ≥ 50 %: Moscow Subregional mirrors 2022 / 2023** | 51 % / 60 % (166 / 73 rows; Peking Univ., "jiangly" etc.) |
| **Non-EC UCup stages with Chinese-city names not in the EC list** | Harbin 70, Zhengzhou 70, Chongqing 68, GP Jinan 63, GP Zhengzhou 62, Jinan (1843) 61, Wuhan (2025) 60, Shenzhen 43, Hubei 36, Wulin 35, Cangqian 34, GP Wulin 23 |
| Other QOJ mirrors | SPb 2023 35, Taipei 2023 33 |
| UCup stages hosted outside China | 10–30 % (Tokyo 31, Sendai 25, Warsaw 12) |
| Russian / Armenian onsite regionals, Petroz camps | 0–4 % |

Caveats. (1) The Chinese-city UCup stages are presumably CCPC/provincial mirrors, but
that was inferred from stage names, not checked. (2) Unmatched ≠ non-Chinese: the
reference stops at 2025 and only holds regional attendees, so 2020–2021 mirrors
(8–31 %) and 2026 online rounds are underestimated; romanised names that collide
or differ in spelling are missed. (3) UCup-hosted boards mix in top international
teams, so their top-50 share is much lower than their overall share. (4) Direct
CCPC/provincial boards are not in the repo (the XCPCIO samples above were not kept),
so those can only be inferred through the UCup mirrors.
