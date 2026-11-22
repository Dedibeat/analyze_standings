# Past-season EC-Final chance from virtual online results (2026-10-08)

**Request.** For the 2024 and 2025 regionals, what would our chance of an
EC-Final seat have been at each site, based on that season's online
performance? "Our" online performance is the account Dedi's virtual runs of
the EC online rounds, done in 2026 and saved in `../my-react-app`. They were
read through the app's API (`GET /api/participations`), read-only.

**Online ranks.** `scripts/ecfinal_retro.py` ranks each typed-in result
(solved / penalty minutes) in the official online ranking of that round:
rank = 1 + teams with more solved, or equal solved and lower penalty. The
method reproduces NUM-R^3's real 2026 ranks exactly (6/877 → #544,
4/482 → #349).

| season | Online I | Online II | geometric mean |
|---|---|---|---|
| 2024 | 6/714 → #96 of 2,205 | 6/402 → #509 of 2,340 | #221 |
| 2025 | 7/626 → #146 of 2,159 | 5/890 → #345 of 1,745 | #224 |

**Method.**
- **Qualifying rank K per site.** From replaying that season's round-robin
  (`ecfinal_cutoff.admits_by_depth`): the deepest rank the walk examined at
  each site. 2025 uses 239 mainland seats (checked against the 公示). 2024
  uses 240, an assumption: its Hong Kong/Macau seats were not checked.
- **Model.** The online-only model of `ecfinal_chance`, as asked; member
  history is left out.
- **"With the actual field".** Adds a per-contest intercept fitted at K with
  the slopes fixed. This is hindsight about who came; before the season the
  sites were not distinguishable (2026-10-08 section above).
- **Hong Kong.** The Hong Kong model at the depth of its 10 places under the
  2026 rule (rank 37 in 2024, 32 in 2025). Under the real 2025 rule Hong Kong
  gave only one seat, to its rank-7 team. Hong Kong's real 2024 seats were not
  checked.

| 2025 site | K | before the season (10–90%) | with the site's actual field |
|---|---|---|---|
| Shenyang | 91 | 58.5% (55.0–62.1%) | 65.8% |
| Xi'an | 90 | 57.8% (54.3–61.4%) | 64.4% |
| Chengdu | 90 | 57.8% | 62.2% |
| Nanjing | 90 | 57.8% | 60.6% |
| Shanghai | 90 | 57.8% | 60.5% |
| Wuhan | 91 | 58.5% | 42.5% |
| Hong Kong (2026 rule) | 32 | 46.3% | — |

| 2024 site | K | before the season (10–90%) | with the site's actual field |
|---|---|---|---|
| Shanghai | 86 | 55.7% (52.2–59.3%) | 64.8% |
| Chengdu | 85 | 55.0% (51.4–58.5%) | 64.7% |
| Nanjing | 86 | 55.7% | 56.1% |
| Shenyang | 85 | 55.0% | 56.1% |
| Hangzhou | 86 | 55.7% | 55.8% |
| Kunming | 86 | 55.7% | 36.4% |
| Hong Kong (2026 rule) | 37 | 59.5% | — |

**Reading it.**
- **The virtual runs are much stronger than the official 2026 rounds.** In
  online-rank terms they are about twice as strong: #222 against #436. At the
  same cut ranks, #436 gives 18–21% (K = 85–91) where #222 gives 55–59%. So
  these figures hold only if the virtual form carries over to official
  contests. This season's official rounds suggest it does not fully.
- **The 2024–2025 cuts were deeper than 2026's.** Six sites shared 240 seats
  (K = 85–91); in 2026 seven sites share 230 (K ≈ 75). At K = 75 the same #222
  gives 46.4%, and #436 gives 13.8%.
- **Site choice with hindsight.** Wuhan 2025 and Kunming 2024 were clearly
  the worst picks: their fields were the strongest above the cut. Shenyang
  2025 and Shanghai/Chengdu 2024 were the best.
- **What actually happened.** The teams in Dedi's official records finished
  Shanghai 2025 #209 (N^3), Kunming 2024 #311 (NUM_DES) and Hangzhou 2023
  #357 (NUM-DSE), all far below K. At Hong Kong 2025, N^3's #30 was inside the
  2026-rule depth of 32, but the 2025 rule gave Hong Kong only one seat.

Run (on Windows set `PYTHONUTF8=1`):
`python scripts/ecfinal_retro.py 2025 7/626 5/890` and
`python scripts/ecfinal_retro.py 2024 6/714 6/402`.
