# Gym-mirror fixed-θ difficulty (`arch_b.gym_difficulty`)

Consumes `data/cf_gym_mirrors.json` (see the data bullet under follow-ups for how it
was scraped). Every gym solver arrives with a **known ability on the true CF scale**
(`cf_rating_at_attempt`), so unlike both main architectures there is no joint fit:
θ is fixed and each problem's `b_p` is an independent 1-D strictly concave MAP
(the `b` Newton block of `model.py` with per-observation weights, prior
`N(2000, 400²)`). Converges in a handful of iterations; Laplace SE median ~43.
Writes `output/gym_difficulty.json` (700 problems, 57 contests, 23,243 rated team
attempts), which `external_validate` picks up as the third yardstick column.

Key decisions:

- **Trust policy (clist.by-style), since rating & contest count are time-relative.**
  A rating backed by few rated contests is noisy, so each member's likelihood
  weight is the repo's reliability convention `w = 1 − 0.9^n` with
  `n = cf_rated_contests_at_attempt` (1 contest → 0.1, 10 → 0.65, 30 → ~0.96);
  members with no rating yet are excluded, and a team with no rated member is
  dropped (~3% of attempts). Removing the trust weighting entirely barely moves
  the certification numbers, so the policy is cheap insurance, not load-bearing.
- **Team reduction = `lse`:** `θ_team = s·log Σ exp(r_i/s)` — the single solver
  equivalent to the members solving independently (in the hard-problem limit
  P(team solves) ≈ Σ exp((r_i−b)/s)); an equal duo → max+120, trio → max+191.
  Team weight = softmax-contribution-weighted member trust. The obvious
  alternative (`max`: strongest member) certifies identically (ties on all
  yardsticks), so `lse` is kept for the principled team-strength story;
  `--certify` sweeps both.
- **Join by problem name; 5 of the 62 scraped gyms were wrong events.** Gym
  problem *names* come from `data/gym_checkpoints/api_standings.json` and join to
  our problems by normalized title within the contest. All five
  `labels_aligned: false` contests turned out to match **zero** problem names —
  the city/season keyword matching had picked a *different event* in the same
  region/season (four Taiwan contests, e.g. our qoj 2657 is the CF-2172-mirrored
  round but the gym is a separate 2025 Taiwan online round; the Iranian contest's
  qoj names are in Farsi so alignment is unverifiable) — so they are dropped
  wholesale (57 contests / 700 of 763 problems survive). Consequence: the two
  planned certification overlaps with `cf_team_contests.txt` (qoj 2657, 3297)
  were among the bogus five, which forced the certification below onto a
  contest-scoped name vote instead.

**Certification (`--certify`)** — is `b_gym` itself trustworthy?

- **vs official CF ratings:** a contest-level problem-name vote against the rated
  CF problemset (a flat name join is dominated by coincidental generic titles —
  it produced Spearman +0.22 from collisions like "Quick Sort"/"Flowers")
  found one genuine rated mirror among the 57: **qoj 2692 ↔ CF 2157** (not in
  `cf_team_contests.txt`). On its 8 shared problems: Spearman **+0.976**,
  Pearson +0.974, affine slope **1.23** (icept −448, RMSE 213) — i.e. `b_gym`
  is *nearly on the true CF scale already* (compare the survival scale's 2.4×
  compression), which is its main promise as a future calibration anchor.
- **vs Kattis, head-to-head with the survival model on the same 223 problems:**
  gym +0.673 vs survival +0.727 pooled; the gap persists within-contest
  (median +0.824 vs +0.882 over 17 contests), so it is not a cross-contest scale
  artifact. Sweeping the fit knobs (reduction, trust off, solo-only,
  `sigma_b` 400→800, dropping zero-solve attempts — only 1% here) moves nothing
  by more than ~0.01. So the gym population is a **decent but not gold-standard
  referee**: good enough to validate regions (its within-contest ordering vs
  solve rate is near-perfect, median −1.000), authoritative on *scale* (CF check
  above), but a bit noisier than our own survival fit at fine-grained ranking —
  likely virtual-participation effects (solvers who have seen a famous problem
  before) that no fit knob can remove.

**Payload:** the per-region Gym column in the validation table above — in
particular the first external numeric anchor for **Asia East Continent**
(18 contests / 230 problems, all three models +0.95 to +0.98), closing the gap the
regional-bias investigation left open. Run:
`./.venv/bin/python -m arch_b.gym_difficulty` (then `-m arch_b.external_validate`);
`--certify` reproduces the instrument checks.
