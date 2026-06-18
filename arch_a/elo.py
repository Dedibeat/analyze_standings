"""The Elo-inversion primitive (strat.tex Def. 1, eq. pi).

Codeforces logistic convention: a competitor of ability theta solves a problem of
difficulty b with probability pi(theta, b) = 1 / (1 + 10**((b-theta)/400)).
"""

import numpy as np

S = 400.0 / np.log(10.0)  # ~173.7

# Scale floor/ceiling (strat.tex section 3.2). Difficulty: solved-by-all has no
# finite root and pins to LO, solved-by-none pins to HI. Performance is inverted
# (rank 1 is best): rank 1 pins to HI, last place pins to LO.
LO = 800.0
HI = 4000.0


def pi(theta, b):
    """Solve / win probability for ability theta against difficulty b."""
    return 1.0 / (1.0 + np.power(10.0, (b - theta) / 400.0))


def weighted_rating(thetas, S_target, weights=None, lo=LO, hi=HI, tol=1e-6):
    """Unique b solving sum_t w_t * pi(theta_t, b) = S_target, by bisection.

    The left-hand side is strictly decreasing in b, so the root is unique. When
    the target is unattainable inside [lo, hi] (e.g. solved by all -> b below lo,
    solved by none -> b above hi) the result is clamped to the corresponding
    bound.
    """
    thetas = np.asarray(thetas, dtype=float)
    if weights is None:
        w = np.ones_like(thetas)
    else:
        w = np.asarray(weights, dtype=float)

    def f(b):
        return np.sum(w * pi(thetas, b)) - S_target

    flo, fhi = f(lo), f(hi)
    # f is decreasing: f(lo) is the max attainable surplus, f(hi) the min.
    if flo <= 0.0:      # even at the floor we expect <= S_target solvers -> easy edge
        return lo
    if fhi >= 0.0:      # even at the ceiling we still expect >= S_target -> hard edge
        return hi

    a, c = lo, hi
    while c - a > tol:
        m = 0.5 * (a + c)
        if f(m) > 0.0:
            a = m
        else:
            c = m
    return 0.5 * (a + c)


def performance_rating(rank, rival_thetas, lo=LO, hi=HI, tol=1e-6):
    """Ability whose expected rank equals the achieved rank (eq. perf).

    Solves 1 + sum_{u != t} pi(theta_u, rho) = rank, i.e. expected number of
    superiors = rank - 1.
    """
    return weighted_rating(rival_thetas, S_target=rank - 1.0, lo=lo, hi=hi, tol=tol)


if __name__ == "__main__":
    # Worked examples from strat_detailed.tex on the toy field.
    field = np.array([2400.0, 2200.0, 2000.0, 1800.0, 1600.0])

    bB = weighted_rating(field, 3.0)   # problem B, 3 solvers -> ~1890
    bC = weighted_rating(field, 1.0)   # problem C, 1 solver  -> ~2360
    rivals_T4 = np.array([2400.0, 2200.0, 2000.0, 1600.0])
    rho = performance_rating(2, rivals_T4)  # T4 finishing 2nd -> ~2350

    print(f"problem B difficulty (expect ~1890): {bB:.1f}")
    print(f"problem C difficulty (expect ~2360): {bC:.1f}")
    print(f"T4 performance at rank 2 (expect ~2350): {rho:.1f}")

    assert abs(bB - 1890) < 25, bB
    assert abs(bC - 2360) < 25, bC
    assert abs(rho - 2350) < 25, rho

    # Edge cases pin to the bounds.
    assert weighted_rating(field, len(field)) == LO    # solved by all -> floor
    assert weighted_rating(field, 0.0) == HI           # solved by none -> ceiling
    assert performance_rating(1, field) == HI          # rank 1 (best) -> ceiling
    assert performance_rating(len(field) + 2, field) == LO  # below last -> floor
    print("elo.py self-checks passed")
