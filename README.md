# analyze_standings

Estimate ICPC-style **problem difficulties from contest standings** — there is no
native contestant rating to invert (unlike Codeforces), so the ability layer is
built from the standings themselves.

The method (`strat.tex`, long-form `strat_detailed.tex`): a problem's difficulty
is the skill level at which solving it is a coin flip. Abilities and difficulties
define each other, so they are solved either by an alternating fixed point
(**Architecture A**) or by a joint item-response (Rasch) MAP fit
(**Architecture B**); teams recurring across contests link everything onto one
scale.

The [2026-09-05 experiment review](experiment_review.md) records the audit that
found held-out-label leakage, incorrect rank/AUC tie handling, incomplete
uncertainty labels, and participation-key collisions. The concrete correctness
defects were repaired on 2026-09-06; open data/model research limitations remain
listed in the review and in `details.md`.

The [fit and rating improvement strategy](rating_improvement_strategy.md) examines
what could improve the underlying measurement beyond benchmark scores: task
choice and time burden, participation and roster continuity, shared problems
across contests, and targeted collection of missing evidence. It records fresh
diagnostics and proposed experiments, not implemented model changes.

The bounded [calibration residual experiment](calibration_experiment_report.md)
now records a nested 15-contest CF-anchor control: raw affine 246.9061,
gym-shaped affine 245.4277, and ridge residual 229.6269 RMSE. This is a
research-only proxy result. The managed [BigQuery TabFM result](tabfm_bigquery_report.md)
completed the full 185-anchor comparison: TabFM reaches 231.2865 RMSE, improving
on raw/gym but not the frozen DE control (226.5661), so no shipped calibration or
rating artifact changed. Reproduce the controls with
`./.venv/bin/python -m arch_b.calibration_experiment --baseline-only`.
The optional TabFM route uses the pinned `TABFM_CHECKPOINT_DIR` interface
documented in that report; it does not silently download a checkpoint, and must
be intentionally run in an isolated process.

The [BigQuery and Google Cloud TabFM plan](tabfm_cloud_plan.md) specifies the
requested **$10 total limit** and native managed TabFM through BigQuery
`AI.PREDICT`, with experiment tables and SQL scoring. It compares against DET
and the newer DE control, limits query spending, and preserves separate result
artifacts. No VM or GPU is needed; the executed result is linked above.

The frozen [feature-group ablation](calibration_ablation_report.md) separates
estimator disagreement (D), non-time evidence (E), and extra calibration timing
features (T) on the same reused anchors. DE is the strongest development
candidate (226.5661 LOCO / 225.7640 LORO RMSE), but this is not fresh
confirmation or a production-promotion decision. Reproduce it with
`./.venv/bin/python -m arch_b.calibration_ablation` and inspect the separate
non-OOF transfer diagnostic with
`./.venv/bin/python -m arch_b.calibration_ablation_transfer`.

The [2026-09-10 prediction audit](calibration_audit_report.md) verifies cached
source/feature consistency and reruns nested DE calibration after each anchor
contest is removed. DE beats both controls in all 15 deletions, but 1,840 of
3,159 full-refit appearances exceed at least one training-feature range
(1,610 on field size). The saved research predictions now include source links
and feature-support flags. Reproduce with
`./.venv/bin/python -m arch_b.calibration_audit`; production ratings are unchanged.

The [TabFM/DE audit and shipped-fit update preparation](shipped_fit_update_plan.md)
replays all 225 managed calls and DE's nested selection, and stages a full
per-problem comparison in `output/shipped_fit_audit.json`. DE improves development
RMSE by 18.86 points over the shipped gym calibration, but would move 1,737
ratings by at least 100 points; 1,840 appearances exceed an anchor feature range.
The plan identifies exporter, ability/medal-map, uncertainty and confirmation
requirements before a default update. Reproduce offline with
`./.venv/bin/python -m arch_b.shipped_fit_audit` (requires the original local
managed-response archive). Production outputs remain unchanged.

The [mechanism explanation and future plan](calibration_interpretation.md)
decomposes DE into an estimator blend and evidence correction. It shows that
conditional SE largely encodes solve count, and that unusual combinations of
disagreement and solve rate explain much of the largest correction. The small
DE–TabFM gap remains uncertain across contests. Proposed next work isolates
these mechanisms and obtains fresh transfer evidence before promotion.

The [experiment roadmap](experiment_roadmap.md) records the remaining audits,
fresh-confirmation requirements, and longer-term rating research. Its correction
and anchor-contest influence audits now have the bounded results linked above;
the deferred local-checkpoint TabFM comparison remains separate from the completed
managed pilot.

## Run

Requires Python 3 + numpy. A project venv is used:

```bash
python3 -m venv .venv
./.venv/bin/pip install numpy
./.venv/bin/python -m arch_a.run
```

This writes `output/problem_ratings.json` (one record per problem with its
estimated `difficulty` on a Codeforces-like [800, 4000] scale) and prints
verification stats. Standing rows that solved no problems are dropped before the
fit (see the zero-solve decision in `details.md`). QOJ omits unattempted problem
labels; the loader treats those cells as censored non-solves rather than dropping
them from the likelihood. If a standings row contains a label absent from that
contest's parsed problem list, that unknown solve is ignored for row retention
because its problem metadata is unavailable.

`run` fits the full `data/tagged.json` **anchored to the Universal Cup scale**:
it first fits the UCup seasons (`ucup_s3` + `ucup_s4`) on their own, then uses
each UCup team's ability as that team's prior when fitting tagged, so the two
sit on one comparable scale (see `arch_a/anchor.py`). Without the anchor the
tagged fit floats ~440 pts above UCup for the 5.8k shared teams; anchoring cuts
that scale gap roughly in half. Tune the pull with `estimate_anchored(anchor_weight=…)`.

