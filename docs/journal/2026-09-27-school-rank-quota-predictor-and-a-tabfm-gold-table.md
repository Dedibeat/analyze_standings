# School-rank quota predictor and a TabFM gold table (2026-09-27)

**Request.** Implement the best quota-gold predictor found above (grouping
quota teams by school combined online rank) and prepare rich data for TabFM
prediction.

## School-rank quota model

The per-contest check used the actual quota teams, which are only known after
registration. A forecast needs the number of quota teams from top-50 schools
*before* registration. Candidates were tested leave-season-out. The best is
the top-50 schools' **WF/host entitlement**: each top-50 school's WF + host
seats, capped by its privileged cap minus band slots (`quota_teams.elite_entitlement`),
times a ratio fit on earlier seasons. Forecast vs actual top-50 quota seats:
MAE 4.0, correlation 0.71. The alternatives did worse: share of planned quota
seats MAE 10.3, headroom 7.5, linear fits 6.5–8.2.

`quota_teams.school_rank_quota_model` (all 2023–2025 data): top-50 quota teams
win gold at **ρ_top50 = 1.38×** the band rate, other quota teams at **ρ_rest =
0.065×**, pooled 0.44; top-50 schools fill **κ = 1.39** quota seats per
entitlement seat. `online_gold.rules_line(..., top50_seats, rho_top50)` gives
band teams `G(1−q)/(1−q + ρ_top50·q50 + ρ_rest·(q−q50))` golds, and reduces to
the pooled formula when `top50_seats = 0`.

- **Quota golds per contest, before registration** (leave-season-out): pooled
  rate × planned quota seats MAE 2.52 (corr 0.44) → school-rank model **1.58**
  (corr 0.25). It fixes season-level errors, but its within-season site
  differences are weak: the entitlement is mostly site-independent within a
  season.
- **Held-out gold prediction** (`rules_line_school_rank` variant, Δ log loss
  vs online-only): 2024 −0.00015 [−0.00038, +0.00010], 2025 −0.00166
  [−0.00415, −0.00003]. Paired against the shipped pooled line: 2024
  **+0.00018 [0.00000, +0.00038] (worse)**, 2025 −0.00014 [−0.00057, +0.00010],
  driven by Xi'an alone. The better quota-gold count does not become better
  gold probabilities: the line's coefficient is small and noisy.
- **Decision:** the 2026 forecast keeps the pooled line (numbers unchanged)
  and prints the school-rank line beside it. The school-rank lines are 0–3
  online ranks deeper (Shenyang 86.9, Wuhan 79.3, Xi'an 73.5, Nanchang 73.0,
  Shanghai 70.9, Chengdu/Nanjing 65.8). The order is the same except that
  Shanghai drops below Nanchang.
- **Evidence added for 2026:** the 51st Xi'an notice lists the 50th WF schools
  (16) and the 2026 host schools (11); 2026 counts WF editions 48–50
  (`quota_evidence.json`). 2023–2025 quota labels are unchanged.

## TabFM gold table (`data/tabfm_gold/`, not run)

`AI.PREDICT` docs, re-read 2026-09-27, now allow **up to 50 feature columns**
(the 2026-09-10 plan quoted 20). A BOOL or STRING label makes it classify and
return per-class probabilities (≤10 classes). Every non-label column of the
training query is a feature, so ids must only appear on the prediction side.

`scripts/build_tabfm_gold_data.py` writes one row per official team of the 18
mainland regionals 2023–2025: 6,473 rows, 648 golds, ids `row_id`/season/site/
school/team. It has 45 features in four tiers, all known before the contest:

- **online (11):** the team's online strength, per-round ranks and solves, link
  method, the school's combined and best-round ranks, and its online depth.
- **rules (15):** band slots; WF/host/invitational/local/non-mainland flags;
  capacity, band seats, quota share, caps, two-slot band, team-count clause;
  rules line (no quota adjustment); top-50 entitlement; calendar position
  (XCPCIO dates).
