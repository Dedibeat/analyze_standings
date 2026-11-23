"""Learn a pre-round player rating adjustment in 2024 and evaluate it in 2025."""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from heapq import heappop, heappush

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from cf_ai_deflation import RC, ST, VET, contests
from cf_difficulty_pilot import slope_predictions


def run():
    experience = Counter()
    trend = {}
    pending = []
    development = []
    weights = None
    scores = []
    scale = np.log(10) / 400
    for c in sorted(contests(), key=lambda c: (c['startTimeSeconds'], c['id'])):
        start = c['startTimeSeconds']
        year = datetime.fromtimestamp(start, timezone.utc).year
        if year > 2025:
            break
        while pending and pending[0][0] < start:
            _, _, previous = heappop(pending)
            for handle, _, old, new in previous:
                if experience[handle] >= 6:
                    trend[handle] = 0.8 * trend.get(handle, 0) + 0.2 * (new - old)
                experience[handle] += 1
        filename = f"{c['id']}.json.gz"
        if not (RC / filename).exists():
            continue
        rows = json.loads(gzip.decompress((RC / filename).read_bytes()))['rows']
        heappush(pending, (start + c['durationSeconds'], c['id'], rows))
        if year < 2024 or 'Div. 2' not in c['name'] or 'Div. 1' in c['name'] or not (ST / filename).exists():
            continue
        standing = json.loads(gzip.decompress((ST / filename).read_bytes()))
        old = {h: r for h, _, r, _ in rows if experience[h] >= VET}
        players = [(h, old[h], t) for h, _, t in standing['rows'] if h in old]
        rated = [r is not None for _, r in standing['problems']]
        if not players or not any(rated):
            continue
        handles, ratings, times = zip(*players)
        x = (np.array(ratings) - 1500) * scale
        features = np.array([[trend.get(h, 0) * scale, np.log(experience[h] / 30)] for h in handles])
        y = (np.array(times) >= 0)[:, rated]
        test = np.array([hashlib.sha256(h.encode()).digest()[0] < 51 for h in handles])
        if year == 2024:
            # Calibrate only on training handles. Two logits recover each fitted line.
            intercept, at_one = slope_predictions(x[~test], y[~test], np.array([0., 1.]), False)
            development.append((x[~test], features[~test], y[~test], intercept, at_one - intercept))
            continue
        if weights is None:
            if not development:
                raise ValueError("2024 training standings are missing")
            weights = learn(development)
            print('weights:', weights, flush=True)
            development.clear()
        loss = []
        for ability in (x, x + features @ weights):
            z = slope_predictions(ability[~test], y[~test], ability[test], False)
            loss.append((np.logaddexp(0, z) - y[test] * z).sum())
        scores.append([y[test].size, *loss])
    n, base, adjusted = np.array(scores).T
    diff = adjusted - base
    idx = np.random.default_rng(42).integers(len(n), size=(10000, len(n)))
    print('rounds, opportunities, improved:', len(n), int(n.sum()), (diff < 0).sum())
    print('baseline, adjusted:', base.sum()/n.sum(), adjusted.sum()/n.sum())
    print('delta interval:', np.quantile(diff[idx].sum(axis=1)/n[idx].sum(axis=1), [.025, .975]))


def learn(rounds):
    def objective(w):
        loss = 0.
        grad = np.zeros(2)
        for x, features, y, intercept, slopes in rounds:
            z = intercept + (x + features @ w)[:, None] * slopes
            loss += (np.logaddexp(0, z) - y * z).sum()
            grad += features.T @ ((expit(z) - y) @ slopes)
        return loss, grad
    fit = minimize(objective, np.zeros(2), jac=True, method='BFGS', options={'gtol': 0.001})
    if not fit.success:
        raise RuntimeError(fit.message)
    return fit.x


if __name__ == '__main__':
    run()
