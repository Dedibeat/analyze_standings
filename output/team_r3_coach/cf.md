# NUM-R^3 on Codeforces: rated rounds, virtuals, practice (2026-11-05)

Handles (user, 2026-11-05):

| member | handle(s) |
|---|---|
| Dedi | Dedibeat |
| Tamir | t4_4 |
| Erdene | erdene1231, plus Munkh-Erdene.B (registered Aug 2026, one rated round) |

Background (user):
- Tamir (3rd year) and Erdene (1st year) are former IOI contestants.
- Dedi (4th year) did maths in high school and started programming as a freshman.

**Source:** the public Codeforces API (`user.rating`, `user.status`, `problemset.problems`,
`contest.list`), cached in `data/team_r3/cf/`. Every number below comes from
`python3 scripts/team_r3_cf.py`, which also writes `output/team_r3_cf.json`.

**What counts:**
- Every timed individual entry: rated rounds, out-of-competition entries and virtuals.
- Excluded:
  - Team entries (earlier teams on ICPC mirrors and gyms: Dedi 12, Tamir 3, Erdene 1).
  - The April Fools contests.
  - Gyms are counted, but left out of everything that needs a problem rating.

**Code is not available.** Codeforces submission pages sit behind a Cloudflare challenge (HTTP 403
even with `cloudscraper`), so this review uses verdicts, failing-test numbers and times, not source.

**Definitions:**
- **Level** is the problem rating at which the member's in-contest solve rate is 50%, fitted on
  every problem of the contests entered; problems not attempted count as unsolved.
  - CF problem ratings sit on the user-rating scale, so a level reads like a rating.
  - Levels use rated rounds only. Out-of-competition entries are not full efforts: Dedi's level
    there is 1390 and Erdene's 1400, far below their rated levels.
- **Topic z** compares observed solves with those expected at the member's level for that
  half-year. It counts rated rounds and virtuals, and only problems within ±500 of that level.
  - Ten topic families × three members are 30 comparisons, so a |z| of 1.5–2 is a lead, not a
    proof.
  - Single tags move noticeably with the model, so only the families are used below.

## 1. At a glance

| | Dedi | Tamir | Erdene |
|---|---|---|---|
| rating now / max | 1817 / 2106 (2025-10-19, round 2154) | 1632 / 1671 (2025-12-29, 2182) | 1959 / 2204 (2026-01-07, 2183) |
| rated rounds (last one) | **121** (2026-10-26) | 22 (2026-02-26) | 58 (2026-03-28) + 1 on Munkh-Erdene.B (2026-10-24) |
| level, rated rounds: all / last 12 months | 1780 / 1840 | 1690 / 1760 | 1850 / **2050** |
| virtuals | 64 (8 gyms solo) | 44 (31 of them Div 3/4 in 2023 H2) | 64 |
| virtual vs rated, time-matched | **same** (+10, 95% −80…+100) | not measurable (18 rated problems in matched half-years) | **320 weaker** (95% 230…420) |
| first-try ACs | 441 / 644 (**68%**) | 214 / 275 (78%) | 377 / 480 (79%) |
| rejections failing test 1 | **208 / 577 (36%)** | 33 / 182 (18%) | 56 / 207 (27%) |
| failed system tests / hacked | 1 / 2 in 94 live CF-rules rounds | 0 / 0 in 14 | 1 / 1 in 49 |
| next unsolved problem of a rated round, upsolved | 25 / 106 | 6 / 19 | 11 / 51 |
| 2026 practice: unique ACs, median rating (IQR) | 90, 2300 (2100–2400) | 119, 1700 (1300–1900) | 125, 1800 (1500–2000) |

Solve rate in rated rounds by problem rating:

| rating | Dedi | Tamir | Erdene |
|---|---|---|---|
| ≤ 1200 | 249/257 | 48/48 | 112/115 |
| 1300–1600 | 84/101 | 19/24 | 56/58 |
| 1700–2000 | 56/119 (47%) | 6/22 (27%) | 27/61 (44%) |
| 2100–2400 | 7/93 | 0/21 | 7/47 |

## 2. Dedi

- **The most active by far:** 121 rated rounds since 2024-01-06, against 22 for Tamir and 59 for
  Erdene.
  - His virtuals are as strong as his rated rounds (offset +10). His virtuals are real practice.
- **The 2026 swings:**
  - Peak: 2106 on 2025-10-19 (2154, Div 2 rank 115).
  - Down to 1765 by 2026-03-14, back up to 1964 by 2026-04-21, down to 1644 by 2026-06-28, now
    1817.
  - The largest drops:
    - 2231 (−143): B, rated 1100, unsolved after 2 WAs; rank 5350.
    - Edu 2182 (−106).
    - 2238 (−99): A, B and C, rank 4175.
    - Div 1 2196 (−77): only A, after 20 wrong tries (next bullet).
