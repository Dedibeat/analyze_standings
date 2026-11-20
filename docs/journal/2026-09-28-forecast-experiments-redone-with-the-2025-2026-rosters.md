# Forecast experiments redone with the 2025–2026 rosters (2026-09-28)

**Data.** `scripts/add_pta_rosters.py` appends the REVIEWED rows of the four PTA
lists to `data/ec_online/online_rosters.csv` (10,025 rows) and is idempotent.
School aliases are **per season**: the 2025 ranking uses the old names (10
aliases), while the 2026 ranking already uses most new names (only 湖南理工大学 →
湖南理工学院). A single table broke 22 round-1 and 12 round-2 matches in 2026. With the aliases, every
ranked 2025 and 2026 team matches a roster (new test). The raw PTA exports stay
untracked in `data/` because they also carry coach names. The duplicate
`icpc_2025_online_2_teams.csv` is unused.

**Bug fixed: 2026 school names with CJK radicals.** The 2026 school-ranking PDF
prints 西, 民, 长, 门, 青, 齐, 龙, 黄, 车 and 马 as CJK Radicals Supplement code points
(U+2E80–2EFF, e.g. ⻄ U+2EC4). NFKC folds only Kangxi radicals (U+2F00–2FDF), so
the 2026-09-27 note above that NFKC fixes them is wrong. Across the three tables,
84 `online_schools.csv` rows kept the radicals. So **413 of 2,893 2026 online
teams (84 schools, including 西北工业大学, 西安电子科技大学 and 江西师范大学) had no
combined school rank**, and therefore no band slots in any 2026 forecast.
`build_ec_online_data.nfkc` now maps them. The committed CSV was rewritten with
that function (no PDF cache locally), and a test checks that every ranked team's
school has a combined rank. 2022–2025 data are unaffected.

**Online-gold model** (`output/online_gold.md`). 2025 held-out teams linked to
an online result rose from 1,282 to 2,019 (mainland link rate 57% → 90%).

| test | online only | rules line | + quota adjusted (shipped) | school-rank line | oracle line |
|---|---|---|---|---|---|
| 2024 (1,939, unchanged) | 0.1659 | −0.0002 [−0.0006, +0.0001] | −0.0003 [−0.0007, +0.0001] | −0.0001 [−0.0004, +0.0001] | −0.0013 [−0.0022, −0.0006] |
| 2025 (2,019; was 1,282) | 0.1545 | −0.0008 [−0.0017, +0.0001] | −0.0010 [−0.0029, +0.0003] | −0.0011 [−0.0029, +0.0003] | −0.0040 [−0.0078, −0.0003] |

The rules-line gain holds in sign but its 2025 interval now crosses zero. Site
history still hurts (+0.0040). ρ falls from **0.441 to 0.394**: renamed band
teams had been counted as quota entrants, and 12 golds move from quota to band
teams (quota golds 142 → 130; WF 1.47 → 1.36×, host 0.91 → 0.80×). Spearman with
the CF gold bar is −0.479 (was −0.503). **2026 lines** (both fixes): Shenyang
75.7 > Wuhan 73.0 > Xi'an = Shanghai 70.2 > Nanchang 68.6 > Chengdu = Nanjing
68.4, previously 88.7 … 68.6. The radical fix alone moved Shenyang from 88.7 to
75.7, because the dropped strong schools had made every line too easy. A team at
online #100 now has 57/56/55/55/55/54/54% (was 66/63/61/60/60/58/58). The sites
are much closer than before; the order is unchanged. NUM-R^3: 3.3–3.7%.

**Quota model** (`output/quota_teams.md`). The Shanghai validation is unchanged
(151/151, 159/159). 118 of 130 quota golds (91%) come from top-50 schools.
Per-contest quota golds from known quota teams (MAE): pooled 1.75, **by channel
1.49**, by school rank 1.85 (the earlier best), by team rank 2.08. Before
registration, the school-rank model still beats the pooled rate (MAE 1.68 vs
2.27), with ρ_top50 1.26 and ρ_rest 0.05, but it still does not improve
held-out gold prediction.

