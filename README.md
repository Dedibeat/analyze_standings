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
Architecture A's output is left untouched. Reuses arch_a's data layer and the same
two-phase UCup anchor, here feeding each UCup team's ability in as its Gaussian
prior mean; tune the prior with `estimate_anchored(sigma_theta=…, sigma_b=…)`
(looser → wider scale but more easy problems pinned to the floor). The Gaussian
prior keeps solved-by-none/all problems finite, so no boundary smoothing is
needed. See `details.md` for the Rasch-vs-2PL scope and the shrinkage-vs-arch_a
comparison.

Architecture B also loads 71 standings-only supplemental QOJ contests:
14 Asia East ICPC regionals from 2020–2021 and 57 Petrozavodsk camp contests
from 2022–2026. They add cross-contest team evidence without using statements
or editorials. The current full-cell fit has calibrated LOCO RMSE 244.2 CF
points (the earlier 261.6 figure excluded omitted no-attempt cells).

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
./.venv/bin/python -m arch_b.predict_eval       # held-out solve prediction (binary vs survival)
./.venv/bin/python -m arch_b.calibrate     # affine map to Codeforces points
./.venv/bin/python -m arch_b.metric        # THE optimization metric: LOCO CF-point RMSE + guards
./.venv/bin/python -m arch_b.data_influence # explain supplemental-contest effects
```

All three architectures agree closely with both opinions. After the full-cell mask
correction, the LLM-bucket Spearman values are +0.908 (arch A), +0.908 (binary),
and +0.911 (survival); the pooled CF values are +0.913, +0.937, and +0.942.
On the corrected tagged-only held-out-cell check, binary scores AUC 0.9733 versus
survival 0.9673; this check now favours binary, while the survival model remains
the shipped choice because it uses solve-time information and leads the broader
external CF/Kattis validation.

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
**244.2**, down from the pre-correction 261.6; lower is better). It exits nonzero if any external
guard regresses (gym
Asia-East-Continent / gym pooled / Kattis / AOJ within-contest Spearman,
solve-count sanity) or if raw affine LOCO rises above 293.4. `program.md` at the
repo root is the matching
instruction file for auto-research loops: verify contract, what code is fair
game, hard anti-gaming rules, and a prioritized idea list. A 2026-07-03 auto-research campaign (Claude Fable 5 + DeepSeek v4 Pro, 25
iterations) found that the only repeatable improvements were data-side identity
fixes (−2.2 RMSE to 288.0, AUC-corroborated); all model-side knobs are at
optimum. Further gains need new anchor data rather than fit changes (see
details.md). A 2026-07-23 data-side campaign added the supplemental standings
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
Validated leave-one-contest-out: shaped RMSE **266** vs plain-affine 288
(P(worse)≈1%, 10/15 contests improve, hard-tail RMSE 477→434). Writes
`output/problem_ratings_calibrated.json` with `difficulty_cf` + `difficulty_cf_se`.
These are the best estimate of CF-equivalent difficulty.

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

This data is **not yet consumed by the fit**.  CPHoF supplies World Finals
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

### Interactive viewer

```bash
./.venv/bin/python -m arch_a.export_viewer
```

Writes a self-contained `output/ratings_viewer.html` from the same UCup-anchored
fit as `run` (the full `tagged.json`, 146 unique contests after deduplication) —
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

Writes `output/virtual_calc.html`: pick one of the 132 fitted contests, check
off which problems your team solved in a virtual (out-of-window) run with the
time (minutes into the contest) and wrong-attempt count for each, and see the
Codeforces-equivalent performance rating you'd have earned. Method: standard
ICPC tie-break (most solved, then lowest penalty) inserts your team into that
contest's real final standings to get a hypothetical rank, then the same Elo
rank-inversion primitive `arch_b.medals` uses for every real team's
`performance_elo` converts that rank plus the real field's fitted abilities
into a rating. The CF-points mapping is the same gym-shape + affine
calibration as `arch_b.calibrate`, sampled into a dense lookup table at
export time so the browser doesn't need to re-fit it. Self-contained, no
server; recomputes live as you edit your solves.

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
  solve-time model, `anchor`, `run`, `validate`, `aoj` collector/matcher,
  `external_validate` check vs Codeforces + Kattis + gym mirrors + AOJ (all 3 models),
  `gym_difficulty` fixed-θ fit on the CF gym-mirror population, `predict_eval`,
  `calibrate`, `season_experiment`, `medals` EA medal badges + lowest-gold
  analysis (with `export_medal_viewer` + `medal_viewer_template.html` for the
  medal viewer), `twopl`/`twopl_region` 2PL discrimination
  prototype, `export_virtual_calc` + `virtual_calc_template.html` for the
  virtual-contest performance calculator); reuses `arch_a.load` and `arch_a.elo`.
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
