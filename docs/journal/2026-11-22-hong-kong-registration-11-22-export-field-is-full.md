# Hong Kong registration: 11-22 export, the field is full (2026-11-22)

**Request.** "Is HK field close to being saturated?", asked about the 11-22
public team export.

**Data.** `data/icpc_hk_macau_public_teams_20261122.xlsx`, copied from the
user's download (stamp 2026-11-22 16:26, UTC+8). It is now in `SNAPSHOTS`.
The default `REGISTRATION` is still the 10-28 export, because the tests pin
it.
- 126 teams: 112 `Reviewed` and 14 `Pending`. On 10-28 all 144 were Pending.
- 51 teams left the list and 33 joined it, comparing (school, team name).
  Three schools (人民大学, 杭州师范大学, 江西农业大学) changed line-up.

**Seats** (from the notice: about 120 teams, 95 non-local, 20 local, about 5 star teams):

| | Reviewed | Pending | seats |
|---|---|---|---|
| non-local | 95 | 12 | 95 |
| local (HK/Macau) | 17 | 2 | 20 |
| total | 112 | 14 | ~120 |

- **The non-local seats are exactly full.** Round 1 was cut by school rank.
  Every 10-28 team at school #201 or worse is gone, except the ones now
  Pending. The last Reviewed school is #199 (湖北工业大学).
- The 12 non-local Pending teams are mostly the overflow: schools #215–#399
  (合肥工业大学宣城, 成都锦城, 南京工程, 上海海洋, 南京师范, 沈阳化工, 惠州, 黄淮,
  燕京理工). There is also a second team (西南大学) and 重庆城市科技学院 (#196).
  北京理工大学 (#50) is Pending too, which ranking does not explain.
  `arch_b.hk_field_2026`'s own round-1 rule cuts 12 teams at #196 / #199.
- Local: 17 of about 20 seats are Reviewed, and 2 more are Pending. 香港理工大学
  has 3 teams, against the notice's limit of 2 per school.
- At most about 8 seats are left, for 14 Pending teams and the star teams.
  Rounds 1 (10-30) and 2 (11-14) are closed, so only round-3 applications remain.

**Strength.** The field is set, and it is weaker at the top than 2024/2025.

| field | linked | within online #50 / #100 / #200 / #500 | 10% line (online rank) | expected golds (absolute) |
|---|---|---|---|---|
| 2024 official | 118 | 7 / 13 / 22 / 42 | 66 | 12.6 |
| 2025 official | 97 | 7 / 16 / 18 / 34 | 53 | 12.3 |
| 2026, all 126 | 97 | 3 / 7 / 13 / 28 | 130 | 6.3 |
| 2026, Reviewed only | 85 | 3 / 7 / 13 / 27 | — | 6.2 |

- 11 past gold/silver schools are not registered, and it is now too late for
  them: 上海交通大学, 复旦大学, 哈尔滨工业大学, 清华大学, 南京大学, 中国科学技术大学 and others.
- 29 teams are unlinked (27 Reviewed), so the strength figures are a lower
  bound. Among them are 南方科技大学 SUSTech-Ok, 大连理工大学, 苏州大学, 兰州大学,
  CUHK ×2 and HKU ×2.
- NUM-R^3 is `Reviewed` (school #128). It is 26th of the 85 linked Reviewed
  teams. Gold / silver / bronze is 1% / 34% / 46% absolute and 7% / 37% / 41%
  field-relative on this list.

**Code.** `arch_b/hk_field_2026.py`: an 11-22 `SNAPSHOTS` entry, and
`XLSX_ONLY_SCHOOLS` for two schools that no PTA CSV lists: 岭南大学 and New
Mongol Institute of Technology, which has no Chinese name. Without it,
`read_registration` raised KeyError. `tests.test_hk_field_2026`: 6/6 pass.

**Reproduce.**

    PYTHONUTF8=1 python -m arch_b.hk_field_2026 --file data/icpc_hk_macau_public_teams_20261122.xlsx
