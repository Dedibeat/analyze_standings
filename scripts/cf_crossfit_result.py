"""Lock the inner-fold rolling learner and confirm without reselecting by evaluation fold."""
import argparse
import json

import numpy as np

from cf_boost_search import atomic_json, summary, transform
from cf_confirm_models import CONFIRM, confidence
from cf_four_metrics import round_scores
from cf_rolling_boost import ROLLING, Rolling


def confirm(fold):
    lock = CONFIRM/'crossfit'
    lock.mkdir(parents=True, exist_ok=True)
    selection = lock/'selection.json'
    if not selection.exists():
        atomic_json(selection, json.loads((ROLLING.with_name('rolling_crossfit')/'best.json').read_text()))
    winner = json.loads(selection.read_text())
    replay = Rolling(2026,fold,crossfit=True)
    raw=replay.predict(winner['recipe'])
    reference=[(z[~t],y[~t]) for _,z,y,t in replay.rows]
    predictions=[(transform(z,r,y,t,winner['strength'],winner['calibration']),y[~t])
                 for (_,z,y,t),r in zip(replay.rows,raw,strict=True)]
    ref,fit=round_scores(reference),round_scores(predictions)
    result=dict(fold=fold,opportunities=int(ref[:,0].sum()),reference=summary(ref).tolist(),
                selected=summary(fit).tolist(), interval=confidence(ref,fit).tolist(),
                loss_wins=int(np.sum(fit[:,1]<ref[:,1])))
    arrays={f'r{i}':np.stack([base,z,y],axis=-1) for i,((base,_),(z,y)) in
            enumerate(zip(reference,predictions,strict=True))}
    np.savez_compressed(lock/f'2026-fold{fold}-standalone.npz',**arrays)
    atomic_json(lock/f'2026-fold{fold}.json',result)
    print(fold,result['selected'][0],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--fold',type=int,choices=range(5),required=True)
    confirm(parser.parse_args().fold)