**TabFM table.** The 2023–2024 rows are unchanged. The 2025 rows gain online
features (NULL `online_x` 1,507 → 770 overall). The 2026 grid adds the four
member-history features: 32 features instead of 28; every team has a roster, 929
have a member from a 2025 regional and 117 a 2025 gold medallist. Local 2025
baselines: online-only improves from 0.1885 to 0.1571, and the rich-feature
logistic gains mostly vanish (pre-registration −0.0017 [−0.0167, +0.0149], was
−0.0201; all −0.0085 [−0.0187, +0.0019]). Those gains had come from standing in
for missing links.

**Managed TabFM run 2** (`test-gemeni-501216`, us-central1, via `bq`; gcloud
already configured). Dataset `tabfm_gold_research` (7-day expiry) was created
and deleted after the run. Eight `AI.PREDICT` jobs: the six backtests, and the
2026 forecast twice (again after the radical fix). Each was dry-run first and
capped at 1 GiB billed. 10 MiB was billed per backtest and 20 MiB per forecast,
≈ 150 MiB with the checks and exports (< $0.001). Ledgers are in
`output/tabfm_gold_predictions/`.

| model | 2024 | 2025 | 2025 linked / unlinked |
|---|---|---|---|
| online_only (logistic) | 0.1705 | 0.1571 | 0.1543 / 0.1828 |
| TabFM, all 45 | −0.0093 [−0.0176, −0.0027] | **−0.0152 [−0.0251, −0.0068]** | 0.1459 / 0.1034 |
| TabFM, 35 pre-registration | −0.0101 [−0.0285, +0.0056] | −0.0042 [−0.0176, +0.0105] | 0.1566 / 0.1174 |
| TabFM, 32 forecast set | **−0.0226 [−0.0335, −0.0133]** | −0.0131 [−0.0259, −0.0012] | 0.1475 / 0.1094 |

**Run-to-run noise.** The 2024 split had byte-identical inputs in both runs
(checked against the uploaded table), so it is a repeat. The all-features call
reproduced (correlation 0.9998, log loss 0.1603 vs 0.1612). **The
pre-registration call did not:** correlation 0.969, mean |Δp| 0.033, max 0.44,
and Δ moved from −0.0218 to −0.0101. The contest bootstrap does not include
this noise, so feature-set rankings from a single managed run are unreliable.
The 32-feature forecast set beating its 35-feature superset in both seasons
fits that noise. In this run, TabFM beats online strength alone with the
all-features and forecast sets in both seasons (intervals exclude zero). That
includes 2025 linked teams, where the old 28-feature set had lost (0.1698 vs
0.1613).

**2026 TabFM forecast** (`output/tabfm_forecast_2026.md`). Within-cap teams
ranked #141–280 average 27% gold (26–29% by site; backtest 20%, actual 18%). The
old run gave 26% with Shanghai at 34%. This run gave 38% before the radical fix,
when 12% of those teams lacked a school rank, a feature that is never missing in
training. At online #100 TabFM and the online-gold model agree within 3 points
at every site (e.g. Shenyang 57/57, Nanjing 56/54, Shanghai 54/55). TabFM barely
separates the sites (top-300 mean 43.4–45.8%) and is higher below #150. Member
history moves it strongly: within the band, teams with no 2025 gold member get
23%, and teams with one or more get 41–48%. NUM-R^3: 3.5–5.0%. **Decision:**
unchanged. The online-gold forecast is the one to use; TabFM is a research
comparison that now agrees with it near #100.

**Tests.** 100 of 101 pass. The failure,
`test_calibration_experiment.test_locked_raw_and_gym_controls_reproduce_documented_loco`
(245.567 vs 245.4277), also fails on the committed state without these changes.

Run: `python3 scripts/add_pta_rosters.py`, then `online_gold`, `quota_teams`,
`build_tabfm_gold_data.py` and `tabfm_gold` as above (on Windows, set
`PYTHONUTF8=1`).
