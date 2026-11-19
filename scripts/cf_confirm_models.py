"""Lock 2025 selections, then apply those published recipes to later rounds."""
import argparse
import json
from itertools import product

import lightgbm as lgb
import numpy as np
from scipy.special import expit

from cf_boost_data import CACHE, NAMES
from cf_boost_search import (FEATURES, OUTPUT, atomic_json, configuration, difference, get_predictions,
                             panel, select, summary, transform)
from cf_factor_search import FACTORS, events, prediction, replay
from cf_field_search import FIELD, field_raw, predictions
from cf_four_metrics import aggregate, round_scores
from cf_rolling_boost import ROLLING, Rolling

CONFIRM = CACHE/'confirm'


def fixed_model(record, fold):
    if fold==0:
        return lgb.Booster(model_file=str(OUTPUT/f"selected-{record['trial']:04}.txt"))
    cache = CACHE.with_name(f'{CACHE.name}_fold{fold}')
    train = panel(2024,cache)
    cols = [NAMES.index(n) for n in FEATURES[record['family']]]
    x = np.concatenate([v.reshape(-1,v.shape[-1])[:,cols] for v,_,_,_ in train])
    data = lgb.Dataset(x, label=np.concatenate([y.ravel() for _,_,y,_ in train]),
                       init_score=np.concatenate([z.ravel() for _,z,_,_ in train]),
                       params={'feature_pre_filter':False,'max_bin':127,'num_threads':4})
    return lgb.train(configuration(record['trial'])[1],data,num_boost_round=record['iterations'])


def components(year,fold,records):
    cache = CACHE if fold==0 else CACHE.with_name(f'{CACHE.name}_fold{fold}')
    model = fixed_model(records['fixed'],fold)
    rows = panel(year,cache)
    reference = [(z[~t],y[~t]) for _,z,y,t in rows]
    r = records['fixed']
    raw = get_predictions(model,rows,[NAMES.index(n) for n in FEATURES[r['family']]],r['iterations'])
    fixed = [transform(z,v,y,t,r['strength'],r['calibration'])
             for (_,z,y,t),v in zip(rows,raw,strict=True)]
    r = records['field']
    raw = field_raw(rows,r['group'],r['ridge'],r['iterations'])
    field = [z for z,_ in predictions(rows,raw,r['scale'],r['method'])]
    del raw,rows,model
    r = records['rolling']
    rolling = Rolling(year,fold)
    raw = rolling.predict(r['recipe'])
    recent = [transform(z,v,y,t,r['strength'],r['calibration'])
              for (_,z,y,t),v in zip(rolling.rows,raw,strict=True)]
    del rolling, raw
    r = records['factor']
    factor_rounds = replay(events(year,fold),r['dims'],r['retention'],r['penalty'])
    factor = [z for z,_ in prediction(factor_rounds,r['strength'],r['method'])]
    return reference, [fixed,field,recent,factor]


def blend(reference, models, weights):
    return [(base + sum(w*(m[i]-base) for m,w in zip(models,weights,strict=True)), y)
            for i,(base,y) in enumerate(reference)]


def confidence(base,fit):
    idx = np.random.default_rng(42).integers(len(base),size=(10000,len(base)))
    d = aggregate(fit[idx].sum(axis=1))-aggregate(base[idx].sum(axis=1))
    return np.quantile(d,[.025,.975],axis=0)


def freeze(path):
    sources = {k:json.loads((d/'best.json').read_text()) for k,d in
               [('fixed',OUTPUT),('field',FIELD),('rolling',ROLLING),('factor',FACTORS)]}
    reference,models = components(2025,0,sources)
    base = round_scores(reference)
    incumbent = summary(base)
    best_loss = best_balance = None
    trials = []
    idx = np.random.default_rng(17).integers(len(base),size=(1000,len(base)))
    base_boot = aggregate(base[idx].sum(axis=1))
    for parts in product(range(5),repeat=len(models)):
        if sum(parts) != 4:
            continue
        for strength in (.65,1.):
            weights = (strength*np.array(parts)/4).tolist()
            fit = round_scores(blend(reference,models,weights))
            metrics = summary(fit)
            rec = dict(weights=weights,metrics=metrics.tolist())
            se = (aggregate(fit[idx].sum(axis=1))-base_boot).std(axis=0)
            rec['minimum_z'] = float(np.min(difference(metrics,incumbent)[0]/np.maximum(se,1e-12)))
            quality = select(rec,incumbent)
            balance = quality[:2]+(rec['minimum_z'],quality[2])
            if best_loss is None or quality>best_loss[0]:
                best_loss = quality,rec
            if best_balance is None or balance>best_balance[0]:
                best_balance = balance,rec
            trials.append(rec)
    atomic_json(path/'selection.json',dict(sources=sources,baseline=incumbent.tolist(),trials=trials,
                                           loss=best_loss[1],balanced=best_balance[1]))
    print('locked',path.name,'loss',best_loss[1],'balanced',best_balance[1],flush=True)


def confirm(path,year,fold):
    frozen = json.loads((path/'selection.json').read_text())
    reference,models = components(year,fold,frozen['sources'])
    base = round_scores(reference)
    report = dict(year=year,fold=fold,rounds=len(base),opportunities=int(base[:,0].sum()),
                  reference=summary(base).tolist(),candidates={})
    for key in ('loss','balanced'):
        pred = blend(reference,models,frozen[key]['weights'])
        fit = round_scores(pred)
        report['candidates'][key] = dict(metrics=summary(fit).tolist(),interval=confidence(base,fit).tolist(),
                                         loss_wins=int(np.sum(fit[:,1]<base[:,1])))
        arrays = {f'r{i}':np.stack([ref,z,y],axis=-1) for i,((ref,_),(z,y)) in
                  enumerate(zip(reference,pred,strict=True))}
        np.savez_compressed(path/f'{year}-fold{fold}-{key}.npz',**arrays)
    atomic_json(path/f'{year}-fold{fold}.json',report)
    print(year,fold,report['reference'][0],{k:v['metrics'][0] for k,v in report['candidates'].items()},
          flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--year',type=int,choices=(2025,2026),default=2026)
    parser.add_argument('--fold',type=int,choices=range(5),default=0)
    args=parser.parse_args()
    path=CONFIRM/args.name
    path.mkdir(parents=True,exist_ok=True)
    if args.freeze:
        if (path/'selection.json').exists():
            parser.error('This selection has already been locked.')
        freeze(path)
    else:
        confirm(path,args.year,args.fold)
