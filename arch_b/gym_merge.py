"""Gym-mirror attempts merged into the main fit as fixed-theta observations.

The strat's original anchor (eq. cfprior) wants contestants with known
Codeforces ratings; our own rosters have none, but the gym-mirror population
(``data/cf_gym_mirrors.json``, parsed by ``gym_difficulty.load_gym``) does.
This module turns those attempts into extra *likelihood terms on b only*:
each gym team contributes trust-weighted Bernoulli observations with its
ability **fixed** at the CF-derived value (``team_theta``), joined to the main
fit's problem indices. theta stays fixed (gym solvers are not fit as teams):
the gym field is a measured yardstick population, not part of the rating pool.

Contrast with the reverted N(b_gym, sigma^2) *prior* (commit 80afc92): here the
information enters through per-solver likelihood terms, so a problem with many
gym attempts is pulled with the weight of its evidence, and a problem with two
attempts barely moves — the prior gave both the same pull.

``weight`` is a global multiplier on the per-team trust weights: gym fields are
large (hundreds of attempts vs a regional's ~100 teams), so ``weight=1`` lets
the gym population dominate covered problems; small values blend it in softly.
"""

import numpy as np

from .gym_difficulty import REDUCTION, load_gym, team_theta

# qoj contests that are also CF-rated metric anchor contests. Their gym rows
# would leak near-copies of the metric target into the fit (on qoj 2692 the
# gym difficulty correlates +0.976 with the official CF ratings), so they are
# always excluded. Verified 2026-07-04: 2692 is the only overlap between the
# 57 gym contests and the 15 mapped anchor contests.
EXCLUDE_QOJ = {2692}


def gym_observations(ds, weight=1.0, reduction=REDUCTION, exclude=EXCLUDE_QOJ,
                     verbose=False):
    """Build ``(g_theta, g_prob, g_y, g_w)`` arrays joined to ``ds`` problems.

    One entry per (gym team, covered problem): fixed ability ``g_theta`` on the
    CF scale, global problem index ``g_prob``, outcome ``g_y``, and weight
    ``g_w`` = team trust * ``weight``. Returns None if nothing joins.
    """
    pidx = {(cid, label): j for j, (cid, label, _, _) in enumerate(ds.problems)}
    g_theta, g_prob, g_y, g_w = [], [], [], []
    n_contests = 0
    for c in load_gym():
        if c["contest_id"] in exclude:
            continue
        cols = {gym_label: pidx[(c["contest_id"], our_label)]
                for gym_label, our_label, _ in c["problems"]
                if (c["contest_id"], our_label) in pidx}
        if not cols:
            continue
        n_contests += 1
        for members, solved in c["teams"]:
            red = team_theta(members, reduction)
            if red is None:
                continue
            theta, w = red
            for gym_label, j in cols.items():
                g_theta.append(theta)
                g_prob.append(j)
                g_y.append(1.0 if gym_label in solved else 0.0)
                g_w.append(w * weight)
    if not g_y:
        return None
    out = (np.array(g_theta), np.array(g_prob, dtype=int),
           np.array(g_y), np.array(g_w))
    if verbose:
        covered = len(np.unique(out[1]))
        print(f"gym merge: {len(g_y)} attempts on {covered} problems "
              f"({n_contests} contests, weight={weight})")
    return out
