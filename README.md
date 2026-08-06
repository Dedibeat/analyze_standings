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
fit (see the zero-solve decision in `details.md`).

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
or editorials and improve calibrated LOCO 264.5 → 261.6.

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
```

All three architectures agree closely with both opinions. On the LLM check arch A
leads (Spearman +0.908 vs arch B +0.874 / +0.880 — deduping the repeated contests
sharpened arch A's solve-count estimate); on the CF ratings the IRT fits edge ahead
(binary +0.962, survival +0.956 vs arch A +0.945), and all three are ≈ 0.95+. On
held-out solve prediction the survival model generalizes best (AUC 0.881 vs binary
0.871).

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
**261.6**, down from 266.4; lower is better). It exits nonzero if any external
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
92 problems) from **star** (beyond even the champions — the extreme problems,
104, almost all 0–2 official solves). Writes
`output/medal_badges.json`; bars and difficulties are also given in CF points via
the `calibrate` map (gold bar across contests: median ≈ 2601 CF, range ≈
[2137, 2932]). See the medal-badge section in `details.md` for why the bars are
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

Forward validation (train on earlier seasons, predict 2023–2025) gives **132 CF
gold-bar RMSE** and **77.1% correct pair ordering** over 19 contests, versus
172 CF / 66.7% for the previous raw-city + order/year formula after correcting
the 2022 Hong Kong host label. The
[2026 ICPC Global city list](https://icpc.global/regionals/results) was checked
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
  prototype); reuses `arch_a.load` and `arch_a.elo`.
- `output/problem_ratings.json` — Architecture A ratings;
  `output/problem_ratings_b.json` — Architecture B (binary) ratings;
  `output/problem_ratings_survival.json` — Architecture B (survival) ratings;
  `output/problem_ratings_calibrated.json` — survival ratings mapped to CF points;
  `output/gym_difficulty.json` — independent CF-scale difficulty from gym mirrors.
- `output/ratings_viewer.html` — generated interactive viewer.
- `details.md` — design notes, key decisions, and follow-ups.
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

### Codeforces pairwise-difficulty tuning pilot

`pairwise_tuning.py` is a separate experiment that teaches Gemini to answer the
same pairwise question used at evaluation time: which of two Codeforces problem
statements is harder? It reuses the official metadata and statement scraper from
`../codeforces_integration`, removes exact statement duplicates, and never puts
problem title, contest index, or rating in the prompt.

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
started on 2026-08-06. The final test remains unenriched and untouched.
