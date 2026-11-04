# Rethinking performance and problem ratings

Review: 2026-11-04, implementation inspected at `872b3cc`.
Experiments 0–2 and a review of this report:
[rating_rethink_experiments.md](rating_rethink_experiments.md).

**Recommendation:** develop a context-aware binary item-response model as the
common probability engine, with member-history priors for teams and a separate
timing component. Keep DE as the problem-rating benchmark until a replacement
demonstrates transfer. The first experiment should separate event and mirror
participations inside the fit; the second should test whether calibration
survives changes in the population attempting a problem.

This interprets “performance” as team contest performance, not software runtime.
This is a design review with refreshed baseline diagnostics. No replacement was
trained, shipped ratings changed, or paid inference run. Earlier proposals are
in [rating_improvement_strategy.md](rating_improvement_strategy.md); the October
findings in [details.md](details.md) materially change their priorities.

## What the evidence says now

The current pipeline has three different estimators:

| Output | Current estimator | Main unresolved issue |
|---|---|---|
| Problem CF points | Survival fit plus clipped DE residual calibration | Timing assumptions and population-dependent calibration corrections |
| Calculator performance and medal cutoff performance | Rank inversion against binary-fit abilities; scalar gym/CF map | Mixed-context abilities remain underneath the corrected event-only ranks; ability calibration is indirect |
| Long-term ability | One ability per union-find identity | Roster changes, elapsed time and participation conditions are collapsed |

The survival viewer still uses survival-based performance. The October 13 fix
changed event-field rank comparisons, not the joint likelihood or DE problem
ratings. `arch_b.metric` also still evaluates the survival gym map, not the
shipped DE calibration. Improving its single score need not improve the product.

Fresh local results are in [output/rating_rethink_audit.json](output/rating_rethink_audit.json).
They cover 262 contests, 35,862 identities, 78,201 appearances, 3,185 problem
appearances and 991,268 response cells.

| Check | Current result | What it establishes |
|---|---:|---|
| Binary response imputation | Log loss 0.1994; Brier 0.0609; AUC 0.9737 | Better completion prediction than survival on this retained-row split |
| Survival response imputation | Log loss 0.2289; Brier 0.0690; AUC 0.9684 | Timing currently harms these probability predictions |
| Clipped DE nested CF LOCO | 225.61 RMSE | Strongest of these problem-calibration controls on reused development anchors |
| Survival affine / gym CF LOCO | 246.66 / 244.38 | Cached, rounded fits; not a fresh raw-fit `metric` run |
| Binary affine / gym CF LOCO | 246.78 / 257.53 | Binary's probability win does not establish a problem-rating win |

The imputation command fits from source. Calibration scores replay the saved
fits, on the same 185 problems in 15 CF contests. These are different tasks;
neither score is a clean future-contest forecast.

Additional findings:

- **2,105 discarded zero-solve rows have wrong submissions.** Some genuine
  participation is omitted. There are 11,867 discarded zero-solve rows in the
  fitted contests; including every registration would introduce a different bias.
- **228 problem appearances have zero or one solve** (122 / 106). Their precise
  ordering needs prior sensitivity and stronger evidence.
- **1,636 of 3,185 appearances exceed the anchors' field-size range.** Another
  support check flags 453 outside the binary/survival-disagreement range. These
  counts overlap. Clipping bounds feature values; it does not validate transfer.
- **448 contest/identity groups have multiple rows**, containing 475 excess
  rows. Participation keys preserve the observations, but a shared ability still
  needs justification.
- **232 boards mix `$DEFAULT...` rows with other IDs.** This is a source-ID
  inventory, not 232 verified onsite/mirror mixtures. The loader's
  `official_of_row` is a prefix heuristic, not verified medal eligibility,
  physical venue or first exposure. EC online rounds can have imported rows too.
- **Calibration provenance is stale.** Both hashes in
  `output/problem_calibration.json` disagree with the current saved raw fits.
  The stored feature ranges still match the current anchors. The audit reproduces
  every shipped `difficulty_cf` with the current full-anchor DE fit. Reproduction does
  not make the old metadata current; regenerate and validate metadata with the
  next release rather than claiming the saved hashes certify these inputs.
- **Useful new data already exist locally:** 59 XCPCIO configuration directories
  with numeric start/end times and 38 with submission logs (38 distinct run-file
  hashes). These are inventory counts, not an audited panel of 38 usable contests.
  September's blanket “no timelines available” limitation no longer describes
  this checkout. They are not integrated into the core rating dataset.

## Decide what each number means

Use three explicit targets:

