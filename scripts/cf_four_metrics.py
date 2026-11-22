"""Use solve speed from completed earlier rounds to predict a held-out player."""
from collections import defaultdict
from heapq import heappop, heappush

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata

from cf_metric_search import Search, loss
from cf_solve_history import run


class TimingSearch(Search):
    def __init__(self, first_feature_year=2024):
        super().__init__()
        self.first_feature_year = first_feature_year
        self.past = {}
        self.pending = []
        self.features = defaultdict(list)
        self.train = defaultdict(list)

    def timing(self, contest, year, handles, train, times, p):
        start = contest['startTimeSeconds']
        while self.pending and self.pending[0][0] < start:
            end, _, previous, stats = heappop(self.pending)
            for h, row in zip(previous, stats):
                old = self.past.get(h)
                self.past[h] = (row if old is None else .90*old[0]+row, end)
        if year >= self.first_feature_year:
            keep = train if year <= 2024 else np.ones_like(train)
            predictors = []
            for h in np.asarray(handles)[keep]:
                entry = self.past.get(h)
                if entry is None:
                    predictors.append(np.zeros(4))
                else:
                    s, end = entry
                    predictors.append([s[0]/(2+s[1]), s[2]/(2+s[3]), s[4]/(2+s[5]),
                                       np.log1p((start-end)/86400/14)])
            self.features[year].append(np.asarray(predictors))
        solved = times >= 0
        speed = np.zeros_like(p)
        for j in range(p.shape[1]):
            sample = times[train & solved[:, j], j]
            if len(sample):
                speed[:, j] = np.where(solved[:, j], np.log((60+np.median(sample)) /
                                                             (60+np.maximum(times[:, j], 0))), 0)
        easy = p >= .5
        # Missed the whole set relative to the probability under independence.
        zero_residual = (~solved.any(axis=1)).astype(float) - (1-p).prod(axis=1)
        row = np.column_stack([(speed*easy).sum(axis=1), (solved*easy).sum(axis=1),
                               (speed*~easy).sum(axis=1), (solved*~easy).sum(axis=1),
                               zero_residual, np.ones(len(handles))])
        heappush(self.pending, (start+contest['durationSeconds'], contest['id'], handles, row))

    def score(self, year, handles, train, logits, solved):
        if year == 2024:
            return super().score(year, handles, train, logits, solved)
        empty = np.zeros((2, 4))
        hist = np.array([self.history.get(h, empty) for h in handles])
        self.cells[year].append((logits, solved, hist, expit(logits[train]).mean(axis=0)))
        self.train[year].append(train)

    def report(self, reference):
        coef, weights = self.fit()
        gradient = np.zeros(12)
        information = 100*np.eye(12)
        blocks = defaultdict(list)
        for year in (2024, 2025, 2026):
            for (base, y, x), features in zip(self.design(year, coef), self.features[year], strict=True):
                z = base + (x[0] @ weights[0] + .5*(x[3] @ weights[3])).reshape(base.shape)
                p = expit(z)
                design = np.stack([v[:, None]*g for v in features.T
                                   for g in (np.ones_like(p), 2*p-1, (2*p-1)**2)], axis=-1)
                f = design.reshape(-1, 12)
                if year == 2024:
                    gradient += f.T @ (y-p).ravel()
                    information += f.T @ ((p*(1-p)).ravel()[:, None]*f)
                else:
                    blocks[year].append((z, y, design @ beta))
            if year == 2024:
                beta = np.linalg.solve(information, gradient)
        self.select(blocks)

    def select(self, blocks):
        def predictions(year, strength, calibration, gate="all"):
            out = []
            pooled = np.zeros((2, 49))
            for (base, y, shift), train in zip(blocks[year], self.train[year], strict=True):
                p0 = expit(base)
                gates = {"all": 1, "unlikely": 1-p0, "likely": p0,
                         "uncertain": 4*p0*(1-p0),
                         "hard task": 1-p0[train].mean(axis=0),
                         "easy task": p0[train].mean(axis=0)}
                z = base + strength*shift*gates[gate]
                if calibration in ("pooled", "pooled soft", "pooled tails"):
                    local_grad, local_info, grid = calibration_stats(z, y, train)
                    pooled += np.stack([local_grad, local_info])
                    offsets = pooled[0] / (20 + pooled[1])
                    correction = np.interp(z, grid, offsets)
                    if calibration == "pooled soft":
                        correction *= .5
                    if calibration == "pooled tails":
                        correction -= .015*np.tanh(z/2)
                    z = z + correction
                    pooled *= .9
                elif calibration in ("rank transfer", "rank blend", "task", "task and field"):
                    if calibration.startswith("rank"):
                        aligned = np.empty_like(z)
                        for j in range(z.shape[1]):
                            aligned[:, j] = np.interp(z[:, j], np.sort(z[train, j]),
                                                     np.sort(base[train, j]))
                        z = aligned if calibration == "rank transfer" else (aligned + z)/2
                    else:
                        p = expit(z[train])
                        offset = (y[train]-p).sum(axis=0)/(5+(p*(1-p)).sum(axis=0))
                        z = z + offset
                        if calibration == "task and field":
                            z = z + field_correction(z, y, train)
                elif calibration:
                    z = z + calibration*field_correction(z, y, train)
                out.append((z[~train], y[~train]))
            return out

        reference25 = evaluate(predictions(2025, 0, 0))
        best = None
        for gate in ("all", "unlikely", "likely", "uncertain", "hard task", "easy task"):
            calibrators = (0, .5, 1., "pooled", "pooled soft", "pooled tails", "rank transfer",
                           "rank blend", "task", "task and field") if gate == "all" else (0, "rank transfer")
            for calibration in calibrators:
                for strength in (.25, .5, .75, 1., 1.25, 1.5):
                    score = evaluate(predictions(2025, strength, calibration, gate))
                    print('2025 trial', strength, calibration, gate, score, flush=True)
                    if all(score[:3]<reference25[:3]) and score[3]>reference25[3]:
                        if best is None or score[0] < best[0]:
                            best = score[0], strength, calibration, gate
        if best is None:
            print('No four-metric selection winner.')
            return
        for year in (2025, 2026):
            ref_rows = round_scores(predictions(year, 0, 0))
            selected_rows = round_scores(predictions(year, *best[1:]))
            indices = np.random.default_rng(42).integers(len(ref_rows), size=(10000, len(ref_rows)))
            delta = aggregate(selected_rows[indices].sum(axis=1)) - aggregate(ref_rows[indices].sum(axis=1))
            print('paired round-bootstrap intervals', year, np.quantile(delta, [.025, .975], axis=0))
            print('year, strengths, reference, selected:', year, best[1:],
                  aggregate(ref_rows.sum(axis=0)), aggregate(selected_rows.sum(axis=0)), flush=True)


