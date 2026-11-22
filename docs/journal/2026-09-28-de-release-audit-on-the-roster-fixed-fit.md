# DE release audit on the roster-fixed fit (2026-09-28)

**Request.** Prepare to ship the binary-survival disagreement calibration (DE)
with this session's roster data fix. Run the audits documented in the repo
(`shipped_fit_update_plan.md`, `calibration_interpretation.md`,
`experiment_roadmap.md`) and consider six ChatGPT recommendations. The user also
pointed to Halpin (2022), *Differential item functioning via robust scaling*.
The full write-up is [de_release_audit.md](../reports/rating/de_release_audit.md). No production
rating, calibration or export changed.

**Code.**
- `scripts/attach_online_rosters.py` is the roster fix as a data-layer script.
  It reproduces the tested variant B exactly and is idempotent. It has not been
  applied to `data/tagged.json`.
- `arch_b.de_release_audit` (calibration layer) and `arch_b.fit_mechanism_audit`
  (fit layer) write `output/de_release_audit.json` and
  `output/fit_mechanism_audit.json`.
- `joint.load_joint_dataset`/`estimate_joint` take a `tagged` path, and
  `calibration_experiment.build_anchor_table`/`_full_rows` take in-memory binary
  records.
- Tests: `tests/test_release_audit.py`.

**Bug fixed: platform-dependent gym map.**
- **Cause:** `calibrate._gym_shape` used `np.argsort`'s unstable default on
  one-decimal difficulties with ties.
- **Effect on Windows (numpy 1.26):** rerunning the calibration would move
  2,949 of 3,159 shipped ratings by up to 17.2 points.
- **Test symptom:** `test_calibration_experiment` got 245.567 instead of the
  documented 245.4277. That is the failure the previous section attributed to
  the committed state.
- **Fix:** a stable sort. It reproduces the shipped ratings and the documented
  LOCO exactly, and all 108 tests now pass.

**Results (candidate = roster-fixed fit):**
- **DE on the candidate.** LOCO 226.32 (raw 246.93, gym map 246.13) and LORO
  225.69. DE is chosen in 15/15 folds and wins 10/15 contests against the gym
  map. The proxy guards are unchanged, and `arch_b.metric` reads 246.3 on the
  candidate (245.4 now).
- **Leave-one-evidence-feature-out and safer variants** (#6): SE +1.9, solve
  rate +6.8, field size +0.7 [−4.7, +5.5]. A blend alone scores 241.2;
  blend + evidence 225.5; clipping to the training range 226.0; Mahalanobis
  shrinkage 225.6.
- **Stress test.** With the three smallest-field anchor contests held out, DE is
  worse than raw (211.0 vs 201.0); clipping gives 204.1. Every other tail
  favours DE.
- **Gym-population robust scaling** (655 non-anchor problems; Halpin-style
  bisquare contest offsets). DE's per-contest levels agree best: offset SD 96
  against raw 133 and the gym map 120. The gym map was fit on this data. DE
  also wins on both field tails, so field size is useful beyond the anchor
  range; dropping it is worse (122).
- **Catalog.** 137 appearances (fields under 31, partial North America boards)
  and 88 (fields over 1,083, including all online rounds) are outside every
  field-size evidence. DE moves them +188 and −143; clipping moves them +55
  and −34.
- **Online vs onsite** (#1; 2,013 roster-verified teams, whole appearances
  held out). Hidden online rows are under-predicted by +0.35 solves
  (survival) / +0.29 (binary); hidden onsite rows are over-predicted by −0.11 /
  −0.20. The paired online-minus-onsite offset is +69 [+62, +76] survival
  points and +102 [+88, +117] binary points (≈ CF points). It is concentrated
  in the stronger two-thirds of teams. Online mirror rows on regional boards
  show +0.95 solves.
- **Online offset inside the fit.** It cannot be estimated for all-online
  contests: it trades one-for-one with those problems' levels (−137 / −131,
  held-out Δ −0.0001). The online-round ratings therefore rest on the
  equal-performance assumption that these data contradict.
- **Disagreement decomposition** (#2). The ability-scale and likelihood parts
  each recover only part of DE's gain (231.9 / 232.7; both together 229.6; D
  226.3). CF ≈ 0.98 × θ_binary and 0.98 × b_binary, but 2.85 × θ_survival and
  1.65 × b_survival. The survival fit compresses abilities.
- **Timing** (#3). The survival conditional-time PIT rises from 0.49 on a
  team's first solve to 0.82 on its 11th or later: sequential solving is read
  as weakness. In-sample, final solves are over-predicted for weak rows
  (2.42 vs 1.62) and under-predicted for strong rows (6.90 vs 8.45). No new
  timing model was built.
- **Team-season offsets** (#4). They improve held-out log loss by 0.0024–0.0034
  in every season, 2022–23 included, but CF LOCO gets worse (DE 230.0 at
  τ = 100, +3.7 [+0.2, +7.5]). They suit team-performance outputs, not this
  release.
- **Fresh anchors** (#5). A fresh CF problemset has 159 newly rated problems in
  26 contests; none of them is in the data. The only shared tasks are the five
  Luxor pairs.

**Verdict.** DE passes every development and independent check that could be
run. Three decisions are still open:
- accepting the release without a fresh confirmation set (none exists);
- the policy for the 225 appearances outside any field evidence (clipping is
  recommended);
- labelling the online-round problems as a separate scale.

Release steps are listed at the end of `de_release_audit.md`.

Run (≈25 min): `python3 scripts/attach_online_rosters.py data/tagged.json /tmp/tagged_rosters.json`,
then `python3 -m arch_b.de_release_audit /tmp/tagged_rosters.json` and
`python3 -m arch_b.fit_mechanism_audit /tmp/tagged_rosters.json` (on Windows set
`PYTHONUTF8=1`).
