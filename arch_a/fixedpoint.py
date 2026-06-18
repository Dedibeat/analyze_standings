"""Architecture A: alternating estimation of abilities and difficulties.

strat.tex Algorithm 1. Abilities theta_t and difficulties b_p are mutually
dependent, so they are solved by alternation:

    repeat
        for each team in each contest: performance rating rho_{t,c}  (eq. perf)
        for each team: ability update theta_t                        (eq. update)
    until max |delta theta| < eps
    for each problem: difficulty b_p                                  (eq. bp)

Anchoring. The strat anchors the scale through the Codeforces ratings of team
members (eq. cfprior), which seed theta_prior. No CF ratings exist in this data,
so we use a constant neutral prior MU0 (a mid Codeforces rating) for every team.
The blend toward theta_prior in eq. update then anchors the global shift on the
Codeforces scale and keeps abilities inside the [800, 4000] working range -- the
role the CF bootstrap would otherwise play. (Mean-centering to 0 is incompatible
with that range, since the clamp is applied during the bisection.)
"""

import numpy as np

from . import elo
from .load import load

MU0 = 2000.0  # neutral prior mean (mid Codeforces rating); anchors the scale


def _experience_weights(ds):
    """w_{t,c} = 1 - 0.9^(n+1), n = prior appearances of the team (eq. weight).

    Contests are ordered by contest_id; a team's n-th appearance in that order
    has n prior contests. Returns an array aligned with ds rows.
    """
    order_rank = np.empty(len(ds.contests), dtype=int)
    order_rank[ds.contest_order] = np.arange(len(ds.contests))

    rows = np.arange(len(ds.team_of_row))
    # sort rows by (team, contest order) and count prior appearances per team
    key = order_rank[ds.contest_of_row]
    sort_idx = sorted(rows, key=lambda i: (ds.team_of_row[i], key[i]))
    n_prior = np.empty(len(rows), dtype=int)
    prev_team = -1
    count = 0
    for i in sort_idx:
        t = ds.team_of_row[i]
        if t != prev_team:
            count = 0
            prev_team = t
        n_prior[i] = count
        count += 1
    return 1.0 - np.power(0.9, n_prior + 1)


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


def _bisect_contest(th, target, lo, hi, tol):
    """Per-team root b_i of f_i(b) = sum_{j!=i} pi(theta_j, b_i) - target_i.

    f is strictly decreasing in b; clamp to [lo, hi] where no interior root.
    """
    th = th[None, :]  # (1, N) abilities of all teams (the j index)

    def f(b):  # b: (N,) candidate per team i
        # M[i, j] = pi(theta_j, b_i)
        M = 1.0 / (1.0 + np.power(10.0, (b[:, None] - th) / 400.0))
        self_term = 1.0 / (1.0 + np.power(10.0, (b - th[0]) / 400.0))  # pi(theta_i, b_i)
        return M.sum(axis=1) - self_term - target

    n = th.shape[1]
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


def estimate(ds=None, eps=0.5, max_iter=100, verbose=False):
    if ds is None:
        ds = load()

    n_teams = len(ds.teams)
    theta = np.full(n_teams, MU0)
    theta_prior = np.full(n_teams, MU0)
    w_row = _experience_weights(ds)

    rows_by_contest = [
        np.where(ds.contest_of_row == ci)[0] for ci in range(len(ds.contests))
    ]

    # denominator of eq. update: sum of experience weights per team
    denom = np.zeros(n_teams)
    np.add.at(denom, ds.team_of_row, w_row)

    history = []
    for it in range(max_iter):
        rho = _performance_ratings(theta, ds, rows_by_contest)
        # numerator: sum_c w_{t,c} * 0.5 * (rho_{t,c} + theta_prior_t)
        contrib = w_row * 0.5 * (rho + theta_prior[ds.team_of_row])
        numer = np.zeros(n_teams)
        np.add.at(numer, ds.team_of_row, contrib)
        new_theta = np.where(denom > 0, numer / np.maximum(denom, 1e-12), theta_prior)
        new_theta = np.clip(new_theta, elo.LO, elo.HI)

        delta = np.max(np.abs(new_theta - theta))
        history.append(delta)
        theta = new_theta
        if verbose:
            print(f"  iter {it:3d}  max|dtheta| = {delta:8.3f}")
        if delta < eps:
            break

    b = _rate_problems(theta, w_row, ds)
    return theta, b, history


def _rate_problems(theta, w_row, ds):
    """b_p = WR({(w_t, theta_t)}, S_p), S_p = sum_t w_t y_tp (eq. bp).

    Uses each team's final experience weight (last appearance), matching the
    converged abilities.
    """
    # final weight per team = max weight observed (most experienced appearance)
    team_weight = np.zeros(len(ds.teams))
    np.maximum.at(team_weight, ds.team_of_row, w_row)

    b = np.empty(len(ds.problems))
    for p in range(len(ds.problems)):
        ci = ds.contest_of_problem[p]
        rows = np.where(ds.contest_of_row == ci)[0]
        teams = ds.team_of_row[rows]
        thetas = theta[teams]
        weights = team_weight[teams]
        solved = ds.y[rows, p] & ds.solve_mask[rows, p]
        S_p = np.sum(weights * solved)
        b[p] = elo.weighted_rating(thetas, S_p, weights=weights)
    return b


if __name__ == "__main__":
    ds = load()
    theta, b, history = estimate(ds, verbose=True)
    print(f"converged in {len(history)} iters, final max|dtheta| = {history[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
    # monotone-ish convergence check
    assert history[-1] < 0.5
    print("fixedpoint.py self-checks passed")
