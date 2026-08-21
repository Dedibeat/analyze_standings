"""Fit every contest -- tagged, supplemental, and Universal Cup -- in one MAP.

Architecture B used to fit in two phases: the densely cross-linked Universal Cup
seasons alone, then ``tagged.json`` with each UCup team's converged ability fed
back as its Gaussian prior *mean* (``arch_a.anchor`` still does exactly that, and
there it measurably tightens the scale). The 2026-08-21 anchoring audit measured
what that prior actually buys in the Bayesian model: replacing it with the flat
``MU0`` moves difficulties by mean -3.6 with sd 0.96 (corr 0.999997) and leaves
the calibrated LOCO metric at 244.3, unchanged to the decimal. At
``sigma_theta=400`` a well-observed team is already pinned by its own likelihood,
and the affine calibration leg absorbs any global level shift the prior could
produce, so the anchor was a no-op on the shipped deliverable.

What it *did* produce was a second scale. UCup problems were rated by the Phase-1
fit and then calibrated with a map fit on the Phase-2 domain; across the 305
problems both fits rated, ``b_ucup ~ 0.959*b_tagged + 36``, which pushed the
exported UCup ratings about 90 CF points low.

So the Universal Cup is now ordinary data in one joint fit. Measured cost on the
metric: 244.3 -> 245.4, inside the +-20 bootstrap noise floor and well under
``program.md``'s 5-point keep threshold; in exchange 684 more problems land on
the shipped scale and there is no second scale left to reconcile. This is only
affordable because ``arch_a.load`` now stores observed cells sparsely -- the old
dense layout needed ~11 GB at joint size.

Identity still resolves through one shared union-find built over every source, so
a roster recurring between a regional and a UCup round is one team. Contests
present in both ``tagged.json`` and the UCup seasons are deduplicated by
``dedupe_contests``, which keeps the ``tagged.json`` copy.
"""

import json
import os

import numpy as np

from arch_a.load import _max_solve_seconds, dedupe_contests, load, member_identity, season_of
from .model import MU0, SIGMA_B, SIGMA_THETA, fit

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
TAGGED = os.path.join(DATA, "tagged.json")
UCUP = [os.path.join(DATA, "ucup_s3.json"), os.path.join(DATA, "ucup_s4.json")]
WF = os.path.join(DATA, "wf_tagged_format.json")
OLDER_ICPC = os.path.join(DATA, "icpc_2020_2021.json")
PETROZ = os.path.join(DATA, "petroz_2022_2026.json")


def estimate_joint(sigma_theta=SIGMA_THETA, sigma_b=SIGMA_B, fit_fn=fit,
                   season_key=False, min_solve_hours=None, verbose=True,
                   gym_merge=None, supplemental_paths=None,
                   identity_paths=None, prior=None):
    """Fit tagged + supplemental + Universal Cup standings in one MAP.

    Returns ``(ds, theta, b, history, uf)``. ``uf`` is the union-find identity
    was resolved through, so callers can map raw standing rows to ``ds.teams``
    via ``team_key``.

    ``fit_fn`` is the MAP fitter, ``model.fit`` (binary Rasch) by default; pass
    ``survival.fit`` for the solve-time model. ``season_key`` /
    ``min_solve_hours`` are passed through to ``load`` (and the union-find) to
    separate teams by season and drop short contests.

    ``prior`` overrides the per-team Gaussian prior, which defaults to the
    neutral ``MU0`` at the global ``sigma_theta`` for every team. Pass a callable
    ``(ds, uf, sigma_theta, season_by_cid) -> (mu, sd)`` to anchor selected teams
    to an external ability scale; ``cf_prior.prior`` is one, built from the
    collected Codeforces participant ratings. Both fitters accept a per-team
    ``sigma_theta`` array, so the returned ``sd`` may vary by team.

    ``gym_merge`` (float weight, or the ``ARCHB_GYM_MERGE`` env var so the
    read-only ``metric.py`` can A/B it) merges the gym-mirror attempts into the
    fit as fixed-theta likelihood terms on ``b`` (``gym_merge.gym_observations``).
    Off by default.

    ``supplemental_paths`` overrides the shipped older-ICPC + Petroz + WF + UCup
    inputs; pass an empty sequence for a tagged-only diagnostic fit. ``None``
    keeps the shipped default. ``identity_paths`` can separately override which
    supplements participate in union-find construction, allowing diagnostics to
    distinguish identity-link changes from added likelihood evidence; by default
    it follows ``supplemental_paths``. ``ARCHB_EXTRA_CONTESTS`` is an
    ``os.pathsep``-separated list of standings JSON files used only by data-side
    experiments; it does not change the shipped default inputs.
    """
    if gym_merge is None and os.environ.get("ARCHB_GYM_MERGE"):
        gym_merge = float(os.environ["ARCHB_GYM_MERGE"])
    extra = [
        path for path in os.environ.get("ARCHB_EXTRA_CONTESTS", "").split(os.pathsep)
        if path
    ]
    supplemental = ([OLDER_ICPC, PETROZ, WF] + UCUP if supplemental_paths is None
                    else list(supplemental_paths))
    identity_supplemental = (supplemental if identity_paths is None
                             else list(identity_paths))
    paths = [TAGGED] + supplemental + extra

    raw_all = []
    for p in [TAGGED] + identity_supplemental + extra:
        with open(p) as f:
            raw_all.extend(json.load(f))
    raw_all = dedupe_contests(raw_all)
    if min_solve_hours is not None:
        raw_all = [c for c in raw_all if _max_solve_seconds(c) >= min_solve_hours * 3600]
    season_by_cid = {c["contest_id"]: season_of(c) for c in raw_all} if season_key else None
    uf = member_identity(raw_all, season_by_cid)

    ds = load(paths, uf=uf, season_key=season_key, min_solve_hours=min_solve_hours)

    if prior is None:
        mu, sd = np.full(len(ds.teams), float(MU0)), sigma_theta
    else:
        mu, sd = prior(ds, uf, sigma_theta, season_by_cid)

    gym_obs = None
    if gym_merge:
        from .gym_merge import gym_observations
        gym_obs = gym_observations(ds, weight=gym_merge, verbose=verbose)

    if verbose:
        print(f"=== joint fit ({len(ds.contests)} contests, {len(ds.teams)} teams, "
              f"{len(ds.problems)} problems) ===")
    theta, b, history = fit_fn(ds, prior_mu=mu, sigma_theta=sd,
                               sigma_b=sigma_b, verbose=verbose, gym_obs=gym_obs)
    return ds, theta, b, history, uf


if __name__ == "__main__":
    ds, theta, b, hist, _ = estimate_joint()
    print(f"converged in {len(hist)} iters, final max delta = {hist[-1]:.4f}")
    print(f"theta range: [{theta.min():.0f}, {theta.max():.0f}], mean {theta.mean():.0f}")
    print(f"b range:     [{b.min():.0f}, {b.max():.0f}], mean {b.mean():.0f}")