- **Submitting without the samples passing:**
  - 36% of his rejections fail test 1, which is almost always the sample. The share is the same
    under CF rules (101 of 268 live) and ICPC rules (40 of 105 live), so it doesn't change when a
    rejection costs penalty.
  - Tamir's share drops to 10% under ICPC rules (§3).
  - The clearest case is **2196 C1** (interactive, rated 1800; 2026-02-11):
    - Nine straight "Idleness limit exceeded on test 1" between minutes 102 and 134 (362490463 …
      362506639). That usually means the program did not flush or did not follow the protocol.
    - Then six WAs, unsolved (15 tries in all); C2 got four more WAs.
  - It is the same judge-as-debugger habit as 4607 E at ICPC (summary §6.4).
  - Overall: 13 idleness rejections on test 1, and the lowest first-try rate of the three (68%).
- **Once a solution passes the pretests, it is right.**
  - One failed system test in 94 live CF-rules rounds (2128 A, 331106511) and two hacks (2000 G,
    2042 C).
  - His losses come early: an unproven idea, or a sample that was never run.
- **Topics:**
  - Above expectation:
    - number theory/bits: +1.5 (57/103 vs 50.8 expected);
    - constructive/greedy: +1.58 (165/293 vs 153.8);
    - implementation: +1.94;
    - interactive: +2.04 (15/24 vs 10.7). He solves them, but with the idleness slips above.
  - Below expectation:
    - **combinatorics/probability: −1.87** (21/64 vs 27.0);
    - **graphs/trees: −1.49** (41/122 vs 47.8; trees alone 14/57 vs 20.8).
- **Practice:**
  - 90 unique practice ACs in 2026, median rating 2300, i.e. about 450 above his level. 61 of them
    come from rounds he entered, so these are upsolves of hard problems.
  - Over all rated rounds, though, he went back to the next unsolved problem only 25 times in 106.

## 3. Tamir

- **Few rounds:** 22 rated rounds in two years, only 2 in 2026 (last 2026-02-26, 2205).
  - Level 1690 over all rated rounds and 1760 over the last 12 months, from only 76 problems, so
    this is the least certain of the three levels.
  - He solves everything up to 1200 (48/48) and most of 1300–1600 (19/24). He gets 6 of 22 at
    1700–2000 and nothing above 2100 (0/46).
- **The cleanest submitter:**
  - 78% first-try ACs; no failed system tests and no hacks.
  - **He checks samples when the rules punish it:** 40% of his rejections fail test 1 in live
    CF-rules rounds (19/47), against 10% in live ICPC-rules rounds (3/29) and 11% in ICPC-rules
    virtuals (11/101). Dedi's share stays at 35–38% everywhere.
- **Topics:**
  - Above expectation: graphs/trees +1.76 (20/41 vs 15.9); strings +1.73 (16/25 vs 13.0).
  - Below expectation: number theory/bits −1.51 (15/50 vs 18.8).
- **Long chains:**
  - 2175 B (rated 1300): 9 tries, unsolved (2025-12-06, −47).
  - 2180 C (1900): 8 tries, unsolved.
- **Practice is steady and at the right height:** 57–69 unique ACs per half-year since 2025 H2.
  - 2026 median rating 1700 (IQR 1300–1900).
  - Only 8 of the 119 come from his own rounds; he practises from the problemset.
- **Upsolving:** he later solves most problems he attempted and missed (15 of 21), but rarely the
  next one he never tried (6 of 19).

## 4. Erdene

- **The strongest individual right now:** level 2050 over the last 12 months of rated rounds
  (106 problems), against Dedi's 1840 and Tamir's 1760.
  - Peak: 2204 at Hello 2026 (2183).
  - Then down to 1959 over five rounds (2190 −88, 2187 −90, 2196 −49, 2207 +29, 2211 −47).
  - No rated round on erdene1231 since 2026-03-28. The new account Munkh-Erdene.B has one round
    (2277, 2026-10-24, rank 1596).
- **His virtuals are much weaker than his rated rounds:** 320 points, time-matched.
  - In 36 of 63 virtuals his last submission came before half-time, against 18 of 59 rated rounds.
  - Examples:
    - 2180, virtual: A at minute 5, B (rated 800) never submitted, nothing for the remaining 145
      minutes.
    - 2098, virtual: A at minute 21, nothing after.
  - These virtuals were abandoned, not lost.
  - Rated rounds can also go silent: Div 1 2187, A at minute 12, then 168 minutes without a
    submission.
- **Clean submissions:**
  - 79% first-try ACs; 27% of rejections fail test 1; no idleness verdicts.
  - One failed system test (2061 B, 302078061) and one hack (2033 D).
