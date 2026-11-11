import json, pickle, numpy as np
from arch_b import hier_binary as hb
hb._init(); ds = hb._G["ds"]
f = pickle.load(open("hier_binary_run/explore/base_fit.pkl","rb")); th, b = f["theta"], f["b"]
anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors]); cf = np.array([a["cf"] for a in anchors])
s, i = np.polyfit(b[idx], cf, 1); pred = s*b[idx]+i
# weakest decile of team CF on each board
tcf = s*th+i
p10 = np.array([np.percentile(tcf[ds.team_of_row[ds.contest_of_row == c]], 10) if (ds.contest_of_row==c).any() else np.nan for c in range(len(ds.contests))])
a10 = p10[ds.contest_of_problem[idx]]
sr = ds.solved_count[idx]/ds.field_count[idx]
print("anchors: CF vs in-sample hb error by CF band")
for lo, hi in [(800,1200),(1200,1600),(1600,2000),(2000,2400),(2400,2800),(2800,3200),(3200,3600)]:
    m = (cf>=lo)&(cf<hi); print("  CF %d-%d n=%2d mean err %+5.0f rmse %4.0f" % (lo,hi,m.sum(), (pred-cf)[m].mean(), np.sqrt(((pred-cf)[m]**2).mean())))
print("easy anchors (CF<=1500): error vs how far the label sits below the board's weakest decile")
m = cf <= 1500
gap = a10 - cf
for lo, hi in [(-500,300),(300,500),(500,700),(700,1500)]:
    k = m & (gap>=lo) & (gap<hi)
    if k.any(): print("  p10 - CF in [%d,%d): n=%2d mean err %+5.0f" % (lo,hi,k.sum(),(pred-cf)[k].mean()))
for j in np.flatnonzero(m):
    a = anchors[j]; print("   %5d %s CF %4d hb %5.0f err %+5.0f | solved %3d/%3d | board p10 %4.0f" % (a["contest_id"], a["problem_label"], cf[j], pred[j], pred[j]-cf[j], ds.solved_count[idx[j]], ds.field_count[idx[j]], a10[j]))
# how many problems overall sit near/below the board floor
allcf = s*b+i; allp10 = p10[ds.contest_of_problem]
print("all problems rated below board p10 - 300:", int((allcf < allp10 - 300).sum()), "of", len(b), "; below p10 - 500:", int((allcf < allp10-500).sum()))
