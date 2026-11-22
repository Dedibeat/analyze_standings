# Medal cutoffs disagreed with the real boards (diagnosis and fix, 2026-10-05)

**Report.** On the app, a virtual result for Xi'an 2022 (QOJ 1051) of 6 solved
in 357 minutes showed a performance of 2435 CF. The medal page shows a silver
bar of 2282 CF and a silver cutoff team of 6 solved in 565 minutes. The user
knows this result did not earn silver.

**The Contests page is right.** XCPCIO's run data puts 6/357 at official
rank 106. The last silver team, 华中农业大学-吸金石, solved 6 in 352 minutes
and has a calculator performance of 2436. Rank 106 is the first bronze.

**The medal page is wrong.** `medals.py` puts the silver cutoff at official
rank 153 (⌈0.30 × 507⌉), and the board puts it at 105. Two bugs cause this:

1. **Star teams counted as official.** For the 47th/48th seasons,
   `scripts/build_xcpcio_official.py` reads only `group: ["official"]`. Those
   boards mark teams with `"official": 1` / `"unofficial": 1` instead. So the
   whole team list is used, and 3–103 star (打星) teams per contest count as
   official. For Xi'an 2022: 476 official + 46 star teams, so the repo
   counts 507 solving teams where the board has 470.
2. **Assumed 10/30/60 % rule.** Each board's `config.json` has
   `medal.official` with per-tier counts. All five 2022 regionals give
   35/70/105, so the cumulative cutoffs are 35/105/210. The repo's percentages
   give 51/153/305 for Xi'an, 57/169/338 for Jinan, 64/190/379 for Hangzhou,
   46/138/276 for Nanjing and 74/220/440 for Shenyang. So in 2022, medals
   did not follow the 10/30/60 % rule for teams that solved at least one
   problem. For Xi'an, that rule over the board's 470 such official teams
   gives 47/141/282, while the board's 35/105/210 is 7.4/22.3/44.7 %. Other
   sources agree with the board. CPC Finder lists 210 awards for Xi'an 2022
   (35 + 70 + 105). Communication University of China's news
   (ices.cuc.edu.cn, 2022-11-17) reports bronze for 定福庄好果汁大学 at
   Shenyang 2022 and honourable mentions for its other two teams. On the
   board those teams rank 170, 380 and 556 among 704 such official teams.
   Board counts give bronze, none, none; the rule would give silver, bronze,
   none.

Other contests compared with their board configs (scratch script; cutoffs
are cumulative gold/silver/bronze):

| contest | repo n | repo cutoffs | board cutoffs |
|---|---|---|---|
| Hangzhou 2023 | 474 | 48/143/285 | 45/135/270 |
| EC-Final 2023 | 320 | 32/96/192 | 28/84/168 |
| Xi'an 2025 | 215 (399 official; ~50 % name match) | 22/65/129 | 40/120/240 |
| other 2023–2025 | — | within ~1–5 ranks | — |

Hong Kong & Macau 2022 has no `medal` entry. Xi'an 2023 failed to download.

**Affected.** `medal_badges.json` cutoffs, cutoff teams and their
`performance_cf`, medal bars, problem badges, and anything that reads the bars
(`medal_predict`, `online_gold`, `hk_gold`, the medal viewer and the app copy).
The silver bar of 2282 is a problem-difficulty threshold: the difficulty the
cutoff cohort solves at 50 %. It is not a team-performance cutoff. Even so, it
inherits the wrong cohort.

