"""Extract player information from earlier rounds across all rated CF divisions."""
import gzip
import hashlib
import json
from heapq import heappop, heappush

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata

from cf_ai_deflation import D, RC, ST, VET, contests

CROSS = D / 'cross_history_v1'
PLAYER_NAMES = ('career_events', 'career_days', 'days_since_rated', 'below_peak',
                'fast_performance', 'slow_performance', 'performance_sd', 'rating_volatility',
                'fast_interval', 'cross_speed', 'cross_missed_easy', 'cross_hard_solves',
                'last_solve_fraction', 'scoreboard_history', 'current_format_performance')
ITEM_NAMES = ('individual_tag_residual', 'individual_tag_experience')


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def rank_performance(old, rank):
    # Compare within the same field of nonzero pre-round ratings. Integrate the Elo
    # win probability over 99 equally spaced quantiles of that field, then invert.
    known = old > 0
    performance = old.astype(float)
    if known.sum() > 1:
        rivals = np.quantile(old[known], (np.arange(99)+.5)/99)
        ruler = np.linspace(-1000, 5000, 501)
        beaten = expit((ruler[:,None]-rivals)*np.log(10)/400).mean(axis=1)
        share = 1-(rankdata(rank[known])-.5)/known.sum()
        performance[known] = np.interp(share, beaten, ruler)
    return np.clip(performance-old, -1200, 1200)


def fmt(name):
    if 'Educational' in name:
        return 0
    if 'Div. 2' in name and 'Div. 1' not in name:
        return 1
    if 'Div. 3' in name or 'Div. 4' in name:
        return 2
    return 3


