"""Finite coordinate search around the published 16-band incumbent."""
from collections import defaultdict
from itertools import product

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

from cf_history_sweep import WEIGHTS
from cf_solve_history import run

FAMILIES = ('recent history', 'history curvature', 'history depth', 'recalibration',
            'position', 'problem difficulty')
GRID = (0., .5, 1., 1.5, 2.)


def loss(z, y):
    return np.logaddexp(0, z) - y*z


class Search:
    def __init__(self):
        self.history = {}
        self.cells = defaultdict(list)

    def update(self, handles, stats):
        decay = np.array([[.95], [.65]])
        for h, row in zip(handles, stats):
            self.history[h] = decay*self.history.get(h, 0) + row

    def score(self, year, handles, train, logits, solved):
        keep = train if year == 2024 else ~train
        empty = np.zeros((2, 4))
        hist = np.array([self.history.get(h, empty) for h in np.asarray(handles)[keep]])
        self.cells[year].append((logits[keep], solved[keep], hist, expit(logits[train]).mean(axis=0)))

    def report(self, reference):
        # Recover the original 16 independent regularized Newton updates.
        info = np.tile(100*np.eye(2), (16, 1, 1))
        grad = np.zeros((16, 2))
        for z, y, hist, _ in self.cells[2024]:
            p, base, features, band = baseline(z, hist)
            q = expit(base)
            for a in range(2):
                f = features[:, a, None]
                grad[:, a] += np.bincount(band.ravel(), ((y-q)*f).ravel(), minlength=16)
                for b in range(2):
                    v = q*(1-q)*f*features[:, b, None]
                    info[:, a, b] += np.bincount(band.ravel(), v.ravel(), minlength=16)
        coef = np.linalg.solve(info, grad[..., None])[..., 0]
        year_data = {}
        for year in sorted(self.cells):
            blocks = []
            gradient = None
            for z, y, hist, difficulty in self.cells[year]:
                p, base, features, band = baseline(z, hist)
                incumbent = base + (features[:, None, :]*coef[band]).sum(axis=2)
                x = corrections(p, incumbent, features, hist, difficulty)
                if year == 2024:
                    if gradient is None:
                        hessian = [100*np.eye(f.shape[-1]) for f in x]
                        gradient = [np.zeros(f.shape[-1]) for f in x]
                    q = expit(incumbent.ravel())
                    for j, f in enumerate(x):
                        gradient[j] += f.T @ (y.ravel()-q)
                        hessian[j] += f.T @ ((q*(1-q))[:, None]*f)
                else:
                    shifts = np.column_stack([f @ w for f, w in zip(x, weights)])
                    blocks.append((incumbent, y, shifts))
            if year == 2024:
                weights = [np.linalg.solve(h, g) for h, g in zip(hessian, gradient)]
            else:
                year_data[year] = blocks
        selected = search(year_data[2025])
        for year, blocks in year_data.items():
            metrics(blocks, selected, year)


def baseline(z, hist):
    p = expit(z)
    f = hist[:, 0, ::2] / (2 + hist[:, 0, 1::2])
    easy, hard = (f @ WEIGHTS).T
    return p, z + easy[:, None]*p + hard[:, None]*(1-p), f, np.minimum((16*p).astype(int), 15)


def corrections(p, z, f, hist, difficulty):
    recent = hist[:, 1, ::2] / (2 + hist[:, 1, 1::2])
    depth = 1 / np.sqrt(1 + hist[:, 0, 1::2])
    gate = 2*p-1
    def gated(values):
        cols = [v[:, None]*g for v in values.T for g in (np.ones_like(p), gate)]
        return np.column_stack([c.ravel() for c in cols])
    def matrix(*cols):
        return np.column_stack([np.broadcast_to(c, p.shape).ravel() for c in cols])
    position = np.linspace(-1, 1, p.shape[1])
    difficulty = 2*difficulty-1
    return [gated(recent-f), gated(np.tanh(f)**2), gated(depth),
            matrix(1, np.tanh(z/3), np.tanh(z/3)**2, np.tanh(z/3)**3),
            matrix(position, position*gate, position**2),
            matrix(difficulty, difficulty*gate, difficulty**2)]


