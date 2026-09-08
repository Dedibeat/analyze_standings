# Experiment roadmap: calibration and rating evidence

Status (2026-09-08): **proposed only; none of the experiments below has run.**
This is a decision aid for later sessions, not a frozen protocol. It authorizes
no model, data, output-artifact, deployment, or TabFM change.

## Starting point and boundary

Freeze the current calibration candidate before seeking new confirmation:
`raw_b + binary_minus_survival + conditional_fit_se + solve_rate +
log_field_size` (DE). On the reused 185 CF/QOJ anchors in 15 completed contests,
DE scored 226.5661 LOCO RMSE, versus locked gym 245.4277 and prior DET 229.6269;
its calibration-label LORO result was 225.7640, versus gym 246.0305 and DET
228.3597. Inner-only selection chose DE in all 15 LOCO folds. These are useful
development observations, not independent confirmation, a future-contest
forecast, probability calibration, or evidence that the underlying raw fit
improved.

The anchor raw-difficulty range is [1177.9, 2936.1], with all 94 outside-support
appearances above that maximum. The descriptive full-refit DE correction range is
-402.5 to +166.9 points for those 94 tail appearances. Across all 3,159
appearances, 16 DE predictions fall outside 800–4000 without clipping (raw: 10).
These are support signals for audit, not errors by definition.

The cached full-refit proxy picture is deliberately not a selector: pooled gym
Spearman changes .9691 to .9780 with DE, Kattis .7955 to .7760, and AOJ .5685
to .5642. It is non-OOF. Luxor shared task 8674 changes from a 5.1-point raw
gap to 101.0 under DE; a common task can still have a real context difference,
so this is an audit case, not an equality target. Details and provenance are in
[the ablation report](calibration_ablation_report.md),
[frozen plan](calibration_ablation_plan.md), and
[machine-readable artifacts](output/calibration_ablation.json).

Existing evidence entrypoints are
[`arch_b/calibration_experiment.py`](arch_b/calibration_experiment.py),
[`arch_b/calibration_ablation.py`](arch_b/calibration_ablation.py), and
[`arch_b/calibration_ablation_transfer.py`](arch_b/calibration_ablation_transfer.py),
with saved [baseline](output/calibration_experiment.json),
[ablation](output/calibration_ablation.json), and
[transfer](output/calibration_ablation_transfer.json) artifacts. No general
resampling, task-context, negative-control, abstention, or simulation harness
exists yet; any future harness and row-level audit output are planned artifacts,
not current commands or files.

## Rules for every proposed run

- State whether the target is completed-contest context calibration, a new
  future-contest forecast, probability calibration, uncertainty, or a structural
  rating question. Do not borrow evidence between targets.
- Version input hashes, row/task/identity provenance, candidate definition,
  folds, and deterministic audit-example selection before inspecting outcomes.
  Keep canonical task and outcome-linked groups together where the question
  requires it.
- Record full-refit diagnostics separately from OOF predictions. Full-refit
  inspection can find failures but cannot validate the candidate.
- The reused 185/15 anchors cannot become confirmation. A bootstrap of saved OOF
  predictions is conditional on those fixed predictions: it cannot account for
  historical adaptive model search or constitute fresh confirmation. Any
  refit/reselection bootstrap must explicitly state which uncertainty it includes;
  overlapping LOCO folds are not independent replicates.
- Pre-register practical tolerances, comparison hierarchy, and stop conditions
  for the particular data before running. No generic numeric threshold here is
  validated as a promotion rule.
- A diagnostic red flag triggers investigation or a narrower claim. Promotion
  requires a fresh, frozen, fit-for-purpose confirmation set plus acceptable
  provenance and safety checks; it is not implied by a lower reused-anchor RMSE.

## Dependencies and resume order

1. Confirm availability and legal/ethical scope of any new labels, task-version
   evidence, submission evidence, or human study. Do not infer missing dates,
   durations, raw gym standings, cached raw field-strength features, or task
   equivalence. The `data/gym_checkpoints` directory is absent.
