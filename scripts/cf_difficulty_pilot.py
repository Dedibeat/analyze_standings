"""Fit standings difficulties and check predictions on held-out handles."""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.special import expit

from cf_ai_deflation import RC, ST, VET, contests


def slope_predictions(x, y, test_x, shared):
    """Fit intercepts and positive slopes, shrinking log slopes toward zero."""
    n = y.shape[1]

    def objective(params):
        intercept = params[:n]
        g = params[n:]
        bx = x[:, None] * np.exp(g)
        z = intercept + bx
        err = expit(z) - y
        # Same half-solve pseudo-observation at 1500 as the pilot.
        loss = (np.logaddexp(0, z) - y * z).sum()
        loss += (np.logaddexp(0, intercept) - 0.5 * intercept).sum()
        loss += 0.5 * np.square(g / 0.5).sum()
        da = err.sum(axis=0) + expit(intercept) - 0.5
        dg = (err * bx).sum(axis=0)
        if shared:
            dg = np.array([dg.sum()])
        return loss, np.r_[da, dg + g / 0.25]

    k = 1 if shared else n
    fit = minimize(objective, np.zeros(n + k), jac=True, method='L-BFGS-B',
                   bounds=[(None, None)] * n + [(-2, 2)] * k,
                   options={'ftol': 1e-12, 'maxiter': 1000})
    if not fit.success:
        raise RuntimeError(fit.message)
    return fit.x[:n] + test_x[:, None] * np.exp(fit.x[n:])


def pilot():
    history = Counter()
    totals = np.zeros(4)
    round_losses = []
    problems = rounds = 0
    slope = np.log(10) / 400
    for c in sorted(contests(), key=lambda c: (c['startTimeSeconds'], c['id'])):
        date = datetime.fromtimestamp(c['startTimeSeconds'], timezone.utc)
        if date.year > 2025:
            break
        file = f"{c['id']}.json.gz"
        if not (RC / file).exists():
            continue
        rows = json.loads(gzip.decompress((RC / file).read_bytes()))['rows']
        if date.year == 2025 and 'Div. 2' in c['name'] and 'Div. 1' not in c['name'] and (ST / file).exists():
            standing = json.loads(gzip.decompress((ST / file).read_bytes()))
            old = {h: r for h, _, r, _ in rows if history[h] >= VET}
            players = [(h, old[h], t) for h, _, t in standing['rows'] if h in old]
            if players and any(r is not None for _, r in standing['problems']):
                rounds += 1
                handles, ratings, times = zip(*players)
                ratings = np.array(ratings)
                solved = np.array(times) >= 0
                test = np.array([hashlib.sha256(h.encode()).digest()[0] < 51 for h in handles])
                rated = [r is not None for _, r in standing['problems']]
                x = slope * (ratings - 1500)
                target = solved[test][:, rated]
                losses = []
                for shared in (True, False):
                    z = slope_predictions(x[~test], solved[~test][:, rated], x[test], shared)
                    losses.append((np.logaddexp(0, z) - target * z).sum())
                before = totals[0]
                for j, (_, cf) in enumerate(standing['problems']):
                    if cf is None:
                        continue
                    train = ratings[~test]
                    count = solved[~test, j].sum()
                    # One pseudo-player at 1500 with half a solve.
                    def residual(d):
                        return expit(slope * (train - d)).sum() - count + expit(slope * (1500 - d)) - 0.5

                    difficulty = brentq(residual, -10000, 12000)
                    y = solved[test, j]
                    for i, d in enumerate((difficulty, cf)):
                        z = slope * (ratings[test] - d)
                        totals[i] += (np.logaddexp(0, z) - y * z).sum()
                    totals[2] += len(y)
                    totals[3] += y.sum()
                    problems += 1
                round_losses.append([target.size, totals[0] - before, *losses])
        history.update(h for h, *_ in rows)
    per_round = np.array(round_losses)
    assert per_round[:, 0].sum() == totals[2]
    rng = np.random.default_rng(42)
    sample = rng.integers(rounds, size=(10000, rounds))
    for col, name in ((2, 'round slope'), (3, 'problem slopes')):
        diff = per_round[:, col] - per_round[:, 1]
        delta = diff[sample].sum(axis=1) / per_round[sample, 0].sum(axis=1)
        print(name, 'loss, delta CI, rounds improved:', per_round[:, col].sum() / totals[2],
              np.quantile(delta, [0.025, 0.975]), (diff < 0).sum())
    print('rounds, problem entries, test opportunities, solves:', rounds, problems, *totals[2:].astype(int))
    print('mean log loss (fitted, official):', *(totals[:2] / totals[2]))


if __name__ == '__main__':
    pilot()
