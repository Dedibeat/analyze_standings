# Four candidates to succeed DE

2026-11-05. These are research candidates, not shipped replacements. The desired
target is difficulty under comparable task versions, rules and duration. Field
invariance is not a requirement across genuinely different task conditions.

1. **Binary difficulty with a small monotone CF map.** Completion-based Rasch
   difficulty is the most stable input in our independent field experiment.
   Compare affine and a tightly constrained increasing curve. A weaker ability
   prior (SD 800) gave an exploratory ~232 affine LOCO versus ~247 at SD 400;
   freeze and validate that lead before treating it as a gain. Default DE is
   ~226 on the reused development anchors.
2. **DE trained with a stability penalty.** Fit CF labels while penalizing
   changes in final predictions when the same task is measured on different
   participant samples. Keep every view of a task together in nested validation.
   Compare against ordinary DE and resampling without the penalty. This is the
   selected next experiment; see [de_stability_plan.md](de_stability_plan.md).
3. **Binary difficulty plus a separate timing correction.** Test a small timing
   residual after accounting for strength and solve order, using verified logs
   and durations. Raw binary/survival disagreement is not a pure measure of
   implementation burden. This needs the separate timing-data pilot first.
4. **A conservative DE hybrid.** Blend a stable baseline with DE, reducing the
   correction outside joint anchor support. The blend weight itself can cause
   field dependence and must be evaluated under the same perturbations. Existing
   blend/reference-population controls score ~241/~243 and do not establish a
   replacement for DE yet.

Prefer a candidate that retains useful CF accuracy and materially improves
field transport. The 185 problems in 15 contests are development evidence already
used for many choices; a fresh confirmation field is still required.
