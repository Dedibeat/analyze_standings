# README snapshot before the 2026-11-20 reorganization

> The findings summary and Layout section of `README.md` as of commit b6732cb. Partly stale (it still calls DE the shipped calibration in places); see docs/STATUS.md.

> **Production rating update (2026-11-16):** problem ratings, team performances,
> medal bars and badges now use hierarchical binary with time (`time_skip`, five
> slices, weight 0.25, `skip_partial`). The source artifacts are
> `output/problem_ratings_hier.json` and `output/problem_calibration_hier.json`.
> See `hier_time_report.md` for the 205.9 nested-LOCO RMSE and its limits.
> Older DE/survival instructions below describe the previous production model.
> Regenerate with `python -m arch_b.hier_time release`, then
> `python -m arch_b.export_virtual_calc`, `python -m arch_b.export_viewer`,
> `python -m arch_b.medals`, and `python -m arch_b.export_medal_viewer`.

## analyze_standings

Estimate ICPC-style **problem difficulties from contest standings** — there is no
native contestant rating to invert (unlike Codeforces), so the ability layer is
built from the standings themselves.

The method (`strat.tex`, long-form `strat_detailed.tex`): a problem's difficulty
is the skill level at which solving it is a coin flip. Abilities and difficulties
define each other, so they are solved either by an alternating fixed point
(**Architecture A**) or by a joint item-response (Rasch) MAP fit
(**Architecture B**); teams recurring across contests link everything onto one
scale.

The [2026-11-04 rating rethink](../reports/rating/rating_rethink.md) proposes a context-aware binary
model, separate completion/timing components and member-informed team priors.
Fresh diagnostics reproduce shipped DE calibration (225.61 nested development
LOCO RMSE), favor binary over survival for response imputation, and identify
stale calibration metadata hashes. The report prioritizes experiments for
onsite/mirror separation, field-composition transfer and stricter forecasting;
it also inventories locally cached submission logs. No production estimator or
rating changed. Reproduce the read-only audit with
`./.venv/bin/python -m scripts.rating_rethink_audit`.

[rating_rethink_experiments.md](../reports/rating/rating_rethink_experiments.md) reviews that
audit and runs its experiments 0–2.
- **Mirror context.** A mirror offset in the binary fit is mostly set by the
  ability prior unless only onsite↔mirror bridge teams carry it. The
  identified same-team lift is +50 … +90 and barely changes predictions
  (`arch_b.context_fit`).
- **Field transport.** Binary difficulties are invariant to who attempted a
  problem. Shipped DE moves about +190 CF between strong and weak halves of
  the same board, and loses its accuracy lead on small or weak fields
  (`arch_b.field_transport`).
- Nothing shipped changed.

[Experiment 3](../reports/forecast/member_forecast_report.md) continues that work with recorded-date
regional forecasts and exact-roster identity. Member history improves cold-roster
pair accuracy from 60.3% to 69.9% on matched 2024–2025 development pairs; the fixed
q=50 random walk provides no useful log-loss gain. Cutoff manifests, missing-data
coverage and limitations are in the report and `output/member_forecast.json`.
Reproduce with `./.venv/bin/python -m arch_b.member_forecast`. This is a
retrospective roster replay, not fresh confirmation; shipped ratings are unchanged.

[Four DE successor candidates](../reports/rating/de_successors.md) are recorded. Candidate #2,
[stability-penalized DE](../reports/rating/de_stability_plan.md), has been run. The penalty adds
nothing: beta = 0 is picked in 8 of 15 folds, CF RMSE is no better than ridge
without the penalty, and drift falls by at most 2.2%. Resampling without the penalty
fixes DE's mean shift on small or weak fields, but on full fields it loses 12
RMSE to DE (237.8 vs 225.6). DE stays shipped. The scorecard is in
`output/de_stability_evaluation.json`. To rerun: install
`requirements-de-stability.txt`, then `python -m arch_b.de_stability check`,
`prepare --jobs N` and `evaluate`. On Windows, check the frozen inputs out with
LF line endings first (see `docs/journal/`).

[Hierarchical binary ratings](../reports/rating/hier_binary_report.md) are the current DE rival
(research only; nothing shipped changed). It is binary Rasch with board-level
ability and problem-set means, and one CF map for problems and teams.
- **Full fields:** CF RMSE 229.5 vs DE's 225.6 (+3.9 [−8.1, +14.5]).
- **Field composition:** the strong and weak halves of a board end 1 point
  apart in mean error (DE: 224). On the weak half, 333 vs 451.