def extract():
    catalog = sorted(contests(), key=lambda c: (c['startTimeSeconds'], c['id']))
    targets = {c['id'] for c in catalog if c['startTimeSeconds'] >= 1640995200
               and 'Div. 2' in c['name'] and 'Div. 1' not in c['name'] and (ST/f"{c['id']}.json.gz").exists()}
    handles = {}
    for cid in sorted(targets):
        for h, *_ in read(ST/f'{cid}.json.gz')['rows']:
            if h not in handles:
                handles[h] = len(handles)
    count = len(handles)
    problems = json.loads((D.parent/'cf_problemset.json').read_text())
    tags = sorted({t for p in problems for t in p.get('tags', []) if not t.startswith('*')})
    tag_id = {t:i for i,t in enumerate(tags)}
    lookup = {(p['contestId'], p['index']): [tag_id[t] for t in p.get('tags',[]) if t in tag_id]
              for p in problems}
    history = np.zeros((count, 8), dtype='f')
    events = np.zeros(count, int)
    first, last = np.zeros(count), np.zeros(count)
    peak = np.zeros(count, dtype='f')
    by_format = np.zeros((count,4,2), dtype='f')
    board = np.zeros((count,5), dtype='f')
    topic = np.zeros((count,len(tags),2), dtype='f')
    CROSS.mkdir(parents=True, exist_ok=True)
    pending = []
    for c in catalog:
        start, cid = c['startTimeSeconds'], c['id']
        while pending and pending[0][0] < start:
            end, _, kind, ids, perf, change, new, extra = heappop(pending)
            first[ids] = np.where(events[ids]==0, end, first[ids])
            gap = np.maximum(0, (end-last[ids])/86400)
            eligible = events[ids]>=6
            eid = ids[eligible]
            v = perf[eligible]
            # Each historical accumulator has its matching effective sample weight.
            history[eid,0] = .65*history[eid,0] + v
            history[eid,1] = .65*history[eid,1] + 1
            history[eid,2] = .94*history[eid,2] + v
            history[eid,3] = .94*history[eid,3] + v*v
            history[eid,4] = .94*history[eid,4] + 1
            history[eid,5] = .94*history[eid,5] + abs(change[eligible])
            history[eid,6] = .80*history[eid,6] + np.log1p(gap[eligible])
            history[eid,7] = .80*history[eid,7] + 1
            by_format[eid,kind,0] = .9*by_format[eid,kind,0] + v
            by_format[eid,kind,1] = .9*by_format[eid,kind,1] + 1
            peak[ids] = np.maximum(peak[ids],new)
            last[ids] = end
            events[ids] += 1
            if extra is not None:
                sid, summary, err, info, tag_map = extra
                board[sid] = .90*board[sid]+summary
                topic[sid] *= .96
                for j, group in enumerate(tag_map):
                    for t in group:
                        topic[sid,t,0] += err[:,j]
                        topic[sid,t,1] += info[:,j]
        path = RC/f'{cid}.json.gz'
        if not path.exists():
            continue
        rows = read(path)['rows']
        if not rows:
            continue
        names, ranks, old, new = zip(*rows)
        old, new = np.array(old), np.array(new)
        perf = rank_performance(old, np.array(ranks))
        ids = np.fromiter((handles.get(h,-1) for h in names), dtype=int)
        known = ids>=0
        extra = None
        path = ST/f'{cid}.json.gz'
        if path.exists():
            d = read(path)
            rated = np.array([r is not None for _,r in d['problems']], dtype=bool)
            rc_index = {h:i for i,h in enumerate(names)}
            players = [(h, rc_index[h], t) for h, _, t in d['rows'] if h in rc_index and h in handles]
            if players and rated.any():
                hn, ix, times = zip(*players)
                ix = np.array(ix)
                sid = ids[ix]
                values = np.array(times)[:,rated]
                solve = values>=0
                tag_map = [lookup.get((cid,label),[]) for label,r in d['problems'] if r is not None]
                bands = np.clip(old[ix]//150,0,30)
                counts = np.bincount(bands,minlength=31)
                kernel = np.exp(-.5*((np.arange(31)[:,None]-np.arange(31))/.9)**2)
                sums = np.zeros((31, solve.shape[1]))
                np.add.at(sums,bands,solve)
                p = ((1+kernel@sums)/(2+(kernel@counts)[:,None]))[bands]
                err, info = solve-p, p*(1-p)
                speed = np.where(solve,1-np.maximum(values,0)/c['durationSeconds'],0)
                summary = np.column_stack([speed.sum(axis=1)/np.maximum(1,solve.sum(axis=1)),
                                           ((~solve)*p**3).sum(axis=1),
                                           (solve*(1-p)**3).sum(axis=1),
                                           np.maximum(0,values.max(axis=1))/c['durationSeconds'],
                                           np.ones(len(sid))])
                if cid in targets:
                    vet = events[sid]>=VET
                    s = sid[vet]
                    h = history[s]
                    slow = h[:,2]/(2+h[:,4])
                    b = board[s]
                    k = fmt(c['name'])
                    f = np.column_stack([np.log1p(events[s]), np.log1p((start-first[s])/86400),
                                         np.log1p((start-last[s])/86400), peak[s]-old[ix[vet]],
                                         h[:,0]/(1+h[:,1]), slow,
                                         np.sqrt(np.maximum(0,h[:,3]/(2+h[:,4])-slow**2)),
                                         h[:,5]/(2+h[:,4]), h[:,6]/(1+h[:,7]),
                                         b[:,:4]/(1+b[:,4,None]), np.log1p(b[:,4]),
                                         by_format[s,k,0]/(2+by_format[s,k,1])])
                    item = np.zeros((len(s),len(tag_map),2),dtype='f')
                    for j, group in enumerate(tag_map):
                        if group:
                            sums = topic[s[:,None],group].sum(axis=1)
                            item[:,j,0] = sums[:,0]/(2+sums[:,1])
                            item[:,j,1] = np.log1p(sums[:,1])
                    digest = np.array([hashlib.sha256(hn[j].encode()).digest()[0]
                                       for j in np.flatnonzero(vet)], dtype='B')
                    tmp = CROSS/f'{cid}.tmp.npz'
                    np.savez(tmp, player=f.astype('f'), item=item, digest=digest, pid=s,
                             old=old[ix[vet]], solved=solve[vet])
                    tmp.replace(CROSS/f'{cid}.npz')
                extra = sid,summary,err,info,tag_map
        heappush(pending,(start+c['durationSeconds'],cid,fmt(c['name']),ids[known],
                          perf[known],(new-old)[known],new[known],extra))
    print('extracted',len(list(CROSS.glob('*.npz'))),'rounds;',count,'handles in target boards')


if __name__ == '__main__':
    extract()