def search(blocks):
    z = np.concatenate([a.ravel() for a, _, _ in blocks])
    y = np.concatenate([b.ravel() for _, b, _ in blocks])
    shifts = np.concatenate([s for _, _, s in blocks])
    w = np.zeros(len(FAMILIES))
    trials = 0
    while True:
        pred = z + shifts @ w
        current = loss(pred, y).mean()
        brier = np.square(expit(pred)-y).mean()
        best = None
        for i, name in enumerate(FAMILIES):
            for v in GRID:
                if v == w[i]:
                    continue
                trials += 1
                candidate = pred + (v-w[i])*shifts[:, i]
                score = loss(candidate, y).mean()
                if score <= current-1e-5 and (best is None or score < best[0]):
                    if np.square(expit(candidate)-y).mean() <= brier:
                        best = score, i, v
        if best is None:
            print('coordinate stop', trials, 'neighbor evaluations; weights', w, flush=True)
            return verify_grid(z, y, shifts, w)
        score, i, weight = best
        w[i] = weight
        print('accept', FAMILIES[i], w[i], score, flush=True)


def verify_grid(z, y, shifts, w):
    """Certify the grid using a lower bound on logistic curvature for every row."""
    total = len(y)
    def objective(v):
        pred = z + shifts @ v
        return loss(pred, y).mean(), shifts.T @ (expit(pred)-y) / total

    center = minimize(objective, w, method='L-BFGS-B', jac=True,
                      bounds=[(min(GRID), max(GRID))]*len(w),
                      options={'gtol': 1e-12, 'ftol': 1e-15}).x
    value, gradient = objective(center)
    # Across the box each logit lies between these extrema. Its least
    # curvature is at the endpoint farthest from zero.
    lo = z + max(GRID)*np.minimum(shifts, 0).sum(axis=1)
    hi = z + max(GRID)*np.maximum(shifts, 0).sum(axis=1)
    tail = expit(-np.maximum(abs(lo), abs(hi)))
    curvature = shifts.T @ ((tail*(1-tail))[:, None]*shifts) / total
    grid = np.array(list(product(GRID, repeat=len(w))))
    offset = grid-center
    lower = value + offset @ gradient + .5*np.sum((offset @ curvature)*offset, axis=1)
    pred = z + shifts @ w
    best_loss = loss(pred, y).mean()
    cutoff = best_loss - 1e-5
    max_brier = np.square(expit(pred)-y).mean()
    evaluated = 0
    for j in np.argsort(lower):
        if lower[j] > cutoff + 1e-12:
            break
        evaluated += 1
        pred = z + shifts @ grid[j]
        score = loss(pred, y).mean()
        if score <= cutoff and np.square(expit(pred)-y).mean() <= max_brier:
            w = grid[j]
            cutoff = score
    print('global check', len(grid), 'combinations;', evaluated, 'exact after bound; weights', w,
          flush=True)
    return w


def metrics(blocks, selected, year):
    totals = []
    for w in [np.zeros_like(selected), selected]:
        calibration = np.zeros(20)
        scores = []
        auc = []
        for z, y, shifts in blocks:
            v = z + (shifts @ w).reshape(z.shape)
            p = expit(v)
            scores.append([y.size, loss(v,y).sum(), np.square(p-y).sum()])
            calibration += np.bincount(np.minimum((20*p).astype(int),19).ravel(),
                                       (p-y).ravel(), minlength=20)
            for j in range(y.shape[1]):
                true = y[:,j]
                n = true.sum()
                if 0 < n < len(true):
                    auc.append((rankdata(v[:,j])[true].sum()-n*(n+1)/2)/(n*(len(true)-n)))
        counts, losses, briers = np.array(scores).T
        totals.append(losses)
        print(year, 'n, loss, Brier, ECE, mean problem AUC, valid problems:',
              int(counts.sum()), losses.sum()/counts.sum(), briers.sum()/counts.sum(),
              abs(calibration).sum()/counts.sum(), np.mean(auc), len(auc))
    delta = totals[1]-totals[0]
    idx = np.random.default_rng(42).integers(len(delta), size=(10000,len(delta)))
    print(year, 'round wins, loss delta interval', (delta<0).sum(),
          np.quantile(delta[idx].sum(axis=1)/counts[idx].sum(axis=1), [.025,.975]))


if __name__ == '__main__':
    run(Search())
