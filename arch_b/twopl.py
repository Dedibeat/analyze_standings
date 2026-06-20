"""Architecture B, 2PL extension: per-problem discrimination (strat.tex eq. twopl).

PROTOTYPE. The shipped fit (model.py) is the 1-parameter Rasch model: every
problem shares the same logistic slope 1/s, so the only thing that varies between
problems is where the 50%-solve point b_p sits. The 2PL model adds a per-problem
discrimination a_p > 0,

    Pr(y_tp = 1) = sigma(a_p (theta_t - b_p)),                      (eq. twopl)

letting some problems separate strong from weak teams more sharply than others. We
keep theta, b on the existing ELO scale by writing a_p = alpha_p / s with alpha_p a
dimensionless multiplier (Rasch == alpha_p == 1):

    eta_tp = alpha_p (theta_t - b_p) / s,     pi = sigma(eta_tp).

Identifiability. The 2PL likelihood is invariant to theta->c*theta, b->c*b,
alpha->alpha/c, so the overall scale of theta is not pinned by the likelihood
alone. The two priors fix it: the Gaussian theta prior (mu_t, sigma_theta) anchors
the ability scale (as in Rasch), and a Gaussian prior on g_p = log alpha_p,
g_p ~ N(0, sigma_g^2), anchors discrimination to the Rasch value 1 and regularizes
sparsely-observed problems back toward it.

Optimizer. Same block-coordinate Newton as model.py, now three blocks. Given the
other two, each block is concave: theta and b enter eta linearly (their blocks are
identical in form to Rasch, with the constant 1/s replaced by alpha_p/s), and
log-discrimination g_p is a 1-D logistic-regression slope. The joint objective is
*non-convex* (the alpha*theta interaction), so we (a) warm-start from a Rasch basin
-- the first ``warmup`` iters hold alpha=1 -- and (b) use Fisher scoring (expected
information) for the g block, whose observed Hessian can be indefinite. The theta/b
blocks keep the exact observed-information Newton step (their second-order term in
eta vanishes, so observed == expected there).

    python -m arch_b.twopl        # self-check on tagged.json
"""

import numpy as np

from arch_a import elo
from .model import MU0, SIGMA_B, SIGMA_THETA, _observations

SIGMA_G = 0.5         # prior std of log-discrimination: alpha in ~[0.37, 2.7] at 1sd
G_LO, G_HI = -1.5, 1.5   # clamp log-alpha (alpha in [0.22, 4.5]) for degenerate problems


def _sigmoid(x):
    """Numerically stable logistic."""
    out = np.empty_like(x)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def fit_full(ds, prior_mu=None, sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B, mu_b=MU0,
             sigma_g=SIGMA_G, warmup=15, eps=0.5, eps_g=0.005, max_iter=400,
             verbose=True, obs=None):
    """MAP fit of the 2PL model; returns (theta, b, alpha, history).

    Same arguments as ``model.fit`` plus ``sigma_g`` (log-discrimination prior std)
    and ``warmup`` (Rasch-only iterations before the discrimination block turns on).
    ``alpha`` is the per-problem discrimination multiplier (Rasch == 1).
    """
    if prior_mu is None:
        prior_mu = np.full(len(ds.teams), MU0)
    obs_team, obs_prob, obs_y = _observations(ds) if obs is None else obs

    s = elo.S
    prec_theta = 1.0 / sigma_theta**2
    prec_b = 1.0 / sigma_b**2
    prec_g = 1.0 / sigma_g**2
    n_teams, n_problems = len(ds.teams), len(ds.problems)

    theta = np.full(n_teams, MU0)
    b = np.full(n_problems, mu_b)
    g = np.zeros(n_problems)            # log discrimination; alpha = exp(g)

    def linear_block(param, index, mu, prec, n, sign, d):
        """Newton step for theta (sign=+1) or b (sign=-1); d = per-obs alpha/s."""
        eta = d * (theta[obs_team] - b[obs_prob])
        pi = _sigmoid(eta)
        resid = obs_y - pi
        info = pi * (1.0 - pi)
        grad = np.zeros(n)
        negH = np.full(n, prec)
        np.add.at(grad, index, sign * d * resid)
        np.add.at(negH, index, d * d * info)
        grad -= prec * (param - mu)
        return np.clip(param + grad / negH, elo.LO, elo.HI)

    history = []
    if verbose:
        print(f"Iterating ({len(obs_y)} observations, "
              f"{n_teams} teams, {n_problems} problems)...\n")
    for it in range(max_iter):
        alpha = np.exp(g)
        d = alpha[obs_prob] / s

        new_theta = linear_block(theta, obs_team, prior_mu, prec_theta, n_teams, +1.0, d)
        d_theta = np.max(np.abs(new_theta - theta)); theta = new_theta
        new_b = linear_block(b, obs_prob, mu_b, prec_b, n_problems, -1.0, d)
        d_b = np.max(np.abs(new_b - b)); b = new_b

        d_g = 0.0
        if it >= warmup:                 # discrimination block (Fisher scoring)
            eta = (alpha[obs_prob] / s) * (theta[obs_team] - b[obs_prob])
            pi = _sigmoid(eta)
            resid = obs_y - pi
            info = pi * (1.0 - pi)
            grad = np.zeros(n_problems)
            negH = np.full(n_problems, prec_g)
            np.add.at(grad, obs_prob, resid * eta)        # d eta / d g = eta
            np.add.at(negH, obs_prob, info * eta * eta)   # Fisher information
            grad -= prec_g * g
            new_g = np.clip(g + grad / negH, G_LO, G_HI)
            d_g = np.max(np.abs(new_g - g)); g = new_g

        delta = max(d_theta, d_b)
        history.append(delta)
        if verbose:
            print(f"  iter {it:3d}  max|dtheta|={d_theta:7.3f}  max|db|={d_b:7.3f}  "
                  f"max|dg|={d_g:.4f}  alpha[{np.exp(g).min():.2f},{np.exp(g).max():.2f}]")
        if it >= warmup and delta < eps and d_g < eps_g:
            break

    return theta, b, np.exp(g), history


def fit(ds, **kwargs):
    """Drop-in for ``model.fit`` / ``anchor.estimate_anchored`` (drops alpha)."""
    theta, b, _alpha, history = fit_full(ds, **kwargs)
    return theta, b, history


if __name__ == "__main__":
    from arch_a.load import load

    ds = load()
    theta, b, alpha, history = fit_full(ds, verbose=True)
    print(f"\nconverged in {len(history)} iters, final max delta = {history[-1]:.4f}")
    print(f"theta: [{theta.min():.0f}, {theta.max():.0f}] mean {theta.mean():.0f}")
    print(f"b:     [{b.min():.0f}, {b.max():.0f}] mean {b.mean():.0f}")
    print(f"alpha: [{alpha.min():.2f}, {alpha.max():.2f}] "
          f"median {np.median(alpha):.2f}")
