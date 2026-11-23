# Hong Kong / Macau teams linked to online results (2026-10-01)

**Why.** `arch_b.online_gold` excludes Hong Kong/Macau. One reason is that
their XCPCIO boards list English (pinyin) team, school and member names, so
the Chinese name/roster links of `link_regionals` never fire. This is step 1
toward a Hong Kong forecast: measure how many of those teams can be tied to an
online-qualifier result.

**Method** (`arch_b.hk_link`, needs `pip install pypinyin`; 0.55.0 used).
Every Chinese roster member in `online_rosters.csv` becomes pinyin spellings:
all readings of each character (heteronyms, capped at 16 per name part),
surname first and last, compound surnames (欧阳, 司马, …) split as two
characters, ü spellings merged (lyu/lv/lu). A regional team links to the roster
team of the same season with the most shared members, if ≥ 2. The school is
ignored for matching and checked afterwards. `scripts/add_pta_rosters.py` now
also writes `data/ec_online/school_names_en.csv`, PTA's 611 English school
names mapped to the ranking's Chinese names (school names only). Teams without
members fall back to mapped school + team name. "(Coach)" entries in the
member lists are dropped.

**Results** (`output/hk_link.md`):

| contest | official | linked | golds linked | school check same / unmapped / different |
|---|---|---|---|---|
| 2022 Hong Kong | 115 | 6 (5%, name only) | 1 / 12 | 6 / 0 / 0 |
| 2023 Macau | 82 | 7 (9%, name only) | 1 / 8 | 7 / 0 / 0 |
| 2024 Hong Kong | 149 | 118 (79%) | 13 / 15 | 102 / 15 / 1 |
| 2025 Hong Kong | 126 | 97 (77%) | 12 / 13 | 91 / 6 / 0 |

- **Correctness.** The one school disagreement is a campus alias: PTA
  北京交通大学（威海） vs the 2024 ranking's 北京交通大学威海校区. The link itself
  is right. Shuffling roster members across teams within a season (3 seeds)
  gives 0–2 chance links per season against ~100 real ones, so about 1% of
  links are false.
- **Ties.** 9 links tie between two roster teams, always at the same school.
  A 3-vs-3 tie is one line-up renamed between the online rounds; a 2-vs-2 tie
  is a line-up split across two online teams. `online_strengths` keys by
  name, so the chosen team carries only one round's rank. This is the known
  cross-round rename issue, not fixed here.
- **Who stays unlinked in 2024/2025** (31 and 29 teams):
  - 10 / 9 local Hong Kong/Macau teams. They mostly did not play the mainland
    online rounds; PolyU and HKU teams that did match only one member.
  - 16 / 16 teams from schools that played online, but at most one member of
    this line-up was on an online roster. These are likely quota entrants, or
    players who skipped the online rounds. Checks on BUPT, Shanghai University
    and USTC found no roster team sharing two surnames, so the pinyin
    conversion is not the cause.
  - 5 / 4 teams from schools with no online team: the Mongolian schools
    (NUM did not enter the online rounds before 2026), plus English names not
    in the PTA table.
- **Unlinked golds:** HKUST2 (local) and USTC "Xitao Village" in 2024; Xiamen
  University of Technology "Nice Nature" (two listed members, one roster hit)
  in 2025.

**Missing data.** The XCPCIO boards of Hong Kong 2022 (`47th/hongkong`) and
Macau 2023 (`48th/macau`) carry **no members** (checked in `team.json`: no
member field). Team names rarely survive from the online rounds: 11 of 12 Hong
Kong 2022 golds and 7 of 8 Macau 2023 golds stay unlinked, including the
mainland winners. No public member list was found: the Macau 2023 contest
sites (cis.um.edu.mo/icpc2023 → 404; icpc2023.scimeeting.cn) show none, and
icpc.global lists no members. Unless such lists turn up, only 2024 and 2025
are usable for a Hong Kong model: about 215 linked teams and 25 linked golds.

**Linked golds' online strength.** Median exp(mean log online rank) is #32.5
(2024) and #50.2 (2025), against 2026 mainland coin-flip lines near #68–76.
This is descriptive only, not yet a fitted line (step 2).

**Not changed:** `arch_b.online_gold` still excludes Hong Kong/Macau, and no
other output was regenerated. `online_rosters.csv` is unchanged by the
`add_pta_rosters.py` rerun.

Run: `python3 scripts/add_pta_rosters.py` (raw PTA exports in `data/`), then
`python3 -m arch_b.hk_link` (on Windows set `PYTHONUTF8=1`). Tests:
`tests/test_hk_link.py`.
