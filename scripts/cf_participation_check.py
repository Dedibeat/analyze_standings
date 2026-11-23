"""Season-matched participation checks using the cf_ai_deflation cache."""
import gzip
import json
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cf_ai_deflation import RC, ST, VET, contests


def collect():
    prior = Counter()
    windows = {}
    for c in sorted(contests(), key=lambda c: (c["startTimeSeconds"], c["id"])):
        date = datetime.fromtimestamp(c["startTimeSeconds"], timezone.utc)
        year = date.year + (date.month >= 8)
        after = 2 <= date.month <= 7
        if year > 2025:
            break
        filename = f"{c['id']}.json.gz"
        if not (RC / filename).exists():
            continue
        rows = json.loads(gzip.decompress((RC / filename).read_bytes()))["rows"]
        name = c["name"]
        if (year >= 2022 and "Div. 2" in name and "Div. 1" not in name
                and (ST / filename).exists()):
            standing = json.loads(gzip.decompress((ST / filename).read_bytes()))
            ratings = np.array([r for _, r in standing["problems"]], dtype=float)
            eligible = {h: r for h, _, r, _ in rows if 1000 <= r < 1600 and prior[h] >= VET}
            players = [(h, eligible[h], times) for h, _, times in standing["rows"] if h in eligible]
            if players and len(ratings):
                handles, old, times = zip(*players)
                gap = ratings - np.array(old)[:, None]
                prob = 1 / (1 + 10 ** (gap / 400))
                solved = np.array(times) >= 0
                frame = pd.DataFrame(dict(handle=handles, after=after, band=np.array(old)//200,
                                          veteran=[prior[h] >= 30 for h in handles],
                                          edu="Educational" in name))
                for label, mask in [('hard', gap >= 600), ('easy', gap <= 0)]:
                    frame[label+'o'] = (solved & mask).sum(axis=1)
                    frame[label+'e'] = np.where(mask, prob, 0).sum(axis=1)
                windows.setdefault(year, []).append(frame)
        prior.update(h for h, *_ in rows)
    return windows


def summarize(frame, label):
    sums = frame.groupby(['band', 'veteran', 'edu', 'after'])[[label+'o', label+'e']].sum()
    obs, exp = (sums[k].unstack() for k in sums)
    keep = exp.gt(0).all(axis=1)
    weights = exp.loc[keep, False]
    adjusted = (obs[keep] / exp[keep]).mul(weights, axis=0).sum() / weights.sum()
    raw = obs.sum() / exp.sum()
    return ' / '.join(f'{x:.3f}' for x in [*raw, *adjusted])


if __name__ == '__main__':
    for year, frames in collect().items():
        full = pd.concat(frames, ignore_index=True)
        both = full.groupby('handle').after.transform('nunique') == 2
        for cohort, frame in [('all', full), ('returning', full[both])]:
            print(year, cohort, frame.handle.nunique(), summarize(frame, 'hard'), summarize(frame, 'easy'))
