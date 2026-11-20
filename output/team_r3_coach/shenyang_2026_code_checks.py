"""Shenyang 2026: our saved onsite code, run against the references in shenyang_2026_checks.py.

The code is transcribed from the printouts made at 13:15-13:19 (minutes 256-259) into
data/team_r3/shenyang_2026/{c,d,f,h,j,l}.cpp.  Input formats are the ones the code reads.
Run: python3 output/team_r3_coach/shenyang_2026_code_checks.py   (needs g++, ~1 min)
"""
import itertools
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shenyang_2026_checks as ref  # noqa: E402

CODE = os.path.join(HERE, "..", "..", "data", "team_r3", "shenyang_2026")
BIN = tempfile.mkdtemp()


def build(name, strip_print=False):
    src = open(os.path.join(CODE, name + ".cpp")).read()
    if strip_print:  # f.cpp only: drop the debug output lines `print(st);`
        src = "\n".join(x for x in src.split("\n") if x.strip() != "print(st);")
    exe = os.path.join(BIN, name + ("_noprint" if strip_print else ""))
    subprocess.run(["g++", "-std=c++17", "-O2", "-x", "c++", "-", "-o", exe], input=src, text=True, check=True)
    return exe


def run(exe, text):
    return subprocess.run([exe], input=text, capture_output=True, text=True, check=True).stdout.split("\n")


def check_l():
    exe, rng = build("l"), random.Random(11)
    cases = ["aa", "abab-", "--", "abcabc", "icpc-ec-shenyang"]
    cases += ["".join(rng.choice("abc-") for _ in range(rng.randint(1, 12))) for _ in range(20000)]
    out = run(exe, f"{len(cases)}\n" + "\n".join(cases) + "\n")
    assert out[:len(cases)] == [ref.solve_l(s) for s in cases]


def check_d():
    exe, rng = build("d"), random.Random(12)
    cases = [(n, a, b, k) for n in range(1, 9) for a in range(1, n + 2) for b in range(1, n + 2) for k in range(1, n + 1)]
    for _ in range(20000):
        n = rng.choice([rng.randint(1, 30), rng.randint(1, 10 ** 9)])
        a, b = rng.randint(1, min(n, 40) + 1), rng.randint(1, min(n, 40) + 1)
        if rng.random() < 0.5:
            a, b = rng.randint(1, n), rng.randint(1, n)
        cases.append((n, a, b, rng.randint(1, n)))
    out = run(exe, f"{len(cases)}\n" + "\n".join(" ".join(map(str, c)) for c in cases) + "\n")
    bad = [c for c, o in zip(cases, out) if int(o) != ref.solve_d(*c)]
    assert not bad, bad[:5]


def check_c():
    exe, rng = build("c"), random.Random(13)
    cases = [((1, 1, 2, 3), [1, 1]), ((2, 2, 1, 3), [1, 1, 1, 2]), ((3, 4, 1, 2), [1, 2, 2, 3, 1]), ((3, 3, 1, 4), [1, 2, 2, 3, 1])]
    for _ in range(4000):
        m, B = rng.randint(1, 5), rng.randint(1, 9)
        cases.append(((m, rng.randint(1, 9), B, rng.randint(B, 12)), [rng.randint(1, m) for _ in range(rng.randint(1, 12))]))
    for _ in range(30):  # larger, against the O(n m) reference only
        m, B = rng.randint(1, 40), rng.randint(1, 10 ** 9)
        cases.append(((m, rng.randint(1, 10 ** 9), B, rng.randint(B, 10 ** 9)), [rng.randint(1, m) for _ in range(300)]))
    text = f"{len(cases)}\n" + "".join(f"{len(r)} {m} {A} {B} {C}\n{' '.join(map(str, r))}\n" for (m, A, B, C), r in cases)
    out = run(exe, text)
    assert [int(x) for x in out[:len(cases)]] == [ref.solve_c(m, A, B, C, r) for (m, A, B, C), r in cases]


def h_ok(pi, grid):
    """The coach's H conditions: regions 4-connected and convex in rows and columns, each rook on its
    own colour, and exactly one way to place one rook per colour with no two in a row or column."""
    n = len(pi)
    for c in range(n):
        cells = {(x, y) for x in range(n) for y in range(n) if grid[x][y] == grid[c][pi[c]]}
        for x in range(n):
            ys = [y for y in range(n) if (x, y) in cells]
            xs = [z for z in range(n) if (z, x) in cells]
            if (ys and len(ys) != ys[-1] - ys[0] + 1) or (xs and len(xs) != xs[-1] - xs[0] + 1):
                return False
        seen, stack = {(c, pi[c])}, [(c, pi[c])]
        while stack:
            x, y = stack.pop()
            for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if t in cells and t not in seen:
                    seen.add(t)
                    stack.append(t)
        if seen != cells:
            return False
    if len({grid[c][pi[c]] for c in range(n)}) != n or any(ch not in {grid[c][pi[c]] for c in range(n)} for row in grid for ch in row):
        return False

    def count(x, cols, colours):
        if x == n:
            return 1
        return sum(count(x + 1, cols | {y}, colours | {grid[x][y]}) for y in range(n) if y not in cols and grid[x][y] not in colours)
    return count(0, frozenset(), frozenset()) == 1


