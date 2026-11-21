# Is Dedibeat improving, net of Codeforces deflation? (2026-11-21)

**Request.** "How do I know if I am improving at CF when people are cheating often?"
Then: do it for the handle Dedibeat.

**What was available.** The cleanest yardsticks, a field or problem ratings set before
AI, have almost no recent data for this handle:
- Virtuals since 2025-01: 2 of about 45 are on pre-2025 rounds (1876 in 2025-02, 2029 in
  2025-08). The rest are on 2025–2026 rounds, whose field has the same contamination.
- Practice on problems from pre-2025 rounds: 3 problems since 2025Q3 (from
  `data/team_r3/cf/status_Dedibeat.json`, fetched 2026-11-04).

So the answer had to come from rated rounds: compare the change with players who stood at
the same level at the same time, and correct with how such players moved before AI.

**Done.** New `scripts/cf_self_check.py <handle>` reads the `data/cf_ai/` cache of
`cf_ai_deflation.py`. It has no fetch step.
- Level per half-year:
  - rating level: the mean internal rating after the half-year's rated contests (≥3);
  - solve level: the 50% point of Codeforces' Elo curve fitted on every rated problem
    of the half-year's rated rounds.
- Base: 2024H2, the last half-year before the onset.
- Peers: ≥10 earlier rated contests and a base rating level within ±50.
  - The AI-era peers start in 2024H2.
  - The pre-AI drift uses bases 2021H1, 2021H2 and 2022H1, followed for the same
    number of half-years, all ending by 2024H1. These bases follow the report's
    baselines and were set before the run.
- A second peer set, "young", keeps only new accounts first rated within 12 months
  before the base. Dedibeat was first rated 2024-01-06.
- Derived quantities:
  - vs peers = own change − AI-era peer mean;
  - net of deflation = vs peers + pre-AI drift.

**Results** (default run; peers n at base: 1,185 all, 210 young).

Own levels:

| half-year | contests | rating level | solve level |
|---|---|---|---|
| 2024H2 (base) | 28 | 1776 | 1860 |
| 2025H1 | 24 | 1795 | 1820 |
| 2025H2 | 16 | 1896 | 1940 |
| 2026H1 | 15 | 1839 | 1830 |
| 2026H2 (to 11-18) | 8 | 1782 | 1980 (28 rated problems only) |

Rating level against all established peers:

| half-year | own change | peers n | peer mean | own percentile | pre-AI drift | deflation | net of deflation |
|---|---|---|---|---|---|---|---|
| 2025H1 | +20 | 572 | +40 | 43 | +29 | +10 | +10 |
| 2025H2 | +121 | 469 | +38 | 73 | +53 | −16 | +136 |
| 2026H1 | +63 | 245 | +23 | 58 | +83 | −60 | +124 |
| 2026H2 | +6 | 165 | −24 | 58 | +104 | −128 | +134 |

- **Young peers:**
  - percentile 25, 55, 24, 22;
  - net of deflation 0, +144, +79, +97;
  - n is only 45 and 27 in 2026H1–H2.
  - Accounts that reached 1776 within a year kept rising: +87 to +137 raw. They also
    did so before AI: pre-AI drift +67 to +196.
- **Solve level, all peers:**
  - net of deflation −14, +108, +26, +269 (the last rests on 28 problems);
  - percentile 37, 58, 44, 75.
  - It matches the team script's `theta_by_half_year` within 20–70 points. That script
    includes virtuals and fits its own slope.
- **Robustness** (two runs after the default, recorded rather than chosen):
  - ≥6 contests per half-year: rating net +11, +133, +121, +183; percentile 40, 70,
    50, 62.
  - ±100 tolerance: net +12, +129, +107, +114; percentile 43, 70, 58, 57.
- **Peer deflation:** −60 at 2026H1. That is in line with the report's 22-month figure
  for 1600–1899 (−63). At 2026H2 it is −108 to −177, larger than the report's −63 to
  −88 for that band. The method differs (half-year means, an activity requirement in
  each half-year), and 2026H2 is partial.

**Reading.**
- The raw level is flat: +6 over two years.
- Net of deflation, it rose about +110 to +135 by 2026H1–H2 in every variant, which is
  roughly 1900 on a pre-AI scale.
- Against players at the same level in the same rounds, Dedibeat sits near the median
  (percentile 50–62 now, 70–73 in 2025H2).
- Against other year-old accounts it is below the median (about 22–25), on small samples.
- The 2106 peak (2025-10-19) followed three rounds worth +240. The 2025H2 level was
  1896. Most of the fall since then is that peak returning to the level.

**Not changed.** No shipped artifact, model or rule. `.venv` was created in this
container on Python 3.13; `requirements.txt` pins 3.12, and the install succeeded.

**Reproduce.**

    ./.venv/bin/python scripts/cf_self_check.py Dedibeat   # ~75 s; output/cf_self_check_Dedibeat.json
