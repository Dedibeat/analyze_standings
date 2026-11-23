"""Checkpointed, development-only LightGBM search for retrospective CF solve predictions."""
import argparse
import json
import time
from itertools import product
from pathlib import Path

import lightgbm as lgb
import numpy as np
from scipy.special import expit

from cf_boost_data import CACHE, NAMES
from cf_four_metrics import aggregate, field_correction, round_scores

FEATURES = {
    'full': NAMES,
    'history': tuple(n for n in NAMES if n not in ('slot_residual', 'slot_information', 'topic_residual',
                                                    'topic_information', 'matched_topics', 'speed_by_slot')),
    'behavior': tuple(n for n in NAMES if n not in ('pre_rating', 'position', 'educational',
                                                     'duration_hours', 'matched_topics')),
}
STRENGTHS = (.5, 1.)
CALIBRATIONS = ('raw', 'field', 'task', 'rank')
OUTPUT = CACHE / 'search'


def panel(year, cache=CACHE):
    rows = []
    for cid in json.loads((cache/f'{year}.json').read_text()):
        with np.load(cache/f'{cid}.npz') as row:
            rows.append(tuple(row[k] for k in ('x', 'z', 'y', 'train')))
    return rows


def configuration(index):
    # Visit each feature/depth/regularization configuration before repeating with a new seed.
    options = list(product(FEATURES, (7, 15, 31, 63), (80, 400, 1600), (.025, .07)))
    np.random.default_rng(20261119).shuffle(options)
    family, leaves, minimum, rate = options[index % len(options)]
    return family, dict(num_leaves=leaves, min_data_in_leaf=minimum, learning_rate=rate,
                        seed=501+index//len(options), feature_fraction=.85, bagging_fraction=.8,
                        bagging_freq=1, lambda_l2=20., objective='binary', verbosity=-1,
                        num_threads=4, force_col_wise=True, deterministic=True)


def transform(base, raw, y, train, strength, method):
    z = base + strength*raw
    if method == 'rank':
        for j in range(z.shape[1]):
            z[:, j] = np.interp(z[:, j], np.sort(z[train,j]), np.sort(base[train,j]))
    elif method == 'field':
        z += field_correction(z, y, train)
    elif method == 'task':
        p = expit(z[train])
        z += (y[train]-p).sum(axis=0)/(8+(p*(1-p)).sum(axis=0))
    return z[~train]


def scores(rows, raw, strength, method):
    pairs = [(transform(z, r, y, train, strength, method), y[~train])
             for (_, z, y, train), r in zip(rows, raw, strict=True)]
    return round_scores(pairs)


def summary(rounds):
    mid = len(rounds)//2
    return np.stack([aggregate(r.sum(axis=0)) for r in (rounds, rounds[:mid], rounds[mid:])])


def difference(scores_, incumbent):
    # Positive is better for every metric in the selection rule.
    return (scores_-incumbent)*np.array([-1, -1, -1, 1])


def select(record, baseline):
    gain = difference(np.array(record['metrics']), baseline)
    # Favor an improvement in both chronological halves before using the full-period loss.
    return (bool(np.all(gain[0]>0)), min(int((gain[1]>0).sum()), int((gain[2]>0).sum())),
            float(gain[0,0]))


def get_predictions(model, rows, columns, iterations):
    results = []
    for x, z, _, _ in rows:
        flat = x.reshape(-1, x.shape[-1])
        results.append(model.predict(flat[:,columns], num_iteration=iterations, raw_score=True,
                                     num_threads=4).reshape(z.shape))
    return results


def atomic_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2)+'\n')
    tmp.replace(path)


def search(until, max_trials):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    dev = panel(2025)
    reference = summary(round_scores([(z[~t], y[~t]) for _, z, y, t in dev]))
    np.testing.assert_allclose(reference[0], [.19755138, .06046434, .00122228, .87281935], atol=1e-8)
    atomic_json(OUTPUT/'baseline.json', reference.tolist())
    training = panel(2024)
    data = np.concatenate([x.reshape(-1,x.shape[-1]) for x, *_ in training])
    response = np.concatenate([y.ravel() for _, _, y, _ in training])
    offset = np.concatenate([z.ravel() for _, z, _, _ in training])
    del training
    best_file = OUTPUT/'best.json'
    best = json.loads(best_file.read_text()) if best_file.exists() else None
    datasets = {}
    for index in range(max_trials):
        path = OUTPUT/f'trial-{index:04}.json'
        if path.exists():
            continue
        if time.time() >= until:
            break
        family, params = configuration(index)
        cols = [NAMES.index(n) for n in FEATURES[family]]
        if family not in datasets:
            datasets[family] = lgb.Dataset(data[:,cols], label=response, init_score=offset,
                                            params={'feature_pre_filter': False, 'max_bin': 127,
                                                    'num_threads': 4})
        model = lgb.train(params, datasets[family], num_boost_round=180)
        records = []
        for depth in (45, 100, 180):
            raw = get_predictions(model, dev, cols, depth)
            for strength, method in product(STRENGTHS, CALIBRATIONS):
                result = summary(scores(dev, raw, strength, method))
                record = dict(trial=index, iterations=depth, family=family, strength=strength,
                              calibration=method, metrics=result.tolist())
                records.append(record)
                if best is None or select(record, reference) > select(best, reference):
                    # A distinct model filename keeps the last selected checkpoint valid across interruption.
                    model_file = OUTPUT/f'selected-{index:04}.txt'
                    if not model_file.exists():
                        tmp = model_file.with_suffix('.tmp')
                        model.save_model(str(tmp))
                        tmp.replace(model_file)
                    best = record
                    atomic_json(best_file, best)
        atomic_json(path, dict(parameters=params, candidates=records))
        print('trial', index, family, 'best', best['trial'], best['metrics'][0], flush=True)


def evaluate(year, record):
    rows = panel(year)
    model = lgb.Booster(model_file=str(OUTPUT/f"selected-{record['trial']:04}.txt"))
    columns = [NAMES.index(n) for n in FEATURES[record['family']]]
    raw = get_predictions(model, rows, columns, record['iterations'])
    ref = round_scores([(z[~t], y[~t]) for _, z, y, t in rows])
    fit = scores(rows, raw, record['strength'], record['calibration'])
    idx = np.random.default_rng(42).integers(len(ref), size=(10000, len(ref)))
    delta = aggregate(fit[idx].sum(axis=1)) - aggregate(ref[idx].sum(axis=1))
    return dict(year=year, rounds=len(ref), cells=int(ref[:,0].sum()), incumbent=summary(ref).tolist(),
                candidate=summary(fit).tolist(), interval=np.quantile(delta, [.025,.975], axis=0).tolist(),
                loss_wins=int(np.sum(fit[:,1]<ref[:,1])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--until', type=float, help='Unix timestamp to stop starting new trials')
    parser.add_argument('--max-trials', type=int, default=10000)
    parser.add_argument('--evaluate', type=int, choices=[2025, 2026])
    args = parser.parse_args()
    if args.evaluate:
        print(json.dumps(evaluate(args.evaluate, json.loads((OUTPUT/'best.json').read_text())), indent=2))
    elif args.until:
        search(args.until, args.max_trials)
    else:
        parser.error('Specify --until or --evaluate')
