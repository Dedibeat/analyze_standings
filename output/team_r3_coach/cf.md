# NUM-R^3 on Codeforces: rated rounds, virtuals, practice (2026-11-05)

Handles (user, 2026-11-05):

| member | handle(s) |
|---|---|
| Dedi | Dedibeat |
| Tamir | t4_4 |
| Erdene | erdene1231, plus Munkh-Erdene.B (registered Aug 2026; its rounds are Erdene's) |

Background (user):
- Tamir (3rd year) and Erdene (1st year) are former IOI contestants.
- Dedi (4th year) did maths in high school and started programming as a freshman.

**Round by round:** see `cf_rounds.md`, which also covers which types of problems you fail and
succeed at, and what to work on.

**Source:** the public Codeforces API (`user.rating`, `user.status`, `problemset.problems`,
`contest.list`, and `contest.standings` for the real problem lists), cached in `data/team_r3/cf/`.
Every number below comes from `python3 scripts/team_r3_cf.py` (writes `output/team_r3_cf.json`).

**Correction, 2026-11-05.** The first version of this file undercounted Div. 2 rounds.
- Cause: `problemset.problems` files the problems a Div. 2 round shares with its Div. 1 twin only
  under the Div. 1 id, so the first script saw only A and B in 49 Div. 2 rounds.
- The problem lists now come from each round's standings. The numbers below are the corrected
  ones.
- The claim that Tamir "checks samples when the rules punish it" is withdrawn: Codeforces penalises
  a failure on test 1 under neither rule set (next paragraph).

**Codeforces does not count a rejection on test 1, under either rule set.** Verified on our own
rated entries:
- Recomputing the official penalty of all 13 ICPC-rules entries (Edu, Div. 3) is exact only when
  test-1 failures are left out.
- In CF-rules rounds, the official rejected-attempt counts also skip them, e.g. Dedi's 2178 D and E.

So on Codeforces a failed sample costs nothing, while at ICPC every rejected run costs 20 minutes.

**What counts:**
- Every timed individual entry: rated rounds, out-of-competition entries and virtuals.
- Excluded:
  - Team entries (earlier teams on ICPC mirrors and gyms: Dedi 12, Tamir 3, Erdene 1).
  - April Fools contests.
  - Gyms are counted, but left out of everything that needs a problem rating.

**Code is not available.** Codeforces submission pages sit behind a Cloudflare challenge (HTTP 403
even with `cloudscraper`), so this review uses verdicts, failing-test numbers, times, the official
standings and the editorials.

**Definitions:**
- **Level** is the problem rating at which the member's in-contest solve rate is 50%. Problems not
  attempted count as unsolved, and it reads like a rating.
  - Levels use rated rounds only. Out-of-competition entries are not full efforts: Dedi's level
    there is 1390 and Erdene's 1400.
- **Topic z** compares observed solves with those expected at the member's level for that
  half-year. It counts rated rounds and virtuals, and only problems within ±500 of that level.
  - Ten families × three members are 30 comparisons, so a |z| of 1.5–2 is a lead, not a proof.

## 1. At a glance

| | Dedi | Tamir | Erdene |
|---|---|---|---|
| rating now / max | 1817 / 2106 (2025-10-19, round 2154) | 1632 / 1671 (2025-12-29, 2182) | 1959 / 2204 (2026-01-07, 2183) |
| rated rounds (last one) | **121** (2026-10-26) | 22 (2026-02-26) | 58 (2026-03-28) + 1 on Munkh-Erdene.B (2026-10-24) |
| level, rated rounds: all / last 12 months | 1790 / 1870 | 1660 / 1710 | 1810 / **2050** |
| virtuals | 64 (8 gyms solo) | 44 (31 of them Div 3/4 in 2023 H2) | 64 |
| virtual vs rated, time-matched | **same** (+10, 95% −80…+100) | 310 weaker (95% 30…570, few rated problems) | **300 weaker** (95% 210…390) |
| first-try ACs | 457 / 671 (**68%**) | 217 / 279 (78%) | 384 / 491 (78%) |
| rejections failing test 1 | **237 / 630 (38%)** | 35 / 186 (19%) | 63 / 226 (28%) |
| failed system tests / hacked | 2 / 2 in 94 live CF-rules rounds | 0 / 0 in 14 | 2 / 1 in 49 |
| next unsolved problem of a rated round, upsolved | 28 / 119 | 6 / 22 | 13 / 58 |
| 2026 practice: unique ACs, median rating (IQR) | 90, 2300 (2100–2400) | 119, 1700 (1300–1900) | 125, 1800 (1500–2000) |

Solve rate in rated rounds by problem rating:

| rating | Dedi | Tamir | Erdene |
|---|---|---|---|
| ≤ 1200 | 250/258 | 50/50 | 113/116 |
| 1300–1600 | 99/117 | 20/27 | 59/63 |
| 1700–2000 | 65/135 (48%) | 7/28 (25%) | 28/69 (41%) |
| 2100–2400 | 7/111 | 0/24 | 7/55 |

## 2. Dedi

- **The most active by far:** 121 rated rounds since 2024-01-06. His virtuals are as strong as his
  rated rounds (offset +10), so they are real practice.
- **The 2026 swings:**
  - Peak: 2106 on 2025-10-19.
  - Down to 1765 by 2026-03-14, back up to 1964 by 2026-04-21, down to 1644 by 2026-06-28, now
    1817.
  - The largest drops:
    - 2231 (−143): B, rated 1100, unsolved after 2 WAs while C was solved.
    - Edu 2182 (−106).
    - 2238 (−99): C (1400) at 82′, against 51′ for the next tier.
    - Div 1 2196 (−77).
- **Submitting before the sample passes:**
  - 38% of his rejections fail test 1, which is almost always the sample. That is 130 of 321 live
    under CF rules and 40 of 105 under ICPC rules. Codeforces charges nothing for these; ICPC
    charges 20 minutes each.
  - The clearest case is **2196 C1** (interactive, rated 1800; 2026-02-11):
    - Nine straight "Idleness limit exceeded on test 1" between minutes 102 and 134 (362490463 …
      362506639). That usually means the program did not flush or broke the protocol.
    - Then six WAs, unsolved.
  - Overall: 15 idleness rejections on test 1, and the lowest first-try rate of the three (68%).
- **Once a solution passes the pretests, it is right:** two failed system tests in 94 live CF-rules
  rounds (1966 C, 2128 A) and two hacks (2000 G, 2042 C).
- **Topics:**
  - Above expectation:
    - number theory/bits: +1.58 (60/109 vs 53.2 expected);
    - constructive/greedy: +1.46;
    - implementation: +2.18;
    - interactive: +1.96 (20/33 vs 15.1).
  - Below expectation:
    - **combinatorics/probability: −1.83** (22/68 vs 28.0);
    - **trees: −2.17** (15/60 vs 21.8); the graphs/trees family as a whole is −1.21.
- **Practice:** 90 unique practice ACs in 2026, median rating 2300, about 430 above his level.
  61 of them come from rounds he entered.

## 3. Tamir

- **Few rounds:** 22 rated rounds in two years, only 2 in 2026 (last 2026-02-26).
  - Level 1660 over all rated rounds and 1710 over the last 12 months, from 86 problems, the least
    certain of the three.
  - He solves everything up to 1200 (50/50) and most of 1300–1600 (20/27). He gets 7 of 28 at
    1700–2000 and nothing above 2100.
- **Clean on first submissions:** 78% first-try ACs; no failed system tests, no hacks.
  - Test-1 failures are 41% of his rejections in live CF-rules rounds (21/51) but 10% in
    ICPC-rules rounds (3/29 live, 11/101 virtual).
  - Codeforces penalises neither, so the difference follows the round type: ad-hoc Div. 2 B/C
    against standard Div. 3/4/Edu problems. `cf_rounds.md` §2 has the rounds.
- **Topics:**
  - Above expectation:
    - **trees +2.12** (9/17 vs 5.9); graphs/trees family +1.95 (21/44 vs 16.3);
    - strings +1.73 (16/25 vs 13.0).
  - Below expectation: number theory/bits −1.52 (16/52 vs 19.9).
- **His virtuals also look weaker** than his rated rounds (310), but only 27 rated problems fall in
  the matched half-years.
- **Practice is steady and at the right height:** 57–69 unique ACs per half-year since 2025 H2,
  2026 median rating 1700.
- **Upsolving:** he later solves most problems he attempted and missed (15 of 22), but rarely the
  next one he never tried (6 of 22).

## 4. Erdene

- **The strongest individual right now:** level 2050 over the last 12 months of rated rounds
  (106 problems).
  - Peak: 2204 at Hello 2026 (2183).
  - Then down to 1959 over five rounds (2190 −88, 2187 −90, 2196 −49, 2207 +29, 2211 −47).
  - The new account has one round (2277, 2026-10-24).
- **His virtuals are much weaker than his rated rounds:** 300 points, time-matched.
  - In 32 of 63 virtuals his last submission came before half-time, against 13 of 59 rated rounds.
  - Examples:
    - 2180, virtual: A at minute 5, B (rated 800) never submitted.
    - 2098, virtual: A at minute 21, nothing after.
  - Rated rounds go silent too: Div 1 2187, A at minute 12, then 168 minutes without a submission.
- **Clean submissions:**
  - 78% first-try ACs; 28% of rejections fail test 1.
  - Four idleness runs on test 1, all on 2078 E.
  - Two failed system tests (2061 B, 2160 E) and one hack (2033 D).
- **Topics:** the flattest profile.
  - Combinatorics/probability +1.18 (15/32 vs 12.4).
  - Interactive −1.16 (8/26 vs 10.4); data structures −1.02.
  - Everything else is within ±0.9.
- **Practice:**
  - 443 unique practice ACs in 2024 H2, about 120 per half-year in 2025, then 59 and 66 in the two
    halves of 2026.
  - 2026 median rating 1800, below his rated level. 11 of the 125 come from his own rounds.
- **Compiler:** the 32-bit `C++17 (GCC 7-32)` was 830 of his 836 submissions in 2024, 817 of 896 in
  2025, and 139 of 348 in 2026.
  - It has no `__int128`, which the ICPC checklist relies on, and its 64-bit arithmetic is slow.

## 5. Team-level

- **Upsolving the next problem is rare for all three**: 28/119, 6/22, 13/58 rated rounds.
- **Pace is similar.** The median time since the previous AC for a problem rated 1300–1600 is
  Dedi 24 min, Erdene 27, Tamir 27.
  - For 1700–2000: Dedi 36.5, Erdene 36, Tamir 58 (11 solves).
- **Exposure gaps match the ICPC gaps.** Problems carrying the tag in contests they entered,
  solved / seen:

  | tag | Dedi | Erdene | Tamir |
  |---|---|---|---|
  | flows | 2/21 | 1/18 | 0/2 |
  | probabilities | 1/27 | 2/22 | 0/12 |
  | hashing | 3/37 | 4/29 | 1/10 |
  | FFT | 2/21 | 1/11 | 1/1 |
  | suffix structures | 0/11 | 0/9 | 0/1 |

  These counts include problems far above their level, so they measure exposure, not ability.
- **Geometry on CF is not the ICPC kind.** Dedi's geometry-tagged solves at 2200–2500 are maths and
  greedy problems (2159 D1, 2225 E). Erdene's 18 geometry solves are mostly rated 800–1500.

## 6. What this changes in the ICPC plan (summary §6)

**Confirmed:**
- **Dedi owns maths, number theory and bits** (+1.58).
- **Dedi's main bug class is "submitted without checking":** 38% of rejections fail the sample, and
  nine idleness runs in one round (2196 C1). Codeforces lets a failed sample go free and ICPC does
  not, so "all samples pass locally before any submission" (§6.3) is his most useful rule.
  Interactive problems get a template: flush after every query, read every reply.
- **Tamir is the careful implementer** (78% first try) and the team's tree/graph solver on CF.
- **Pace is not the gap between members.**

**Conflicts worth testing in the Hong Kong block** (not before Shenyang):
1. **Counting/combinatorics.** On CF Dedi is −1.83, Erdene +1.18 and Tamir +0.47. The ICPC
   counting misses were Dedi's too (1053 C; 4607 C's modulus chain). Let Erdene lead the counting
   week.
