"""Shenyang 2026: the ideas in shenyang_2026.md, each checked against a brute force.

No editorial was available, so the solutions below are the coach's own.  Each `check_*`
compares a short reference solution with an exhaustive search on small inputs and with the
statement's samples.  Run: python3 output/team_r3_coach/shenyang_2026_checks.py   (~1 min)
"""
import itertools
import random
from math import gcd


# L. Picky Editor I: no palindrome of length >= 2  <=>  no palindrome of length 2 or 3.
def solve_l(ops):
    s = []
    for c in ops:
        if c == "-":
            if s:
                s.pop()
        elif not (s and s[-1] == c) and not (len(s) > 1 and s[-2] == c):
            s.append(c)
    return "".join(s) or "-"


def check_l():
    def brute(ops):
        s = ""
        for c in ops:
            if c == "-":
                s = s[:-1]
            else:
                t = s + c
                if not any(t[i:j] == t[i:j][::-1] for i in range(len(t)) for j in range(i + 2, len(t) + 1)):
                    s = t
        return s or "-"
    assert [solve_l(x) for x in ("aa", "abab-", "--", "abcabc", "icpc-ec-shenyang")] == ["a", "a", "-", "abcabc", "icshenyang"]
    rng = random.Random(1)
    for _ in range(20000):
        ops = "".join(rng.choice("abc-") for _ in range(rng.randint(1, 12)))
        assert solve_l(ops) == brute(ops), ops


# D. Prefix Extremes: k-th element of the lexicographically largest permutation with a prefix maxima
# and b prefix minima.  Position 1 is both; every later position is at most one of them.
def solve_d(n, a, b, k):
    if a + b - 1 > n or (n > 1 and a + b < 3):
        return -1
    if n == 1:
        return 1
    if b == 1:  # nothing may be smaller than p1: p1 = 1, then a-1 maxima among 2..n
        m, d = n - 1, a - 1
        seq = lambda j: (m - d + j if j <= d else m - j + 1) + 1  # noqa: E731  (j = 1..m)
        return 1 if k == 1 else seq(k - 1)
    first = n - a + 1  # the a-1 larger values follow at once, increasing
    if k <= a:
        return first + k - 1
    m, c, j = n - a, b - 1, k - a  # the rest: 1..m with exactly c prefix minima, lexicographically largest
    if j <= c - 1:
        return m - j + 1  # m, m-1, ..., m-c+2
    if j == c:
        return 1
    return m - j + 2  # m-c+1, ..., 2


def check_d():
    samples = [(4, 2, 2, 1, 3), (4, 2, 2, 2, 4), (4, 2, 2, 3, 1), (4, 2, 2, 4, 2), (4, 1, 2, 3, 3), (8, 3, 7, 6, -1), (9, 3, 7, 6, 4)]
    assert all(solve_d(*s[:4]) == s[4] for s in samples)
    for n in range(1, 8):
        best = {}
        for p in itertools.permutations(range(1, n + 1)):
            a = sum(p[i] == max(p[:i + 1]) for i in range(n))
            b = sum(p[i] == min(p[:i + 1]) for i in range(n))
            best[(a, b)] = max(best.get((a, b), p), p)
        for a in range(1, n + 1):
            for b in range(1, n + 1):
                for k in range(1, n + 1):
                    want = best[(a, b)][k - 1] if (a, b) in best else -1
                    assert solve_d(n, a, b, k) == want, (n, a, b, k)


# C. Cache or Not: the cache is the pair (most recent, least recent).  A direct access adds A to every
# state; a cache access with address v only rewrites row v:  f[v][w] = min(f[v][w] + B, f[w][v] + B,
# min_y f[w][y] + C).  Index 0 is an empty slot.  O(n m).
def solve_c(m, A, B, C, req):
    inf = float("inf")
    f = [[inf] * (m + 1) for _ in range(m + 1)]
    f[0][0] = 0
    rowmin = [inf] * (m + 1)
    rowmin[0] = 0
    add = 0  # every stored value is short by `add`
    for v in req:
        new = [min(f[v][w] + A, min(f[v][w], f[w][v]) + B, rowmin[w] + C) - A if w != v else inf for w in range(m + 1)]
        add += A
        f[v] = new
        rowmin[v] = min(new)
    return min(rowmin) + add


