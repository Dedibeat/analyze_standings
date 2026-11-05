# NUM-R^3: season review and plan (Aug–Nov 2026)

Team: Tamir (Tamir Jamiyangarav), Erdene (Munkh-Erdene Bayarjargal), Dedi (Dugarjantsan Bilguun).
Basis: 16 contests (14 TEAM_R3 virtuals with every submission's code, plus the 2026 official online
rounds 4071 and 4113 from their board rows). Each contest has a dossier in this folder (`<id>.md`)
with problem-by-problem notes and a timeline (steps 1–2). Every claim below cites a contest,
problem and/or QOJ submission id; details are in the dossiers.

Fixed conventions:
- **Fields.** Medal and EC-Final lines are taken from the onsite official field: XCPCIO for the 2026
  regionals and the CCPC stations, XCPCIO rows of `regional_teams.csv` for the 2022 regionals
  (35/70/105 medals). QOJ boards are used for the online rounds.
- **EC-Final line.** "EC-Final line" = rank ≈ 75 under the 2026 rule (plausible 70–80;
  details.md 2026-10-01). At Hong Kong the bar is about rank 32–37 (details.md 2026-10-07).
- **Pace.** "Pace ×k" = our solve minute / the median solve minute of the top group (gold teams at
  regionals and CCPC, the top 10% online).
- **Members.** From `members_solved.csv`; in "A + B", A proposed the idea and B most likely
  implemented it. 1051, 1485, 2513, 2524, 2575 (and 4071 F, M) have no member data: **unknown**.
- **Not done.** Step 0 (shortest public ACs) was skipped at the user's request, so library
  comparisons use the editorials and our own code only.

## 1. Season results

| contest | type | result | rank / field | where it sits |
|---|---|---|---|---|
| 1071 Hangzhou 2022 | regional virtual | 7 / 886 | **#19 / 556** | **gold** |
| 4607 Chengdu 2026 | regional virtual | 6 / 894 | #35 / 319 | silver, **59 min from gold**, inside EC-Final line |
| 4593 Xi'an 2026 | regional virtual | 4 / 536 | #86 / 402 | silver, 33 min outside EC-Final line |
| 1096 Shenyang 2022 | regional virtual | 4 / 435 | #88 / 708 | silver, 23 min outside EC-Final line |
| 1053 Jinan 2022 (2 members) | regional virtual | 5 / 578 | #92 / 511 | silver |
| 1051 Xi'an 2022 | regional virtual | 6 / 357 | #106 / 476 | bronze, **5 min from silver** |
| 2693 CCPC Jinan 2025 | CCPC virtual | 4 / 484 | #80 / 260 | bronze, **18 min from silver** |
| 2575 CCPC Harbin 2025 | CCPC virtual | 5 / 707 | #118 / 260 | bronze |
| 2661 CCPC Zhengzhou 2025 | CCPC virtual | 3 / 591 | #127 / 260 | bronze |
| 1794 EC Online I 2024 | online virtual | 6 / 714 | #96 / 2323 (4%) | L was GPT-assisted; without it #136 (6%) |
| 2513 EC Online I 2025 | online virtual | 7 / 625 | #147 / 2279 (6.5%) | best clean online result |
| 2524 EC Online II 2025 | online virtual | 5 / 890 | #345 / 2575 (13%) | |
| 1485 EC Online I 2023 | online virtual | 6 / 758 | #417 / 2554 (16%) | |
| 1799 EC Online II 2024 | online virtual | 6 / 402 | #514 / 2450 (21%) | |
| **4071 EC Online I 2026** | **official** | 6 / 877 | **#544 / 2535 (21%)** | standard six at 2× the top-10% penalty |
| **4113 EC Online II 2026** | **official** | 4 / 482 | **#352 / 2636 (13%)** | standard four, 93 min behind top 10% |

- **The six ICPC regional virtuals:** 1 gold, 4 silver, 1 bronze. Inside the EC-Final line twice
  (1071, 4607). Three near misses: 4593 (one wrong run), 1096 (two wrong runs) and 1051 (one more
  problem).
- **In almost every contest we solved exactly the field's standard set for our solve count**
  (e.g. 139 of 140 four-solvers at 4593 had CHJM like us). The rank was decided by **penalty** and
  by **whether a 6th/7th problem came**, not by which problems we picked.

## 2. Strengths and weaknesses by topic

