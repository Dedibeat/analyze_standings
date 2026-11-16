# Solve time in the hierarchical fit, and a release candidate

2026-11-16. Follow-up to `hier_binary_report.md` and `skip_cells_report.md`.
Code: `arch_b/hier_time.py`; tests: `tests/test_hier_time.py`. Research only:
shipped DE stays the shipped rating.

## Protocol (written and committed before the formal run)

### Model

The binary fit knows only whether a cell was solved. Here a solved cell also
says in which of K equal slices of the contest window it was solved
(u = solve time / T_c; T_c is the board's latest solve, as in `survival`):

```text
P(solved by the end of slice k) = logistic(g − d_k),   g = (θ_t − b_p) / s
d_1 > … > d_K = 0
log-likelihood = (1 − w) · binary + w · slices
```

- The last slice is the binary model, so θ and b keep its scale.
- The thresholds d are global, estimated by maximum likelihood.
- Priors and their settings are the frozen `hier_binary` ones (σ 300, τ 800,
  σ_b 600, τ_b 400). Nothing there is reselected.
- A setting is (K, w, skip). `skip` also applies `skip_partial`. K = 0 is the
  frozen `hier_binary` fit, called `base`.

### What was seen before this protocol

An exploration on the full data and on split 1, with the CF anchors and both
hand panels in view:

- **Pooled data fit the slice form.** At a fixed gap g, the logit of "solved
  by u" sits a constant below the logit of "solved by the end": about −4.4 at
  u = 0.2, −2.1 at 0.5 and −1.1 at 0.7, for g between −1 and 4.
- **Full weight (w = 1) fixes the floor and costs accuracy.**

  | K (w = 1) | EC sign-in bias | all-72 hand RMSE | fresh panel RMSE | anchors, in-sample | split-1 log loss | pair accuracy |
  |---|---|---|---|---|---|---|
  | base | +398 | 302 | 399 | 225.5 | 0.2363 | 80.98% |
  | 2 | +244 | 242 | 332 | 218.7 | 0.2409 | 81.08% |
  | 3 | +163 | 224 | 324 | 223.1 | 0.2436 | 81.13% |
  | 5 | +99 | 222 | 338 | 232.7 | 0.2456 | 81.21% |
  | 10 | +4 | 222 | 346 | 245.4 | — | — |

  Difficulties stretch within a board (SD 723 → 784 at K = 10): teams solve
  easy problems first, and the slices read that as extra ease.
- **A problem-order term did not repair it.** A threshold shift proportional
  to the problem's distance from its set mean came out small (0.02–0.05 per
  logit) and left split-1 log loss at 0.2422 (K = 3).
- **A small weight keeps most of the floor gain at almost no cost.** K = 5,
  w = 0.1: sign-in bias +243, hand RMSE 240, fresh panel 357, nested LOCO
  221.6 (base 229.1), split-1 log loss 0.2366, pair accuracy 81.18%.
  K = 10, w = 0.25: sign-in bias +38, LOCO 234.1, log loss 0.2389.

So the dose (K, w) is chosen below without CF labels or hand ratings, and
split 1, the anchors and both panels are development data for this candidate.
Split 0, split 2, the stability views and the 2026 boards were not looked at.

### Dose selection (no CF label, no hand rating, no reserved view)

The grid is frozen: K ∈ {3, 5, 10} × w ∈ {0.05, 0.1, 0.25, 0.5, 1}, without
`skip`. The two stages are `hier_binary`'s:

1. **Predictive.** Keep the settings whose held-out cell log loss on split 0
   (final results only) is within 1% of the best of the grid and `base`.
2. **Measurement stability.** Among those, take the setting whose latent
   difficulties on the 15 anchor boards move least over the six training
   views (RMS change over the full-view SD).

The winner is `time`. If no setting survives stage 1, the time term is
rejected.

### Evaluation, run once

Four settings: `base`, `skip` (`base` + `skip_partial`), `time`, `time_skip`.

A setting **passes** if all four hold against `base`:

1. **Hand panels.** On the old panel, EC sign-in |bias| ≤ 150 and no other
   group's RMSE worse by more than 50. On the fresh blind panel, a lower RMSE.
2. **CF accuracy.** Full fields, nested LOCO affine map: the RMSE difference
   interval (paired contest bootstrap) is not entirely above 0.
3. **Team prediction.** On splits 1 and 2, held-out log loss no more than 1%
   above `base` (`skip` settings: on the cells no rule touches). A setting
   with a time term must also not lose linked rank-pair accuracy on either
   split.
4. **Stability.** Drift no larger than `base` on at least 5 of the 8 reserved
   views that have a drift.

**Release candidate:** among the passing settings, the lowest RMSE over both
hand panels pooled (104 problems). Settings within 10 of it tie, and a tie
goes to the one with fewer components (`skip`, then `time`, then `time_skip`).
If none passes, `base` stays.

Also reported, without a pass rule:

- **DE.** Nested-LOCO DE on the current shipped fit, paired on full fields.
  DE is not refit on the stability views: the 2026-11-05 view results used
  other team samples.
- **Fresh boards.** The five 2026 EC regionals were added on 2026-11-15, after
  the `hier_binary` setting was frozen. Fit without the 17 contests added
  that day, then score rank-pair accuracy among each regional's linked teams
  for flat binary, survival and the four settings.
- **CF-rated teams** (54) on each setting's own map.

No fresh CF-rated board exists: on 2026-11-16 the newest ICPC mirror on
Codeforces is contest 2206, already an anchor.
