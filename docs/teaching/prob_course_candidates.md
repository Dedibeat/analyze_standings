# Probability-course candidates (2026-11-06)

Problems for a probability course, picked from the 41 problems in
`data/tagged.json` tagged `probabilities`, `probability`, `expected-value` or
`linearity-of-expectation` (primary, secondary or extra tags; deduplicated by
problem URL).

Rules for a pick:
- **Discrete probability only.** No uniform points in regions, no densities.
- **The core trick must survive on paper.** Once the CP layer (modular output,
  big constraints, data structures, DP over large states) is stripped, a math
  or probability problem with a hand-derivable answer must remain.

Each entry gives the core trick, a paper version and its answer. Every answer
below was checked by brute force against the problem's official samples.
Solve counts are from the contest board in `data/tagged.json`.

The full write-up, with clean statements and worked solutions for all nine
picks, is [prob_course_problems.tex](prob_course_problems.tex). It cuts each
problem to one question built on its trick, so some of its instances differ
from the paper versions below (Chopsticks uses 4+4+4 chopsticks, Orchard Fence
a regular n-gon).

## Main five (course order, easiest first)

### 1. Mingle
NAQ 2025 G · [QOJ](https://qoj.ac/contest/2554/problem/14443) · 10/27 solved
· topic: indicators.

**Trick.** Count rooms, not players: a winner is a room with exactly one
player. Exactly 2k+1 players can reach each room, each going there with
probability 1/(2k+1), independently.

**Paper version.** n players and n rooms sit on a circle (n ≥ 2k+1). Each
player independently walks to a uniformly random room within distance k of
their own. A player alone in a room wins. Find the expected number of winners,
and its limit per player as k → ∞.

**Answer.** n·(2k/(2k+1))^(2k); for n=3, k=1 it is 4/3. Per player the limit
is 1/e, the chance that a Poisson(1) variable equals 1. Follow-up: the variance
(needs pairs of rooms).

### 2. Accidental Arithmetic
Northwestern Europe 2025 A · [QOJ](https://qoj.ac/contest/2603/problem/14855)
· 52/75 solved · topic: linearity and symmetry.

**Trick.** Every term after the first gets + or − with equal probability,
independent of its digits, so its expected contribution is 0. Only the first
term counts.

**Paper version.** Type the digits of N = d₁…d_L. After each of the first L−1
digits, independently, a "+" is inserted with probability α, a "−" with
probability α, and nothing with probability 1−2α. Find the expected value of
the expression.

**Answer.** E = Σ_{l<L} 2α(1−2α)^(l−1)·P_l + (1−2α)^(L−1)·N, where P_l is the
number formed by the first l digits. N = 12345, α = 0.45 gives 5.4321.
Follow-up: with "+" at probability β and "−" at γ, each later term comes back
with weight (β−γ)/(β+γ), the mean of its sign.

### 3. 502 Bad Gateway
EC Online 2024 (II) L · [QOJ](https://qoj.ac/contest/1799/problem/9381) ·
1023/2614 solved · topic: geometric distribution, optimal stopping.

**Trick.** The best policy is a threshold (keep the timer iff t ≤ c), and the
number of resets is geometric: E(c) = (T−c)/c + (c+1)/2 = T/c + (c−1)/2,
smallest near c ≈ √(2T).

**Paper version.** A timer starts at a uniform value in {1,…,T} and counts down
each second. While it is nonzero you may reset it to a fresh uniform value,
losing the second already spent. Find the best strategy and the smallest
expected wait.

**Answer.** E* = min_c [T/c + (c−1)/2]: 2 for T=3, 4 for T=10, 398/9 for
T=1000 (c=45); about √(2T) − ½ for large T. Optimality: with V the optimal
value after a fresh draw, keep t exactly when t ≤ 1+V.

### 4. Uniform Chemistry
SWERC 2022 B · [QOJ](https://qoj.ac/contest/1123/problem/5646) · 78/157
solved · topic: Markov chains, records, random permutations.

**Trick.** The jump chain visits each intermediate element j independently,
with probability 1/(n−j+1). So T = 1 + Σ_{i=2}^{n−a} Bernoulli(1/i): the
number of cycles of a random permutation of n−a elements.

**Paper version.** Start at element a. Each step, jump to a uniform element of
{x+1,…,n}; T is the number of steps to reach n.
- (a) Show P(j is visited) = 1/(n−j+1) and that these events are independent.
  Hint: the first jump into {j,…,n} lands uniformly there.
- (b) Find E[T] and Var T.
- (c) Show P(T=t) = c(n−a, t)/(n−a)!, with c the unsigned Stirling numbers of
  the first kind.
- (d) Three researchers start at 1 with n=3. A researcher wins if nobody
  reaches n strictly earlier. Find P(a given researcher wins).

**Answers.** E[T] = H_{n−a}; Var T = H_{n−a} − H⁽²⁾_{n−a}; (d) 5/8.

### 5. Jinx or Jackpot
NERC 2025 J · [QOJ](https://qoj.ac/contest/2785/problem/15902) · 42/343 solved
· topic: Bayes' rule, value of information.

**Trick.** The value scales linearly with the bankroll, so every bet is 0 or
all-in. A bet of 0 still shows the outcome (free information). The unknown p
is updated by Bayes' rule over a finite prior.

**Paper version.** A machine's win probability p is 0.7 or 0.3, each with
prior ½. You have $1000 and 2 rounds; each round you bet any amount up to your
balance at even odds. Maximise the expected final wealth.

**Answer.** Go all-in in round 1 even though the bet is fair (p̂ = ½): a win
raises p̂ to 0.58, so go all-in again. Expected profit $160; watching round 1
first earns only $80. Second exercise: known p = 0.61 and 5 rounds gives
all-in every round, profit 1000·(1.22⁵ − 1) ≈ $1702.71.

## Backups

### Orchard Fence
Mid-Atlantic USA 2025 A in the repo (statement footer: Southeast USA D1) ·
[QOJ](https://qoj.ac/contest/3502/problem/16814) · 3/163 solved · topic:
linearity over edges.

**Trick.** The fence is the hull perimeter of the kept centres plus πd. By
linearity over directed edges, i→j is a hull edge with probability
C(n−2−r, k−2)/C(n,k), where r is the number of points strictly to its right
(general position).

**Paper version.** Keep 3 random vertices of a regular hexagon with side 1.
Find the expected perimeter of the triangle.

**Answer.** (12 + 6√3)/5 ≈ 4.478 (6 ear triangles, 2 equilateral, 12 others).

### Chopsticks
Taiwan 2025 H · [QOJ](https://qoj.ac/contest/2621/problem/15121) · 2/241
solved · topic: parity, indicators.

**Trick.** The number of mismatched pairs is (number of types drawn an odd
number of times)/2, so E = ½ Σ P(Xᵢ odd), using P(odd) = (1 − E[(−1)^X])/2.

**Paper version.** An urn has 8 red and 8 blue chopsticks. Draw 10 and pair
them to maximise same-colour pairs. Find the expected number of mixed pairs.

**Answer.** 72/143. With replacement, P(odd) = (1 − (1−2p)^(2n))/2.

### Crashing Competition Computer
Northwestern Europe 2022 C · [QOJ](https://qoj.ac/contest/1044/problem/5127)
· 20/54 solved · topic: consecutive successes, convexity.

**Trick.** Typing a block of k characters from a save costs
(q^(−k) − 1)(1/p + r) + t, with q = 1−p. This is convex in k, so equal-length
blocks are optimal; only the number of saves is left to choose.

**Paper version.** Type c=3 characters; each keystroke crashes with
probability p=½, recovery costs r=2, a save costs t=5, and the code must be
saved at the end. Find the minimal expected time.

**Answer.** 26, with blocks of 2 and 1 (one block: 33; three blocks: 27).

### Disbursement on Quarantine Policy
Taiwan 2024 D · [QOJ](https://qoj.ac/contest/2622/problem/15129) · 65/203
solved · topic: linearity, complements.

**Trick.** Linearity over seats. For a seat with e unknown edge-neighbours and
c unknown corner-neighbours (no known infections nearby), the expected cost is
d₀/2 + d₁·½(1 − 2^(−e)) + d₂·½·2^(−e)(1 − 2^(−c)).

**Paper version.** A 3×3 grid of seats, each infected independently with
probability ½. Infected: 4 days; healthy with an infected edge-neighbour: 2
days; healthy with only an infected corner-neighbour: 1 day. Find the expected
total.

**Answer.** 13263/512 ≈ 25.90.

## Left out

- **Continuous probability:** Computational Intelligence, Military Maneuver,
  Prism Palace, Garden of Thorns, Mouse Trap, Innovative Washing Machine,
  Honkai Stress Relief, Minimum Manhattan Distance.
- **Interactive:** Isaac's Queries, Eight-Connected Figures.
- **Large optimal-play or bitmask DPs:** Rivals, Seven Up, Metro Quiz, Draw
  Your Deck, Divisor Card Game, Play It by Ear, Erratic Lights.
- **Graph algorithms with a one-line probability step:** Kruidnoten, Cosmic
  Commute, Information Spread.
