# Shenyang 2026 — 51st ICPC Shenyang regional, onsite, 2026-11-15

The first onsite contest of the season, so the first real measurement after 14 virtuals.

Sources and limits:
- **Board:** XCPCIO `icpc/51st/shenyang`, 401 official teams, with every team's runs. Read with
  `scripts/team_r3_onsite.py /icpc/51st/shenyang`. Minutes are contest minutes; penalty is the
  board's (seconds summed, 20 minutes per wrong run before the AC).
- **Members and the story of the contest:** Dedi's account (2026-11-16; who worked on F added
  2026-11-20). Tamir and Erdene have not given theirs.
- **Statements:** Dedi's photos of the Chinese statements of A, C, D, F, H, J and L (2026-11-16).
  H's second page (output format and samples) and the pages of B, E, G, I, K and M were not
  sent. The photos are not in the repo; each problem below starts with what the statement asks.
- **Our code (received 2026-11-20).** Six files were printed on the contest's print service:
  c, d, f, h, j and l.cpp. Dedi sent photos of the printouts.
  - They are transcribed into `data/team_r3/shenyang_2026/` with the printouts' line numbers.
  - The print stamps run from 13:15:47 to 13:19:18 in file-name order. The contest ran
    09:00–14:00 (UTC+8), so that is minutes 256–259, two minutes after J's AC (253.9'). This
    assumes the print server's clock is the contest clock.
  - So they are the files as they stood at 256–259': the final code of the five solved problems,
    and an F draft from 38 minutes before F's only run.
  - H's wrong run (138') and the F run (295.8') are not among them. H's wrong run is explained
    by Dedi's account (2026-11-20): a space between the characters of each output row.
  - `shenyang_2026_code_checks.py` runs each file against the references below.
- **No editorial.** The ideas below are the coach's own solutions. Each is checked against a
  brute force and the statement's samples in `shenyang_2026_checks.py`; where only part of a
  solution is checked, the problem's section says so.
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
| 138.1 | H WA (Tamir): the right grid, printed with a space between characters | |
| 167.7 | H AC (Tamir) | #106 |
| 168.4 | H AC again, 43 seconds later (a run after the first AC: no penalty, the board counts only the first AC) | |
| 253.9 | J AC (Dedi, with Erdene debugging), first try. Erdene had it first and did not see the offline segment tree | #73 |
| 255.8–259.3 | all six source files printed (c, d, f, h, j, l, in name order); F's file (Tamir's) is a greedy that fails sample 2 | |
| 295.8 | F WA (Tamir's run; by Dedi's recollection not the printed `f.cpp`) | final #87 |

