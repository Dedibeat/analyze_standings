# NUM-R^3: training plan to Hong Kong (2026-11-21 → 2027-01-09/10)

Seven weeks. The plan builds on summary §6 (written before Shenyang) and on the Shenyang dossier
(`shenyang_2026.md`, "What changes for Hong Kong"). Where they differ, this file wins.

## 1. What Hong Kong asks for

The ten EC-Final places go to medal teams in rank order. The 2026-11-16 estimate puts the 10th
place at about **rank 21–25**. Here is what that rank cost on the last two onsite boards
(official teams, `data/ec_online/regional_teams.csv`):

| season | teams | #18 | #21 | #23 | #25 | teams with 4+ solves |
|---|---|---|---|---|---|---|
| 2024 | 149 | 4 / 457 | 4 / 602 | 4 / 647 | 3 / 230 | 24 |
| 2025 | 126 | 5 / 894 | 4 / 499 | 4 / 541 | 4 / 638 | 28 |

- **The line is the 4th problem.**
  - Only 24 and 28 teams solved 4 or more, which is 16–22% of the field.
  - The best 3-solve team was #25 in 2024 and lower in 2025.
- **The target is 4 solved in about 550 minutes**, so the 4th problem needs to be in by about 250'.
  Five solves was top 18 in both seasons.
- **Our chance is real but not large.**
  - The 11-16 estimate: Hong Kong rank median 47 (10–90%: 15–88), a place in 18% of the draws.
  - A later 11-16 ranking, on a branch not merged here: about the 24th-strongest of the 103
    registrants with a 2026 result.
- **The 4th Hong Kong problem is our Shenyang 6th problem.** That was the problem solved by about
  15% of the field (F 60 / 401, A 59 / 401), and Shenyang showed what we lack there:
  - we were slow on the standard set (×1.6–2.2 the gold medians), so it started late;
  - one person was on it;
  - the idea went over as a bound, not an algorithm;
  - the one problem read early (A) was never re-read.

  This plan trains exactly those four things.

## 2. Calendar

Weeks run Monday to Sunday. One full team virtual a week, on a fixed day, on **one computer**.

| week | dates | topic block (owner leads) | team virtual | also |
|---|---|---|---|---|
| 0 | Nov 21–23 | — | — | Shenyang upsolve and setup (§3) |
| 1 | Nov 24–30 | observation / small-answer problems (all three) | #1 | speed drills on easy problems |
| 2 | Dec 1–7 | counting and DP state design (**Erdene leads**: the swap test of summary §6.5) | #2 | Shanghai regional 12-05 |
| 3 | Dec 8–14 | number theory and bits (**Dedi leads**, teaches submask / XOR) | #3 | library check: Dedi's items |
| 4 | Dec 15–21 | graphs and trees (**Tamir leads**: the second swap test) | #4 | Nanchang regional 12-19; library check: Erdene's items |
| 5 | Dec 22–28 | geometry (Tamir, on his library) | #5 | library check: Tamir's items |
| 6 | Dec 29–Jan 4 | no new topic | #6, a full dress rehearsal on Jan 2 or 3 | review only |
| 7 | Jan 5–8 | no new topic | — | light problems, checklist read-through, travel |

- **Flows have no block.** Six weeks do not fit all of summary §6.1. Flows are the item with the
  least evidence that it costs us a medal problem (1051 B and 1794 H only). Erdene keeps Dinic
  and min-cost flow as tested library code and solves those two on his own.
- **If exams or holidays take a week, cut a topic block, not a virtual.** The virtuals and their
  reviews are the core of the plan.

## 3. Week 0 (this weekend): Shenyang upsolve and setup

Upsolve from scratch, timed (dossier, Hong Kong item 7):

| who | problem | how |
|---|---|---|
| Tamir, with Erdene | F | Write the all-partitions brute force first. Find the tests for 1 and 2. Then see why the 257' greedy gives 1 on sample 2. |
| Erdene | C, then J | C: write the state and the one-row update on paper before coding. J: prove the comparability lemma, then compare `j.cpp` with the popcount version. |
| Dedi | A | Number theory, his category. |
| Tamir | D | The case list from memory. |

Setup (one evening, all three):
- A sample check that diffs against the expected output: `./a < 1.in | diff - 1.out`.
- The stress kit (`gen.py`, `brute.cpp`, a 5-line loop), typed until it takes under 3 minutes.
- Erdene moves to a 64-bit compiler (C++20).
- Dedi writes the interactive template, with a flush after every query.

## 4. The weekly routine

**Team day.**
- A 5-hour virtual on a set nobody has read (§6), played under the in-contest rules (§5).
- The same evening, a one-hour review in the dossier format:
  - the standard set's pace against the gold medians;
  - every wrong run with its class;
  - silent minutes;
  - who read what and when;
  - how the 6th problem was chosen.
- Then upsolve the first problem we did not solve, before the next virtual.

**Topic block.**
- The owner gives a one-hour talk on the method and our own past failures.
- During the week each member solves 3–5 problems from the block's list (summary §6.1), timed,
  with the brute force written before the first submission.
