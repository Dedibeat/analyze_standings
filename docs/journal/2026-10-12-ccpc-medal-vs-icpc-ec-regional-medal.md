# CCPC medal vs ICPC EC regional medal (2026-10-12)

**Request.** Explore how a CCPC medal relates to an ICPC Asia East regional
medal, without spoiling unseen contests. Of the CCPC sets, only Jinan 2025
has been done (as a virtual). So the analysis reports ranks, percentiles and
medals only. Solve counts are shown for 11th Jinan only.

**Merge first.** `git pull` conflicted in this file: both sides had appended
sections. Both were kept (2631c15), and all 155 tests passed.

**Data** (`scripts/ccpc_icpc_medals.py` → `output/ccpc_icpc_medals.{md,json}`).
- **CCPC boards.** The 16 regional stations on XCPCIO for 2022–2025
  (8th–11th CCPC), official teams only. Standings come from
  `regional_standings(board, "ccpc")`.
- **CCPC medals.**
  - 8th and early 9th boards: the board's own counts.
  - Later boards: XCPCIO's `"medal": "ccpc"` preset. XCPCIO's source
    (`rank.ts` `buildAwards`) gives gold to rank ⌈10%⌉, silver to ⌈30%⌉ and
    bronze to ⌈60%⌉ of official teams with ≥ 1 solve. This is exactly the
    rule `medal_counts` falls back to.
  - **Fix in shared code:** `build_ec_online_data.medal_counts` crashed on the
    preset string. It now treats the string as "no counts". ICPC boards are
    unchanged.
- **Link.** A CCPC entry is matched to an official ICPC EC regional entry of
  the same season with the same school and ≥ 2 shared members
  (`regional_teams.csv`).
  - At each ICPC regional, the entry sharing the most members is taken.
  - Hong Kong 2024–2025 boards list pinyin members and English schools. There
    the CCPC members are converted with `hk_link.pinyin_variants`, and the
    school is mapped through `school_names_en.csv`.
  - Hong Kong 2022 and Macau 2023 have no members, so they stay unlinked.
- **Coverage.** 4,078 official CCPC entries; 3,375 (83%) link to at least one
  ICPC regional. That gives 5,798 pairs: 4,050 mainland pairs in 2023–2025
  (the model seasons; 2022's ICPC regionals were online) and 115 Hong Kong
  pairs.
- **Outcomes.** "Rank ≤ 75" is the mainland 2026 EC-Final line used by
  `anchor_teams`. For Hong Kong the line is the 10th place under the 2026 rule
  (37 in 2024, 32 in 2025).

**CCPC medal → the same team at a mainland ICPC regional of the same season (2023–2025).**

| CCPC | n | ICPC gold | silver+ | any medal | rank ≤ 75 |
|---|---|---|---|---|---|
| gold | 463 | 71% | 95% | 100% | 91% |
| silver | 1,011 | 23% | 75% | 96% | 57% |
| bronze | 1,404 | 3% | 36% | 80% | 19% |
| none | 1,172 | 1% | 13% | 51% | 5% |

**Benchmark: a medal at one mainland ICPC regional → the same team at another.**
Gold → gold 61%, silver+ 93%; silver → gold 15%, rank ≤ 75 44%; bronze →
medal 69%, rank ≤ 75 11%; none → medal 38%.

**Reading it.**
- **A CCPC medal is about one notch harder than an ICPC medal.** Over the same
  4,050 pairs, the CCPC gold share is 11.4% against 15.2% ICPC gold, and any
  medal is 71% against 78%. This fits CCPC stations (~260 official teams)
  having stronger fields per medal than the ICPC regionals; field strength
  was not measured directly.
- **A CCPC medal is the stronger predictor.** Each CCPC row beats the matching
  ICPC→ICPC row: silver → ICPC gold 23% vs 15%, rank ≤ 75 57% vs 44%.
- **Even odds** (logistic in logit CCPC percentile, team-clustered bootstrap),
  as rank at a 260-team station:

  | ICPC outcome | even odds at CCPC rank |
  |---|---|
  | gold | ~24 (0.093), i.e. the CCPC gold line |
  | rank ≤ 75 | ~59 (0.228), i.e. mid-silver |
  | silver or better | ~93 (0.358), i.e. upper bronze |
  | any medal | ~209 (0.80) |

  The logistic matches the binned shares within 8 points; most bins are
  within 4. The worst bin is percentile 0.10–0.15 for rank ≤ 75: 82%
  observed against 74% from the model.
- **Stable across seasons.** 2023 / 2024 / 2025: CCPC gold → ICPC gold 73 / 69 /
  72%; silver → rank ≤ 75 59 / 55 / 56%. In 2022 (online ICPC regionals) a
  CCPC silver gave ICPC gold 38%.
- **Station field strength.** Each station's intercept shift (pooled slope
  fixed) is about ±0.5 log-odds, SD ~0.3; the noise on one station is ~0.13.
  It does not repeat by city: Chongqing −0.28 → +0.41 and Harbin +0.08 →
  −0.24 (rank ≤ 75, 2024 → 2025). So it cannot guide a choice between future
  stations; it only matters when reading a result from a known past station.
  11th Jinan: +0.30 (rank ≤ 75), +0.34 (silver+), −0.09 (gold).
- **Hong Kong (115 pairs, thin).** CCPC gold → HK gold 81%, HK line 95%;
  silver → 29% / 62%; bronze → 0% / 22%; none → 3% / 10%.

**Jinan 2025 virtual** (`--board 11th/jinan --solved 4 --penalty 484`):
- **Placement.** Official rank 80 of 259 (percentile 0.309) → **CCPC bronze**,
  two places short of silver. The silver line is rank 78 at 4 solved /
  466 min; gold is rank 26 at 6 / 845; bronze is rank 156 at 3 / 377.
- **Same-season mainland ICPC outcome** for real teams at that CCPC percentile:

  | mainland ICPC outcome | P | 10–90% | with 11th Jinan's offset |
  |---|---|---|---|
  | gold | 9% | 8–10% | 8% |
  | silver or better | 57% | 55–58% | 65% |
  | any medal | 89% | 88–90% | 91% |
  | rank ≤ 75 | 36% | 34–37% | 43% |

- **Agreement.** This matches the anchor reading (2026-10-11): "at the
  EC-Final line, below gold".
- **Caveats.**
  - These numbers assume the virtual equals onsite form. The online virtuals
    ran about 2× stronger in rank terms than the official 2026 rounds
    (2026-10-08). The official-online model gives NUM-R^3 ~12% per mainland
    site, against 36–43% here.
  - The 2025 teams played both contests in the same season, in either order.
    This is association, not a forecast from a year-old set.
  - Rank ≤ 75 is a proxy for the line; 2026's K is ~70–80.

**Not covered.** CCPC finals (held months later, with a different field), the
CCPC invitationals and provincials, and the girls' and vocational contests.

Run (~10 s once the boards are cached; on Windows set `PYTHONUTF8=1`):
`python scripts/ccpc_icpc_medals.py --board 11th/jinan --solved 4 --penalty 484`.
Tests: `python -m unittest tests.test_ccpc_icpc_medals`.