- **history (9):** members' previous-season regional participation, golds,
  best medal and best rank %; the team's earlier regionals this season
  (strictly earlier dates; matched by ≥2 shared members or the same team name
  at the same school, since Xi'an 2023 has no member names); and the school's
  previous-season golds and medals.
- **registration (10):** band/quota, quota channel, the team's order in its
  school, the school's teams, field size, field linked share, the field's
  top-50 quota teams, the field's 10% strength line, the team's strength rank,
  and x minus the line.

Labels are `gold` (BOOL), `medal` (4 classes) and `rank_pct`. No feature uses
the contest's own results or a label-fitted season constant (ρ, κ). History
signal: a team with ≥1 member who won gold the previous season wins gold
43–60% of the time (base 5.5%); a gold at an earlier regional this season,
60%. `schema.json` is the BigQuery load schema. `predict.sql` has four calls:
all features and the 35 pre-registration features, each on train 2023 →
2024 and train 2023–24 → 2025. Each call returns `row_id, p_gold`.

**Local baselines** (`arch_b.tabfm_gold`; L2 logistic, log-rank features,
missing → 0 + indicator, L2 chosen by leave-one-contest-out CV inside the
training seasons; Δ log loss vs online-only, contest-bootstrap CI):

| model | 2024 (2,094 teams) | 2025 (2,231 teams) | 2025 linked / unlinked |
|---|---|---|---|
| online_only | 0.1705 | 0.1885 | 0.1613 / 0.2254 |
| online + rules line | −0.0000 | −0.0004 [−0.0007, −0.0000] | 0.1606 / 0.2254 |
| pre-registration (35) | −0.0019 [−0.0182, +0.0144] | **−0.0201 [−0.0336, −0.0045]** | 0.1663 / 0.1713 |
| all features (45) | +0.0046 [−0.0062, +0.0165] | −0.0064 [−0.0279, +0.0164] | 0.1764 / 0.1900 |

The rich features help the teams that cannot be linked to an online result
(1,507 of 6,473; 2025 links only 57% because its rosters are on PTA). A linear
model loses a little on linked teams, where online strength already
dominates. The registration tier hurts, likely because it shifts with the
seasons' link rates. These are the comparators a TabFM run must beat.
Expectations for TabFM: it can model the interaction (history matters when
online evidence is weak or missing) that the linear baseline cannot. The
2024 split trains on one season (2,148 rows).

**Before any cloud run:** a smoke query must confirm that NULL features are
accepted and how the BOOL label is spelled in `predicted_gold_probs` (`'true'`
assumed). The existing $10 BigQuery budget protocol (`tabfm_cloud_plan.md`)
applies. Four calls on ~6k rows are far below the earlier 225-call run. No
query was sent.

**Also changed:** `online_gold.link_regionals` returns the linked online key
(`online_key`), which the table builder uses for per-round features.

Run: `python3 scripts/build_quota_evidence.py`, `python3 -m arch_b.online_gold`,
`python3 -m arch_b.quota_teams`, `python3 scripts/build_tabfm_gold_data.py`
(network once for contest dates), `python3 -m arch_b.tabfm_gold [--score FILE]`.
Tests: `tests/test_quota_teams.py`, `tests/test_tabfm_gold.py` (99 pass).

## Managed TabFM run on the gold table (2026-09-27)

Run in `test-gemeni-501216` / `us-central1` from this session (gcloud user
login, revoked afterwards). Dataset `tabfm_gold_research` (7-day expiry) was
created, `teams.csv` loaded with `schema.json`, and then deleted after the run.
A smoke query (Hefei 2023 → 4 Chengdu 2024 rows, NULL features included)
confirmed that NULLs are accepted and that the BOOL label comes back as
`'true'`/`'false'` in `predicted_gold_probs`. Then the four `predict.sql` calls ran;
each was dry-run first and capped at 1 GiB billed. Each billed the 10 MiB
minimum (1.6–2.0 MB processed), 55–88 s, 0.9 M slot-ms in total. Total
≈ 50 MiB billed including the smoke query: well under $0.01 on demand, and
before the 2026-10-30 token pricing. The job ledger is
`output/tabfm_gold_predictions/ledger.json`; predictions are
`output/tabfm_gold_predictions/{all_features,pre_registration}.csv`.

Held-out log loss (Δ vs online-only, contest-bootstrap 95% CI):

| model | 2024 | 2025 | 2024 linked / unlinked | 2025 linked / unlinked |
|---|---|---|---|---|
| online_only (logistic) | 0.1705 | 0.1885 | 0.1649 / 0.2398 | 0.1613 / 0.2254 |
| best logistic (pre-registration) | −0.0019 [−0.018, +0.014] | −0.0201 [−0.034, −0.004] | 0.1669 / 0.1896 | 0.1663 / 0.1713 |
| **TabFM, all 45 features** | −0.0102 [−0.019, −0.004] | **−0.0325 [−0.045, −0.019]** | 0.1605 / 0.1579 | 0.1601 / 0.1506 |
| **TabFM, 35 pre-registration** | **−0.0218 [−0.033, −0.013]** | −0.0239 [−0.041, −0.005] | 0.1507 / 0.1222 | 0.1660 / 0.1628 |

TabFM beats online-only in both held-out seasons with intervals excluding
zero, beats the tuned logistic baselines, and, unlike them, improves on
linked teams as well. That is the online-strength × history interaction a
linear model cannot represent. Neither feature set wins both seasons: the
pre-registration set is best in 2024 (one training season), the full set in
2025. This is one managed-backend run with unexposed settings (checkpoint,
seed, ensemble count) and no repeat, so it is a research result. It does not
replace the shipped `online_gold` model, which predicts from online ranks
alone for 2026 teams. A 2026 use would need 2026 rows (history and rules
features exist before registration) and a pre-registered comparison.

## 2026 TabFM forecast (2026-09-27)

`data/tabfm_gold/forecast_2026.csv` has 20,251 rows: every 2026 online team
(2,893) at each 2026 mainland site, asking "gold chance if this team attends". It
uses 28 features: the 35 pre-registration features minus members' history and
earlier-regional results. Those can't be known before the season: 2026 rosters
are only on PTA, a same-name 2025 regional team exists for only 161 teams, and
no 2026 regional has been held. `forecast_2026.sql` backtests this feature set
on both splits, then trains on all 2023–2025 teams and predicts 2026. It ran
in `test-gemeni-501216`: three queries, 10/10/20 MiB billed. The dataset was
deleted and the login revoked afterwards. Jiangxi provincial boards were added
as Nanchang's local evidence. Nanchang's invitational board uses English school
names and marks official teams `icpc`, so it is recorded as a gap.

**Backtest of the 28-feature set** (Δ log loss vs online-only): 2024 −0.0125
[−0.021, −0.006], 2025 −0.0086 [−0.027, +0.014]. On linked teams, the only kind
in the 2026 grid: 2024 0.156 vs 0.165 (better), **2025 0.170 vs 0.161
(worse)**. Removing member and earlier-regional history removes most of
TabFM's advantage. Held-out calibration was good: teams ranked #141–280
online were predicted 19–21% gold and won 18–19%.

**Shift in the 2026 rows.** The grid contains teams that would never attend.
For online ranks #141–280, the 2026 rows come from schools with 3.6 top-100
teams on average, versus 1.6–1.9 in training. These are strong schools' 5th–10th
teams, which are capped out in reality. TabFM gives that band 34% gold. Keeping
each school's strongest `site_school_cap` teams (the report does this) lowers
it to 26%, still above the backtest. The remaining excess is mostly
Shanghai (34%). Its 2026 rules (1–50 ×2, 51–200 ×1, capacity 336) give a rules
line x of −4.45 and a band profile outside the 2023–2025 range, so TabFM is
extrapolating there.

**Result** (`output/tabfm_forecast_2026.md`, within-cap teams; TabFM /
online-gold model at online #100): Shanghai 64/60, Wuhan 63/63,
Shenyang 62/66, Xi'an 60/61, Nanchang 55/60, Nanjing 54/58, Chengdu 54/58.
Apart from Shanghai, TabFM agrees with the rules model's grouping: easier
Wuhan/Shenyang/Xi'an, harder Nanchang/Nanjing/Chengdu. At #200 the two agree
within ~3 points. TabFM is less certain at the top (#10: 92–97% vs 100%).
NUM-R^3 (online #436): Shanghai 10.7%, Nanchang 5.6%, Shenyang 4.9%, other
sites 2.9–4.0%. The Shanghai figure inherits the Shanghai extrapolation.
**Decision:** the online-gold forecast stays the one to use. The TabFM 2026
table is a research comparison and is marked uncalibrated in its report.
Once 2026 registration lists or early-regional results exist, the full
feature sets (which did beat online-only) become usable for the later sites.