def check_h():
    exe, rng = build("h"), random.Random(14)
    perms = [p for n in range(1, 8) for p in itertools.permutations(range(n))]
    perms += [tuple(rng.sample(range(n), n)) for n in (8, 9) for _ in range(300)]
    for pi in perms:
        n, letters = len(pi), rng.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", len(pi))
        board = ["".join(letters[x] if y == pi[x] else "." for y in range(n)) for x in range(n)]
        grid = run(exe, f"{n}\n" + "\n".join(board) + "\n")[:n]
        assert all(grid[x][pi[x]] == letters[x] for x in range(n)) and h_ok(pi, grid), (pi, grid)
    return len(perms)


def check_j():
    exe, rng = build("j"), random.Random(15)

    def anchored(b):  # the lemma: comparable (submask or supermask) with every other value
        return sum(all(y & x == y or y & x == x for y in b) for x in b)
    a = [0, 5, 1, 3, 2, 4, 6]
    sample = [(1, 7), (1, 4), (2, 6), (2, 4), (4, 5), (4, 7)]
    out = run(exe, f"7 3 6\n{' '.join(map(str, a))}\n" + "".join(f"{l} {r}\n" for l, r in sample))
    assert [int(x) for x in out[:6]] == [1, 2, 0, 1, 2, 0]
    for it in range(1500):  # small: against all m! orders through ref.anchored
        m = rng.randint(1, 5)
        a = rng.sample(range(1 << m), rng.randint(1, min(1 << m, 7)))
        qs = [(l, r) for l in range(1, len(a) + 1) for r in range(l, len(a) + 1)]
        out = run(exe, f"{len(a)} {m} {len(qs)}\n{' '.join(map(str, a))}\n" + "".join(f"{l} {r}\n" for l, r in qs))
        assert [int(x) for x in out[:len(qs)]] == [ref.anchored(a[l - 1:r], m) for l, r in qs], (a, m)
    for it in range(20):  # larger, 60-bit, chains with noise so that answers are not all 0
        n, m = rng.randint(50, 400), 60
        x, a = 0, []
        while len(a) < n:
            x = x | (1 << rng.randrange(m)) if rng.random() < 0.8 else rng.getrandbits(m)
            if x not in a:
                a.append(x)
        qs = [(l, r) for l, r in (sorted(rng.sample(range(1, n + 1), 2)) for _ in range(400))]
        out = run(exe, f"{n} {m} {len(qs)}\n{' '.join(map(str, a))}\n" + "".join(f"{l} {r}\n" for l, r in qs))
        assert [int(x) for x in out[:len(qs)]] == [anchored(a[l - 1:r]) for l, r in qs]


def check_f():
    """f.cpp is the version printed at 13:17:21 (minute 257); the only F run was at 295.8'."""
    printed, greedy = build("f"), build("f", strip_print=True)
    samples = [(2, [1, 2, 3, 5]), (3, [1, 3, 4, 6, 6, 8]), (9, [2, 5, 5, 6, 7, 8, 9, 9])]
    text = f"{len(samples)}\n" + "".join(f"{len(a)} {d}\n{' '.join(map(str, a))}\n" for d, a in samples)
    lines = [x for x in run(printed, text) if x]
    debug = sum(x.startswith("st: ") for x in lines)
    got = [int(x) for x in run(greedy, text) if x]
    want = [ref.solve_f(d, a) for d, a in samples]
    rng, wrong, total = random.Random(16), 0, 1500
    cases = []
    for _ in range(total):
        d = rng.randint(1, 4)
        cases.append((d, sorted(rng.randint(1, 16) for _ in range(rng.randint(1, 8)))))
    text = f"{total}\n" + "".join(f"{len(a)} {d}\n{' '.join(map(str, a))}\n" for d, a in cases)
    outs = [int(x) for x in run(greedy, text) if x]
    wrong = sum(o != ref.solve_f(d, a) for o, (d, a) in zip(outs, cases))
    return {"debug lines on the samples": debug, "samples got": got, "samples want": want,
            "random cases wrong": f"{wrong} / {total}"}


if __name__ == "__main__":
    for name in ("l", "d", "c", "h", "j"):
        result = globals()["check_" + name]()
        print(f"{name}.cpp ok" + (f" ({result} boards)" if result else ""))
    print("f.cpp (as printed):", check_f())
