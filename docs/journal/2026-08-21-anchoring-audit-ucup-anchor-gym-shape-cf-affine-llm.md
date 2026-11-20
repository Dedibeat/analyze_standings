# Anchoring audit: UCup anchor, gym shape, CF affine, LLM comparisons (2026-08-21)

A review of every mechanism that pins the difficulty scale — the Phase-1
Universal Cup prior, the gym-learned monotone shape, the CF affine leg, and the
LLM opinions — asking where the scale is actually anchored, how consistent it is
across contests and regions, and why the exported UCup ratings disagree with the
shipped fit. All numbers are measured on the current shipped survival fit; the
fit variants A–D are scored on exactly the metric `arch_b.metric` prints (which
reads **244.3** today). No repository code was changed to produce them.

## Finding 1 — the UCup prior-mean anchor is a no-op in Architecture B

`arch_b.anchor` feeds each UCup team's Phase-1 `theta_u` in as its Gaussian
prior *mean* at the single global `sigma_theta=400`. Refitting with that prior
replaced by the flat `MU0` — same union-find, so identity links are held
constant and only the prior mean changes — moves the fit by

    delta b:     mean -3.6, sd 0.96, max |delta| 10.3, corr 0.999997
    delta theta: mean -4.2, sd 4.9,  max |delta| 72.6

and leaves the metric identical (244.3 anchored vs **244.3** unanchored, all
guards unchanged). Two reasons: at `sigma_theta=400` a well-observed team is
dominated by its own likelihood (the documented design intent), and the affine
calibration leg absorbs any global level shift the anchor could produce. What
actually normalizes the scale is the shared union-find plus the joint
likelihood — consistent with the existing no-link control (LOCO 244.2 → 333.5).
Unlike `arch_a.anchor`, whose prior *strength* scales with each team's UCup
evidence, arch B's anchor has no measurable effect on the shipped deliverable.

## Finding 2 — the exported UCup-only ratings sit ~90 CF points too low

`arch_b/export_ucup_only.py` rates the 52 UCup-only contests from the **Phase-1
UCup-only fit** (`b_u`) and then pushes them through the shape+affine map fit on
the **tagged-scale** `b`. Those are two different fits with two different
scales — the very premise the two-phase anchor exists to address. 24 contests
appear in both fits, giving 305 problems rated twice:

    mean b_tagged 2318   mean b_ucup 2260   offset -59
    b_ucup ~ 0.959 * b_tagged + 36   (RMSE 65, corr +0.998, residual sd 23)
    per-contest offset range: -39 .. -70 (all 24 contests negative)

The UCup-only fit is a near-perfectly ranked but systematically compressed and
shifted copy of the tagged scale, so applying the tagged-domain calibration to
it under-rates every exported problem. Correcting `b_u` through the measured
crosswalk before calibration raises `output/ucup_only_ratings.json` by **+90 CF
points on average** (mean 2418 → 2508, max shift 147, largest in the hard tail).
The same mismatch affects the UCup half of the virtual calculator, whose UCup
abilities come from the same Phase-1 fit
(`theta_ucup ~ 0.851*theta_tagged + 261`).

## Finding 3 — one joint fit removes the second scale at no metric cost

Since the anchor is a no-op (Finding 1) and the second scale is the source of
Finding 2, the structurally simpler option is to fit UCup as ordinary data.
Four variants, same union-find construction, same metric and guards:

| variant | fit inputs | prior mean | problems | CAL LOCO | raw LOCO | gym EC | gym all | Kattis | AOJ |
|---------|-----------|------------|---------:|---------:|---------:|-------:|--------:|-------:|----:|
| A (shipped) | tagged+supp | UCup Phase-1 | 2475 | **244.3** | 245.4 | +0.978 | +0.969 | +0.772 | +0.568 |
| B joint | tagged+supp+UCup | MU0 | 3159 | **245.4** | 246.9 | +0.977 | +0.969 | +0.772 | +0.568 |
| C joint+prior | tagged+supp+UCup | UCup Phase-1 | 3159 | 245.9 | 247.2 | +0.977 | +0.969 | +0.771 | +0.568 |
| D no anchor | tagged+supp | MU0 | 2475 | **244.3** | 245.4 | +0.978 | +0.969 | +0.773 | +0.568 |

B costs +1.1 CF points — inside the ±20 bootstrap noise floor and well under
`program.md`'s 5-point keep threshold — while putting 684 more problems on the
shipped scale and removing the Phase-1/Phase-2 mismatch by construction.

**Blocker:** `arch_a.load` materializes dense `rows x n_problems` arrays (`y`,
`solve_mask`, `tau` float64, `wrong` int64). At 94,093 rows x 3,464 problems the
joint fit needs ~2.6 GB for `tau` alone and ~11 GB at peak, which OOMs on a
16 GB machine; variants B/C above were only measurable after temporarily
narrowing `tau` to float32 and `wrong` to int16 (verified neutral: patched
variant A reads 244.3, identical to the unpatched `arch_b.metric` run). Observed
density is ~0.35% (774,639 observed cells out of 223M dense cells), and
`model._observations` flattens the matrices to 1-D anyway, so a per-contest
block or COO layout is a prerequisite for the joint fit, not an optimization.