**Fix (user approved; the user confirmed 35/70/105 for Xi'an 2022).**
- `scripts/build_xcpcio_official.py`:
  - A team is official if its `group` contains `official` or its `official`
    flag is set.
  - Each cache entry stores the board's `medal` counts (`config.json`
    `medal.official`). Hong Kong & Macau 2022 has none, so its value is None.
  - Bilingual names: the Chinese text and the "zh(en)" form are keys on their
    own. The English text is used only together with the school. On its own
    it matched the unofficial UCup team DeepSleep (10 solved) at Xi'an 2025.
  - Xi'an 2023 organizations are looked up in `organizations.json`.
  - **QOJ 1784 (Xi'an 2023) was mapped to the wrong board.** It pointed to
    `/icpc/48th/xian-invitational`, the May 2023 invitational (11 problems,
    no medal counts). The correct board is `/icpc/48th/xian`, the October
    regional (14 problems, 41/82/123 medals). This is why only ~10 % of
    its teams matched.
- `medals._is_official`: the display name with parentheses stripped is also a
  key. 2022 rows read "school-school - name (members)" and never matched, for
  example 南方科技大学 and 中山大学 at Xi'an 2022.
- `medals.main`: cutoffs are the board's cumulative counts. 10/30/60 % is used
  only for a board without counts.
- Viewer text and README now describe the board counts.

**Check** (scratch script). For every contest, the official ranking was
rebuilt from the board's `team.json` and `run.json` and compared with the
matched QOJ rows.
- **Official solving-team counts:** 13 contests match the board exactly and
  the other 15 differ by −3 to +4. Before: Xi'an 2022 had 507 vs 470,
  Xi'an 2023 34 vs 367, and Xi'an 2025 215 vs 398.
- **Cutoff teams:** at all 81 compared cutoffs the cutoff team has the
  board's solved count. Hong Kong & Macau 2022 is not compared: its board
  has no counts. In 12 contests the penalty is also identical at all three tiers,
  including Xi'an 2022, Hangzhou 2022 and Xi'an 2025. Elsewhere the penalty
  differs by at most 36 minutes; my own penalty arithmetic and a team
  swapped at a tie account for most of that. The extra rows are existing
  name-only matches of same-named unofficial teams, for example
  "啊对对队 (Beijing Jiaotong University)" at Shenyang 2022.

**Effect** (`medal_badges.json`, old → new):
- **2022 regionals:** cutoffs are 35/105/210 everywhere. For Xi'an the old
  cutoffs were 51/153/305.
- **Xi'an 2022 silver cutoff team:** 为了梦想 (6 solved, 565 min, 2319 CF) →
  华中农业大学-吸金石 (6 solved, 352 min, **2436 CF**). The user's 6 solved
  in 357 min (2435) falls just below.
- **2022 gold bars (CF):** Xi'an 2615 → 2862, Jinan 2724 → 2859,
  Shenyang 2445 → 2753, Hangzhou 2742 → 2704, Nanjing 2653 → 2665.
- **Xi'an 2022 silver bar** stays at 2282, and the bronze bar rises to equal
  it. The cohorts at the old and new silver lines, and at the bronze line,
  all solved the same six problems. The bar is a problem threshold and cannot
  separate them; penalty decided the medal.
- **Xi'an 2023:** n 34 → 368, cutoffs 4/11/21 → 41/123/246, gold bar
  2322 → 2442.
- **Xi'an 2025:** n 215 → 395, cutoffs 22/65/129 → 40/120/240.
- **Badges:** 29 of 358 changed. Gold bar range [2322, 2834] → [2381, 2862],
  median 2549 → 2557.

**Downstream, not rerun:**
- **`medal_predict` reads every gold bar.** Two of its tests now fail
  because their pinned values came from the old 2022 bars. The 2026 chooser's
  three easiest gold cities change from Hong Kong, Shanghai, Shenyang to
  Hong Kong, Shanghai, Nanjing. Shenyang drops to 6th and Xi'an to last.
  Forward-validation gold RMSE rises from below 120 to 148.
- **Why it matters:** the 2022 bars now reflect a stricter gold line (35 of
  416–708 teams, about 5–8 %) than later seasons (about 10 %).
- **Resolved:** the user chose to accept the corrected results and keep
  2022 in the chooser. In `tests/test_medal_predict.py` the expected top
  three is now Hong Kong, Shanghai, Nanjing, and the gold RMSE limit rose
  from 120 to 160. The old limit was 120 against an RMSE of 105.6; the new
  RMSE is 147.9. The README's forward-validation figures are updated:
  RMSE 148 CF and pair ordering 54.2 %, previously 105 and 47.9 %. All
  132 tests pass.
- **`online_gold`** uses the bars only in its `cf_bar_history` backtest
  variant and the `contest_difficulty` table. Because the board link
  changed, it now also gets a Xi'an 2023 bar. Its outputs are stale until
  rerun.
- **`scripts/add_xcpcio_official.py`** still has the old group-only logic and
  the invitational mapping. Its output, `data/tagged_with_official.json`, does
  not exist and nothing reads it.

Run (Windows: `PYTHONUTF8=1`): `python3 scripts/build_xcpcio_official.py`
(delete the cache first to refetch everything; rerun it if a board times
out), then `python3 -m arch_b.medals` and `python3 -m arch_b.export_medal_viewer`.
Copy `output/medal_viewer.html` to `../my-react-app/data/medal_viewer.html`.
