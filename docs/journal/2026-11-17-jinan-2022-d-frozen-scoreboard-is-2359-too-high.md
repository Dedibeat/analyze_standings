# Jinan 2022 D "Frozen Scoreboard": is 2359 too high? (2026-11-17)

**Request.** Tamir reported the shipped rating (2359) as too high: most silver
and many bronze teams solved it. Check analytically and by hand. Research
only; nothing shipped changed. No script was kept: the numbers come from
`arch_b.shipped.shipped_fit()`, `data/tagged.json`,
`data/cf_gym_mirrors.json` and `output/gym_difficulty.json`.

**The board** (568 official QOJ rows, ranked among themselves; XCPCIO lists 511
medal-eligible teams, so the bands are a few places off).

| official rank | solved D | model predicted | tried D |
|---|---|---|---|
| 1–35 (gold) | 34 / 35 | 87% | 35 |
| 36–105 (silver) | 63 / 70 | 64% | 68 |
| 106–210 (bronze) | 61 / 105 | 39% | 85 |
| 211–300 | 19 / 90 | 26% | 37 |
| 301+ | 1 / 268 | 11% | 34 |

- 178 of 568 solved it. Of the 390 that did not, 309 never submitted.
- It is solved late: median minute 233, 78 of 178 solves in the last hour,
  after A for 122 of the 144 teams with both.
- 85 of 178 solvers were right first try; 69% of the teams that tried solved it.

**On the model's own scale: about 55 too high.**
- The rating sits at the ability of official rank ~105 (2363), where 95% solved
  it. Half the teams solve it at rank 160–210 (2216–2304).
- A logistic curve with a free slope puts the 50% point at 2304 (official
  rows) and 2316 (all rows), with 86 CF points per logit against the model's
  fixed 151.
- The single slope under-predicts medal teams and over-predicts the lower
  field. The rating that reproduces the medal teams alone is 2192; the teams
  that tried, 2173–2192; the non-medal rows alone, 2535.
- DE 2300, hierarchical binary 2311, shipped (with solve times) 2359.
- A shows the same misfit (ranks 301–400: 1% solved, 37% predicted), so it is
  the board, not a fault in D's cells.

**Against real Codeforces ratings: about 450 too high, 310 of it common to
every EC board.**
- CF gym mirror 104076: 647 teams, 311 solved D. Fixed-ability reading
  1915 ± 19. By the best member's CF rating: 1600–1800 36%, 1800–2000 56%,
  2000–2200 65%, 2200–2400 85%; the 50% point is 1850.
- Shipped minus gym, problems with 3–97% gym solves on boards of 100+ gym
  teams: EC median +314 (115 problems, 18 regionals; per contest +223 … +510;
  Jinan 2022 +311). All regions: +312 (475 problems).
- EC regression: a gym reading of 1915 ships at 2291 on average. D's own
  residual is +69 (0.5 SD), so D is not an outlier among its siblings.
- Same board: A 2186 against gym 1318, E 1847 against 993, C 2586 against 2271.

**By hand: about 1900 (±150) as an individual CF problem.**
- Each `?` cell gives a contiguous penalty interval; enumerate the 2^13
  subsets of `?` cells, test the total against the interval sum, then build
  the output. The editorial is three lines.
- The difficulty is the implementation: four input formats and the
  construction of tries and minutes.
- QOJ's own label is 4 of 10 (A 3, C 4, E 2, G 5): the same order as the model.
- Tamir (CF level 1690–1760) solved it first try in the 2026-10-08 virtual.

**Not settled.**
- Whether the +310 is scale inflation or the real gap between an onsite
  five-hour set and a gym entry. Gym entrants solve A 92% of the time against
  45% onsite, and every gym row has a solve.
- No EC regional carries official CF labels (the 184 anchors are Asia Pacific,
  Europe and Northern Eurasia), and only one anchor contest (2692, 8 problems)
  has a gym reading. On the anchors the shipped map reads +48 … +77 in the
  1500–2900 band.
- Neither the single-slope misfit nor the gym offset was turned into a rule.

### Cause hunt (2026-11-17, second entry)

**Request.** Find the cause of the gap and any bug. Research only; nothing
shipped changed.

**Answer.** D ships about 105 too high on the CF-label scale; the
"450" against the gym was mostly the referee.

| identity \ setting | time slices (shipped) | binary + `skip_partial` |
|---|---|---|
| shipped (pair links) | D **2359**, CF 1900–2500 bias +63, RMSE 198.9 | D 2310, bias +7, RMSE 205.5 |
| no cross-roster pair links | D 2305, bias +61, RMSE 197.2 | D **2252**, bias +4, RMSE 203.9 |

