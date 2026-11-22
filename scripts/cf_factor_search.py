"""Chronological multidimensional player profiles learned from previous solve patterns."""
import argparse
import json
from heapq import heappop, heappush
from itertools import product

import numpy as np
from scipy.special import expit, logit

from cf_ai_deflation import contests
from cf_boost_data import CACHE
from cf_boost_search import atomic_json, select, summary, transform
from cf_cross_history import CROSS
from cf_four_metrics import round_scores

FACTORS = CACHE/'factors'


def events(year, fold):
    cache = CACHE if fold==0 else CACHE.with_name(f'{CACHE.name}_fold{fold}')
    targets = set(json.loads((cache/f'{year}.json').read_text()))
    last = max(c['startTimeSeconds'] for c in contests() if c['id'] in targets)
    result = []
    for c in sorted(contests(), key=lambda c:(c['startTimeSeconds'],c['id'])):
        cid,start = c['id'],c['startTimeSeconds']
        path = CROSS/f'{cid}.npz'
        if start>last:
            break
        if not path.exists():
            continue
        with np.load(path) as row:
            ids, old, digest, y = (row[k] for k in ('pid','old','digest','solved'))
        train = (digest < fold*51) | (digest >= (fold+1)*51)
        # Smooth historical solve probabilities against pre-round rating.
        bands = np.clip(np.rint(old/50).astype(int),0,85)
        smooth = np.exp(-.5*((np.arange(86)[:,None]-np.arange(86))/1.7)**2)
        n = np.bincount(bands[train],minlength=86)
        counts = np.zeros((86,y.shape[1]))
        np.add.at(counts,bands[train],y[train])
        prior = (y[train].sum(axis=0)+1)/(train.sum()+2)
        p = ((smooth@counts + 2*prior)/((smooth@n)[:,None]+2))[bands]
        target = None
        if cid in targets:
            with np.load(cache/f'{cid}.npz') as base:
                np.testing.assert_array_equal(y,base['y'])
                np.testing.assert_array_equal(train,base['train'])
                target = base['z']
        result.append((cid,start,start+c['durationSeconds'],ids,train,y,p,target))
    return result


def fit_items(u,z,y,train,prior,penalty):
    q = prior.copy()
    utr = u[train]
    for j in range(z.shape[1]):
        for _ in range(2):
            prob = expit(z[train,j]+utr @ q[j])
            hessian = utr.T @ ((prob*(1-prob))[:,None]*utr)
            hessian.flat[::len(q[j])+1] += penalty
            gradient = utr.T @ (y[train,j]-prob) - penalty*(q[j]-prior[j])
            q[j] += np.linalg.solve(hessian,gradient)
    return q


def replay(rounds, dims, retention, ridge):
    size = 1+max(ids.max() for _,_,_,ids,*_ in rounds)
    grad = np.zeros((size,dims),dtype='f')
    info = np.zeros((size,dims,dims),dtype='f')
    eye = np.eye(dims)
    pending = []
    forecast = []
    for cid,start,end,ids,train,y,p,target in rounds:
        while pending and pending[0][0]<start:
            _,_,idx,g,h = heappop(pending)
            grad[idx] = retention*grad[idx]+g
            info[idx] = retention*info[idx]+h
        u = np.linalg.solve(info[ids] + 3*eye,grad[ids,:,None])[...,0]
        u /= np.maximum(1,np.linalg.norm(u,axis=1,keepdims=True)/3)
        h = 1-2*p[train].mean(axis=0)
        slot = np.linspace(-1,1,len(h))
        # Fixed initial directions separate overall skill, harder tasks and task positions.
        prior = np.column_stack([np.ones_like(h),h,1.5*h*h-.5,slot,
                                 np.sin(np.pi*slot),np.cos(np.pi*slot)])[:,:dims]
        history_q = fit_items(u,logit(p),y,train,prior,ridge)
        if target is not None:
            q = fit_items(u,target,y,train,np.zeros_like(prior),ridge)
            forecast.append((target,y,train,u @ q.T))
        g = (y-p) @ history_q
        outer = np.einsum('ij,ik->ijk',history_q,history_q).reshape(len(h),-1)
        information = ((p*(1-p)) @ outer).reshape(len(ids),dims,dims)
        heappush(pending,(end,cid,ids,g,information))
    return forecast


def prediction(rounds, strength, method):
    return [(transform(z,raw,y,t,strength,method),y[~t]) for z,y,t,raw in rounds]


def search():
    data = events(2025,0)
    base = summary(round_scores([(z[~t],y[~t]) for _,_,_,_,t,y,_,z in data if z is not None]))
    FACTORS.mkdir(parents=True,exist_ok=True)
    best_path = FACTORS/'best.json'
    best = json.loads(best_path.read_text()) if best_path.exists() else None
    for dims, retention, penalty in product((2,4,6),(.8,.94,.985),(10,100,500)):
        path = FACTORS/f'{dims}-{retention}-{penalty}.json'
        if path.exists():
            continue
        rounds = replay(data,dims,retention,penalty)
        records = []
        for strength,method in product((.5,1.,1.5),('raw','field','rank','task')):
            values = summary(round_scores(prediction(rounds,strength,method)))
            rec = dict(dims=dims,retention=retention,penalty=penalty,strength=strength,
                       method=method,metrics=values.tolist())
            if best is None or select(rec,base)>select(best,base):
                best=rec
                atomic_json(best_path,best)
            records.append(rec)
        atomic_json(path,records)
        print(dims,retention,penalty,'best',best['metrics'][0],flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluate',type=int,choices=(2025,2026))
    args=parser.parse_args()
    if args.evaluate:
        b=json.loads((FACTORS/'best.json').read_text())
        rounds=replay(events(args.evaluate,0),b['dims'],b['retention'],b['penalty'])
        print(summary(round_scores(prediction(rounds,b['strength'],b['method']))))
    else:
        search()
