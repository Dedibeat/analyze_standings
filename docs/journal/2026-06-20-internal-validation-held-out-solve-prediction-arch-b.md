# Internal validation: held-out solve prediction (`arch_b.predict_eval`)

Complementary to the external ranking checks: train on a random 80% of observed
cells, predict the solve probability on the held-out 20%, score with proper rules.
Both arch B fits predict the same quantity on a held-out cell — P(solve within the
contest) — so this isolates the value of the solve-time signal the survival model
uses in training. (Architecture A has no per-cell likelihood, so it is not in this
comparison.)

| model           | log-loss | Brier  | AUC    |
|-----------------|----------|--------|--------|
| arch B binary   | 0.3173   | 0.1001 | 0.8710 |
| arch B survival | **0.3169** | **0.0990** | **0.8810** |

The survival model generalizes **better** on every metric — the AUC lift
(0.871 → 0.881) is the clearest sign that training on solve *times* sharpens the
latent abilities/difficulties. Trade-off: the binary model's probabilities are
very well calibrated (predicted ≈ empirical in every bin), whereas the survival
model is mildly **under-confident** in the 0.5–0.9 range (better ranking, slightly
worse probability calibration — the expected effect of scoring a hazard-model
solve probability against a binary outcome; a recalibrated link is a follow-up).