2. Freeze the DE candidate, raw-coordinate convention, data hashes, and a
   proposal-specific analysis sheet before reading new outcomes.
3. Run the low-cost audits below first. They decide whether a fresh confirmation
   is interpretable and which structural uncertainty most needs data.
4. Assemble a genuinely new frozen confirmation set only after its source,
   temporal meaning, and leakage boundaries are documented. It is not currently
   assembled in this repository.
5. Consider a model-changing study only if an audit supplies a concrete failure
   mechanism and the required data/authorization exist. TabFM remains deferred.

## Immediate proposed experiments

### 1. Deterministic largest-correction audit

**Hypothesis.** A small set of large DE corrections, including both apparent
wins and losses, may expose off-support extrapolation, context mismatch, or a
provenance error that pooled RMSE hides.

**Design and controls.** From saved OOF predictions, select examples by a
written deterministic rule: the top ten largest absolute DE-minus-raw
corrections, top ten DE improvements, and top ten DE deteriorations in absolute
CF error, taking unique rows in that order and resolving ties by stable row ID.
Include all five Luxor shared tasks as a fixed appendix. Make a separate,
visibly labelled full-refit list only after reconstructing frozen full-anchor
maps through the existing helper API and saving a **planned** row table; the
transfer JSON contains aggregates, not a row-level prediction table. Never merge
this descriptive list with OOF evidence. Inspect task, contest, feature
completeness, anchor linkage, and raw-coordinate provenance.

**Observe beyond RMSE.** Correction sign/magnitude, anchor raw-range support,
feature missingness, rank/order changes, task version, and whether examples
cluster by contest or identity. **Artifacts.** Versioned selection manifest,
two audit tables, source links/notes, and an issue log. **Cost.** Low compute;
moderate manual source review. **Decision.** A reproducible data/provenance
fault stops interpretation until repaired; coherent hard cases become inputs to
the context/identity studies, not grounds to retune DE.

### 2. CF-versus-proxy disagreement decomposition

**Hypothesis.** The opposing gym and Kattis/AOJ proxy directions could reflect
region, contest, rank-position, task matching, or source-provenance composition
rather than a universal candidate failure.

**Design and controls.** Freeze DE and raw maps; compare matched and explicitly
unmatched cohorts, report both canonical-task-only and whole-anchor-contest-plus-
task purges, and pre-state all, task-purged, and strict cohorts. Stratify by
source, region where known, contest, raw support, and rank/solve-count
composition. Retain each proxy's native metric; do not pool unlike metrics.
Audit matching and task-version provenance before interpreting a stratum.

**Observe beyond RMSE.** Cohort overlap, composition shifts, within-contest
orders, correlations of correction with support/missingness, and match confidence.
**Artifacts.** Cohort manifest, contingency summaries, matching audit, and
separate non-OOF diagnostic report. **Cost.** Low compute; moderate provenance
review. **Decision.** Unexplained disagreement is a red flag and blocks a
global claim; a well-specified contrast can define the required fresh transfer
set, not choose a calibration on the proxy outcomes.

### 3. Shared-task and context decomposition

**Hypothesis.** Repeated tasks may separate a common task component from small
contest-context effects; neither forced equality nor unrestricted independent
ratings answers that question.

**Design and controls.** Start with a source-audited panel (including Luxor)
whose task versions and contest context are corroborated. Compare fixed raw-map
diagnostics, a common-task-only representation, and a common task plus one
shrunk context/appearance effect. Hold out whole task-context appearances, not
just cells; keep the raw coordinate consistent across any refit. Do not treat
unverified same labels as the same task. The current five IDs across two Luxor
events are a descriptive pilot, not five independent replications. Only after
the version audit should a structural pool be considered. Intentionally holding
the same known task in another context is a distinct transfer target; keep it
separate from CF-calibration folds, which purge shared canonical tasks.

**Observe beyond RMSE.** Cross-context residuals, task-gap distributions,
context-effect shrinkage, order stability, and held-out appearance prediction.
**Artifacts.** Task identity ledger, panel manifest, fit specification, and
OOF/full-refit-separated plots. **Cost.** Moderate source audit and modelling.
**Decision.** If common-task identity/context cannot be audited, stop at the
descriptive panel; if a shrunk effect predicts held appearances, prioritize a
separate structural experiment rather than altering calibration directly.

