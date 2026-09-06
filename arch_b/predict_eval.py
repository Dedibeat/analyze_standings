"""Held-out response-imputation check: does the model predict missing cells?

The external checks (LLM, Codeforces) validate the *difficulty ranking*. This is
the complementary *internal* test of the fit itself: hold out a random slice of
resolved (team, problem) response groups, fit on the rest, and score the predicted
solve probability on the held-out cells with proper scoring rules (log-loss,
Brier, AUC). Grouping keeps repeated responses for the same resolved team/problem
out of the opposite split, and survival durations use training solves only.

It directly answers whether the survival model's use of solve *times* in training
yields latent abilities/difficulties that generalize better than the binary model:
both predict the same quantity on a held-out cell -- P(team solves problem within
the contest) = pi(theta,b) (binary) or 1 - exp(-ln2 e^{(theta-b)/s}) (survival) --
so a fair head-to-head on identical held-out cells isolates the value of the time
signal. (Architecture A has no per-cell likelihood -- its abilities come from ranks
-- so per-cell hold-out does not apply to it; this compares the two arch B fits.)

This evaluates imputation for already-retained appearances, not future contests:
the loader's zero-solve-row filter was applied before the split. The fit uses the
same joint standings sources and duration filter as the shipped model.

    python -m arch_b.predict_eval
"""

import numpy as np

from arch_a import elo
from .aoj import _rank
from . import model, survival
from .joint import load_joint_dataset
from .run import MIN_SOLVE_HOURS

TEST_FRAC = 0.2
SEED = 0


def _grouped_test_mask(obs_team, obs_prob, candidates=None, seed=SEED,
                       test_frac=TEST_FRAC):
    """Select response groups without splitting duplicate team/problem keys."""
    obs_team, obs_prob = np.asarray(obs_team), np.asarray(obs_prob)
    if candidates is None:
        candidates = np.ones(len(obs_team), dtype=bool)
    else:
        candidates = np.asarray(candidates, bool)
    keys = np.column_stack((obs_team[candidates], obs_prob[candidates]))
    unique_keys, inverse = np.unique(keys, axis=0, return_inverse=True)
    selected = (np.random.default_rng(seed).random(len(unique_keys)) < test_frac)[inverse]
    test = np.zeros(len(obs_team), dtype=bool)
    test[np.flatnonzero(candidates)] = selected
    return test


def _metrics(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if y.shape != p.shape or y.ndim != 1:
        raise ValueError("y and p must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(p)):
        raise ValueError("predictions must be finite")
    if not np.all((y == 0) | (y == 1)):
        raise ValueError("labels must be binary")
    p = np.clip(p, 1e-6, 1 - 1e-6)
    logloss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    brier = np.mean((p - y) ** 2)
    # AUC via the rank-sum (Mann-Whitney) identity, no sklearn
    ranks = _rank(p) + 1.0
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        raise ValueError("AUC requires both label classes")
    auc = (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return logloss, brier, auc


def _calibration(y, p, edges=(0, .1, .3, .5, .7, .9, 1.0001)):
    print(f"    {'pred bin':12} {'n':>7} {'pred mean':>9} {'emp rate':>9}")
    edges = np.asarray(edges)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            print(f"    [{lo:.1f},{hi:.1f})      {m.sum():7d} {p[m].mean():9.3f} {y[m].mean():9.3f}")


def main():
    ds, _uf, _season = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    obs_team, obs_prob, obs_y, _rho = survival._survival_observations(ds)

    test = _grouped_test_mask(obs_team, obs_prob)
    train = ~test
    _t, _p, _y, rho = survival._survival_observations(ds, duration_mask=train)
    n_groups = len(np.unique(np.column_stack((obs_team, obs_prob)), axis=0))
    print(f"{len(obs_y)} cells / {n_groups} resolved team-problem groups: "
          f"{train.sum()} train / {test.sum()} held out "
          f"(solve rate {obs_y.mean():.3f})")

    tr_bin = (obs_team[train], obs_prob[train], obs_y[train])
    tr_sur = (obs_team[train], obs_prob[train], obs_y[train], rho[train])
    yte = obs_y[test]
    tte, pte = obs_team[test], obs_prob[test]

    th_b, b_b, _ = model.fit(ds, obs=tr_bin, verbose=False)
    th_s, b_s, _ = survival.fit(ds, obs=tr_sur, verbose=False)

    p_bin = elo.pi(th_b[tte], b_b[pte])                       # P(solve) = pi(theta,b)
    g_s = (th_s[tte] - b_s[pte]) / elo.S
    p_sur = 1.0 - np.exp(-survival.LN2 * np.exp(g_s))         # P(solve within window)

    for name, p in [("binary  ", p_bin), ("survival", p_sur)]:
        ll, br, auc = _metrics(yte, p)
        print(f"\n{name}  log-loss {ll:.4f}   Brier {br:.4f}   AUC {auc:.4f}")
        _calibration(yte, p)


if __name__ == "__main__":
    main()
