"""Small-domain checks supporting the proofs in cses_intro_teaching.md."""

from collections import deque
from itertools import combinations_with_replacement, product

counts = {}

# Search all bounded nondecreasing final arrays, independently of prefix maxima.
counts['increasing'] = 0
for n in range(1, 6):
    candidates = list(combinations_with_replacement(range(1, 4), n))
    for original in product(range(1, 4), repeat=n):
        best = min(
            sum(y - x for x, y in zip(original, final))
            for final in candidates
            if all(y >= x for x, y in zip(original, final))
        )
        maximum = cost = 0
        for x in original:
            maximum = max(maximum, x)
            cost += maximum - x
        assert cost == best, original
        counts['increasing'] += 1

# Exhaust every original grid of these shapes and validate every output edge.
counts['coloring'] = 0
for rows, cols in [(1, 1), (1, 2), (2, 2), (2, 3)]:
    for original in product('ABCD', repeat=rows * cols):
        result = []
        for i, old in enumerate(original):
            forbidden = {old}
            if i >= cols:
                forbidden.add(result[i - cols])
            if i % cols:
                forbidden.add(result[i - 1])
            result.append(next(c for c in 'ABCD' if c not in forbidden))
        assert all(x != y for x, y in zip(original, result))
        for i in range(rows * cols):
            if i >= cols:
                assert result[i] != result[i - cols]
            if i % cols:
                assert result[i] != result[i - 1]
        counts['coloring'] += 1

# An independent reachable-sums DP certifies the YES/NO decisions.
counts['two_sets'] = 0
for n in range(1, 101):
    total = n * (n + 1) // 2
    reachable = 1
    for j in range(1, n + 1):
        reachable |= reachable << j
    feasible = total % 2 == 0 and bool(reachable >> (total // 2) & 1)
    assert feasible == (total % 2 == 0)
    if feasible:
        residual = total // 2
        chosen = []
        for j in range(n, 0, -1):
            if j <= residual:
                chosen.append(j)
                residual -= j
        assert residual == 0 and sum(chosen) * 2 == total
        assert len(chosen) == len(set(chosen))
    counts['two_sets'] += 1

# Enumerate all valid words, then obtain the true lexical minimum per multiset.
counts['string_reorder'] = 0
for n in range(1, 10):
    minima = {}
    for word in product('ABC', repeat=n):
        if all(word[i] != word[i - 1] for i in range(1, n)):
            key = tuple(word.count(c) for c in 'ABC')
            minima.setdefault(key, ''.join(word))
    for initial in product(range(n + 1), repeat=3):
        if sum(initial) != n:
            continue
        if max(initial) > (n + 1) // 2:
            result = None
        else:
            remaining = list(initial)
            previous = None
            answer = []
            for length in range(n, 0, -1):
                largest = max(remaining)
                if length % 2 and largest == (length + 1) // 2:
                    selected = remaining.index(largest)
                else:
                    selected = next(
                        i for i in range(3) if remaining[i] and i != previous
                    )
                assert selected != previous
                remaining[selected] -= 1
                previous = selected
                answer.append('ABC'[selected])
            result = ''.join(answer)
        assert result == minima.get(initial), (initial, result)
        counts['string_reorder'] += 1


def hanoi(n, source, target, spare):
    if n:
        yield from hanoi(n - 1, source, spare, target)
        yield source, target
        yield from hanoi(n - 1, spare, target, source)


def neighbors(state):
    # Disk 0 is smallest. A state assigns a peg to each disk.
    tops = [next((i for i, p in enumerate(state) if p == peg), None)
            for peg in range(3)]
    for source, disk in enumerate(tops):
        if disk is None:
            continue
        for target, top in enumerate(tops):
            if source != target and (top is None or disk < top):
                updated = list(state)
                updated[disk] = target
                yield tuple(updated)


counts['hanoi'] = 0
for n in range(1, 8):
    start, goal = (0,) * n, (2,) * n
    queue = deque([start])
    distance = {start: 0}
    while goal not in distance:
        state = queue.popleft()
        for updated in neighbors(state):
            if updated not in distance:
                distance[updated] = distance[state] + 1
                queue.append(updated)
    state = start
    moves = list(hanoi(n, 0, 2, 1))
    for source, target in moves:
        disk = state.index(source)
        updated = list(state)
        updated[disk] = target
        updated = tuple(updated)
        assert updated in set(neighbors(state))
        state = updated
    assert state == goal and len(moves) == distance[goal] == 2**n - 1
    counts['hanoi'] += 1

counts['gray_code'] = 0
code = ['']
for n in range(1, 11):
    code = ['0' + s for s in code] + ['1' + s for s in reversed(code)]
    assert len(code) == len(set(code)) == 2**n
    assert all(len(s) == n and set(s) <= {'0', '1'} for s in code)
    assert all(sum(x != y for x, y in zip(a, b)) == 1
               for a, b in zip(code, code[1:]))
    counts['gray_code'] += 1

# Verify the stated counterexample to balancing apples greedily.
piles = [0, 0]
for weight in [8, 7, 6, 5, 4]:
    piles[piles.index(min(piles))] += weight
assert abs(piles[0] - piles[1]) == 4
assert 8 + 7 == 6 + 5 + 4
counts['apple_counterexample'] = 1

print(counts)
