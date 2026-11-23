# Hong Kong gold: does practice predict onsite? (2026-11-23)

**Request.** A debate with Codex about the Hong Kong gold claim. Codex asked:
- which performance the forecast assumes;
- how Chengdu, Changchun and Wuhan are weighted;
- whether "6.3 expected golds" and the online-only uncertainty were
  over-read;
- for the decisive test: would the method, using only results from before
  Shenyang, have predicted Shenyang?

Codex's own journal files (`2026-11-23-hk-gold-argument.md`,
`2026-11-23-hk-opponent-replay.md`) are on the user's PC and not pushed, so
its exact figures were not reproduced here.

**Merge.** The branch was merged with `origin/master` first, which brought
three changes:
- the `docs/journal` layout (this branch's `details.md` entries now live in
  `2026-11-16-hong-kong-field-by-shenyang-rank.md`);
- the 11-22 export;
- `hier_time` performances in `export_virtual_calc.performance_fit`.

`hk_shenyang_rank` now takes `--file` and defaults to the 11-22 export.
`build()` and `hk_model()` were split out of `main()`; the output is
byte-identical to before the split. On hier_time and the 11-22 list, NUM-R^3
is 25th of 105 by mean and 19th on Shenyang alone. Renmin's All ways Onward
(Shenyang #13) is 4th.

**Method** (`scripts/hk_form_backtest.py`, new):
- Every 2026 NUM-R^3 result goes on the `hk_shenyang_rank` scale:
  - official online rounds: the team's own fitted row;
  - 15 QOJ virtuals: 51st regionals at official rank k, the older boards by
    scoreline insertion;
  - Changchun: through the CCPC map;
  - Wuhan is counted as #53 (5 / 631, B excluded because it was finished with
    help).
- The spread of single results within a team, pooled over 174 degrees of
  freedom, is **182**.

**Backtest: predicting Shenyang from results before 11-15** (actual: #87,
perf 2327):

| rule | predicted Shenyang rank | error |
|---|---|---|
| official online rounds | 113 | −90 |
| all virtuals | 52 | +155 |
| all virtuals −100 | 73 | +55 |
| recency-weighted virtuals (half-life 14 d) | 54 | +150 |
| last 3 virtuals | 49 | +176 |
| Chengdu repeated | 35 | +264 |

- Virtuals overstated onsite by **150** (±182, from a single result). The
  −100 discount was too small.
- "Repeat Chengdu" was the worst rule.
- The official online rounds understated the team by 90; online round 2
  alone (2319) matched Shenyang (2327) almost exactly.

**After Shenyang.** The Wuhan virtual (2478) equals the earlier weighted
virtual level (2477), so form has not changed since Shenyang. Every estimate
calibrated on Shenyang lands at about 2327.

**Hong Kong** (Monte Carlo: gold = top round(10%) of the attending field;
team strengths drawn within the 182 spread; teams with no 2026 result drawn
from the linked field):

| estimate | HK position | model gold | MC gold (Reviewed / all / online-only ×2) |
|---|---|---|---|
| Shenyang level (all calibrated estimates) | 19 | 19% | 10% / 13% / 9% |
| virtuals −100 | 16 | 25% | 15% / 18% / 14% |
| mean of the 15 QOJ virtuals | 13 | 42% | 29% / 34% / 27% |
| Chengdu repeated | 8 | 62% | 47% / 53% / 45% |

- Doubling the uncertainty of the 30 online-only teams lowers NUM-R^3's
  chance by about 1 point. More spread among the teams ahead helps one of
  them as much as it hurts.
- The earlier "30–60% at virtual level" was optimistic. The defensible
  planning figure is **~10–20% gold, finishing ~16–20th**.

**Concessions recorded:**
- The 0.99 correlation between online rank and online performance is a unit
  conversion, not evidence that practice transfers to onsite. The backtest
  is the evidence, and it says virtuals overstate onsite.
- The model's expected-gold sums are not tiers. The Monte Carlo replaces them
  with ranks.

**Limits:**
- There is one onsite result, so the gap is ±182.
- Strength is a plain mean with a flat prior.
- 21 registrants have no 2026 result.
- The Changchun virtual (two members, 3:15) is not adjusted.

Reproduce: `python3 scripts/hk_form_backtest.py` (~1.5 min) →
`output/hk_form_backtest.md`; `python3 scripts/hk_shenyang_rank.py --virtual
Chengdu:35 --virtual Wuhan:53 --virtual 'CCPC Changchun:29'`.
