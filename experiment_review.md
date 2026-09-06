# Experiment and implementation review — 2026-09-05

Reviewed revision: `8a351e0`. Scope: the current ICPC standings pipeline,
historical experiment logs, calibration, prediction/medal consumers, and the
Codeforces/LLM pairwise experiments. Findings below distinguish reproduced
defects, statistical limitations, and proposed experiments. This review changes
documentation only; it does not fix code, regenerate ratings, or dispatch inference.

**Resolution note (2026-09-06):** the concrete correctness defects in findings
1, 2, and 5 were repaired after this snapshot, along with the row-specific CF
prior provenance gap and the reproducible parts of finding 3. See the
implementation-resolution section at the end of `details.md`. Research work that
needs missing/new evidence remains open; the historical reproductions below are
preserved as the audit record.

The sparse loader, full-contest observation mask, and single joint fit are sound
structural improvements. The strongest next investment is evaluation correctness.
The evidence does not justify the historical claim that model improvements are
exhausted, nor deployment of the cross-contest LLM offsets.

## Reproduced baseline

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 32 tests pass |
| `python -m arch_b.metric` | Calibrated LOCO 245.4; raw affine 246.9; all guards pass |
| Current joint dataset | 260 contests, 37,576 identities, 3,159 problems, 73,023 rows, 923,842 cells |
| `python -m arch_b.predict_eval`, binary | Log-loss 0.2009, Brier 0.0615, reported AUC 0.9733 |
| Same command, survival | Log-loss 0.2309, Brier 0.0699, reported AUC 0.9673 |

Commands used `./.venv/bin/python`. The prediction command covers only tagged
standings, not the joint dataset. AUC values above reproduce the current code;
they retain the tie-handling defect below. Baseline metric runtime here was 33 s,
not the approximately 5 s described in `program.md`.

## 1. High priority: the cross-contest LLM gain uses held-out labels

Evidence: [llm_crosscontest.py](llm_crosscontest.py), `analyse`, lines 447–459.
The supposedly held-out offset is computed as:

```python
off = float((cf[te] - (ab_ * bt[te] + bb_)).mean())
```

It is added to the survival prediction before scoring that same contest.
Refitting the slopes and shrink factor on training contests does not repair
this direct dependence on `cf[te]`. An unanchored contest has no such labels.
The reported offset correlation also correlates two residuals containing the
same CF targets; it is not an independent validation of LLM level information.

Using the saved manifest, BT scores, and current saved survival shape:

| Offset calculation | LOCO RMSE |
|---|---:|
| Survival baseline | 245.4277 |
| Existing implementation, including held-out CF labels | 242.8481 |
| Deployable diagnostic using BT prediction minus survival prediction | 246.7782 |

For the diagnostic, each fold fits survival and BT affine maps on training
contests. Its feature is the per-contest mean of `BT_CF - survival_CF`.
Regress training contests' mean survival residuals on that feature through the
origin, then apply the learned coefficient to the held-out feature. Held-out
CF labels enter scoring only. This is one simple control, not a tuned replacement
or proof that every LLM integration will fail.

Recommendation: retract the 2.6-point improvement as evidence of generalization.
Separate feature construction from target/scoring arguments, and add a test
that changing held-out CF labels cannot change predictions. Reanalyse existing
responses before spending on a wider deployment.

The BT solver itself is not the explanation on this dataset: its result agrees
with an independently assembled full-Hessian Newton fit with backtracking to
maximum score difference 0.0011, correlation effectively 1, and equal objective
(-820.3693867). Increasing its sweeps from 400 to 2,000 changes nothing.

## 2. High priority: statistical helpers and guard enforcement need repair

Evidence: `arch_b/metric.py:73`, `arch_b/predict_eval.py:35`, and the repeated
double-`argsort` implementations in validation/calibration modules.

Double `argsort` arbitrarily orders ties instead of assigning their mean rank.
CF ratings, four-category LLM labels, solve counts, and clipped prediction
probabilities contain ties. These are not edge cases for this project.

Reproductions:

- `_spearman([0,0,1,1], [0,1,2,3])` returns 1.0; average-rank Spearman is
  0.894427.
- `_metrics([0,1], [.5,.5])` returns AUC 1.0; reversing the labels returns 0.0.
  Both must be 0.5. Log-loss and Brier are unaffected.
- `NaN < floor` and `NaN > ceiling` are false. `metric.main` therefore does
  not fail NaN-valued guards/raw RMSE, and does not explicitly check that the
  primary metric is finite. Some missing-data paths raise independently, but
  the numeric guard contract itself is incomplete.
- The raw ceiling remains 293.4 despite the current 246.9 baseline: it allows
  about 46.5 points of deterioration, not the advertised 5.