### Architecture B (joint item-response model)

```bash
./.venv/bin/python -m arch_b.run
```

Fits the joint **Rasch** item-response model by MAP (`strat.tex` §4): each solve
is a Bernoulli draw on `sigma((θ_t − b_p)/s)`, and the shared `θ_t` links contests
automatically. Writes `output/problem_ratings_b.json` — same record format plus a
`difficulty_se` (Laplace standard error) per problem, a distinct file so
Architecture A's output is left untouched. Reuses arch_a's data layer and fits
**one joint MAP** over tagged.json, the supplemental standings, and the Universal
Cup seasons (`arch_b.joint`) — the two-phase UCup prior was retired on
2026-08-21 after it measured as a no-op here; tune the prior with
`estimate_joint(sigma_theta=…, sigma_b=…)`
(looser → wider scale but more easy problems pinned to the floor). The Gaussian
prior keeps solved-by-none/all problems finite, so no boundary smoothing is
needed. See `details.md` for the Rasch-vs-2PL scope and the shrinkage-vs-arch_a
comparison.

Architecture B also loads 71 standings-only supplemental QOJ contests:
14 Asia East ICPC regionals from 2020–2021 and 57 Petrozavodsk camp contests
from 2022–2026. They add cross-contest team evidence without using statements
or editorials. The current joint fit has calibrated LOCO RMSE 245.4 CF
points (244.2 was the earlier two-phase fit; 261.6 also predates the
omitted-non-attempt-cell correction).

Add `--survival` to fit the **solve-time survival model** (`strat.tex` §5) instead,
which also uses *when* each problem was solved (writes
`output/problem_ratings_survival.json`):

```bash
./.venv/bin/python -m arch_b.run --survival
```

It distinguishes problems with identical solve counts that the binary model cannot
(e.g. it correctly separates two APAC problems both solved by 76 teams), and gives
tighter uncertainty.

Both `run` modes drop short-format contests (warm-ups / 3 h rounds) by default
(`MIN_SOLVE_HOURS`). `load` also offers `season_key=True` to separate recurring
rosters by ICPC season — but `arch_b.season_experiment` shows it doesn't improve
difficulty estimates, so it stays off; run that module to reproduce the comparison.

Validate any model against independent opinions from editorial-backed LLM labels,
official Codeforces ratings, Kattis, fixed-ability Codeforces gym mirrors, and
AOJ practice statistics:

```bash
./.venv/bin/python -m arch_b.validate           # LLM buckets, all models
./.venv/bin/python -m arch_b.gym_difficulty     # fixed-θ difficulty from CF gym mirrors
./.venv/bin/python -m arch_b.aoj --refresh      # rebuild the matched AOJ validation artifact
./.venv/bin/python -m arch_b.external_validate  # Codeforces + Kattis + gym + AOJ, all models
./.venv/bin/python -m arch_b.predict_eval       # held-out response imputation (binary vs survival)
./.venv/bin/python -m arch_b.calibrate     # affine map to Codeforces points
./.venv/bin/python -m arch_b.metric        # THE optimization metric: LOCO CF-point RMSE + guards
./.venv/bin/python -m arch_b.data_influence # explain supplemental-contest effects
```

All three architectures agree closely with both opinions. After the full-cell mask
correction, the LLM-bucket Spearman values are +0.908 (arch A), +0.908 (binary),
and +0.911 (survival); the pooled CF values are +0.913, +0.937, and +0.942.
On the corrected joint response-group imputation check, binary scores AUC 0.9727
versus survival 0.9674; this check favours binary, while the survival model remains
the shipped choice because it uses solve-time information and leads the broader
external CF/Kattis validation. This is not a future-contest forecast because row
retention occurs before the split.

`gym_difficulty` turns the scraped CF **gym-mirror** attempts
(`data/cf_gym_mirrors.json` — real timed attempts whose solvers carry their own
time-accurate Codeforces rating, trust-weighted by rated-contest count) into an
independent per-problem difficulty on the CF scale, fit with ability *fixed* at
each solver's rating. It is the third yardstick in `external_validate` and the
first external numeric anchor for **Asia East Continent** (230 problems), where
all three models validate at +0.95–0.98. `--certify` checks the instrument itself
(vs official CF ratings: Spearman +0.976, affine slope ≈1.2).

`arch_b.aoj --refresh` fetches the live AOJ problem catalog and writes
`data/aoj_difficulty.json` with source time, raw IDs, match method, accepted
matches, and rejected candidates. A match is used only when its normalized title
is unique in both datasets and at least three problems corroborate the same
contest. The current artifact accepts 45 problems from four Japan regionals and
keeps 26 isolated title matches rejected. `external_validate` compares
`submissions / solvedUser` only by within-contest rank; AOJ never enters training.

### The optimization metric