- **Teams:** held-out appearances are predicted better than by both shipped
  engines (log loss 0.237 vs binary 0.252 and survival 0.278; rank-pair
  accuracy 80.7% vs 79.4% / 80.0%). The recorded-date forward replay is level
  on history pairs and better with member priors (+0.35 pp).
- **Open issues:** EC online rounds read ~140 easier than DE (a tail effect;
  the hand panel sides with this fit). Weak, weakly linked boards read about
  300 too hard by hand in both models (below).
- **Re-measured 2026-11-10:** the cut-board level float is +11 (SE 7) over 8
  random quarter cuts, not +52. What is real is tail compression (floor +196,
  hard tail −129). σ_b = 600 is an interior optimum, not a grid edge.

Settings are chosen without CF labels. Run
`PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 ./.venv/Scripts/python -m arch_b.hier_binary all 10`
(~75 min); results go to `output/hier_binary.json` and
`output/hier_binary_ratings.json`.

A [hand audit of problem ratings](../reports/rating/problem_rating_audit.md) compares 72
problems, rated by reading their statements and solutions, with both models.
It also reviews the worst CF anchors.
- **Middle:** between 5% and 95% solved, both models are sound.
- **Sign-in problems:** inflated on EC mirror-merged boards (hierarchical
  +387, DE +209). The cause is mirror accounts that never submitted to a
  problem being counted as failing it.
- **EC online:** the 2025 rounds side with the hierarchical fit (bias +3 vs
  DE +118).
- **Anchors:** one mislabeled anchor, Uniform Chemistry (CF 3200, about 2000
  by hand), is 16% of the anchor squared error.

Run `PYTHONUTF8=1 ./.venv/Scripts/python -m scripts.problem_rating_audit`
(~3 min) → `output/problem_rating_audit.json`.

The audit's follow-up, [skipped cells as missing data](../reports/rating/skip_cells_report.md),
fixes the sign-ins in rows that submitted ≤ 2 problems. Unsubmitted easier
cells in those rows are treated as missing.
- **Result:** it passes its four pre-registered criteria. Sign-in bias falls
  from +387 to +148, full-field CF RMSE is 227.6 vs 229.5, held-out log loss on
  untouched cells is better, and reserved-view drift is no worse on 7 of 8.
- **The broader all-rows version fails on stability.**
- **A second test, `skip_mirror`,** also spares official registrations. It
  fixes 2025 EC Online II D, where weak official teams really failed the
  easiest problem (1211 → 1458, hand 1650). It fails the sign-in criterion,
  though (+174), so `skip_partial` stays preferred.
- **Other hand findings** are in the audit's follow-up section:
  - strong-board floors read high in the hierarchical fit (EC-Final 2021
    "DFS Order" 1676 vs ~1200 by hand);
  - no rating-order inversions;
  - tiny NA boards have as few as 1–2 rows. Their shipped ratings are now
    flagged with `small_board` (below).

- **Third and fourth tests (2026-11-10):** `skip_margin` and `skip_early` both
  fail their pre-registered criteria. A fresh blind panel of 32 easy EC
  problems confirms the sign-in fix: `base` +328 on the 16 most-solved,
  `skip_partial` +155.

Research only. Run `python -m arch_b.skip_cells 8` (a few minutes, needs the
`hier_binary` cache). Every problem's rating under the preferred rule is in
`output/skip_cells_ratings.json`.

**Stable DE, continued (2026-11-10).** Six ideas were tested on the
hierarchical candidate and none replaces the current setting; the scripts are
in [scripts/stable_de_explore](../../scripts/stable_de_explore/README.md) and the
record is the last entry of `docs/journal/`. Two findings matter beyond the
candidate:
- **A loader bug affected 8 shipped ratings (fixed 2026-11-16, below).** On
  contests with incomplete problem lists, only rows that solved a listed
  problem were kept. CCPC Harbin 2025 M was shipped at 1947; with the dropped
  rows counted as failures it is about 2805.
- **Weak, weakly linked boards read too hard by hand.** Latin America 2023,
  13 problems rated blind: DE +486, hierarchical +349. A simulation rules out
  the estimator; settling it needs CF ratings of some of those teams.

