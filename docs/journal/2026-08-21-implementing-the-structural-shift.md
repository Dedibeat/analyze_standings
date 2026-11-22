# Implementing the structural shift (2026-08-21)

The five steps proposed by the anchoring audit above, as built and measured.
Every number is from `arch_b.metric` (the shipped calibrated LOCO CF-point RMSE
plus its guards) unless stated otherwise; the pre-change baseline is **244.3**.

## 1. Sparse data layer — done

`arch_a.load` stored `y`, `solve_mask`, `tau` (float64) and `wrong` (int64) as
dense `n_rows x n_problems` matrices that were **99.65% empty**: a cell is
observed only where the problem belongs to the row's contest. `Dataset` now
carries the observed cells in COO form — `obs_row`, `obs_prob`, `obs_y`,
`obs_tau` (float32), `obs_wrong` (int32) — in the exact row-major order
`np.nonzero(solve_mask)` produced, plus precomputed `solved_count` and
`field_count` for the per-problem reductions seven call sites were doing by
hand. `model._observations` / `survival._observations` now read the arrays
directly instead of flattening a dense matrix back into them.

| | before | after |
|---|---:|---:|
| peak RSS, `arch_b.run --survival` | 6,177 MB | **696 MB** |
| runtime | 12 s | 10 s |
| `calibrated_loco_cf_rmse` | 244.3 | **244.3** (bit-identical) |

`arch_a.run` reproduces its documented `theta=[1372, 3698]` mean 2011 and median
solve-count Spearman −0.995. This was the prerequisite for step 2: at joint size
(94,093 rows x 3,464 problems) the dense layout needs ~11 GB and OOMs on a 16 GB
machine.

## 2. One fit, one scale — done

`arch_b/anchor.py` became `arch_b/joint.py`, `estimate_anchored` became
`estimate_joint`, and the Universal Cup is now ordinary fit data rather than a
separate Phase-1 anchor. `arch_a.anchor` is untouched: there the prior
*strength* scales with each team's UCup evidence and it does measurably tighten
the scale (shared-team RMSE 519 → 301).

| | before | after |
|---|---:|---:|
| `calibrated_loco_cf_rmse` | 244.3 | **245.4** |
| raw affine LOCO | 245.4 | 246.9 |
| rated problems | 2,475 | **3,159** |
| gym EC / gym pooled / Kattis / AOJ | +0.978 / +0.969 / +0.772 / +0.568 | +0.977 / +0.969 / +0.772 / +0.568 |

The +1.1 cost is inside the ±20 bootstrap noise floor and well under
`program.md`'s 5-point keep threshold. In exchange the second scale is gone:
all 684 UCup-only exported problems now come from the shipped fit and match
`output/problem_ratings_calibrated.json` to within rounding (max |diff| 0.2),
against a **mean +79 CF shift** from the old two-scale export. `external_validate`
is unchanged within noise (CF pooled +0.941, Kattis +0.770, gym +0.969, LLM
+0.911). `export_virtual_calc` no longer needs a second fit or `exclude_ids`
(241 contests, unchanged); `data_influence._fit` always includes UCup so its
supplemental variants stay comparable, and its recorded artifact needs
regenerating.

## 5. Ability-side Codeforces anchoring — done, and inert

`arch_b/cf_prior.py` turns `data/cphof_cf_participants.json` into a
time-accurate Gaussian prior on team ability — `strat.tex` eq. cfprior, and the
only anchor that reaches Asia East Continent (79% of the corroborated
appearances). Conservative by construction: roster-complete rows only, a
leak-free 1-January-of-the-season cutoff (regionals carry no start time), the
`lse` team reduction, trust-weighted precision, and placement *relative* to
`MU0` so no CF level enters the fit. `joint.estimate_joint` gained a `prior`
hook; both fitters already accepted a per-team `sigma_theta` array.

Coverage is 57 team identities from 310 standing rows, and the sweep is flat:

| scale \ cf_sigma | 100 | 200 | 400 |
|---|---:|---:|---:|
| 0.5 | 245.6 | 245.4 | 245.4 |
| 1.0 | 245.6 | 245.4 | 245.4 |

