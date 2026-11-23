# Hong Kong field ranked by Shenyang rank (2026-11-16)

**Request.** Where does NUM-R^3 rank in Hong Kong, reading the field in
Shenyang-rank terms? Use the 2026 online rounds, regionals and CCPC.

**NUM-R^3 at Shenyang** (`icpc/51st/shenyang`, 11-15): board #94, **official
#87 of 401**, 5 solved, 647 min.

**Method** (`scripts/hk_shenyang_rank.py`, new):
- Field: the 10-28 Hong Kong export (144 teams), the newest one in `data/`.
- Each registrant is linked to its 2026 appearances:
  - EC Online I/II rows (4071/4113): the `hk_field_2026` online link, then
    the board row with the same team name and solve count;
  - the five 51st regionals' official XCPCIO rows: same school and ≥ 2 shared
    members, or the same team name where the board has no members (Xi'an);
  - the 2026 CCPC boards: Changchun (QOJ 4582), Guizhou, Nanchang and
    Qinhuangdao (XCPCIO; no affiliations, so these match on ≥ 2 members alone).
- Online and regional rows take their CF performance from the binary joint
  fit (`export_virtual_calc.performance_fit`). The QOJ-hosted regionals
  (Xi'an/Chengdu/Wuhan) map an XCPCIO official row to a QOJ row by team name
  and solve count.
- CCPC boards are not in the fit. Each is mapped as `perf = a + b·log(rank)`,
  fitted on its line-ups that have a 2026 regional performance:
  - Guizhou: 68 pairs, r −0.67;
  - Nanchang: 80 pairs, r −0.69;
  - Qinhuangdao: 72 pairs, r −0.75;
  - Changchun: 0 pairs (51/939 rows have members), so it is not used.
- Strength is the mean of a team's appearances. Its Shenyang-equivalent rank
  is 1 + the number of official Shenyang teams with a higher performance.

**Result** (`output/hk_shenyang_rank.md`; 130 of 144 registrants have a 2026
result, 79 of them from an onsite contest):

| NUM-R^3 | perf | Shenyang-equivalent |
|---|---|---|
| Online I (#544 official) | 2245 | #129 |
| Online II (#349) | 2442 | #82 |
| Shenyang (#87 official) | 2425 | #87 |
| mean of all three | 2371 | #101 |

- **About 23rd in the Hong Kong field.** 22 registrants are ahead:
  - 2 are local (HKUST 喵喵喵幼儿园, Shenyang #10; HKUST 许愿是要付出代价的);
  - 8 are rated on online rounds only (e.g. PKU 飞带不长队, 福州大学, 杭电, 南航,
    人大, 天大);
  - the closest are 南方科技大学 SUSTech-Ok (Chengdu #87, eq. #98), 西安交通大学
    (eq. #98), 华中科技大学 (#99) and HKUST's second team (#100).
- **Onsite results only** (NUM-R^3 2425 = Shenyang #87): 9 registrants with
  an onsite result are stronger.
- Medal shares on the 2024/2025 boards: gold 10%, silver-or-better 30%. With
  ~120 teams, gold reaches about rank 12 and silver about rank 36. 23rd is
  mid-silver, consistent with the earlier Hong Kong forecasts.

**Limitations / missing data:**
- **The registration list is stale.** The newest export is 10-28. Round 1
  closed 10-30 and round 2 on 11-14. 13 schools with a 2024/2025 Hong Kong
  gold or silver had not registered by 10-28. Each strong late entrant moves
  NUM-R^3 down a place. A fresh PTA export is needed to settle the final
  field.
- Online performance is not onsite form. Teams rated on online rounds only
  are less certain, in both directions.
- Xi'an rows match on school and team name only, so a renamed line-up is
  missed there.
- 14 registrants have no 2026 result (listed in the output), among them the
  local HKU team.
- Team strength is a plain mean: it has no shrinkage and no weighting by
  contest type.

Run: `python3 scripts/hk_shenyang_rank.py [--team NAME]` (~20 s; needs
`openpyxl` and `pypinyin`).

## 11-16 export: rechecked (2026-11-16, second entry)

**Data.** `data/icpc_hk_macau_public_teams_20261116.xlsx` is the user's PTA
export, stamped 14:18 UTC+8 (06:18 UTC). It is now the `hk_field_2026`
default and the newest `SNAPSHOTS` entry. Round 1 (10-30) and round 2 (11-14)
have both closed.
- **122 teams:** 110 Reviewed, 12 Pending. NUM-R^3 is **Reviewed**.
- Against 10-28: 52 teams are gone and 30 are new.
- The new teams are mostly local, round-2 or late line-ups: 香港理工大学 ×3,
  香港城市大学 ×2, 香港浸会大学 ×2, 澳门城市大学 ×2, 澳门科技大学, 杭州师范大学,
  西安电子科技大学, 南开大学 and others.
- The Pending teams include all 9 non-local teams that the module's round-1
  cut would drop (school #215 and worse), plus 西南大学's second team,
  重庆城市科技学院 and PolyU 冻柠走冰. The Pending status most likely marks the
  waiting list. This is inferred from the overlap; it is not stated anywhere.
- **The strong schools did not come.** 上海交通大学, 复旦大学, 哈尔滨工业大学,
  中国人民大学 (the 10-28 line-up left), 南京大学, 中国科学技术大学 and others
  with a 2024/2025 Hong Kong gold or silver are absent.

**Field** (`output/hk_field_2026.md`):
- 95 of 122 teams link to an online result.
- Gold / silver+ / medal lines are online **#135 / #504 / #1005**, against
  #53–66 gold in 2024/2025.
- Expected golds from the absolute model: 5.6, against 12.3–12.6.
- So this is a weaker top than in past years. The scenario rows (adding
  unregistered 2025 schools) and the round-1 cut-risk section no longer apply,
  because registration has closed.

**NUM-R^3:**
- **By online strength:** 26th of the 95 linked teams.
- **Gold / silver / bronze:**
  - field-relative model on the actual list: **8% / 36% / 42%** (silver or
    better 44%);
  - absolute model: 1% / 34% / 46%, unchanged.
  - The field-relative model was preferred once the list closed (2026-10-15).
- **By Shenyang-equivalent strength** (`output/hk_shenyang_rank.md`): **24th
  of the 103 registrants with a 2026 result.** 23 are ahead; 3 of them are
  local: HKUST ×2 and the new PolyU 冻柠走冰 (Chengdu #16, Pending).
- On onsite results alone, 11 registrants are stronger.
- The new teams ahead: 杭州师范大学 Rise from the Brink (online only, Shenyang
  eq. #26) and PolyU 冻柠走冰 (#38). 西安电子科技大学 (#117) is new too, but
  behind NUM-R^3. One team that was ahead left: 中国人民大学 亻亻亻 (#42). Net:
  one place down, from 23rd to 24th.
- With ~110 attending teams and 10% / 30% medal shares: gold reaches rank
  ~11, silver ~33. 24th is mid-silver, ~13 places below gold.
- Teams ahead that are rated only online: 8, the same as before.

**No 2026 result:** 19 teams, among them HKU, CityU CityU 0.5, HKBU_Team,
澳门城市大学 基米斗队 and 苏州大学.

**Tests.** `tests/test_hk_field_2026.py` now pins the 11-16 export:
- 122 / 95 teams;
- 104 round-1 teams with 9 cut;
- the extra team is 西南大学 梦到哪句写哪句万一对了呢;
- the renamed line-up check moves to 南京工程学院 (round 1 #665 / round 2 #1077),
  because 西南石油大学 left;
- cut-risk counts: 6 + 3 registered and 1 + 0 withdrawn since 10-28;
- 8 others needed.

All 6 tests pass.

## Chengdu and Changchun virtuals in the Hong Kong field (2026-11-16, third entry)

**Request.** What do the Chengdu and Changchun virtuals translate to at Hong
Kong?

**Inputs.**
- **Chengdu 2026 virtual** (11-01): 6 solved, 894 min, **#35 of 319
  official**. Source: `output/team_r3_participations.md`.
- **12th CCPC Changchun virtual** (2026-11-08 entry, on the unmerged branch
  `claude/vigilant-bohr-gd202a`): **7 solved / 683 min at 3:15**. Two members
  played (Erdene absent) and stopped early. That is official **#29 of 301**
  (gold, one place inside the line) on the final board, and **#13** at the
  3:15 cut.
- That branch's `output/ccpc_12th_changchun_standings.csv` (the official
  rank.iccpc.cn board, with members) is copied here unchanged.

**Script changes** (`scripts/hk_shenyang_rank.py`):
- **Changchun is now mapped from the official CSV**, not QOJ 4582, which has
  members on only 51 rows.
  - 192 line-ups pair with a 2026 regional: `perf = 3745 − 328·log(rank)`,
    r −0.81.
  - Registrants who played Changchun now count it. NUM-R^3 stays 24th of 103;
    12 registrants (was 11) have a stronger onsite mean.
- **`--virtual BOARD:RANK`** places a virtual result in the field:
  - regional: the mean performance of the official teams at ranks k−1 and k;
  - CCPC: the board's map.
- **Each virtual is converted to:**
  - a Shenyang-equivalent rank;
  - a position among the registrants;
  - an online-equivalent rank, from a linear fit of online strength x on
    online performance over 85 registrants (r 0.99);
  - gold / silver / bronze, from the field-relative Hong Kong model on the
    registered 11-16 field (gold line online #135).
- Each virtual is shown raw and 100 CF weaker. Earlier entries found a
  virtual scoreline reads up to ~100 CF stronger than onsite form.

**Result:**

| result | perf | Shenyang-eq. | HK position (of 103) | online-eq. | gold / silver / bronze |
|---|---|---|---|---|---|
| Shenyang onsite (#87) | 2425 | 87 | 18 | #319 | 17% / 42% / 32% |
| Chengdu virtual #35 | 2738 | 37 | 8 | #146 | 63% / 25% / 10% |
| … −100 | 2638 | 49 | 12 | #187 | 46% / 35% / 16% |
| Changchun virtual #29 (final board) | 2641 | 48 | 12 | #186 | 47% / 34% / 15% |
| … −100 | 2541 | 59 | 13 | #239 | 31% / 41% / 22% |
| Changchun at 3:15 (#13), pace only | 2904 | 24 | 5 | #96 | 84% / 10% / 5% |

**How to read it:**
- The two virtuals agree with each other. Both put the team around Shenyang
  #37–59 and 8th–13th in the Hong Kong field. That is the gold/silver
  border, against the onsite Shenyang reading of ~18th (strength alone) or
  24th (mean of all appearances, including the weaker online round 1).
- **The field is weak at the top.** With ~110 teams, gold reaches about
  rank 11. So a virtual-level performance at Hong Kong is a near coin flip
  for gold: ~30–60% after the discount.
- **The Changchun #13 row is a pace extrapolation, not a result.** Two
  members stopping early pull the real reading up, and the virtual effect
  pulls it down. Neither effect has been measured.
- **Gap between virtuals and onsite.** Onsite Shenyang read ~300 CF below
  the Chengdu virtual. Whether that gap is form or the virtual effect decides
  which row to trust.
- **The −100 column is a ceiling, not a measured value.** Earlier entries
  measured the virtual effect at up to ~100 CF.
- The Hong Kong position compares one performance with registrants' mean
  strengths, which mix online and onsite results.

Run: `python3 scripts/hk_shenyang_rank.py --virtual Chengdu:35 --virtual
'CCPC Changchun:29' --virtual 'CCPC Changchun:13'`.

*(Merged into this file from the branch's `details.md` when master moved the
journal to `docs/journal/`. The 11-16 export and its test pins from that branch
were dropped in the merge: master's `hk_field_2026` keeps the 10-28 default for
its tests and gained the 11-22 export, which supersedes 11-16.)*