**Solve time in the hierarchical fit; a release candidate (2026-11-16).**
[hier_time_report.md](../reports/rating/hier_time_report.md). A solved cell now also says in
which fifth of the contest window it was solved, on the binary scale and at
weight 0.25 next to the binary likelihood. The dose was chosen without CF
labels, and the criteria were fixed before the run. Two labels documented as
wrong are left out of the CF maps and RMSE: the anchor Uniform Chemistry
(CF 3200, about 2000 by hand) and one blind hand rating.
- **Release candidate:** time slices plus `skip_partial`. It passes all four
  criteria with the lowest hand-panel error. Its ratings are in
  `output/problem_ratings_hier.json`, in the shipped file's layout. DE stays
  shipped until someone decides to switch.
- **Accuracy:** full-field CF RMSE 205.9 on 184 anchors (DE 207.0,
  hierarchical binary 211.5). On cut fields it is better than hierarchical
  binary everywhere (strong half 289 vs 360, weak half 288 vs 319), with
  lower drift on all 8 reserved views.
- **By hand:** EC sign-in bias +385 → −1; 72-problem panel RMSE 296 → 196
  (DE 290); fresh blind panel 379 → 282. Problems a whole strong board solved
  late move up to their CF labels.
- **Teams:** rank-pair accuracy up 0.2–0.5 pp; held-out log loss on untouched
  cells 0.2% worse.
- **Fresh boards:** on the five 2026 EC regionals, added after the
  hierarchical setting was frozen, the hierarchical fit ranks linked teams
  better than flat binary (82.2% vs 81.4%), and the time term adds 0.4 pp.
- **Cost:** within-contest order reversals under field cuts about double.

**Loader bugs fixed and the shipped fit re-released (2026-11-16).** All in
`arch_a/load.py`:
- rows that solved only unlisted problems were dropped, which selects on the
  outcome (CCPC Harbin 2025 M: shipped DE 1961 → 2811; Greater New York 2023
  E, J, K, L +110 … +152);
- Rocky Mountain 2023's official rows store solve times in minutes (shipped DE
  on that board −236 … +167);
- one Xi'an 2026 solve dated before the start counted as a result;
- a board without a problem list would have kept empty rows.

`arch_b.metric` reads 246.7 (246.3 before; inside its noise band).

Run `PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m arch_b.hier_time evaluate 4`
(~25 min on 4 cores) → `output/hier_time.json`, then
`python -m arch_b.hier_time release`.

A [probability-course shortlist](../teaching/prob_course_candidates.md) picks five main
problems and four backups from the probability-tagged problems in
`data/tagged.json`: discrete probability only, each with its core trick, a
paper version and the answer. [prob_course_problems.tex](../teaching/prob_course_problems.tex)
writes all nine up in LaTeX: each is one question resting on one key idea,
followed by its solution and a remark with extensions. The compiled
[PDF](../teaching/prob_course_problems.pdf) is committed.
Rebuild it with `pdflatex prob_course_problems.tex` (run twice for the table
of contents).

The [2026-09-05 experiment review](../reports/rating/experiment_review.md) records the audit that
found held-out-label leakage, incorrect rank/AUC tie handling, incomplete
uncertainty labels, and participation-key collisions. The concrete correctness
defects were repaired on 2026-09-06; open data/model research limitations remain
listed in the review and in `docs/journal/`.

The [fit and rating improvement strategy](../reports/rating/rating_improvement_strategy.md) examines
what could improve the underlying measurement beyond benchmark scores: task
choice and time burden, participation and roster continuity, shared problems
across contests, and targeted collection of missing evidence. It records fresh
diagnostics and proposed experiments, not implemented model changes.

The bounded [calibration residual experiment](../reports/calibration/calibration_experiment_report.md)
recorded a nested 15-contest CF-anchor control: raw affine 246.9061,
gym-shaped affine 245.4277, and ridge residual 229.6269 RMSE. This is a
research-only proxy result. Since the 2026-09-28 DE release,
`output/calibration_experiment.json` holds the same control rerun on the
roster-fixed fit (246.9288 / 246.1274 / 229.4028). The managed [BigQuery TabFM result](../reports/calibration/tabfm_bigquery_report.md)
completed the full 185-anchor comparison: TabFM reaches 231.2865 RMSE, improving
on raw/gym but not the frozen DE control (226.5661), so no shipped calibration or
rating artifact changed. Reproduce the controls with
`./.venv/bin/python -m arch_b.calibration_experiment --baseline-only`.
The optional TabFM route uses the pinned `TABFM_CHECKPOINT_DIR` interface
documented in that report; it does not silently download a checkpoint, and must
be intentionally run in an isolated process.

The [BigQuery and Google Cloud TabFM plan](../reports/calibration/tabfm_cloud_plan.md) specifies the
requested **$10 total limit** and native managed TabFM through BigQuery
`AI.PREDICT`, with experiment tables and SQL scoring. It compares against DET
and the newer DE control, limits query spending, and preserves separate result
artifacts. No VM or GPU is needed; the executed result is linked above.