1. **Problem difficulty:** completion threshold for a reference team in stated
   conditions, initially a five-hour first-exposure onsite team contest. This is
   operational contest difficulty, including task choice and shared resources;
   standings cannot isolate “intrinsic insight difficulty.” Other durations and
   modes need their own predictions or a validated conversion.
2. **Contest performance:** the strength implied by this particular appearance,
   conditional on its rules and mode. An off-day belongs here. A common weak
   performance prior avoids giving identical results different headline scores
   merely because one team has a longer history.
3. **Current team strength:** a posterior forecast based on information available
   before the next contest. It uses history, roster continuity and uncertainty.

Keep solve probabilities on the fitted latent scale. CF-equivalent display points
are an external prediction target. Applying `10^((b-P)/400)` to separately
calibrated performance and DE problem points is not a probability model validated
by either calibration. Agreement between those two numbers is a useful diagnostic,
not independent ground truth. A shared affine display scale is a candidate only
if both ability and problem evidence validate it.

## The replacement to test

Start with binary Rasch, retaining the sparse observation layer and all valid
non-solve cells. Add mechanisms in separate experiments, not one large rewrite.
The eventual model could have the form

```text
P(solve[r,p]) = logistic((a[r] - b[p]) / s)
a[r] = team_strength[roster, date]
       + context_effect[mode, team_strength]
       + appearance_deviation[r]
```

Here `b[p]` describes a canonical, version-checked task under the reference
conditions. An appearance deviation is a pooled off-day effect, not a new
independent observation. First fit only the context term. Then test an appearance
term and member-informed priors separately. Time evolution comes later.

### 1. Put participation conditions inside the likelihood

The October audit found the same teams stronger as mirror entrants and showed
that event-only difficulties flattened much of the rank/solve disagreement.
Changing only the displayed rival set leaves mirror observations influencing both
team abilities and problem difficulties underneath it.

Build provenance-backed labels for event onsite, official online, timed mirror,
and unknown. Keep participation mode, medal eligibility, team size and previous
exposure as separate fields. Neither account prefix nor “unofficial” establishes
prior exposure or assistance. Preserve unknowns explicitly.

On verified mixed boards, compare these controls:

- Current pooled binary fit.
- Event-only problem refit with team abilities estimated outside that appearance;
  this is a diagnostic, since removing mirrors may weaken cross-contest links.
- Binary fit with one pooled mirror offset.
- Only if residuals still vary with strength, add one regularized
  mirror-by-ability slope, keeping the response monotone in ability.

Hold out complete team appearances, including duplicate/replay groups, and estimate
context parameters on other boards. Test both completion calibration and transfer
to held-out event fields. A context effect is descriptive; observational data do
not identify whether it comes from rules, selection, exposure or assistance.

**Identification is the constraint.** If a set appears only online, shifting its
problem difficulties and the online intercept together preserves every predicted
outcome. A prior chooses one answer without supplying evidence. Estimate the
conversion on audited mixed boards/shared tasks and test transport to other
boards. A team-specific context deviation needs repeated observations in both
contexts; otherwise shrink it to the pooled effect. Do not introduce free
contest offsets alongside one free difficulty for each contest-only problem.

### 2. Replace field-dependent calibration only after testing transport

DE has earned its place as the benchmark: it beats simple maps on CF development
anchors and the September gym-level audit. Its October EC-Final/online offsets
are nevertheless a specific failure hypothesis. Dropping log field size alone
was already tried; that is not a new structural solution. Solve rate, conditional
SE and binary/survival disagreement can all carry population effects.

Run a **field-composition experiment** on the same audited problems:

1. Estimate reference team abilities from other appearances. Split each board
   into disjoint training and target groups at the participation/replay level.
2. Change the training field's ability and context mix by prespecified sampling;
   keep the held-out target field fixed. Compare equally sized samples as well
   as size changes, and repeat the sampling with fixed seeds.
3. Refit difficulties and feature summaries on each sample. Evaluate prediction
   on the unchanged target field and changes in calibrated difficulty. Distinguish
   ordinary sampling/prior shrinkage from systematic drift with field composition.

Compare four frozen calibrators: current DE, binary affine, a constrained
binary/survival blend without evidence corrections, and a small correction using
performance relative to a fixed reference ability distribution. Learn every map
and any reference distribution from training data only. The last option is an
experiment, not a claim that standardized features become field-independent.

