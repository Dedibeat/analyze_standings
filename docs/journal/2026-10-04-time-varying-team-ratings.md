# Time-varying team ratings (2026-10-04, research)

**Request.** Improve the prediction of team performance and test bold ideas.
The user's idea: a Codeforces-style rating, updated after every contest, which
can learn that teams improve. Their suspicion: the static fit inflates team
ratings in older contests, because teams improve and show it later. The plan
was to measure where a time-based rating disagrees with the current model and
use that to predict better. Module: `arch_b.dynamic_rating` (research only; no
shipped rating, calibration or export changed). Output:
`output/dynamic_rating.{json,md}`.

**Dates.** No contest has a date field, and QOJ's contest list is behind a
Cloudflare challenge (HTTP 403). `contest_day` uses a proxy:
- XCPCIO start dates anchor a QOJ-id → date interpolation (right for contests
  run live on QOJ);
- boards uploaded long after the event (most non-Asia-East regionals, the
  2020–21 supplement, championships) fall back to their season's typical day;
- Petrozavodsk camps go by their Winter/Summer name, and EC online rounds by
  September.

Unofficial mirror rows are dated with their contest. Ordering errors are
weeks, not seasons.

**Models** (all on the shipped binary Rasch likelihood; joint inputs, 262
contests, 35,862 teams, 78,201 rows):
- `cf_filter` (`filter_ratings`): the requested CF-style system. Contests are
  processed in date order. Each is one Rasch MAP (`model.fit`) whose team
  priors are the current ratings, `N(mu, var + q²·Δt)`. A Kalman/Laplace
  update follows.
- `dynamic` (`smooth_fit`): one joint MAP with an ability per team and
  appearance day, tied by a Gaussian random walk `N(drift·Δt, q²·Δt)`
  (TrueSkill Through Time style). The θ block is solved exactly as one
  tridiagonal system per team (`_chain_solve`, ~2.5 s per fit). `q = 0`
  reproduces `model.fit` to 1e-6 (tested).
- **Prior choice (found on the way).** The first version put the shipped
  `N(2000, 400²)` prior on a team's first node only. That shrinks early
  abilities more than late ones and invented trends: strong teams' within-team
  slope came out +31 points/year against +7 in the artifact-free static
  residuals, and weak teams' +10 against +41. The prior is now spread over a
  team's K nodes as `N(2000, K·400²)` each. That is exactly the shipped prior
  on the team mean, with no time asymmetry.

**1. Are older appearances over-rated? Yes, modestly.**

Static-fit performance minus rating, by position in the team's observed span
(teams with ≥ 4 rows over ≥ 180 days):

| span | 0–0.1 | 0.1–0.3 | 0.3–0.5 | 0.5–0.7 | 0.7–0.9 | 0.9–1 |
|---|---|---|---|---|---|---|
| residual | −26.5 | −22.9 | +9.4 | +20.5 | +27.6 | +14.8 |

- **Within-team trend:** +14.9 points/year. By static-ability tercile it is
  +41.2 (weak), +24.7 and +7.4 (strong): weak teams improve most.
- **Random-walk fit vs static.** It shifts problems and the abilities of teams
  with more than one row by contest year. At q = 100: 2022 −32, 2023 −11,
  2024 −2, 2025 +6, 2026 +8 (problems) and +22 (abilities). At q = 50 the
  shifts are a third to a half as large.
- **The edge effect is the user's mechanism.** Early in the data window, a
  recurring team's later (better) form lifts its single ability, so the
  problems it failed look harder. At the end of the window, the reverse.
- **CF anchors (raw-ridge LOCO, binary).** The static residuals trend by year:
  2022 +135 (12 problems, one contest), 2023 +28, 2024 −9, 2025 −17, 2026 −62
  (13 problems, one contest). The direction matches, but the end points are
  single contests. The random-walk fit moves 2022 to +120 / +107, yet the
  overall LOCO does not improve: 246.78 → 247.47 (q = 50, +0.70 [−0.53,
  +1.81]) and 249.15 (q = 100, +2.37 [−0.38, +5.17]). In exploration, q = 150
  / 200 were significantly worse (+4.6 / +7.1).