def check_c():
    def brute(A, B, C, req):
        states = {(): 0}  # cache as a tuple, most recent first
        for v in req:
            nxt = {}
            for s, cost in states.items():
                for t, c in ((s, cost + A), (((v,) + tuple(x for x in s if x != v))[:2], cost + (B if v in s else C))):
                    if c < nxt.get(t, float("inf")):
                        nxt[t] = c
            states = nxt
        return min(states.values())
    samples = [((1, 1, 2, 3), [1, 1], 2), ((2, 2, 1, 3), [1, 1, 1, 2], 7), ((3, 4, 1, 2), [1, 2, 2, 3, 1], 9), ((3, 3, 1, 4), [1, 2, 2, 3, 1], 13)]
    for (m, A, B, C), req, want in samples:
        assert solve_c(m, A, B, C, req) == want == brute(A, B, C, req)
    rng = random.Random(2)
    for _ in range(4000):
        m = rng.randint(1, 5)
        B = rng.randint(1, 9)
        A, C = rng.randint(1, 9), rng.randint(B, 12)
        req = [rng.randint(1, m) for _ in range(rng.randint(1, 12))]
        assert solve_c(m, A, B, C, req) == brute(A, B, C, req), (m, A, B, C, req)


# J. Sirius I: x is anchored in b  <=>  every other y in b is a submask or a supermask of x.
# Equivalently, with popcounts: x is the only value of its popcount, the OR of the values with a
# smaller popcount is inside x, and x is inside the AND of the values with a larger popcount.
def anchored(b, m):
    out = 0
    for x in b:
        low = [y for y in b if bin(y).count("1") < bin(x).count("1")]
        high = [y for y in b if bin(y).count("1") > bin(x).count("1")]
        same = [y for y in b if bin(y).count("1") == bin(x).count("1")]
        lo_or = 0
        for y in low:
            lo_or |= y
        hi_and = (1 << m) - 1
        for y in high:
            hi_and &= y
        ok = len(same) == 1 and lo_or & ~x == 0 and x & ~hi_and == 0
        assert ok == all(y & x == y or y & x == x for y in b)
        out += ok
    return out


def check_j():
    def brute(b, m):
        ranks = {x: set() for x in b}
        for p in itertools.permutations(range(m)):
            order = sorted(b, key=lambda x: [x >> i & 1 for i in p])
            for i, x in enumerate(order):
                ranks[x].add(i)
        return sum(len(r) == 1 for r in ranks.values())
    a = [0, 5, 1, 3, 2, 4, 6]
    queries = [(1, 7, 1), (1, 4, 2), (2, 6, 0), (2, 4, 1), (4, 5, 2), (4, 7, 0)]
    assert all(anchored(a[l - 1:r], 3) == want for l, r, want in queries)
    rng = random.Random(3)
    for _ in range(1500):
        m = rng.randint(1, 5)
        b = rng.sample(range(1 << m), rng.randint(1, min(1 << m, 7)))
        assert anchored(b, m) == brute(b, m), (b, m)


# F. MEX Deletion: the answer is 1, 2 or 3.  Blocks [kd, (k+1)d) taken by k mod 3 give three sets of
# cost 1, so 3 always works.  1: no pair with d <= diff < 2d.  2: no pair with 2d <= diff < 3d (one
# operation of cost 2), or the graph of pairs with d <= diff < 2d is bipartite (two of cost 1).
def solve_f(d, a):
    def pair_in(lo, hi):
        return any(lo <= y - x < hi for x in a for y in a)
    if not pair_in(d, 2 * d):
        return 1
    if not pair_in(2 * d, 3 * d):
        return 2
    colour = {}
    for s in a:  # contest version: union the window [v+d, v+2d) with a next-pointer DSU, then parity DSU
        if s in colour:
            continue
        colour[s], stack = 0, [s]
        while stack:
            x = stack.pop()
            for y in a:
                if d <= abs(y - x) < 2 * d:
                    if y not in colour:
                        colour[y] = 1 - colour[x]
                        stack.append(y)
                    elif colour[y] == colour[x]:
                        return 3
    return 2


