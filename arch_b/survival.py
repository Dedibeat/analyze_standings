"""Architecture B with the solve-time survival likelihood (strat.tex section 5).

The binary Rasch model (``model.py``) throws away *when* a problem was solved.
Here we model the act of solving as a constant-hazard (exponential) process over
the contest window, with proportional hazards in the ability--difficulty gap
(eq. hazard):

    lambda_tp = lambda0 * exp((theta_t - b_p) / s)

A team that solves p at time tau_tp contributes the event density, a team that
never solves it contributes the survival probability to the contest end T_c
(a right-censored observation), giving the per-pair log-likelihood (eq. survlik):

    l_tp = log lambda_tp - lambda_tp * tau_tp     if solved at tau_tp
         = -lambda_tp * T_c                        if censored at T_c

Baseline hazard (deviation from the strat). The strat leaves lambda0 a free
parameter. But lambda0 is globally confounded with the overall level of b: a shift
b_p -> b_p + delta for all p is exactly log lambda0 -> log lambda0 - delta/s, so
the two cannot both float. We therefore *fix* the baseline per contest at

    lambda0_c = ln 2 / T_c,

which (a) removes the confounding and (b) calibrates difficulty exactly as the
binary model does -- at theta=b the probability of solving within the window is
1 - exp(-lambda0_c * T_c) = 1/2 -- so survival b_p lives on the same coin-flip
scale as the Rasch b_p and the two are directly comparable. With this calibration
the cumulative hazard collapses to

    Lambda_tp = ln2 * exp((theta_t - b_p)/s) * rho_tp,
    rho_tp = tau_tp / T_c  (solved)   or   1  (censored),

so T_c enters only through the fraction rho of the window a solve used (it cancels
for censored cells), making the fit robust to T_c misspecification. T_c is taken
per contest as the latest observed solve time (no duration field in the data).

Estimation is the same strictly-concave MAP as ``model.py`` (the survival
log-likelihood is concave in theta, b and the Gaussian prior is strictly concave),
solved by the same block-coordinate Newton -- only the per-cell ``resid`` and
``info`` change: residual y - Lambda and curvature term Lambda (vs y - pi and
pi(1-pi) in the binary model), the Poisson-GLM form of this likelihood.
"""

import numpy as np

from arch_a import elo
from .model import MU0, SIGMA_B, SIGMA_THETA

LN2 = np.log(2.0)
DEFAULT_TC = 18000.0  # fallback window (5 h) for a contest with no observed solves


def _survival_observations(ds):
    """Flatten Obs into (obs_team, obs_prob, obs_y, rho) with the exposure ratio.

    rho_tp = tau_tp / T_c for a solved cell (fraction of the window used) and 1 for
    a censored cell. T_c per contest is the latest observed solve time.
    """
    obs_row, obs_prob = np.nonzero(ds.solve_mask)
    obs_team = ds.team_of_row[obs_row]
    obs_y = ds.y[obs_row, obs_prob].astype(float)
    obs_contest = ds.contest_of_problem[obs_prob]
    solved = obs_y > 0
    tau = np.nan_to_num(ds.tau[obs_row, obs_prob])  # 0 where censored (unused)

    n_contests = len(ds.contests)
    Tc = np.zeros(n_contests)
    np.maximum.at(Tc, obs_contest[solved], tau[solved])
    Tc[Tc <= 0] = DEFAULT_TC

    rho = np.where(solved, tau / Tc[obs_contest], 1.0)
    return obs_team, obs_prob, obs_y, rho


def fit(ds, prior_mu=None, sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B, mu_b=MU0,
        eps=0.5, max_iter=200, verbose=True):
    """MAP fit of the survival model; returns (theta, b, history).

    Signature matches ``model.fit`` so it is a drop-in for
    ``anchor.estimate_anchored(fit_fn=...)``.
    """
    if prior_mu is None:
        prior_mu = np.full(len(ds.teams), MU0)
    obs_team, obs_prob, obs_y, rho = _survival_observations(ds)

    s = elo.S
    prec_theta = 1.0 / sigma_theta**2
    prec_b = 1.0 / sigma_b**2
    n_teams, n_problems = len(ds.teams), len(ds.problems)

    theta = np.full(n_teams, MU0)
    b = np.full(n_problems, mu_b)

    def newton_block(param, index, mu, prec, sign):
        g = (theta[obs_team] - b[obs_prob]) / s
        Lam = LN2 * np.exp(g) * rho          # cumulative hazard per cell
        resid = obs_y - Lam
        grad = np.zeros_like(param)
        negH = np.full_like(param, prec)
        np.add.at(grad, index, resid)
        np.add.at(negH, index, Lam / s**2)   # d Lambda / d param = Lambda / s
        grad = sign * grad / s - prec * (param - mu)
        return np.clip(param + grad / negH, elo.LO, elo.HI)

    history = []
    if verbose:
        print(f"Iterating ({len(obs_y)} observations, "
              f"{n_teams} teams, {n_problems} problems)...\n")
    for it in range(max_iter):
        new_theta = newton_block(theta, obs_team, prior_mu, prec_theta, +1.0)
        d_theta = np.max(np.abs(new_theta - theta))
        theta = new_theta
        new_b = newton_block(b, obs_prob, mu_b, prec_b, -1.0)
        d_b = np.max(np.abs(new_b - b))
        b = new_b

        delta = max(d_theta, d_b)
        history.append(delta)
        if verbose:
            print(f"  iter {it:3d}  max|dtheta|={d_theta:8.3f}  max|db|={d_b:8.3f}")
        if delta < eps:
            break

    return theta, b, history


def laplace_se(ds, theta, b, sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B):
    """Per-parameter Laplace standard errors for the survival fit; (se_theta, se_b).

    Same observed-information SE as ``model.laplace_se``, with the survival
    curvature term Lambda in place of the binary pi(1-pi).
    """
    obs_team, obs_prob, _, rho = _survival_observations(ds)
    g = (theta[obs_team] - b[obs_prob]) / elo.S
    Lam = LN2 * np.exp(g) * rho
    negH_theta = np.full(len(theta), 1.0 / sigma_theta**2)
    negH_b = np.full(len(b), 1.0 / sigma_b**2)
    np.add.at(negH_theta, obs_team, Lam / elo.S**2)
    np.add.at(negH_b, obs_prob, Lam / elo.S**2)
    return 1.0 / np.sqrt(negH_theta), 1.0 / np.sqrt(negH_b)


if __name__ == "__main__":
    from arch_a.load import load

    ds = load()
    theta, b, history = fit(ds, verbose=True)
    se_theta, se_b = laplace_se(ds, theta, b)
    print(f"converged in {len(history)} iters, final max delta = {history[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
    print(f"b SE range:  [{se_b.min():.0f}, {se_b.max():.0f}], median {np.median(se_b):.0f}")
    assert history[-1] < 0.5
    print("survival.py self-checks passed")