`arch_b.metric` is the single number model improvements are judged by:
**calibrated leave-one-contest-out RMSE in CF points** against the official
ratings of all 15 CF-mirrored contests (185 anchor problems — every rated
mirror the dataset has; an exhaustive sweep found no more). It refits the
survival model from source, applies the locked shipped gym shape, and prints
`METRIC calibrated_loco_cf_rmse=…` as its last line (current baseline
**245.4** for the joint fit; lower is better). It exits nonzero if any external
guard regresses (gym
Asia-East-Continent / gym pooled / Kattis / AOJ within-contest Spearman,
solve-count sanity) or if raw affine LOCO rises above 251.9 (the corrected 246.9
baseline plus five points). Anchor coverage and every metric must also be finite.
`program.md` at the
repo root is the matching
instruction file for auto-research loops: verify contract, what code is fair
game, hard anti-gaming rules, and a prioritized idea list. A 2026-07-03 auto-research campaign (Claude Fable 5 + DeepSeek v4 Pro, 25
iterations) found that the only repeatable improvements were data-side identity
fixes (−2.2 RMSE to 288.0, AUC-corroborated). That finite search predates major
data/model corrections and does not establish that model improvements are
exhausted (see the current review). A 2026-07-23 data-side campaign added the supplemental standings
and fixed an over-broad World Finals affiliation join; original-cell held-out
AUC also improved 0.885761 → 0.886000.
Those campaign numbers predate the full-cell mask correction; the corrected
row-by-row retest of `autoresearch/loop-260723-1333/classic-results.tsv` is
recorded in `details.md`. The deeper [supplemental-contest influence audit](data_influence.md)
finds that the corrected 1.065-CF gain is almost entirely Petroz-to-Northern-
Eurasia transfer, is not corroborated by the current original-cell holdout, and
does not justify a metric-selected contest subset. A strict no-link control
degrades LOCO from 244.2 to 333.5, confirming that shared-team normalization is
essential even though merely maximizing the number of new links is not useful.

### Calibrated Codeforces-point ratings

`arch_b.calibrate` maps the (relative) survival scale to CF points in two legs: a
monotone **shape** learned from the ~660 gym-mirror difficulties (nearly CF-native
in scale; it cannot reorder our problems) and an **affine** leg fit on the official
CF ratings of all 15 rated mirror contests (185 anchor problems, auto-mapped).
Current saved joint-fit leave-one-contest-out: shaped RMSE **245.43** vs
plain-affine **246.91**. The paired contest-bootstrap difference includes zero
([-9.63, +6.16] CF); the earlier 266 vs 288 improvement is historical. Writes
`output/problem_ratings_calibrated.json` with `difficulty_cf`, conditional
`difficulty_cf_fit_se`, `difficulty_cf_level_sd`, and their
`difficulty_cf_partial_se` quadrature. The partial SE is deliberately not called
a total: it is not a calibrated CF prediction interval (see the current review).

### Anchoring audit (2026-08-21)

A historical review of every mechanism that pins the scale — the UCup prior, the gym shape,
the CF affine leg, and the LLM opinions — is recorded in the anchoring-audit
section of `details.md`. These measurements precede the implemented structural
shift below; the second-scale bug and dense-memory blocker have since been resolved:

- The Phase-1 **UCup prior-mean anchor is a no-op in Architecture B** (removing
  it moves difficulties by mean −3.6 with sd 0.96 and leaves the metric at
  244.3). Cross-contest normalization is carried by the shared union-find and
  the joint likelihood, not by the prior.
- `output/ucup_only_ratings.json` is **~90 CF points too low**: it rates the
  52 UCup-only contests on the Phase-1 fit but calibrates them with a map fit on
  the tagged-scale fit. Measured on the 305 problems both fits rate,
  `b_ucup ≈ 0.959·b_tagged + 36`.
- Fitting **UCup as ordinary data in one joint fit** costs +1.1 CF points
  (245.4 vs 244.3, all guards unchanged) and puts 684 more problems on the
  shipped scale. It is currently blocked by the dense `rows × n_problems`
  arrays in `arch_a.load` (~11 GB peak at joint size, ~0.35% density).
- **Per-region levels are not identified.** Against the gym yardstick
  Europe − Asia East = +117 ± 42; against the LLM bucket labels the same pair is
  −134 ± 30. Both referees rank well within region and disagree in sign on the
  level, so a per-region offset cannot be learned from either alone.
- The **LLM pairwise instrument pairs only within a contest** (185 problems /
  15 mirrors), i.e. on the axis the fit already gets right. Statements cover
  100% of tagged and UCup problems in every region, so a cross-contest schedule
  is the one anchor candidate with full regional reach — and it can be validated
  against the known per-contest CF offsets before being trusted.
- Only **92 of 207 fitted contests** have any external anchor, and all 185 CF
  anchor problems come from three regions.

The proposed structural shift (sparse data layer → one joint fit → cross-contest
LLM pairwise → hierarchical per-contest/per-region calibration → ability-side CF
anchoring) is written up at the end of `details.md`.

### Structural shift implemented (2026-08-21)

The five steps the audit proposed, as built and measured (baseline metric 244.3):

1. **Sparse data layer.** `arch_a.load` now stores observed cells in COO form
   (`obs_row`/`obs_prob`/`obs_y`/`obs_tau`/`obs_wrong` plus `solved_count`),
   replacing dense `n_rows x n_problems` matrices that were 99.65% empty. Peak
   RSS for `arch_b.run --survival` drops **6,177 MB -> 696 MB** with the metric
   bit-identical at 244.3.
2. **One fit, one scale.** `arch_b/anchor.py` -> `arch_b/joint.py`;
   `estimate_anchored` -> `estimate_joint`. The Universal Cup is ordinary fit
   data and the two-phase prior is gone (`arch_a.anchor` keeps its anchor, which
   there does work). Metric 244.3 -> **245.4**, inside the noise floor; rated
   problems 2,475 -> **3,159**; the UCup-only export now matches
   `problem_ratings_calibrated.json` to within rounding instead of sitting ~79
   CF points low.