2. **Graphs/trees.** On CF Tamir is +1.95 (trees alone +2.12), Erdene −0.84 and Dedi −1.21 (trees
   alone −2.17). Let Tamir lead the graphs/trees week. Dedi should not be the first reader of a tree
   problem.
3. **Interactive.** Erdene stays the owner (3 of 3 at ICPC; on CF his hardest solve is an interactive
   2600, 2109 C3). Dedi (+1.96) is a real backup once he uses the protocol template.
4. **Strings.** Tamir is +1.73 on CF (16/25), Dedi +0.22. This is a lead with a small sample.

**New habits:**
- **Virtuals are played to the end.**
- **Upsolve the first unsolved problem after every round.**
- **Erdene moves to a 64-bit compiler.**
- **Tamir plays rated rounds again.**

## 7. Open questions

- With a browser `cf_clearance` cookie, passed in the environment (`CF_COOKIES`) and never written
  to disk, the chains above could be read as code: 2196 C1/C2 and 2208 D1/D2 (Dedi), 2175 B
  (Tamir). Do you want that?
- Answered 2026-11-05: Munkh-Erdene.B's rounds are Erdene's.
- Do any of you use other handles or other platforms (AtCoder, Luogu) for rounds or upsolving? The
  CF upsolve numbers may undercount.