with every guard unchanged. Same mechanism as Finding 1: those 57 teams are
World-Finals-level rosters that play many contests, so their own likelihood
already pins them. It is therefore **off by default**.

Its value is as a yardstick. `python -m arch_b.cf_prior --validate` gives the
repo's first external check of the **ability** axis, which no other yardstick
reaches:

    fitted theta vs CF team ability: Pearson +0.752  Spearman +0.762  (57 teams)
    cf_ability ~ 2.86 * theta - 3699   (sd ratio 3.80, residual sd 220 CF)

That 2.86 is much steeper than the **1.63** slope the shipped difficulty map
applies over the same range, even though `theta` and `b` share one logit scale
by construction — so the compression is not a single global factor, and the
ability axis is compressed more than the difficulty axis where they overlap.
(Caveat: this population is elite and narrow — theta sd 88 against CF sd 334 —
so range restriction and errors in `theta` both inflate the slope estimate.)

## 4. Hierarchical calibration — done; ships as the uncertainty model

`arch_b/hier_calibrate.py` fits `cf = A*f(b) + B + u_contest + v_region` with
partially pooled Gaussian random effects: empirical-Bayes group means
`n_g/(n_g + sigma^2/tau^2) * mean residual`, and method-of-moments variance
components debiased by the sampling variance of a group mean (estimating `tau`
from the *shrunken* means instead collapses it to zero — the first version of
this module did exactly that and reported `tau=0`). An `offsets=` hook accepts
an external per-contest level observation as a weighted pseudo-observation of
`u_c`.

On the survival fit's 185 anchors (15 contests, 3 regions):

    sigma = 228.0    tau_contest = 72.4    tau_region = 12.0   CF points
    per-region level: Asia Pacific +0.0, Europe +3.3, Northern Eurasia -3.4

**This is the substantive result.** Contest-to-contest level varies materially
(tau 72 CF), but the between-*region* level, among three regions as different as
Asia Pacific, Europe and Northern Eurasia, is essentially nil — 12 CF points.
That is direct evidence that the 100+ point region gaps the gym (+117 Europe
over Asia East) and the LLM bucket labels (−134 on the same pair) disagree about
in Finding 5 are **referee artifacts, not fit bias**. It does not prove Asia
East is unbiased — no CF anchor reaches it — but it removes the prior that large
regional level bias is the norm.

LOCO does **not** improve: 245.4 plain vs 248.3 hierarchical. A held-out contest
cannot know its own `u`, and with `tau_region` at the noise floor there is
nothing for the region effect to transfer. The shipped map therefore stays the
plain global affine.

What did change is the reported uncertainty. `difficulty_cf_se` previously
scaled only the Laplace SE of `b` through the map — treating the map itself as
exact. It is now the quadrature sum of that (kept as `difficulty_cf_fit_se`) and
the calibration **level** sd (`difficulty_cf_level_sd`): the posterior sd of its
own offset for the 15 anchored contests (~48 CF), and `sqrt(tau_c^2 + tau_r^2)`
= **73.4 CF** for the 2,970 problems no CF anchor ever saw.

| | median | mean |
|---|---:|---:|
| `difficulty_cf_fit_se` (old meaning) | 46.8 | 61.2 |
| `difficulty_cf_level_sd` | 73.4 | 71.9 |
| `difficulty_cf_se` (new total) | **86.4** | 99.7 |

The level term is larger than the fit term for a typical problem, so the old
figure understated the real uncertainty by about half. `calibrate`,
`export_ucup_only` and the Architecture B viewer all report the same total.

## 3. Cross-contest LLM comparisons — instrument built and validated

**2026-09-05 correction:** the comparisons were collected, but the offset
validation below leaks held-out CF ratings (`llm_crosscontest.py:457`). The
245.4 → 242.8 improvement and offset correlation do not validate a deployable
instrument. See [experiment_review.md](../reports/rating/experiment_review.md), finding 1.