### 4. Coherent team/identity-group resampling

**Hypothesis.** A few identity bridges, teams, or contests may make fitted
evidence and calibration unusually sensitive.

**Design and controls.** The concrete primary is conditional within-contest
field sensitivity: for one preselected contest at a time, subsample its resolved
identity blocks without replacement at 50%, 75%, and 100%, retaining every
participation row and response cell for each kept block. Other contests and the
union mapping stay fixed. Use 20 pilot draws per reduced fraction and the 100%
case as a deterministic control; these defaults are proposed, not run or
validated. Do not row-bootstrap cells or identity edges. Whole-identity removal
across contests is a separate bridge/leverage axis. Freeze contest eligibility
and the observation window in the primary arm so a changed latest solve is not
confused with field size; make duration re-inference a separate sensitivity. Do
not drop cells or rebuild identity unions as a resampling side effect; test
contested identity edges on a separate sensitivity axis. Run two labelled
analyses: (a) an **artificial fixed-latent calibration sensitivity, not a
coherent new-data/refit uncertainty estimate**, holding `raw_b`, disagreement,
and conditional fit SE fixed while recomputing solve rate and `log1p(field)`;
and (b) a full-refit sensitivity that recomputes all features while retaining the
primary duration/eligibility rule. For (b), align to a fixed-prior, unperturbed
reference using predeclared common stable items/identities—never held CF targets—
and report unaligned shifts as well. Examine whether reduced fields widen
uncertainty; do not require exact mean invariance or assume every draw will do so.

**Observe beyond RMSE.** Correction distributions, rank/order changes, feature
uncertainty, connected-component changes, bridge leverage, and failures to
align coordinates. **Artifacts.** Resampling seed/units manifest, eligibility
window, alignment method, replicate summaries, and separate fixed-latent/full-
refit reports. **Cost.** Moderate to high compute and engineering; no new data.
**Decision.** Large sensitivity or unstable alignment is a red flag for
confidence statements; an identified influential bridge moves to provenance
adjudication, not automatic edge deletion.

### 5. Candidate, anchor, and uncertainty leverage

**Hypothesis.** The DE result may be driven by a small set of anchors, contests,
or uncertain evidence regimes despite all-fold DE selection.

**Design and controls.** The primary analysis leaves groups out with fixed DE
and fixed controls, measuring influence without reopening candidate selection.
Run adaptive reselection only as a separate development diagnostic, entirely
inside remaining development data. Separately perturb documented feature
uncertainty or missingness assumptions, never the held labels. Retain the 15/15
adaptive-selection observation as historical, not as a stability proof.

**Observe beyond RMSE.** Candidate-selection frequency, correction dispersion,
anchor influence, support coverage, uncertainty-feature dependence, and tail
behavior. **Artifacts.** Predeclared leave-group schedule, influence table,
uncertainty scenario ledger, and OOF predictions. **Cost.** Moderate compute.
**Decision.** Concentrated leverage requires a broader confirmation design;
stable development sensitivity only advances to fresh confirmation, never
promotion by itself.

### 6. Fresh frozen confirmation

**Hypothesis.** DE generalizes to a new, provenance-audited target population.

**Design and controls.** This cannot start until genuinely new labels and the
prediction-time setting are assembled and frozen. Define whether standings of a
completed contest are available, isolate all model/feature/anchor selection from
the confirmation outcomes, lock DE and controls (raw affine, gym, prior DET),
and choose groups that prevent task/contest/identity leakage. Include a transfer
population rather than assuming the current three regions suffice.

**Observe beyond RMSE.** Per-contest/region errors, support and tail coverage,
order changes, uncertainty behavior, source matching, and predeclared failure
cases. **Artifacts.** Data card, hashes, split manifest, blinded evaluator, and
confirmation report. **Cost.** Unknown; depends on unavailable data and any
necessary authorization. **Decision.** Only this kind of result can inform a
promotion discussion; failure or ambiguity retains the current map and directs
work to the relevant diagnostic.

