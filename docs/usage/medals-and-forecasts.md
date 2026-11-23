# Medals and regional forecasts: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## East-Asia medal badges

```bash
./.venv/bin/python -m arch_b.medals
```

Assigns every problem of the 28 medal-awarding **Asia East Continent** contests a
**bronze / silver / gold / platinum / star badge** (weakest → hardest) and reports the
**lowest gold-medal team** per regional. Medal cutoffs are each XCPCIO board's
own official medal counts (the 2022 regionals gave a fixed 35/70/105; later
seasons are about 10% / 30% / 60% cumulative of official teams solving ≥1
problem, which is the fallback for a board without counts). The official onsite
field (star teams excluded) is recovered by matching the QOJ standings to
XCPCIO's official-team data. Each tier's
**medal bar** is the fitted (survival-model) difficulty at which the boundary
cohort's actual solve rate crosses 50% (isotonic regression), and a problem gets
the weakest tier whose bar clears it — badges are monotone in difficulty, and the
medal-badge count per contest ≈ the lowest gold team's solve count. Above the gold
bar, a second crossing at the **champion cohort** (top-5 official teams) splits
**platinum** (champions still solve it at even odds — decides ranking within gold,
88 problems) from **star** (beyond even the champions — the extreme problems,
104, almost all 0–2 official solves). Writes
`output/medal_badges.json`; bars and difficulties are also given in CF points via
the `calibrate` map (gold bar across contests: median ≈ 2540 CF, range ≈
[2316, 2828]). The current badge totals are 85 bronze / 41 silver / 40 gold /
88 platinum / 104 star. See the medal-badge section in `docs/journal/` for why the bars are
empirical crossings rather than Elo performance ratings.

```bash
./.venv/bin/python -m arch_b.export_medal_viewer
```

Builds the interactive **medal viewer** (`output/medal_viewer.html`, self-contained,
no server, light/dark aware) from `medal_badges.json`: a season filter + KPI row,
a dot-range chart of the bronze/silver/gold bars per contest (sorted by gold bar,
click a row to open the contest), a per-contest detail view (problems as lettered
lollipops on the difficulty axis against the three medal-bar thresholds and the
platinum zone, plus a table with band solve rates), and a sortable lowest-gold-team
table. Cutoff teams' performance is shown in CF points (`performance_cf`): the
binary-fit performance the virtual calculator shows for the same standings row.

## Regional medal-cutoff chooser

```bash
./.venv/bin/python -m arch_b.medal_predict
./.venv/bin/python -m arch_b.medal_predict --target bronze
./.venv/bin/python -m arch_b.medal_predict --city Shanghai
./.venv/bin/python -m arch_b.medal_predict --report
```

The default command ranks the eight ordinary 2026 Asia East regional sites by
predicted gold-medal cutoff; `--target` can instead rank for silver or bronze,
and `--cities` compares a custom list. Lower is historically easier. The model
uses only the 25 ordinary 2022–2025 regionals and partially pools each host city
with one overall-mean pseudo-contest. EC Finals do not contaminate ordinary-city
baselines, and one-off hosts no longer get full weight.

