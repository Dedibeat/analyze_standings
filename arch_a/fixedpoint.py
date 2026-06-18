"""Architecture A: alternating estimation of abilities and difficulties.

strat.tex Algorithm 1. Abilities theta_t and difficulties b_p are mutually
dependent, so they are solved by alternation:

    repeat
        for each team in each contest: performance rating rho_{t,c}  (eq. perf)
        for each team: ability update theta_t                        (eq. update)
    until max |delta theta| < eps
    for each problem: difficulty b_p                                  (eq. bp)

Anchoring (deviation from the strat). The strat anchors the scale through the
Codeforces ratings of team members (eq. cfprior), which seed a per-team
theta_prior, and its eq. update blends 0.5*(rho + theta_prior). No CF ratings
exist in this data, so theta_prior is a constant neutral MU0 (a mid Codeforces
rating) for every team. A fixed 0.5 blend toward a *constant* MU0 never washes
out with evidence -- even a 40-contest team stays pinned halfway to MU0 -- which
flattens contest-strength differences toward MU0 and damps the cross-contest
normalization the shared teams are meant to carry.

We therefore treat MU0 as a single pseudo-observation of strength PRIOR_STRENGTH
that the data outvotes as a team plays more contests:

    theta_t = (w_t * sum_c rho_{t,c} + PRIOR_STRENGTH * MU0)
              / (w_t * N_t            + PRIOR_STRENGTH)

A one-contest team leans on MU0 (cold start); a veteran is driven by its own
performances. MU0 still fixes the global shift on the [800, 4000] scale.

Weighting (deviation from the strat). The strat's experience weight
1 - 0.9^(n+1) grows with a team's accumulated history n. We replace it with a
single reliability weight per team from its *total* contest count N_t,
w_t = 1 - 0.9^(N_t): a team seen in many contests is a steady yardstick and
speaks loudly in both the ability update and the difficulty estimate; a
one-off team is down-weighted to 0.1.
"""

import numpy as np

from . import elo
from .load import load

MU0 = 2000.0          # neutral prior mean (mid Codeforces rating); anchors the scale
PRIOR_STRENGTH = 1.0  # MU0 counts as this many effective contests of evidence


def _team_weights(ds):
    """Reliability weight per team, w_t = 1 - 0.9^(N_t), N_t = contests played.

    Returns (w_team, n_contests), both indexed by team. A team appears once per
    contest, so its appearance count is its contest count.
    """
    n_contests = np.bincount(ds.team_of_row, minlength=len(ds.teams))
    return 1.0 - np.power(0.9, n_contests), n_contests


def _performance_ratings(thetas, ds, rows_by_contest, lo=elo.LO, hi=elo.HI, tol=1e-4):
    """Vectorized eq. perf for every row, grouped by contest.

    For team i in a contest, solve sum_{j!=i} pi(theta_j, b_i) = rank_i - 1.
    """
    rho = np.empty(len(ds.team_of_row))
    for rows in rows_by_contest:
        th = thetas[ds.team_of_row[rows]]          # (N,) abilities in this contest
        target = ds.rank_of_row[rows] - 1.0        # (N,) expected superiors
        b = _bisect_contest(th, target, lo, hi, tol)
        rho[rows] = b
    return rho


