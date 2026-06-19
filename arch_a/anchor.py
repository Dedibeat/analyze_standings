"""Anchor the full tagged.json fit to the Universal Cup scale.

The neutral MU0 prior lets every fit float to its own scale, so a tagged-only fit
and a UCup-only fit are not directly comparable -- the same team can land at very
different abilities in each. We instead derive a trusted scale from a UCup-only
fit (seasons s3 + s4, a densely cross-linked league) and feed each UCup team's
converged ability theta_u back as the *prior mean* for that same team in the full
tagged fit. Teams absent from UCup keep the neutral MU0 prior; the cross-contest
linking graph then carries the UCup scale to them.

Anchor strength is the team's UCup evidence w_u * N_u (scaled by ``anchor_weight``):
a team seen in many UCup rounds is pinned hard to its UCup ability, a one-off team
only loosely. It is folded together with the standing MU0 pseudo-contest, so a
weakly-seen UCup team still gets the MU0 cold start:

    s_a   = anchor_weight * w_u * N_u                    (UCup pseudo-contests)
    mu    = (PRIOR_STRENGTH*MU0 + s_a*theta_u) / (PRIOR_STRENGTH + s_a)
    str   =  PRIOR_STRENGTH + s_a

Identity must be shared across the two fits: ``team_key`` resolves through a
union-find whose component root depends on union order, so both datasets are
loaded under one union-find built from tagged + UCup together.
"""

import json
import os

import numpy as np

from .fixedpoint import MU0, PRIOR_STRENGTH, _team_weights, estimate
from .load import load, member_identity

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
TAGGED = os.path.join(DATA, "tagged.json")
UCUP = [os.path.join(DATA, "ucup_s3.json"), os.path.join(DATA, "ucup_s4.json")]


def estimate_anchored(anchor_weight=1.0, verbose=True):
    """Fit tagged.json with its UCup teams anchored to a UCup-only fit.

    Returns (ds_tagged, theta, b, rho, history, uf) for the anchored tagged fit.
    ``uf`` is the shared union-find both fits resolved identity through, so callers
    can map raw standing rows to ``ds_tagged.teams`` via ``team_key``.
    """
    raw_all = []
    for p in [TAGGED] + UCUP:
        with open(p) as f:
            raw_all.extend(json.load(f))
    uf = member_identity(raw_all)  # one identity space for both fits

    ds_ucup = load(UCUP, uf=uf)
    ds_tagged = load(TAGGED, uf=uf)

    if verbose: print("=== UCup anchor fit (s3 + s4) ===")
    theta_u, _, _, _ = estimate(ds_ucup, verbose=verbose)
    w_u, n_u = _team_weights(ds_ucup)
    evid_u = w_u * n_u  # UCup evidence per UCup team

    anchor = {  # team_key -> (UCup ability, UCup evidence)
        ds_ucup.teams[i]: (theta_u[i], evid_u[i]) for i in range(len(ds_ucup.teams))
    }

    prior_mu = np.full(len(ds_tagged.teams), MU0)
    prior_strength = np.full(len(ds_tagged.teams), float(PRIOR_STRENGTH))
    n_anchored = 0
    for i, tk in enumerate(ds_tagged.teams):
        hit = anchor.get(tk)
        if hit is None:
            continue
        th_u, ev = hit
        s_a = anchor_weight * ev
        prior_strength[i] = PRIOR_STRENGTH + s_a
        prior_mu[i] = (PRIOR_STRENGTH * MU0 + s_a * th_u) / prior_strength[i]
        n_anchored += 1
    if verbose:
        print(f"anchored {n_anchored} of {len(ds_tagged.teams)} tagged teams "
              f"to UCup (anchor_weight={anchor_weight})")

    if verbose: print("=== anchored tagged fit ===")
    theta, b, rho, history = estimate(
        ds_tagged, verbose=verbose, prior_mu=prior_mu, prior_strength=prior_strength
    )
    return ds_tagged, theta, b, rho, history, uf


if __name__ == "__main__":
    ds, theta, b, rho, hist, _ = estimate_anchored()
    print(f"converged in {len(hist)} iters, final max|dtheta| = {hist[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
