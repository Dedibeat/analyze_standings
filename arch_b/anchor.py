"""Anchor the full tagged.json IRT fit to the Universal Cup scale.

Same two-phase idea as ``arch_a.anchor``, adapted to the Bayesian model: the
neutral MU0 prior lets every fit float to its own scale, so a tagged-only fit and
a UCup-only fit are not directly comparable. We fit the densely cross-linked UCup
seasons (s3 + s4) alone, then feed each UCup team's converged ability theta_u back
as the *Gaussian prior mean* mu_t (eq. priors) for that same team in the full
tagged fit. Teams absent from UCup keep the neutral MU0 prior mean; the shared
theta_t across contests then carries the UCup scale to them through the likelihood.

The anchor is the prior mean only; the pull strength is the single global
sigma_theta (the prior precision). Unlike ``arch_a.anchor``, the strength is not
scaled per team by UCup evidence -- a well-observed UCup team is already pinned by
its own likelihood, so the prior chiefly matters for sparse teams. ``sigma_theta``
is therefore the one anchor knob: tighter pins the shared teams harder to UCup.

Identity must be shared across the two fits: ``team_key`` resolves through a
union-find whose component root depends on union order, so both datasets are
loaded under one union-find built from tagged + UCup together.
"""

import json
import os

import numpy as np

from arch_a.load import _max_solve_seconds, load, member_identity, season_of
from .model import MU0, SIGMA_B, SIGMA_THETA, fit

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
TAGGED = os.path.join(DATA, "tagged.json")
UCUP = [os.path.join(DATA, "ucup_s3.json"), os.path.join(DATA, "ucup_s4.json")]


def estimate_anchored(sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B, fit_fn=fit,
                      season_key=False, min_solve_hours=None, verbose=True):
    """Fit tagged.json with its UCup teams' prior mean anchored to a UCup-only fit.

    Returns (ds_tagged, theta, b, history, uf) for the anchored tagged fit. ``uf``
    is the shared union-find both fits resolved identity through, so callers can
    map raw standing rows to ``ds_tagged.teams`` via ``team_key``.

    ``fit_fn`` is the MAP fitter, ``model.fit`` (binary Rasch) by default; pass
    ``survival.fit`` to anchor the solve-time survival model on the same scale.
    ``season_key`` / ``min_solve_hours`` are passed through to ``load`` (and the
    shared union-find) to separate teams by season and drop short contests.
    """
    raw_all = []
    for p in [TAGGED] + UCUP:
        with open(p) as f:
            raw_all.extend(json.load(f))
    if min_solve_hours is not None:
        raw_all = [c for c in raw_all if _max_solve_seconds(c) >= min_solve_hours * 3600]
    season_by_cid = {c["contest_id"]: season_of(c) for c in raw_all} if season_key else None
    uf = member_identity(raw_all, season_by_cid)  # one identity space for both fits

    ds_ucup = load(UCUP, uf=uf, season_key=season_key, min_solve_hours=min_solve_hours)
    ds_tagged = load(TAGGED, uf=uf, season_key=season_key, min_solve_hours=min_solve_hours)

    if verbose: print("=== UCup anchor fit (s3 + s4) ===")
    theta_u, _, _ = fit_fn(ds_ucup, sigma_theta=sigma_theta, sigma_b=sigma_b, verbose=verbose)
    anchor = {ds_ucup.teams[i]: theta_u[i] for i in range(len(ds_ucup.teams))}

    prior_mu = np.full(len(ds_tagged.teams), MU0)
    n_anchored = 0
    for i, tk in enumerate(ds_tagged.teams):
        hit = anchor.get(tk)
        if hit is not None:
            prior_mu[i] = hit
            n_anchored += 1
    if verbose:
        print(f"anchored {n_anchored} of {len(ds_tagged.teams)} tagged teams to UCup")

    if verbose: print("=== anchored tagged fit ===")
    theta, b, history = fit_fn(ds_tagged, prior_mu=prior_mu,
                               sigma_theta=sigma_theta, sigma_b=sigma_b, verbose=verbose)
    return ds_tagged, theta, b, history, uf


if __name__ == "__main__":
    ds, theta, b, hist, _ = estimate_anchored()
    print(f"converged in {len(hist)} iters, final max delta = {hist[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
