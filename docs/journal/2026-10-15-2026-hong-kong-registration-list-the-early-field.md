# 2026 Hong Kong registration list: the early field (2026-10-15)

**Data.** `data/icpc_51_asia_hkmo_teams.csv` is the PTA export of the 51st
Asia Hong Kong/Macau registration, downloaded by the user on 10-15. It has
the same columns as the online-round exports:
- 88 teams from 88 schools, registered 10-11 16:01 to 10-15 05:12 UTC, all
  `PENDING_REVIEW`;
- 87 non-local teams plus HKU, the only local team (local seats are by
  application, so most local teams are probably not on this list);
- one 2-member team (汕头大学) and one 1-member team (井冈山大学).

**Rules re-read** (notice: https://icpc.pku.edu.cn/docs/2026-08/8f9a5ef234f04f5690f8a35eb52fee9f.pdf):
- About 120 teams, including about 5 star teams (over-quota school teams and
  Hong Kong/Macau secondary-school teams).
- 95 non-local seats. **Round 1** runs until 10-30, one team per school. If
  more than 95 register, the 95 are taken "按网络预选赛排名从高到低". The
  notice does not say which online round counts or how the two are combined.
- **Round 2**, before 11-14: one extra team per school, first-come. **Round 3**:
  applications.
- 20 local seats, at most 2 per school (HKU included), by application. HKU
  allocates any seats left over.
- The EC-Final rule is as recorded on 2026-10-08.

**Linking** (`arch_b.hk_field_2026`). The list has Chinese member names, so
no pinyin step is needed. In each online round a line-up links to the
same-school 2026 online team sharing at least 2 members, or failing that to
the same school + team name. A line-up renamed between the rounds keeps both
ranks (西南石油大学: round 1 as 昇天, round 2 as 接地).
- 78 of 88 teams link, all by members.
- 10 do not: HKU (local), and 9 line-ups that mix members of different online
  teams or have members on no roster.

**Field** (linked teams; online rank = exp(mean log rank)):

| field | linked | median online rank | within #50 / #100 / #200 / #500 | gold / silver+ / medal line (online rank) | expected golds (absolute model) |
|---|---|---|---|---|---|
| 2024 Hong Kong (149 official) | 118 | 753 | 7 / 13 / 22 / 42 | 66 / 417 / 965 | 12.6 |
| 2025 Hong Kong (126 official) | 97 | 776 | 7 / 16 / 18 / 34 | 53 / 431 / 827 | 12.3 |
| 2026 registered so far (88) | 78 | 1006 | 1 / 2 / 5 / 10 | 368 / 734 / 1089 | 2.2 |
| 2026 scenario: + 51 unregistered 2025 schools, top 95 | 95 | 708 | 6 / 14 / 19 / 33 | 71 / 388 / 804 | 11.1 |

- **The early list is far weaker than the 2024/2025 fields, because the
  strong schools have not registered yet.** 40 of the 91 linked non-local
  schools of the 2025 field are on the list. 28 schools with a 2024/2025
  Hong Kong gold or silver are missing, among them 上海交通大学, 复旦大学, 清华大学,
  哈尔滨工业大学, 北京航空航天大学, 南方科技大学, 香港中文大学深圳, 香港科技大学广州
  and 西安交通大学.
- **Scenario.** Every 2025 school not yet registered comes back with a team
  as strong as its 2025 Hong Kong team (2025 online ranks), and round 1 keeps
  the top 95 by online rank. This brings the field back to the 2024/2025
  level: gold line #71, 11.1 expected golds. The early list therefore does not
  change the Hong Kong forecast yet. It will once round 1 closes.
- **The round-1 cut would bite.** In the scenario, 24 of the 78 linked
  registrants fall outside the top 95: every team at online #1,139 or worse.

**Field-relative model.** `logit P(medal ≥ k) = c_k + b_k (x − line_k)`, where
line_k is the linked team at 10% / 30% / 60% of the field. The line's
coefficient is fixed at −b_k, not estimated, because there are only two
seasons. Compared with the absolute Hong Kong model (`c_k + b_k x`), training
on one year and testing on the other (log loss, with expected / actual counts):

| test | gold: absolute / relative | silver+: absolute / relative | any medal: absolute / relative |
|---|---|---|---|
| 2024 | 0.1007 / 0.1010 (12.3, 14.4 / 13) | 0.4155 / 0.4342 | 0.5249 / 0.5208 (71.3, 77.5 / 80) |
| 2025 | 0.1165 / 0.1181 (12.6, 10.9 / 12) | 0.3255 / 0.3223 | 0.4963 / 0.4824 (67.6, 63.8 / 61) |

- For gold it is a wash. For any medal it is better in both years.
- It is worth using once the list closes. On today's incomplete list it is
  meaningless: it would give NUM-R^3 57% gold. The absolute model stays the
  forecast for now.

**Teams** (`output/hk_field_2026.md` lists all 78; gold / silver / bronze from
the absolute model, conditional on attending):
- Strongest registered: 北京大学 飞带不长队 (round 2 #4, ~100% gold); 福州大学
  (#36 / #234: 39% gold, 51% in the scenario); 杭州电子科技大学 (#120: 25%);
  华东师范大学 (#130 / #129: 21%); 天津大学 (#203 / #170: 10%).
- **NUM-R^3** (#544 / #349):
  - 10th of the 78 linked registrants by mean online rank (12 non-local
    teams ahead by best-round rank), and 30th of 129 in the scenario.
  - Safe from the round-1 cut: it drops out only if about 65 more teams
    stronger than it register.
  - Gold / silver / bronze: 1.3% / 34% / 46% (absolute model, unchanged from
    2026-10-01); 1.6% / 30% / 48% (field-relative, scenario).

**Not changed:** `hk_gold`, `online_medals` and `ecfinal_chance`. The Hong
Kong EC-Final depth (rank 32–37) is not recomputed, because that needs to
know which Hong Kong teams already hold a mainland round-1 seat.
`icpc_2025_online_2_teams.csv` is still the 2026 round-2 list. Its content is
identical; only its CRLF line endings differ, which is why its MD5 changed.
It stays uncommitted.

Run: `python3 -m arch_b.hk_field_2026 [--file CSV] [--team NAME]` (on Windows
set `PYTHONUTF8=1`). Tests: `tests/test_hk_field_2026.py`, which pins this
export's counts (88 / 78). Rerun on a fresh export after round 1 closes
(10-30) and update the tests' counts.

## Updated export (2026-10-17 follow-up)

**Data.** `data/icpc_hk_macau_regional_teams.csv` is the user's PTA export of
10-17 (registrations up to 14:30 UTC). It is now the module's default; the
10-15 file stays as a snapshot.
- 106 teams, all `PENDING_REVIEW`: the 88 of 10-15 plus 18 new ones. None was
  removed. One team was renamed (昆明理工大学 N.P.L.G → 数论、概率论、线性代数滚出我的 ICPC).
- One new team (北京理工大学) was created on 10-14, before the 10-15 export's
  last entry, yet was not in it. So PTA's public list can lag.
- 福建师范大学 now has two teams. Round 1 allows one per school, so the
  module now treats a school's later registration as a round-2 entry: it is
  left out of the round-1 pool and the scenario (`extra` in the table).
- 95 of 106 teams link to the online rounds. The new unlinked team is
  南方科技大学 SUSTech-Ok. Its three members are on no 2025 or 2026 online
  roster and no regional board. SUSTech's 2025 Hong Kong gold line-up (online
  team 南方科技大学1队) has not registered.

**Round 1 is already oversubscribed.** There are 104 non-local round-1 teams
for 95 seats, so 9 would be cut if the list closed now. 10 of the 104 have no
online result, and the notice does not say how they are ranked:
- if they are ranked last, 9 of the 10 are cut, SUSTech-Ok among them;
- if they are kept, the 9 weakest rated teams are cut (online rank worse
  than #1,723).

**Field** (as in the 10-15 table):

| field | linked | median | within #50 / #100 / #200 / #500 | gold / silver+ / medal line | expected golds |
|---|---|---|---|---|---|
| 2026 registered, 10-15 | 78 | 1006 | 1 / 2 / 5 / 10 | 368 / 734 / 1089 | 2.2 |
| 2026 registered, 10-17 | 95 | 998 | 2 / 3 / 7 / 16 | 294 / 708 / 1089 | 3.6 |
| scenario (+ 44 unregistered 2025 schools, top 95) | 95 | 708 | 6 / 12 / 17 / 33 | 71 / 374 / 799 | 10.8 |

- **The strong new teams:**

  | team | online ranks | P(gold) |
  |---|---|---|
  | 香港中文大学（深圳） Mynoghra | #18 / #61 | 89% |
  | 中山大学 SYSU_2333er | #127 / #84 | 32% |
  | 武汉工程大学 | #266 | 4% |
  | 北京航空航天大学 蒟蒻果冻 | #250 / #302 | 4% |
  | 北京科技大学 | #283 / #306 | 3% |
  | 江西农业大学 | #176 / #589 | 3% |

- 23 schools with a 2024/2025 Hong Kong gold or silver have still not
  registered (28 on 10-15). Among them are 上海交通大学, 复旦大学, 清华大学,
  哈尔滨工业大学, 南京大学, 西安交通大学 and 香港科技大学广州.
- The list is still far weaker than the 2024/2025 fields. The scenario still
  puts the gold line at #71, so the forecast is unchanged.

**NUM-R^3:**
- 16th of the 95 linked teams (15 round-1 teams ahead by mean online rank,
  18 by best-round rank), and still 30th in the scenario (of 138).
- It stays in under either reading of the cut.
- Gold / silver / bronze: 1.3% / 34% / 46% (absolute model, unchanged);
  2% / 29% / 49% (field-relative, scenario).

Tests now pin the 10-17 export: 106 / 95 teams, the extra 福建师范大学 team,
and 104 round-1 teams with 9 cut.

## Updated export (2026-10-23 follow-up)

**Data.** `data/icpc_hk_macau_public_teams_20261023.xlsx` is the user's PTA
export of 10-23 (file stamp 22:45). It is now the module's default; the
10-15 and 10-17 CSVs stay as snapshots.
- **PTA changed the format.** It is now an xlsx with English school names,
  no team id, no creation time and no province, plus a new "Online ranking"
  column. The module maps each English school name to its Chinese name and
  province through the PTA CSV exports (2026 online rounds + the two Hong
  Kong lists). All 129 rows map. It takes `created_at` from an earlier Hong
  Kong export with the same line-up; the 24 teams new since 10-17 have none
  and count as registered later.
- 129 teams, all `Pending`: the 106 of 10-17, minus one, plus 24 new. 广西大学
  swapped its line-up (你是我的梦幻之AC → 队名Wa2了, different members). Two
  teams were renamed (成都锦城学院 Random → x x xxx; 西南大学 AFOpointer →
  算法进阶退役指南).
- 6 local teams now: two each from HKU, CUHK and HKUST. Local schools may
  enter two, so they are no longer counted as `extra`. 福建师范大学 BBQ team is
  still the only non-local extra.
- 112 of 129 link (11 unlinked on 10-17). The new unlinked teams are CUHK ×2,
  HKU's second team, 大连理工大学, 山东科技大学 and 昆山杜克大学. Their members are
  on no 2026 online roster of their school.

**The selection rank is the school's combined online rank.** On all 129
rows, the export's "Online ranking" equals the school's 2026 `combined` rank
in `online_schools.csv`. Two teams of one school show the same number (CUHK 8,
HKUST 18, HKU 73, 福建师范大学 176). NUM-R^3 shows 128. So round 1's
"按网络预选赛排名" is a school ranking, not a team ranking. This settles both
open points of 10-17:
- which round counts: neither alone; it is the combined school table;
- teams with no online result of their own: they carry their school's rank.
  SUSTech-Ok is school #9, so it is safe, not cut.

The module now ranks round 1 by school rank, linked or not. The scenario's
top-95 cut also uses school rank: a late 2025 school gets its 2026 combined
rank, or goes last if it has none.

**Round 1 if it closed now:** 123 non-local teams. The second 福建师范大学 team
waits for round 2, so 122 compete for 95 seats and 27 would be cut. The last
team kept is school #284; every team from #286 down is cut. 13 of the 122
have no online result of their own.

**Field** (as in the 10-15 table):

| field | linked | median | within #50 / #100 / #200 / #500 | gold / silver+ / medal line | expected golds |
|---|---|---|---|---|---|
| 2026 registered, 10-17 | 95 | 998 | 2 / 3 / 7 / 16 | 294 / 708 / 1089 | 3.6 |
| 2026 registered, 10-23 | 112 | 957 | 3 / 5 / 11 / 23 | 186 / 679 / 1083 | 5.2 |
| scenario on 10-17, cut by school rank | 89 | – | – | 70 / 368 / 799 | 10.8 |
| scenario on 10-23 (+ 33 unregistered 2025 schools, top 95 by school rank) | 86 | 680 | 5 / 10 / 16 / 32 | 80 / 382 / 816 | 9.1 |

- The strongest new teams: HKUST 喵喵喵幼儿园 (local, #34 / #63: 78% gold),
  HKUST(GZ) BPM 222.22 (#80 / #80: 47%), NUAA (#99 / #183: 20%) and RUC
  (#170 / #162: 13%).
- **Returning strong schools send weaker line-ups than in 2025.** That is
  why the scenario's gold line moved from #70 to #80. Of the 2025 schools
  that registered since 10-17, the four strongest had 2025 Hong Kong teams at
  online #42–#109. Their 2026 line-ups sit at #80–#382 (西安交通大学: #50 →
  #382; HKUST(GZ): #42 → #80; NUAA: #72 → #135; RUC: #109 → #166). The
  scenario assumes every school still missing returns at its 2025 strength.
  If they follow the same pattern, the real gold line will be weaker than
  #80.
- 17 schools with a 2024/2025 Hong Kong gold or silver are still not
  registered (23 on 10-17), among them 上海交通大学, 复旦大学, 清华大学,
  哈尔滨工业大学, 南京大学 and 上海大学. 58 of the 2025 field's linked
  non-local schools have registered (47 on 10-17).
- Pre-existing quirk, not fixed: `hk_gold.is_local` treats the 2025 board's
  "Beijing Normal-Hong Kong Baptist University" (北师香港浸会大学, Zhuhai) as
  local. So "returning" undercounts by one, as does the 2025 non-local
  count. It is registered (school #255), so the scenario is unaffected.

**NUM-R^3** (school #128; online #544 / #349):
- 49 registered round-1 teams have a better school rank. It keeps a round-1
  seat while no more than 45 of the 74 unregistered non-local schools ranked
  above it register by 10-30.
- That looks safe. 34 of those 74 schools played Hong Kong in 2024 or 2025
  (school-level, by English board name; 31 by linked teams only), 40 in
  neither year. Even if all 34 come back, NUM-R^3 is 84th. The 2024 and 2025
  fields held 51 and 56 linked non-local schools from that year's combined
  top 127. NUM-R^3 would need about 95 such schools to be cut.
- **Chance of the round-1 cut** (follow-up question). The 123 non-local
  top-127 schools split into 73 with a 2024/2025 Hong Kong team and 50
  without. Registered so far: 22 + 5 on 10-15, 30 + 8 on 10-17, 39 + 10 on
  10-23, so about 2 a day lately and 4 a day since 10-11. Each school is
  treated as an independent coin with that pace's per-day rate, carried over
  the 7 days to 10-30. The table gives P(46 or more of the 74 register):

  | assumption | P(past-HK) / P(other) | expected new | P(cut) |
  |---|---|---|---|
  | 10-17 → 10-23 pace | 0.24 / 0.06 | 10 | ~0 |
  | 10-11 → 10-23 average pace | 0.36 / 0.12 | 17 | ~0 |
  | 3× the average pace (deadline rush) | 0.74 / 0.32 | 38 | 2.7% |
  | every past-HK school + 20% of the others | 1 / 0.20 | 42 | 9% |
  | every past-HK school + 30% of the others | 1 / 0.30 | 46 | 56% |

  The last two rows need a 100% return of past-HK schools (2024 → 2025 was
  62%), so the estimate is about 1%, under 3% even with a heavy deadline
  rush. It assumes that first teams registered after 10-30 cannot displace
  round-1 seats, and that PTA cuts by the shown rank. It does not cover
  review rejection or travel problems.
- In the scenario it is 73rd of 155 by school rank, and the cut falls at
  school #207.
- By team strength it is 23rd of the 112 linked teams (20 round-1 teams
  ahead by mean online rank).
- Gold / silver / bronze: 1.3% / 34% / 46% (absolute, unchanged);
  2% / 29% / 49% (field-relative, scenario, unchanged at the shown
  precision).

Tests pin the 10-23 export: 129 / 112 teams, 122 round-1 teams with 27 cut,
and "Online ranking" equal to the combined school rank on all 129 rows
(NUM-R^3 128). The early-list check is now "gold line > 2× the 2024/2025
line" (#186 vs #66), down from 3×, because the list is filling in.
`pypinyin` (needed by `arch_b.hk_link`) was missing in this environment and
was installed; `openpyxl` reads the xlsx.

## Updated export (2026-10-26 follow-up)

**Data.** `data/icpc_hk_macau_public_teams_20261026.xlsx`, the user's PTA
export of 10-26 (file stamp 19:53, UTC+8), same xlsx format; now the default.
- 143 teams, all `Pending`: the 129 of 10-23 plus 15 new, minus one.
  山东大学（威海） swapped its line-up (面向样例编程队 → Attack on MilkFrog).
  惠州学院 renamed its team (某科学的超电磁炮 → 沧海一粟). One new team is local:
  澳门大学.
- 124 link. The two new unlinked teams are 新疆大学 and 烟台大学.
- "Online ranking" again equals the combined school rank on all 143 rows.

**Round 1 is filling fast with schools ranked above NUM-R^3.** 10 of the 15
new teams come from schools above #128: 山东大学 #21, 东北大学秦皇岛分校 #22,
东南大学 #24, 西北工业大学 #25, 同济大学 #28, 杭州师范大学 #35, 深圳技术大学
#49, 哈尔滨工业大学（威海） #55, 上海大学 #62 and 大连理工大学盘锦校区 #124. 9
of the 10 had a 2024/2025 Hong Kong team.
- If round 1 closed now: 135 round-1 non-local teams for 95 seats, so 40 are
  cut. The last team kept is school #248 (#284 on 10-23).
- NUM-R^3: 59 registered teams ahead (49 on 10-23), so it is 60th. 35 more
  of the 64 unregistered non-local schools above it can register before it
  is cut; the 36th would cut it.

**Cut risk, now in the module** (`cut_risk`, in `selection[team]`).
`SNAPSHOTS` records when each export was taken: a CSV's last registration,
or an xlsx file name's stamp. Round 1 is assumed to close at the end of
10-30, UTC+8 (`ROUND1_CLOSE`), so 4.17 days are left. The schools above the
team are split into those with a 2024/2025 Hong Kong team (linked, or by the
board's English school name) and the rest. Each group's per-day rate comes
from the last two snapshots. Each school registers independently at its
group's rate, carried to the close at 1× / 2× / 3× that rate, plus a stress
row where every past-Hong Kong school returns. P(cut) is exact (convolved
binomials).

| assumption | P(register): past-HK (25 left) / other (39 left) | expected new | P(cut) |
|---|---|---|---|
| 1× the 10-23 → 10-26 pace | 0.36 / 0.04 | 10.4 | ~0 |
| 2× | 0.59 / 0.07 | 17.5 | ~0 |
| 3× | 0.74 / 0.10 | 22.5 | ~0 |
| every past-HK school, others at 3× | 1 / 0.10 | 29.1 | 0.2% |

- The previous estimate underestimated the pace. From the 10-17 → 10-23
  pace it expected about 4–5 schools above NUM-R^3 by 10-26; 10 came, about
  2× faster. The 2× / 3× rows cover that.
- Even so, the cut needs all 25 remaining past-HK schools plus 11 of the 39
  others. Only 1 of those 39 registered in the last 3 days, and 11 of the
  50 since 10-11. So the chance stays **under 1%**, though the margin shrank
  from 45 to 35.
- Reading `cut_risk` on the 10-23 file reproduces the earlier estimate (need
  46; 10.4 expected at 1×; 1.8% for every past-HK school with others at 3×).
- **Break-even** (`break_even_p_other`). Suppose every one of the 25
  past-HK schools returns, which at even 3× the pace has about a 0.05%
  chance. The cut then needs 11 of the 39 others. That has a 5% chance if
  each registers with probability 0.17, and 50% at 0.27. Their pace so far
  gives 0.04 (last 3 days) or 0.07 (average since 10-11). So it takes 2.6×
  to 4.5× their average pace on top of a full past-HK return.

**User notes (10-26), recorded as given:**
- In past Hong Kong rounds, an oversubscribed non-local list meant an extra
  selection contest. This year it is school rank alone, so weak line-ups
  from well-ranked schools get in, as seen (山东大学 #21 → a #1638 team).
  This conflicts with the 2026-10-01 reading of the 2024/2025 notices
  ("by online rank if oversubscribed"); not re-checked.
- Hong Kong has 10 EC-Final places this year against 1 in 2025 (the 2025
  count was inferred on 2026-10-08). This likely explains both the fast
  registration and the second line-ups from strong schools: places go to
  medal teams in rank order, skipping teams with a member on the mainland
  round-1 list, with at most 3 − x per school. That makes Hong Kong a route
  for a school's lower teams. The 10-place rule was in the 08-28 notice,
  before registration opened on 10-11, so the pace used above already
  reflects it.

**Field** (as in the 10-15 table):

| field | linked | median | within #50 / #100 / #200 / #500 | gold / silver+ / medal line | expected golds |
|---|---|---|---|---|---|
| 2026 registered, 10-23 | 112 | 957 | 3 / 5 / 11 / 23 | 186 / 679 / 1083 | 5.2 |
| 2026 registered, 10-26 | 124 | 947 | 3 / 5 / 12 / 27 | 198 / 658 / 1064 | 5.4 |
| scenario on 10-26 (+ 27 unregistered 2025 schools, top 95 by school rank) | 86 | 652 | 5 / 9 / 16 / 34 | 92 / 382 / 776 | 8.7 |

- Strong schools again sent second line-ups. 山东大学 (school #21) entered a
  #1638 team, 哈工大威海 (#55) a #1607, 东北大学秦皇岛 (#22) a #622, 上海大学
  (#62) a #726. Only 西北工业大学 (#198), 东南大学 (#394) and 同济大学 (#411)
  are stronger than NUM-R^3 (#436). So the scenario's gold line weakened
  again, #80 → #92.
- 12 schools with a 2024/2025 Hong Kong gold or silver are still not
  registered (17 on 10-23): 上海交通大学, 复旦大学, 清华大学, 哈尔滨工业大学,
  中国科学技术大学, 南京大学, 南开大学, 南京邮电大学, 暨南大学, 湘潭大学,
  西安电子科技大学 and 广东以色列理工学院.

**NUM-R^3**:
- 26th of the 124 linked teams by team strength (23 round-1 teams stronger),
  though 60th by school rank.
- Gold / silver / bronze: 1.3% / 34% / 46% (absolute, unchanged);
  3.1% / 28% / 48% (field-relative, scenario).

Tests pin the 10-26 export: 143 / 124 teams, 135 round-1 teams with 40
cut, the rank check on 143 rows, and NUM-R^3's cut risk (59 ahead, need 36
of 64, 9 + 1 registered since 10-23, P(cut) rising with the pace and below
1%).
