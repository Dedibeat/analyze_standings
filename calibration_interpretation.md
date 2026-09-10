# Understanding DE and TabFM, and the next experiments

The strongest supported interpretation is that **one scalar survival difficulty
loses information useful for mapping standings to CF ratings**. DE recovers some
of it by combining the binary estimate with a correction based on solve counts
and field size. Its gain is credible development evidence; it does not establish
the physical cause of the original errors or reliable transfer everywhere.

This follow-up reconstructs existing selected fits and analyzes saved predictions.
It does not train a new candidate, change hyperparameters, regenerate production
ratings or invoke TabFM. Numeric results and hashes are saved in
[`output/calibration_interpretation.json`](output/calibration_interpretation.json).

## How DE changes the prediction

The shipped gym calibration is a single monotone function of survival difficulty:
the same raw difficulty always gets the same CF prediction. DE instead starts
with the raw affine calibration and adds a ridge prediction of its CF residual.
Only training contests supply CF labels for fitting or selecting that correction.

For the full-anchor fit, the raw affine baseline is approximately
`1.651225 * survival_b - 1206.657`. The added correction is:

| Feature, centered on its anchor mean | Mean | CF points per feature unit |
| --- | ---: | ---: |
| Survival difficulty | 2184.231 | +0.160285 |
| Binary minus survival difficulty | 63.571 | +0.876768 |
| Conditional fit SE | 45.927 | -2.284458 |
| Solve rate (fraction, not percent) | .405606 | +620.681577 |
| `log1p(retained field size)` | 4.972415 | -67.708590 |

These coefficients reconstruct all 3,159 saved DE predictions within 1e-7 CF
points. They are an algebraic description of this fitted model, not causal
effects of independently changing the features. In the 15 outer fits the signs
of disagreement, SE, solve rate and field size are consistent; the small extra
raw-difficulty term changes sign in one or more folds.

Expanding `binary_minus_survival` makes the estimator combination clear:

`DE ≈ 0.934742 * survival_b + 0.876768 * binary_b + evidence terms + intercept`.

Thus the difficulty part is approximately a **52% survival / 48% binary blend,
followed by rescaling**, together with the evidence correction. This equivalence
holds for the selected full fit; it is not a new fitted model or a universal
optimal mixing weight. It also explains why neither “survival alone wins” nor
“discard solve times” follows from DE's result.

## Why these features can help

Binary uses completion outcomes; survival also uses elapsed solve time and a
different probability curve. Both estimate their own team abilities. Their
disagreement can therefore reflect timing, likelihood shape, and differences in
the inferred ability scales. It is **not a pure timing measurement**. Both curves
have 50% completion at theta=b, but they differ elsewhere.

There is a stronger, model-specific explanation for E. With unweighted survival
observations, default priors and an interior converged optimum, let k be the
number of solves, s the model scale and sigma_b the difficulty prior SD. The
first-order condition and conditional curvature give:

`sum(Lambda) = k + s * (b - MU0) / sigma_b²`

`SE(b) = [k/s² + (b - MU0)/(s*sigma_b²) + 1/sigma_b²]^(-1/2)`.

Here `Lambda` is the cumulative hazard contribution used by `survival.py`.
Reconstructing SE from saved solve counts and raw b matches the stored SE with
median absolute difference **0.0247**, maximum **0.0508**, and correlation
**0.9999997**. The small discrepancy is consistent with one-decimal stored
values and the finite convergence tolerance.

Consequently E's “uncertainty feature” is largely a **nonlinear solve-count
feature**: k is already field size times solve rate. This is not three independent
pieces of evidence, and the regression does not attach uncertainty to predictions
merely because SE is an input. The SE term can still help linear ridge represent
a nonlinear relationship; algebraic redundancy does not justify deleting it.

The measured ablation supports using these signals together: raw 246.91 RMSE,
D-only 241.71, E-only 238.20, DE 226.57. It supports a correction that depends on
more than scalar difficulty. Explaining the gain specifically as prior shrinkage,
team strength, omitted engagement, or timing bias still requires distinguishing
those mechanisms. The current result does not do that.

## Why the full catalog moves so much

On anchors, disagreement and solve rate correlate **-0.952**. Their large,
positive coefficients often offset each other after centering. On a population
with a different relationship between these features, that cancellation can
disappear even if each feature is individually inside its training range.

Aobayama's *12 Grid* illustrates this directly. Its solve rate is .86 and its
binary-minus-survival gap is +241.1; both are above their anchor means.

| Contribution to its correction from raw affine | CF points |
| --- | ---: |
| Raw difficulty | -21.4 |
| Binary–survival disagreement | +155.7 |
| Conditional SE | +44.6 |
| Solve rate | +282.0 |
| Field size | +70.5 |
| **Total correction** | **+531.4** |

Raw affine 2180.0 becomes DE 2711.4. The shipped gym value is 2151.5, giving
the previously reported +559.9 displayed change. **Field size alone does not
explain this jump.** The feature combination drives most of it. The table is
relative to anchor means and is not a causal attribution; an equivalent
reparameterization could redistribute contributions between correlated inputs.

