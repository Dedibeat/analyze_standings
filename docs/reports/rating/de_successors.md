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
   Compare against ordinary DE and resampling without the penalty. Plan:
   [de_stability_plan.md](de_stability_plan.md). **Run 2026-11-05: no gain.**
   Beta = 0 was picked in 8 of 15 folds, CF RMSE was no better than unpenalized
   ridge, and drift fell by at most 2.2%. Unpenalized resampling lost 12 RMSE to DE on
   full fields (237.8 vs 225.6). Results: `output/de_stability_evaluation.json`.
3. **Binary difficulty plus a separate timing correction.** Test a small timing
   residual after accounting for strength and solve order, using verified logs
   and durations. Raw binary/survival disagreement is not a pure measure of
   implementation burden. This needs the separate timing-data pilot first.
4. **A conservative DE hybrid.** Blend a stable baseline with DE, reducing the
   correction outside joint anchor support. The blend weight itself can cause
   field dependence and must be evaluated under the same perturbations. Existing
   blend/reference-population controls score ~241/~243 and do not establish a
   replacement for DE yet.

5. **Hierarchical binary (added 2026-11-05, run).** Binary Rasch with a
   board-level ability mean and a set-level difficulty mean, one affine CF map
   for problems and teams. It removes the strong-board shrinkage bias that
   DE's solve-rate term corrects after the fact. Full-field CF 229.5 vs DE
   225.6 (+3.9 [−8.1, +14.5]). Strong − weak mean error 1 point apart (DE:
   224). It beats both shipped engines at predicting held-out team
   appearances. The current rival; see
   [hier_binary_report.md](hier_binary_report.md).

6. **Hierarchical binary with solve-time slices (added 2026-11-16, run).**
   Candidate #3's timing idea inside candidate #5's fit: a solved cell also
   says in which fifth of the window it was solved, at weight 0.25 next to the
   binary likelihood, plus `skip_partial`. With the mislabeled anchor Uniform
   Chemistry left out (184 anchors): full-field CF 205.9 vs DE 207.0
   (−1.1 [−11.7, +9.0]) and #5's 211.5. Better than #5 on every cut field. It
   passes all four pre-registered criteria. The release candidate; see
   [hier_time_report.md](hier_time_report.md).

Prefer a candidate that retains useful CF accuracy and materially improves
field transport. The 185 problems in 15 contests are development evidence already
used for many choices; a fresh confirmation field is still required.