- 60 minutes after the start we still had one problem (#191 at that moment).
- From 168' to 254' there was no submission. Dedi and Erdene were on J. Tamir was on F, working
  from Dedi's observation that the answer is at most 3 (Dedi, 2026-11-20).
- Before 168' (Dedi, 2026-11-20):
  - Erdene probably read A in the first 5 minutes and dropped it with no idea. That is Dedi's
    guess.
  - Dedi tried F after L (11') and before Erdene handed him C (C AC at 129.6'). The bound "the
    answer is at most 3" comes from then. When C changed hands is not known.
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
- **Code** (`l.cpp`, 34 lines): the stack and the two-character test, as above. It passes the five
  samples and 20,000 random strings.

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
- **Code** (`d.cpp`, 106 lines): casework in O(1) per query.
  - The first branch rejects a = 0, b = 0, a = b = 1 with n > 1, and a + b − 1 > n.
  - The second handles b = 1 (p1 = 1).
  - So both traps of the field are dealt with in the first 30 lines.
  - Checked: every (n ≤ 8, a, b ≤ n + 1, k) and 20,000 random cases up to n = 10^9 agree with the
    reference.
  - Two `y < 1` / `x < 1` guards can no longer trigger after the first check; they are harmless.

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
  Tamir solved D first and H after it; H's first run came 73 minutes after D's AC.
- **The wrong run was output format** (Dedi, 2026-11-20).
  - The 138' run printed a space between the characters of each row. Tamir noticed after about
    20 minutes, and the AC came 29.6 minutes after the wrong run.
  - So the idea and the code were right at 138'. The format slip cost 20 penalty minutes plus
    29.6 minutes of delay: **49.6 minutes on the scoreline**.
  - Without it: 5 / 598, **#81**, the estimated last EC-Final seat (range 77–84).
- **Code** (`h.cpp`, 80 lines, the accepted version). It uses a different construction from the
  idea above. It goes down the rows; in row i, with the rook at column c and colour x:
  - x spreads left and right in row i over empty cells that lie in the column of a rook from an
    earlier row;
  - x fills the empty cells of row i − 1 that are contiguous with column c;
  - at the end every empty cell takes the colour of the cell below it. The bottom row is always
    full by then.

  Checks and what the code adds:
  - It satisfies the shape and uniqueness conditions on all 5,913 boards with n ≤ 7 and on 600
    random boards with n = 8, 9.
  - It was accepted with a colouring other than the coach's. That agrees with the dossier's
    reading that any valid colouring is accepted, and with its conditions.
  - It gives H's format, which the missing second page holds: n, then an n × n grid with `.` for
    an empty cell and one character per rook; the output is the filled grid; one test per file.
  - Two commented lines (`char last;`, `last = x;`) are left from an earlier version that kept
    the previous row's colour. They have nothing to do with the wrong run, which was the
    output format.

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
- **Code** (`c.cpp`, 103 lines). It is the idea above: a `Table` with a lazy offset (`lift(A)`),
  one patched row per request, and the argmin of each row.
  - Row 0 is the empty slot.
  - Requests where the address is already the most recent also write the state (x, x). That state
    is always dominated by a real one (C ≥ B), so it does no harm.
  - Checked: the four samples, 4,000 random cases against the full-state brute force, and 30
    larger cases (m ≤ 40, costs up to 10^9) against the O(n·m) reference.

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
- **Code** (`j.cpp`, 194 lines). It is simpler than the popcount form above. The values are
  distinct, so a smaller value that is comparable with x must be a submask of x, and a larger one
  a supermask. So it goes by value instead of popcount:
  - In increasing order of value, it finds the widest window around each position in which the
    OR of the smaller values is inside x. This is a binary lifting from 2^20 down over an OR
    segment tree.
  - In decreasing order, it finds the widest window in which x is inside the AND of the larger
    values (an AND tree).
  - Position i counts for a query (l, r) when both l and r lie in the intersection of the two
    windows. The queries are answered offline by left end, with a sum segment tree over right
    ends.

  Checks and leftovers:
  - This is the part the dossier left unchecked. The code passes the sample, 1,500 small sets
    with every query against all m! orders, and 20 sets of 50–400 60-bit values (400 queries
    each) against the lemma.
  - An empty `if(x == 6) { //hha… }` block is left from debugging sample 1, which contains a 6.
    It is harmless.

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
- **Ours:** one run 4 minutes before the end. **Tamir worked on F, starting from Dedi's
  observation that the answer is at most 3** (Dedi, 2026-11-20). So the key bound was found in
  the contest. Dedi found it when he tried F himself, after L and before Erdene handed him C.
  That earlier attempt is why the team stayed on F. Tamir submitted the 295.8' run (Dedi,
  2026-11-20).
- **Code at 257'** (`f.cpp`, 44 lines, Tamir's, printed 38 minutes before the run): a greedy over
  chains.
  - It keeps a multiset of chain ends. Each value joins the chain with the lowest end that is
    less than d below it; if there is none, the chain with the highest end that is at least 2d
    below it; if there is none, it starts a new chain. It prints the number of chains.
  - **Wrong idea.** It checks only neighbours inside a chain, but the cost is the mex over all
    pairs. Sample 2 (d = 3: 1 3 4 6 6 8) becomes one chain, since every gap is < 3. Yet
    8 − 1 = 7 and 6 − 1 = 5 give the values 2 and 1, so that set costs 3. The greedy also never
    uses a set of cost 2.
  - With its debug lines removed it prints 2, 1, 1 on the samples (answers 2, 3, 1). It is wrong
    on 122 of 1,500 random small cases.
  - **Debug output left in.** As printed, it writes the multiset after every value (`print(st)`,
    18 extra lines on the samples).
  - **What was missing was the test, not the bound.** With the answer at most 3, F reduces to
    telling 1, 2 and 3 apart:
    - 1 needs no pair at all with d ≤ difference < 2d;
    - 2 is one set of cost 2 (no pair with 2d ≤ difference < 3d) or two sets of cost 1 (the
      graph of pairs with d ≤ difference < 2d is bipartite);
    - otherwise 3.
  - Read from the code, the greedy counts sets of cost 1, testing consecutive values only, and
    it has no branch for a single set of cost 2. At 257' it did not pass the samples.
  - Dedi thinks the 295.8' run was not this code. What it was is not known.

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
- **Erdene read A, probably in the first 5 minutes, and dropped it with no idea. The rest of the
  team did not hear about it** (Dedi, 2026-11-20; the minute is his guess).
  - Dropping it at minute 5 was reasonable: A's gold median is 184'.
  - The miss came later. A was never looked at again, and when the team chose its 6th problem
    it stayed on F because Dedi had tried F earlier.
  - The board favoured A: the same solves, better conversion (59 of 81 against 60 of 124), and
    Dedi's category. 38 teams had solved A by 240'.
