"""Architecture B: joint item-response (Rasch) model, fit by MAP.

strat.tex section 4. Each solve is a Bernoulli response governed by the gap
between team ability and problem difficulty (eq. rasch):

    Pr(y_tp = 1 | theta_t, b_p) = sigma((theta_t - b_p) / s) = pi(theta_t, b_p)

The same theta_t appears in every contest team t entered, so contests sharing a
team are linked automatically -- no post-hoc rescaling (contrast Architecture A,
where the coupling lives in an explicit ability-update step).

Gaussian priors regularize sparsely observed teams and problems (eq. priors), and
the estimate is the maximum-a-posteriori point (eq. map):

    maximize  sum_{(t,p) in Obs} [ y log pi + (1-y) log(1-pi) ]
              - (1/2 sigma_theta^2) sum_t (theta_t - mu_t)^2
              - (1/2 sigma_b^2)     sum_p (b_p     - mu_b)^2

This objective is strictly concave (a concave log-likelihood plus a strictly
concave Gaussian prior), so the MAP point is unique. A problem solved by nobody
contributes only sum_t log(1 - pi), which pushes b_p up but is held finite by the
prior -- so the bare-likelihood b_p -> +inf does not occur, and Architecture A's
boundary-smoothing dummy teams are unnecessary here.

Optimizer. The objective splits into per-team and per-problem terms that are each
a 1-D concave function of a single parameter (given the others), so we run
block-coordinate Newton: one exact Newton step over all theta (given b), then one
over all b (given the new theta). Each step is closed form and vectorized via
np.add.at -- numpy only, no learning rate. Strict concavity makes every 1-D
Newton step a guaranteed ascent toward that coordinate's optimum, and the blocks
alternate to a fixed point.
"""

import numpy as np

from arch_a import elo

MU0 = 2000.0          # neutral prior mean (mid Codeforces rating); anchors the scale
SIGMA_THETA = 200.0   # ability prior std (eq. priors): regularization knob
SIGMA_B = 200.0       # difficulty prior std (eq. priors): regularization knob


def _observations(ds):
    """Flatten the observed competitor--problem pairs Obs into 1-D arrays.

    Returns (obs_team, obs_prob, obs_y): for every (row, problem) cell that
    belongs to the row's contest (solve_mask), the team index, problem index, and
    the 0/1 solve outcome. A team plays several contests (several rows), all
    sharing one theta_t -- that shared index is what links the contests.
    """
    obs_row, obs_prob = np.nonzero(ds.solve_mask)
    obs_team = ds.team_of_row[obs_row]
    obs_y = ds.y[obs_row, obs_prob].astype(float)
    return obs_team, obs_prob, obs_y


def fit(ds, prior_mu=None, sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B, mu_b=MU0,
        eps=0.5, max_iter=200, verbose=True):
    """MAP fit of the Rasch model (eq. map); returns (theta, b, history).

    ``prior_mu`` is the per-team prior mean mu_t (eq. priors); defaults to the
    scalar neutral MU0 for every team. Pass a per-team array to anchor selected
    teams to an external scale (see ``anchor.estimate_anchored``). ``history`` is
    the per-iteration max parameter change.
    """
    if prior_mu is None:
        prior_mu = np.full(len(ds.teams), MU0)
    obs_team, obs_prob, obs_y = _observations(ds)

    s = elo.S
    prec_theta = 1.0 / sigma_theta**2   # prior precision (Hessian/gradient terms)
    prec_b = 1.0 / sigma_b**2
    n_teams, n_problems = len(ds.teams), len(ds.problems)

    theta = np.full(n_teams, MU0)
    b = np.full(n_problems, mu_b)

    def newton_block(param, index, other, other_index, mu, prec, sign):
        """One Newton step for a block of parameters sharing the response pi.

        ``param`` is updated; ``other`` is held fixed. ``sign`` is +1 for theta
        (logit increases with theta) and -1 for b (logit decreases with b). The
        per-coordinate gradient is sign*(1/s)*sum(y - pi) - prec*(param - mu); the
        negative curvature is (1/s^2)*sum pi(1-pi) + prec.
        """
        pi = elo.pi(theta[obs_team], b[obs_prob])
        resid = obs_y - pi
        info = pi * (1.0 - pi)
        grad = np.zeros_like(param)
        negH = np.full_like(param, prec)
        np.add.at(grad, index, resid)
        np.add.at(negH, index, info / s**2)
        grad = sign * grad / s - prec * (param - mu)
        step = grad / negH
        return np.clip(param + step, elo.LO, elo.HI)

    history = []
    if verbose:
        print(f"Iterating ({len(obs_y)} observations, "
              f"{n_teams} teams, {n_problems} problems)...\n")
    for it in range(max_iter):
        new_theta = newton_block(theta, obs_team, b, obs_prob, prior_mu, prec_theta, +1.0)
        d_theta = np.max(np.abs(new_theta - theta))
        theta = new_theta
        new_b = newton_block(b, obs_prob, theta, obs_team, mu_b, prec_b, -1.0)
        d_b = np.max(np.abs(new_b - b))
        b = new_b

        delta = max(d_theta, d_b)
        history.append(delta)
        if verbose:
            print(f"  iter {it:3d}  max|dtheta|={d_theta:8.3f}  max|db|={d_b:8.3f}")
        if delta < eps:
            break

    return theta, b, history


if __name__ == "__main__":
    from arch_a.load import load

    ds = load()
    theta, b, history = fit(ds, verbose=True)
    print(f"converged in {len(history)} iters, final max delta = {history[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
    assert history[-1] < 0.5
    print("model.py self-checks passed")
