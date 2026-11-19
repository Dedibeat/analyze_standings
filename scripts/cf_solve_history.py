"""Compare calibrated rating curves and lagged solve history on matched fields."""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from heapq import heappop, heappush

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from cf_ai_deflation import RC, ST, VET, contests
from cf_difficulty_pilot import slope_predictions

SCALE = np.log(10) / 400


def local_curve(x, y, train, z):
    """Smooth solve rates in overlapping rating neighborhoods toward the 2PL."""
    grid = np.arange(-2000, 6001, 50)
    bins = np.clip(np.rint((x / SCALE + 1500 - grid[0]) / 50).astype(int), 0, len(grid)-1)
    kernel = np.exp(-0.5 * ((grid[:, None] - grid) / 85)**2)
    residual = y[train] - expit(z[train])
    sums = np.zeros((len(grid), y.shape[1]))
    np.add.at(sums, bins[train], residual)
    # One Newton update for a locally constant log-odds correction.
    info = np.zeros_like(sums)
    p = expit(z[train])
    np.add.at(info, bins[train], p * (1-p))
    correction = (kernel @ sums) / (5 + kernel @ info)
    return z + np.clip(correction[bins], -1.5, 1.5)


def predictors(history, p):
    # Easier and harder items need not carry the same player signal.
    return np.stack([np.broadcast_to(h[:, None], p.shape) * gate
                     for h in history.T for gate in (p, 1-p)], axis=-1)


def learn(samples):
    def objective(w):
        loss = 0.
        grad = np.zeros(len(w))
        for z, f, y in samples:
            pred = z + f @ w
            loss += (np.logaddexp(0, pred) - y * pred).sum()
            grad += f.T @ (expit(pred) - y)
        return loss, grad
    result = minimize(objective, np.zeros(4), jac=True, method='BFGS', options={'gtol': .001})
    if not result.success:
        raise RuntimeError(result.message)
    return result.x


def run(sweep=None, timing=None):
    prior, trend, records = Counter(), {}, {}
    pending, samples = [], []
    results = defaultdict(list)
    w = None
    for c in sorted(contests(), key=lambda c: (c['startTimeSeconds'], c['id'])):
        start = c['startTimeSeconds']
        year = datetime.fromtimestamp(start, timezone.utc).year
        while pending and pending[0][0] < start:
            _, _, rows, updates = heappop(pending)
            for h, _, a, b in rows:
                if prior[h] >= 6:
                    trend[h] = .8 * trend.get(h, 0) + .2 * (b-a)
                prior[h] += 1
            if updates:
                handles, stats = updates
                if sweep is not None:
                    sweep.update(handles, stats)
                for h, row in zip(handles, stats):
                    records[h] = .85 * records.get(h, 0) + row
        filename = f"{c['id']}.json.gz"
        if not (RC / filename).exists():
            continue
        rows = json.loads(gzip.decompress((RC / filename).read_bytes()))['rows']
        updates = None
        if 'Div. 2' in c['name'] and 'Div. 1' not in c['name'] and (ST / filename).exists():
            d = json.loads(gzip.decompress((ST / filename).read_bytes()))
            old = {h: r for h, _, r, _ in rows if prior[h] >= VET}
            players = [(h, old[h], t) for h, _, t in d['rows'] if h in old]
            rated = [r is not None for _, r in d['problems']]
            if players and any(rated):
                handles, ratings, times = zip(*players)
                y = (np.array(times) >= 0)[:, rated]
                train = np.array([hashlib.sha256(h.encode()).digest()[0] >= 51 for h in handles])
                x = SCALE * (np.array(ratings)-1500)
                x -= np.array([1.20679056*SCALE*trend.get(h, 0) +
                               .06933997*np.log(prior[h]/30) for h in handles])
                z = slope_predictions(x[train], y[train], x, False)
                smooth = local_curve(x, y, train, z)
                p = expit(smooth)
                if timing is not None:
                    timing(c, year, handles, train, np.asarray(times)[:, rated], p)
                stats = []
                for group in (p >= .5, p < .5):
                    stats.extend([((y-p)*group).sum(axis=1), (p*(1-p)*group).sum(axis=1)])
                updates = handles, np.column_stack(stats)
                if year >= 2024:
                    hist = np.array([records.get(h, (0, 0, 0, 0)) for h in handles])
                    f = predictors(hist[:, ::2] / (2 + hist[:, 1::2]), p)
                    if sweep is not None:
                        sweep.score(year, handles, train, smooth, y)
                    if year == 2024:
                        samples.append((smooth[train].ravel(), f[train].reshape(-1, 4), y[train].ravel()))
                    else:
                        if w is None:
                            w = learn(samples)
                            samples.clear()
                            print('history weights', w, flush=True)
                        loss = []
                        for pred in (z, smooth, smooth + f @ w):
                            v = pred[~train]
                            loss.append((np.logaddexp(0, v) - y[~train]*v).sum())
                        results[year].append([y[~train].size, *loss])
        heappush(pending, (start+c['durationSeconds'], c['id'], rows, updates))
    if sweep is not None:
        sweep.report(results)
    for year, scores in results.items():
        n, base, smooth, full = np.array(scores).T
        diff = full-base
        idx = np.random.default_rng(42).integers(len(n), size=(10000, len(n)))
        print(year, len(n), int(n.sum()), np.array([base,smooth,full]).sum(axis=1)/n.sum(),
              (diff<0).sum(), np.quantile(diff[idx].sum(axis=1)/n[idx].sum(axis=1), [.025,.975]))


if __name__ == '__main__':
    run()