Forward validation (train on earlier seasons, predict 2023–2025) gives **148 CF
gold-bar RMSE** and **54.2% correct pair ordering** over 19 contests, on the
medal cutoffs taken from the XCPCIO boards. It was 105 / 47.9% before 2022's
real 35/70/105 medal counts replaced the 10/30/60% rule. The 2022 gold lines
were stricter than later seasons, which raises the error. The pair ordering is
therefore weak in this snapshot; use the city ranking as a rough shortlist, not
a reliable ordering.
The [2026 ICPC Global city list](https://icpc.global/regionals/results) was checked
on 2026-07-27; dates were still absent, and temporal order is weak historically, so
the chooser does not invent positions. All current error bands overlap: use the
ranking as a shortlist alongside travel, quotas, eligibility, and registration
constraints, not as a medal guarantee. `output/medal_predict_viz.html` remains
the descriptive city/time chart; `--report` prints that analysis.

## Online results, slot rules and gold chances

```bash
python3 scripts/build_ec_online_data.py        # official online rankings, rosters, regional results
python3 scripts/add_pta_rosters.py              # + 2025-2026 registration rosters (PTA exports in data/)
python3 -m arch_b.online_gold                   # backtest, rating-fit comparison, 2026 forecast
python3 -m arch_b.online_gold --school 复旦大学  # per-team forecast for a school
```

Independent of the rating fit: gold chance at a regional is modelled from a
team's official online ranks plus a site "rules line" derived from the
hand-encoded slot rules (`data/ec_online/slot_rules.json`), with the golds
won by quota entrants (invitational/WF/host teams, measured at ~0.39× the band
teams' gold rate on earlier seasons) taken out first. Trained on earlier
seasons, online strength alone predicts held-out gold well; the rules line adds
a small gain in both 2024 and 2025 (intervals touch zero), while per-site
history and the rating fit's CF gold bars do not. The same data independently confirm the Shenyang
2024→2025 swing. The fit-vs-online comparison reads the fit's gold line (the
last gold team's performance), which tracks gold difficulty better than the
bar. Its largest disagreements are Xi'an 2023, Hefei 2023 and Xi'an 2025.
Results: `output/online_gold.md`; details in `docs/journal/`.
Hong Kong/Macau are not modelled, but `arch_b.hk_link` (needs `pypinyin`)
links their English-named teams to online results by matching roster members
in pinyin: 79% / 77% of the 2024 / 2025 Hong Kong official teams and 25 of 28
golds (`output/hk_link.md`). The 2022 Hong Kong and 2023 Macau boards list no
members, so those two contests link only 5–9% by name. `arch_b.hk_gold` turns
these links into a Hong Kong gold model: fit on 2024 + 2025 and checked across
the two years, it puts the 2026 coin flip at online #77 (a team at #100: 34%,
range 21–49% for a harder or easier field; mainland sites give 54–57%). A
mainland gold earlier in the same season is the strongest extra signal (most
Hong Kong golds had one). Predicting the field from school attendance does not
beat "same field as last year". Results: `output/hk_gold.md`. `arch_b.online_medals` extends the gold
model to silver and bronze (top 30% / 60% lines, a quota rate per level, Hong
Kong per level): a team at online #300 has about 8% / 48% / 36% gold / silver /
bronze on the mainland, and Hong Kong is the hardest gold but the easiest medal
for weaker teams. Results: `output/online_medals.md`. Ways to improve these forecasts, and the hand-off state: `forecast_next_steps.md`. The 2025–2026 registration rosters (PTA
exports in `data/`: `icpc_2025_online_1_teams.csv`,
`icpc_teams_2025_online_2_fixed.csv`, `icpc_2026_ec_round1_teams.csv`,
`icpc_2026_ec_online_round2_teams.csv`) are added by `add_pta_rosters.py`; they
link 90% of 2025 mainland regional teams to an online result (57% by name
alone). `arch_b.hk_field_2026` links the 2026 Hong Kong registration list
(`data/icpc_hk_macau_public_teams_20261028.xlsx`, the 10-28 export of 144
teams; earlier exports of 10-26 (143), 10-23 (129), 10-17 (106) and 10-15 (88)
stay in `data/`) to the 2026 online rounds by Chinese member names (123 of
144). The export's "Online ranking" is the school's 2026 combined online rank,
so the round-1 cut is by school: 136 round-1 non-local teams for 95 seats,
cut below school #250 if it closed now. NUM-R^3 (school #128) is 60th; it is
cut only if 36 of the 64 unregistered schools above it register by 10-30,
and registration has nearly stopped (1 in, 1 out since 10-26), so the
registration pace (`cut_risk`) puts that at ~0. The list is still weaker than
the 2024/2025 fields (gold line online #198 vs #53–66). With the 2025 schools
that have not registered yet added back, the gold line is #80–92, as strong
schools keep sending weaker line-ups than in 2025; NUM-R^3's chances are unchanged. Results: `output/hk_field_2026.md`.

```bash
python3 scripts/build_quota_evidence.py        # WF/host/invitational/provincial evidence + Shanghai lists
python3 -m arch_b.quota_teams                   # which teams entered each regional on a quota seat, and why
python3 -m arch_b.hk_link                       # Hong Kong/Macau teams linked to online results (pinyin members)
python3 -m arch_b.hk_gold                       # Hong Kong field history, gold backtest and 2026 forecast
python3 -m arch_b.online_medals                 # gold / silver / bronze chances per 2026 site (incl. Hong Kong)
python3 -m arch_b.hk_field_2026                 # 2026 Hong Kong registration list vs online results and past fields
```

```bash
python3 scripts/ecfinal_cutoff.py --project-2026   # how deep a 2026 mainland EC-Final seat reaches (~rank 75)
python3 scripts/ecfinal_chance.py --team '*'       # a school's EC-Final chance per regional and per two-regional plan
python3 scripts/ecfinal_retro.py 2025 7/626 5/890  # chance at each past regional from typed-in online results
```

EC-Final chance per regional: P(rank ≤ the projected qualifying rank) from
online strength plus the members' best previous-season mainland rank. The
history term is held-out better in 2024 and 2025. Hong Kong uses its own
online-only model at the replayed depth of its 10 places. Mainland sites
differ (SD 0.38 log-odds), but no pre-registration feature predicted which
site would be easier, so all mainland sites get one number. A shared
team-season effect combines two regionals. For NUM-R^3: one mainland site
12%, Hong Kong 19%, two mainland sites 22%, mainland + Hong Kong 28%. Details
are in `docs/journal/` (2026-10-08).

Every official team of the 2023–2025 mainland regionals is labelled band
(online rank-band seat) or quota, and each quota team gets the channel that
explains its seat: host, World Finals school, invitational medal, non-mainland,
provincial/local, girls, or unexplained (wildcards, problem setters,
second-round applications). The inferred band seats reproduce Shanghai's
published per-school online seats exactly (2024, 2025), and WF + host explain
68 of the 71 published reward schools. Quota teams hold 39% of seats but win
20% of golds (130 of 648); 91% of those golds come from the extra teams of
top-50 online schools (mostly WF/host seats), and quota teams from schools
ranked below 100 practically never win gold. Results:
`output/quota_teams.md` (per team: `output/quota_teams.csv`).

The school-rank quota model is implemented as the `rules_line_school_rank`
variant of `arch_b.online_gold`. (It was the best quota-gold predictor before
the 2025 rosters; with them, grouping known quota teams by channel does better,
MAE 1.49 vs 1.85.) Top-50 schools are expected to fill 1.39 quota seats per
WF/host entitlement seat and win gold at 1.26× the band rate; all other quota
teams win at 0.05×. Before registration it predicts each contest's quota golds
better than a pooled rate (MAE 1.68 vs 2.27), but it does not improve held-out
gold prediction (worse in 2024, slightly better in 2025). The 2026 forecast therefore keeps the pooled line and shows
the school-rank line beside it.

```bash
python3 scripts/build_tabfm_gold_data.py   # team-level table + BigQuery schema + AI.PREDICT SQL
python3 -m arch_b.tabfm_gold                # local baselines on the same splits
python3 -m arch_b.tabfm_gold --score p.csv  # score TabFM output (row_id,p_gold)
```

`data/tabfm_gold/` holds one row per official 2023–2025 mainland regional
team with 45 pre-contest features in four availability tiers (online, rules,
history, registration). History covers members' previous-season medals and
the team's earlier regionals this season. Labels are `gold` (BOOL, so
`AI.PREDICT` classifies), `medal` and `rank_pct`. `predict.sql` has the four
leave-season-out calls. Local L2-logistic baselines barely beat online strength
alone once the 2025 rosters link 90% of teams: their earlier 2025 gain came
from teams with no online link. Managed TabFM (BigQuery, rerun 2026-09-28,
≈150 MiB billed) beats online strength alone in both seasons with all 45
features (−0.009 in 2024, −0.015 in 2025) and with the 32 forecast features
(−0.023, −0.013), with 95% intervals excluding zero. A repeat on identical 2024
inputs reproduced the all-features call but moved the pre-registration call
from −0.022 to −0.010. Single-run rankings between feature sets are therefore
within run noise. Results: `output/tabfm_gold.md`; predictions and job ledgers
in `output/tabfm_gold_predictions/`.
A pre-season 2026 TabFM forecast (every 2026 online team at every site, 32
features knowable now, including members' 2025 results from the registration
rosters) is in `output/tabfm_forecast_2026.md`. Near online #100 it agrees with
the online-gold model within 3 points. It runs high further down (27% vs a
backtested 20% for #141–280) and barely separates the sites. It is a research
comparison; use `output/online_gold.md` for decisions.

## Anchor teams for non-regional contests (2026-10-11)

```bash
python3 scripts/anchor_teams.py                                    # output/anchor_teams.csv
python3 scripts/anchor_teams.py --board ccpc/12th/harbin --team NUM-R^3  # anchors present / beaten
python3 scripts/anchor_teams.py --overlap [--since 2026-03-01]     # XCPCIO boards by 2026-online overlap
```

To judge a result on CCPC, provincial or invitational boards, the 2,153 teams
that played both 2026 EC online rounds (paired across rounds by PTA roster, so
renamed teams count) are tiered by their predicted chance at one mainland 2026
regional: **gold** anchors have P(gold) ≥ 50% (`arch_b.online_gold`, 88 teams,
about online #1–107), **ecfinal** anchors P(EC-Final seat) ≥ 50%
(`scripts/ecfinal_chance.py`, 83 more, about #112–205). Once 51st-season
regional boards are in `regional_teams.csv`, a team's actual best result
replaces the prediction. `--board` matches anchors on any XCPCIO board (same
school and ≥ 2 shared members, one-to-one, else school + team name) and counts
how many the team beat (`--solved N --penalty M` instead of `--team` scores a virtual run, e.g. a QOJ mirror). `--overlap` lists every board with its share of
2026-online contestants and anchors present; the 2025 CCPC stations held as
many anchors as ICPC regionals, the spring 2026 invitationals and provincials
far fewer. Details in `docs/journal/`.

## Techniques in EC regionals and a 2026 forecast (2026-10-10)

```bash
python scripts/technique_forecast.py   # writes output/technique_forecast.{md,json}
```

Which named techniques (the Gemini 128-id taxonomy, from the Technique Atlas)
appear in the 27 ICPC Asia East regionals of 2022–2025. The script forecasts
the chance of each one at a 2026 regional and tests the forecast on the 2025
regionals and on 8 CCPC contests (2024–2025).

- **56% of problems use no named technique**, and 90% of positions 1–3 need
  none. The tags leave out ambient dp, greedy and math. General categories
  are derived from each technique's taxonomy category. That catches only
  15–16% of DeepSeek's dp and math problems, so dp / greedy / math are
  reported for ICPC only. The CCPC problems have no DeepSeek tags.
- **Model:** each technique's past presence rate, shrunk toward its category's
  rate. It beats a uniform rate on ICPC 2025 (log loss gain .020) and on CCPC
  (.022). Its top-20 list covers 39% / 42% of named problems (a random list
  covers 18%).
- **No site effect and no trend.** The ICPC-vs-CCPC differences do not survive
  multiple-testing correction either.
- **2026, P per regional:** dsu and fenwick 25%, fft 23%, convex hull and
  rolling hash 21%.
- **Hidden cycles or patterns** (`python scripts/technique_patterns.py`;
  report `output/technique_patterns.md`): no season cycle, drift, site style
  or shared ICPC/CCPC fashion. Every regional so far has a graph problem; this
  is suggestive only (Holm p = .14). The solid pattern is slots: greedy and
  implementation problems sit early, while geometry and data structures sit
  late.

Details: `docs/journal/` (2026-10-10 entry).