3. **Cross-contest LLM comparisons** — `llm_crosscontest.py`, see below.
4. **Hierarchical calibration** (`arch_b/hier_calibrate.py`): `cf = A*f(b) + B +
   u_contest + v_region`, partially pooled. It measures **tau_contest = 72.4**
   and **tau_region = 12.0** CF points. Only three regions inform the latter
   estimate; it cannot establish absence of bias in unanchored regions or prove
   that the gym/LLM disagreement is a referee artifact. LOCO does not improve
   (245.4 vs 248.3), so the
   shipped map stays the plain affine. The exported uncertainty components are
   the conditional fit SE (`difficulty_cf_fit_se`) and calibration level SD
   (`difficulty_cf_level_sd`) plus their explicitly partial quadrature; these are
   not advertised as a calibrated prediction interval.
5. **Ability-side CF anchoring** (`arch_b/cf_prior.py`): the CPHoF participant
   ratings as a time-accurate, roster-complete, leak-free prior on team ability.
   Measured **inert** (57 anchored identities, metric moves <= 0.2), so it is
   off by default — but `--validate` gives the repo's first external check of the
   *ability* axis: fitted theta vs CF team ability Pearson **+0.752**, with an
   implied compression of 2.86x against the 1.63x the difficulty map applies.

### Cross-contest LLM difficulty comparisons

```bash
python llm_crosscontest.py prepare --scope mirrors --matches 6
python llm_crosscontest.py count   --project <gcp-project>
python llm_crosscontest.py run     --project <gcp-project>
python llm_crosscontest.py analyse
```

`llm_survival.py` only ever pairs problems **inside one contest**, which is the
axis the fit already gets right — hence its flat fusion result. This module
pairs problems **across** contests, the axis nothing else can measure, and
validates the instrument first on the 15 CF-mirrored contests where the true
cross-contest levels are known. Partners are drawn uniformly from other contests
(never using our difficulty, a CF rating, or any other target proxy), both A/B
orientations are sent, and `bt_scores` fits Bradley-Terry by coordinate Newton in
O(edges) per sweep so the graph can be far larger than `llm_survival.bt_fit`'s
dense Hessian allows.

**Corrected 2026-09-06:** `analyse` now constructs its held-out adjustment only
from the contest's BT-minus-survival feature; held-out CF labels are scoring-only,
with mutation invariance covered by a regression test. Reanalysis of the saved
responses scores 245.43 plain versus **246.78 adjusted**, so the LLM feature does
not improve LOCO and the wider paid run remains unjustified.

### Participant Codeforces ratings (research finding)

A 2026-07-21 feasibility test matched exactly one Codeforces handle for 1,168 of
25,656 distinct standing member names (4.6%); only 2.3% of roster rows had every
member resolved.  The official Codeforces API is the right rating/history source,
while CLIST is useful only as secondary identity evidence.  The proposed fit
improvement is a confidence-weighted, time-accurate CF prior on team ability,
starting with fully resolved rosters so missing members are not silently treated
as weak.

The conservative source layer is now implemented:

```bash
./.venv/bin/python scripts/cphof_cf_participants.py --refresh
```

It caches CPHoF's 2021–2025 World Finals rosters/profile pages, accepts only
explicit CPHoF Codeforces profile links, and caches each handle's complete
official `user.rating` history.  `data/cphof_cf_participants.json` contains 346
explicit person→handle identities; requiring a second matching roster member
corroborates 285 people across 1,582 standing-member appearances and leaves 347
unique standing rows with handles for the full roster.  Exact-name-only
appearances and stale/missing handles remain in the artifact as rejected or
review-only evidence.

This data is consumed by the **opt-in** `arch_b.cf_prior` hook described above;
the default fit leaves it off. CPHoF supplies World Finals
calendar dates but no start times, so the artifact includes 470 pre-event rating
observations using a conservative 00:00 UTC cutoff that excludes same-date
rating changes.  Most `tagged.json` regionals have only a year, so the
collector retains full histories but does not invent regional timestamps or
derive priors from them.  See
[`cf_participant_ratings.md`](cf_participant_ratings.md).

### East-Asia medal badges

```bash
./.venv/bin/python -m arch_b.medals
```

Assigns every problem of the 28 medal-awarding **Asia East Continent** contests a
**bronze / silver / gold / platinum / star badge** (weakest → hardest) and reports the
**lowest gold-medal team** per regional. Medals go by cumulative percentile of
official teams solving ≥1 problem (gold 10%, silver 30%, bronze 60%); the official
onsite field is recovered by matching the QOJ standings to XCPCIO's official-team
data. Each tier's
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
88 platinum / 104 star. See the medal-badge section in `details.md` for why the bars are
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
table.

### Regional medal-cutoff chooser

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

