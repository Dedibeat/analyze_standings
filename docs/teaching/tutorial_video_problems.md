# 27 competitive programming problems for tutorial videos

For viewers who know arrays and loops and are learning proofs. The first pick in each section is the one I would film first. The opening questions use small examples you can draw before introducing notation.

## Divide and conquer

### 1. Tromino Puzzle

**On screen.** Cross out any square of an 8×8 board. Cover the rest with L-shaped tiles of three squares each. Draw the two center lines. Only one quarter has a hole. Where could you put a single tile to give the other three quarters the same problem?

**Proof.** Place one L over the three central squares belonging to the quarters without a hole. Each quarter now has exactly one unavailable square. Tile each quarter recursively. A 2×2 board with one unavailable square is exactly one L. The quarters are disjoint, so the four tilings and the center tile cover every required square exactly once. This works for every power-of-two side length starting at two. [UC San Diego problem sheet, problem 3](https://ucsd-cse-spis-2016.github.io/hwk/aps1/aps_dc_problems.pdf)

### 2. The Number of Inversions

**On screen.** Merge the sorted halves `[2,5,8]` and `[1,6]`. When 1 comes out first, how many out-of-order pairs did that one comparison reveal?

**Proof.** All three remaining left values exceed 1, and all originally preceded it. More generally, whenever a smaller right value comes out, add the number of left values remaining. Each inversion crossing the split is counted exactly when its right value comes out. Recursion counts the pairs entirely within each half, and a singleton has zero pairs. [Aizu ALDS1_5_D](https://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ALDS1_5_D)

### 3. Masha and a Beautiful Tree

**On screen.** Put `3,1 | 4,2` on four leaves. You may exchange the two children of any node. Can you prove the leaves can never be sorted before trying a single swap?

**Proof.** At every node, each child's leaves stay together. If all left values are smaller than all right values, keep the order. If all right values are smaller, one swap here is forced. If their ranges overlap, neither order works. Apply this test inside each child. Every counted swap is necessary, and performing exactly those swaps sorts the leaves whenever sorting is possible. [Codeforces 1741D](https://codeforces.com/problemset/problem/1741/D)

### 4. Hierarchical Majority Vote

**On screen.** Nine voters form three committees of three. The committees then vote. Show `111 | 110 | 000`. Which *one* voter could flip the final result?

**Proof.** At each node record the minimum cost to make its output 0 and to make it 1. For a target bit, at least two children must output it. Take the two smallest costs for that bit and leave the third child alone. This meets the lower bound because the children have disjoint voters. At a leaf, keeping its bit costs zero and flipping it costs one. At the root ask for the opposite of the original result. [AtCoder ABC391 E, 2025](https://atcoder.jp/contests/abc391/tasks/abc391_e?lang=en)

### 5. a-Good String

**On screen.** To make `bbad` good for the letter a, one whole half must become `aa` and the other half must be good for b. Which half would you paint solid?

**Proof.** The definition permits exactly two orientations. For each, count mismatches in the half that must be solid and recursively find the minimum edits in the other half for the next letter. The halves are disjoint, so the costs add. Take the smaller total. A single character costs zero or one according to whether it already matches. [Codeforces 1385D](https://codeforces.com/problemset/problem/1385/D)

## Greedy

### 6. Missing Coin Sum

**On screen.** Give the viewer coins `1,2,3,8`, each usable once. The first three make every sum from 0 through 6. Pause before adding 8. Could any larger coin ever rescue 7?

**Proof.** Sort the coins. Start with only 0 covered. If sums 0 through R are covered, adding coin c also covers c through c+R. When c ≤ R+1, the intervals touch or overlap, so coverage extends to R+c. When c > R+1, the old coins total only R and every unused coin is too large. Return R+1 at the first gap, or after the final coin. [CSES 2183](https://cses.fi/problemset/task/2183)

### 7. Movie Festival

**On screen.** Draw three screenings, 1–6, 2–3, and 3–4. Ask the audience to choose the first movie. Then ask what a choice has to preserve so the remaining tickets still work.

**Proof.** Take the available movie that ends earliest. In any maximum schedule, replace its first movie with this one. It ends no later, so every later movie still fits and the count stays the same. Repeat with movies starting at or after that finish. [CSES 1629](https://cses.fi/problemset/task/1629)

### 8. Stick Lengths

**On screen.** Mark lengths `1,2,8,9` on a ruler. Move the target from 2 to 3. Two sticks cost one more each, two cost one less each. Why is every target from 2 to 8 equally good?

**Proof.** Pair the shortest and longest stick, then the next shortest and next longest, and so on. For a pair of lengths a ≤ b, the total adjustment to any target is at least b−a. Every target between a and b attains that bound. A median lies inside every pair and matches the middle stick if one remains. It minimizes all the costs at once. [CSES 1074](https://cses.fi/problemset/task/1074)

### 9. Tasks and Deadlines

**On screen.** Two tasks take 8 and 2 minutes. Hide their deadlines. Can viewers still tell which one to do first?

**Proof.** Each reward is deadline minus completion time, so the sum of deadlines is fixed. Swap two adjacent tasks of lengths a > b that occur in that order. The second completion time stays fixed, the first occurs a−b earlier, and all other completion times stay fixed. Removing every such inversion yields shortest-first order and maximum reward. [CSES 1630](https://cses.fi/problemset/task/1630)

### 10. Ferris Wheel

**On screen.** Each gondola holds at most two people with total weight at most 10. Put weights `2,3,7,8` on cards. Whom can you safely seat beside 8?

**Proof.** If the heaviest and lightest exceed the limit together, the heaviest must ride alone. Otherwise an optimum can seat them together. If they ride separately, pair them and move their former partners into the freed gondola. If there are two former partners, the new pair fits because the lightest person's former partner weighs at most the heaviest person it replaces. With zero or one former partner the same rearrangement uses at most the original number of gondolas. Remove the settled riders and repeat. [CSES 1090](https://cses.fi/problemset/task/1090)

### 11. SauSaGe Bank

**On screen.** A dollar doubles daily. Withdrawing resets the account to one dollar. With six days and exactly two withdrawals, waiting three days twice pays 16. Waiting five days and one day pays 34. Can an optimum ever have two long waits?

**Proof.** Delay the final withdrawal to the last day to use every doubling. If two waits have lengths x ≥ y ≥ 2, move one day from the shorter to the longer. The longer wait gains 2ˣ and the shorter loses only 2ʸ⁻¹. Repeat until all waits except one last a single day. Those lengths are feasible and give the maximum. [Codeforces 2269A, 2026](https://codeforces.com/problemset/problem/2269/A)

## Recursion

### 12. Gray Code

**On screen.** Write `00, 01, 11, 10`. Copy it on a second strip. You want to visit all eight three-bit strings, changing one bit per step. What happens if you turn the second strip around before adding the new bit?

**Proof.** Start with the one-bit list 0, 1. Prefix the old list with 0, then prefix its reverse with 1. Adjacent entries inside each half still differ in one bit. At the join, the suffix is identical on both sides, so only the prefix changes. Each suffix occurs exactly once with each prefix, covering every string. [CSES 2205](https://cses.fi/problemset/task/2205)

### 13. Tower of Hanoi

**On screen.** Freeze the animation just before the largest disk moves. Where must every smaller disk be?

**Proof.** Before the largest disk first moves, all smaller disks must move from the source to one spare peg. After its last move to the target, the smaller disks must move onto it from another peg. These phases need at least T(n−1) moves each. Moving the smaller stack aside, moving the largest directly to the target, then rebuilding the stack attains that bound. Thus T(0)=0 and T(n)=2T(n−1)+1. [CSES 2165](https://cses.fi/problemset/task/2165)

### 14. Strange Mirroring

**On screen.** Start from `aB` and repeatedly append a case-flipped copy. The first eight characters are `aBAbAbaB`. To recover character 6, trace 6 back to 2 and flip its case once.

**Proof.** Grow the length until it covers the queried position. At each doubling, a position in the first half keeps its previous character. A position in the second half maps to the same offset in the first half with one case flip. Recurse to the original string, toggling once per right-half visit. [AtCoder ABC380 D, 2024](https://atcoder.jp/contests/abc380/tasks/abc380_d?lang=en)

### 15. Josephus Queries

**On screen.** Put seven children in a circle. Remove every second child, starting by removing 2. After 2, 4, 6 leave, rotate the survivors into counting order: 7, 1, 3, 5. Which child is now second?

**Proof.** The first floor(n/2) removals are 2, 4, 6, and so on. From the next counting position, the survivors follow the identical game. For even n their order starts 1, 3, 5; for odd n it starts n, 1, 3 and continues through n−2. For a later query subtract the removals already made, recurse on the smaller circle, and map its returned position into this order. A circle of one returns its only child. [CSES 2164](https://cses.fi/problemset/task/2164)

### 16. Sierpinski carpet

**On screen.** Reveal a 3×3 black square with a white center, then zoom out to 9×9. Ask viewers to draw the next level using a stamp of the previous picture.

**Proof.** Level zero is one black cell. At every higher level the central ninth is white, and the other eight ninths are copies of the previous level. The nine regions partition the picture, so drawing the eight smaller carpets and leaving the center blank gives exactly the requested grid. [AtCoder ABC357 C, 2024](https://atcoder.jp/contests/abc357/tasks/abc357_c?lang=en)

## Dynamic programming

### 17. Deque

**On screen.** Two players take turns keeping a number from either end of `[8,15,3,7]`. Taking 8 lets the opponent take 15. Taking 7 leaves 8 and 3 exposed, so whichever one they take, you get 15 next. How do you write that reasoning only once for both players?

**Proof.** Let D(l,r) be the best score lead for the player about to move on this interval. Taking the left end earns a[l], then the opponent can earn a lead of D(l+1,r). The resulting lead is a[l]−D(l+1,r). Taking the right end gives a[r]−D(l,r−1). These are the only moves, so take the larger value. An empty interval has lead zero. Store each interval's answer. [AtCoder DP L](https://atcoder.jp/contests/dp/tasks/dp_l)

### 18. Slimes

**On screen.** Four adjacent slimes weigh `4,3,3,4`. Each merge costs the combined weight. Merging the two 3s first costs 6+10+14=30 overall. Pairing the two outer couples costs 7+7+14=28. Which merge has a price you know before choosing anything?

**Proof.** The last merge costs the total interval weight, regardless of previous choices. Its two inputs must come from consecutive blocks split at some boundary k. For that k, independently minimize the cost of each block, then add the interval weight. Taking the minimum across all boundaries covers every possible final merge. One slime costs zero. [AtCoder DP N](https://atcoder.jp/contests/dp/tasks/dp_n)

### 19. Projects

**On screen.** Offer jobs on days 1–2 and 3–4 paying 4 each, or one job on days 1–4 paying 20. Ask viewers to reuse the Movie Festival rule and watch where it fails.

**Proof.** Sort by end day. Any optimum for the first i projects either skips project i or earns its reward plus the best schedule ending before its start. Those cases are exhaustive and both are feasible. Take the larger value, starting from zero for no projects. Days are inclusive, so the earlier end must be strictly smaller than the next start. [CSES 1140](https://cses.fi/problemset/task/1140)

### 20. Mixture

**On screen.** Add chemicals one at a time and avoid dangerous mixtures. If A then B and B then A both reach the same safe beaker, can any future addition tell which order you used?

**Proof.** Safety depends only on the set in the beaker. Start with the empty set reachable. A nonempty set S is reachable exactly when S is safe and some set obtained by removing one chemical from S is reachable. Removing the last addition proves necessity. Adding it back proves sufficiency. Store one yes/no answer per subset. [AtCoder ABC415 C, 2025](https://atcoder.jp/contests/abc415/tasks/abc415_c?lang=en)

### 21. Stones

**On screen.** Each player can take 1 or 3 stones. With 4 stones left, every move hands the opponent an odd pile. Whose position do you want to be evaluating after a move?

**Proof.** A player with zero stones loses. A position is winning if any legal move reaches a losing position for the opponent. If every legal move reaches a winning position, or no move is possible, the current player loses. Each move shrinks the pile, so filling positions in increasing order proves every result from smaller ones. [AtCoder DP K](https://atcoder.jp/contests/dp/tasks/dp_k)

## Binary search

### 22. Factory Machines

**On screen.** Two machines finish a toy every 3 and 5 seconds respectively. Freeze the clock at 14 seconds. The machines have made 4 + 2 = 6 toys. Advance one second and both finish together, bringing the total to 8. When was the seventh toy ready? The counter jumps straight over 7.

**Proof.** By time t, a machine taking p seconds can finish at most ⌊t/p⌋ toys, and running it continuously attains that count. Add those counts because the machines run simultaneously. Once the sum reaches or exceeds the target, it meets the target at every later time. Binary-search for the first such time, between zero and the time the fastest machine would need alone. [CSES 1620](https://cses.fi/problemset/task/1620)

### 23. Worms

**On screen.** Put 2, 3, and 4 worms in three piles and number them consecutively from 1. Cover every label except the last one in each pile: 2, 5, 9. Which pile holds worm 5? Which holds worm 6?

**Proof.** Pile i contains precisely the labels greater than the previous pile's last label and at most its own last label. So the answer for worm q is the first pile whose last label is at least q. The last labels are increasing prefix sums, and even an exact match belongs to that pile. [Codeforces 474B](https://codeforces.com/problemset/problem/474/B)

### 24. Aggressive Cows

**On screen.** Place three cows in stalls at 1, 2, 4, 8, 9. For a minimum gap of 3, circle stalls 1, 4, 8. Now demand a gap of 4. Starting at 1 forces the second cow as far as 8. Could starting later possibly help?

**Proof.** For a proposed gap d, place each cow in the earliest legal stall, starting with the leftmost. Its first cow is no farther right than in any feasible placement. If that holds for cow i, the other placement's next stall is also available to greedy, so greedy's next cow is no farther right either. Thus greedy fits all cows whenever any placement can. A placement that works for d works for every smaller gap, so binary-search the largest feasible d. [SPOJ AGGRCOW](https://www.spoj.com/problems/AGGRCOW/)

### 25. Maximum Median

**On screen.** The sorted array is [1, 2, 4, 4, 10]. Spend one coin per unit increase. Can four coins buy a median of 6? Lift the two 4s to 6. Now ask the price of 7 before moving anything.

**Proof.** For an odd length n, the median reaches x exactly when at least (n+1)/2 values reach x. Raising a larger value costs no more than raising a smaller one, so choose the largest (n+1)/2 values. Their total shortfall below x is the exact minimum cost. It stays level or rises as x rises. Search for the largest x within budget. Here 6 costs four coins and 7 costs six. [Codeforces 1201C](https://codeforces.com/problemset/problem/1201/C)

### 26. Array Division

**On screen.** Split [3, 1, 4, 2, 2] into two consecutive groups. With a cap of 6, packing left to right gives [3, 1], [4, 2], [2]. Raise the cap to 7 and the same three groups appear. At 8 the first group can finally absorb the 4. Could different cuts have beaten the scan?

**Proof.** For a cap at least as large as the biggest element, pack each group as far right as it fits. After one group, greedy has covered at least as much as any valid partition. If this holds after j groups, greedy either already covers the other partition's next group or can fit its remaining suffix because all entries are positive. Thus greedy uses the fewest groups. At most k groups suffice exactly when k do, since splitting a group preserves the cap and k ≤ n. Search for the smallest feasible cap between the largest element and the total sum. [CSES 1085](https://cses.fi/problemset/task/1085)

### 27. Squares in Circle

**On screen.** Draw a radius-2 circle centered on the middle square of graph paper. The center of the diagonally adjacent square lies inside the circle. Does the whole square fit? Mark its outer corner at (1.5, 1.5). Now slide the square outward along the same row.

**Proof.** On row y, take a square centered at integer x ≥ 0. Its farthest corner has squared distance (x+½)² + (|y|+½)² from the origin. The whole square fits exactly when this is at most R². The expression increases with x, so binary-search the last fitting x on each row. If x=0 fails, the row contributes zero. Otherwise the fitting centers run from −x to x, contributing 2x+1. Sum over integer rows from −R to R. For R=2 the row counts are 0, 1, 3, 1, 0. [AtCoder ABC389 D, 2025](https://atcoder.jp/contests/abc389/tasks/abc389_d?lang=en)
