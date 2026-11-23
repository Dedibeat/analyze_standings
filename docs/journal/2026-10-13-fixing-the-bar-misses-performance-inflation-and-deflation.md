# Fixing the bar misses; performance inflation and deflation (2026-10-13)

**Request.** How do we fix the bar misses of the previous entry (Shanghai
2025 and Nanjing 2024 too low, Xi'an 2025 and Kunming 2024 too high) and the
rating inflation and deflation?

**1. The bar misses: read gold difficulty on the gold line, not the bar.**
- **Why the bar misses.** The bar is a problem threshold: the difficulty the
  ±7-rank cohort around the gold cutoff solves at 50%, interpolated between
  the two problems that bracket that rate. It reflects how the set's
  difficulties are spaced as much as how strong the field is.
- **Reliability.** This is each measure's correlation with the gold difficulty
  that the two rating-free referees share, from the triad
  r(a, B)·r(a, C)/r(B, C). Over 16 mainland regionals, within season:

  | measure | reliability |
  |---|---|
  | bar | 0.61 |
  | gold-line performance (last gold team) | 0.85 |
  | ±7-rank cohort performance | 0.86 |

  - The cohort performance correlates 0.99 with the gold line, so it adds
    nothing.
  - Cohort minus bar, 90% bootstrap: +0.04 … +0.51.
- **Not the interpolation.** The gap between the two bracketing problems
  (median 230 CF) does not predict the size of the miss (Spearman +0.06).
  Xi'an 2025, one of the four misses, has a 2-CF gap.
- **Fix (shipped).** `online_gold.contest_difficulty` now reads fit − online
  on the gold line: `cutoff_teams.gold.performance_cf` in `medal_badges.json`,
  via `cf_gold_bars(line=True)`.
  - The bar stays as a column. It still sets the badges, where a problem
    threshold is what is wanted.
  - New keys: `cf_gold_line`, `cf_line_implied_by_online` (replaces
    `cf_bar_implied_by_online`) and `spearman_rank_vs_line`.
- **Effect** (17 regionals, 2023–2025):
  - Spearman with the online rank for even odds: line −0.515, bar −0.373
    (pooled). Within season: +0.64 against +0.52.
  - RMS disagreement with online: 67 CF against 81.
  - The four misses, fit − online (old bar from the 2026-09-28 report → line):

    | regional | bar | line |
    |---|---|---|
    | Shanghai 2025 | −118 | +24 |
    | Nanjing 2024 | −114 | −64 |
    | Kunming 2024 | +156 | +81 |
    | Xi'an 2025 | +66 | +4 |

  - Shenyang 2024, where CCPC sided with the fit, is +59 on the line (bar
    +95).
  - **The largest gaps now:** Xi'an 2023 −166 (no bar in the old report),
    Wuhan 2025 +108 and Hefei 2023 −91.
  - **Updated by the second entry below.** The cutoff performances are now
    ranked within each event's own field. After that change, Shanghai 2025 is
    +33, Nanjing 2024 +9, Kunming 2024 +33, Xi'an 2025 −53 and Wuhan 2025 +9.
- **Other diffs in the regenerated `online_gold` report.** These are inputs
  that changed after its 2026-09-28 run. `medal_badges.json` was updated on
  2026-10-04/05, which moves the `cf_bar_history` backtest row (Δ within
  ±0.0005) and the `medal_predict` column of the forecast table. The 2026
  gold probabilities are unchanged.
- **`medal_predict` is not changed.** City history has no skill for any of
  the measures. In a rolling-origin test (pool a city's earlier seasons,
  predict the next), 22–45% of within-season pairs come out in the right
  order, against 50% by chance. Changing its input would not make its city
  ranking skilful. `online_gold` remains the 2026 forecast.

**2. Performance inflation and deflation: what was found.**
- **Superseded in part** by the second entry below, which finds the causes:
  - (a) comes from merged QOJ boards and is fixed there;
  - (b) comes from the shipped DE problem ratings;
  - (c) is mostly the same merging plus a banding artifact.

  The "partial correction" and the "cannot be told" points below are
  replaced by that entry.
- **The measure.** Each row's rank-based performance minus its
  problem-implied rating: the rating at which the CF formula, applied to the
  shipped DE ratings of the set's problems, gives the row's solve count.
- **(a) Big fields inflate strong teams.**
  - Same team at two regionals in a season, performance minus problem-implied,
    at a 440-team against a 300-team field: −2 below 2500, **+33** at
    2500–2800 and **+62** above 2800.
  - The gold line minus the rating-free consensus correlates with log field
    size: r = +0.55 over 17 regionals.
- **(b) Offsets by contest type** (median performance minus problem-implied):

  | contest type | median | below 2200 | above 2800 |
  |---|---|---|---|
  | regionals | +12 | −33 | +70 |
  | CCPC mirrors | +9 | −80 | +117 |
  | EC-Final | **−73** | −167 | +92 |
  | EC online rounds | **+89** | +95 | +33 |

- **(c) A stretch within each contest.** At regionals the difference is −33
  below 2200 and +70 to +74 above 2600.
- **Causes tested and ruled out:**
  1. **Weakly identified rivals.** With rivals restricted to teams with ≥ 3
     or ≥ 5 contests, (a) stays: +35 / +64 and +38 / +80.
  2. **The team-vs-team curve.** Eq. perf uses the per-problem logistic (scale
     400) for "this rival finishes above me".
     - In sample, the rank outcomes fit a steeper curve: scale 345 for teams
       with ≥ 5 contests.
     - Out of sample it is flatter. With abilities fitted without a
       pseudo-random 136 of the 262 contests (`model.fit(obs=…)`), the
       held-out rank outcomes give 480 overall, 450 for teams with ≥ 3
       training contests and 435 for ≥ 5. So 400 sits between, and
       nothing supports changing it.
     - It would not fix (a) or (b) anyway. At any scale from 250 to 400:
       - (a) stays between +62 and +78 above 2800;
       - EC-Final stays between −71 and −73;
       - online rounds stay between +71 and +89.
     - Only (c) shrinks: the 2600–2800 band goes from +74 to +48 at scale
       345.
- **A partial correction, not shipped.** Take the same-team field-size slope,
  86 CF per unit of log field. It comes from team pairs, not from the gold
  lines. Applied to the gold lines, it improves their agreement with both
  referees (16 regionals): r with online 0.80 → 0.84, r with CCPC
  0.81 → 0.84, reliability 0.85 → 0.90.
  - **The correction is small.** The season-centred log-field SD is 0.14,
    so lines typically move ~±12 CF. Wuhan 2025 and Kunming 2024, the
    largest fields of their seasons, move by only about −17 and −22 of their
    +108 / +81.
  - **Not shipped:** it changes no reading, and its mechanism is unknown.
- **Which instrument is off at EC-Final and in the online rounds cannot be
  told.**
  - Performance and the problem-implied rating come from the same fit.
  - No rating-free referee exists for those contests.
  - **Working rule:** compare performances within one contest type. Do not
    read an EC-Final or online-round performance against a regional one
    directly: they sit −73 and +89 from the problem-implied scale.

Scratch scripts are not kept. Part 1 is rebuilt from `medal_badges.json`,
`online_gold.contest_difficulty` and `contest_quality.json`. Part 2 is
rebuilt from `export_virtual_calc.performance_fit`,
`contest_quality.performance` / `problem_difficulty` and `joint.estimate_joint`
with a `fit_fn` that drops the held-out contests' cells. Tests:
`python -m unittest tests.test_online_gold tests.test_hk_gold` (10 pass).