Forward validation (train on earlier seasons, predict 2023–2025) gives **105 CF
gold-bar RMSE** and **47.9% correct pair ordering** over 19 contests after the
full-cell rating correction. The pair ordering is therefore weak in this
snapshot; use the city ranking as a rough shortlist, not a reliable ordering.
The [2026 ICPC Global city list](https://icpc.global/regionals/results) was checked
on 2026-07-27; dates were still absent, and temporal order is weak historically, so
the chooser does not invent positions. All current error bands overlap: use the
ranking as a shortlist alongside travel, quotas, eligibility, and registration
constraints, not as a medal guarantee. `output/medal_predict_viz.html` remains
the descriptive city/time chart; `--report` prints that analysis.

### Online results, slot rules and gold chances

```bash
python3 scripts/build_ec_online_data.py        # official online rankings, rosters, regional results
python3 -m arch_b.online_gold                   # backtest, rating-fit comparison, 2026 forecast
python3 -m arch_b.online_gold --school 复旦大学  # per-team forecast for a school
```

Independent of the rating fit: gold chance at a regional is modelled from a
team's official online ranks plus a site "rules line" derived from the
hand-encoded slot rules (`data/ec_online/slot_rules.json`), with the golds
won by quota entrants (invitational/WF/host teams, measured at ~0.44× the band
teams' gold rate on earlier seasons) taken out first. Trained on earlier
seasons, online strength alone predicts held-out gold well; the rules line adds
a small consistent gain (2024 and 2025), while per-site history and the rating
fit's CF gold bars do not. The same data independently confirm the Shenyang
2024→2025 swing and flag Kunming/Nanjing 2024 as the largest fit-vs-online
disagreements. Results: `output/online_gold.md`; details in `details.md`.
Hong Kong/Macau are not modelled, and 2025–2026 rosters (only on PTA) are
missing.

```bash
python3 scripts/build_quota_evidence.py        # WF/host/invitational/provincial evidence + Shanghai lists
python3 -m arch_b.quota_teams                   # which teams entered each regional on a quota seat, and why
```

Every official team of the 2023–2025 mainland regionals is labelled band
(online rank-band seat) or quota, and each quota team gets the channel that
explains its seat: host, World Finals school, invitational medal, non-mainland,
provincial/local, girls, or unexplained (wildcards, problem setters,
second-round applications). The inferred band seats reproduce Shanghai's
published per-school online seats exactly (2024, 2025), and WF + host explain
68 of the 71 published reward schools. Quota teams hold 39% of seats but win
22% of golds (142 of 648); 89% of those golds come from the extra teams of
top-50 online schools (mostly WF/host seats), and quota teams from schools
ranked below 100 practically never win gold. Results:
`output/quota_teams.md` (per team: `output/quota_teams.csv`).

The best quota-gold predictor, school rank, is implemented as the
`rules_line_school_rank` variant of `arch_b.online_gold`. Top-50 schools are
expected to fill 1.39 quota seats per WF/host entitlement seat and win gold at
1.38× the band rate; all other quota teams win at 0.07×. Before registration it
predicts each contest's quota golds better than a pooled rate (MAE 1.58 vs
2.52), but it does not improve held-out gold prediction (worse in 2024, slightly
better in 2025). The 2026 forecast therefore keeps the pooled line and shows
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
leave-season-out calls. Local L2-logistic baselines:
adding online, rules and history features beats online strength alone in 2025
(−0.020 log loss) and ties in 2024, mostly through teams with no online link.
Managed TabFM (BigQuery, 2026-09-27, ≈50 MiB billed) beats all of them in both
seasons: −0.022 (2024, pre-registration features) and −0.033 (2025, all
features) log loss vs online strength alone, with 95% intervals excluding zero,
and it also improves on linked teams. Results: `output/tabfm_gold.md`; predictions
and job ledger in `output/tabfm_gold_predictions/`.
A pre-season 2026 TabFM forecast (every 2026 online team at every site, 28
features knowable now) is in `output/tabfm_forecast_2026.md`. Without member and
earlier-regional history it no longer beats online strength on linked teams,
and it runs high for 2026 (especially Shanghai, whose rules fall outside the
training range). It is a research comparison; use `output/online_gold.md` for
decisions.

### Interactive viewer

```bash
./.venv/bin/python -m arch_a.export_viewer
```

Writes a self-contained `output/ratings_viewer.html` from the same UCup-anchored
fit as `run` — the full `tagged.json`, 146 unique contests after deduplication
(Architecture A keeps its two-phase anchor, which measurably works there) —
just open it in a browser (no server needed). The contest picker is grouped by year
(newest first); the header shows the year and a link to the qoj contest. Pick a
contest to see its problems ranked by difficulty and its teams with both their
overall ability `θ` and their **performance** in that contest (the rating implied
by their final rank, eq. perf) — the gap shows who over- or under-performed. Click
any column to sort, filter teams by name/member/affiliation, and use the URL hash
(`#<contest_id>`) to share a link straight to a contest.

To view just the UCup-only anchor fit (Phase 1: seasons s3 + s4, 76 contests)
instead of the full anchored tagged fit:

```bash
./.venv/bin/python -m arch_a.export_viewer --ucup
```

This writes a separate `output/ratings_viewer_ucup.html` (the main viewer is
left untouched).

#### Architecture B viewer (Codeforces-calibrated)

```bash
./.venv/bin/python -m arch_b.export_viewer
```

Writes `output/ratings_viewer_b.html` from the **survival** fit, with every
difficulty and ability mapped to **Codeforces-equivalent points** and each problem
difficulty shown with its Laplace standard error (±SE). This is the recommended
viewer. It is published live via GitHub Pages:

**<https://dedibeat.github.io/analyze_standings/output/ratings_viewer_b.html>**

(The Architecture A viewer is also live at `.../output/ratings_viewer.html`.)

### Virtual contest performance calculator

```bash
./.venv/bin/python -m arch_b.export_virtual_calc
```

Writes `output/virtual_calc.html`: pick one of the 241 fitted contests (132
tagged.json regionals + all 57 Petrozavodsk camp contests + 52 Universal Cup
rounds not already in tagged.json, rated on their own Phase-1 UCup-only fit)
by name from the year-grouped dropdown, or jump straight to one by its qoj
**contest id** in the id box. Enter your team's solved count and penalty (minutes) from a
virtual (out-of-window) run — standard ICPC scoring, the same two numbers any
real team's standings line carries — and see the Codeforces-equivalent
performance rating you'd have earned. Method: standard ICPC tie-break (most
solved, then lowest penalty) inserts your team into that contest's real final
standings to get a hypothetical rank, then the same Elo rank-inversion
primitive `arch_b.medals` uses for every real team's `performance_elo`
converts that rank plus the real field's fitted abilities into a rating. The
standings table shows every real team's own calibrated performance
alongside yours for direct comparison. The CF-points mapping is the same
gym-shape + affine calibration as `arch_b.calibrate`, sampled into a dense
lookup table at export time so the browser doesn't need to re-fit it.
Self-contained, no server; recomputes live as you edit solved/penalty.