## Finding 4 — cross-contest offsets are small and bounded

Decomposing the in-sample residual of the shipped map on the 185 CF anchors:

    residual sd 240.3 = between-contest 99.5 + within-contest 218.7
    per-contest constant offsets account for 17.1% of residual variance
    oracle per-contest intercept:        RMSE 240.3 -> 218.7
    oracle per-contest intercept+slope:  RMSE 240.3 -> 207.6

Per-contest offsets run from -161 (CF 1773) to +267 (CF 2068), but the
within-contest slope is stable (mean 0.906, sd 0.105, vs a global 0.909) and
within-contest Spearman is +0.85 to +1.00. So inside the anchored regions the
contest-to-contest inconsistency is real but bounded: perfect per-contest
re-anchoring would buy ~22 CF points, and there is no residual within-contest
compression left for a better map to remove.

## Finding 5 — the per-region level is not identified: the two standings-free referees disagree in sign

Scoring the shipped `difficulty_cf` per region against the **gym** yardstick
mapped onto CF points by its certified transform (`cf ~ 1.23*b_gym - 448`), SEs
clustered by contest:

| region | n | contests | offset (ours - gym) |
|--------|---:|---:|---:|
| Europe | 294 | 24 | +321 ± 32 |
| North America | 24 | 2 | +337 ± 34 |
| Asia West Continent | 21 | 2 | +264 ± 49 |
| Asia East Continent | 230 | 18 | +204 ± 27 |
| Asia Pacific | 98 | 8 | +154 ± 74 |

The pooled level is not interpretable (the gym transform rests on 8 problems),
but the *differences* are, since one transform applies to every region:
Europe − Asia East = **+117 ± 42**, Asia East − North America = **−133 ± 44**,
Asia Pacific − North America = **−183 ± 82**.

Repeating the same measurement against the **LLM bucket** referee (`tagged.json`
`difficulty_estimate`, editorial-backed contests only; each problem's residual
is taken against the global mean `difficulty_cf` of its own bucket — easy 1638,
medium 2225, hard 2675, very_hard 3247):

| region | n | contests | offset (ours - LLM bucket) |
|--------|---:|---:|---:|
| Asia East Continent | 420 | 33 | +65 ± 15 |
| Latin America | 13 | 1 | +18 ± n/a |
| Asia Pacific | 203 | 16 | +5 ± 31 |
| North America | 75 | 7 | −21 ± 32 |
| Europe | 274 | 23 | −69 ± 26 |
| Northern Eurasia | 105 | 9 | −74 ± 45 |

Here Asia East − Europe = **+134 ± 30** and Asia East − North America =
**+86 ± 35** — the **opposite sign** of the gym result on the same pair of
regions. Within-region ranking is excellent against both referees (+0.95 to
+0.98 on gym), so this is purely a level effect; but the two standings-free
referees do not agree on which way the level is wrong.

The conclusion is that a per-region level correction **cannot be estimated from
either referee alone today**. Each carries its own region-specific population
bias: the gym measures who chooses to virtual-participate in which region's
mirror, and the LLM bucket is a 4-level absolute label whose meaning can drift
with statement style, length, and translation quality by region. This retires
the obvious next move (adding per-region offsets learned from the gym) — it
would bake in a bias the other referee reverses.

## Finding 6 — the LLM comparison instrument was pointed at the wrong axis

`llm_survival.py` is the one referee that can be forced into a *direct*
cross-region head-to-head, which is exactly what removes the absolute-scale
drift that spoils the bucket labels in Finding 5. As built, it cannot: the
pilot asserts its scope to the 185 CF-anchored problems in 15 mirrors, and
`_make_requests` groups by `contest_id` and pairs only within a contest, so the
Bradley–Terry scores in `llm_survival_run/analysis.json` are **per contest**
(`bt.per_contest[cid].bt_scores`) with no edges between contests.

That is the axis where the fit is already strongest — within-contest Spearman
vs CF is +0.85 to +1.00 and there is no within-contest compression left
(Finding 4) — which explains why the fusion result was flat-to-negative (nested
contest-level LOCO 275.68 survival vs 282.31 fused). It says nothing about the
cross-contest and cross-region levels, which is the open question.

The instrument is also the only anchor candidate with full regional reach.
Statement coverage is **100% for all 1,668 tagged problems in every region**
(Asia East 466, Europe 356, Asia Pacific 324, North America 300, Northern
Eurasia 140, Asia West 45, Latin America 37) and **100% for all 989 UCup
problems**; only the 850 standings-only supplemental problems (Petroz, 2020–21
ICPC) have none. Compare the current external coverage in Finding 7. The prior
full run was 2,128 requests at an estimated $5.4270 (~$0.0026/request), so a
cross-contest schedule sized for contest-level offsets — order 40 cross-contest
pairs per contest over ~207 contests, both orientations — is roughly 17k
requests, i.e. tens of dollars, not hundreds.