def check_f():
    def mex(vals, d):
        s = {(y - x) // d for x in vals for y in vals if y >= x}
        return next(i for i in range(len(s) + 1) if i not in s)

    def brute(d, a):
        best = [10 ** 9]

        def rec(i, groups):
            if i == len(a):
                best[0] = min(best[0], sum(mex(g, d) for g in groups))
                return
            for g in groups:
                g.append(a[i])
                rec(i + 1, groups)
                g.pop()
            groups.append([a[i]])
            rec(i + 1, groups)
            groups.pop()
        rec(0, [])
        return best[0]
    samples = [(2, [1, 2, 3, 5], 2), (3, [1, 3, 4, 6, 6, 8], 3), (9, [2, 5, 5, 6, 7, 8, 9, 9], 1)]
    assert all(solve_f(d, a) == want for d, a, want in samples)
    rng = random.Random(4)
    for _ in range(1500):
        d = rng.randint(1, 4)
        a = sorted(rng.randint(1, 16) for _ in range(rng.randint(1, 8)))
        assert solve_f(d, a) == brute(d, a), (d, a)


# A. Minimalism: the divisors of n that divide m are the divisors of g = gcd(m, n), so the answer is
# the sum of phi(n / g) over the good g.  The indices start at 1, so with step s the divisor set of g
# is a prefix of D[1], D[1+s], D[1+2s], ...; s = index(q) - 1 for the smallest prime q of g.  Walk
# that sequence once per prime: the prefix of length t is good when its lcm is its last element and
# has exactly t divisors.
def solve_a(factors):
    n = 1
    for p, e in factors:
        n *= p ** e
    divs = [1]
    for p, e in factors:
        divs = [x * p ** i for x in divs for i in range(e + 1)]
    divs.sort()

    def tau(g):
        t = 1
        for p, _ in factors:
            e = 0
            while g % p == 0:
                g //= p
                e += 1
            t *= e + 1
        return t

    def phi(g):
        r = g
        for p, _ in factors:
            if g % p == 0:
                r = r // p * (p - 1)
        return r
    good = {1}
    for q, _ in factors:
        step, lcm = divs.index(q), 1
        for t, x in enumerate(divs[::step], 1):
            lcm = lcm * x // gcd(lcm, x)
            if lcm == x and tau(x) == t:
                good.add(x)
    return sum(phi(n // g) for g in good)


def check_a():
    def brute(n):
        divs = [x for x in range(1, n + 1) if n % x == 0]
        count = 0
        for m in range(1, n + 1):
            idx = [i for i, x in enumerate(divs) if m % x == 0]
            count += len({b - a for a, b in zip(idx, idx[1:])}) <= 1
        return count
    assert solve_a([(5, 1), (2, 2)]) == 19
    big = [(2, 9), (3, 4), (5, 3), (7, 2)] + [(p, 1) for p in (11, 13, 17, 19, 23, 29, 31, 37)]
    assert solve_a(big) == 3497350720389120001
    for n in range(2, 2500):
        factors, x, p = [], n, 2
        while p * p <= x:
            if x % p == 0:
                e = 0
                while x % p == 0:
                    x //= p
                    e += 1
                factors.append((p, e))
            p += 1
        if x > 1:
            factors.append((x, 1))
        assert solve_a(factors) == brute(n), n


# H. Perfect Puzzle: rook of row x at column pi[x].  Cell (x, y) with y >= pi[x] takes colour x.
# Any other cell copies the nearest row below it whose rook is at a column <= y, or, if there is
# none, the nearest such row above.  Every region stays in columns >= its rook's column, and in the
# rook's own column its other cells lie in rows of rooks further right, so the rooks are forced from
# the rightmost column to the left.  (The statement's second page, with the output format, was not
# available; this checks the three shape rules and uniqueness only.)
def solve_h(pi):
    n = len(pi)
    col = [[None] * n for _ in range(n)]
    for x in range(n):
        for y in range(n):
            if y >= pi[x]:
                col[x][y] = x
            else:
                below = [z for z in range(x + 1, n) if pi[z] <= y]
                col[x][y] = below[0] if below else [z for z in range(x) if pi[z] <= y][-1]
    return col


def check_h():
    for n in range(2, 8):
        for pi in itertools.permutations(range(n)):
            col = solve_h(pi)
            for c in range(n):
                cells = {(x, y) for x in range(n) for y in range(n) if col[x][y] == c}
                assert (c, pi[c]) in cells
                for x in range(n):  # convex in rows and in columns
                    ys = [y for y in range(n) if (x, y) in cells]
                    xs = [z for z in range(n) if (z, x) in cells]
                    assert (not ys or len(ys) == ys[-1] - ys[0] + 1) and (not xs or len(xs) == xs[-1] - xs[0] + 1)
                seen, stack = {(c, pi[c])}, [(c, pi[c])]
                while stack:
                    x, y = stack.pop()
                    for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if t in cells and t not in seen:
                            seen.add(t)
                            stack.append(t)
                assert seen == cells

            def count(x, used_cols, used_colours):  # rook placements: one per row, column and colour
                if x == n:
                    return 1
                return sum(count(x + 1, used_cols | {y}, used_colours | {col[x][y]}) for y in range(n)
                           if y not in used_cols and col[x][y] not in used_colours)
            assert count(0, frozenset(), frozenset()) == 1, pi


if __name__ == "__main__":
    for name, check in sorted((k, v) for k, v in globals().items() if k.startswith("check_")):
        check()
        print(name, "ok")