- **Topics:** the flattest profile.
  - Combinatorics/probability +1.16 (13/30 vs 10.5); constructive/greedy +0.92.
  - **Interactive −1.12** (7/24 vs 9.2).
  - Everything else is within ±0.6.
- **Practice:**
  - 443 unique practice ACs in 2024 H2, about 120 per half-year in 2025, then 59 and 66 in the
    two halves of 2026.
  - 2026 median rating 1800 (IQR 1500–2000), below his rated level. 11 of the 125 come from his
    own rounds.
- **Compiler:** the 32-bit `C++17 (GCC 7-32)` was 830 of his 836 submissions in 2024, 817 of 896 in
  2025, and still 139 of 348 in 2026.
  - That compiler has no `__int128`, which the ICPC checklist relies on for products of values
    ≥ 10⁹, and its 64-bit arithmetic is slow.

## 5. Team-level

- **Upsolving the next problem is rare for all three**: 25/106, 6/19, 11/51 rated rounds.
- **Pace is similar.** The median time since the previous AC for a problem rated 1300–1600 is
  Dedi 24 min, Erdene 24.5, Tamir 27.
  - For 1700–2000 it is Dedi 36, Erdene 34, Tamir 56 (only 10 solves).
- **Exposure gaps match the ICPC gaps.** Problems carrying the tag in contests they entered,
  solved / seen:

  | tag | Dedi | Erdene | Tamir |
  |---|---|---|---|
  | flows | 1/20 | 1/15 | 0/1 |
  | probabilities | 1/25 | 1/20 | 0/10 |
  | hashing | 3/35 | 4/28 | 1/10 |
  | FFT | 2/21 | 1/11 | 1/1 |
  | suffix structures | 0/11 | 1/10 | 0/1 |

  These counts include problems far above their level, so they measure exposure, not ability.
- **Geometry on CF is not the ICPC kind.** Dedi's geometry-tagged solves at 2200–2500 are maths and
  greedy problems: 2159 D1 also carries binary search, dp and greedy; 2225 E carries constructive
  and maths. Erdene's 18 geometry solves are mostly rated 800–1500. CF gives no evidence on the
  convex-hull and point-in-polygon work that lost 4607 E.

## 6. What this changes in the ICPC plan (summary §6)

**Confirmed:**
- **Dedi owns maths, number theory and bits:** number theory/bits +1.5 here.
- **Dedi's main bug class is "submitted without checking":** 36% of rejections fail the sample,
  whatever the rules, and nine idleness runs in one round (2196 C1). The pre-submit rule "all
  samples run" (§6.3) is the single most useful habit for him. Interactive problems get a
  template: flush after every query, read every reply.
- **Tamir is the careful implementer:** 78% first try, and he adjusts to the penalty rules.
- **Pace is not the gap between members.** Their solve times per problem rating are close.

**Conflicts worth testing in the Hong Kong block** (not before Shenyang: 10 days is too short to
change roles):
1. **Counting/combinatorics.** Dedi owns it now, but on CF he is −1.87 while Erdene is +1.16 and
   Tamir +0.56. The ICPC counting misses were also Dedi's (1053 C; the 4607 C modulus chain). Let
   Erdene lead the counting week, and swap owner and backup if it holds.
2. **Graphs/trees.** Erdene owns it now with Tamir as backup. On CF Tamir is +1.76, Erdene −0.43
   and Dedi −1.49. Let Tamir lead the graphs week. Dedi should not be the first reader of a
   graph/tree problem.
3. **Interactive.** Erdene stays the owner (3 of 3 first try at ICPC), although on CF he is −1.12
   and Dedi +2.04. Dedi is a real backup once he uses the protocol template.
4. **Strings.** Dedi owns it, but Tamir is +1.73 on CF (16/25) and Dedi +0.05. This is a lead with
   a small sample.

**New habits:**
- **Virtual training is played to the end.** Erdene abandons half his virtuals, and a
  half-played virtual teaches nothing about the last 100 minutes, the team's weakest phase
  (summary §5).
- **Upsolve the first unsolved problem after every round.** All three do it about 1 time in 4.
- **Erdene moves to a 64-bit compiler** (`C++20/23 (GCC 13/14-64)`), so `__int128` and fast 64-bit
  arithmetic are normal for him before Hong Kong.
- **Tamir plays rated rounds again.** He has had 2 since 2025-12-29, and his level is the least
  certain of the three.

## 7. Open questions

- With a browser `cf_clearance` cookie, passed in the environment (`CF_COOKIES`) and never written
  to disk, the chains above could be read as code: 2196 C1/C2 and 2208 D1/D2 (Dedi), 2175 B
  (Tamir). Do you want that?
- Why the new account Munkh-Erdene.B? Should its future rounds count as Erdene's (they do here)?
- Do any of you use other handles or other platforms (AtCoder, Luogu) for rounds or upsolving? The
  CF upsolve numbers may undercount.