- **CF RMSE of the random-walk fits** (`cf_rmse`; survival and binary refit
  with the same q). These are the project's own scores:
  - `arch_b.metric`: raw affine LOCO, the north-star gym-shaped LOCO and the
    guards. `metric.main` now delegates to a new `metric.score(ds, b)`, and
    its output is unchanged (244.6 / 246.7, same guards).
  - the shipped DE calibration's nested LOCO, ridge and clipped features
    (`de_release_audit.loco`), with a paired contest bootstrap against q = 0.

  q = 0 reproduces the shipped numbers.

  | q | north-star (survival, gym-shaped) | survival raw | binary raw | DE ridge | DE clip (shipped) | Δ DE clip vs q = 0 |
  |---|---|---|---|---|---|---|
  | 0 | 244.6 | 246.7 | 246.8 | 225.9 | 225.6 | |
  | 25 | 245.6 | 246.6 | 247.0 | 225.1 | 225.3 | −0.27 [−1.71, +0.74] |
  | 50 | 245.0 | 247.1 | 247.5 | 225.3 | 224.6 | −1.00 [−3.89, +1.39] |
  | 100 | 245.1 | 248.2 | 249.2 | 225.7 | 224.9 | −0.67 [−4.90, +3.24] |

  - **All moves are within about 1 point.** That is under the 5-point keep
    threshold and far inside the ±20 noise floor of `program.md`.
  - **The north-star gets slightly worse** (+0.4 to +1.0).
  - **DE gets slightly better, but not significantly.**
  - **Guards are unchanged:** gym EC 0.977–0.978, Kattis 0.795–0.797, AOJ
    0.563, solve-count sanity ≥ 0.996.
- **Conclusion for problem ratings:** this is a real bias of the static fit,
  but letting abilities move does not calibrate problems measurably better or
  worse. Team-season offsets in the DE audit were similar (+3.7 there).
  Nothing changed in the shipped fit.

**2. Forecasts.** At each month start from 2023-01, every model is refit on
the contests that started before the month. It then forecasts every row of
that month whose team appeared earlier.
- **Periods:** 2023 tunes; 2024-01..2026-10 is the test period (26,469 rows,
  151 contests).
- **Scores:**
  - pairwise order accuracy within a contest (6.1 M pairs);
  - pairwise log loss at scale 1.25·S (best for every model);
  - held-out solve log loss. Its problem difficulties come from the full-data
    static fit, the same ruler for every model; one level offset per contest
    is fitted on a random half of the rows and the other half is scored.
- **Intervals:** paired contest bootstrap.
- **Rejected metric:** fitting the target contest's difficulties from the
  forecasts themselves was dominated by easy problems clipped at 800, so it
  was dropped.

Test period, rows with history (Δ vs static, 95% CI):

| model | accuracy | Δ accuracy | Δ solve log loss |
|---|---|---|---|
| static (shipped form) | 0.7931 | | (0.22090) |
| cf_filter q = 0 / 100 | 0.7886 / 0.7895 | −0.0046 / −0.0037 [−0.0055, −0.0020] | +0.0029 / +0.0015 |
| dynamic q = 25 / 50 / 100 | 0.7933 / 0.7936 / 0.7935 | +0.0005 [+0.0003, +0.0007] (q = 50) | −0.0007 [−0.0009, −0.0005] (q = 50) |
| dynamic q = 50, drift +25/yr | 0.7941 | +0.0010 [+0.0007, +0.0013] | −0.0006 |
| static + online offset 100 | 0.7949 | +0.0018 [+0.0007, +0.0030] | −0.0003 |
| dynamic q = 50 + online offset 100 | 0.7955 | +0.0023 [+0.0013, +0.0035] | −0.0010 [−0.0015, −0.0006] |

- **The CF-style filter loses** in both periods (2023: −0.0092). Its gap at
  q = 0 is the cost of updating forward only: each contest's difficulties
  and every team's posterior are frozen when the contest is processed, while
  the joint fit re-estimates them with everything seen since. Letting ratings
  move (q = 100) recovers only a fifth of that. **"Update after every
  contest" should therefore mean refitting the dynamic joint model after
  every contest (a few seconds), not an incremental Elo step.**