def calibration_stats(z, y, train):
    # Smooth a residual log-odds correction on the training field only.
    grid = np.arange(-12, 12.01, .5)
    bins = np.clip(np.rint((z-grid[0])/.5).astype(int), 0, len(grid)-1)
    b = bins[train].ravel()
    p = expit(z[train])
    grad = np.bincount(b, (y[train]-p).ravel(), minlength=len(grid))
    info = np.bincount(b, (p*(1-p)).ravel(), minlength=len(grid))
    kernel = np.exp(-.5*((grid[:, None]-grid)/.65)**2)
    return kernel @ grad, kernel @ info, grid


def field_correction(z, y, train):
    grid = np.arange(-12, 12.01, .25)
    bins = np.clip(np.rint((z[train]-grid[0])/.25).astype(int), 0, len(grid)-1)
    p = expit(z[train])
    grad = np.bincount(bins.ravel(), (y[train]-p).ravel(), minlength=len(grid))
    info = np.bincount(bins.ravel(), (p*(1-p)).ravel(), minlength=len(grid))
    kernel = np.exp(-.5*((grid[:, None]-grid)/.65)**2)
    return np.interp(z, grid, (kernel @ grad)/(10 + kernel @ info))


def evaluate(blocks):
    return aggregate(round_scores(blocks).sum(axis=0))


def round_scores(blocks):
    rows = []
    for z, y in blocks:
        p = expit(z)
        auc = []
        residual = np.bincount(np.minimum((20*p).astype(int),19).ravel(),
                                (p-y).ravel(), minlength=20)
        for col, truth in zip(z.T, y.T):
            n = truth.sum()
            if 0 < n < len(col):
                auc.append((rankdata(col)[truth].sum()-n*(n+1)/2)/(n*(len(col)-n)))
        rows.append([y.size, loss(z,y).sum(), np.square(p-y).sum(), sum(auc), len(auc), *residual])
    return np.asarray(rows)


def aggregate(rows):
    counts, losses, brier, auc, problems = np.moveaxis(rows[..., :5], -1, 0)
    return np.stack([losses/counts, brier/counts, abs(rows[..., 5:]).sum(axis=-1)/counts,
                     auc/problems], axis=-1)


if __name__ == '__main__':
    search = TimingSearch()
    run(search, timing=search.timing)