Across the whole catalog, DE-minus-raw averages **+73.35**, of which the
disagreement term contributes +60.06 algebraically. Raw-minus-gym adds +2.38
before clipping/rounding. Thus the broad increase reflects a shift in input
distribution, especially estimator disagreement, rather than a fitted global
instruction to raise every rating. It could contain useful corrections and
systematic extrapolation error; the old anchors cannot distinguish them.

In the OOF anchors, **40.8%** of DE correction variance is between contest means
and **59.2%** is within contests. Few rank reversals do not make DE just a contest
offset: it changes gaps substantially while usually retaining their order.

## What the TabFM result does and does not say

DE 226.57 versus managed TabFM 231.29 is a small observed advantage. It is also
not a pure backend comparison: DE uses five features and TabFM uses all seven.
The matched seven-feature ridge DET scores **229.63**, just 1.66 points better
than TabFM. Adding explicit timing summaries to DE already worsened ridge's
score; timing remains inside the underlying survival estimate regardless.

The two methods' OOF corrections correlate **.722**. Managed TabFM's chosen
shrinkage is .75 in nine folds and .5 in six; its correction SD is **78.6**
versus **106.7** for DE. This suggests overlapping learned structure and smaller
TabFM corrections after selection, but does not identify the backend's internal
reason for its errors. There are only 185 labels across 15 contest groups; the
225 inference calls reuse those labels rather than creating independent evidence.

A descriptive paired bootstrap resampling those 15 contests, with predictions
fixed, gives the following 2.5–97.5 percentile ranges for RMSE differences:

| Difference; negative favors ridge | Observed difference | Bootstrap range |
| --- | ---: | ---: |
| DE minus shipped gym | -18.86 | [-34.45, -2.27] |
| DE minus TabFM | -4.72 | [-13.94, +6.48] |
| DET minus TabFM | -1.66 | [-9.76, +7.63] |

This resampling does not refit or account for repeated candidate selection on
the reused benchmark. It is a sensitivity description, not fresh confirmation
or a selection-adjusted significance claim. The defensible conclusion is that
TabFM did not demonstrate an advantage here, while **which residual learner is
better remains uncertain**. A higher-capacity backend being unnecessary for
this small problem is plausible, not proven.

## Proposed future plan

1. **Explain the disagreement on a fixed panel before changing the model.**
   Retain Aobayama H/L, both Luxor Sphinx appearances, the known CF 1949/2041
   losses, and ordinary anchor controls chosen before further inspection. Replay
   binary/survival abilities and likelihood contributions to separate the part
   associated with team-ability scale from completion/time behavior. Verify
   recorded timing and task/context equivalence where evidence exists; record
   missing facts explicitly. Success is an accounted-for gap with corroborated
   inputs, not a smaller score after hand editing examples. Do not force shared
   tasks to equal ratings without version/context evidence.
2. **Run one bounded mechanism comparison, then freeze.** Compare unchanged DE
   with exactly three prespecified variants, omitting one E feature at a time
   (SE, solve rate, field size), under the same task-purged nested protocol and
   existing alpha/lambda grid. Inspect which omissions alter OOF errors and the
   flagged full-catalog corrections. This tests the correction's dependence on
   those terms, not their causal effects. The algebraically equivalent SE/count
   rewrite needs no new experiment; its equivalence is already established.
   Separately inspect joint disagreement/solve-rate support; do not
   select a support cutoff or correction cap from improved benchmark scores.
   Keep DE as the control even if a simpler representation ties. If the question
   specifically becomes backend choice, a matched **five-feature** TabFM run is
   the relevant comparison; it is optional and lower priority than explaining
   transfer, and needs the runner reuse defect fixed first.
3. **Test transfer with new information.** Freeze predictions and a new
   confirmation cohort before inspecting its labels. Cover both field-size
   tails, unusual disagreement/solve-rate combinations, and regions without CF
   anchors, alongside ordinary supported cases. Obtain genuinely independent
   reference ratings or explicitly label weaker ordinal adjudications; Kattis
   ranks are not interchangeable with CF-point targets. Choose sample size and
   release margins from contest-level variability before evaluation. Report
   absolute calibration and ordering separately. Fresh labels, recorded durations
   and task/roster adjudications are presently missing; another split of the
   old anchors cannot supply them.
4. **Ship a coordinated calibration change only after the evidence supports
   its declared scope.** Start with an opt-in comparison artifact, one shared
   exporter path and explicit support/uncertainty labels. Keep team performance
   and medal semantics distinct from problem-specific correction. Evaluate the
   candidate's actual displayed outputs against the frozen confirmation and
   transfer checks, not only raw-fit guards. Promote only within the scope those
   checks support, with a complete rollback set. The implementation dependencies
   are already enumerated in [the update plan](shipped_fit_update_plan.md).

The immediate priority is steps 1–2: understand the disagreement and its joint
support while keeping the candidate fixed. More backend capacity, regional
offsets, or ad hoc clipping do not address the mechanism identified here.

Reproduce the diagnostic, including coefficient replay and the fixed-prediction
20,000-resample bootstrap (seed 20260910), with:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  ./.venv/bin/python -m arch_b.calibration_interpretation
```

It verifies the previous readiness audit's input hashes and writes only its new
research artifact. None of the proposed future experiments has been executed.
