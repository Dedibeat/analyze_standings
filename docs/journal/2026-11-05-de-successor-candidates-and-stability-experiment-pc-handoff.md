# DE successor candidates and stability experiment PC handoff (2026-11-05)

**Request.** Record the four suggested DE successors, prepare candidate #2
(stability-penalized DE), and push so work can continue on the user's home
i9-14700 / RTX 4070 PC. `de_successors.md` records all four: binary monotone
calibration, stability-penalized DE, binary plus isolated timing, and a
conservative DE hybrid. The frozen protocol and PC commands are in
`de_stability_plan.md`; this numbering is separate from the rating-rethink
experiment numbers.

**Prepared, not evaluated.** `arch_b/de_stability_data.py` prepares resumable
whole-model field refits. Seven training views (full, four random halves, two
quarters) are separated from nine reserved stress views (new random sizes,
ID-based event/mirror compositions, independently selected strength halves).
Samples move whole resolved identities together. Strength selection uses
non-anchor contest subset A; its pool/strong/weak measurements exclude A and
use subset B plus the selected anchor rows. These three stress views use their
own pool as the drift reference. Missing board coverage is explicit.

`arch_b/de_stability.py` fits an augmented ridge residual over the existing
survival affine baseline, with a penalty on changes in the **entire final
prediction** across training views. Each task has total supervised weight one;
resampled views do not become independent labels. Frozen alpha {0.1,1,10} and
beta {0,0.1,1,10} are selected by inner contest error across training views.
Outer CF-contest/canonical-task purging applies to supervised and stability
fitting. Means/scales/clipping come from full training anchors only. Reserved
stress views cannot influence selection. Controls are unchanged clipped DE,
augmented ridge with beta=0, and binary affine. Selection of beta=0 is an
explicit possible result, not a stability-penalty success.

The runner saves every fold's selections and predictions, per-view coverage,
problem/contest-balanced CF errors, tail/region errors, paired contest-bootstrap
differences, matched-task drift, order reversals and predicted/target spread.
These remain reused development data; no production promotion is implemented.

**Portable inputs.** `data/de_stability_anchors.json` freezes all 185 anchor
rows; `data/de_stability_inputs.json` pins 68 source/input hashes. Every required
input is tracked. No external board caches, account credentials or downloaded
GPU weights are needed. `requirements-de-stability.txt` pins the tested NumPy
2.5.1 (availability checked through pip). Source/plan changes reject old caches.
Prepared views are atomic and checksummed under gitignored `de_stability_run/`.
The CLI exposes `check`, `prepare --jobs N [--view NAME]`, and `evaluate`;
evaluation refuses incomplete caches. Use one BLAS thread per worker and start
with two workers because the PC's RAM capacity was not supplied. The GPU is
unused; independent refits use CPU processes.

**Verified here.** All **212 tests pass**, including seven new tests for final-
prediction stability, task weighting, held labels/reserved-view isolation,
canonical-task purging, identity sampling, cache validation and matched metrics.
One real full-field preparation refit both models: 53 binary / 154 survival
iterations, all 185 problems, no missing coverage, maximum feature difference
from the released anchors **0.0**. Replaying unchanged clipped-DE LOCO from
that cache gives **225.607314** RMSE. A two-worker preparation invocation reused
the completed full view successfully. The other 15 views and the stability
candidate's nested evaluation are intentionally left for the PC.

**Run on PC.** Pull the branch; create/use a venv, install
`requirements-de-stability.txt`, then run the plan's `check`, `prepare --jobs 2`
and `evaluate` commands. No ignored cache transfer is required: the PC rebuilds
the expensive features once and reuses them for calibration runs. Source and
production rating artifacts are unchanged outside the new research files.