84 solved problems; first-try share, wrong runs and median pace by primary topic:

| topic | solved | first try | wrong runs | pace | evidence |
|---|---|---|---|---|---|
| implementation / simulation | 16 | 14 | 2 | ×1.27 | 1053 D (frozen scoreboard, 3.5 KB, first try), 2513 A, 4593 M |
| greedy / observation | 18 | 12 | 13 | ×1.30 | clean: 4607 M/K, 2693 C; chains: 2524 C ×3, 1053 A ×2 |
| constructive | 7 | 5 | 3 | **×1.17** | 2575 K, 1096 F, 2693 K, 2524 J (190 solves), 1799 I |
| interactive / communication | 3 | **3** | **0** | ×1.34 | 4607 H (26/319 onsite), 4607 I, 1071 I (35 QOJ solves) |
| strings | 4 | 3 | 3 | ×1.34 | 1071 K trie (35' ahead of median), 2575 J Manacher (WA, MLE ×2) |
| math / number theory | 10 | 4 | 10 | ×1.44 | 1794 C (perm mod 2, 68' vs 126'); 1071 A (negative egcd), 4607 D ×3 |
| DP | 7 | 4 | 5 | ×1.62 | 1071 C, 2513 D/I; 2575 L ×3 |
| graphs / trees | 8 | 2 | **21** | ×1.69 | 1485 G ×5, 1794 L ×4 (assisted), 2513 M ×2, 1071 G ×2 |
| counting / combinatorial DP | 8 | 3 | **14** | **×1.92** | 4607 C ×4, 2661 B ×5, 4071 D |
| flows / matching (Hall) | 1 | 0 | 3 | ×2.31 | 2524 C ×3 before the Hall bound |
| geometry | **0** | — | — | — | 4607 E failed (Dedi; 3 bugs); 1485 K never attempted |

**Strengths (the evidence holds across contests):**
- **Interactive and two-run communication problems:** 3 of 3 first try, two of them rare onsite
  (4607 H, 1071 I). All by Erdene.
- **Constructive problems with a short proof:** best pace of any topic (2575 K, 1096 F, 2693 K,
  2524 J, 4593 J's idea).
- **Clean implementation of long but well-specified statements** (1053 D, 2513 A, 4593 M).
- **Discovering structure in data-structure problems** (2693 L faster than the gold median;
  1071 K).

**Weaknesses:**
- **Counting/combinatorial DP and graph/tree problems** produce the long chains: 35 of our 75
  wrong runs come from 16 problems in these two topics.
- **Greedy without proof:** many greedy problems are solved cleanly, but the failures are all
  unproven orders or assumptions (2524 C, 1053 A, 1051 E, 2661 B, 4071 A ×4 by Dedi before
  Erdene's first-try takeover).
- **Topics we cannot do at all yet:** geometry, flows/matching, XOR linear basis, polynomial
  interpolation, discrete log / multiplicative orders. These are exactly the "next problems" we
  missed (§5).

## 3. Recurring bug classes

All **68 penalised wrong runs** in the 14 virtuals (= 1360 penalty minutes, ≈ 97 per contest),
each assigned one primary class. The per-contest counts match the boards' wrong-try counts exactly.

| class | runs | penalty | examples (contest problem: submission) |
|---|---|---|---|
| **unproven idea / greedy / guessed formula** | 14 | 280 | 4607 D: 3333931, 3334026; 2524 C: 2914380–2914780; 1053 A: 3130459, 3130682; 2661 B: 3191526, 3191627; 1051 E: 3072945; 1799 L: 2924110; 1071 D: 3078780 |
| **casework / off-by-one** | 11 | 220 | 2693 F: inverted boolean 3152894, missing branch 3153295; 2661 M: lexicographic `max` on numbers 3191371; 1794 G: median definition 2801138; 1794 F: ties in monotonic stack 2800660 |
| **memory or time not estimated** | 10 | 200 | 1485 G: `up[22][2e6]` (176 MB) ×3; 1485 D: deep recursion + sets in 128 MB ×2; 2575 J: 4n `long long` arrays for n = 10^7 ×2; 1799 L: gcd inside binary search; 1799 G: exponential recursion; 1485 I: 62²·8·n |
| **data-structure misuse / structural bug** | 8 | 160 | 2661 G: `priority_queue<…, less<>>` (max-heap) 3191724; 2524 J: `map::operator[]` inserting while iterating 2917141; 2513 M: up and down passes not composed ×2; 1794 L ×4 (assisted) |
| **edge parameters and indexing** | 7 | 140 | 4593 J: array sized n, indexed to 2n (3274161); 1053 E: division by zero at k = n (UBSan-confirmed); 2661 B: p = 0 / q = 0 ×3; 1485 D: start vertex unmarked; 1096 C: symmetric case |
| **blind or identical resubmission** | 6 | 120 | 1799 L: byte-identical 2924396; 2661 G: transition toggled back and forth ×3; 1794 G: `#define int long long` with no overflow; 2575 L: bit order flipped |
| **overflow / sentinel / modular slips** | 5 | 100 | 4607 D: `b * (k + 4)` with b, k ≤ 10^18; 4593 C: `inf = 1e18` < real answers; 2575 L: `inf + 1` drifting past `== inf` checks; 4607 C: unreduced final sum; 1071 A: negative ext-gcd coefficient |
| **debug leftovers and typos** | 4 | 80 | 1071 G: `cnt = 100` cap on the cycle walk; 1485 G: DSU `return dsu[u] = get(u)` ×2; 1096 L: `printf("%.10.lf")` |
| **misread statement constant** | 3 | 60 | 4607 C: modulus 1e9+7 instead of 998244353 in three runs (counted ×2 here, once more under "idea"); 1485 L: k ≥ 2 ignored |

Wrong runs on problems we never solved (no penalty, but a lost problem). The 14 virtuals have four
such problems with 11 runs, and **all four were Dedi's** (2661 J from the sheet; 4607 E, 1053 C
and 1071 M from the user, 2026-11-05):
- 4607 E: 5 runs. Orientation-dependent point-in-triangle, `sort` inside the output routine, and a
  missing case. With two local fixes our code passes 14,000 random tests.
- 2661 J: a test-time loop bound `l < 3` was left in; one character from AC (#127 → #86).
- 1053 C: overflow, then TLE from rebuilding a knapsack per child.
- 1071 M: an identical resubmission.

**What the classes cost in places** (each a one-line fix, see the dossiers):
- Chengdu 2026 silver → gold: the modulus in C and the overflow in D are 60 min (894 → 834 ≤ 835).
- Xi'an 2026 #86 → #69, inside the EC-Final line: drop J's array bound and C's sentinel.
- Jinan 2025 bronze → silver: one F casework run fewer.
- Xi'an 2022 bronze → silver: E's untested assumption.
- Zhengzhou 2025 #127 → #86: J's leftover loop bound.
- **Penalty from wrong runs alone moved us across a medal or EC-Final line in 5 of the 9 regional
  and CCPC virtuals.**

## 4. Per member

From the sheet (51 credited solves with idea/implementation roles; 31 solves have no member data).

| member | solo solves | first try | wrong runs | median pace | in pairs | topics |
|---|---|---|---|---|---|---|
| **Tamir** | 9 | 6 | 7 | **×1.19** | idea ×3 (1053 A, 1071 G, 4113 K), implementation ×2 (1071 K, 1794 L) | greedy/observation, heavy implementation, constructive |
| **Erdene** | 18 | 12 | 13 | ×1.48 | idea ×1 (1096 F); took over 4071 A | interactive, greedy, DP, data structures, easy-problem speed |
| **Dedi** | 20 | 10 | 18 (+4 on 4071 A, handed over; +11 on 4 unsolved) | ×1.47 | idea ×2 (1071 K, 1794 L), implementation ×4 (1096 F, 1053 A, 1071 G, 4113 K) | math/number theory, constructive, counting, strings |

The wrong-runs column counts problems the member solved. Runs on problems never solved in the
virtuals: Dedi 11 (4607 E 5, 1053 C 2, 1071 M 2, 2661 J 2), Tamir 0, Erdene 0.

- **Erdene** is the team's interactive and communication solver: 4607 H, 4607 I and 1071 I, all first
  try. Also fast on easy problems (4607 M 23') and structural data structures (2693 L at gold pace),
  plus knapsack DP (1071 C).
  - *Rescues:* 4071 A in the official round. After Dedi's four wrong tries he took it over and
    was accepted first try.
  - *Fails on* model/maths chains: 4607 D (two wrong models, then overflow), 2661 G (wrong idea,
    max-heap, three toggles), 1794 G (median off-by-one, then a blind change).
- **Dedi** carries the most problems and the insight-heavy maths: 1794 C at 68' vs 126', 1071 A,
  1799 G/L, and a correct idea for 2661 J. He writes most of the brute-force testers seen in the code
  (4607 C, 4593 C/J, 2661 J), but **after** the first WA.
  - *Fails on* implementation details: the 4607 C modulus (×3), the 4593 C sentinel and 4593 J array
    size, 2693 F casework (×2), 2661 M comparison, the 2661 J leftover bound, and the 1799 L identical
    resubmit. In the official round, 4 wrong tries on 4071 A before Erdene solved it.
  - *Takes the last open problem, and it does not go in:* all four unsolved problems we attempted
    in the virtuals were his: 4607 E (263–272'), 1053 C (213–236'), 1071 M (283–286'), 2661 J
    (184–227'). E and J had the editorial's idea and failed on code: three glue bugs in E, one
    leftover loop bound in J. C had an init/`% mod` slip and then lacked the knapsack-deletion trick
    (TL). M's rerooting code was resubmitted unchanged and never debugged.
  - *Overloaded:* 2 of 4 problems at 4593, both stalled; 4 of 6 at 1799; 3 of 4 at 4113; 4 of the
    6 attempted at 1053 (with A's fix and C open at once in the last 35 minutes); at 4607, C and E,
    9 of the 12 in-contest wrong runs.
- **Tamir** has the best relative pace and the cleanest heavy implementation (1053 D first try,
  4607 K first try, 2693 K's constructive proof). He is the idea source in three pair solves,
  including 1071 G.
  - *Fails on* 2661 B: a missing global verification step, then p = 0 / q = 0 edge cases; 169 minutes.
  - **No recorded solve at 4593 and 1799.** What he worked on there is unknown (question).
- **Pairs that worked:** 1071 K (Dedi idea, Tamir code) 35' ahead of the gold median; 1071 G;
  1096 F; 4113 K. The best contest (1071) had all three members contributing in parallel.
- **Gaps nobody covers:** geometry, flows/matching (Hall, Dinic, MCMF), XOR linear basis, Lagrange
  interpolation, discrete log / orders, knapsack-with-deletion and rerooting tricks. Our 179
  submissions contain **no** flow, interpolation or XOR-basis code, and the only geometry is Dedi's
  in-contest attempt at 4607 E.

## 5. Strategy

### Reading and choosing problems
- **We usually follow the field's order, but twice we did not, and it cost a medal tier:**
  - 2524: 74 minutes and 3 WAs on the second-easiest problem C while the easiest, D, sat untouched
    (D then went in first try).
  - 2575: J (80 onsite solves) instead of I (131 solves, a 20-line parity invariant). That was the
    silver line.
- **Slow first problem** in 5 contests: 4593 43' (gold median 20'), 2575 35' (17'), 2693 31' (14'),
  2524 first AC at 100', 1051 J 14' (10').
- **The next problem we never reached** (the field's next solve after our count):
  - geometry: 4607 E, 1485 K;
  - flows: 1051 B, 1794 H;
  - number theory and bits: 2693 A, 4593 G, 4113 A;
  - counting: 1053 C, 2513 J;
  - graphs: 1799 E, 1071 M;
  - interpolation: 2524 I;
  - invariant: 2575 I.

### When to switch or give up
- The long stalls were solo: 2661 B 169 min (Tamir), 4593 J 95 min (Dedi, also on C), 2524 C
  74 min, 1053 A 100 min, 4607 C 86 min.
- **The one recorded handover worked.** 4071 A: Dedi made 4 wrong tries, Erdene took over and was
  accepted first try. Handing over after two WAs would have saved 40 penalty minutes in an
  official round.
- **The silent finish:** 7 of 14 virtuals ended with 80+ minutes and no submission:
  1051 176 min, 1799 163, 2513 131, 4593 110, 2693 85, 1096 84, 1485 82. In each, the field's next
  problem was solvable for a team at our level (several were upsolved later, e.g. 2513 J).

### Pairing and implementation
- Pair solves are fast (1071 K, G). Solo debugging under pressure produced the worst habits: blind
  toggles (2661 G, Erdene), judge-as-debugger traps (4607 E, Dedi), identical resubmissions
  (1799 L and 1071 M, both Dedi).

### Verification before submitting
- **14 runs were unproven ideas** that a 10-line brute force over tiny inputs refutes. Stress tests
  confirm this for 2661 M, 1053 A and 4607 E (dossiers).
- The team already writes testers (4607 C, 4593 C/J, 2661 J, 1051 E, 1071 A, 2575 J), but always after
  a WA.

### Templates and library
The code shows retyped or missing pieces:
- DSU retyped as `int get(int …)` in 15 files, with a typo in 1485 G.
- ext-gcd / modular inverse not normalised (1071 A).
- No flow, geometry, interpolation or XOR basis anywhere.
- An LCA that doesn't fit memory (1485 G).
- A hand-rolled SCC with incremental closure that we could not debug (1794 L).
- The default language left on C++14 (2575 A compile error).

### Virtual vs official form
- **Online rounds:** virtual median ~13% (4%, 6.5%, 13%, 16%, 21%), official 21% (4071) and 13%
  (4113). Pace ×1.25 in the online virtuals vs ×1.55 in the official rounds. Wrong runs per solve:
  0.93 (virtual) vs 0.70 (official).
- So **officially we were more careful but much slower**: same problem set as the top 10%, 2× their
  penalty at 4071.
- **Caveats:**
  - A virtual is not onsite form: no travel, no pressure, a known end time.
  - Past-season virtuals may carry some familiarity.
  - The 2022 regional virtuals compare against online-held 2022 fields.
  - details.md (2026-10-08, 2026-10-26) measured the same: virtual results read ~2× better in rank
    terms than the 2026 official rounds.
- Treat the virtual medals as an **upper bound** for Shenyang and Hong Kong.

## 6. Action plan for the rest of the season: Shenyang (2026-11-15), Hong Kong (~2027-01-07/08), EC-Final (2027-01-22/23)

The team is accepted to both regionals (user, 2026-11-04). The target is set by the data:
- Our virtuals show the standard set solved at 1.3–1.9× the top group's pace, with ≈ 97 penalty
  minutes per contest from wrong runs.
- **Halving the wrong runs and adding the 6th problem are worth more than any new topic.**

### 6.0 Calendar and targets

**Shenyang, 2026-11-15 (11 days away).**
- Recent lines (XCPCIO official, `regional_teams.csv`):

  | season | teams | last gold | rank 75 | last silver |
  |---|---|---|---|---|
  | 2023 | 291 | 6 / 871 | 5 / 975 | 4 / 345 (#87) |
  | 2024 | 300 | 6 / 928 | 5 / 968 | 4 / 479 (#90) |
  | 2025 | 400 | 5 / 561 | 4 / 297 | 4 / 482 (#120) |

- Our Shenyang 2022 virtual was 4 / 435 (#88 of 708), 23 minutes outside rank 75.
- **Target: the standard set with ≤ 2 wrong runs, plus a 5th or 6th problem in the last 100
  minutes.** That is the EC-Final line (≈ 75) at every recent Shenyang.

**Hong Kong, ~2027-01-07/08.**
- An EC-Final place needs about rank 32–37 (10 places, medal teams; details.md 2026-10-07).
- The members' past HK ranks are 30, 39 and 42.

**EC-Final, 2027-01-22/23**, if a place comes from Shenyang or Hong Kong.

**Phase 1, Nov 4–14 (to Shenyang): process only, no new topics.**
- Adopt the rules of 6.3 and the checklist.
- Build the essential library pieces of 6.2: DSU, normalised modint/ext-gcd, the stress-test kit,
  C++20 + sanitizer setup, and Dinic.
- Re-solve the chain problems of 6.1 item 1 with zero WAs.
- Play two full 5-hour virtuals of regionals the team has **not** read, run strictly under 6.3.
  Afterwards, review each the same way as these dossiers: wrong runs by class, silent minutes,
  board order.

**Phase 2, Nov 16 – Jan 6 (to Hong Kong, 7 weeks).**
- Topics 6.1 items 2–7 (geometry, flows, counting, number theory/bits, graphs, invariants), about
  one per week, plus the rest of 6.2.
- One full virtual per week under the same rules.
- First, review Shenyang onsite with the same method (it will be the first onsite measurement of
  this season).

**Phase 3, Jan 9–21 (to EC-Final, if qualified).**
- Harder 7th/8th-problem practice in the team's strong types (interactive, constructive), and
  keep the process rules.

### 6.1 Topics to train, in priority order (practice problems from these contests: all already read, no new spoilers)
1. **Clean first submission (process, not a topic).** Re-solve our own chains from scratch with the
   checklist below, timed, with zero WAs allowed:
   - 4607 C (Counting Arrays), 4607 D (Duel of Wrath);
   - 2661 B (Cutting Chocolate), 2661 G (Plus Xor);
   - 2524 C (Jiaxun!), 1053 A (Tower).
2. **Geometry with safe predicates.** Build the library first (6.2), then:
   - 4607 E Enclose the Point (31/319 onsite);
   - 1485 K Minimum Euclidean Distance (309 online);
   - 2575 B Ball And Movable Walls (74/260);
   - 2524 A Angry Birds (131 online).
3. **Flows, matching, Hall's theorem:**
   - 1051 B Cells Coloring (102; incremental max flow + edge colouring);
   - 1794 H Rainbow Bracket Sequence (86; min-cost flow with lower bounds);
   - 2524 C Jiaxun! (redo with a flow/Hall check);
   - 2524 B Rectangular Wooden Block (24; bounded flow, stretch).
4. **Counting / combinatorial DP tricks:**
   - 1053 C DFS Order 2 (68; knapsack with item deletion);
   - 2661 I Dumb Problem II (53);
   - 2693 E Tree and Subgraph Problem (52);
   - 2513 J Moving on the Plane (127; re-solve without the upsolve code);
   - 4607 A Average of Averages.
5. **Number theory, bits, linear algebra:**
   - 2693 A Cipher (69; discrete log mod 2^64);
   - 4113 A All Closed (115; XOR basis);
   - 2524 I DAG Query (417; Lagrange interpolation, interactive);
   - 4113 E Exponent (93; orders via CRT);
   - 4593 G Gungnir Fracture (11 onsite, stretch).
6. **Graphs and tree DP:**
   - 1799 E Escape (505; parity BFS);
   - 1071 M Please Save Pigeland (34; rerooting with a gcd state);
   - 2661 D Diameter of a Tree (34);
   - 1096 E Graph Completing (57);
   - 4071 G Toll Gates (135).
7. **Observation / invariants** (cheap points we skipped):
   - 2575 I hexagon flip (131/260; parity per coordinate line);
   - 4071 A Recall (redo; 4 wrong officially);
   - 4071 N Red Sequence (153).

### 6.2 Library / template items to add (each tested before Hong Kong)
- **DSU** with path compression and size; **modint** that always stays in [0, m); **ext-gcd /
  CRT / modinv** returning normalised values. Evidence: 1485 G typo, 1071 A negative coefficient.
- **Max flow (Dinic) and min-cost flow**, plus a one-page note on Hall's theorem and König's
  edge-colouring theorem. Evidence: 1051 B, 1794 H, 2524 C.
- **Geometry core:**
  - `orient`, point-in-triangle and point-in-convex-polygon (O(log n)), all orientation-safe;
  - convex hull; point-to-segment and point-to-polygon distance;
  - a rule never to `sort` output vertices.
  - Evidence: 4607 E, 1485 K.
- **XOR linear basis; Lagrange interpolation** (at 0..n and arbitrary points). Evidence: 4113 A,
  2524 I.
- **LCA** in two variants (binary lifting, and an O(n)-memory Euler tour + sparse table or jump
  pointers). Also **SCC (Tarjan)** and a **Kruskal reconstruction tree**. Evidence: 1485 G, 1794 L.
- **Knapsack with deletion / prefix-suffix knapsack**, and a **rerooting DP skeleton**. Evidence:
  1053 C, 1071 M.
- **Stress-test kit:** `gen.py`, `brute.cpp`, and a 5-line `check.sh` loop. Make it muscle memory;
  it was effectively written from scratch in 6 contests.
- **Contest setup:** C++20 as default (2575 A); compile with
  `-Wall -Wextra -fsanitize=address,undefined` locally. This flags 1096 L's printf and 1053 E's
  division by zero.

### 6.3 In-contest rules
1. **Opening (0–30').** Split the set into thirds and read. By 10', each member names the easiest
   problem in their third. The fastest coder starts the easiest immediately. **Target: first AC by
   20'.**
2. **Choose by the board.** After every AC, the next problem is the most-solved unsolved one on the
   live board (before the freeze), unless someone already has a full solution to another. Evidence:
   2524 D vs C, 2575 I vs J.
3. **Time caps:**
   - 25 minutes on an easy problem without a submission → a second member reads the statement.
   - **2 WAs on the same problem → stop submitting:** write the brute force and generator, or hand
     the problem to a teammate for a cold read of statement + code. 4071 A shows it works: Erdene's
     takeover was AC first try, but only after 4 WAs.
   - 45 minutes stuck on any problem → switch.
4. **Pre-submit checklist** (one line each, all from our bugs):
   - (a) every constant copied from the statement: modulus, bounds, k ≥ 2 — 4607 C, 1485 L;
   - (b) any product of inputs ≥ 10^9 → `__int128` or reorder — 4607 D;
   - (c) INF larger than the maximum answer, compared with `>= INF/2` — 4593 C, 2575 L;
   - (d) array sizes vs the largest index (2n, n+1) — 4593 J;
   - (e) n = 1, k = n, p = 0, empty input; any division by zero — 1053 E, 2661 B;
   - (f) memory in MB and operation count, written down — 1485 D/G/I, 2575 J, 1799 L;
   - (g) no debug caps, test bounds or `test()` calls left — 1071 G, 2661 J;
   - (h) all samples run and output format checked — 1096 L;
   - (i) for greedy / casework / formula: compared against a brute force on small inputs — 14 runs.
5. **Never resubmit without a visible diff that fixes a diagnosed bug.** No identical files, toggles
   or `#define int long long` guesses (1799 L, 2661 G, 1794 G). Don't resubmit accepted problems
   (4593 J/C, 1071 I).
6. **The last 100 minutes.** At 200', fix the final plan: two members on the most-solved remaining
   problem, one finishing whatever is closest to AC. **No member idle.** Evidence: 7 of 14 virtuals
   had 80+ silent minutes at the end.
7. **Interactive problems go to Erdene first** (3 of 3 first try). Reserve 30 minutes of his time
   in the last two hours if one is open (4113 H, 4593 L were never read, as far as the data shows).

### 6.4 Habits to drop (with evidence)

| habit | evidence |
|---|---|
| Submitting an unproven greedy or assumption | 14 runs / 280 min: 2524 C ×3, 1053 A ×2, 4607 D ×2, 2661 B ×2, 1051 E, 1799 L, 1071 D, 2661 G, 4607 C |
| Debugging by submission (toggles, traps, identical files) | 2661 G 3191747–3191819 (Erdene); 4607 E 3336557–3336649 (Dedi; `for(;;)` and a non-returning `int ass()` as probes); 1799 L 2924396 and 1071 M 3081379 identical (Dedi) |
| Writing the brute-force tester only after a WA | 4607 C, 4593 C/J, 2661 J, 1051 E, 1071 A, 2575 J all add `brute`/`test` in the run after the first failure |
| Reflexive `#define int long long` and per-component containers | 1485 D (MLE in 128 MB), 4607 C (810 MB for a 200 MB table), 2575 J (MLE) |
| Retyping standard structures in contest | DSU typo 1485 G; custom SCC closure 1794 L; max-heap default 2661 G |
| Resubmitting after AC | 4593 J 3275839, 4593 C 3276249, 1071 I 3081413–3081454 |
| Going silent in the last hour | 1051 (176 min), 1799 (163), 2513 (131), 4593 (110), 2693, 1096, 1485 |
| Solo stalls on easy problems | 2661 B 169 min, 4593 J 95 min, 2524 C 74 min, 1053 A 100 min |

### 6.5 If the team specialises: who takes which category

Based on the 51 attributed solves (31 more are unknown, so treat this as a starting split to
revisit after Shenyang). Each category has a **primary owner**, who studies it, owns its library
code and reads those problems first, and a **backup**, who can take it when the owner is busy.

| category | primary | backup | evidence |
|---|---|---|---|
| interactive / communication | **Erdene** | Dedi | 4607 H, 4607 I, 1071 I: 3 of 3 first try |
| data structures (segment tree, Fenwick, DSU, LCA, SCC) | **Erdene** | Tamir | 2693 L at gold pace; owner of the retyped pieces (1485 G, 1794 L) |
| graphs, trees, flows / matching (Dinic, MCMF, Hall, König) | **Erdene** | Tamir | nobody covers flows today (1051 B, 1794 H); the graph/structure library sits with the DS owner |
| math, number theory, bits / XOR basis, interpolation | **Dedi** | Tamir | 1794 C (68′ vs 126′), 1071 A, 1799 G/L, 2661 J idea |
| counting / combinatorial DP, probability | **Dedi** | Erdene | 4607 C (right method), 1799 L, 2661 J; the missed 1053 C, 2661 I, 2513 J |
| strings (trie, hashing, Manacher, Z/KMP) | **Dedi** | Tamir | 4071 L, 1071 K idea |
| geometry (new) | **Tamir** | Dedi | needs exact, careful casework code; Tamir has the fewest implementation slips and best pace (1053 D, 4607 K first try). Dedi wrote the only geometry attempt (4607 E): the editorial's approach, lost to three glue bugs |
| constructive / proof-heavy | **Tamir** | Dedi | 2693 K, 4607 K; constructive is the team's best-pace topic (×1.17) |
| long implementation / simulation | **Tamir** | Erdene | 1053 D (3.5 KB, first try), 2693 K |
| easy problems / opening | **Erdene** | everyone | 4607 M 23′, 4593 M; fastest on the first problem |

**How it changes a contest:**
- **Opening:** Erdene codes the first easy problem while Tamir and Dedi read.
- **Dedi thinks, Tamir types** on long maths/counting implementations. The fastest pair solve of
  the season was exactly this split (1071 K: Dedi's idea, Tamir's code, 35′ ahead of the gold
  median). It also moves code away from Dedi's main bug class (constants, sentinels, array sizes:
  4607 C, 4593 C/J).
- **Every submission by Dedi gets the constants line of the checklist read aloud by a teammate**
  (modulus, bounds, INF, array sizes).
- **The last open problem: Dedi's idea, a second reader before every run.** All four unsolved
  problems we attempted in the virtuals were his (4607 E, 1053 C, 1071 M, 2661 J). Before each run on
  the last problem, a teammate reads the diff or runs the brute force. A reader catches 2661 J's
  `l < 3` and 1053 C's missing `% mod`; a 30-line brute force finds 4607 E's first bug in under a
  second.
- **Erdene keeps interactive problems for the last two hours** if one is open, and is the team's
  cold reader for graph/DS chains. His 4071 A takeover (first-try AC after Dedi's 4 WAs) is the
  model.
- **Tamir needs a visible share of the problems.** He has no recorded solve at 4593 or 1799.
  Owning geometry and constructive gives him problems that the other two do not take.

**Training split** (problem lists from 6.1):
- **Erdene:** the flows block (1051 B, 1794 H, 2524 C), the graphs/trees block (1799 E, 1071 M,
  2661 D, 1096 E, 4071 G), interactive (4113 H, 4593 L), and the library: Dinic/MCMF, DSU, LCA ×2,
  SCC, Kruskal tree.
- **Dedi:** the number theory/bits block (2693 A, 4113 A, 2524 I, 4113 E), the counting block
  (1053 C, 2661 I, 2693 E, 2513 J, 4607 A), and the library: modint/CRT, XOR basis, Lagrange,
  knapsack with deletion.
- **Tamir:** the geometry block (4607 E: start from Dedi's in-contest code and the three bugs in
  `4607.md`; 1485 K, 2575 B, 2524 A) and the geometry library;
  constructive re-solves; and the heavy re-solve 2661 B (his 169-minute chain).
- **All three:** the observation block (2575 I, 4071 A, 4071 N) and the checklist drills. A
  specialist still has to be able to solve the easy and greedy problems in every category.

**Risk:** specialisation must not recreate the solo stalls of §5. The 2-WA and 45-minute rules
still apply to owners: an owner stuck on their own category hands it to the backup for a cold read.

## 7. Open questions (answers would sharpen the per-member picture)
- **Members for 1051, 1485, 2513, 2524 and 2575** (31 solves), and for 4071 F and M.
- 4071 A (Dedi's 4 wrong, then Erdene AC) and 4113 A (3 wrong, member not recorded): wrong idea or
  implementation? Is that account's code recoverable anywhere?
- **Tamir at 4593 and 1799:** what was he working on (no recorded solve)?
- In the silent finishes (1051, 1799, 2513, 4593, 2693, 1096, 1485): was the field's next problem
  read, and by whom?
