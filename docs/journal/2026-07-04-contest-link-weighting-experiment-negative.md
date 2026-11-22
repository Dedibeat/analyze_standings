# Contest-link weighting experiment (2026-07-04): NEGATIVE

Can the contest-linking graph be *weighted* to improve normalization? In the
IRT fit there is no explicit edge weight — linking is emergent through shared
`theta_t` — so "link weight" can only be parametrized indirectly. The global
and per-team versions were already tested in the campaigns (σ_θ sweeps,
evidence-scaled per-team priors, evidence-scaled anchor weight, per-contest
hazard intercepts — all discarded). The two remaining parametrizations are
per-*observation* weights, now supported by both fitters via ``obs_w=``
(default off, baseline byte-identical) and tested on the exact metric+guards
harness:

| variant | rmse | guards |
|---------|------|--------|
| baseline (unweighted) | 288.4 | kattis 0.795 |
| A: arch-A-style reliability `w_t = 1−0.9^N_t` per obs | **305.5** | kattis 0.792 |
| B: thick-bridge contests (>1000 rows: 5 EC qualifiers + Shenyang/Metropolis/Xi'an) ×0.25 / ×0.5 / ×2.0 | 288.3–288.4 | unchanged |

**A is decisively harmful (+17):** one-off teams' observations carry essential
within-contest difficulty evidence, and the Bayesian machinery already
discounts their unreliable *ability* via the θ prior — arch A's `w_t` hack done
properly. Downweighting their observations discounts twice and starves `b`.
**B is perfectly flat in both directions:** the CF anchors don't cover EC (the
qualifiers' linking load), and even the gym EC guard doesn't move, so the
thick bridges are neither a noise source nor an untapped lever. Verdict:
evidence weighting inside the likelihood is a solved problem in the MAP model;
the linking graph is not a knob. Log:
`autoresearch/autoresearch-260704-0130/classic-results.tsv`.
