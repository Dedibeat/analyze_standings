# PTA registration lists for 2025–2026 (2026-09-28, review)

**Files** (downloaded by the user from PTA into `data/`, untracked; columns
`team_id, team_name, team_name_en, school_name_cn/en, province, city, leader,
members` (`/`-separated), `coaches, review_status, created_at`):

| file | round | rows (REVIEWED) | created | PKU ranking matched by school + team |
|---|---|---|---|---|
| `icpc_2025_online_1_teams.csv` | 2025 r1 | 2,298 (2,279) | 2025-08-11 – 08-28 | 2,124 / 2,159 |
| `icpc_teams_2025_online_2_fixed.csv` | 2025 r2 | 2,597 (2,575) | 2025-08-11 – 09-03 | 1,723 / 1,745 |
| `icpc_2026_ec_round1_teams.csv` | 2026 r1 | 2,537 (2,535) | 2026-08-10 – 08-26 | 2,478 / 2,486 |
| `icpc_2026_ec_online_round2_teams.csv` | 2026 r2 | 2,640 (2,636) | 2026-08-10 – 09-01 | 2,472 / 2,480 |

`icpc_2025_online_2_teams.csv` is a **byte-identical copy of the 2026 round-2
file** (same MD5, 2026 timestamps) and must not be used; the `_fixed` file
replaces it. Quality: unique ids, no duplicate (school, team), no member on two
teams of one school, leader always among members; 1–2-member teams are ~4%.
Every unmatched ranking team is a school renamed or re-registered on PTA
(信息工程大学 → 中国人民解放军网络空间部队信息工程大学, 绍兴文理学院 → 绍兴大学,
湖州师范学院 → 湖州师范大学, 湖南理工学院 → 湖南理工大学, 常熟理工学院（已改名）,
`…（重复）` duplicates, …), so an alias table is needed on integration. The PKU
2025 rankings list only ≥1-solve teams (QOJ round 2 has 836 zero-solve rows),
which is why registrations exceed ranking rows.

**Online-gold / TabFM (measured by re-running `link_regionals` with the rows
appended to `online_rosters`).** 2025 mainland regional teams linked to an
online result: **1,282 → 2,017 of 2,231 (57% → 90%)**, every site 88–92%;
2025 golds linked 164 → 211 of 233. 2022–2024 (78–86%) are unchanged. This
removes the 2025 gap behind the quota labels (band slots only go to linked
teams), the 2025 online-tier features and the 2025 held-out/training rows. For
2026 the rosters make the member-history tier computable before registration:
of ~2,480 ranked teams per round, ~830 have a member who played a 2025
official regional, 540 a 2025 medallist and 97–104 a 2025 gold medallist
(79–85 of the top 300). That tier carried most of TabFM's backtest gain.
Cross-round renames (≥2 shared members, same school, new name): 84 teams in
2025 and 130 in 2026; `online_strengths` keys by name, so they are currently
split into two one-round teams.

**Rating fit.** QOJ 2513 / 2524 (the 2025 online rounds, in the fitted set)
have members on only 9 / 4 rows, so their teams link to the rest of the fit
only by trusted names, mostly to each other. Attaching roster members to rows
whose name is unique in the round's roster, whose school + name is in the PKU
ranking and whose solved count agrees (2,038 / 1,659 rows; one mismatch) raises
the rows sharing an identity with a non-online contest **240 → 1,432** and
**205 → 1,294** in the `joint.py` union-find. The new links go to the 2025
Wuhan, Shenyang, Nanjing, Shanghai and Chengdu regionals and EC-Final. The
effect on calibrated LOCO is **untested**: identity fixes are the only changes
that have improved it before, but qualifier removal was neutral. The 2026 lists
do not affect the fit yet (no 2026 contest is loaded).

**Status:** the forecast side is integrated in the next section. The fit
attachment is still untested with `arch_b.metric`.