The frozen [feature-group ablation](../reports/calibration/calibration_ablation_report.md) separates
estimator disagreement (D), non-time evidence (E), and extra calibration timing
features (T) on the same reused anchors. DE is the strongest development
candidate (226.5661 LOCO / 225.7640 LORO RMSE), but this is not fresh
confirmation or a production-promotion decision. Reproduce it with
`./.venv/bin/python -m arch_b.calibration_ablation` and inspect the separate
non-OOF transfer diagnostic with
`./.venv/bin/python -m arch_b.calibration_ablation_transfer`.

The [2026-09-10 prediction audit](../reports/calibration/calibration_audit_report.md) verifies cached
source/feature consistency and reruns nested DE calibration after each anchor
contest is removed. DE beats both controls in all 15 deletions, but 1,840 of
3,159 full-refit appearances exceed at least one training-feature range
(1,610 on field size). The saved research predictions now include source links
and feature-support flags. Reproduce with
`./.venv/bin/python -m arch_b.calibration_audit`; production ratings are unchanged.

The [TabFM/DE audit and shipped-fit update preparation](../reports/rating/shipped_fit_update_plan.md)
replays all 225 managed calls and DE's nested selection, and stages a full
per-problem comparison in `output/shipped_fit_audit.json`. DE improves development
RMSE by 18.86 points over the shipped gym calibration, but would move 1,737
ratings by at least 100 points; 1,840 appearances exceed an anchor feature range.
The plan identifies exporter, ability/medal-map, uncertainty and confirmation
requirements before a default update. Reproduce offline with
`./.venv/bin/python -m arch_b.shipped_fit_audit` (requires the original local
managed-response archive). Production outputs remain unchanged.

The [mechanism explanation and future plan](../reports/calibration/calibration_interpretation.md)
decomposes DE into an estimator blend and evidence correction. It shows that
conditional SE largely encodes solve count, and that unusual combinations of
disagreement and solve rate explain much of the largest correction. The small
DE–TabFM gap remains uncertain across contests. Proposed next work isolates
these mechanisms and obtains fresh transfer evidence before promotion.

The [DE release audit](../reports/rating/de_release_audit.md) (2026-09-28) reruns DE on the fit
with the EC online-round rosters attached (`scripts/attach_online_rosters.py`).
**DE is now the shipped problem calibration** (released 2026-09-28, see
"Calibrated Codeforces-point ratings" below). DE scores 226.3 LOCO / 225.7 LORO against the gym map's 246.1.
Its per-contest levels also agree best with the independent CF-gym population
(robust contest-offset SD 96, against 133 raw and 120 for the gym map).
- **Decisions taken at release:** shipped without a fresh confirmation set
  (none exists); DE's features are clipped to the anchor range, which bounds
  the 225 appearances outside any field-size evidence; online-round problems
  get no special handling, although their ratings rest on an equal
  online/onsite assumption that held-out verified teams contradict by about
  100 CF-scale points.
- **Other findings:** the survival fit compresses team abilities (CF slope 2.85
  vs binary 0.98) because it reads sequential solving as weakness. Team-season
  offsets help solve prediction but hurt CF calibration.
- **Bug fixed on the way:** the gym map now sorts ties stably, so shipped
  ratings reproduce on every platform.

Reproduce with `python3 -m arch_b.de_release_audit /tmp/tagged_rosters.json`
and `python3 -m arch_b.fit_mechanism_audit /tmp/tagged_rosters.json`, after
running the attach script.

The [experiment roadmap](../reports/rating/experiment_roadmap.md) records the remaining audits,
fresh-confirmation requirements, and longer-term rating research. Its correction
and anchor-contest influence audits now have the bounded results linked above;
the deferred local-checkpoint TabFM comparison remains separate from the completed
managed pilot.


## Layout

- `data/tagged.json` — full input standings (165 contests, 65,758 rows; the 2026
  season adds the Xi'an/Chengdu/Wuhan/Nanjing/Shenyang regionals and the Universal
  Cup S5 stages); `data/ucup_s3.json`,
  `data/ucup_s4.json` — the Universal Cup seasons used to anchor the scale.
- `data/xcpcio_ccpc.json` / `data/qoj_ccpc.json` — the CCPC boards (7th–12th
  seasons) for experiments: 35 XCPCIO contests (16,081 rows) plus the 10 QOJ
  contests XCPCIO does not host (Changchun 2026, the women's/vocational
  divisions, and three online rounds). Research only — never a fit input.
