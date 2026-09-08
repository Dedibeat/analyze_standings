# Frozen calibration feature-group ablation

This is a frozen, research-only development result on the reused 185 CF/QOJ
anchors in 15 completed contests. It does not change a production rating or
calibration artifact, and it is not fresh confirmation.

Every residual ridge fit retains raw survival difficulty (`raw_b`). The added
groups are D = binary-minus-survival disagreement; E = conditional fit SE,
solve rate, and log field size; and T = log median solve time plus a missing-time
flag. Alpha and residual shrinkage were selected only in inner contest folds.
The underlying survival fit and its timing data were fixed throughout: omitting
T below does **not** mean removing timing from that fit.

## Results

RMSE in CF points; lower is better. LOCO holds out one completed CF contest;
LORO holds out all labels from one observed anchor region before fitting or
selection.

| residual method | LOCO | LORO |
| --- | ---: | ---: |
| raw affine | 246.9061 | 248.6523 |
| locked gym shape | 245.4277 | 246.0305 |
| D | 241.7094 | 243.4531 |
| E | 238.2049 | 237.5236 |
| T | 247.3457 | 248.6584 |
| DE | **226.5661** | **225.7640** |
| DT | 245.2137 | 243.2424 |
| ET | 241.1893 | 242.2078 |
| DET | 229.6269 | 228.3597 |
| adaptive inner-only selection | **226.5661** | 226.9881 |

The adaptive selector chose DE in all 15 LOCO outer folds. In LORO it chose DET
for Asia Pacific and DE for Europe and Northern Eurasia. The retained DET
control exactly reproduces the prior OOF result and selections.

DE is the strongest calibration candidate in this development comparison: joint
disagreement plus non-time evidence helps more than either group alone, while
the extra calibration timing features do not help. These predictors are
correlated, so this does not establish a causal mechanism or an individual
feature attribution.

## Transfer-facing diagnostics

Full-anchor refits are explicitly non-OOF, non-deployment diagnostics against
pre-existing cached proxies; they were not used to choose a method. They are
mixed: DE versus raw is 0.9780 versus 0.9691 on pooled gym Spearman (n=667),
0.7760 versus 0.7955 on Kattis (n=427), and 0.5642 versus 0.5685 on AOJ
within-contest Spearman (n=45). After purging only canonical anchor tasks, the
gym/Kattis counts are 659/416; the stricter whole-anchor-contest plus task purge
is 655/412 and reproduces the historical reported counts. These are different
subset definitions, not interchangeable estimates.

One shared Luxor task illustrates why an absolute gap alone is not a verdict:
task 8674 changes from a raw gap of 5.1 to DE 101.0 CF points (DET: 75.3), but
the other shared-task pairs and tail diagnostics vary. No artificial prediction
clipping was applied. These proxy results neither establish regional transfer nor
justify forcing equal shared-task ratings.

## Scope, provenance, and reproduction

Both protocols use completed-contest context and fixed underlying raw fits. LOCO
is an out-of-fold context-calibration diagnostic; LORO is a calibration-label
transfer stress check. Neither is a forecast for a new future contest, nor does
either validate a global rating replacement. No TabFM import, download, or run
occurred.

The machine-readable results include fold membership, OOF predictions, selected
settings, transfer diagnostics, and SHA-256 provenance for inputs, plan, and
source modules: [ablation output](output/calibration_ablation.json) and
[transfer output](output/calibration_ablation_transfer.json). The frozen
protocol is [calibration_ablation_plan.md](calibration_ablation_plan.md).
The final transfer artifact has 18 verified provenance hashes and no non-finite
numeric values; the full test suite passed 58 tests.

```bash
./.venv/bin/python -m arch_b.calibration_ablation
./.venv/bin/python -m arch_b.calibration_ablation_transfer
./.venv/bin/python -m unittest discover -s tests
```

Verdict: DE is the strongest calibration candidate on this reused development
set, but it is not validated as a global rating replacement. No further model
experiments should proceed until the project owner decides the next step.
