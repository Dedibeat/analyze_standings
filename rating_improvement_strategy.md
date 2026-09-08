# Improving fit and ratings beyond the benchmark

Review date: 2026-09-06. Code inspected: `c181982`. This is a research
recommendation, with fresh read-only data diagnostics; no candidate model was
implemented, ratings regenerated, or paid inference dispatched. The repaired
evaluation and its remaining limits are recorded in [experiment_review.md](experiment_review.md).

The largest opportunity is to distinguish the processes that produce a standing:
problem understanding, team composition, problem choice, implementation, and the
contest clock. The current scalar model absorbs all of them into ability and
difficulty. That can be useful for describing a contest, but it does not establish
a context-independent difficulty or a separately calibrated team rating.

My priority is a small collection of informative cases and structural experiments.
No numerical improvement is promised. Agreement with CF remains useful evidence,
but the proposed changes should also explain repeated tasks, participation, and
team behavior that the existing benchmark cannot resolve.

## 2026-09-08 proposed experiment roadmap

The later [experiment roadmap](experiment_roadmap.md) is the current
proposed-only sequencing note for calibration audits, fresh confirmation, and
structural research. Its dated status matters: it does not replace the evidence
or limitations below, and it authorizes no run, data collection, model change,
or deferred TabFM comparison.

## What the current data actually supports

Diagnostics loaded the shipped configuration with
`load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)`: 260 contests, 37,576
identities, 3,159 problem appearances, 73,023 retained rows, and 923,842 cells.
Raw-row checks use the same source order, contest deduplication and duration
filter, before the zero-solve retention rule.

| Observation | Fresh count | Interpretation and limit |
|---|---:|---|
| Fitted cells with an omitted source problem entry | 525,259 (56.9% of all cells; 88.4% of non-solves) | A missing entry is an observed non-solve, but does not reveal thinking time or why the team skipped submission. |
| Non-solves with positive `wrong_attempts` | 48,769 | There is some evidence of submission activity; its timestamps are absent. |
| Dropped rows with zero listed solves but positive wrong attempts on a listed problem | 2,052 | Zero solves does not imply absence of participation. This alone does not establish a full, serious contest attempt. |
| Dropped rows without listed solves or positive wrong attempts | 9,550 | Participation remains ambiguous. |
| Problem appearances with zero / one / two-to-five solves | 121 / 104 / 337 | The hard tail needs stronger evidence and explicit prior sensitivity. |
| Repeated contest/ability-identity groups | 281, containing 295 excess rows | Participation keys now preserve these rows, but their shared ability still needs justification. |
| Fitted identity components containing multiple source rosters | 2,436; maximum 15 rosters | This count includes zero-solve source rows used by identity resolution, so it is not the earlier retained-roster-only audit count. |
| Such components with no member common to every source roster | 142 | Transitive roster links need not identify a fixed group of people. Turnover is a possible explanation; these are audit candidates, not proven false merges. |
| Cross-contest repeated non-null QOJ problem IDs | Five IDs, ten appearances | The two Luxor World Finals offer a small existing test of task identity and context. |

None of the shipped contest records has a recorded duration or exact start-time
field. Cells carry final acceptance time and wrong-attempt count, without a
submission timeline. The maximum solve time among retained contests ranges from
3.867 to 5.533 hours; that is a proxy distribution, not measured contest duration.

## 1. Separate difficulty from the contest clock

In [survival.py](arch_b/survival.py), an unsolved cell contributes exposure through
the entire inferred window. A solved cell contributes its acceptance timestamp
relative to contest start. Consider two otherwise comparable tasks: one accepted
at minute 240 after 20 minutes of work, another after 240 minutes of work. Their
timestamps do not distinguish those histories. Changing an exponential hazard
to a Weibull hazard does not supply the missing start-of-work information.

The proposed target is explicit: difficulty for a reference team, on first
exposure, under specified contest conditions. Keep a separate measure of time
burden. A short task needing one difficult insight and a lengthy task needing
routine implementation can then receive different descriptions even when their
contest completion rates match. These are hypotheses about what users need;
the current data cannot identify pure insight or active implementation time.

