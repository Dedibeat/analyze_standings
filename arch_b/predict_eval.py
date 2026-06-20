"""Held-out solve-prediction check: does the model predict who solves what?

The external checks (LLM, Codeforces) validate the *difficulty ranking*. This is
the complementary *internal* test of the fit itself: hold out a random slice of the
observed (team, problem) cells, fit on the rest, and score the predicted solve
probability on the held-out cells with proper scoring rules (log-loss, Brier, AUC).

It directly answers whether the survival model's use of solve *times* in training
yields latent abilities/difficulties that generalize better than the binary model:
both predict the same quantity on a held-out cell -- P(team solves problem within
the contest) = pi(theta,b) (binary) or 1 - exp(-ln2 e^{(theta-b)/s}) (survival) --
so a fair head-to-head on identical held-out cells isolates the value of the time
signal. (Architecture A has no per-cell likelihood -- its abilities come from ranks
-- so per-cell hold-out does not apply to it; this compares the two arch B fits.)

Fit on the full tagged.json (neutral MU0 prior, no UCup anchor: the anchor sets the
absolute scale, irrelevant to a within-contest predictive comparison).

    python -m arch_b.predict_eval
"""

import os

import numpy as np

from arch_a import elo
from arch_a.load import load
from . import model, survival

TAGGED = os.path.join(os.path.dirname(__file__), os.pardir, "data", "tagged.json")
TEST_FRAC = 0.2
SEED = 0


def _metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    logloss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    brier = np.mean((p - y) ** 2)
    # AUC via the rank-sum (Mann-Whitney) identity, no sklearn
    order = np.argsort(p)
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    n1 = y.sum()
    n0 = len(y) - n1
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
    ds = load(TAGGED)
    obs_team, obs_prob, obs_y, rho = survival._survival_observations(ds)

    rng = np.random.default_rng(SEED)
    test = rng.random(len(obs_y)) < TEST_FRAC
    train = ~test
    print(f"{len(obs_y)} cells: {train.sum()} train / {test.sum()} held out "
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
