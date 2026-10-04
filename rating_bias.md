# Rating bias: mechanisms that inflate or deflate estimated difficulties

A catalog of every mechanism in the pipeline that can push a problem's estimated
difficulty away from its true value — up (inflate, rated harder than it is) or
down (deflate, rated easier). Each entry is tagged with its direction and whether
it is a shipped trade-off, a fixed bug, or a latent risk. Grounded in
`details.md` and the code under `arch_a/` and `arch_b/`; written 2026-08 after
the Nanjing 2022 linking audit.

The audit that prompted this catalog: Nanjing 2022's shipped calibrated problem B
("Ropeway") is 2440 CF while the independent CF-gym instrument says 2145. The
conclusion was that the gap is **not** the contest's linking (severing all of
Nanjing's cross-contest links moves its raw difficulties by <25 points) but the
global calibration affine leg, and that 2440 vs 2145 is within the two
instruments' combined noise.

## 1. Data ingestion (`arch_a/load.py`)

| Issue | Direction | Status |
|---|---|---|
| **Zero-solve rows dropped** (13.2% of tagged rows; 73% are real teams' off-days, not non-participants). The surviving population is stronger, so every difficulty shifts up: mean `b` 2462 → 2605, mean `theta` 2018 → 2165. | **Inflate** | Shipped trade-off; documented in the zero-solve decision |
| **Censored no-attempt cells** (`solve_mask`). QOJ omits a problem from a row when the team never attempted it; those cells are right-censored non-solves. Before the fix they were silently excluded, so the likelihood saw only the *attempted* (stronger) subset → biased `b` (Shenyang 2023: raw B 2265 vs M 2226 flips to B 2577 vs M 2480 after the fix; 774,639 observations after). | Both, problem-specific | Fixed + regression-tested |
| **Unknown-label rows dropped** (`row_solved_any`). Rows solving only labels absent from the parsed problem list are dropped (Petroz 2575: 610 such rows). | Inflate (drops low-solving rows) | Fixed + regression-tested |
| **Duplicate contest entries** (up to 6× replay of identical standings). Every row counted 6× → inflated `N_t`, reliability `w_t`, likelihood. Arch A difficulty mean 2605 → 2216 after dedup; LLM agreement +0.792 → +0.908. | **Inflate** | Fixed; idempotent `dedupe_contests` guard kept |
| **One-member / no-member rows** (72 + 1,476 rows) get no usable roster → isolated per-contest keys; their evidence never links across contests. | Deflate (missing linking evidence) | Known limitation (identity decision) |
| **`team_name` unreliable** (33% of recurring teams vary display name across contests); trusted-name fallback is narrow, so some valid links are missed. | Deflate (missing links) | Mitigated by roster keying |
| **Roster pair-overlap union** (any two rosters sharing ≥2 members merge). Merges distinct teams that happen to share two common Chinese names → over-linking, inflated `N_t` and cross-contest evidence. | Inflate | Deliberate; measured ~3.7k near-miss pairs |
| **WF→regional top-team linking** (university → best regional roster of the season). Before the guards were added it affiliation-joined 3,605 no-roster rows in 120 non-WF contests with season keying off. | Inflate (wrong links) | Fixed (calibrated LOCO 266.4 → 264.5) |

## 2. Prior & anchoring (`anchor.py`, `fixedpoint.py`, `model.py`)

| Issue | Direction | Status |
|---|---|---|
| **Constant MU0=2000 prior, PRIOR_STRENGTH=1.0**. One-contest teams lean on MU0: a strong one-off team is pulled *down* (Nanjing 2022 rank-2 逆十字, 11 solves, perf 3299, gets θ 2118), a weak one-off team is pulled *up* toward 2000. | Strong teams **deflated**, weak teams **inflated** (compression toward 2000) | Shipped cold-start necessity |
| **UCup anchor scale** is itself only MU0-anchored in absolute terms; any error in the UCup fit propagates through every linked team and contest. | Both (scale-level) | Shipped; outputs are "relative scale pinned near 2000, not certified CF points" |
| **anchor_weight (arch A) / σ_θ (arch B)** — the pull of the UCup prior; looser → wider scale but more easy problems pinned at 800; tighter → harder pinning. One global knob for all teams. | Both | Tuned (1.0 / 400) |
| **Non-causal reliability weight** `w_t = 1 − 0.9^N_t`, with `N_t` counting *all* contests including later ones (look-ahead). A team's first appearance is weighted using its future contests; a veteran's early-career results are never discounted. | Both | Documented; batch-only, unsuitable for online use |

## 3. Model structure (`model.py`, `survival.py`, `elo.py`)

| Issue | Direction | Status |
|---|---|---|
| **Rasch 1PL vs 2PL discrimination**. EA fields' solve curves are steeper than the global Rasch slope (EA discrimination ~2.1); a single slope misplaces medal cutoffs (predicted−actual solve rate +0.10 at bronze, +0.34 at gold). | Both, worst near cutoffs | Documented; 2PL is a follow-up (`twopl.py` exists) |
| **σ_θ = σ_b = 400 shrinkage** (MAP prior). Compresses the scale: 14 easy problems pin at the 800 floor, the hard end under-spreads. | Easy end inflated to 800, **hard end deflated** | Shipped choice; agreement peaks/plateaus at 400–800 |
| **Clamps [800, 4000]**. Solved-by-all → 800, solved-by-none → 4000. Arch A had 66 at 800 / 98 at 4000 before boundary smoothing. | Both (boundary collapse) | Smoothed (arch A dummy teams) / prior-held finite (arch B) |
| **Survival model `T_c` proxy** = latest observed solve time (no duration field; clusters at 5 h); `λ0 = ln2/T_c` fixed per contest. A wrong duration assumption scales the baseline. | Minor, uniform | Accepted; robust by design (`T_c` cancels for non-solves) |
| **`wrong_attempts` never used** — only solve time enters; a problem with many failed attempts but the same solve-time distribution rates as easier. | Deflate | Untapped signal |
| **No-attempt cells as full-window non-solves** — strong teams that skipped a problem look weak on it. | Deflate | Deliberate right-censoring |

## 4. Linking graph (the "inflated contest" class)

| Issue | Direction | Status |
|---|---|---|
| **Contest scale is set entirely by its linkers**. An unlinked contest collapses to MU0; a contest whose linkers are atypically strong (many UCup top teams) is lifted; one carried by a thin minority of linkers sits on a noisy scale (Europe 10%, Asia Pacific 29% median linkers/contest vs Asia East Continent 65%). | Both, contest-level | Documented (linking caveat) |
| **Cross-contest θ pumping** — the mechanism "teams got stronger elsewhere → this contest's problems rate harder". Real for small fields riding on a few linkers; negligible for 600+ team contests (Nanjing isolation experiment: raw `b` moves +0.8…+22.5 points, Ropeway +3.7). | Inflate (small contests) | Verified per-contest via the isolation control |
| **Time-invariant team ability** — teams improve (static-fit residuals rise ~15 points/year within a team, ~40 for weak teams), so one ability per team is too high in its early contests and too low in its late ones. A random-walk fit moves 2022 problems 12–32 points easier and 2025–26 ones 2–8 harder (q = 50–100 per year); static CF-anchor residuals trend the same way by year (+135 in 2022 to −62 in 2026, one contest at each end). The random-walk fit itself does not improve CF-anchor LOCO (+0.7 / +2.4, n.s.). | Older contests **inflated**, newest **deflated** | Measured, not changed (`arch_b.dynamic_rating`, 2026-10-04) |

## 5. Calibration (`calibrate.py`, `gym_difficulty.py`)

| Issue | Direction | Status |
|---|---|---|
| **Affine leg `cf = 0.91·f(b) + 465`** — a global +~300 lift in the 1800–2500 range (Nanjing's whole contest sits +295…+533 above the CF-gym instrument). | **Inflate** (mid-range) | No systematic in-sample bias found (mean −23 in the 2000–2400 band); per-contest scatter ±150–250 |
| **Gym↔CF certification rests on 8 problems** (qoj 2692 ↔ CF 2157, slope 1.23, RMSE ±250). If the gym scale is off, both the shape leg and the affine leg inherit it. | Both | Thin ground truth; only 1 overlapping contest exists |
| **Anchor pool = 15 contests / 185 problems**, dominated by championships (hard problems). A mid-range bias is under-identified by the pool. | Both | LOCO-validated (244 RMSE) but a fixed pool is a known residual risk |
| **Shape leg is in-sample for most gym contests** (only qoj 2692 excluded) — it absorbs per-contest raw-scale offsets, so it can hide rather than reveal them. | Deflate (hides errors) | By design; monotone, cannot reorder problems |
| **`difficulty_cf_se` is conditional** (local slope only) — understates the real cross-instrument uncertainty (~±250 vs the shown ±23). | Deflate (overconfidence) | Documented as approximate |

## Bottom line (from the Nanjing 2022 audit)

1. **"Participating teams got stronger" → not supported.** Severing all of
   Nanjing's cross-contest links moves raw difficulties by <25 points.
2. **The visible 2440-vs-2145 gap → the calibration affine leg**, not the
   linking; it is within the two instruments' combined noise, and no in-sample
   bias was found.
3. **The biggest real risks elsewhere**: zero-solve-row dropping (shifts all
   difficulties up), the MU0-prior compression of strong one-off teams
   (deflation), and the thin gym↔official-CF ground truth underpinning the whole
   calibration.