### Contest-linking graph

```bash
./.venv/bin/python -m arch_a.export_graph
```

Writes a self-contained `output/contest_graph.html`: each node is a contest, an
edge joins contests that share team identities (the links that put every contest
on one scale). Toggle between the current roster/id keying and a year-appended
keying to see that adding the season to the team key fragments the single scale
into per-year islands. Runs on the 5-season `data/tagged.json`.

Module self-checks:

```bash
./.venv/bin/python -m arch_a.elo         # worked-example unit tests
./.venv/bin/python -m arch_a.load        # data summary
./.venv/bin/python -m arch_a.fixedpoint  # convergence trace
./.venv/bin/python -m arch_b.model       # MAP convergence trace
./.venv/bin/python -m arch_b.survival    # survival-model convergence trace
```

## Layout

- `data/tagged.json` — full input standings (146 contests); `data/ucup_s3.json`,
  `data/ucup_s4.json` — the Universal Cup seasons used to anchor the scale.
- `data/icpc_2020_2021.json` — 14 older Asia East ICPC standings;
  `data/petroz_2022_2026.json` — 57 recent Petrozavodsk camp standings. Both are
  QOJ standings-only supplements consumed by Architecture B.
- `data/aoj_difficulty.json` — provenance-rich AOJ validation matches (practice
  statistics; never a fit input).
- `arch_a/` — Architecture A implementation (`load`, `elo`, `fixedpoint`,
  `anchor`, `run`), plus `export_viewer` + `viewer_template.html` for the viewer.
- `arch_b/` — Architecture B implementation (`model` binary Rasch, `survival`
  solve-time model, `joint` (one MAP over tagged + supplemental + Universal Cup;
  replaced the two-phase `anchor`), `cf_prior` opt-in ability anchor +
  ability-axis validation, `hier_calibrate` per-contest/per-region calibration
  levels, `run`, `validate`, `aoj` collector/matcher,
  `external_validate` check vs Codeforces + Kattis + gym mirrors + AOJ (all 3 models),
  `gym_difficulty` fixed-θ fit on the CF gym-mirror population, `predict_eval`,
  `calibrate`, `season_experiment`, `medals` EA medal badges + lowest-gold
  analysis (with `export_medal_viewer` + `medal_viewer_template.html` for the
  medal viewer), `twopl`/`twopl_region` 2PL discrimination
  prototype, `export_virtual_calc` + `virtual_calc_template.html` for the
  virtual-contest performance calculator); reuses `arch_a.load` and `arch_a.elo`.
- `data/ec_online/` — official Asia East online rankings (teams, schools),
  2022–2024 online rosters, 2022–2025 regional official standings and medals,
  and hand-encoded 2023–2026 slot rules; built by
  `scripts/build_ec_online_data.py`, consumed by `arch_b.online_gold`.
  `quota_evidence.json` (quota-channel evidence and Shanghai's published
  allocation lists) is built by `scripts/build_quota_evidence.py`, consumed by
  `arch_b.quota_teams`.
- `data/tabfm_gold/` — team-level gold-prediction table for TabFM (`teams.csv`,
  BigQuery `schema.json`, `features.json`, `predict.sql`); built by
  `scripts/build_tabfm_gold_data.py`, baselines/scoring in `arch_b.tabfm_gold`.
- `output/problem_ratings.json` — Architecture A ratings;
  `output/problem_ratings_b.json` — Architecture B (binary) ratings;
  `output/problem_ratings_survival.json` — Architecture B (survival) ratings;
  `output/problem_ratings_calibrated.json` — survival ratings mapped to CF points;
  `output/gym_difficulty.json` — independent CF-scale difficulty from gym mirrors.
- `output/ratings_viewer.html` — generated interactive viewer.
- `output/virtual_calc.html` — generated virtual-contest performance calculator.
- `details.md` — design notes, key decisions, and follow-ups.
- `rating_bias.md` — catalog of every mechanism that can inflate or deflate
  estimated difficulties (by pipeline stage, with direction + status).
- `data/cphof_cf_participants.json` — audited CPHoF person/profile links,
  roster-corroborated standing appearances, and official Codeforces rating
  histories (source data only; not yet a fit input).
- `scripts/cphof_cf_participants.py` — resumable, rate-limited builder for that
  artifact; raw source responses are cached under the gitignored
  `data/cphof_cache/`.
- `scripts/fetch_qoj_supplemental.py` — standings-only QOJ category collector;
  `scripts/fetch_xcpcio_standings.py` — resumable converter for XCPCIO-hosted
  official boards. Their broader camp/provincial datasets were tested and
  discarded; see the 2026-07-23 campaign in `details.md`.
- `cf_participant_ratings.md` — measured member→Codeforces coverage and the
  proposed historical-rating prior (the source layer is implemented; fit
  integration remains research).
- `external_data_sources.md` — internet-source audit covering CPHoF/Codeforces
  participant identities, ICPC Global/Contest API metadata, and AOJ/solved.ac
  difficulty signals, with measured overlap and a fit experiment order.