- **Dynamics help only once histories are long.** In 2023 no q beats static
  (q = 50: −0.0003, n.s.; q = 100: −0.0015). In the test period the gain
  concentrates in teams with ≥ 10 earlier rows: 0.8433 → 0.8446, against
  0.7680 → 0.7682 for teams with one. A drift of +25/year adds a little
  (test +0.0010; 2023 +0.0003, n.s.). A season-boundary jump in the walk's
  variance (exploration, SD 50/100 at Aug 1) gave nothing.
- **Online-round offset** (bold idea 2). Ratings that rest on EC online rounds
  overstate onsite strength. The DE audit measured this as +102 [+88, +117]
  binary points on held-out verified teams. Forecasting onsite contests with
  `rating − 100 × (share of the team's earlier rows from online rounds)`
  helps in both periods (2023 +0.0059, test +0.0018). That is more than three
  times the gain from dynamics. When forecasting online contests, the same
  deflation hurts (exploration): online form persists. So this is a
  team-specific context ability, not one constant.

**3. New rosters: carry members' ratings (bold idea 3, the largest gain).**
- **The gap.** Rosters merge into one identity only when two members recur.
  In the forecast months, 7,705 rows are new identities with at least one
  member seen earlier: 5,202 with one known member, 1,734 with two (from
  different teams) and 769 with three. The shipped model gives all of them
  the flat 2000 prior.
- **The prior.** For each known member, take the rating at the month start of
  their latest earlier team. The new roster's forecast is
  `2000 + a_k + w_k·(member mean − 2000)` by known count k, fitted on 2023
  rows (target: row performance on the ruler).
- **Coefficients:** a = +42 / +97 / +183, w = 0.52 / 0.64 / 0.87. New rosters
  beat their members' old ratings, again a sign of improvement.

Test period, history rows plus new rosters with known members (32,684 rows):

| model | accuracy | Δ accuracy | Δ solve log loss |
|---|---|---|---|
| static, new rosters at 2000 | 0.6907 | | (0.24317) |
| static + member prior | 0.7335 | +0.0428 [+0.0268, +0.0521] | −0.0132 [−0.0160, −0.0100] |
| dynamic q = 50 + online 100 + member prior | 0.7345 | +0.0438 [+0.0284, +0.0528] | −0.0139 [−0.0166, −0.0108] |

The 2023 tuning rows agree (+0.0219 / +0.0255).

**Verdict.**
- **The hypothesis holds:** a single ability per team is too high early and
  too low late (≈15 points/year, ≈40 for weak teams).
- **Fixing it with time dynamics** gives a small, significant forecast gain
  (+0.0005 to +0.0010 pair accuracy), mostly for long-history teams.
- **The literal CF-style incremental update is worse than the static fit.**
- **For problem ratings** the dynamic fit does not beat the static fit on CF
  anchors, so the shipped fit is unchanged.
- **The bigger levers for predicting team performance:**
  - who the team's members are (member prior: +0.043 accuracy where it
    applies);
  - where the team's evidence came from (online offset: +0.002).

**Next steps (not done).**
- **Person-level dynamic ratings.** Give each member a random walk, with team
  ability = mean of members plus a team effect. This is the CF-like system
  at the level CF actually rates. It joins the two largest gains (member
  carry-over and time) and keeps the joint refit.
- **A two-context ability in the fit.** Onsite and online, with a
  team-specific online offset, instead of the post-hoc share correction.
- **Medal forecasts.** Feed the forecast rating (dynamic + online + members)
  into `online_gold` / `online_medals` as a feature beside online rank, and
  check it on the 2024/2025 backtests.
- **Real dates:** contest start times from QOJ (needs a logged-in session) or
  ICPC sources would replace the proxy.

Run (~7 min): `python3 -m arch_b.dynamic_rating` (on Windows set
`PYTHONUTF8=1`). Tests: `tests/test_dynamic_rating.py`. This environment
needed `pip install numpy` first.
