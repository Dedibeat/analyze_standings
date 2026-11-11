import json, numpy as np
from pathlib import Path
from arch_b import hier_binary as hb, de_stability_data as dsd
dsd.initialize()
ds, anchors, boards, ctx = dsd._STATE
team, prob, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
aidx = np.array([pi[(r["contest_id"], r["problem_label"])] for r in anchors])
acf = np.array([r["cf"] for r in anchors])
asr = np.array([a["solve_rate"] for a in anchors])
boards = np.array(boards)
def view_cells(view):
    rows = dsd.sample_rows(ds, ctx, boards, view)
    active = ~np.isin(ds.contest_of_row, boards); active[rows] = True
    return active, active[ds.obs_row]
def fitv(view, fit=hb.fit, **kw):
    active, cells = view_cells(view)
    return fit(ds, obs=(team[cells], prob[cells], y[cells]), rows=active, **kw), active
BINS = [(0,.02),(.02,.1),(.1,.3),(.3,.7),(.7,.95),(.95,1.01)]
def drift_report(full, cut, label=""):
    d = cut["b"][aidx] - full["b"][aidx]
    s = " ".join("%+5.0f" % d[(asr>=lo)&(asr<hi)].mean() for lo,hi in BINS)
    print("%-34s mean %+6.1f rms %6.1f | by solve rate: %s | dmu %+5.0f dnu %+5.0f" % (
        label, d.mean(), np.sqrt((d**2).mean()), s, (cut["mu"]-full["mu"])[boards].mean(), (cut["nu"]-full["nu"])[boards].mean()))

def cut_rows(seed, frac):
    kept = []
    for c in boards:
        rows = np.flatnonzero(ds.contest_of_row == c)
        t = ds.team_of_row[rows]
        teams = np.random.default_rng([seed, int(ds.contests[c])]).permutation(np.unique(t))
        kept.extend(rows[np.isin(t, teams[:max(1, int(len(teams) * frac))])].tolist())
    rows = np.array(kept, int)
    active = ~np.isin(ds.contest_of_row, boards); active[rows] = True
    return active, active[ds.obs_row]
def info_cells(cells):
    """cells of problems that have both a solve and a failure among `cells`"""
    s = np.bincount(prob[cells], y[cells], len(ds.problems)); n = np.bincount(prob[cells], None, len(ds.problems))
    return cells & ((s > 0) & (s < n))[prob]