- The two swap tests (counting for Erdene, graphs for Tamir) decide the owners for EC-Final.
  The deciding question: who solved more of the block's problems, faster and cleaner?

**Individual.**
- Codeforces rounds as usual, and **upsolve the first unsolved problem after every round**.
- Virtuals are played to the end.
- One problem from the field's next level gets an attempt in every round.

## 5. In-contest rules to rehearse in every virtual

From summary §6.3 and the Shenyang changes. These are the ones Shenyang tested:

1. **Opening.**
   - Erdene opens with the easy problems.
   - No two easy problems queue on one member: the free member takes the second.
   - A harder problem goes to a member early only when it is his type.
2. **Every problem read is reported aloud** in two lines: what it asks, and a first idea or "no
   idea". "No idea" hands the problem to its category owner. A problem dropped in the first
   minutes is re-read at the 6th-problem decision if the board says it is solvable.
3. **Mid problems by type, with a clock.**
   - At 30' without a solution the holder can state, he explains it to a teammate.
   - At 45' it changes hands.
   - After 2 wrong runs: brute force, or a cold read.
4. **The next problem gets two people.**
   - From the moment the closer starts the last standard problem, the other two pair on the
     field's next one: most-solved first, then best conversion.
   - **An idea is handed over as an algorithm** (what to compute in each case) and checked by
     hand on the samples before typing.
5. **Before every submission:**
   - the checklist (summary §6.3 item 4);
   - the samples are compared with `diff`;
   - a greedy or casework solution is compared with a brute force.
   - After any wrong run, the first two minutes go to the output format.
6. **At 200', fix the final plan. No member idle**, and Erdene has a fixed next job after a
   miss: first the cold read for the closer, then the next problem.

## 6. Which sets to play

Six sets nobody has read. Candidates are below; **cross out any that a member has read** (see
§9):
- **Hong Kong-style:** Macau 2023 and Hong Kong 2022. These are the closest to the Hong Kong
  field and difficulty. Use one for the dress rehearsal (#6).
- **2026 regionals we did not attend:**
  - Wuhan and Nanjing, if they are on QOJ;
  - Shanghai (12-05) and Nanchang (12-19), once the sets are public.
  - Their boards give a same-year field to measure against.
- **2025:** Wuhan, Chengdu, Xi'an, Shanghai.
- **2024:** Kunming, Chengdu, Shanghai, Shenyang.

Already read, so not usable:
- the 2022 Hangzhou, Xi'an, Jinan and Shenyang virtuals;
- the 2026 Chengdu and Xi'an virtuals;
- CCPC Jinan, Harbin and Zhengzhou 2025, and CCPC Changchun 2026;
- the practice sets: Shenyang 2023, Nanjing and Hangzhou 2024, Nanjing and Shenyang 2025;
- probably Hong Kong 2024 and 2025, where members competed before.

## 7. What each virtual is measured against

| measure | Shenyang | target by week 6 |
|---|---|---|
| standard set, pace against the gold medians | ×1.6–2.2 | ≤ ×1.4 |
| penalised wrong runs | 1 | ≤ 2 |
| first AC | 11' | ≤ 20' |
| the next problem (solved by 15–20% of the field) | one person from 168', no correct idea | two people from the 200' decision at the latest; solved in 3 of the 6 virtuals |
| problems read and not reported | A | none |
| a member without a clear next job | after C and J, Erdene stayed on J instead of taking F | none |

On a Hong Kong-style set the target is the one from §1: **4 solved in about 550 minutes**.

## 8. Per member

- **Dedi.**
  - Samples must pass before any submission: 38% of his Codeforces rejections fail test 1.
  - A teammate reads the constants line aloud.
  - He leads the number theory and bits week and teaches the submask argument from J.
  - He hands ideas over as algorithms.
  - He keeps A-type problems: number theory is his category, so he takes them when they are
    reported.
- **Tamir.**
  - Speed on easy and constructive problems: H at 168' against a 105' silver median. 49.6 of
    those minutes were the output format, so `diff` the samples.
  - He leads the graphs and trees week and builds the geometry library.
  - He takes F's upsolve with a brute force first.
- **Erdene.**
  - He opens with the easy problems.
  - DP state design (C; his Codeforces 2174 B, 2190 B2) and submask arguments (J).
  - He finishes every virtual and reports every problem he reads.
  - He leads the counting week (the swap test) and stays interactive owner.

## 9. What would change this plan (please answer)

1. **Exams and holidays** between now and Jan 8. Which weeks are short?
2. **Team days.** Can the three of you meet for a 6-hour virtual-plus-review once a week, and
   on which day?
3. **Sets read.** Which candidates in §6 has any member already read?
4. **The library** of summary §6.2 (DSU, modint/CRT, stress kit, Dinic, geometry core). What was
   built before Shenyang? Week 0 and the weekly checks assume nothing beyond the code in the
   saved submissions.

After Hong Kong: if a place comes (from Hong Kong, or an incentive seat after Nanchang; dossier
item 9), EC-Final is Jan 22/23. That leaves 12 days for summary §6 phase 3 (harder 7th/8th
problems in our strong types).
