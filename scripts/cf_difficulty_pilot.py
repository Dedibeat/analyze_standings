"""Fit standings difficulties and check predictions on held-out handles."""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import brentq
from scipy.special import expit

from cf_ai_deflation import RC, ST, VET, contests


def pilot():
    history = Counter()
    totals = np.zeros(4)
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
        history.update(h for h, *_ in rows)
    print('rounds, problem entries, test opportunities, solves:', rounds, problems, *totals[2:].astype(int))
    print('mean log loss (fitted, official):', *(totals[:2] / totals[2]))


if __name__ == '__main__':
    pilot()