- **Code:** none was printed. The six files came out in name order, which looks like a print of
  the whole folder. If so, nobody had started coding A by 256'.

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
   - H first try at 138' → 5 / 598 → **#81, the estimated last seat**. That run *was* correct
     apart from a space between characters (Dedi, 2026-11-20). So the format slip alone cost
     49.6 minutes, the whole margin to the line.
   - H clean at the silver median (105') → 5 / 565 → #75.
   - Two of the three easiest problems were on one member while the third member's problems
     (C, then J) produced no solve. That is the cost of the opening plan (next section), not a
     flaw in Tamir's work: his D was the cleanest solve of the contest.
4. **C and J were not slow by our tier's standard.** C at 130' is 18 minutes behind the silver
   median; J at 254' is on it. The two handovers from Erdene to Dedi both ended in a first-try AC.
5. **The 6th problem had one person on it.** A and F were equally solved (59 and 60), and the
   six-solvers split evenly between them. 21 of A's 59 solves and 10 of F's 60 came in the last
   hour. Our only run on either was F at 295.8'. By the specialisation in summary §6.5, F
   (observation, graph/DSU) was Erdene's and Tamir's and A (number theory) was Dedi's. F was
   Tamir's, from Dedi's bound ("What the code says", §4).
6. **Load.** Dedi 3 of 5 (L, C, J), Tamir 2 (D, H, then F unsolved), **Erdene 0**. Dedi's overload is the pattern of
   4593, 1799, 4113 and 1053 (summary §4), now onsite. Erdene without a solve is new: he had 18
   solo solves in the virtuals, 4 of the 6 at Chengdu.

## What the code says

The six printed files, run against brute forces in `shenyang_2026_code_checks.py` (~1 min):

| file | problem | result |
|---|---|---|
| `l.cpp` | L, AC | agrees on every test |
| `d.cpp` | D, AC | agrees on all n ≤ 8 and 20,000 random cases up to 10^9 |
| `c.cpp` | C, AC | agrees with the brute force and the O(n·m) reference |
| `h.cpp` | H, AC | valid and unique on all 5,913 boards n ≤ 7, 600 boards n = 8, 9 |
| `j.cpp` | J, AC | agrees with all m! orders (small) and with the lemma (60-bit) |
| `f.cpp` | F, draft at 257' | **fails sample 2**; wrong on 122 / 1,500 small cases; debug output on |

1. **The accepted code is clean.**
   - No debug output is left in the five accepted files: the leftovers are commented out, plus
     one empty `if` in J.
   - Each file is one idea, written once. This matches the single wrong run on the board.
2. **Twice our solution was simpler than the coach's.**
   - H uses a different colouring.
   - J goes by value instead of popcount, which removes the same-popcount case.
   - Both were found in the contest without an editorial. The ideas the team had were good. The
     time went elsewhere (board, §2–3).
3. **D shows why it was first try.** The two cases the field missed (b = 1; a = b = 1) are
   handled before anything else.
4. **F had the bound but not the test.**
   - Dedi found that the answer is at most 3, and Tamir built on it. The step from the bound to
     a decision (when 1, when 2) was never worked out.
   - At 257' Tamir's file held a greedy that fails the second sample. It checks neighbours, not
     all pairs, and it still printed its debug output.
   - There is no file for A. Erdene had read it, but it never reached the others.
   - So 43 minutes before the end neither 6th problem had a correct solution. F was the nearer
     one: the hard observation was done.
   - The idea went from one member to another as a bound, not as an algorithm. The coder then
     had to invent the rest alone, and a greedy was the result.
   - By the bug classes of summary §3 the draft is an **unproven idea** plus **debug leftovers**.
     Checklist items (g), (h) and (i) of §6.3 each catch it: no debug output, samples run, a
     greedy compared with a brute force. The brute force over all partitions is 20 lines for
     n ≤ 8.
   - Dedi thinks the 295.8' run was not this draft, so what that run contained is not known.
5. **Not in the printouts:** H's 138' wrong run, H's second accepted run at 168.4', and the F run
   at 295.8'. The board's run data does not include code.
   - H's wrong run is now explained by Dedi's account: spaces between the characters of each row.
   - The 168.4' run cost nothing: runs after the first AC do not count.
   - The F run was Tamir's. Its code stays unknown.

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
- **Dedi was not on the easy problems either.** After L (11') he tried F, a problem only 60
  of 401 teams solved, until Erdene handed him C (Dedi, 2026-11-20).
  - So in the opening both other members were on hard or mid problems.
  - Meanwhile H, solved by 357 teams, waited behind D on Tamir.
  - The F attempt did produce the bound used later, so it was not wasted.
  - Hong Kong rule 3 is about exactly this: the free member takes the queued easy problem.
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
   - **An idea is handed over as an algorithm, not a fact.** When one member gives the idea and
     another codes it, the giver states what to compute for each case (for F: when the answer is
     1, when it is 2, otherwise 3). Both check it by hand on the samples before typing starts.
     If the giver has only a bound, the two work out the rest together. F was handed over as
     "the answer is at most 3", and the coder filled the gap with a greedy.
5. **Erdene after a miss:** a fixed next job, so that a miss is not the end of his contest: first
   the cold read for the closer, then the next problem with Tamir. In training: every virtual
   played to the end, and a submission on the field's next problem in every round (already in
   summary §6.4; now his first item).
6. **Speed on the easy-mid problems is the main training target**, ahead of new topics: it is
   what separated #87 from the EC-Final line here. All virtuals on one computer, as onsite.
7. **Upsolve this set first, from scratch and timed:**
   - Erdene: C (write the state and the one-row update before coding), then J (prove the lemma,
     then the offline version).
   - Tamir, with Erdene: F. Keep the bound. Write the all-partitions brute force first, then
     find the tests for 1 and 2. Then see why the 257' greedy prints 1 on sample 2.
   - Dedi: A.
   - Tamir: D's case list from memory. H needs no upsolve: the wrong run was the output format
     (item 10).
   - J is solved; compare `j.cpp` (value order) with the popcount version above. It is short
     material for the submask block in item 8.
8. **Topic weeks** (summary §6.1) stay, with two additions for Erdene: DP state design (start
   from C and his own 2174 B, 2190 B2) and submask / bit arguments (Dedi teaches, as planned in
   §6.5).
9. **Incentive seat.** If the allocation after Nanchang leaves NUM without a seat, the rule lets a
   school apply for one of up to 10 incentive seats, judged on regional results (details.md
   2026-10-08). A silver at #87 is the result to cite. Deadline and form are not known here.
10. **Samples are compared with `diff`, not by eye.** Set up a one-line check at the start
    (`./h < 1.in | diff - 1.out`). After any wrong run, the first two minutes go to the
    output format against the sample, before any search for a logic bug. H lost 49.6 minutes
    to a space between characters, the whole margin to the EC-Final estimate. That is item (h)
    of the checklist in summary §6.3, already learned from 1096 L.
11. **Every problem read is reported aloud,** in two lines: what it asks, and a first idea or
    "no idea". "No idea" is worth saying too: it hands the problem to the member whose
    category it is. The 6th problem is chosen from those reports by the board (solves, then
    conversion), not by who started it first. A problem dropped in the first minutes is
    re-read at that point if the board says it is solvable.
    - At Shenyang Erdene read A in the first minutes, had no idea, and it never reached the
      team. A is number theory, Dedi's category.
    - The team stayed on F because Dedi had tried it early, although the board favoured A.

## Open questions

1. **The rest of the set:**
   - the pages of B, E, G, I, K and M, and the editorial once it is out;
   - H's second page (its format is now known from `h.cpp`, its samples are not).
   - The saved code arrived on 2026-11-20 (six files, above).
2. **H:** when did Tamir start it? (Answered: the wrong run was spaces in the output, noticed
   after about 20 minutes. The 168.4' resubmission cost nothing.)
3. **D:** was it 65' because of the case analysis, or because the keyboard was busy?
4. **Erdene:** when did he start C, and did he read D or H first? At what minute did C and then
   J move to Dedi? On J, was the blocker the submask lemma or the data structure?
5. **F at 295.8':** answered on 2026-11-20:
   - Tamir wrote the chain greedy in `f.cpp` from Dedi's bound, and Tamir submitted the run.
   - Dedi thinks the run was not the printed `f.cpp`, and does not know its idea.
   - Erdene read A probably in the first 5 minutes, had no idea, and the team did not hear
     about it.
   - Dedi tried F between L (11') and the C handover.

   Still open: what idea the run used, and whether its samples were run. Only Tamir can say
   (question 7).
6. **Setup:** are the virtuals played on one computer? Who typed between 168' and 254'?
7. Tamir's and Erdene's own accounts of the contest.
