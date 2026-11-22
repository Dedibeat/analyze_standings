# Hong Kong registration: 10-28 export (2026-10-28)

**Data.** `data/icpc_hk_macau_public_teams_20261028.xlsx` (file stamp 13:50,
UTC+8), now the default and the newest `SNAPSHOTS` entry.
- 144 teams, all `Pending`: the 143 of 10-26, plus 5 new, minus 4 that
  withdrew. One team was renamed (山东大学（威海） Attack on MilkFrog →
  进击的奶蛙).
- New: 重庆邮电大学 (school #29), 南昌大学 (#139), 湖北工业大学 (#199), 太原理工大学
  (#325) and 广州软件学院 (#471).
- Withdrawn: 浙江理工大学 (#79; 2024 Hong Kong silvers), 温州医科大学 (#207),
  桂林电子科技大学 (#227) and 河北科技大学 (#248).
- 123 link; 南昌大学 and 湖北工业大学 do not.

**Registration has nearly stopped.** In the 1.75 days since 10-26, one school
above NUM-R^3 registered (重庆邮电大学) and one withdrew (浙江理工大学).
- NUM-R^3 is still 60th: 59 ahead, room 35, 64 unregistered non-local
  schools above it.
- Round 1 if it closed now: 136 non-local teams for 95 seats, cut below
  school #250.

**Cut risk.** `cut_risk` now counts the registrations among the group's
schools unregistered at the earlier snapshot. On 10-28 the old net count
(unregistered before − after) was 0 for the past-HK group, because one
school registered and one withdrew. A school that withdrew counts as
unregistered again, and withdrawals are reported per group.
- In the 2.42 days left, at any multiple of the 10-26 → 10-28 pace, the
  chance NUM-R^3 is cut is ~0.
- The "others" group registered nobody in this window, so its stress row
  reads 0 too. The break-even still applies: with every past-HK school back,
  each of the 39 others would need a 17% chance to register for a 5% cut.
- Over the longer 10-23 → 10-28 window (10 of 34 past-HK, 1 of 40 others),
  even 5× that pace gives 17 expected new schools against the 36 needed. So
  P(cut) ≈ 0.

**Field.** The registered list is unchanged in strength: gold line online
#198, 5.4 expected golds. The scenario's gold line moved #92 → #80 only
because its field has 85 matched teams instead of 86. The 10% line is
therefore the 8th team rather than the 9th. Expected golds are unchanged at
8.7.
- None of the new teams is strong. The best is 太原理工大学 at online #1118;
  重庆邮电大学 (school #29) entered a #1382 line-up.
- 13 schools with a 2024/2025 Hong Kong gold or silver are not registered
  (浙江理工大学 joins the 12 of 10-26).

**NUM-R^3** is 26th of the 123 linked teams by strength (23 round-1 teams
stronger). Gold / silver / bronze: 1.3% / 34% / 46% absolute (unchanged);
2.2% / 29% / 47% field-relative, scenario. On the Xi'an virtual reading, at
most ~2.5% / 45% / 40%.

Tests pin the 10-28 export: 144 / 123 teams, 136 round-1 teams with 41 cut,
the rank check on 144 rows, and cut-risk counts of 1 + 0 registered and
1 + 0 withdrawn since 10-26.
