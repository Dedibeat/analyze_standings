"""Score official CF ratings on exactly the same eligible opportunities."""
import gzip
import json

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from cf_ai_deflation import ST
from cf_boost_data import CACHE
from cf_boost_search import atomic_json, summary
from cf_four_metrics import round_scores
from cf_metric_search import loss
from cf_solve_history import SCALE


def official(year):
    result=[]
    for cid in json.loads((CACHE/f'{year}.json').read_text()):
        probs=json.loads(gzip.decompress((ST/f'{cid}.json.gz').read_bytes()))['problems']
        ratings=np.array([r for _,r in probs if r is not None])
        with np.load(CACHE/f'{cid}.npz') as data:
            mask=data['train'] if year==2024 else ~data['train']
            old=data['x'][mask,0,6].astype(float)
            z=SCALE*(old[:,None]-ratings)
            result.append((z,data['y'][mask]))
    return result


def benchmark():
    train=official(2024)
    x=np.concatenate([z.ravel() for z,_ in train])
    y=np.concatenate([s.ravel() for _,s in train])
    def objective(params):
        z=params[0]+params[1]*x
        err=expit(z)-y
        return loss(z,y).mean(), np.array([err.mean(),np.mean(err*x)])
    fit=minimize(objective,[0.,1.],jac=True,method='L-BFGS-B',bounds=[(None,None),(1e-6,None)],
                 options={'ftol':1e-15,'gtol':1e-10})
    if not fit.success:
        raise RuntimeError(fit.message)
    result={'intercept':fit.x[0],'slope':fit.x[1],'train_cells':len(x)}
    for year in (2025,2026):
        test=official(year)
        raw=round_scores(test)
        calibrated=round_scores([(fit.x[0]+fit.x[1]*z,y) for z,y in test])
        result[str(year)]=dict(opportunities=int(raw[:,0].sum()),raw=summary(raw).tolist(),
                               calibrated=summary(calibrated).tolist())
        np.testing.assert_allclose(raw[:,3],calibrated[:,3],atol=1e-10)
    np.testing.assert_allclose(result['2025']['raw'][0][0],.21915401172422183,atol=1e-9)
    atomic_json(CACHE/'official.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    benchmark()
