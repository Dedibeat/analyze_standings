"""25 predeclared CF player-history experiments. Run with one BLAS thread."""
from collections import defaultdict

import numpy as np
from scipy.special import expit

from cf_solve_history import run

DECAYS = np.array([.65, .80, .90, .95, .98])
BINS = (1, 2, 4, 8, 16)
# Frozen from the original 2024-only fit, as printed by cf_solve_history.
WEIGHTS = np.array([[1.04585638, -1.03545599], [-.63692926, .89328377]])


class HistorySweep:
    def __init__(self):
        self.history = {}
        self.gradient = np.zeros((len(DECAYS), max(BINS), 2))
        self.info = np.zeros((len(DECAYS), max(BINS), 2, 2))
        self.coefficients = {}
        self.losses = defaultdict(list)
        self.winner = None

    def update(self, handles, stats):
        for handle, row in zip(handles, stats):
            self.history[handle] = DECAYS[:, None] * self.history.get(handle, 0) + row

    def freeze(self):
        for bins in BINS:
            grad = self.gradient.reshape(len(DECAYS), bins, -1, 2).sum(axis=2)
            info = self.info.reshape(len(DECAYS), bins, -1, 2, 2).sum(axis=2)
            self.coefficients[bins] = np.linalg.solve(info + 100*np.eye(2), grad[..., None])[..., 0]

    def score(self, year, handles, train, logits, solved):
        mask = train if year == 2024 else ~train
        empty = np.zeros((len(DECAYS), 4))
        history = np.array([self.history.get(h, empty)
                            for h in np.asarray(handles)[mask]])
        history = history[:, :, ::2] / (2 + history[:, :, 1::2])
        z, y = logits[mask], solved[mask]
        p = expit(z)
        bucket = np.minimum((16*p).astype(int), 15)
        if year > 2024 and not self.coefficients:
            self.freeze()
        if year > 2025 and self.winner is None:
            selection_loss = np.sum(self.losses[2025], axis=0)
            self.winner = np.unravel_index(np.argmin(selection_loss), selection_loss.shape)
        losses = np.zeros((len(DECAYS), len(BINS)))
        for i in range(len(DECAYS)):
            if self.winner is not None and i != self.winner[0]:
                continue
            features = history[:, i, :]
            easy, hard = (features @ WEIGHTS).T
            base = z + easy[:, None] * p + hard[:, None] * (1-p)
            if year == 2024:
                q = expit(base)
                for a in range(2):
                    f = features[:, a, None]
                    self.gradient[i, :, a] += np.bincount(bucket.ravel(), ((y-q)*f).ravel(), minlength=16)
                    for b in range(2):
                        v = q*(1-q)*f*features[:, b, None]
                        self.info[i, :, a, b] += np.bincount(bucket.ravel(), v.ravel(), minlength=16)
                continue
            for j, bins in enumerate(BINS):
                if self.winner is not None and j != self.winner[1]:
                    continue
                coef = self.coefficients[bins][i][bucket // (16//bins)]
                pred = base + (features[:, None, :]*coef).sum(axis=2)
                losses[i,j] = (np.logaddexp(0, pred) - y*pred).sum()
        if year > 2024:
            self.losses[year].append(losses)

    def report(self, reference):
        for year, losses in self.losses.items():
            n, _, _, incumbent = np.array(reference[year]).T
            values = np.array(losses)
            if year == 2025:
                print('2025 loss matrix', values.sum(axis=0)/n.sum())
            i, j = self.winner
            candidate = values[:, i, j]
            delta = candidate - incumbent
            idx = np.random.default_rng(42).integers(len(n), size=(10000,len(n)))
            print(year, DECAYS[i], BINS[j], 'loss', candidate.sum()/n.sum(), 'rounds improved',
                  (delta<0).sum(), 'delta CI', np.quantile(delta[idx].sum(axis=1)/n[idx].sum(axis=1), [.025,.975]))


if __name__ == '__main__':
    run(HistorySweep())