Recommendation: reuse the existing average-rank implementation in
`arch_b.aoj._rank`, add permutation/tie tests, require finite metrics and fixed
coverage, and establish a versioned new baseline before adjusting guard limits.
Audit Kattis joins too: the current global normalized-title dictionary can
overwrite collisions; the AOJ matcher already demonstrates a more conservative
contest-corroborated pattern. Do not compare corrected metrics directly to old
thresholds without measuring the change. Average ranks are the standard tie
treatment documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rankdata.html).

## 3. High priority: the holdout does not answer several questions asked of it

Evidence: `arch_b/predict_eval.py:58` loads only `TAGGED`, constructs survival
exposures from the entire dataset, then splits cells. It bypasses
`estimate_joint`, its supplemental/UCup inputs, its prior hook, and the shipped
duration filter. Consequently the recommended corroborating command cannot
detect improvements confined to those components.

There are three additional limitations:

- Retention already conditions on at least one solve across the full row.
  On the fixed split, 1,152 retained rows have no training solves: their
  inclusion reveals something about held-out outcomes.
- `T_c` is computed from all solve times before splitting. Training exposures
  can therefore depend on a held-out event time. Actual contest duration
  would be legitimate metadata; a duration inferred from test events is different.
- 284 of the 119,693 held-out cells have the same resolved team/problem key
  in training through another standing row. This is a small fraction, so it
  does not explain the whole AUC, but it defeats a clean unseen-response claim.

A random-cell check remains useful for imputing missing outcomes for known
teams/problems. It is not a future-performance evaluation. CF LOCO likewise
holds out calibration labels, not contest standings: that is appropriate for
rating a contest whose final standings are available, but not forecasting it.

Recommendation: define separate frozen evaluations for (a) rating difficulty
from observed standings, (b) predicting a team's complete contest appearance
using other appearances, and (c) forecasting later seasons from earlier data.
Make the joint-fit configuration injectable into the holdout. Split repeated
team/problem groups together, make preprocessing respect the intended split,
and evaluate new-region transfer separately. Exact dates are missing for many
contests; report that limitation instead of calling year-only splits exact.

## 4. High priority: exported uncertainty is incomplete and sometimes miscentered

Evidence: `arch_b/survival.py:laplace_se`, `arch_b/hier_calibrate.py:level_sd`,
and `arch_b/calibrate.py:main`.

The exported quadrature term is useful, but it is not a validated total
uncertainty. It omits ability–difficulty covariance, affine/shape estimation
uncertainty, uncertainty in variance components, and problem-level discrepancy
between the fitted scale and CF ratings. The hierarchical model itself estimates
within-contest residual SD around 228 CF points, which is not in that sum.

For anchored contests, `level_sd` uses the posterior SD of their offset while
the shipped point estimate deliberately omits the posterior mean offset.
Uncertainty around an uncorrected point cannot generally be summarized by the
posterior SD around a different mean; the remaining offset matters too.

A local LOCO diagnostic refitted affine and hierarchical variance components
on each training fold and used the training-derived unseen-contest level SD
plus mapped conditional fit SE for held-out problems. Across 185 anchors,
36.2% of CF ratings fell within one SD and 62.2% within 1.96 SD; median SD was
90.3 CF. The gym shape remained fixed as in the main metric. This evaluates
coverage of **CF ratings**, not coverage of an unobservable latent true
difficulty. It shows why the current SE must not be advertised as a calibrated
CF prediction interval.

Recommendation: explicitly distinguish conditional latent fit SE from CF
prediction uncertainty. Check intervals by held-out contest and difficulty
band. Account for joint curvature using the sparse block Hessian, and evaluate
calibration uncertainty by refitting the map within contest resamples. Include
remaining predictive discrepancy rather than simply adding another arbitrary
constant.

