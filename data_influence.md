# Supplemental-contest influence audit

This audit revisits `autoresearch/loop-260723-1333/` after the full-cell mask
correction.  (There is no `deep_research/` directory in this checkout.)  Run:

```bash
./.venv/bin/python -m arch_b.data_influence
```

The command writes the detailed, machine-readable result to
`output/data_influence.json`.  Contest subsets are selected from identity-graph
connectivity, not from Codeforces outcomes, except for the explicitly labelled
post-selection mutation.

## Result

| Fit | calibrated LOCO | equal-contest LOCO | raw LOCO | delta vs tagged-only |
|---|---:|---:|---:|---:|
| tagged only | 245.253 | 249.592 | 247.372 | — |
| no cross-contest team links | 333.469 | 339.734 | 330.307 | +88.216 |
| identity links only, no supplemental solves | 245.184 | 249.490 | 247.355 | -0.069 |
| older ICPC only | 245.887 | 250.250 | 247.155 | +0.634 |
| Petroz only | 244.285 | 248.674 | 245.464 | -0.968 |
| all supplemental | **244.188** | **248.560** | **245.192** | **-1.065** |
| Petroz top link-count quartile | 244.952 | 249.254 | 246.535 | -0.301 |
| all supplemental, linked rows only | 244.426 | 248.828 | 245.469 | -0.827 |

All existing guards pass in every row except the deliberately broken no-link
control, whose raw LOCO exceeds the 293.4 ceiling. The equal-contest custom
metric gives the same direction as pooled LOCO, so the small supplemental gain
is not only a consequence of one anchor contest having more rated problems.

The no-link control gives every standing row its own ability and disables UCup
prior transfer, while preserving every within-contest response cell. Its
calibrated LOCO is **333.469**, 89.281 CF worse than the linked shipped fit.
Within-contest solve-count sanity remains +0.995, demonstrating the distinction:
the model can still rank problems inside a contest, but it cannot place different
contests reliably on one difficulty scale. Cross-contest linking itself is
therefore essential; only the *marginal value of additional links* is small and
non-monotonic.

The current effect is much smaller than the historical 266.4 → 261.6 campaign
result.  Against the corrected tagged-only baseline, all 71 supplemental
contests improve calibrated LOCO by only **1.065 CF**, below the project's
predeclared 5-point keep threshold.

## How the extra contests act

Supplemental problems are not part of the 185 CF anchors.  They can change an
anchor difficulty only by changing a team ability shared with `tagged.json`.
The decomposition supports that mechanism:

- Identity unions alone explain only 0.069 CF of the 1.065-CF change.  The gain
  is performance evidence, not a hidden identity repair.
- Petroz contributes 4,736 retained rows from linked teams and 2,976 UCup-team
  appearances.  Older ICPC contributes 1,100 linked rows and 201 UCup-team
  appearances.  Petroz therefore supplies much denser constraints on abilities
  already used by the shipped fit.
- Keeping only already-linked supplemental rows retains 0.827 CF of the gain.
  Unlinked opponents still add about 0.238 CF: they help calibrate each new
  contest's problem scale, which makes the linked teams' performances
  interpretable.  They are context, not a direct bridge.
- Keeping only the top quartile of Petroz contests by linked-row count retains
  just 0.301 CF.  Link count is necessary but not a sufficient quality score;
  the useful constraint is distributed across the schedule.

The regional decomposition provides the clearest rational explanation.  Petroz
contests have 3,411 direct team-overlaps with Northern Eurasia CF-anchor
contests, versus 307 with Europe and 296 with Asia Pacific.  Correspondingly,
Northern Eurasia calibrated LOCO improves **220.13 → 214.28**, while Asia
Pacific slightly regresses **208.99 → 209.73** and Europe is flat
**332.48 → 332.54**.  The pooled improvement is therefore a geographically
plausible transfer from a Northern-Eurasia-heavy camp, not a global improvement.
Seven of 15 held-out CF contests improve and eight regress.

## Contest mutation and anti-overfitting check

The five supplemental contests with the most linked rows were removed one at a
time from the full fit.  Every deletion improved LOCO, but only by 0.037–0.263
CF.  Removing all five after observing those results gives 243.646, an apparent
0.542-CF improvement over the full fit.  This is a post-selected result on the
same 15 CF contests and is not a valid keep by itself.

An independent, fixed 20% holdout of 117,634 original `tagged.json` cells rejects
that interpretation:

| Fit | log-loss | Brier | AUC |
|---|---:|---:|---:|
| tagged only | **0.229876** | **0.069451** | **0.967638** |
| all supplemental | 0.230252 | 0.069548 | 0.967626 |
| post-selected five-contest removal | 0.230105 | 0.069547 | 0.967593 |

Thus neither the full supplemental set nor the mutation improves current
held-out solve prediction.  The five-contest removal is retained only in the
audit artifact as an example of metric-selection overfit; the shipped contest
set is unchanged.  The defensible conclusion is narrow: Petroz slightly adjusts
Northern Eurasian shared-team abilities in a direction favored by the CF anchor
pool, but there is no evidence for a new data-selection rule.
