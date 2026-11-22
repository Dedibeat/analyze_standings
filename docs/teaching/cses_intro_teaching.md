# CSES Introductory Problems for a general audience

Reviewed 2026-11-09 against the official
[CSES problem list](https://cses.fi/problemset/). This continues the general-
audience selection in [the Codeforces notes](cf_div2_teaching.md). The scope
here is specifically **Introductory Problems**, including the newer tasks in
that section. Rankings below are teaching judgments. Proofs are independent
derivations from the linked statements; examples are explanatory examples.

## Recommended selection

| Role | Official problem | Main teaching idea |
|---|---|---|
| Best first greedy proof | [Increasing Array](https://cses.fi/problemset/task/1094) | Every chosen value is forced to be at least the prefix maximum |
| Cleanest surprising greedy | [Grid Coloring I](https://cses.fi/problemset/task/3311) | Four choices, at most three forbidden |
| Best greedy invariant | [Two Sets](https://cses.fi/problemset/task/1092) | Taking the largest affordable number preserves representability |
| Trickiest greedy follow-up | [String Reorder](https://cses.fi/problemset/task/1743) | Lexicographic greed needs a feasibility condition |
| Best first recursive decomposition | [Tower of Hanoi](https://cses.fi/problemset/task/2165) | Solve a smaller transfer twice; prove the lower bound too |
| Best recursive construction twist | [Gray Code](https://cses.fi/problemset/task/2205) | Reverse the second half to make the join work |
| Contrast exercise | [Apple Division](https://cses.fi/problemset/task/1623) | A plausible greedy fails; exhaustive search is feasible |

**Start with Increasing Array, Grid Coloring I, and Tower of Hanoi.**
Add Two Sets to teach an invariant, String Reorder for a stronger audience,
and Gray Code after learners understand recursion.

If “DC” means divide and conquer, Hanoi and Gray Code teach recursive
construction from smaller instances. They are not balanced, independent-half
examples like merge sort: Hanoi has sequential subproblems, and reflected
Gray Code reuses one smaller construction. Make that distinction explicit.

For a **first DP lesson**, I would use a problem from the separate Dynamic
Programming section. Apple Division can be formulated with reachable-sum
states, but its weights reach 10^9, so a DP array indexed by total weight is
not suitable for the official constraints. Do not label ordinary recursive
enumeration as an efficient DP merely to fill the category.

## 1. Increasing Array: the minimum is forced

**Rules.** Increase individual entries by 1 until the array is nondecreasing;
minimize the number of increments. Equal neighbors are permitted despite the
title's use of “increasing.”

**Algorithm.** Keep the largest original value seen so far, `M`. At each
position, update `M = max(M, a_i)` and add `M-a_i` to the answer.

**Proof.** Let `b` be any feasible final array. For every `j <= i`, increments
imply `b_j >= a_j`, and nondecreasing order implies `b_i >= b_j`.
Consequently `b_i >= max(a_1,...,a_i)`. Summing `b_i-a_i` gives a lower bound
on the number of increments in every solution. Setting each `b_i` equal to
that prefix maximum is feasible and attains the bound at every position.
It is therefore optimal.

**Trap.** Compare with the previous **modified** value, not merely the previous
original value. On `[5,1,2]`, the optimum is `[5,5,5]`, costing 7.
**Prompt.** “Once a 5 appears, how small can any later value be?”
**Cost.** O(n) time and O(1) auxiliary space. Use a 64-bit total.

## 2. Grid Coloring I: a greedy choice can always be extended

**Rules.** Every cell initially contains A, B, C, or D. Change every cell's
letter, and make letters different across every shared horizontal or vertical
edge. Any valid grid is accepted.

**Algorithm.** Visit cells row by row, left to right. Choose any letter other
than (1) this cell's original letter, (2) its upper neighbor's new letter,
and (3) its left neighbor's new letter. Ignore a missing neighbor at a boundary.

**Proof of existence.** There are four available letters and at most three
forbidden letters. Thus a choice always exists, regardless of earlier choices.

**Proof of correctness.** Each assigned cell differs from its own original
letter. For each grid edge, its later-visited endpoint explicitly avoids the
letter of its earlier-visited endpoint. Therefore every edge is valid after
the scan. Neither endpoint changes again. This proves the complete output
satisfies both requirements, so IMPOSSIBLE is never necessary.

**Trap.** Trying to avoid all four neighbors before they have been assigned
adds unnecessary constraints. Assigning every cell the same alternative letter
fails the adjacency requirement.
**Prompt.** “How many letters can be forbidden when we reach this square?”
**Cost.** O(nm) time. Store and modify the grid in place, using O(1) auxiliary
space beyond the grid; streaming can instead use O(m) row storage.

## 3. Two Sets: why this subset-sum greedy works

**Rules.** Split the integers `1,...,n` into two groups of equal sum.

**Algorithm.** Let `S=n(n+1)/2`. If `S` is odd, answer NO. Otherwise set
`r=S/2` and consider `j=n,n-1,...,1`. Put `j` in the first group if `j <= r`,
subtracting it from `r`; otherwise put it in the second group.

**Proof.** Odd `S` is impossible because twice an integer is even. For even
`S`, prove the invariant that just before considering `j`,

```
0 <= r <= j(j+1)/2.
```

It holds initially. If `r >= j`, choosing `j` leaves
`0 <= r-j <= j(j-1)/2`, exactly the invariant for the next step.
If `r < j`, skipping `j` leaves `r <= j-1 <= j(j-1)/2` for `j >= 2`.
For `j=1`, the skip case has `r=0` directly. Thus after considering 1, the
residual is 0. The chosen group sums to `S/2`, and its complement does too.

**Trap.** This is not a general subset-sum algorithm. The invariant uses
having *all* integers from 1 through `j` available. With available numbers
`[2,3,4]` and target 5, taking 4 first fails although `2+3` works.
**Prompt.** “After taking this number, can the smaller numbers still cover
what remains?”
**Cost.** O(n) time and O(n) space to collect the two output groups; 64-bit
arithmetic is needed for `S` at the official limit `n=10^6`.

## 4. String Reorder: the trickiest, with a precise feasibility proof

**Rules.** Rearrange uppercase letters to avoid equal adjacent letters.
Among valid answers, output the lexicographically smallest; if none exists,
output -1. Lexicographic order compares the first position at which two strings
differ, using A before B before C, and so on.

**Why ordinary greed fails.** For `ABCC`, taking A and then B leaves `CC`.
A valid lexicographically smallest answer is `ACBC`.

**Feasibility lemma.** Suppose `N` letters remain, with counts `f_x`, and the
already written prefix ends in `p`. A valid continuation exists exactly when

```
f_p <= floor(N/2),
f_x <= ceil(N/2) for every x != p.
```

With no prefix, only the second bound applies to every letter.

**Necessity.** Copies of any letter need other letters between them, so
`f_x <= N-f_x+1`. If that letter is `p`, a separator is also required before
its first new occurrence, so `f_p <= N-f_p`. These are the stated bounds.

**Sufficiency and constructive algorithm.** Induct on `N`. For `N=0`, append
nothing. For positive `N`, do the following:

- If `N=2k+1` and some letter has count `k+1`, choose that letter. It is
  unique, since two such counts would exceed `N`, and cannot equal `p` by the
  bound on `f_p`.
- Otherwise choose the smallest available letter different from `p`.

A permitted letter exists in the second case: if every remaining letter were
`p`, its positive count `N` would violate `f_p <= floor(N/2)`. With no prefix,
any nonempty collection has an available letter.

Check that the conditions survive after writing the chosen letter `c`:

- For `N=2k`, all old counts are at most `k`. After decrementing `f_c`, its
  count is at most `k-1 = floor((N-1)/2)`; every other count is at most
  `k = ceil((N-1)/2)`.
- For `N=2k+1` with a count `k+1`, it is the chosen count. After decrementing
  it, every count is at most `k`, meeting both bounds for the remaining `2k`
  letters.
- For `N=2k+1` without such a count, all old counts are at most `k`.
  Decrementing any permitted choice leaves all counts at most `k`, again
  meeting both bounds for `2k` letters.

The new forbidden letter is `c`. The bounds therefore permit a continuation
by induction. This proves the lemma as well as validity of the algorithm.

**Lexicographic optimality.** In the odd-length forced case, choosing any
other letter would leave `k+1` copies of the dominant letter among `2k`
positions, which is impossible by necessity. In every other case, the checks
above show that *every* available letter different from `p` admits a valid
completion. Choose the smallest one. At each position our choice is the
smallest possible after our prefix; a supposed smaller valid answer would
contradict this at its first differing position. Hence the output is optimal.

Initially reject if any count exceeds `ceil(n/2)`; otherwise the invariant
starts valid and the algorithm completes.

**Prompt.** “If we postpone this very frequent letter, are there enough gaps
left for it?”
**Cost.** With 26 frequency counters, scan them for the maximum and the smallest
permitted letter at each position: O(26n) time, O(26) auxiliary space when output
is streamed. Storing the answer uses O(n) output space.
**Audience.** Use after an introductory greedy lesson. Its statement is simple,
but the proof is substantially harder than Increasing Array's.

## 5. Tower of Hanoi: recursive construction and optimality

**Rules.** Transfer a stack of different-sized disks from peg A to peg C,
using peg B. Move one top disk at a time; never put a larger disk on a smaller
one. Output a minimum-length move sequence.

**Algorithm `move(n,A,C,B)`.** For `n=0`, do nothing. Otherwise:

1. Move the top `n-1` disks from A to B using C.
2. Move disk `n` from A to C.
3. Move those `n-1` disks from B to C using A.

**Validity proof.** Induct on `n`. The empty transfer is valid. The first
recursive call clears the largest disk and is valid by induction. A larger
disk underneath a smaller transfer causes no obstruction. Peg C is then empty,
so the largest disk can move there. The second call validly puts all smaller
disks onto it, preserving their order. The required final stack results.

**Optimality proof without assuming the largest disk moves only once.** Let
`H(n)` be the minimum number of moves for a transfer between any specified two
pegs, with the third available; peg names do not affect this minimum.
Before the largest disk's **first** move, all smaller disks must be together
on the third peg: its source must be uncovered and its destination empty.
That requires at least `H(n-1)` smaller-disk moves from the initial stack.
Immediately after its **last** move, the largest disk is on C, and all smaller
disks are together on the peg that was neither the source nor destination of
that move. Moving them from there to C requires at least `H(n-1)` further
moves. These phases are disjoint, with at least one largest-disk move between
them. Therefore `H(n) >= 2H(n-1)+1`.
The construction attains equality. With `H(0)=0`, induction gives `H(n)=2^n-1`.

**Trap.** Showing that an algorithm works does not prove that its move count
is minimal. Both arguments are needed here.
**Prompt.** “Before the biggest disk can move, where must every smaller disk be?”
**Cost.** O(2^n) time, which matches the required number of printed moves,
and O(n) recursion space if moves are streamed.

## 6. Gray Code: the reversal is the insight

**Rules.** List all length-`n` binary strings once, with consecutive strings
differing in exactly one bit.

**Construction.** Start with `G_0` containing only the empty string. From
`G_(n-1)`, output its strings in their original order with 0 prefixed, then
in reverse order with 1 prefixed.

**Proof by induction.** The base list contains the only length-0 string.
Assume the smaller list contains each string once with valid consecutive
pairs. In the new list, the first half contains exactly all strings starting
with 0; the second contains exactly all strings starting with 1, so coverage
and uniqueness follow. Within either half the prefix is constant, and suffixes
are consecutive smaller-code strings (in forward or reverse order), so exactly
one bit changes. At the join, both suffixes equal the last smaller-code string;
only the new leading bit changes. Thus every adjacent pair is valid.

**Trap.** Without reversal, the join generally changes multiple bits. For
`n=2`, the unreversed order `00,01,10,11` fails between `01` and `10`.
**Prompt.** “What should the last suffix of the first half and first suffix of
the second half have in common?”
**Cost.** O(n*2^n) time to construct and print `2^n` strings of length `n`.
Materializing the list uses O(n*2^n) characters; recursive streaming can use
O(n) auxiliary space with a mutable bit buffer and a traversal-direction flag.

## 7. Apple Division: a useful limit on greedy thinking

**Rules.** Split at most 20 positive weights into two groups minimizing the
absolute difference of group totals. Individual weights can reach 10^9.

**Counterexample to a plausible greedy.** Sort descending and put each apple
on the currently lighter side. On `[8,7,6,5,4]`, the totals become 17 and 13,
giving difference 4; `[8,7]` versus `[6,5,4]` gives difference 0.

**Exact algorithm and proof.** For each apple, branch on whether it belongs
to the first group; the second group is its complement. This enumerates every
subset and hence every partition. If the first group's weight is `s` and the
total weight is `W`, the difference is `abs(W-2s)`. Minimize this expression
over all leaves. Every inspected result is feasible and every feasible partition
is inspected, so the minimum is exact. Maintain `s` along the recursion for
O(2^n) time and O(n) stack space, using 64-bit sums.

Reachable-sum sets are an alternative formulation, but may still contain
exponentially many distinct sums. There is no small weight-indexed table
guaranteed by these constraints. Present this as exhaustive search, with DP
as a later comparison under smaller weights.

## Verification

`python3 scripts/check_cses_teaching.py` checks the constructions and algorithms
on finite small domains against independent enumeration or search. Hanoi is
compared with breadth-first shortest paths, and String Reorder with all valid
small words grouped by their letter counts. No CSES submission was made.
The proofs establish correctness for the full constraints; finite checks are
supporting evidence. Source statements and category membership were read from
the official CSES pages linked above on 2026-11-09.