See `details.md` for the no-Codeforces-data anchoring choice, the `$DEFAULT`
team-id handling, the two architectures, and what's deliberately out of scope.
2PL discrimination has now been **prototyped** (`arch_b.twopl`) and measured by
region: it captures the regional discrimination signal in-sample but overfits
(worse held-out prediction and LLM agreement), so the shipped fit stays Rasch —
see the 2PL prototype section in `details.md`.

### Planned zero-shot LLM + survival integration

[`llm_survival_plan.md`](llm_survival_plan.md) applies the pairwise-comparison +
Bradley--Terry method from arXiv:2512.14220 to this repository without replacing
the survival model. The plan uses base zero-shot `gemini-3.5-flash`,
metadata-sanitized statements, both A/B orientations, an uncertainty-aware
survival prior, and nested contest-level validation against the existing metric
and guards. Knowledge cutoff is reporting context, not a split requirement;
solve data, ratings, labels, and other target proxies remain excluded from the
prompt. The document records planning only; no repository problem was dispatched
during that planning task. The plan was subsequently executed on 2026-08-07 with the
user-approved $50 cap. The run used only sanitized per-problem `statement`
text: the contest-level `editorial` field (which contains all problem editorials)
was never read or sent. The 156-request pilot passed parsing and 85.9% A/B
order consistency; the full 2,128-request run completed after two transient
429 retries. Estimated actual inference cost was **$5.4270**.

The result is deliberately not integrated into standings. Re-running the local
analysis against the corrected survival fit gives nested contest-level LOCO
275.68 CF points for survival versus 282.31 for fusion (fusion worse by 6.63),
with 0.733 bootstrap probability that fusion was worse. A/B consistency was 0.816,
BT pairwise accuracy against CF ratings was 0.752, and the selected robust
sparse schedule was 10 unordered matches/problem (mean/minimum Kendall 0.974 /
0.921). Survival remains the default. Use [`llm_survival.py`](llm_survival.py)
to reproduce the prepared, resumable workflow; raw statements and responses are
kept in the local gitignored `llm_survival_run/` directory.

### Codeforces pairwise-difficulty tuning pilot

`pairwise_tuning.py` is a separate experiment that teaches Gemini to answer the
same pairwise question used at evaluation time: which of two Codeforces problem
statements is harder? It reuses the official metadata and statement scraper from
`../codeforces_integration`, removes exact statement duplicates, and does not
interpolate the structured problem-title, contest-index, or rating fields into
the prompt. Editorial/tutorial text now passes through a metadata sanitizer in
`cf_pairwise.py` before it is hashed or sent: problem IDs, URLs, title/header
lines, attribution, and rating-footer boilerplate are removed, with prompt-level
regression checks. The historical Phase 2/3 artifacts below predate this fix and
remain unsanitized; the clean base-model diagnostic is recorded in `details.md`.

The frozen temporal contract is 600 training candidates before 2025-02-01,
validation from February–March 2025, and an untouched final test from
2025-04-01 through 2025-05-21. Raw statements and run credentials/results are
gitignored; `data/cf_pairwise/collection_summary.json` records the auditable
collection counts. Generate the deterministic files with:

```bash
./.venv/bin/pip install -r ../codeforces_integration/requirements.txt google-auth
./.venv/bin/python pairwise_tuning.py collect --cf-integration ../codeforces_integration
./.venv/bin/python pairwise_tuning.py prepare --output pairwise_tuning_run
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

#### Copying the frozen pairwise artifacts

The raw problem cache and the three `pairwise_*_run/` directories are deliberately
gitignored. They are required to reproduce the already-submitted experiments
exactly: recollecting would re-scrape live Codeforces statements and editorials.
First clone/pull this repository at the same revision on both computers, then,
from the destination checkout, pull the artifacts over SSH:

```bash
./scripts/sync_pairwise_artifacts.sh pull dedibeat@DESKTOP_HOST
./scripts/sync_pairwise_artifacts.sh verify
```

Replace `DESKTOP_HOST` with the desktop's LAN hostname/IP or Tailscale name/IP.
The helper resumes interrupted transfers and copies `pairwise_tuning_run/`,
`pairwise_phase2_run/`, `pairwise_phase3_run/`, and
`data/cf_pairwise/problems/` (about 38 MB at the published snapshot). To copy
the other direction, run `push` instead of `pull`. If the source repository has
a different path, set `PAIRWISE_ARTIFACT_REPO` before invoking it. `verify`
checks the file counts and content hashes against the tracked
`data/cf_pairwise/artifact_snapshot.json`; update that snapshot intentionally
whenever a new frozen artifact set is published.

The 2026-08-05 pilot uses 400 balanced pairwise examples from 200 training
problems, 150 post-cutoff tuning-validation pairs, two epochs, and a $25 pilot
dispatch cap inside the overall $100 budget. Exact `countTokens` preflight was
649,514 tokens per epoch and $12.99 estimated training cost. The pre-tuning
Gemini 3.5 Flash baseline on 200 swapped-order requests was 69.0% overall,
55.8% at an exact 300-point gap, and 84.0% order-consistent. A deliberately
small 20-request Gemini 3.1 Pro Preview check scored 80.0%; its sample is too
small for a strong model comparison. Vertex accepted tuning job
`projects/703166210069/locations/us-central1/tuningJobs/2518784060365471744`,
which completed successfully. On the identical 200 validation requests, the
tuned model scored 70.0% overall, 37.0% at an exact 200-point gap, 65.4% at an
exact 300-point gap, and 94.0% order-consistent. This is a +1.0-point overall
change and +9.6 points at gap 300, but -4.3 points at gap 200; the paired changes
are too small to establish a reliable improvement. The tuned validation run used
319,416 input and 1,200 output tokens, estimated at $0.81. The final 96-problem
test partition was not uploaded or evaluated.

Phase 2 is submitted as a fresh editorial-only model. It uses all 561
exact-statement-unique substantive-editorial pre-cutoff problems in 400
coverage-guaranteed training pairs, 75 contest-disjoint tuning-validation
pairs, and a separate 100-request development evaluation. The editorial-only
base scored 80.0% overall and 72.5% at gap 300; adding the first scoped author
solution scored 77.0% and 65.0%, while increasing the two-epoch preflight from
$20.87 to $27.80. Code was therefore excluded. The editorial job
`projects/703166210069/locations/us-central1/tuningJobs/3895319841782890496`
completed successfully on 2026-08-06. On the identical clean development
requests, the tuned endpoint improved from 80.0% to 84.0% overall and from
72.5% to 80.0% at the exact 300-point gap; this is only a 100-request
development result, so the final test remains unenriched and untouched.

Phase 3 is a fresh-base-model replication with 600 rather than 400 editorial
pairs. It retains the same 561 problems, tuning-validation split, development
set, two epochs, and prompt; only the 200 additional training comparisons
change. The sampler has no duplicate unordered pairs and uses every problem
one to three times (mean 2.14), with 150/210/240 pairs at 200/300/at-least-400
rating gaps. Exact preflight was 1,608,024 tokens per epoch and $32.16 for two
epochs. Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/8563467981319831552`
completed successfully. Its monitor shows no visible train/validation
divergence, but the near-perfect score is only on the 75-pair tuning-validation
set and may reflect validation-set overfitting; the final test remains
validation-only until a clean final evaluation is run.

