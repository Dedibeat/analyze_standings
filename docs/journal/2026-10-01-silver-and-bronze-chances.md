# Silver and bronze chances (2026-10-01)

**Request.** Forecast regionals by silver and bronze chance as well as gold.

**Labels.** Every 2022–2025 board gives medals to 10% / 20% / 30% of official
solvers (within rounding; the 2022 boards use the 10/20/30 rule), so gold,
silver-or-better and any medal are the top 10% / 30% / 60%.

**Model** (`arch_b.online_medals`):
- Each level k reuses the online-gold model:
  `logit P(medal ≥ k) = c_k + b_k x + d_k line_k`.
- `line_k` is the rule-admitted team at 10% / 30% / 60% of capacity, after
  the quota entrants' share at their own measured rate (ρ = 0.394 / 0.467 /
  0.651).
- Class probabilities are differences of the cumulative ones, made monotone.
  No crossings occurred in either test season.
- Hong Kong uses a Hong Kong-only `c_k + b_k x` per level on its 2024–2025
  linked teams.
- `online_gold` gained three default-preserving parameters (`rules_line(…,
  fraction)`, `quota_split(…, won)`, `medal` on linked rows). Its full output
  is unchanged, and the gold level reproduces it exactly: backtest Δ −0.0003 /
  −0.0010; 2026 P(gold) at online #100 55.2% for Xi'an.

**Backtest** (train earlier seasons; Δ log loss vs online-only, contest-bootstrap
95% CI):

| level | 2024 rules line | 2024 oracle | 2025 rules line | 2025 oracle |
|---|---|---|---|---|
| gold | −0.0003 [−0.0007, +0.0001] | −0.0013 | −0.0010 [−0.0029, +0.0003] | −0.0040 |
| silver or better | +0.0043 [−0.0006, +0.0113] | −0.0035 | −0.0051 [−0.0113, +0.0007] | −0.0110 |
| any medal | +0.0004 [−0.0046, +0.0069] | −0.0100 | −0.0018 [−0.0043, +0.0001] | −0.0048 |

Four-class log loss: 2024 online-only 0.8941 vs rules line 0.9002; 2025 0.8776
vs 0.8713. For silver and bronze, the rules lines are a wash. Mainland site
differences at those levels are small in the forecast anyway and not
validated. The oracle line (the actual attending field) helps at every level,
so registration lists would matter more for silver/bronze than the slot rules
do.

**Hong Kong backtest** (train the other year):
- Hong Kong-only beats the mainland online-only model on 2024 at every level
  (any medal 0.525 vs 0.609) and loses slightly on 2025 at silver+ and medal
  (0.326 vs 0.315, 0.496 vs 0.488). Summed over both years it is better.
- Expected vs actual counts: silver+ 39.1 / 37 and 31.0 / 32; any medal
  71.3 / 80 and 67.6 / 61. The medal share of linked teams varies by year
  (68% vs 63%).

**2026 forecast** (`output/online_medals.md`; conditional on attending;
gold / silver / bronze):

| online rank | mainland sites (range) | Hong Kong |
|---|---|---|
| #100 | 54–57% / 39–41% / 3–4% | 34% / 56% / 8% |
| #200 | 18–20% / 58–62% / 16–20% | 8% / 63% / 23% |
| #300 | 8–9% / 46–53% / 32–38% (any 91–93%) | 3% / 50% / 36% (89%) |
| #500 | 2–3% / 21–27% / 48–52% (any 73–78%) | 1% / 29% / 48% (78%) |

- **Hong Kong is the hardest gold and the easiest medal for weaker teams.**
  Its field has a weak tail: half of the linked teams are below online #750,
  and 60% of the field gets a medal. A team at online #1171 has 45% for any
  medal at Hong Kong vs 22–26% on the mainland.
- **NUM-R^3** (online #544/#349): any medal 80–84% everywhere. Silver chance:
  Hong Kong 34%, Shenyang 34%, Wuhan 30%, Chengdu/Nanjing 27%. Gold:
  1.3% at Hong Kong, 3.3–3.7% on the mainland. NUM-MNM: any medal 47–54% on
  the mainland, 64% at Hong Kong.

Run: `python3 -m arch_b.online_medals [--school NAME]` (~30 s; on Windows set
`PYTHONUTF8=1`). Tests: `tests/test_online_medals.py`.
