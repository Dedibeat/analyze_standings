# CCPC comparisons: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## CCPC medal vs ICPC EC regional medal (2026-10-12)

```bash
python3 scripts/ccpc_icpc_medals.py [--board 11th/jinan --solved 4 --penalty 484]
# writes output/ccpc_icpc_medals.{md,json}; --board places a virtual run
```

Official teams of the 16 CCPC regional stations of 2022–2025 are linked to the
same season's ICPC EC regionals by school and ≥ 2 shared members. Hong Kong
boards are linked by pinyin. That gives 4,050 mainland pairs for 2023–2025.
The report shows ranks, percentiles and medals only, so it spoils no contest.

- **A CCPC medal is harder than the ICPC one at every tier, gold included.**
  A team at the CCPC gold line has a 47% chance of ICPC gold. A team at an
  ICPC gold line has 34% at another regional. An average ICPC gold line is
  worth about CCPC rank 35 of 260. CCPC
  gold → ICPC gold 71%. CCPC silver → ICPC silver or better 75%
  and rank ≤ 75 (the EC-Final line) 57%. CCPC bronze → ICPC medal 80% and
  rank ≤ 75 19%. A CCPC medal predicts better than a medal at another ICPC
  regional (ICPC gold → gold 61%).
- **Even odds** at a 260-team station: ICPC gold at CCPC rank ~24 (the CCPC
  gold line), rank ≤ 75 at ~59 (mid-silver), ICPC silver at ~93.
- **Stable** across 2023–2025. Station field strength shifts the curve by
  ±0.5 log-odds but does not repeat by city.
- **Jinan 2025 virtual** (4 solved / 484 min): official rank 80 / 259, CCPC
  bronze, 2 places short of silver. That maps to mainland ICPC rank ≤ 75 at
  36% (43% with Jinan 2025's field offset). This assumes virtual form equals
  onsite form.

Details: `docs/journal/` (2026-10-12 entry).

## ICPC regionals vs CCPC stations: medal difficulty and problem quality (2026-10-12)

```bash
python3 scripts/contest_quality.py   # writes output/contest_quality.{md,json}
```

The 44 onsite boards: 28 ICPC EC regionals and 16 CCPC stations, 2022–2025.
Everything is reported per contest, never per problem, so no set is spoiled.

- **Medals, measured with the same teams.** An average ICPC gold is easier
  than a CCPC gold. Only the hardest regionals reached CCPC gold level: by
  linked teams Shenyang 2024, Shanghai 2025 and Chengdu 2025 (about a top
  6–8% CCPC finish for even odds); by performance Chengdu 2025, Shenyang
  2024 and Wuhan 2025. None was clearly harder. Xi'an and Shenyang 2025 were
  the easiest.
- **Rank ≤ 75 (the EC-Final line)** was hardest at the 434–444-team fields:
  Kunming 2024, Wuhan 2025 and Hangzhou 2023.
- **Gold lines in CF-equivalent performance:** CCPC 2765–2811 (2024–2025);
  ICPC median about 2690. The highest ICPC lines are Chengdu 2025 2799,
  Shenyang 2024 2779 and Wuhan 2025 2774.
- **Mirror check.** CCPC sets exist only as UCup mirrors. There the same
  teams read the same as on onsite ICPC boards (+9), so the lines are
  comparable. (A first run reported −184; that was a board-copy bug, fixed
  the same day.)
- **Problem difficulty**: CCPC sets rate ~115 higher at the median problem
  (2024–2025), which is not significant.
- **Quality, from standings only.** Five measures: discrimination, problems
  nobody solved, ties at the gold line, rejected runs per accepted run, and
  ranking consistency with the same teams' other contests. ICPC and CCPC are
  indistinguishable on all of them.
  - CCPC Harbin 2024 is the cleanest set.
  - A crowded gold line goes with less consistent rankings (suggestive:
    p = .013 before multiple-testing correction).
  - Standings cannot show originality, statement clarity or test strength.

Details: `docs/journal/` (2026-10-12, second entry).

## CCPC findings vs the 2026 forecast and the ratings (2026-10-12)

These checks used scratch queries; the only code change is the
`contest_quality` fix. Contest-level numbers only.

- **Bug fixed.** `contest_quality.performance` ranked results against the UCup
  copy of 15 ICPC boards stored twice, overstating their lines by 70–290.
  The −184 "mirror offset" came from this bug. A regression test covers it.
- **The ratings pass a rating-free check.** For the same teams in the same
  season, CCPC mirror minus ICPC board is +9 by performance and +23 by the
  problem-implied rating (shipped DE ratings). With the 2026-10-13
  event-field ranking it is −8 by performance.
- **Gold difficulty per regional** (16 mainland regionals, within season):
  - The online-rank and CCPC-percentile measures, which use no ratings,
    agree with each other at Spearman 0.80.
  - The fit's gold-line performance agrees with them at 0.74–0.81.
  - The CF medal bar agrees with them at only 0.54–0.56.
  - The bar's largest misses are Shanghai 2025 and Nanjing 2024 (bars too
    low) and Xi'an 2025 and Kunming 2024 (bars too high).
  - So `medal_predict`'s "Shanghai / Nanjing are easy gold cities" is not
    supported. Site difficulty does not repeat by city, so `online_gold`
    remains the 2026 forecast.
- **An earlier same-season CCPC result as a forecast update.** It is worth
  about as much as an earlier ICPC regional:
  - In 2024 it improved held-out log loss for the 916 teams that had one
    (EC-Final line −0.021).
  - In 2025 it did nothing; only 208 teams had one.
  - Not shipped.
- **NUM-R^3, what-if.** Online plus members' history gives a ~10% chance of
  rank ≤ 75. With the Jinan virtual's CCPC place (0.309) counted as onsite
  it is ~14%, and with a real top-15% CCPC finish ~24%.

Details: `docs/journal/` (2026-10-12, third entry).

## CCPC sets ranked by problem difficulty (2026-10-18)

```bash
python3 scripts/ccpc_difficulty_rank.py   # writes output/ccpc_difficulty_rank.md
```

19 CCPC sets, hardest first: fewest problems rated ≤ 2400 CF, ties by a
2400-rated team's expected solves. Ranks and verdicts only, so nothing is
spoiled.

- **Which sets.** 9 sets have full shipped ratings. 10 more stations are rated
  from their onsite XCPCIO boards: the 2022–2023 stations, 10th Chongqing and
  11th Harbin. Their onsite teams are linked to fitted teams by shared
  members, and each problem is rated with those abilities held fixed, then
  mapped onto the shipped scale. The fit and the shipped ratings are
  unchanged.
- **Comparison.** Each set is compared with the mainland ICPC regionals of
  2023–2025 at bronze, silver and gold, in two ways:
  - **Medal:** is the last medallist's performance higher? Yes at every tier
    for almost every station. 11th Harbin is the same as a regional, and
    10th Chongqing is the same at bronze and silver. The finals and the 2017
    set have no onsite board.
  - **Problems only:** does a team at that tier's regional line need more
    rating to solve as much? The two finals, Guangzhou 2022, both Zhengzhou
    sets and Jinan 2025 are harder at every tier.
- **The easy sets** have easier problems at every tier: 10th Chongqing
  (2024), 8th Weihai (2022), 11th Harbin (2025), 10th Harbin (2024) and
  Qinhuangdao 2017.
- **Check.** Held out of the fit, the onsite method reproduces the shipped
  ratings of the six rated stations in set-level terms, with the same
  order.

Details: `docs/journal/` (2026-10-18 entry and its follow-up).