First experiment: fit binary completion and a separate conditional acceptance-time
model, allowing team speed and problem time burden to differ from ability and
difficulty. Treat the initial time component as descriptive until richer logs
identify more. Any time model restricted to completed solves must account for
the deadline and selection of successful teams; an uncorrected regression on
solvers is insufficient. Test whether borrowing time information improves
completion predictions without forcing the two traits to be identical.

Separate response and time models have a psychometric precedent in
[van der Linden's speed/accuracy framework](https://research.utwente.nl/en/publications/a-hierarchical-framework-for-modeling-speed-and-accuracy-on-test--2/).
Applying it to ICPC requires additional modeling of task choice and parallel
team work; exam-item response times are not interchangeable with acceptance
timestamps. Begin with the separation experiment before attempting a complete
simulation of three people sharing a computer.

## 2. Learn from engagement and failure

The 2,052 dropped rows with recorded wrong attempts provide a concrete pilot
population. Recover their provenance and distinguish confirmed participation,
partial attempts, repeated virtual attempts, and unresolved rows where the
sources allow it. Positive submission evidence is useful even when the team
solves nothing. Blanket inclusion of all zero rows was already tested; explicit
participation modeling is a different hypothesis.

For a small source-audited contest panel, retain submission timestamps and
judgements, original/virtual status, actual duration, and actual date. Preserve
the full contest response matrix: omitted cells remain non-solves for the
completion target. Their unknown effort belongs in an engagement model, rather
than silently deleting them from the denominator or treating a first submission
as the exact start of thought.

The [ICPC Contest API](https://ccs-specs.icpc.io/2026-01/contest_api.html)
defines start time, duration, submissions and judgements. Access and historical
coverage must be checked per contest. The existing
[XCPCIO collector](scripts/fetch_xcpcio_standings.py) already reads config and run
files, so preserving their richer evidence is a concrete extension. Availability
of the desired boards was not established in this review.

The decisive question is whether the extra evidence explains skipped tasks,
failed attempts, late completions and off-days. A lower aggregate error alone
would not show that the intended mechanism had been learned.

## 3. Treat shared members as related ability, not identical ability

`member_identity` unions rosters sharing two normalized names, transitively,
and the fit assigns the final component one time-invariant ability. For example,
ABC can link to ABD, then ADE, then DEF: there need not be a person common to
the whole chain. That is a stronger statistical assumption than retaining a
team's institutional identity through substitutions.

First, adjudicate a manageable sample of the 142 components above, starting with
those that carry cross-contest bridges or contain multiple rows in one contest.
Record evidence for each edge: stable account, exact roster, shared members,
recurring name or inferred affiliation link. The ability consequences of an
edge deserve scrutiny as well as its entity-resolution plausibility.

Then test separate roster/appearance performance variables with partial pooling
through corroborated members or team history. Begin with one shrunk appearance
effect; add time evolution only where dates support it. This preserves useful
connections while allowing a substitution or an off-day to change performance.
An entire appearance must be withheld when evaluating the ability to predict it.
Individual abilities may be unidentifiable when members always compete together;
those cases should retain a team-level estimate.

[TrueSkill Through Time](https://www.microsoft.com/en-us/research/publication/trueskill-through-time-revisiting-the-history-of-chess/)
provides a precedent for coupling abilities across time and inferring skill from
team outcomes. Its existence does not establish an ICPC gain. In particular,
retrospective smoothing and forecasting are different uses: future performances
can inform historical ratings, but cannot enter an earlier forecast.

## 4. Build bridges through the problems themselves

The loader registers a difficulty by `(contest_index, problem_label)` even when
the same QOJ `problem_id` appears elsewhere. The 46th and 47th Luxor Finals,
QOJ contests 1661 and 1662, contain these shared IDs:

| QOJ problem ID | Task | Labels in 1661 / 1662 | Saved CF-mapped difficulty in 1661 / 1662 |
|---|---|---|---:|
| 8680 | Turning Red | P / G | 1844.7 / 1921.4 |
| 8683 | Bridging the Gap | S / J | 3363.1 / 3324.1 |
| 8677 | Carl's Vacation | T / D | 2169.0 / 2150.9 |
| 8676 | Three Kinds of Dice | V / C | 2639.6 / 2632.8 |
| 8674 | Riddle of the Sphinx | W / A | 1794.3 / 1799.8 |

The official [46th problem book](https://icpc.global/worldfinals/problems/2022-ICPC-World-Finals/icpc2022.pdf)
and [47th problem book](https://icpc.global/worldfinals/problems/2023-ICPC-World-Finals/icpc2023.pdf)
corroborate the shared tasks. Most estimates already agree closely: this is a
useful consistency check, not evidence of a large current scale failure.

Pilot a canonical task difficulty linked to separate contest appearances,
after checking versions and duplicate response provenance. Keep genuine
responses from both fields. Shared tasks can transfer scale without relying
entirely on team-identity chains. If a context effect is later added, it must be
constrained/pooled so it cannot freely cancel every shared difficulty.

This also supplies a small study of the same task under a different surrounding
problem set. Compare its completion and timing after accounting for field
strength estimated from other evidence. A remaining difference could reflect
task choice, sampling noise, or model error; the two fields were not randomized.
Forcing both exported numbers to agree is not validation of the model.

Dates matter here too: the source years are 2022 and 2023, whereas the
[official Luxor event page](https://icpc.global/worldfinals/scoreboard/2023/scoreboards/index.html)
places both finals in April 2024. Competitive-season labels and event dates need
separate fields before fitting temporal abilities.

## 5. Collect observations chosen to resolve uncertainty

The historical additions show that more standings need not supply the missing
kind of evidence. A potentially better collection unit is a verified team near
the uncertain problem's difficulty, or an independent bridge between weakly
connected fields. A famous elite team already observed in many contests may
contribute less than a moderately strong team in a poorly anchored field.

Use the joint ability/difficulty information matrix to identify uncertain
contrasts and influential bridges. Under the current models each observation
contributes curvature proportional to `(dtheta - db)^2`, giving a weighted
team/problem graph plus prior precision. Connectivity alone is insufficient:
the precision of a contrast depends on edge information and alternative paths.
This is a local approximation under the model, not a measure of identity truth.
Graph-based experimental design has a related precedent in
[optimal designs for discrete choice models](https://pmc.ncbi.nlm.nih.gov/articles/PMC12274245/).

An unconventional acquisition experiment is a small voluntary calibration set:
teams with corroborated rosters from different contest communities attempt
overlapping unfamiliar tasks under the same time and assistance conditions.
Balance task allocation, record prior exposure, and include new bridges and
hard-tail tasks. Choose the set to reduce uncertainty in useful comparisons;
retain independent tasks for checking transfer. This requires new human
participation and has not been arranged or authorized here.

## 6. Measure why a task is hard, and whether it is hard for this team

After a reliable scalar baseline, test one or two prespecified skill contrasts
using well-observed teams: for example, geometry familiarity or implementation
burden. A reproducible crossover, where similarly rated teams switch their
relative success across task families, would justify a limited team-by-task
interaction. A pooled score can miss that behavior. Start with repeated
within-team evidence; a region-wide offset cannot distinguish it from population
composition or statement differences.

Existing LLM tags are candidate annotations, not ground truth. A useful content
workflow would extract prerequisites, the key proof/insight and implementation
requirements with supporting editorial passages, then have people verify a small
sample. Evaluate whether these features explain held-out residual behavior.
The corrected pairwise experiments do not justify treating another absolute
LLM rating as an established improvement.

A stronger but more expensive experiment separates discovery from execution:
randomly assign comparable teams to statement-only, a standardized conceptual
hint, or editorial-supplied conditions on different tasks. Measure completion
and active work time, with task allocation counterbalanced across groups and
no team seeing the same task in multiple conditions. A large benefit from the
hint suggests a discovery bottleneck; continued difficulty after an editorial
suggests another burden. These are intervention-specific effects, not universal
intrinsic difficulty. This is a proposed human study, not a current capability.

## What better ratings would look like

Keep a convenient headline contest-difficulty number, accompanied by evidence
that changes its use: first-exposure/context qualification, sparse-data status,
time burden when supported, and an uncertainty statement appropriate to the
target. For the 225 zero/one-solve appearances, compare reasonable priors and
report unresolved ordering or a justified one-sided bound where appropriate.
Standings still provide field-dependent evidence; sparse does not mean none.

Distinguish problem difficulty, current team ability and a particular contest's
performance. The viewer currently applies the problem-CF map to all three;
`export_viewer.py` explicitly calls the latter two an unvalidated extrapolation.
A shared coordinate system is useful but does not validate all three meanings.
The common monotone map preserves the equality `theta = b`; nonlinear mapping
does not preserve one universal probability formula based on mapped point gaps.
Validate ability/performance against the relevant team evidence before making
strong CF-equivalence claims. The existing cohort-centered CF prior does not
test absolute anchoring.

Useful success checks extend beyond CF RMSE: shared tasks transfer across fields;
rankings survive removal of one uncertain identity bridge; genuine zero-solve
attempts are represented; a future appearance is predicted without its outcomes;
and practice recommendations distinguish unfamiliar concepts from time burden.
For each experiment, prespecify the cases and counterfactual behavior it should
explain, and retain the existing metric as a regression check.

## Recommended next sequence

1. Build a small source-audited panel from the five shared tasks, zero-solve rows
   with submissions and influential roster chains. Verify versions, participation
   provenance, actual dates and duration availability. This is the cheapest way
   to make the next model experiment interpretable.
2. Test a common-task fit and a single shrunk appearance effect separately.
   Check transfer on the panel and stability of the other ratings; equality
   imposed by construction does not count as predictive success.
3. On contests with usable timelines, test completion/time separation and
   engagement. Expand only if it explains the intended behavior. Target new
   bridge observations or a human hint study when existing data cannot identify
   the cause of an error.

Highest immediate confidence: better provenance, consistent task identities and
clearer rating meaning. Highest model upside: separating completion, speed and
participation. Most informative unconventional investment: controlled common-task
attempts that measure the missing distinctions directly.

## Calibration and Google's TabFM (2026-09-06 follow-up)

Calibration deserves a focused experiment alongside the structural work above.
There are three separate targets: mapping latent difficulty to CF points,
calibrating solve probabilities, and quantifying prediction uncertainty. A better
CF mapping does not establish either of the other two. Reproducing `_loco_rmse`
on the saved survival records gives **246.9061 affine / 245.4277 gym-shaped**,
185 problems in 15 contests. The historical 22-point shape benefit is not the
current benefit. Keep a plain affine control in the next calibration experiment;
the earlier paired interval [-9.63, +6.16] does not establish a current shape win.

Google's [TabFM announcement](https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/)
describes regression/classification by in-context learning, with pretraining on
synthetic tables. It still needs labeled examples from our task as context;
zero-shot here means no task-specific weight training, not no CF labels.
That makes it a plausible experiment on the 185-problem calibration table.
Its general tabular prior supplies an inductive bias, not additional evidence
about ICPC ability, engagement, or unanchored regions.

The most promising first use is a residual correction:

`predicted_CF = affine(b_survival) + lambda * TabFM(features)`

The TabFM target is the CF residual relative to the baseline. Start with a small
prespecified feature set: raw survival difficulty, binary/survival disagreement,
conditional fit SE, solve/field counts, and summary timing and field-strength
information. Binary and survival values share the internal coordinate system
but have different scales; their disagreement needs empirical interpretation,
not a presumed direction. Timing summaries need missing indicators for unsolved
problems. Use raw fit evidence, not a CF-calibrated feature computed with the
held-out contest's labels. Region and contest IDs should not enter the first
pilot as shortcuts for the limited anchor coverage.

This asks whether two problems with the same current difficulty require
different corrections because their evidence differs. With only `b` as input,
TabFM mainly supplies another one-dimensional curve. Extra covariates could
recover useful information discarded by the scalar estimate. Such a correction
can change problem ordering, so it is an additional predictive model and loses
the shipped monotone map's automatic ordering guarantee. Check any reorderings
on the shared-task panel and independent outcomes as well as CF errors.

Compare affine, the locked gym shape, one simple regularized feature regression,
and TabFM residual correction on the same outer contest folds. Learn baseline
coefficients, preprocessing and residual models using training labels only;
choose features, context sampling and `lambda` inside the training contests.
Keep the outer contest's CF labels out of every prediction step. Standings from
that contest are legitimate inputs when rating completed contests; they would
not be available for a future-contest forecast. Keep repeated canonical tasks
together where applicable. The 15 repeatedly inspected contests remain a
development set, so confirmation needs fresh contests and checks of transfer
to different fields.

The limitation is coverage rather than the bare sample count: 185 examples can
support a small-data learner, but they represent only 15 contest environments
from three regions. The saved raw anchor range is [1177.9, 2936.1], and 94 fitted
problem appearances lie outside it. Inspect tail behavior explicitly; neither
a model's tabular pretraining nor a distributional output establishes reliable
extrapolation or calibrated uncertainty there. Treat residual shrinkage toward
the affine baseline as a candidate evaluated in the inner folds, not a guaranteed
improvement.

A more targeted use is solve-probability calibration: learn systematic departures
from the current ability/difficulty link using predictions and evidence available
at the intended prediction time. Construct features without the held-out
responses, including refitting any ability/difficulty estimates that would
otherwise contain them. If this reveals repeatable dependence on roster state,
timing or field composition, it provides a concrete hypothesis for improving the
generative model. Directly flattening all response cells into a supervised table
does not automatically preserve the joint model's identity links or yield an
identifiable problem-difficulty scale.

Practical constraints checked in the [official repository](https://github.com/google-research/tabfm):
inference uses sampled bounded contexts (the documented estimator default is
100 context rows), so a pilot should record context coverage and sampling
stability. The default v1 weights have a separate license restricting them to
non-commercial, non-production use; the source code is Apache-2.0. A research
comparison and deployment in the published viewer therefore require different
considerations. No installation, weight download, TabFM inference, or calibration
change was performed for this assessment. The numerical results above are a
read-only reproduction of the existing maps, not a TabFM result.

## Reproduction limits

Counts above are direct reductions of the local joint inputs, not a new metric
run or estimates of a candidate's improvement. Roster diagnostics include all
source rosters in components resolving to a fitted identity. Repeated-task
values come from the saved calibrated artifact. QOJ's public contest pages
redirected to login; the public ICPC books supplied independent corroboration.
Exact task-version/test-data equality was not exhaustively audited.

The shipped inputs lack submission timelines and recorded contest dates/durations;
the raw gym checkpoint `data/gym_checkpoints/api_standings.json` is also absent.
No missing observations, effort times, identity adjudications or raw experiment
snapshots were reconstructed by inference.

SHA-256 of the inspected inputs/artifact:

```text
54677cf98b452e115e24bcd2149b609d00a50e74fa783ad4865e8162b2446a94  data/tagged.json
6c72e5eaa2de7eb536cd784dcdcab7288c89f6a6c5edbd5306ab017b8fc52ec1  data/icpc_2020_2021.json
84961ea5542fa1281a567e54cacc14ac91311d6599dcf29470d15c7dc456cb84  data/petroz_2022_2026.json
63eba1ca8a996a97e9e471553ce67ed058ffc6cd197241df0330372ed88329de  data/wf_tagged_format.json
8c74b4b963ce8f33027624e53c8dde320180704d93a96714e5e802e7ab4b7615  data/ucup_s3.json
021e02abd20750ae77357a02922da1ac754572f923735cd28501344692732e23  data/ucup_s4.json
a7d9582797632eada113c4a02ba03f440ad91ed5d29dac569a7408b0fb008087  output/problem_ratings_calibrated.json
```