Monitor changes in within-set ordering, sparse-tail behavior and contest-level
bias. Prefer the simpler model if it transports comparably. Do not force identical
ratings across contexts when the underlying task version or conditions differ.
Robust cross-group linking offers a useful diagnostic precedent, but does not
remove the need for comparable measurements: [Halpin, robust DIF scaling](https://arxiv.org/abs/2207.04598).

### 3. Make performance and team history separate estimators

The October forecast artifact reports a much larger gain from member carry-over
than from dynamics:

| Comparison | Pair accuracy | Scope |
|---|---:|---|
| Static → dynamic q=50 | 0.7931 → 0.7936 | 26,469 history rows |
| Static → online-share correction | 0.7931 → 0.7949 | Same history population |
| Flat new-roster prior → member prior | 0.6907 → 0.7335 | 32,684 history/new-roster rows |

These are historical research results, not rerun gains or directly comparable
effect sizes across populations. Revalidate them under the stricter protocol
below before promotion. Start by carrying known members' previous team evidence
into a new roster's prior, with uncertainty for missing members. Do not interpret
three copies of one old team's rating as three independent measurements.

Replace transitive roster equality with partial pooling only after adjudicating
identity edges. Exact repeated rosters can share a team state; related rosters
can borrow evidence without becoming identical. Fully individual dynamic skills
plus a team effect are a later candidate: people who always compete together
cannot be separately identified by these standings.

For observed performance, compare current event-rank inversion against a weakly
regularized completion-based appearance estimate using difficulties learned
without that appearance. Retain penalty information in a conditional timing or
same-solve-count ordering model; binary Rasch alone cannot distinguish teams
with equal totals. Do not multiply full rank and solve likelihoods as though they
were independent evidence: the rank already contains the solve count.

Calibrate performance against held-out verified team evidence and future outcomes,
not only problem CF labels. The 54 elite CF-linked teams are a limited validation
panel, not coverage of the whole ability range. Bayesian skill systems such as
[TrueSkill 2](https://www.microsoft.com/en-us/research/publication/trueskill-2-improved-bayesian-skill-rating-system/)
are useful alternative performance baselines; they do not independently rate
each problem from a final ordering.

### 4. Give time a separate job

The existing survival model treats every task as exposed from contest start.
An acceptance at minute 240 includes task selection, waiting and parallel work.
The September timing audit's conditional PIT increased from 0.49 for first solves
to 0.82 for the eleventh or later solve. Replacing the exponential hazard with
another hazard family would still leave this exposure assumption unresolved.

Use the cached logs for a small pilot: check time units, final verdicts, freezes,
team/problem joins and exact score reconstruction. Recover actual dates and
duration first; retain verified zero-solve participants. A first submission is
evidence of activity, not the start of thinking. An absent submission does not
mean the task was never read.

Compare binary completion alone with a separate deadline-aware conditional timing
model and, later, a joint submission/acceptance process. Define exactly whether
time predicts completion, same-total penalty, or implementation burden. Check
held-out time distributions by solve order, not just an aggregate CF score.
Separate speed and ability have a precedent in
[van der Linden's hierarchical framework](https://research.utwente.nl/en/publications/a-hierarchical-framework-for-modeling-speed-and-accuracy-on-test--2/),
but ICPC acceptance times are not individual exam-item response times.

## Experiments in order, with decisions attached

| Order | Experiment and smallest useful implementation | Main check / stop condition |
|---|---|---|
| 0 | Freeze source hashes, exact-date panel, mode labels, canonical tasks and split manifests; repair release provenance | Reproduce baselines and scoreboards; unresolved joins stay excluded from the verified panel |
| 1 | Contextual binary fit: offset, then optional strength slope | Better whole-appearance log loss/Brier and event transfer; stop adding terms if no supported residual effect |
| 2 | Field-composition/calibration transport experiment | Lower target-field prediction error and less systematic drift; CF nested LOCO and external guards remain visible |
| 3 | Member prior; independently test appearance effect and modest random walk | Rolling-origin rank log loss and cold-roster predictions; improve matched populations, not aggregate scores through coverage changes |
| 4 | Recorded-duration/confirmed-participation pilot, then separate timing | Reconstruct scores; improve deadline/tie predictions without degrading completion calibration |
| 5 | Canonical shared-task linking, small task-skill interactions, content priors | Held-out task/context transfer; expand only with enough independent bridges and evidence |

Experiments 1 and 2 have the clearest connection to the known rating defects.
Experiment 3 has the strongest historical forecast signal. Experiment 4 now has
a local starting dataset. Do not run a large search across all combinations before
the individual mechanisms pass their tests.

## Evaluation must follow the intended use

Maintain separate scorecards:

- **Completed-contest problem ratings:** task-purged nested CF LOCO, region/type
  transfer, calibration transport and gym/Kattis/AOJ checks. Target standings
  are valid inputs here; held-out CF labels are not.
- **Unseen team appearance on a measured set:** remove all of that appearance's
  responses and replay duplicates. Other teams may measure the set, but their
  outcomes must not be described as pre-contest information.
- **Before-contest forecasts:** use only earlier results and identity evidence
  available at the cutoff. Predict rank/medal distributions directly for new
  sets; do not use difficulties fitted from their final standings. Report
  contest-balanced metrics as well as row/pair-weighted metrics so huge online
  boards cannot dominate the conclusion.
- **Historical performance:** check rank/tie behavior, stability when unrelated
  mirror rows are added, and consistency on independently linked team panels.
  Validate uncertainty separately from accuracy of the point estimate.

`dynamic_rating` currently builds identity from the full dataset before monthly
fitting. It dates mirror rows by their parent contest and uses proxy dates.
Its solve score uses full-data `b0`, then fits a target-contest level on half the
rows; member-prior training targets also use `b0`. Thus that solve score is a
retrospective ruler comparison, not a strict forecast. The pair-order score does
not use `b0` directly, but still needs a cutoff-specific identity/date audit.
Replay identity building within each cutoff, fit member-prior targets within the
tuning era, and test date-sensitive results on a recorded-date subset.

Freeze all feature selection, context definitions and hyperparameters before a
new confirmation set. The 15 CF contests and the inspected 2024–2026 forecast
period are development evidence now. Repeatedly selecting a method on them can
overfit the evaluation procedure even with nested folds inside an individual run:
[Cawley and Talbot](https://www.jmlr.org/beta/papers/v11/cawley10a.html).

Use paired contest resampling for differences, plus a team/season dependence
sensitivity analysis where teams recur. Save per-contest errors, coverage,
convergence and all tested variants. Require an improvement on the intended task
with an interval supporting its direction and no unexplained important subgroup
regression. An underpowered result stays inconclusive; a nominal five-point CF
cutoff is not a universal statistical significance rule.

## Alternatives worth retaining or rejecting

| Alternative | Decision |
|---|---|
| Current survival + DE | Keep as the problem benchmark while developing the replacement; preserve its measured calibration advantage |
| Contextual binary + separate timing | Preferred structural candidate: addresses the measured context and timing mechanisms |
| Elo/Glicko/TrueSkill-style rank-only system | Useful cheap team-performance challenger; loses per-problem evidence and cannot replace problem estimation alone |
| Literal incremental CF-style updates | Low priority: the existing filter lost to joint refitting; new claims need a materially different experiment |
| Multidimensional IRT / matrix factorization | Later: first demonstrate reproducible team-by-task-family crossovers; sparse rosters and disconnected fields make a large latent model fragile |
| New TabFM/LLM rating layer | Low priority: managed TabFM lost to DE; corrected LLM calibration did not establish a gain. Content may help cold/rare tasks only under task-disjoint validation |
| More arbitrary prior, hazard and discrimination sweeps | Low priority until participation and evaluation are fixed; they do not create missing identification |

Eventually ship model-based uncertainty for abilities/performance and separately
validated CF prediction intervals for problems. Conditional curvature SE alone
omits shared ability/difficulty uncertainty and calibration error. Begin with
contest/identity sensitivity, joint-curvature estimates and held-out residual
coverage; evaluate zero/one-solve problems separately. Where the data only support
a bound or unstable ordering, show that rather than an unjustified precise rank.

## Missing evidence and reproduction

Still missing: audited participation mode/exposure and actual mirror attempt
dates for much of the joint dataset; broad external ability anchors; a fresh,
untouched confirmation set; exact task-version checks; and
`data/gym_checkpoints/api_standings.json`. Local XCPCIO logs require joining and
completeness checks before use. No missing observation was fabricated. The
[ICPC Contest API](https://ccs-specs.icpc.io/2026-01/contest_api.html) supplies a
schema for start/duration, submissions and judgements where a source supports
them; that specification does not guarantee access to any particular archive.

Reproduce the new diagnostics from the repository root:

```bash
./.venv/bin/python -m scripts.rating_rethink_audit > /tmp/rating_rethink_audit.json
./.venv/bin/python -m arch_b.predict_eval
```

The first command asserts exact reproduction of the shipped rounded DE points,
reruns its nested development LOCO, inventories inputs and reports hashes. It
does not refit the saved binary/survival difficulties. The second refits both
models on the grouped imputation split. Neither command changes production
outputs. Cached board files are gitignored, so another checkout may report less
coverage. Historical mechanisms and forecast gains above are cited from existing
repository reports/code, not represented as new experimental results.
