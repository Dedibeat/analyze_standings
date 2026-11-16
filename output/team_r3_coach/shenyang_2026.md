# Shenyang 2026 — 51st ICPC Shenyang regional, onsite, 2026-11-15

The first onsite contest of the season, so the first real measurement after 14 virtuals.

Sources and limits:
- **Board:** XCPCIO `icpc/51st/shenyang`, 401 official teams, with every team's runs. Read with
  `scripts/team_r3_onsite.py /icpc/51st/shenyang`. Minutes are contest minutes; penalty is the
  board's (seconds summed, 20 minutes per wrong run before the AC).
- **Members and the story of the contest:** Dedi's account (2026-11-16). Tamir and Erdene have not
  given theirs.
- **Statements:** Dedi's photos of the Chinese statements of A, C, D, F, H, J and L (2026-11-16).
  H's second page (output format and samples) and the pages of B, E, G, I, K and M were not
  sent. The photos are not in the repo; each problem below starts with what the statement asks.
- **No editorial and none of our code.** The ideas below are the coach's own solutions. Each is
  checked against a brute force and the statement's samples in `shenyang_2026_checks.py`; where
  only part of a solution is checked, the problem's section says so.
- `members_solved.csv` has no Shenyang 2026 rows: `team_r3_participations.py` needs a QOJ contest
  id in the sheet's contest name, and the set has none yet.

**Result:** 5 solved (C D H J L), 647 min, **#87 / 401, a silver medal** (40 gold, 80 silver,
120 bronze: silver is #41–#120). **Members: Dedi L, C, J; Tamir D, H; Erdene none.**

## Lines (official board)

| line | rank | scoreline | set |
|---|---|---|---|
| last gold | #40 | 7 / 1169 | ACDFHJL |
| six solves | #44–#62 | | ACDHJL ×8, CDFHJL ×7, ACDFHL ×4 |
| 2026 EC-Final estimate (~81, range 77–84; re-estimated 2026-11-16 from the five finished sites, was ~75) | #81 | 5 / 604 | CDHJL |
| **us** | **#87** | **5 / 647** | CDHJL |
| last silver | #120 | 4 / 328 | CDHL |
| last bronze | #240 | 3 / 222 | DHL |

- **Six ranks and 43 minutes outside the EC-Final estimate.** The estimate was re-made on
  2026-11-16 (`scripts/ecfinal_cutoff_2026.py`, details.md): the seat rule replayed on the five
  finished sites, plus what Shanghai and Nanchang should add, puts the last seat at rank ~81
  (77–84). A seat at #87 needs those two sites to admit at most 10 new teams within their top 86;
  the smallest such number in 2023–2025 is 18. So a direct seat from Shenyang is unlikely. The
  real answer comes after Nanchang (12-19).
- **Gold needed 7 problems** (32 of the 33 seven-solvers had ACDFHJL). Gold was never in reach;
  the 6th problem (A or F) was worth #58 at the latest minute.
- **J made the medal silver.** With four problems we were 4 / 393 = #139, a bronze.
- We solved the field's standard set for our count (CDHJL: 33 of the 44 five-solvers), as in the
  virtuals.

## Timeline

| min | event | rank after |
|---|---|---|
| 11.1 | L AC (Dedi), first try | #91 |
| 64.7 | D AC (Tamir), first try | #96 |
| 129.6 | C AC (Dedi), first try. Erdene had it first and did not see the DP | #129 |
| 138.1 | H WA (Tamir) | |
| 167.7 | H AC (Tamir) | #106 |
| 168.4 | H AC again, 43 seconds later (a second submission of an accepted problem) | |
| 253.9 | J AC (Dedi, with Erdene debugging), first try. Erdene had it first and did not see the offline segment tree | #73 |
| 295.8 | F WA (not solved; who submitted is not recorded) | final #87 |

