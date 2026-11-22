"""Matched 2025 feature ablations of an already locked rolling recipe."""
import argparse
import json

from cf_boost_search import atomic_json, scores, summary
from cf_confirm_models import CONFIRM
from cf_cross_history import ITEM_NAMES, PLAYER_NAMES
from cf_rolling_boost import Rolling

ABLATIONS = {
    'full': {},
    'without all-division history': dict(drop=(*PLAYER_NAMES,*ITEM_NAMES)),
    'without solve speed': dict(drop=('easy_speed','hard_speed','speed_by_slot','cross_speed',
                                      'last_solve_fraction')),
    'without rank performance': dict(drop=('weighted_rank','rank_variability','fast_performance',
                                           'slow_performance','performance_sd','current_format_performance')),
    'without problem specialization': dict(drop=('topic_residual','topic_information','slot_residual',
                                                'slot_information','matched_topics',*ITEM_NAMES)),
    'one January fit': dict(chunks=1),
    'one-year lookback': dict(lookback=1),
}


def run(lock):
    path = CONFIRM/lock
    record = json.loads((path/'selection.json').read_text())['sources']['rolling']
    outfile = path/'ablations.json'
    results = json.loads(outfile.read_text()) if outfile.exists() else {}
    dev = Rolling(2025)
    for name,params in ABLATIONS.items():
        if name in results:
            continue
        raw = dev.predict(record['recipe'],**params)
        measures = scores(dev.rows,raw,record['strength'],record['calibration'])
        results[name] = summary(measures).tolist()
        atomic_json(outfile,results)
        print(name,results[name][0],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('lock')
    run(parser.parse_args().lock)