The claim that `tau_region=12` demonstrates that the gym/LLM regional gaps are
referee artifacts also goes too far. Only three CF-anchored regions estimate
that variance, and Asia East—the region in dispute—is absent. Small-group
variance estimates need uncertainty and sensitivity analysis; see
[Gelman (2006)](https://sites.stat.columbia.edu/gelman/bayescomputation/Gelman2006.pdf).
The evidence supports “no large detected offset among these anchors,” not
“unanchored regions are calibrated.”

## 5. Medium priority: entity identity and contest participation are conflated

Evidence: `arch_a/load.py:member_identity` merges all rosters sharing two
normalized member names transitively. `arch_b/export_virtual_calc.py:86`
then assumes `(contest_id, resolved_team)` identifies a unique performance row.

Current joint data contain 281 repeated contest/identity groups, 295 excess
rows, and up to three rows per group. There are 2,354 identity components with
multiple distinct normalized rosters, with up to 15 rosters in one component.
These counts do not prove that every merge is wrong: substitutions and
repeat attempts are plausible. They do prove that identity is not a unique
participation identifier.

The virtual calculator's performance dictionary overwrites earlier rows in
such groups. Different ranks sharing an identity can receive the last row's
performance. Merely asserting that a lookup exists cannot detect this.

Recommendation: preserve a separate source participation key through the loader
and exporters. Audit same-contest collisions and long transitive roster chains
using provenance and contradictory affiliations/rosters before changing merge
rules. Group legitimate replay attempts in validation. Keep the useful shared
ability graph, but do not treat every identity union as verified equivalence.
WF affiliation/rank matching remains a heuristic: choosing the best percentile
across all source contests is not proof of the actual finalist roster.

## 6. Medium priority: the CF prior experiment does not test absolute anchoring

Evidence: `arch_b/cf_prior.py:172` sets
`mu = MU0 + scale * (cf_team - mean_cf_of_matched_teams)`.

Centering the elite matched cohort at MU0 removes its absolute CF level and
assigns its mean the same prior mean as the full population. Thus the null
metric result is evidence about this relative, sparse, cohort-centered prior;
it does not establish that absolute ability information is useless. The
year-specific ratings are also averaged into one season-agnostic ability, so
the January cutoff is causal per observation but the final averaged team prior
is not a chronological forecast for every earlier appearance.

There is a provenance gap as well: the collector groups corroborated members
in `row['members']`, but the completeness loop looks up every member in the
global `history` dictionary instead. A rating can be present globally without
that person's appearance being corroborated for this row. Check row-specific
evidence explicitly before declaring a roster fully trusted.

Recommendation: first evaluate ability on held-out verified teams, collect
actual dates, and estimate the ability-to-CF mapping independently of the
problem-difficulty mapping. A shared raw latent scale does not certify the
nonlinear difficulty calibration for team performance. The existing 2.86 vs
1.63 slope discrepancy already warns against that use. Only then test a joint
measurement model for CF ability with mapping uncertainty and season effects.

## 7. Research direction: challenge the model assumptions with the right tests

The old “plateau” verdict came from finite searches under an earlier mask and
two-phase fit. Later correctness changes moved the metric far more than those
sweeps. Some discarded collections and patches cannot be reconstructed here.
The search has not demonstrated an irreducible error floor.

Specific opportunities, after repairing evaluation:

1. **Selection and duration.** Model actual participation and retain genuine
   zero-solve performances where identifiable. Current zero-solve removal is
   outcome-dependent truncation; simply adding all zero rows is a different
   experiment from handling the selection mechanism. Replace latest-solve
   duration with recorded duration where available. Selecting contests by
   latest solve also selects on field strength/problem outcomes.
2. **Team performance over time.** Try a shrunk team-season ability and/or
   team-contest performance effect, assessed on whole-appearance holdouts.
   Hard identity splitting and a smoothed time model are different hypotheses.
3. **Solve-time likelihood.** A final acceptance timestamp includes problem
   choice, waiting, and implementation; it is not pure time spent solving.
   Inspect residuals by time, solve order, field strength, and official/replay
   status before choosing a hazard extension. Survival currently loses binary
   log-loss/Brier, so solve-probability calibration is a measured weakness.
4. **Hard-tail information.** Zero/one solves provide weak but nonzero
   information through field strength and exposure. Report prior sensitivity
   and one-sided bounds before choosing heavier tails. New independently
   linked solver evidence or clean content comparisons may distinguish the
   tail; repeated prior sweeps cannot create missing evidence.

One theoretical correction matters when interpreting experiments: in a complete
unweighted Rasch contest, the problem score equation depends on its total solves
and common field abilities. Two problems with equal totals and identical priors
have equal fitted difficulties regardless of *which* teams solved them. The
historical prose crediting binary Rasch with that distinction is incorrect;
survival can distinguish them through exposure times.

Numerical verification should precede dismissing richer models. Concavity does
not guarantee that an undamped full Newton step increases the objective, despite
`model.py`'s claim. Add gradient/objective and convergence checks against small
reference problems; the main metric currently ignores returned convergence
history. This is a missing safeguard, not a reproduced failure of the current
joint fit. The independent BT solver check above passed.

## 8. Experiment selection and LLM claims need stronger controls

Repeatedly choosing models on the same 15 CF contests makes LOCO a development
score. A five-point threshold and additional repeatedly inspected guards do not
turn it back into a fresh test. This is the model-selection bias discussed by
[Cawley and Talbot (2010)](https://www.jmlr.org/beta/papers/v11/cawley10a.html).

The original gym-shape win also needs current qualification. On the saved
joint-fit ratings, shaped versus affine LOCO is 245.4277 versus 246.9061.
A paired contest bootstrap of those fixed LOCO errors (10,000 draws, seed
20260905) gives a shaped-minus-affine 95% interval of [-9.63, +6.16] CF, with
36.38% of resamples worse. This bootstrap does not rerun historical model
selection. It does show that the old 22-point, approximately 1%-worse result
does not describe the current shape's incremental value. An affine-only control
is now worth including; this review does not switch calibration.

For the pairwise tuning experiments, the metadata-contamination audit and
decision not to claim clean generalization were appropriate. Remaining gaps:

- The 1,000 final requests are two orientations of 500 pairs drawn from only
  96 problems in 15 contests. Pair-level intervals still ignore dependence
  through shared problems/contests. Use problem/contest-aware uncertainty and
  a new untouched corpus for the next confirmatory comparison.
- Better order consistency is not equivalent to better accuracy; consistency
  filtering also selects a different subset. Report retained coverage and
  close-gap accuracy separately.
- Pairwise wording removes an absolute response scale, but cannot eliminate
  bias from statement style, domain familiarity, or memorized content. Test
  those assumptions through blinded paraphrases and region-balanced controls.
- A random cross-contest graph spends many comparisons on obvious large gaps.
  After establishing an honest validation, a prespecified uncertain-pair
  schedule can be compared with uniform sampling at equal cost. Conditioning
  on a pre-existing standings estimate is not itself target leakage if the
  estimate is available at deployment and held-out labels never select pairs.

Medal-site ranking needs its own decision standard too: the documented 47.9%
within-season ordering does not support confident “easiest site” advice. Compare
against the pooled-mean baseline, propagate historical-bar uncertainty, and
test rank stability/regret before adding city features. The current rough
shortlist framing is more defensible than fine numerical rankings.

## Recommended order and completion checks

| Order | Work | Evidence required before proceeding |
|---|---|---|
| 1 | Repair LLM leakage, ties, finite guards, participation keys | Held-out-label mutation invariance; tie/permutation cases; collision fixture |
| 2 | Version the evaluation suite and freeze new confirmatory data | Identical joint configuration; disjoint appearance groups; recorded split/data hashes |
| 3 | Rebaseline affine/shape, binary/survival, uncertainty | Paired contest errors; calibrated coverage; missing-data/region coverage reported |
| 4 | Audit identities, dates, participation, ability calibration | Provenance-backed corrections and held-out-team checks |
| 5 | Test one structural model change at a time | Improvement on the relevant frozen task, with cluster uncertainty and no guard regression |
| 6 | Consider new paid LLM comparisons | Existing responses demonstrate a deployable signal under corrected evaluation |

Store the commit, complete configuration, source hashes, split IDs, per-contest
errors, convergence status, costs, and keep/discard reason together for each
future experiment. Retain rejected data snapshots when reproducibility matters.

## Reproduction and limits

All diagnostics were local and read-only. No trained endpoint or external API
inference was used. This checkout lacks `data/gym_checkpoints/api_standings.json`,
so the gym-merge experiment cannot be reproduced from its raw observations.
Discarded campaign inputs identified as missing in `details.md` were not
recollected. Historical OI code appears in Git history but is absent from the
current tree; the detailed model review here concerns the current ICPC/LLM code.
No new claim is made about those absent implementations or data.

The LLM/interval diagnostics use saved rounded survival records, while the main
metric refits from source; their printed baselines agree to the reported decimal.
The interval check refits variance components per fold, uses the fixed gym shape,
and recomputes the affine map's local derivative at each held-out difficulty.
The deployable LLM control fits all its coefficients within each training fold;
further model selection would require nested validation or fresh data.

Key SHA-256 fingerprints for the locally reproduced LLM result:

```text
5913860ba769db43531005ac6ed1f6f07e27d57b9c904b4568fbab0c2b819374  llm_crosscontest_run/manifest.json
9243b90b1c0f79e0e8ad3fe7375e524dcb33a9ec2f15d81a97986d5058bafd50  llm_crosscontest_run/analysis.json
a928c5670e4fbadb4d59381f2706c8e651cc658eefc6c3b4f7f0d9d3fda371fc  llm_crosscontest_run/predictions.json
f899c89ae99669d91ab31f2b5dc38d1e3a42a030bf5bf20fb14887f09a2d7f49  llm_survival_run/predictions_full.json
8af4583b8163f58e6103b9440a47ef81f33cc5a8cece5391f0ed8db93cbc989f  output/problem_ratings_survival.json
1e3f7c1da8c2f2939d34c4a81f080b064bb96c853f3082c79e615e7b369e4df8  data/cf_problemset.json
```