- `data/xcpcio_51st_regionals.json` — XCPCIO-hosted 51st-season East Asia boards
  (Xi'an/Chengdu/Wuhan/Nanjing/Shenyang). Nanjing and Shenyang are the two 2026
  regionals QOJ does not host, and they are the only two appended to `tagged.json`
  (see the 2026-11-15 entry in `docs/journal/`).
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
  virtual-contest performance calculator, `dynamic_rating` time-varying team
  ratings and month-by-month forecast test, `context_fit` event/mirror context
  terms in the binary fit, `field_transport` calibration under field changes);
  reuses `arch_a.load` and `arch_a.elo`.
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
- `data/techniques_atlas.json` — named-technique tags and taxonomy snapshot from
  `../my-react-app/data/techniques_viewer.html`, consumed by
  `scripts/technique_forecast.py` (report `output/technique_forecast.{md,json}`).
- `output/problem_ratings.json` — Architecture A ratings;
  `output/problem_ratings_b.json` — Architecture B (binary) ratings;
  `output/problem_ratings_survival.json` — Architecture B (survival) ratings;
  `output/problem_ratings_calibrated.json` — DE-calibrated problem ratings in CF points
  (settings in `output/problem_calibration.json`);
  `output/gym_difficulty.json` — independent CF-scale difficulty from gym mirrors.
- `output/ratings_viewer.html` — generated interactive viewer.
- `output/virtual_calc.html` — generated virtual-contest performance calculator.
- `docs/journal/` — design notes, key decisions, and follow-ups.
- `rating_bias.md` — catalog of every mechanism that can inflate or deflate
  estimated difficulties (by pipeline stage, with direction + status).
- `data/cphof_cf_participants.json` — audited CPHoF person/profile links,
  roster-corroborated standing appearances, and official Codeforces rating
  histories (source data only; not yet a fit input).
- `scripts/cphof_cf_participants.py` — resumable, rate-limited builder for that
  artifact; raw source responses are cached under the gitignored
  `data/cphof_cache/`.
- `data/team_r3/` — the TEAM_R3 account's submissions (`submissions.json`,
  `code/`), its contests' dashboards, statements, tutorials and QOJ boards
  (`contests/`; PDFs/zips are git-ignored), XCPCIO boards (`boards/`) and the
  member attribution (`members_solved.csv`); built by `scripts/fetch_team_r3.py`.
- `scripts/add_qoj_contest.py` — adds one QOJ contest's standings to
  `data/tagged.json` (`python3 scripts/add_qoj_contest.py 4071 --name "EC Online (I)"
  --region "Asia East Continent"`; `--refresh` replaces an entry already stored).
  QOJ shows contests only to logged-in users and Cloudflare-gates non-browser
  clients, so it logs in through the browserless flow (`curl_cffi`, md5 password,
  `_token` from the page's JS) with `QOJ_USERNAME`/`QOJ_PASSWORD`, caching the
  session in the git-ignored `data/.cookies-<user>.json`. Then rerun the release
  steps (see the 2026-11-15 entry in `docs/journal/`).
- `scripts/fetch_qoj_supplemental.py` — standings-only QOJ category collector;
  `scripts/fetch_xcpcio_standings.py` — resumable converter for XCPCIO-hosted
  official boards. Their broader camp/provincial datasets were tested and
  discarded; see the 2026-07-23 campaign in `docs/journal/`.
- `cf_participant_ratings.md` — measured member→Codeforces coverage and the
  proposed historical-rating prior (the source layer is implemented; fit
  integration remains research).
- `cf_ai_deflation.md` — Codeforces rating deflation and AI use: size, onset,
  mechanism. Built by `scripts/cf_ai_deflation.py`, from the gitignored
  `data/cf_ai/` cache, with results in `output/cf_ai_deflation.json`.
- `external_data_sources.md` — internet-source audit covering CPHoF/Codeforces
  participant identities, ICPC Global/Contest API metadata, and AOJ/solved.ac
  difficulty signals, with measured overlap and a fit experiment order.

See `docs/journal/` for the no-Codeforces-data anchoring choice, the `$DEFAULT`
team-id handling, the two architectures, and what's deliberately out of scope.
2PL discrimination has now been **prototyped** (`arch_b.twopl`) and measured by
region: it captures the regional discrimination signal in-sample but overfits
(worse held-out prediction and LLM agreement), so the shipped fit stays Rasch —
see the 2PL prototype section in `docs/journal/`.