`llm_crosscontest.py` pairs problems **across** contests, the axis
`llm_survival.py` never touched (`_make_requests` groups by `contest_id`, and
its scope is asserted to the 185 problems of the 15 rated mirrors). Same
statement-only prompt, same metadata sanitizer, both A/B orientations, a seeded
schedule whose partners are drawn **uniformly from other contests** — never using
our difficulty, a CF rating, or any other target proxy — and resumable
checkpoints behind a hard preflight budget gate. `bt_scores` refits
Bradley--Terry by coordinate Newton in O(edges) per sweep, because
`llm_survival.bt_fit` builds a dense `(n-1)^2` Hessian per iteration, which is
fine for one 13-problem contest and hopeless for a cross-contest graph.
Statements that cannot be made metadata-free are **skipped**, never sent with the
leak (the Phase-3 forensics showed verbatim ids and labels invalidate the
comparison); that costs a handful of problems.

**Validation stage, dispatched.** 185 problems / 15 CF-mirrored contests, 698
cross-contest unordered pairs in both orientations = 1,396 requests to
`gemini-3.5-flash`, exact `countTokens` preflight **$3.5402**, all 1,396
returned valid decisions (2 transient failures retried). The global BT is fitted
over these new cross-contest edges *plus* the 2,128 within-contest predictions
the earlier run already paid for.

The instrument is **not** damaged by crossing contests — raw pairwise accuracy
against official CF ratings is nearly the same either way, with the same
gap profile:

| CF rating gap | cross-contest | within-contest |
|---|---:|---:|
| <= 200 | 0.531 | 0.579 |
| 300-500 | 0.619 | 0.658 |
| 600-1000 | 0.711 | 0.752 |
| > 1000 | 0.899 | 0.895 |
| **all** | **0.717** (n=1,394) | **0.754** (n=2,054) |

A/B order consistency was 0.784, in line with the within-contest run's 0.816.

But as a *global* difficulty estimator it is far behind the standings fit —
Spearman against CF **+0.634** for the cross-contest BT versus **+0.943** for
survival — and the level signal it does carry is weak:

    correlation of BT-implied vs true per-contest offsets:  +0.540  (15 contests)
    optimal shrink factor k:                                 0.453
    LOCO plain 245.4  ->  LOCO + shrunk BT contest offset 242.8   (-2.6)

with `k` and the affine leg both refit inside each fold and the held-out contest
contributing only its own BT offset. **Applying the offsets raw makes things
worse** (247.6): they are about half noise, so they must be shrunk — the first
version of `analyse` skipped that and reported a false negative.

The mechanism is visible in the accuracy table. Contest levels differ by
`tau_contest = 72` CF points (step 4), which is deep inside the <= 200 gap band
where the model runs at 0.53 — barely above chance. The instrument measures the
right quantity on the right axis; its resolution is simply coarser than the
quantity.

**A fixed-position variant is worse, not better.** Holding each problem at our
own calibrated difficulty and fitting one free level per contest — the
`gym_difficulty` pattern, and the better-posed estimator on paper — scores
offset correlation +0.36 to +0.40 across `kappa` in {200, 400, 600}, against
+0.540 for the free BT. Fixing positions forces every disagreement with our
within-contest ranking into the offset as noise; the free BT uses the
within-contest edges to pin positions from the model's *own* view and isolates
the level better. That matters for costing the deployment stage: the validated
estimator **needs within-contest edges too**, not only cross-contest ones.

**Deployment stage: not dispatched.** The full scope is 2,345 statement-bearing
problems over 191 contests (Universal Cup 642, Asia East 458, Europe 442, North
America 312, Asia Pacific 279, Northern Eurasia 140, Latin America 37, Asia West
35 — exactly the regions with no anchor). Cross-contest pairs alone at 4 matches
per problem cost about $21, which fits the remaining budget; but adding the
sparse within-contest schedule the validation showed is necessary (~10 matches
per problem, the density `llm_survival`'s own sparse-schedule analysis selected)
takes the full scope to roughly **$75** — over the approved cap. A targeted
build covering only the unanchored regions plus the 15 anchored mirrors as
bridges (~1,027 problems) is about **$21** and would fit. That scope change was
not pre-approved, so the run is prepared but not dispatched.
