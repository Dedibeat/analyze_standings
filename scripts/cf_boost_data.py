"""Build chronological features for the CF four-metric benchmark."""
import argparse
import gzip
import json
from collections import defaultdict
from heapq import heappop, heappush
from pathlib import Path

import numpy as np
from scipy.special import expit

from cf_ai_deflation import D, RC, ST
from cf_four_metrics import TimingSearch
from cf_solve_history import run

CACHE = D / 'boost_v1'
TOPICS = (
    {'dp', 'bitmasks'},
    {'math', 'number theory', 'combinatorics', 'probabilities'},
    {'graphs', 'trees', 'dfs and similar', 'shortest paths', 'dsu'},
    {'data structures', 'binary search', 'sortings', 'two pointers'},
    {'strings', 'hashing', 'string suffix structures'},
    {'greedy', 'constructive algorithms', 'implementation'},
)
NAMES = ('incumbent', 'problem_logit', 'field_solve_rate', 'position', 'duration_hours',
         'educational', 'pre_rating', 'easy_speed', 'hard_speed', 'zero_history', 'recency',
         'long_easy_residual', 'long_hard_residual', 'recent_easy_residual', 'recent_hard_residual',
         'easy_information', 'hard_information', 'topic_residual', 'topic_information',
         'slot_residual', 'slot_information', 'weighted_rank', 'rank_variability', 'rated_appearances',
         'rating_trend', 'speed_by_slot', 'matched_topics')


class Panel(TimingSearch):
    def __init__(self, cache=CACHE, first_feature_year=2024):
        super().__init__(first_feature_year)
        self.cache = cache
        problemset = json.loads((D.parent/'cf_problemset.json').read_text())
        self.tags = {(p['contestId'], p['index']): set(p.get('tags', [])) for p in problemset}
        self.profile = {}
        self.queue = []
        self.meta = defaultdict(list)

    def timing(self, c, year, handles, train, times, p):
        super().timing(c, year, handles, train, times, p)
        start, cid = c['startTimeSeconds'], c['id']
        while self.queue and self.queue[0][0] < start:
            _, _, past, sufficient = heappop(self.queue)
            for h, row in zip(past, sufficient):
                self.profile[h] = .94*self.profile.get(h, 0) + row
        rows = json.loads(gzip.decompress((RC/f'{cid}.json.gz').read_bytes()))['rows']
        ratings = {h: (rank, old, new) for h, rank, old, new in rows}
        problems = json.loads(gzip.decompress((ST/f'{cid}.json.gz').read_bytes()))['problems']
        labels = [label for label, r in problems if r is not None]
        topic = np.array([[bool(self.tags.get((cid, label), set()) & family) for family in TOPICS]
                          for label in labels], dtype=float)
        slots = np.minimum(np.arange(len(labels)), 6)
        slot = np.eye(7)[slots]
        ranks, old, new = np.array([ratings[h] for h in handles], dtype=float).T
        if year >= self.first_feature_year:
            keep = train if year <= 2024 else np.ones_like(train)
            default = np.zeros(3*7 + 2*len(TOPICS) + 4)
            history = np.array([self.profile.get(h, default) for h in np.asarray(handles)[keep]])
            residual, info, speed = np.split(history[:, :21], 3, axis=1)
            topic_res, topic_info = np.split(history[:, 21:-4], 2, axis=1)
            mean_rank, squared_rank, delta, n = history[:, -4:].T
            avg = mean_rank/(n+1e-10)
            extra = [topic_res @ topic.T/(2+topic_info @ topic.T), np.log1p(topic_info @ topic.T),
                     (residual/(2+info))[:, slots], np.log1p(info[:, slots]), avg[:, None],
                     np.sqrt(np.maximum(0, squared_rank/(n+1e-10)-avg**2))[:, None],
                     np.log1p(n)[:, None], (delta/(1+n))[:, None],
                     (speed/(2+info))[:, slots], topic.sum(axis=1)]
            self.meta[year].append((cid, c['durationSeconds']/3600, 'Educational' in c['name'],
                                    old[keep], [np.asarray(a, dtype=np.float32) for a in extra]))
        solved = times >= 0
        err, info = solved-p, p*(1-p)
        speed = solved*(1-np.maximum(times, 0)/c['durationSeconds'])
        rank = 1 - (ranks-.5)/len(rows)
        sufficient = np.column_stack([err @ slot, info @ slot, speed @ slot, err @ topic, info @ topic,
                                      rank, rank**2, new-old, np.ones(len(handles))])
        heappush(self.queue, (start+c['durationSeconds'], cid, handles, sufficient))

    def score(self, year, handles, train, logits, solved):
        if year >= 2024:
            return super().score(year, handles, train, logits, solved)
        empty = np.zeros((2, 4))
        hist = np.array([self.history.get(h, empty) for h in np.asarray(handles)[train]])
        self.cells[year].append((logits[train], solved[train], hist, expit(logits[train]).mean(axis=0)))

    def report(self, reference):
        coef, weights = self.fit()
        self.cache.mkdir(parents=True, exist_ok=True)
        for year in sorted(self.cells):
            if self.first_feature_year < 2024 and year >= 2024:
                continue
            round_ids = []
            for i, ((base, y, x), (z, _, hist, difficulty), timing, meta) in enumerate(zip(
                    self.design(year, coef), self.cells[year], self.features[year], self.meta[year], strict=True)):
                cid, duration, edu, old, extra = meta
                incumbent = base + (x[0] @ weights[0] + .5*(x[3] @ weights[3])).reshape(base.shape)
                residual = hist[:, :, ::2] / (2 + hist[:, :, 1::2])
                features = [incumbent, z, difficulty, np.linspace(0,1,z.shape[1]), duration, edu,
                            old[:, None], *[v[:, None] for v in timing.T],
                            *[v[:, None] for v in residual.reshape(len(old),4).T],
                            *[v[:, None] for v in np.log1p(hist[:, 0, 1::2]).T], *extra]
                assert len(features) == len(NAMES)
                values = np.stack([np.broadcast_to(f, z.shape) for f in features], axis=-1)
                train = np.ones(len(old), dtype=bool) if year <= 2024 else self.train[year][i]
                np.savez(self.cache/f'{cid}.npz', x=values.astype('f'), z=incumbent, y=y, train=train)
                round_ids.append(cid)
            (self.cache/f'{year}.json').write_text(json.dumps(round_ids))
            print('panel', year, len(round_ids), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fold', type=int, choices=range(5), default=0)
    parser.add_argument('--from-year', type=int, choices=(2022, 2024), default=2024)
    args = parser.parse_args()
    cache = CACHE if args.fold == 0 else CACHE.parent/f'{CACHE.name}_fold{args.fold}'
    if args.from_year < 2024:
        cache = cache.with_name(cache.name + "_long")
    panel = Panel(cache, args.from_year)
    run(panel, timing=panel.timing, fold=args.fold, first_feature_year=args.from_year,
        last_year=2024 if args.from_year<2024 else None)
