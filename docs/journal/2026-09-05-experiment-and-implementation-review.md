# Experiment and implementation review (2026-09-05)

Reviewed the current ICPC/LLM implementation, saved artifacts and historical
campaigns at `8a351e0`; full findings, evidence, limitations, artifact hashes and
recommended experiment order are in [experiment_review.md](../reports/rating/experiment_review.md).
This was a documentation-only review: no model fixes, output regeneration or
paid inference were performed.

Reproduced `arch_b.metric`: **245.4 calibrated / 246.9 raw affine CF RMSE**,
all guards pass. The joint dataset has **260 contests, 37,576 identities, 3,159
problems, 73,023 rows and 923,842 observed cells**, including the four World
Finals. Earlier WF-identity-only descriptions and dataset counts are historical.
The unittest suite passes **32/32**. Tagged-only binary/survival log-loss
reproduces at **0.2009/0.2309**, Brier **0.0615/0.0699**, and reported AUC
**0.9733/0.9673**; AUC tie handling needs correction.

Principal corrections:

- The cross-contest LLM held-out offset reads `cf[te]`. Saved artifacts
  reproduce baseline **245.4277** and leaked **242.8481** RMSE. A simple
  deployable BT-minus-survival offset control yields **246.7782**. This is
  diagnostic, not a tuned replacement; the claimed gain cannot justify rollout.
- Rank/AUC ties and NaN guard enforcement need repair. The holdout also
  bypasses the joint configuration, uses outcome-dependent preprocessing,
  and has 284 test cells with the same team/problem key in training.
- Fit-plus-level SE is not validated total CF prediction uncertainty. A LOCO
  interval diagnostic covers **62.2%** of CF ratings within 1.96 SD; this is
  predictive coverage, not a test against latent true difficulty. Three
  anchored regions do not establish absence of bias in unanchored regions.
- There are **281 repeated contest/identity groups** (295 excess rows), so
  the virtual calculator's performance dictionary overwrites nonunique keys.
  Identity resolution needs a separate participation identifier and provenance
  audit. These counts alone do not establish which merges are wrong.
- The CF prior tests cohort-centered relative spacing, not absolute anchoring;
  its roster check also needs row-specific corroboration.
- The gym shape's historical 22-point gain is now **1.48 points** on saved
  joint-fit records. A paired contest bootstrap of fixed LOCO errors gives
  shaped-minus-affine 95% interval **[-9.63, +6.16]** (10,000 draws, seed
  20260905); it does not account for historical model selection.

Keep the sparse/full-cell loader and joint fit. Repair and version evaluation,
freeze task-specific holdouts, rebaseline calibration/uncertainty, then audit
identity/date/ability data before focused model experiments. The historical
finite-search “plateau” is not an established error floor. Missing raw gym
standings and discarded campaign snapshots were not reconstructed by guessing.