(bias = model − CF label on the anchors labelled 1900–2500; RMSE = in-sample
anchor RMSE, not nested LOCO; EC model − gym: +314 / +298 / +297 / +283.)

- **Identity chaining (bug 2): −54 on D.** Jinan-specific: the band bias
  moves −2 and the EC gym offset −17.
- **Solve-time slices: +49 on D**, and the same +56 on the whole 1900–2500
  band against CF labels. This is the documented cost of the flatter map
  ("moves the 1900–2500 band up 60", `hier_time_report.md`), not a D
  quirk: D's shift is at the 89th percentile of all problems, the band shift
  is general.
- **Single Rasch slope: about −40 more** (D's free-slope 50% point 2304 vs
  binary MLE 2341 on the same abilities). Not a bug; 2PL overfit before.
- So D is about 2210–2250 on the scale where mid-band anchors are unbiased.
  Hand ~1900 ± 150 and the gym 1915 remain below; the gym reads mid
  problems 100–160 under their CF labels on 2692 (A, G, I), the one board
  with both.

**Bug 1: the gym scrape is cut at 1,000 standings rows.**
- `data/cf_gym_mirrors.json`: 14 of the 18 EC gyms end at rank 996–1000
  (1053, 1071, 1093, 1096, 1435, 1440, 1449, 1472, 1516, 1821, 1828, 1865,
  1871, 1893). Ghost rows fill the page, so the weakest entrants are missing.
- Jinan 2022: no gym row has fewer than 3 solves (onsite, 17% do). That is why
  A reads 92% solved and 1318.
- The rows are selected on the outcome, so easy problems read far too low
  there. For D the effect is small (about +20 by a rough count).
- The four untruncated EC gyms (1099, 1459, 2567, 2641) still read
  +228 … +299, and the European gyms are complete and read +300 … +450. The
  truncation is not the main cause.
- The scraper is not in the repo; the data needs a paged re-fetch.

**Bug 2: team identity chains through shared members.**
- `arch_a.load.member_identity` unions any two rosters that share two members,
  in any season. Chains merge a school's whole lineage into one team.
- 174 teams have two or more rows in one contest (1,062 rows). 143 teams hold
  6 or more rosters, up to 18 (Shanghai University, Changchun University of
  Science and Technology: up to 4 rows in one contest).
- Rows sharing a team inside one contest: 1,062 shipped, 415 with pair links
  kept inside one ICPC season, 47 with no pair links.
- Effects (table above): Jinan's board and D drop 44–58; anchor in-sample
  RMSE 198.9 → 198.3 (season-scoped pairs) → 197.2 (none). World-Finals
  rosters' fitted − CF ability: +67 / +66 / +50 (median, 54–55 rosters).
- The 2026-07 season-key test (whole rosters split by season, CF LOCO worse)
  is a different change; this one keeps exact rosters linked across seasons
  and only drops the two-shared-member chain. Not run through nested LOCO.

**Checked and cleared.**
- The gym excludes untimed practice rows (`PRACTICE` dropped at scrape time).
- Jinan gym readings do not drift with time or account age: D is 1904 in the
  first week, 1887 after a year, 1946 for teams with 30+ rated contests each,
  2021 with 60+.
- `hier_binary.fit`: gradient, Hessian product and priors read through; no
  error found.
- The offset is nearly the same on every gym board (+83 … +510, correlation
  with board strength −0.25), so it is a global level, not a Jinan effect.
- By onsite solve share the offset peaks in the middle: +194 below 5%, +349 at
  30–50%, +418 at 50–70%, +215 above 90%. Model ≈ 0.845 × gym + 620.
- On 2692, the one board with CF labels and a complete gym, shipped − gym is
  +172.

**Ruled out by refits.**
- Team-prior width: σ 600 / 1500 raise D (2378 / 2394), the gym offset
  (+328 / +335) and the anchor RMSE (201.8 / 208.8).
- Per-season identity (`season_key`): D 2292, gym offset +300, RMSE 197.6;
  about the identity fix's effect, at more splits.
- The ability axis is compressed at the top in every variant (World-Finals
  rosters: fitted on CF slope 0.46–0.51, CF < 2600 reads +231, CF > 3200
  reads −217), as found 2026-08-21; it does not explain the mid-band level.

**Not done.** No fix applied. The identity fix touches `arch_a/load.py` (a
hashed input) and needs the `hier_time` protocol and a re-release. The gym
needs a paged re-fetch before it is used as a level referee again. Scripts
were in the session scratchpad and are not in the repo.

