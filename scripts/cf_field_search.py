"""Fit regularized per-problem models on other participants in the same round."""
import argparse
import json
from itertools import product

import numpy as np
from scipy.special import expit

from cf_boost_data import CACHE, NAMES
from cf_boost_search import atomic_json, panel, select, summary
from cf_four_metrics import field_correction, round_scores

GROUPS = {
    'speed': ['easy_speed', 'hard_speed', 'recency', 'zero_history', 'speed_by_slot'],
    'skill': ['topic_residual', 'slot_residual', 'long_easy_residual', 'long_hard_residual',
              'recent_easy_residual', 'recent_hard_residual', 'rating_trend', 'weighted_rank'],
    'context': ['topic_information', 'slot_information', 'rank_variability', 'rated_appearances',
                'easy_information', 'hard_information'],
}
FIELD = CACHE / 'field'
RIDGES = (20, 80, 320, 1280)
SCALES = (.4, .8, 1.2)
METHODS = ('raw', 'field', 'rank', 'blend')


def feature_matrix(x, z, train, group):
    names = {'speed': GROUPS['speed'], 'skill': GROUPS['skill'],
             'combined': GROUPS['speed'] + GROUPS['skill'],
             'all': sum(GROUPS.values(), [])}[group]
    x = x[..., [NAMES.index(n) for n in names]].astype(float)
    mean = x[train].mean(axis=0)
    std = x[train].std(axis=0)
    f = np.clip((x-mean)/np.maximum(std,.02), -4, 4)
    gate = np.tanh(z/2)[...,None]
    return np.concatenate([np.ones_like(gate), gate, f, gate*f], axis=2)


def solve(f, z, y, mask, ridge, iterations):
    # One coefficient vector per problem. Keep a finite intercept on sparse tasks.
    dim = f.shape[2]
    w = np.zeros((f.shape[1], dim))
    for _ in range(iterations):
        for j in range(f.shape[1]):
            v = f[mask,j]
            q = expit(z[mask,j]+v @ w[j])
            info = v.T @ ((q*(1-q))[:, None]*v)
            info.flat[::dim+1] += ridge
            grad = v.T @ (y[mask,j]-q) - ridge*w[j]
            w[j] += np.linalg.solve(info, grad)
    return np.einsum('ijk,jk->ij', f, w)


def field_raw(rows, group, ridge, iterations):
    raw = []
    for x, z, y, train in rows:
        f = feature_matrix(x, z, train, group)
        # Score training players out of fold when using their predictions for calibration.
        r = solve(f, z, y, train, ridge, iterations)
        halves = np.zeros(len(train), bool)
        halves[np.flatnonzero(train)[::2]] = True
        for cal in (train & halves, train & ~halves):
            # Scale regularization to preserve its ratio to sample size.
            r[cal] = solve(f, z, y, train & ~cal, ridge*(train & ~cal).sum()/train.sum(),
                           iterations)[cal]
        raw.append(r)
    return raw


def predictions(rows, raw, scale, method):
    result = []
    for (_, z, y, t), r in zip(rows,raw,strict=True):
        v = z + scale*r
        if method == 'field':
            v += field_correction(v,y,t)
        if method in ('rank','blend'):
            aligned = np.empty_like(v)
            for j in range(v.shape[1]):
                aligned[:,j] = np.interp(v[:,j], np.sort(v[t,j]), np.sort(z[t,j]))
            v = aligned if method == 'rank' else (v+aligned)/2
        result.append((v[~t], y[~t]))
    return result


def search():
    rows = panel(2025)
    baseline = summary(round_scores([(z[~t], y[~t]) for _,z,y,t in rows]))
    FIELD.mkdir(parents=True, exist_ok=True)
    best_path = FIELD/'best.json'
    best = json.loads(best_path.read_text()) if best_path.exists() else None
    for group, iterations, ridge in product(('speed','skill','combined','all'), (1,3), RIDGES):
        path = FIELD/f'{group}-{iterations}-{ridge}.json'
        if path.exists():
            continue
        raw = field_raw(rows,group,ridge,iterations)
        records = []
        for scale, method in product(SCALES,METHODS):
            metrics = summary(round_scores(predictions(rows,raw,scale,method)))
            rec = dict(group=group, ridge=ridge, iterations=iterations, scale=scale, method=method,
                       metrics=metrics.tolist())
            records.append(rec)
            if best is None or select(rec,baseline)>select(best,baseline):
                best = rec
                atomic_json(best_path,best)
        atomic_json(path, records)
        print(group, iterations, ridge, 'best', best['metrics'][0], flush=True)


def evaluate(year, best):
    rows = panel(year)
    raw = field_raw(rows,best['group'],best['ridge'],best['iterations'])
    ref = round_scores([(z[~t], y[~t]) for _,z,y,t in rows])
    fit = round_scores(predictions(rows,raw,best['scale'],best['method']))
    return ref,fit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluate', type=int, choices=(2025,2026))
    args = parser.parse_args()
    if args.evaluate:
        ref, fit = evaluate(args.evaluate,json.loads((FIELD/'best.json').read_text()))
        print(summary(ref),summary(fit))
    else:
        search()
