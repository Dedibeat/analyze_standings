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

Validate any model against two independent opinions — the LLM `difficulty_estimate`
(editorial-backed contests) and the official Codeforces ratings of the 2026 Asia
Pacific Championship:

```bash
./.venv/bin/python -m arch_b.validate           # LLM buckets, all models
./.venv/bin/python -m arch_b.gym_difficulty     # fixed-θ difficulty from CF gym mirrors
./.venv/bin/python -m arch_b.external_validate  # per-region vs Codeforces + Kattis + gym, all models
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

### The optimization metric

`arch_b.metric` is the single number model improvements are judged by:
**leave-one-contest-out RMSE in CF points** against the official ratings of all
15 CF-mirrored contests (185 anchor problems — every rated mirror the dataset
has; an exhaustive sweep found no more). It refits the survival model from
source in ~5 s, prints `METRIC loco_cf_rmse=…` as its last line (lower is
better; baseline **290.2**, cluster-bootstrap SE ±20 → improvements under ~5
points are noise), and exits nonzero if any guard regresses (gym
Asia-East-Continent / gym pooled / Kattis Spearman, solve-count sanity — the
things the CF anchors can't see). `program.md` at the repo root is the matching
instruction file for auto-research loops: verify contract, what code is fair
game, hard anti-gaming rules, and a prioritized idea list. A 2026-07-03 auto-research campaign (Claude Fable 5 + DeepSeek v4 Pro, 25
iterations) found that the only repeatable improvements were data-side identity
fixes (−2.2 RMSE to 288.0, AUC-corroborated); all model-side knobs are at
optimum. Further gains need new anchor data rather than fit changes (see
details.md).

### Calibrated Codeforces-point ratings

`arch_b.calibrate` maps the (relative) survival scale to CF points in two legs: a
monotone **shape** learned from the ~660 gym-mirror difficulties (nearly CF-native
in scale; it cannot reorder our problems) and an **affine** leg fit on the official
CF ratings of all 15 rated mirror contests (185 anchor problems, auto-mapped).
Validated leave-one-contest-out: shaped RMSE **266** vs plain-affine 288
(P(worse)≈1%, 10/15 contests improve, hard-tail RMSE 477→434). Writes
`output/problem_ratings_calibrated.json` with `difficulty_cf` + `difficulty_cf_se`.
These are the best estimate of CF-equivalent difficulty.

### East-Asia medal badges

```bash
./.venv/bin/python -m arch_b.medals
```

Assigns every problem of the 28 medal-awarding **Asia East Continent** contests a
badge on the ladder **bronze < bronze+ < silver < silver+ < gold < gold+ <
plat < plat+** (weakest → hardest) and reports the
**lowest gold-medal team** per regional. Medals go by cumulative percentile of
official teams solving ≥1 problem (gold 10%, silver 30%, bronze 60%); the official
onsite field is identified by matching XCPCIO scoreboard data against the qoj
standings. Every badge boundary is an anchored cohort crossing: the fitted
(survival-model) difficulty at which the anchor cohort's actual solve rate
crosses 50% (isotonic regression). Each medal's **"+" edge is the medal cutoff
itself** and its plain edge the mid-band cohort (gold 20%, silver 45%, bronze
80% — plain bronze is the giveaways the whole field solves); a problem gets the
weakest grade whose bar clears it — badges are monotone in difficulty, and the
badge count at gold+ or below per contest ≈ the lowest gold team's solve count.
Above the gold-medal bar sits **platinum**, split by a crossing at the
**champion cohort** (top-5 official teams): **plat** (champions still solve it
at even odds — decides ranking within gold, 93 problems) vs **plat+** (beyond
even the champions — the extreme problems, 103, almost all 0–2 official
solves). Writes
`output/medal_badges.json`; bars and difficulties are also given in CF points via
the `calibrate` map (gold-medal bar across contests: median ≈ 2655 CF, range ≈
[2100, 2900]). See the medal-badge section in `details.md` for why the bars are
empirical crossings rather than Elo performance ratings.

```bash
./.venv/bin/python -m arch_b.export_medal_viewer
```

Builds the interactive **medal viewer** (`output/medal_viewer.html`, self-contained,
no server, light/dark aware) from `medal_badges.json`: a season filter + KPI row,
a dot-range chart of the bronze/silver/gold medal bars per contest (sorted by
gold bar,
click a row to open the contest), a per-contest detail view (problems as lettered
lollipops on the difficulty axis against the badge-boundary lines and the
plat/plat+ zones, plus a table with half-band solve rates), and a sortable
lowest-gold-team table.

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
- `arch_a/` — Architecture A implementation (`load`, `elo`, `fixedpoint`,
  `anchor`, `run`), plus `export_viewer` + `viewer_template.html` for the viewer.
- `arch_b/` — Architecture B implementation (`model` binary Rasch, `survival`
  solve-time model, `anchor`, `run`, `validate`, `external_validate`
  per-region check vs Codeforces + Kattis + gym mirrors (all 3 models),
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

See `details.md` for the no-Codeforces-data anchoring choice, the `$DEFAULT`
team-id handling, the two architectures, and what's deliberately out of scope.
2PL discrimination has now been **prototyped** (`arch_b.twopl`) and measured by
region: it captures the regional discrimination signal in-sample but overfits
(worse held-out prediction and LLM agreement), so the shipped fit stays Rasch —
see the 2PL prototype section in `details.md`.
