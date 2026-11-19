"""Forward-only refits using all-division histories and ended training fields."""
import argparse
import json
import time
from itertools import product

import lightgbm as lgb
import numpy as np

from cf_ai_deflation import contests
from cf_boost_data import CACHE, NAMES
from cf_boost_search import CALIBRATIONS, atomic_json, scores, select, summary
from cf_cross_history import CROSS, ITEM_NAMES, PLAYER_NAMES
from cf_four_metrics import round_scores

ROLLING = CACHE/'rolling'
YEAR_DAYS = 365.25*86400
FEATURE_NAMES = (*NAMES, *PLAYER_NAMES, *ITEM_NAMES)


def config(index):
    options = list(product((7,15,31,63), (.5,1.,2.), (100,500), (75,150), ('all','cross')))
    np.random.default_rng(19).shuffle(options)
    leaves, half_life, minimum, trees, features = options[index%len(options)]
    return dict(leaves=leaves, half_life=half_life, minimum=minimum, trees=trees,
                features=features, seed=111+index//len(options))


def load_year(year, fold=0, crossfit=False):
    root = CACHE if fold == 0 else CACHE.with_name(f'{CACHE.name}_fold{fold}')
    curve_cache = root.with_name(root.name + "_crossfit")
    if year < 2024:
        root = root.with_name(root.name+'_long')
    ids = json.loads((root/f'{year}.json').read_text())
    rows = []
    for cid in ids:
        with np.load(root/f'{cid}.npz') as base, np.load(CROSS/f'{cid}.npz') as extra:
            known = (extra['digest']<51*fold) | (extra['digest']>=51*(fold+1))
            keep = known if year <= 2024 else np.ones_like(known)
            x, z, y, train = (base[k] for k in ('x','z','y','train'))
            if crossfit:
                with np.load(curve_cache/f'{cid}.npz') as independent:
                    np.testing.assert_array_equal(z[~train],independent['z'][~train])
                    z = independent['z']
                    x[:,:,0] = z
                    x[:,:,1] = independent['local']
                    x[:,:,2] = independent['difficulty']
            np.testing.assert_array_equal(extra['old'][keep], x[:,0,NAMES.index('pre_rating')])
            np.testing.assert_array_equal(extra['solved'][keep],y)
            if year > 2024:
                np.testing.assert_array_equal(known,train)
            player = extra['player'][keep,None,:]
            assert player.shape[-1] == len(PLAYER_NAMES)
            wide = np.concatenate([x,np.broadcast_to(player,(*z.shape,player.shape[-1])),
                                   extra['item'][keep]], axis=-1)
            rows.append((wide,z,y,train))
    return ids,rows


class Rolling:
    def __init__(self, year, fold=0, crossfit=False):
        self.year = year
        self.contests = {c['id']:c for c in contests()}
        self.archive = []
        self.ids = []
        self.rows = []
        for y in range(year-3,year+1):
            ids,rows = load_year(y, fold, crossfit)
            if y==year:
                self.ids,self.rows=ids,rows
            for cid,(x,z,outcome,train) in zip(ids,rows,strict=True):
                # Sample whole participants, retaining their entire task set.
                rng = np.random.default_rng(cid)
                keep = train & (rng.random(len(train))<.35)
                self.archive.append((cid,x[keep].reshape(-1,x.shape[-1]),
                                     z[keep].ravel(),outcome[keep].ravel()))

    def predict(self, recipe, chunks=4, drop=(), lookback=3):
        raw = []
        columns = np.arange(len(FEATURE_NAMES))
        if recipe['features']=='cross':
            columns = np.array([0,1,2,3,6,7,8,9,10,*range(len(NAMES),len(FEATURE_NAMES))])
        columns = np.array([j for j in columns if FEATURE_NAMES[j] not in drop])
        for ix in np.array_split(np.arange(len(self.rows)),chunks):
            cutoff = self.contests[self.ids[ix[0]]]['startTimeSeconds']
            xs,ys,zs,ws = [],[],[],[]
            for cid,x,z,y in self.archive:
                c = self.contests[cid]
                end = c['startTimeSeconds'] + c['durationSeconds']
                age = (cutoff-end)/YEAR_DAYS
                if 0 < age <= lookback:
                    xs.append(x[:,columns])
                    ys.append(y)
                    zs.append(z)
                    ws.append(np.full(len(y),.5**(age/recipe['half_life']), dtype='f'))
            data = lgb.Dataset(np.concatenate(xs), label=np.concatenate(ys),
                               init_score=np.concatenate(zs), weight=np.concatenate(ws),
                               params={'max_bin':95, 'num_threads':3})
            params = dict(objective='binary',verbosity=-1,num_threads=3,deterministic=True,
                          force_col_wise=True,num_leaves=recipe['leaves'],learning_rate=.05,
                          min_data_in_leaf=recipe['minimum'],lambda_l2=24,
                          bagging_fraction=.85,bagging_freq=1,feature_fraction=.85,seed=recipe['seed'])
            model = lgb.train(params,data,num_boost_round=recipe['trees'])
            for i in ix:
                x,z,_,_ = self.rows[i]
                values = x.reshape(-1,x.shape[-1])[:,columns]
                raw.append(model.predict(values,raw_score=True,num_threads=3).reshape(z.shape))
        return raw


def search(until, max_trials=10000, crossfit=False):
    destination = ROLLING.with_name("rolling_crossfit") if crossfit else ROLLING
    destination.mkdir(parents=True,exist_ok=True)
    dev = Rolling(2025, crossfit=crossfit)
    baseline = summary(round_scores([(z[~t],y[~t]) for _,z,y,t in dev.rows]))
    path = destination/'best.json'
    best = json.loads(path.read_text()) if path.exists() else None
    for i in range(max_trials):
        if time.time()>=until:
            break
        output = destination/f'trial-{i:04}.json'
        if output.exists():
            continue
        recipe = config(i)
        raw = dev.predict(recipe)
        results = []
        for scale,method in product((.5,.8,1.,1.2), CALIBRATIONS):
            metrics = summary(scores(dev.rows,raw,scale,method))
            record = dict(trial=i, recipe=recipe, strength=scale, calibration=method, metrics=metrics.tolist())
            results.append(record)
            if best is None or select(record,baseline)>select(best,baseline):
                best = record
                atomic_json(path,best)
        atomic_json(output,results)
        print('rolling trial',i,'best',best['trial'],best['metrics'][0],flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--until',type=float,required=True)
    parser.add_argument('--max-trials', type=int, default=10000)
    parser.add_argument('--crossfit', action='store_true')
    args = parser.parse_args()
    search(args.until, args.max_trials, args.crossfit)
