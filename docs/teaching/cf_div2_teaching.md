# Recent Codeforces A/B problems for a general audience

Selection date: 2026-11-09. Audience: general audience; no prior contest
vocabulary assumed. The recommendations below are teaching judgments, not a
ranking of difficulty. Proofs are derived here from the official statements.

## Scope and recommendation

“Recent” and “DC” were not defined in the request. This first pass explicitly
uses the **20 most recent finished rounds whose official names contain
“Div. 2”**, including Educational and combined Div. 1 + Div. 2 rounds:
2026-08-01 through 2026-11-07. Dates and round types come from the
[official contest API](https://codeforces.com/api/contest.list). A/B statements,
including split versions, were read from the official combined problem pages.
This is a bounded shortlist, not an exhaustive search of the last year.
If DC means divide and conquer, I found no strong teaching recommendation in
this sample; none of the problems below is presented as divide and conquer.

**Best single greedy lesson: SauSaGe Bank. Best DP lesson: Prefix.
Best trickier greedy lesson: Merge to Match.**

| Suggested order | Problem and official statement | Date | Teaching purpose | Prerequisites |
|---|---|---|---|---|
| Warm-up | [2276A — Perfect Sandwiches](https://codeforces.com/contest/2276/problem/A), Educational 195 | Oct 14 | Upper bound plus construction | Counting |
| Main greedy lesson | [2269A — SauSaGe Bank](https://codeforces.com/contest/2269/problem/A), Round 1124 | Sep 26 | Exchange argument | Powers of two |
| Main DP lesson | [2274B — Prefix](https://codeforces.com/contest/2274/problem/B), Round 1127 | Oct 11 | Preserve both extremes of a state | Negative numbers, min/max |
| Trickier follow-up | [2248B — Merge to Match](https://codeforces.com/contest/2248/problem/B), Round 1113 | Aug 1 | Necessary witnesses and sorted greedy construction | Sorting, inequalities |
| Bonus discovery | [2256B — Domino Tiles](https://codeforces.com/contest/2256/problem/B), Round 1116 | Aug 9 | A four-state DP simplifies to four patterns | Binary strings, cancellation |

Avoid opening with interactive problems, MEX terminology, or game strategies
for this audience. These are additional concepts to teach before the algorithm.
All examples below are explanatory examples, not claimed official samples.

## 1. Perfect Sandwiches: a gentle proof warm-up

**Rules.** Use all `a` cheese slices and `b` sausage slices. Every sandwich
needs both ingredients and strictly more cheese than sausage. Maximize the
number of sandwiches. The statement guarantees `a,b >= 1`.

**Answer.** Impossible if `a <= b`; otherwise `min(b, a-b)`.

**Proof.** If there are `t` sandwiches, each uses at least one sausage slice,
so `t <= b`. Each also uses at least one more cheese slice than sausage slice;
summing these differences gives `t <= a-b`. In particular `a <= b` is impossible.

Conversely, assume `a > b` and set `t = min(b,a-b)`, which is positive. Make
`t` sandwiches with two cheese slices and one sausage slice each. This is
possible because `a >= b+t >= 2t`. Add all remaining sausage slices, paired
with an equal number of remaining cheese slices, to the first sandwich.
There are enough cheese slices since `a-2t >= b-t`. Add any leftover cheese
to that sandwich too. Every slice is used, and every sandwich still has
strictly more cheese. Thus the upper bound is attained.

**Prompt.** “What resource does every additional sandwich consume?”
**Cost.** O(1) arithmetic and O(1) space.

## 2. SauSaGe Bank: the cleanest exchange argument

**Rules.** Start with $1 in the bank. Each morning its balance doubles.
On a withdrawal night, take the whole balance and reset it to $1. Withdraw
on exactly `k` different days within `n` days; maximize the total withdrawn.
Here `1 <= k <= n <= 30`.

**Answer.** `2^(n-k+1) + 2(k-1)`.

**Proof, including the final day.** If the last withdrawal occurs before day
`n`, move it to day `n` while keeping all earlier withdrawals. It now follows
more doublings, so the total strictly increases. Hence an optimal schedule
withdraws on day `n`.

Let `d_1,...,d_k` be the positive numbers of days from the start to the first
withdrawal and between successive withdrawals. They sum to `n`, and the
withdrawn total is `sum(2^d_i)`.

If two lengths `x,y` are both at least 2, choose their names so `x >= y`.
Replace them by `x+1,y-1`. Both remain positive and their sum is unchanged.
The change in total is

```
2^(x+1) + 2^(y-1) - 2^x - 2^y = 2^x - 2^(y-1) > 0.
```

Therefore an optimal composition has at most one length greater than 1.
The lengths must be `n-k+1` and `k-1` copies of 1, giving the formula.
These lengths are a legal withdrawal schedule, so the bound is attainable.

**Trap.** Equal-sized intervals feel fair, but doubling rewards concentrating
time. For `n=6,k=2`, lengths `(3,3)` give 16; `(5,1)` give 34.
**Prompt.** “Move one day from the shorter waiting period to the longer one.
Does that help?”
**Cost.** O(1) fixed-width arithmetic and space; use a 64-bit integer.

## 3. Prefix: the strongest DP teaching choice

**Rules.** Process positions `2,...,n`. At position `i`, let `s` be the sum of
already processed elements. Replace the original value `x=a_i` by one of
`x-s`, `x`, `x+s`. Maximize the largest final array element.

**State.** After processing a prefix, keep its smallest reachable sum `lo`
and largest reachable sum `hi`. Keep `answer`, the largest element attainable
at any position processed so far. Initially all three equal `a_1`.

For each next original value `x`, use the **old** `lo,hi` for all updates:

```
answer = max(answer, x + max(abs(lo), abs(hi)))
new_lo = x + min(0, 2*lo)
new_hi = x + max(0, 2*hi)
lo, hi = new_lo, new_hi
```

**Proof of the state transitions.** Let `S` be the exact set of reachable old
prefix sums. It is finite and nonempty. For a fixed `s` in `S`, the new element
is `x-s`, `x`, or `x+s`, so its largest possible value is `x+abs(s)`.
The maximum absolute value in `S` is `max(abs(lo),abs(hi))`, and an endpoint
attains it.

The new prefix sum is respectively `x`, `x+s`, or `x+2s`.
For each fixed `s`, its minimum is `x+min(0,2s)` and its maximum is
`x+max(0,2s)`. Minimizing and maximizing over `S` gives exactly the transitions
above. Both extremes are reachable, so induction proves the state remains
exact. We do **not** assume that every number between `lo` and `hi` is reachable.

Every final element was fixed at its own processing step. Every sequence of
choices for a prefix can be extended through the rest of the array, since all
three choices remain legal. Consequently the largest attainable element over
all positions is the maximum of the per-position optima, exactly `answer`.
The state extremes and `answer` need not come from the same history.

**Trap.** Keeping only the largest sum fails on `[-2,-2,-2]`: after position
2 the reachable sums are `-6,-4,-2`. The smallest, `-6`, lets the next element
become 4. The largest, `-2`, only lets it become 0.
**Prompt.** “When subtracting a sum, would you prefer it large or negative?”
**Cost.** O(n) time and O(1) auxiliary space. Signed 64-bit integers suffice:
after `i` positions, every prefix sum has absolute value at most
`50*(2^i-1)`; the official limit is `n <= 50`.

## 4. Merge to Match: the trickiest recommended greedy proof

**Rules.** Merge any two current values into any integer between them,
including either endpoint. Make the final multiset equal to a target array.
All original and target values are pairwise distinct; rearrangement is allowed.

Sort the original values `a_1 < ... < a_n` and targets `b_1 < ... < b_m`.
The answer is YES exactly when

```
n >= 2m, and a_i < b_i < a_(n-m+i) for every i=1,...,m.
```

**Necessity.** Each current value descends from a nonempty group of original
values. These groups are disjoint, and a value always lies between its group's
minimum and maximum: this holds initially and is preserved by merging.
Because no target is an original value, the group producing target `b` must
contain one original value strictly below `b` and another strictly above `b`.
Choose these two witnesses for every target. All `2m` witnesses are distinct,
so `n >= 2m`.

For the first `i` targets, their `i` lower witnesses are all strictly below
`b_i`. Thus at least `i` originals lie below `b_i`, giving `a_i < b_i`.
For the last `m-i+1` targets, that many upper witnesses lie strictly above
`b_i`. Therefore `a_(n-m+i) > b_i`. Every stated inequality is necessary.

**Sufficiency.** Pair `a_i` with `a_(n-m+i)` for each `i=1,...,m` and merge
that pair directly into `b_i`. The inequalities permit each merge, and
`n >= 2m` makes all pairs disjoint. If originals remain, merge each into
`b_1`, choosing `b_1` again as the result. This is legal because an endpoint
is allowed. After absorbing every leftover, the targets are exactly the
remaining values.

**Trap.** Having enough values and enclosing every target in the overall
range is insufficient: `[1,2,3,100]` cannot produce `[4,5]`. Each target
requires its own upper witness, and there is only one value above 4.
**Prompt.** “What must each final number inherit from its original ancestors?”
**Cost.** O(n log n + m log m) time for sorting, then a linear scan.
Auxiliary space depends on the sorting implementation.

## 5. Domino Tiles: derive a DP, then simplify it

**Rules.** Fill unknown binary tiles. Neighboring tiles form overlapping
dominoes, whose weights are the sums of their two bits. Consecutive dominoes
must have different weights. Count valid completions.

**Natural DP.** Let `dp_i[p][q]` count completions of positions `1,...,i`
ending with bits `p,q`. Initialize the four pairs at `i=2` with count 1
when they match the given characters, otherwise 0. Appending bit `r` is
allowed exactly when it matches the next given character and
`p+q != q+r`; add the old count to `dp_(i+1)[q][r]`.
Each valid completion has a unique previous prefix, and each permitted
extension satisfies the one new condition. This proves the recurrence by
induction. Sum the four final states, using the required modulus.

**Simplification and proof.** Cancel `q` in the inequality to obtain `p != r`.
For bits this means `r=1-p`. Hence after choosing the first two bits, every
later bit is forced: `s_(i+2)=1-s_i`. There are exactly four unrestricted
candidates, the prefixes of the repetitions of `0011`, `0110`, `1001`, `1100`.
Check each against every fixed character and count the matches. Necessity
follows from cancellation; sufficiency follows by substituting the recurrence
back into every adjacent-domino inequality. The four candidates have distinct
first pairs, so there is no double counting, including when `n=2`.

**Trap.** Alternating tiles are not the goal: `010` has domino weights 1,1
and is invalid, while `0011` has weights 0,1,2 and is valid.
**Cost.** Both approaches take O(n) time and O(1) auxiliary space. The answer
is at most 4; the simplified method needs no modular arithmetic.
**Teaching role.** A good follow-up on sufficient state, but use Prefix if
the main objective is teaching why DP is needed.

## Suggested session

For a general audience, start with Sandwiches, then develop the Bank exchange
proof with concrete waiting periods. Introduce Prefix after learners are
comfortable listing choices and retaining results. Save Merge to Match for
an audience ready to reason about sorted order and disjoint witnesses.
Domino Tiles works as a short discovery exercise between lessons.

These are mathematical lessons first; coding is optional. Teach only the
vocabulary needed by the current problem. Do not present all five in one short
introductory talk. No duration or programming background was supplied, so this
is an ordering recommendation rather than a timed lesson plan.

## Verification and search record

Official statement pages were retrieved on 2026-11-09 using the existing
`../codeforces_integration` scraper; contest metadata came from the live API.
The proofs above are independent derivations, not quotations or claims about
an official editorial. No submission to Codeforces was made.

The inspected contest IDs, newest first, were:
`2280, 2284, 2283, 2272, 2277, 2261, 2276, 2274, 2271, 2269,
2267, 2264, 2263, 2260, 2258, 2257, 2256, 2253, 2252, 2248`.
The selection favors transparent proofs over merely short solution code.

`python3 scripts/check_cf_teaching.py` independently checks the four main
algorithms on finite small domains. It enumerates withdrawal compositions,
all reachable Prefix histories, binary completions, and disjoint ancestor
groups for Merge to Match. These checks support the derivations; the proofs,
not the finite checks, establish correctness for the full input constraints.