Two design points carried over from the existing experiments: run both A/B
orientations and keep only order-consistent pairs (the within-contest run scored
81.6% consistency), and prefer `gemini-3.6-flash`, which the 2026-08-21 gap
check found markedly more order-consistent than 3.5 (82.6%/84.6% vs
78.3%/57.7%) at indistinguishable accuracy. Crucially the new instrument can be
**validated before it is trusted**: a cross-contest schedule restricted to the
15 CF-mirrored contests can be scored against the known per-contest CF offsets
of Finding 4, so whether cross-contest LLM BT recovers real level differences is
a measurable question answered on existing anchors.

## Finding 7 — anchor coverage, not fit quality, is the binding constraint

Of the 207 fitted contests, **92 (44%)** have any external anchor at all and
only 15 have a CF-rated mirror:

| yardstick | contests |
|-----------|---------:|
| CF rated mirror | 15 |
| gym mirror | 54 |
| Kattis | 45 |
| AOJ | 4 |
| **any** | **92 / 207** |

Unanchored by region: all 75 supplemental contests (896 problems — 36% of the
rated set, contributing links but never checked), 18/36 Asia East, 7/22 Asia
Pacific, 7/11 Northern Eurasia, 4/29 North America, 3/3 Latin America. All 185
CF anchor problems come from just three regions (Asia Pacific 93, Northern
Eurasia 50, Europe 42), so the affine leg is fit on three regions and
extrapolated onto the other five. The exhaustive problemset sweep already
established that no further rated mirrors exist for the current contest set, so
anchor growth requires new contests or a new *kind* of anchor.

The other collected-but-unused source is the ability side:
`data/cphof_cf_participants.json` carries 2,119 roster-corroborated standing
appearances across 89 contests, **1,677 (79%) of them in Asia East Continent** —
precisely the region with no CF problem-level anchor. A time-accurate CF prior
on `theta` pins the scale through the *ability* axis and propagates to `b` in
every contest a matched team played. See `cf_participant_ratings.md` for the
identity layer and its open requirement (exact per-contest timestamps).

## Suggested structural shift

The theme is one the repo already established with the gym shape — **use the
trustworthy half of each signal and discard the noisy half** — applied to the
axis the current pipeline leaves unmodelled. Every referee here is trustworthy
about *ordering within a contest* and suspect about *level across contests*,
while the fit is the reverse. Ordered by dependency, not by expected metric gain
(Findings 1 and 4 say the metric is near its floor inside the anchored regions):

1. **Sparse data layer.** Replace the dense `rows x n_problems` blocks in
   `arch_a.load` with per-contest blocks or COO. Prerequisite for everything
   below; also removes a ~6 GB working set from every current run.
2. **One fit, one scale.** Fold UCup into the main fit as ordinary data and
   retire the Phase-1 prior-mean anchor (measured cost +1.1 CF points; gain: 684
   more problems on the shipped scale and no second scale to reconcile). This
   deletes the class of bug in Finding 2 instead of patching it. If the joint
   fit is deferred, the interim fix is to push `b_u` through the measured
   crosswalk before calibrating `export_ucup_only` and the virtual calc.
3. **A cross-contest LLM pairwise instrument.** Re-point `llm_survival.py` from
   within-contest to cross-contest pairs, first on the 15 CF-mirrored contests
   alone so it can be scored against the known per-contest offsets of Finding 4,
   then — only if it passes — across all statement-bearing contests. This is the
   only path to a referee with full regional coverage that is standings-free
   *and* free of the absolute-scale drift that made the two existing referees
   disagree in Finding 5.
4. **Hierarchical calibration instead of a single global affine.** Model
   `cf_p ~ A*f(b_p) + B + u_contest + v_region` with partially pooled `u`, `v`,
   with the cross-contest LLM BT scores (step 3) as the observation that
   identifies `u` and `v` outside the 15 anchored contests. Anchored contests
   estimate their own offset; unanchored ones shrink to their region, and
   unanchored regions to the global mean. Inside the anchored regions the
   ceiling is modest (240 → 219 in-sample); the real payoff is that the
   per-region level becomes an explicit estimated parameter with an honest
   uncertainty instead of an assumed zero.
5. **Ability-side CF anchoring.** Consume the CPHoF layer as a time-accurate
   Gaussian prior on `theta` for roster-complete rows — the only anchor in the
   repo that reaches Asia East Continent numerically, and a third independent
   opinion on the Finding 5 region question.

**Explicitly not recommended:** per-region gym offsets. Per-region gym *shapes*
were already tried and overfit (298 vs 266), and Finding 5 now shows that even
one offset parameter per region, learned from the gym alone, would encode a
level difference the LLM referee reverses.
