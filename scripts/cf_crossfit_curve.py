"""Recompute each training player's problem-curve features without their own fold."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from heapq import heappop, heappush

import numpy as np
from scipy.special import expit

from cf_ai_deflation import RC, ST, VET, contests
from cf_boost_data import CACHE, NAMES
from cf_difficulty_pilot import slope_predictions
from cf_metric_search import Search, baseline, corrections
from cf_solve_history import SCALE, local_curve


def history(x):
    f = x[:,0,:]
    info=np.expm1(f[:,[NAMES.index('easy_information'),NAMES.index('hard_information')]].astype(float))
    out=np.zeros((len(f),2,4))
    out[:,0,1::2]=info
    out[:,0,::2]=f[:,[NAMES.index('long_easy_residual'),NAMES.index('long_hard_residual')]]*(2+info)
    out[:,1,::2]=2*f[:,[NAMES.index('recent_easy_residual'),NAMES.index('recent_hard_residual')]]
    return out


def adjusted(z,hist,coef,weights,difficulty):
    p, base, f, band=baseline(z,hist)
    inc=base+(f[:,None,:]*coef[band]).sum(axis=2)
    x=corrections(p,inc,f,hist,difficulty)
    return inc+(x[0]@weights[0]+.5*x[3]@weights[3]).reshape(inc.shape)


def prepare(fold):
    cache=CACHE if fold==0 else CACHE.with_name(f'{CACHE.name}_fold{fold}')
    long=cache.with_name(cache.name+'_long')
    out=cache.with_name(cache.name+'_crossfit')
    out.mkdir(parents=True,exist_ok=True)
    paths={}
    for year in range(2022,2027):
        root=long if year<2024 else cache
        paths.update({cid:(root,year) for cid in json.loads((root/f'{year}.json').read_text())})
    fit=Search()
    for cid,(root,year) in paths.items():
        if year!=2024:
            continue
        with np.load(root/f'{cid}.npz') as data:
            x=data['x']
            fit.cells[year].append((x[:,:,1].astype(float),data['y'],history(x),x[0,:,2].astype(float)))
    coef,weights=fit.fit()
    del fit
    prior,trend,pending=Counter(),{},[]
    for c in sorted(contests(),key=lambda c:(c['startTimeSeconds'],c['id'])):
        cid,start=c['id'],c['startTimeSeconds']
        while pending and pending[0][0]<start:
            _,_,earlier=heappop(pending)
            for h,_,old,new in earlier:
                if prior[h]>=6:
                    trend[h]=.8*trend.get(h,0)+.2*(new-old)
                prior[h]+=1
        path=RC/f'{cid}.json.gz'
        if not path.exists():
            continue
        rows=json.loads(gzip.decompress(path.read_bytes()))['rows']
        heappush(pending,(start+c['durationSeconds'],cid,rows))
        if cid not in paths or (out/f'{cid}.npz').exists():
            continue
        root,year=paths[cid]
        d=json.loads(gzip.decompress((ST/f'{cid}.json.gz').read_bytes()))
        old={h:r for h,_,r,_ in rows if prior[h]>=VET}
        players=[(h,t) for h,_,t in d['rows'] if h in old]
        names,times=zip(*players)
        rated=[r is not None for _,r in d['problems']]
        y=(np.array(times)>=0)[:,rated]
        hashes=np.array([list(hashlib.sha256(h.encode()).digest()[:2]) for h in names])
        train=(hashes[:,0]<51*fold)|(hashes[:,0]>=51*(fold+1))
        group=hashes[:,1]%4
        a=np.array([SCALE*(old[h]-1500-1.20679056*trend.get(h,0)) -
                    .06933997*np.log(prior[h]/30) for h in names])
        with np.load(root/f'{cid}.npz') as data:
            keep=train if year<=2024 else np.ones_like(train)
            x=data['x']
            np.testing.assert_array_equal(y[keep],data['y'])
            np.testing.assert_array_equal(x[:,0,6],[old[h] for h,k in zip(names,keep) if k])
            z=data['z'].copy()
        hist=history(x)
        reproduced=adjusted(x[:,:,1].astype(float),hist,coef,weights,x[0,:,2])
        # Float32 feature cache; exactly-on-boundary bin assignment can differ.
        if np.mean(abs(reproduced-z))>1e-4:
            raise ValueError(f'incumbent reconstruction failed for {cid}')
        local=x[:,:,1].copy()
        difficulty=x[:,:,2].copy()
        for g in range(4):
            sub=train&(group!=g)
            cal=train&(group==g)
            pos=cal[keep]
            logits=slope_predictions(a[sub],y[sub],a,False)
            logits=local_curve(a,y,sub,logits)
            rate=expit(logits[sub]).mean(axis=0)
            z[pos]=adjusted(logits[cal],hist[pos],coef,weights,rate)
            local[pos]=logits[cal]
            difficulty[pos]=rate
        tmp=out/f'{cid}.tmp.npz'
        np.savez(tmp,z=z,local=local,difficulty=difficulty)
        tmp.replace(out/f'{cid}.npz')
    print('cross-fitted panels',fold,len(paths),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--fold',type=int,default=0,choices=range(5))
    prepare(parser.parse_args().fold)
