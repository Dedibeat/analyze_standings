# Auto-research campaign on the metric (2026-07-03): verdict PLATEAU

A 25-iteration autoresearch loop (`program.md`) attacked `loco_cf_rmse`
(baseline **290.2**) with one structural change per iteration. The loop ran in
two phases: iterations 1–15 by **Claude Fable 5**, iterations 16–25 by
**DeepSeek v4 Pro** (after a session handoff). **2 iterations kept, 23
discarded** — the model is at a robust local optimum; further gains need new
anchor data rather than fit changes. Final metric **288.0** (−2.2, under the
±5-point threshold but held-out AUC corroborated: 0.8810 → 0.8858). Full
per-iteration log in `autoresearch/autoresearch-260703-1733/classic-results.tsv`.

The only successful changes were **data-side identity fixes** (both by Fable):
the roster token was normalized (Unicode NFKD + strip case/punctuation) and
rosters sharing ≥2 members were unioned (~3.7k near-miss pairs resolved), then
domjudge rows with no roster were linked across contests by trusted recurring
team names (~5.3k names × ~13k appearances). Together they cut RMSE from 290.2
to 288.0 while improving survival held-out AUC from 0.8810 to 0.8858 and
lifting the gym-pooled guard from 0.950 to 0.954.

**Everything else was within noise or worse** (range 286.8–321.9; best single
improvement −1.2 from the new baseline at σ_θ=600, but AUC regressed to 0.8838
so it was discarded per the corroboration rule). The deepseek phase (10
iterations) retried the most promising fable-era ideas on the improved identity
graph (σ_θ=500/600, Weibull k=1.25, per-contest hazard intercept, evidence-
scaled priors, time-varying θ, anchor weight) — all either regressed AUC or
landed within noise. Two additional identity experiments (lower name threshold,
1-member rosters) made things worse. A data-driven per-problem prior (solve-rate
→ μ_b) blew up to 305.9 — confirming the Rasch likelihood alone is better than
any heuristic prior.

**Where the error lives** (unchanged from the original report — identity fixes
don't touch the hard tail because 0–1 solver problems have no linking data to
improve): the cf[3200,3600) bucket carries ~41% of pooled MSE (n=28, RMSE
~476, bias −321) — nothing in standings data distinguishes CF 2900 from CF 3500
when at most one team solved. Per-contest offsets contribute ~13%; the rest is
within-contest variance. Progress needs new anchor data: more CF-rated mirrors
in `tagged.json`, ideally gym-covered, or member→CF-handle data for true
ability anchoring.
