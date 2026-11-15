import json, pickle, sys, numpy as np
from arch_b import hier_binary as hb
hb._init(); ds = hb._G["ds"]
f = pickle.load(open("hier_binary_run/explore/base_fit.pkl","rb")); th, b = f["theta"], f["b"]
A, B = 0.907, 515
pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
ci = {c: i for i, c in enumerate(ds.contests)}
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
def show(cid, lab, maxrows=14):
    p = pi[(cid, lab)]; c = ci[cid]
    cells = np.flatnonzero(ds.obs_prob == p)
    rows = ds.obs_row[cells]; y = ds.obs_y[cells]; w = ds.obs_wrong[cells]; tau = ds.obs_tau[cells]
    board_rows = np.flatnonzero(ds.contest_of_row == c)
    tot = np.bincount(ds.obs_row[ds.obs_y], minlength=len(ds.team_of_row))
    tried = np.bincount(ds.obs_row[ds.obs_y | (ds.obs_wrong > 0)], minlength=len(ds.team_of_row))
    thr = A * th[ds.team_of_row[rows]] + B
    print(f"--- {cid} {lab} {ds.problems[p][3]!r}: solved {y.sum()}/{len(y)} | hb CF {A*b[p]+B:.0f} | median solve min {np.nanmedian(tau[y])/60:.0f} | board team CF median {np.median(A*th[ds.team_of_row[board_rows]]+B):.0f}, p10 {np.percentile(A*th[ds.team_of_row[board_rows]]+B,10):.0f}")
    fail = ~y
    print(f"    failures {fail.sum()}: no submission {int((fail & (w==0)).sum())}, with wrong tries {int((fail & (w>0)).sum())}; official {int(ds.official_of_row[rows[fail]].sum())}; one-board teams {int((nb[ds.team_of_row[rows[fail]]]==1).sum())}")
    print(f"    failing rows: team CF median {np.median(thr[fail]):.0f} (min {thr[fail].min():.0f}, max {thr[fail].max():.0f}); their solves median {np.median(tot[rows[fail]]):.0f}, problems tried median {np.median(tried[rows[fail]]):.0f}")
    order = np.argsort(-thr[fail])[:maxrows]
    for k in order:
        r = rows[fail][k]
        solved_labs = "".join(sorted(ds.problems[q][1] for q in ds.obs_prob[(ds.obs_row == r) & ds.obs_y]))
        print(f"      rank {ds.rank_of_row[r]:4d} off={int(ds.official_of_row[r])} boards={nb[ds.team_of_row[r]]:3d} CF {thr[fail][k]:5.0f} wrong_here={w[fail][k]} solved={solved_labs} key={str(ds.teams[ds.team_of_row[r]])[:40]}")
for a in sys.argv[1:]:
    c, l = a.split(":"); show(int(c), l)
