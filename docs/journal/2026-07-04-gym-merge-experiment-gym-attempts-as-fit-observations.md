# Gym-merge experiment (2026-07-04): gym attempts as fit observations — NEGATIVE

The natural follow-up to the reverted gym *prior*: merge the gym-mirror
attempts into the main fit as **likelihood terms** instead — the strat's
original CF anchor (eq. cfprior) realized on the only population with known
CF ratings. `arch_b/gym_merge.py` turns `load_gym()` into fixed-θ Bernoulli
observations (θ = `team_theta` lse reduction, trust-weighted) joined to the
tagged problem indices; `model.fit` / `survival.fit` accept them via
`gym_obs=` and accumulate them in the `b` Newton block only (mixed
binary+survival likelihood, still concave; gym attempts carry no per-problem
times). qoj 2692 — verified as the *only* overlap between the 56 usable gym
contests and the 15 CF-anchor contests — is always excluded (its `b_gym`
correlates +0.976 with the metric target there: a leak). A global weight λ
balances the large gym fields (277k attempts on 688 problems) against the
onsite signal.

**Result: discard at every weight.** The metric moves sub-noise while both
genuinely independent checks degrade monotonically with λ:

| λ    | loco_cf_rmse | Kattis pooled | held-out AUC |
|------|--------------|---------------|--------------|
| 0 (baseline) | 288.4 | 0.795         | 0.8851       |
| 0.1  | 287.2        | 0.773         | —            |
| 0.3  | 286.9        | 0.755         | **0.8771**   |
| 1.0  | 288.8        | 0.736 (guard FAIL) | —       |

(The gym EC/pooled guards *rise* with λ — 0.962 → 0.985 at λ=1 — but they are
circular for this change, same source data, and were ignored for the verdict.)
This quantitatively confirms the certification's warning: the gym population
is authoritative on **scale** but noisier than our own survival fit at
fine-grained **ranking** (virtual-participation effects), so injecting it into
the likelihood trades our sharper ordering for its scale — and the LOCO metric,
whose per-fold affine map absorbs scale anyway, can't reward the trade. Same
verdict as the prior-form (80afc92, reverted): the gym signal's home is the
**calibration layer** (per-region CF map on `b_gym` anchors), not the fit.
The machinery stays as an opt-in (`estimate_anchored(gym_merge=λ)` or
`ARCHB_GYM_MERGE=λ`, default off — verified byte-identical baseline when off);
log in `autoresearch/autoresearch-260704-0110/classic-results.tsv`.
