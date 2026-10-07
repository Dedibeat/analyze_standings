# Regional medal forecasts: state and next steps (2026-10-01)

Hand-off for continuing the online-result forecasts in another session. The
details of every result are in `details.md`, in the sections dated 2026-09-27 to 2026-10-01.

## State

Branch `pta-rosters-forecast-rerun`. Modules (all run from the repo root; on
Windows set `PYTHONUTF8=1`; needs `numpy` and `pypinyin`):

| module | what | output |
|---|---|---|
| `arch_b.online_gold` | P(gold) per 2026 mainland site from online strength + slot-rule line | `output/online_gold.md` |
| `arch_b.online_medals` | gold / silver / bronze per 2026 site, Hong Kong included | `output/online_medals.md` |
| `arch_b.hk_link` | links Hong Kong/Macau teams to online results by pinyin members | `output/hk_link.md` |
| `arch_b.hk_gold` | Hong Kong field history, field-prediction and gold backtests, 2026 Hong Kong forecast | `output/hk_gold.md` |

Data: `data/ec_online/` (online rankings, rosters incl. PTA 2025–2026,
regional standings, slot rules, `school_names_en.csv`), the raw PTA exports in
`data/` (input of `scripts/add_pta_rosters.py`; `icpc_2025_online_2_teams.csv`
is a wrong duplicate of the 2026 round-2 file and is not committed), and the
XCPCIO `config.json` cache in `data/ec_online_cache/xcpcio/` (contest dates for
`hk_gold`; the rest of that cache stays git-ignored and is re-downloaded by the
build scripts).

## Ways to improve the predictions (in order of expected value)

**1. Use the real 2026 fields instead of slot-rule fields (biggest, available now).**
Lines from the teams that actually attended beat the slot-rule lines at every
level in both test seasons (Δ log loss vs online-only):

| level | actual field (2024 / 2025) | slot rules (2024 / 2025) |
|---|---|---|
| gold | −0.0013 / −0.0040 | −0.0003 / −0.0010 |
| silver or better | −0.0035 / −0.0110 | +0.0043 / −0.0051 |
| any medal | −0.0100 / −0.0048 | +0.0004 / −0.0018 |

For silver/bronze the slot-rule lines are a wash, which is why the mainland
sites barely differ in `online_medals.md`. PTA's public team lists exist for
Xi'an, Chengdu, Wuhan and Nanjing (deadlines 10-03 to 10-18). The other
sites' lists appear when their registration opens. Registered ≠ attended, so
expect a gain between the two columns.

PTA API (public, no login; header `Accept: application/json;charset=UTF-8`;
fetch pages one at a time and retry empty pages; see the
`icpc-reg-teams-export` skill):
- contests: `GET https://uep.pintia.cn/api/exam_groups/team?t=icpc&season_id=2028382149021446144&active=false`
- exam group ids: Xi'an `2088167199273963520`, Chengdu `2092545392235982848`,
  Wuhan `2099383493947887616`, Nanjing `2101597567202500608`
- teams: `GET /api/teams/public?exam_group_id=<id>&page=<n>&limit=100` (teams + teamUsers)
- schools: `GET /api/schools`
- earlier seasons need a login (`/api/seasons` → `REG_REQUIRE_ADMIN_USER`)

Link registered teams to 2026 online results (school + team name, else ≥ 2
shared members), build each site's line from the registered field
(oracle-style, allowing for teams without an online result), and compare with
the shipped lines.

**2. Update as the season goes (second biggest).** At Hong Kong, "already won
a mainland gold this season" was the strongest signal after online rank. It
cut held-out log loss from 0.1007 to 0.0880 (2024) and from 0.1165 to 0.1119
(2025). The same should hold for later mainland sites (Shenyang, Shanghai,
Nanchang) once Xi'an (10-18) and Chengdu (10-25) finish; this is untested on
the mainland. `scripts/build_tabfm_gold_data.history` already computes
`earlier_best_medal`.

**3. Test members' previous-season results for silver/bronze (cheap).** Only
tested for Hong Kong gold, where it added nothing beyond online rank. Online
rank is noisier in the middle of the field, where silver/bronze are decided.
Relevant for NUM: its 2025 Hong Kong silver is invisible to the model,
because NUM skipped the online rounds in 2023–2025.

**4. Merge teams renamed between online rounds (small).** 84 (2025) and
130 (2026) teams renamed between rounds. `online_strengths` keys by name, so
each counts as two one-round teams. Merging by shared members gives them a
two-round strength.

**Not worth the time:** site history and rating-fit gold bars (no help, or
worse for gold); simulating the Hong Kong field (lost to "same as last year");
more TabFM runs (run-to-run noise; gains vanished once rosters were linked).

**Limits no model fixes:**
- The 2026 Hong Kong registration list (round 1 closes 2026-10-30; not on
  PTA's public list) is the main missing input for Hong Kong.
- The 2022 Hong Kong and 2023 Macau boards have no member names (checked on
  every XCPCIO board), so only 2024–2025 can be linked.
- NUM's 2026 online rank is untested as a predictor for NUM itself.

## Open asks to the user

- The Hong Kong 2026 registration / accepted list, or where it is published.
- A PTA login in the browser, to check for Hong Kong 2024/2025 registration lists.
- Any 2022 Hong Kong / 2023 Macau team lists with members (low priority).