- 60 minutes after the start we still had one problem (#191 at that moment).
- From 168' to 254' there was no submission: Dedi and Erdene were on J, and F was open.
- Dedi asked Erdene to take F with Tamir. By Dedi's account Erdene had lost confidence after C
  and J and stayed on J with him.

## Against the field

Median solve minute among the teams of each medal tier that solved the problem (count in
brackets), and the share of solvers who got it first try.

| problem | solved / tried | first try | gold | silver | bronze | ours |
|---|---|---|---|---|---|---|
| L | 398 / 401 | 79% | 10 (40) | 12 (80) | 14 (120) | 11.1, first try |
| D | 387 / 399 | **17%** | 41 (40) | 51 (80) | 62 (120) | 64.7, first try |
| H | 357 / 381 | 61% | 83 (40) | 105 (80) | 131 (120) | **167.7, +1** |
| C | 229 / 319 | 62% | 60 (40) | 112 (80) | 197 (105) | 129.6, first try |
| J | 93 / 188 | 45% | 131 (40) | 251 (51) | 243 (2) | 253.9, first try |
| F | 60 / 124 | 47% | 146 (40) | 215 (20) | — | 1 wrong run at 295.8 |
| A | 59 / 81 | 51% | 184 (40) | 229 (19) | — | not submitted |

B, E, I, M: 3–6 solves each; G, K: none. Correct skips.

The 33 teams that finished with the same five problems:

| | the 33 CDHJL teams (median) | us |
|---|---|---|
| C, D, H, L all done | 143' | 168' |
| J accepted | 253' | 254' |
| wrong runs on solved problems | 4 | **1** |

## Problems

### L. Picky Editor I — field 398/401 — **AC 11', first try** (Dedi)
- **Statement:** a string starts empty. A letter is appended only if the result has no palindromic
  substring of length ≥ 2; `-` deletes the last character. Print the final string. Σ length ≤ 10^6.
- **Idea:** a string has a palindrome of length ≥ 2 exactly when it has one of length 2 or 3. So
  keep a stack and accept a letter if it differs from the top two characters. Tags: strings, stack.
- **Ours:** on pace (gold median 10').

### D. Prefix Extremes — field 387/399, **17% first try** — **AC 65', first try** (Tamir)
- **Statement:** among the permutations of 1..n with exactly a prefix maxima and b prefix minima
  (position 1 is both), print the k-th element of the lexicographically largest, or −1.
  n ≤ 10^9, T ≤ 10^5.
- **Idea:** every position after the first is at most one of the two, so a + b − 1 ≤ n; and for
  n ≥ 2 the second position is always one of them, so a = b = 1 only works for n = 1.
  - a, b ≥ 2: p = [n−a+1, n−a+2, …, n], then the values 1..n−a with exactly b−1 prefix minima,
    largest first: m, m−1, …, m−b+3, then 1, then m−b+2, …, 2 (m = n−a).
  - a = 1: the same with p1 = n.
  - **b = 1:** nothing may be smaller than p1, so p1 = 1, then n−a+2, …, n, then n−a+1, …, 2.
  - Tags: constructive, casework. Checked against all permutations for n ≤ 7.
- **Why the field failed it:** the b = 1 and a = b = 1 cases. 83% of the solvers needed more than
  one run (1.8 wrong runs per solver).
- **Ours:** first try on the set's trap problem. This is Tamir's profile (careful, constructive).
  14 minutes behind the silver median.

### H. Perfect Puzzle — field 357/381 — **AC 168' after 1 WA** (Tamir)
- **Statement:** n ≤ 9. n non-attacking rooks are given, one per colour. Colour the n × n board
  with n colours so that each colour is a 4-connected region convex in rows and in columns, each
  rook stands on its own colour, and the given placement is the only way to put one rook on each
  colour without attacks. (Second page not seen.)
- **Idea** (mine; any valid colouring should be accepted): let the rook of row x stand at column
  π(x). A cell (x, y) with y ≥ π(x) takes colour x. Any other cell copies the nearest row below
  whose rook is at a column ≤ y, or, if there is none, the nearest such row above.
  - Shape: region x is row x from the rook to the right edge, a shrinking staircase above it, and
    a rectangle below it.
  - Uniqueness: every region lies in columns ≥ its rook's column, and in the rook's own column
    its other cells are in rows of rooks further right. So the rooks are forced one by one from
    the rightmost column to the left.
  - Tags: constructive with a uniqueness proof. Checked for every permutation up to n = 7 (shape
    rules and a full count of rook placements).
- **Ours:** the third-easiest problem by solves, accepted later than the bronze median (131').
  Tamir solved D first and H after it; H's first run came 73 minutes after D's AC. The wrong run
  and its 30-minute fix are not explained (open questions).

### C. Cache or Not — field 229/319 — **AC 130', first try** (Dedi; Erdene first)
- **Statement:** an LRU cache holds two addresses. For each of n requests (addresses 1..m,
  m ≤ 500, Σn ≤ 10^5) choose a direct access (cost A, cache untouched) or a cache access (hit B,
  miss C ≥ B, the address becomes the most recent). Minimise the total.
- **Idea:** the cache is the ordered pair (most recent, least recent): m² states, too many to
  update per request. But a direct access adds A to every state (one lazy offset), and a cache
  access with address v only creates states whose most recent address is v. So each request
  rewrites one row: f[v][w] = min(f[v][w] + B, f[w][v] + B, min_y f[w][y] + C), with a row
  minimum kept per row. O(n·m). Tags: DP, state design. Checked against a full-state DP.
- **Ours:** Erdene did not find the DP; Dedi took it over and it went in first try, 18 minutes
  behind the silver median. This is the problem type the Codeforces review named as Erdene's wall
  (DP state design: 2174 B, 2190 B2 in `cf_rounds.md`).

### J. Sirius I — field 93/188 — **AC 254', first try** (Dedi, Erdene debugging; Erdene first)
- **Statement:** distinct m-bit numbers (m ≤ 60). For a permutation p of the bit positions,
  sort by comparing bits in the order p. A value is *anchored* in a set if its rank is the same
  for all m! orders. q ≤ 2·10^5 queries: how many anchored values in a[l..r]?
- **Idea:**
  - Lemma: x is anchored exactly when every other value is a submask or a supermask of x. (Put
    x's one-bits first, then its zero-bits first: the two ranks differ by the number of values
    incomparable with x.)
  - Popcount form: x must be the only value of its popcount, contain the OR of the values with a
    smaller popcount, and be contained in the AND of those with a larger one.
  - Offline: for each i find the nearest incomparable value on each side. Insert values in
    increasing popcount into an OR segment tree and descend to the nearest position whose value
    is not inside a_i; the same with an AND tree in decreasing popcount; the nearest value of the
    same popcount is incomparable too. Then i counts for (l, r) when L_i < l ≤ i ≤ r < R_i, a
    sweep with a Fenwick tree.
  - Tags: bits, offline data structures. Checked: the lemma and the popcount form against all
    permutations (m ≤ 5). The segment-tree part is not implemented here.
- **Ours:** on the silver median (251'), first try where 45% of the solvers were. After C, D, H, L
  the same-set teams needed 89 minutes for J; we needed 86.

### F. MEX Deletion — field 60/124 — **1 wrong run at 296', not solved**
- **Statement:** a sorted array and d. Delete any chosen set at cost mex of {⌊(a_r − a_l)/d⌋}
  over its pairs (l = r included, so the cost is ≥ 1). Minimise the total cost of deleting
  everything. n ≤ 2·10^5.
- **Idea:** the answer is 1, 2 or 3.
  - Three is always enough: put a value in block ⌊a/d⌋ and take the blocks by index mod 3. Inside
    one class every difference is < d or ≥ 2d, so each class costs 1.
  - 1 if no pair has d ≤ difference < 2d.
  - 2 if no pair has 2d ≤ difference < 3d (one operation of cost 2), or if the graph of pairs
    with d ≤ difference < 2d is bipartite (two operations of cost 1).
  - The bipartite test at n = 2·10^5: each value's neighbours are one window [v+d, v+2d), all of
    which must share a colour. Union each window with a next-pointer DSU, then one parity edge
    per value.
  - Tags: observation, graphs / DSU. Checked against all partitions for n ≤ 8, with a plain
    graph search for the bipartite test.
- **Ours:** one run 4 minutes before the end. Whose run and what idea is not recorded.

### A. Minimalism — field 59/81 — not submitted
- **Statement:** n is given by its factorisation (≤ 15 primes, n ≤ 9·10^18). Number n's divisors
  1, 2, … in increasing order. Count the m ≤ n for which the numbers of the divisors of n that
  divide m form an arithmetic progression.
- **Idea:** those divisors are the divisors of g = gcd(m, n), so the answer is Σ φ(n/g) over the
  good divisors g. The numbering starts at 1, so with step s the divisors of g must be a prefix of
  D[1], D[1+s], D[1+2s], …, where s is fixed by g's smallest prime. Walk that sequence once per
  prime of n: a prefix is good when its lcm is its last element and that element has exactly as
  many divisors as the prefix is long. At most 15 walks over ≤ 153,600 divisors.
  Tags: number theory. Checked against a direct count for n < 2500 and both samples, including
  the 19-digit one.
- **Missed?** Yes, as much as F: the same number of solves, and a better conversion (59 of the
  81 teams that tried it, against 60 of 124). It is Dedi's category (number theory), and he was
  on J until 254'.

### B, E, G, I, K, M — statements not seen
3–6 solves each for B, E, I, M and none for G, K. Correct skips for a five- or six-solve team.

## What the board says

1. **This was our cleanest contest, and Dedi's cleanest.** One penalised wrong run in five solves;
   the virtuals averaged 4.9 per contest (68 in 14). Dedi: three solves, three first tries,
   including the two hardest we solved. The teams around us made four wrong runs. D went in first
   try (Tamir) where 83% of its solvers needed more than one run.
2. **We lost on speed, not on accuracy.** Against the gold medians we were ×1.6 on D, ×2.2 on C,
   ×2.0 on H and ×1.9 on J. The virtuals ran at ×1.3–1.9. This repeats the official online rounds
   ("more careful but much slower", summary §5) and confirms that the virtual results were an upper
   bound: #87 of 401 is the 22nd percentile, the same as the Xi'an 2026 virtual (#86 / 402) and
   twice the Chengdu virtual (#35 / 319).
3. **H is the gap to the EC-Final estimate, and it waited behind D.** Tamir solved the two
   constructive problems one after the other: D at 65', then H with a first run at 138' and the AC
   at 168'. H was the third-easiest problem (357 solves); half of its eventual solvers had it
   before our first run, and our AC was later than the bronze median (131').
   - H first try at 138' → 5 / 598 → **#81, the estimated last seat**.
   - H clean at the silver median (105') → 5 / 565 → #75.
   - Two of the three easiest problems were on one member while the third member's problems
     (C, then J) produced no solve. That is the cost of the opening plan (next section), not a
     flaw in Tamir's work: his D was the cleanest solve of the contest.
4. **C and J were not slow by our tier's standard.** C at 130' is 18 minutes behind the silver
   median; J at 254' is on it. The two handovers from Erdene to Dedi both ended in a first-try AC.
5. **The 6th problem had one person on it.** A and F were equally solved (59 and 60), and the
   six-solvers split evenly between them. 21 of A's 59 solves and 10 of F's 60 came in the last
   hour. Our only run on either was F at 295.8'. By the specialisation in summary §6.5, F
   (observation, graph/DSU) was Erdene's and Tamir's and A (number theory) was Dedi's.
6. **Load.** Dedi 3 of 5 (L, C, J), Tamir 2 (D, H), **Erdene 0**. Dedi's overload is the pattern of
   4593, 1799, 4113 and 1053 (summary §4), now onsite. Erdene without a solve is new: he had 18
   solo solves in the virtuals, 4 of the 6 at Chengdu.

## The opening pattern: Erdene takes a hard problem early

The team's usual plan: Erdene gets a harder problem early while Dedi and Tamir clear the rest.
Dedi credits it for the Chengdu virtual (59 minutes from gold).

- **What Chengdu actually shows.** Erdene's four solves there were the two easiest problems (M, D)
  and the two interactive/communication problems (I, H): his best category, 3 of 3 first try over
  the season. The plan worked because the mid problems were his type, and because he also took
  the opening.
- **Shenyang's mid problems were not his type.**
  - C is DP state design, his wall on Codeforces.
  - J needs a submask lemma before any data structure. Bits are Dedi's strength and, by the
    Codeforces review, a weak spot of the other two. The plan in summary §6.5 made Erdene the
    data-structure owner on the evidence of one problem (2693 L); J is the first evidence
    against that, though the blocker may have been the lemma and not the tree.
- **Here the plan cost twice.** His two problems gave no solve, and the easy problems he usually
  opens (Chengdu M at 23') went to Tamir one after the other, which is where H's 63 minutes went.
- **The weak point is not the miss, it is the missing clock.** A plan that rests on one member
  hitting needs a fixed moment at which the problem is explained aloud and handed over. Rule 3 of
  §6.3 has it (25 minutes without a submission → a second reader; 45 minutes stuck → switch).
  When C and J changed hands is not known (open questions).
- **After a miss he stops attempting.** This is the same behaviour as in his Codeforces data: he
  attempted the field's next problem in 2 of 21 rounds, and 32 of 63 virtuals have no submission
  after half-time. So it is a habit to train, not a one-off. Asking him to start a third problem
  cold after two misses was the hardest thing to ask for; that he stayed on J is understandable.
- **Staying on J was not the loss.** A second reader on the last open problem is the rule in §6.5,
  and J went in first try. The loss was that A/F had one person from 168' on.
- **Dedi's call (Erdene and Tamir on F) was the right one by the board and by the split.** It
  needs to be a standing rule, so that nobody has to be persuaded in the fourth hour.
- **One contest.** Of the contests with member data, this is the first Erdene played without a
  solve, after 18 solo solves. It changes the plan, not the assessment of him as the strongest
  individual.

## Health

Dedi had an allergic reaction to an insect bite in Shenyang: a hormonal injection, then ebastine
in the morning and bismuth potassium citrate in the evening. Tamir was bitten after the contest.
- The board shows no sign of it in Dedi's work (three first-try solves), but thinking speed cannot
  be read from a board, so the effect is unknown.
- For Hong Kong: finish the course as prescribed, ask the doctor whether to carry an antihistamine,
  and pack repellent. This is a travel checklist item, not a coaching finding.

## What changes for Hong Kong (HKU, 2027-01-09/10 by the notice; an EC-Final place needs about rank 21–25, re-estimated 2026-11-16; was 32–37)

Keep: the opening (first AC at 11'), the pre-submit checklist (1 wrong run), a second reader on
Dedi's last problem.

1. **Erdene opens with the easy problems again**, as at Chengdu. A harder problem goes to him
   only when it is his type (interactive, structure) or when the easy ones are done.
2. **Assign mid problems by type, with a clock.** The owner of the category takes it. At 30
   minutes without a solution he can state in two sentences, he explains the problem to a
   teammate; at 45 minutes it changes hands.
3. **No two easy problems queued on one member.** If a member holds a second unsolved problem with
   more than half the field's solves, a free teammate takes it.
4. **Two on the next problem while the closer codes.** From the moment Dedi starts the last
   standard problem, Tamir and Erdene pair on the field's next one (most-solved on the board, then
   best conversion). One of them reads Dedi's diff before each run, for at most 15 minutes.
5. **Erdene after a miss:** a fixed next job, so that a miss is not the end of his contest: first
   the cold read for the closer, then the next problem with Tamir. In training: every virtual
   played to the end, and a submission on the field's next problem in every round (already in
   summary §6.4; now his first item).
6. **Speed on the easy-mid problems is the main training target**, ahead of new topics: it is
   what separated #87 from the EC-Final line here. All virtuals on one computer, as onsite.
7. **Upsolve this set first, from scratch and timed:**
   - Erdene: C (write the state and the one-row update before coding), then J (prove the lemma,
     then the offline version).
   - Erdene and Tamir together: F.
   - Dedi: A.
   - Tamir: H, until the wrong run is explained; then D's case list from memory.
8. **Topic weeks** (summary §6.1) stay, with two additions for Erdene: DP state design (start
   from C and his own 2174 B, 2190 B2) and submask / bit arguments (Dedi teaches, as planned in
   §6.5).
9. **Incentive seat.** If the allocation after Nanchang leaves NUM without a seat, the rule lets a
   school apply for one of up to 10 incentive seats, judged on regional results (details.md
   2026-10-08). A silver at #87 is the result to cite. Deadline and form are not known here.

## Open questions

1. **The rest of the set:** H's second page, the pages of B, E, G, I, K, M, the editorial once it
   is out, and any onsite code that was saved.
2. **H:** when did Tamir start it? What was the wrong run, and why did the fix take 30 minutes?
   Who submitted the second AC at 168.4', and why?
3. **D:** was it 65' because of the case analysis, or because the keyboard was busy?
4. **Erdene:** when did he start C, and did he read D or H first? At what minute did C and then
   J move to Dedi? On J, was the blocker the submask lemma or the data structure?
5. **F at 295.8':** whose run, and what was the idea? Did anyone read A?
6. **Setup:** are the virtuals played on one computer? Who typed between 168' and 254'?
7. Tamir's and Erdene's own accounts of the contest.