## Longer-horizon research directions

All rows are proposed, not run. They build on the existing
[rating-improvement strategy](rating_improvement_strategy.md); each needs a
separate protocol after the immediate evidence work.

| Direction | Hypothesis and feasible control | Beyond-RMSE observations and artifacts | Cost and decision/stop |
| --- | --- | --- | --- |
| Evidence for uncertainty versus mean | Evidence features may be useful for uncertainty or abstention even if they do not shift the mean. Compare fixed mean maps with conditional uncertainty/shrink-or-abstain rules, using prediction-time inputs only. | Coverage by support regime, interval/abstention behavior, calibration curves; write a support data card and uncertainty ledger. | Moderate. Stop if uncertainty is not evaluable on held outcomes; do not reinterpret it as a mean gain. |
| Completion, speed, engagement | Completion, speed, and engagement are distinct latent processes. On contests with corroborated timelines, compare a completion-only control with a separated model; include zero-solve rows with submission evidence. | Held appearance prediction, time residuals, genuine-attempt classification, zero-solve sensitivity; record timeline/attempt provenance. | High; missing timelines block it. No inferred effort times or dates. |
| Identity and graph bridges | Roster/graph bridges may carry useful scale links while some are fragile. Test targeted bridge removal or alternative corroborated linkage, against a fixed identity policy. | Component/connectivity changes, ability/rating drift, bridge audit ledger, held appearance behavior. | Moderate-high manual audit. Stop when an edge lacks evidence; do not silently delete it. |
| Objective-specific outputs | Problem difficulty, team ability, contest performance, and solve probability need not share one product claim. Define each target and evaluate it against target-specific held evidence. | Separate data cards, calibration/order checks, and user-facing semantics. | Moderate design work. Do not map one score into another without validation. |
| Low-dimensional specialization and bridges | A small specialization dimension or targeted cross-field bridge may explain residual structure better than a global residual correction. Compare scalar control with a strongly regularized low-dimensional extension and targeted bridge observations. | Cross-field task/appearance prediction, shrinkage, bridge leverage, coordinate stability. | High; requires enough corroborated bridges. Stop if dimensions are not identifiable. |
| Negative-control and invariance checks | A bijective task-ID renaming applied consistently to all linked records, plus a row-order permutation, should preserve memberships, canonical-task purges, and predictions up to numerical tolerance. A train-only synthetic noise feature in nested selection can test selection fragility. | Invariance comparisons, null-result distribution, selection frequency, and exact renaming/permutation manifest. | Low-moderate. It detects fragility, not a mechanism or real-world accuracy; investigate non-invariance or noise-feature selection before continuing. |
| Generative numerical simulation | Simulated standings from the frozen generative model can test numerical/refit robustness against a known truth. | Recovery, convergence, coordinate-alignment, and resampling diagnostics; save simulation seeds/specification. | Moderate. It validates behavior under its assumed model only, never real-world fit. |
| Controlled task/context acquisition | Carefully chosen common-task, position/context, or hint studies could identify distinctions unavailable in standings. Require human consent, operational authorization, and a predeclared no-harm protocol. | Completion/time trade-offs, controlled context effects, participant/data governance record. | High and externally dependent. Do not collect or intervene without authorization. |
| TabFM conditional comparison | A tabular prior might be a conditional calibration control after fresh data exist. Compare it only to frozen DE/controls on the same splits, preserving licensing and isolated execution requirements. | Context-sampling stability, support/tail behavior, resource use, and external confirmation. | Deferred by user. Do not install, download, or run it until explicitly authorized. |

## Resume checklist

Before a later session starts a run: confirm authorization and data availability;
name the target; freeze candidate/control versions and hashes; publish split and
selection rules; pre-register tolerances and stop decisions; distinguish OOF,
full-refit, and confirmation outputs; and decide where results and provenance
will be saved. If any item is missing, document the blocker rather than filling
it in by assumption.
