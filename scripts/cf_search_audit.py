"""Summarize locked predictions on disjoint handle folds and calibration sensitivities."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from cf_ai_deflation import ROOT, ST
from cf_boost_data import CACHE
from cf_boost_search import atomic_json, summary
from cf_confirm_models import CONFIRM, confidence
from cf_four_metrics import round_scores


def calibration(p, y, bins):
    idx = np.minimum((p*bins).astype(int), bins-1)
    residual = np.bincount(idx,p-y,minlength=bins)
    n = len(y)
    variance = np.bincount(idx,p*(1-p),minlength=bins)
    return dict(ece=abs(residual).sum()/n, bias=(p-y).mean(),
                independent_null_approx=np.sqrt(2/np.pi)*np.sqrt(variance).sum()/n)


def check(lock, key, folds):
    path=CONFIRM/lock
    ids=json.loads((CACHE/'2026.json').read_text())
    by_round=[[] for _ in ids]
    subset=[[] for _ in ids]
    for fold in folds:
        cache = CACHE if fold==0 else CACHE.with_name(f'{CACHE.name}_fold{fold}')
        with np.load(path/f'2026-fold{fold}-{key}.npz') as predictions:
            for i,cid in enumerate(ids):
                arr=predictions[f'r{i}']
                with np.load(cache/f'{cid}.npz') as data:
                    old=data['x'][~data['train'],0,6]
                    np.testing.assert_array_equal(arr[:,:,2],data['y'][~data['train']])
                by_round[i].append(arr)
                probs=json.loads(gzip.decompress((ST/f'{cid}.json.gz').read_bytes()))['problems']
                official=np.array([r for _,r in probs if r is not None])
                gap=official-old[:,None]
                eligible=(old[:,None]>=1000)&(old[:,None]<1600)
                subset[i].append(np.select([eligible&(gap>=600),eligible&(gap<=0)],[1,2],default=0))
    by_round=[np.concatenate(xs) for xs in by_round]
    subset=[np.concatenate(xs) for xs in subset]
    ref=round_scores([(a[:,:,0], a[:,:,2].astype(bool)) for a in by_round])
    fit=round_scores([(a[:,:,1], a[:,:,2].astype(bool)) for a in by_round])
    data=np.concatenate([a.reshape(-1,3) for a in by_round])
    y=data[:,2]
    result=dict(folds=folds, opportunities=len(y), reference=summary(ref).tolist(),
                selected=summary(fit).tolist(),interval=confidence(ref,fit).tolist(),
                loss_wins=int((fit[:,1]<ref[:,1]).sum()),calibration={},subgroups={})
    membership=np.concatenate([x.ravel() for x in subset])
    for j,label in enumerate(('reference','selected')):
        p=expit(data[:,j])
        result['calibration'][label]={str(b):calibration(p,y,b) for b in (10,20,40)}
        for ix,group in enumerate(('remaining','1000-1599 and gap >=600','1000-1599 and gap <=0')):
            keep=membership==ix
            z=data[keep,j]
            out=result['subgroups'].setdefault(group,dict(opportunities=int(keep.sum()),
                                                          solve_rate=y[keep].mean()))
            out[label]=dict(loss=(np.logaddexp(0,z)-y[keep]*z).mean(),brier=np.square(p[keep]-y[keep]).mean())
    return result


def archive(output):
    sources={'fixed':CACHE/'search','field':CACHE/'field','rolling':CACHE/'rolling','factor':CACHE/'factors',
             'rolling_crossfit':CACHE/'rolling_crossfit'}
    data={'metric_order':['log loss','Brier','20-bin ECE','within-problem macro AUC'],
          'period_order':['2025 full','first half of rounds','second half of rounds'],'families':{}}
    for name,path in sources.items():
        data['families'][name]={p.stem:json.loads(p.read_text()) for p in sorted(path.glob('*.json'))
                                if p.name not in ('best.json','baseline.json')}
    output.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('lock')
    parser.add_argument('--folds',type=int,nargs='+',default=list(range(5)))
    parser.add_argument('--archive',action='store_true')
    parser.add_argument('--keys',nargs='+',default=['balanced','loss'])
    args=parser.parse_args()
    result={key:check(args.lock,key,args.folds) for key in args.keys}
    out=CONFIRM/args.lock
    atomic_json(out/('audit-'+'-'.join(map(str,args.folds))+'.json'), result)
    if args.archive:
        archive(ROOT/'output/cf_five_hour_trials.json.gz')
    print({key:v['selected'][0] for key,v in result.items()})