The final evaluation then used the frozen 96-problem test partition as 500
unordered pairs in both orientations (1,000 editorial-only requests). The one
short but official tutorial for `2086A` was retained as an explicit exception;
no solution code was included. The base model ran through Vertex batch job
`projects/703166210069/locations/us/batchPredictionJobs/7631252811556061184`,
and the tuned model used endpoint
`projects/703166210069/locations/us/endpoints/4697676623812493312`. All 2,000
responses were valid. Base scored 82.3% overall versus 85.2% tuned, a +2.9
percentage-point gain. The tuned gains were +2.3 points at exact gap 200,
+5.3 at exact gap 300, +3.1 at gaps of at least 300, and +1.3 at gaps of at
least 400; swapped-order consistency rose from 77.8% to 89.2%. The scorer's
non-global list-rate estimates were $5.119 for base and $7.589 for tuned;
generated predictions and the final score remain gitignored artifacts.

As an exploratory reasoning audit, the same final-test pool was sampled into 50
unordered pairs (15 exact-200, 15 exact-300, and 20 at least 400) and sent in
both orientations with `thinkingLevel=HIGH` and returned thoughts enabled. On
these 100 requests, base scored 84.0% and tuned 81.0%; this is a -3.0-point
change and is not an independent test because it reuses the final-test pool.
Both sides returned 100 valid decisions and thought text on 98/100 requests.
The raw reasoning-audit predictions and score are gitignored under
`pairwise_phase3_run/`; the evaluator now uses a 4,096-token output allowance
when thought capture is enabled so the final JSON decision is not truncated.

A forensic join against the minimal-reasoning outputs changes the interpretation.
On those exact 100 requests, minimal reasoning scored 81.0% for both base and
tuned; high reasoning raised base to 84.0% but left tuned at 81.0%. The
high-thinking tuning delta has a wide approximate 95% paired-pair interval of
-12.0 to +6.0 points and is not evidence that tuning hurts. High reasoning cost
about 3.9x base and 4.1x tuned inference on the same sample, with no reliable
accuracy gain, so this pilot does not justify enabling it.

More importantly, verbatim tutorial text contaminates the intended metadata-free
comparison. Literal problem IDs occur in 51/96 final-test problem prompts and
title text in 66/96; 816/1,000 ordered final requests contain at least one
literal ID. The same issue affects training: 352/600 Phase 3 pairs contain at
least one literal ID, and every tuning-validation pair does. Returned thoughts
explicitly use forbidden problem letters, inferred contest positions, and
supposed ratings. Consequently the +2.9-point final gain is a positive result
only for the current unsanitized editorial input, not clean evidence that tuning
improves intrinsic algorithmic-difficulty judgment. A fresh sanitized
train/validation build, fresh tuning job, and untouched clean test are required
before making that claim; the existing final pool has already been used and does
not supply that clean test. A 40-request-per-setting base-only check after the
sanitizer gave 80.0% minimal versus 82.5% high reasoning, with 70.0% versus
85.0% swapped-order consistency. This is a small development diagnostic, not a
replacement for the fresh tuned-model and untouched-test evaluation.

### Gemini 3.6 vs 3.5 gap check

Using the same frozen statement-only pairs in both orientations, Gemini 3.5
Flash scored 21/46 (45.7%, 95% CI 32.2–59.8%) at an exact 200-point gap and
31/52 (59.6%, CI 46.1–71.8%) at 300. Gemini 3.6 Flash scored 16/46 (34.8%, CI
22.7–49.2%) and 30/52 (57.7%, CI 44.2–70.1%), respectively. The 3.5 point
estimates are higher, but the paired differences are inconclusive at this
sample size. Gemini 3.6 was more A/B-order consistent: 82.6% vs 78.3% at 200
and 84.6% vs 57.7% at 300. Details and raw ignored outputs are in
`details.md` and `gemini_gap_run/`.