def _bisect_contest(th, target, lo, hi, tol, grid_n=2048):
    """Per-team root b_i of f_i(b) = sum_{j!=i} pi(theta_j, b_i) - target_i.

    f is strictly decreasing in b; clamp to [lo, hi] where no interior root.

    The shared term sum_j pi(theta_j, b) is one monotone function G(b), the same
    for every team i in the contest; only the self-term pi(theta_i, b_i) differs.
    Rather than rebuild the dense (N, N) matrix pi(theta_j, b_i) on every bisection
    step (O(N^2) per step), we sample G(b) once on a grid (O(N * grid_n)) and read
    it back by interpolation (O(N) per step). The self-term stays exact. Grid error
    in G is ~1e-3 ELO at grid_n=2048, far below the eps convergence threshold.
    """
    grid = np.linspace(lo, hi, grid_n)
    # G[k] = sum_j pi(theta_j, grid[k]); built once, shared by all teams i
    G = (1.0 / (1.0 + np.power(10.0, (grid[:, None] - th[None, :]) / 400.0))).sum(axis=1)

    def f(b):  # b: (N,) candidate per team i
        Gb = np.interp(b, grid, G)                                # sum_j pi(theta_j, b_i)
        self_term = 1.0 / (1.0 + np.power(10.0, (b - th) / 400.0))  # pi(theta_i, b_i)
        return Gb - self_term - target

    n = th.shape[0]
    a = np.full(n, lo)
    c = np.full(n, hi)
    fa, fc = f(a), f(c)
    # decreasing f: interior root only where f(lo) > 0 and f(hi) < 0
    interior = (fa > 0.0) & (fc < 0.0)
    out = np.where(fa <= 0.0, lo, hi)  # f(lo)<=0 -> floor, else (f(hi)>=0) -> ceiling
    if interior.any():
        ai, ci = a.copy(), c.copy()
        for _ in range(60):
            if (ci - ai).max() <= tol:
                break
            m = 0.5 * (ai + ci)
            fm = f(m)
            hi_side = fm > 0.0
            ai = np.where(hi_side, m, ai)
            ci = np.where(hi_side, ci, m)
        mid = 0.5 * (ai + ci)
        out = np.where(interior, mid, out)
    return out


def estimate(ds=None, eps=0.5, max_iter=100, verbose=True,
             prior_mu=None, prior_strength=None):
    """Alternating fixed point for abilities, then problem difficulties.

    ``prior_mu`` / ``prior_strength`` are the per-team prior mean and its strength
    (in pseudo-contests). They default to the scalar neutral prior (MU0 at
    strength PRIOR_STRENGTH) for every team; pass per-team arrays to anchor
    selected teams to an external scale (see ``anchor.estimate_anchored``).
    """
    if verbose: print("Loading...\n")
    if ds is None:
        ds = load()
    if prior_mu is None:
        prior_mu = MU0
    if prior_strength is None:
        prior_strength = PRIOR_STRENGTH

    n_teams = len(ds.teams)
    theta = np.full(n_teams, MU0)
    w_team, n_contests = _team_weights(ds)

    rows_by_contest = [
        np.where(ds.contest_of_row == ci)[0] for ci in range(len(ds.contests))
    ]

    # denominator of the evidence-weighted update: w_t * N_t + prior_strength
    denom = w_team * n_contests + prior_strength

    history = []
    if verbose: print("Iterating...\n")
    for it in range(max_iter):
        rho = _performance_ratings(theta, ds, rows_by_contest)
        # numerator: w_t * sum_c rho_{t,c} + PRIOR_STRENGTH * MU0
        sum_rho = np.zeros(n_teams)
        np.add.at(sum_rho, ds.team_of_row, rho)
        numer = w_team * sum_rho + prior_strength * prior_mu
        new_theta = np.clip(numer / denom, elo.LO, elo.HI)

        delta = np.max(np.abs(new_theta - theta))
        history.append(delta)
        theta = new_theta
        if verbose:
            print(f"  iter {it:3d}  max|dtheta| = {delta:8.3f}")
        if delta < eps:
            break

    # final per-row performance ratings (eq. perf) consistent with converged theta
    rho = _performance_ratings(theta, ds, rows_by_contest)
    b = _rate_problems(theta, w_team, ds)
    return theta, b, rho, history


def _rate_problems(theta, w_team, ds):
    """b_p = WR({(w_t, theta_t)}, S_p), S_p = sum_t w_t y_tp (eq. bp).

    Down-weights unreliable (few-contest) teams via the same reliability weight.
    """
    b = np.empty(len(ds.problems))
    for p in range(len(ds.problems)):
        ci = ds.contest_of_problem[p]
        rows = np.where(ds.contest_of_row == ci)[0]
        teams = ds.team_of_row[rows]
        thetas = theta[teams]
        weights = w_team[teams]
        solved = ds.y[rows, p] & ds.solve_mask[rows, p]
        S_p = np.sum(weights * solved)
        b[p] = elo.weighted_rating(thetas, S_p, weights=weights)
    return b


if __name__ == "__main__":
    ds = load()
    theta, b, rho, history = estimate(ds, verbose=True)
    print(f"converged in {len(history)} iters, final max|dtheta| = {history[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
    # monotone-ish convergence check
    assert history[-1] < 0.5
    print("fixedpoint.py self-checks passed")
