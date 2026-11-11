import json, pickle, numpy as np, collections
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
rs = np.array([np.nan if v is None else v for v in ds.raw_solved_count], float)
sc = ds.solved_count.astype(float)
print("problems", len(sc), "with reported count", np.isfinite(rs).sum())
ok = np.isfinite(rs)
diff = sc - rs
print("exact match", (diff[ok]==0).sum(), "fit>reported", (diff[ok]>0).sum(), "fit<reported", (diff[ok]<0).sum())
# per contest summary of mismatch
byc = collections.defaultdict(list)
for p in np.flatnonzero(ok):
    byc[ds.problems[p][0]].append((ds.problems[p][1], int(sc[p]), int(rs[p]), int(ds.field_count[p])))
rows = []
for c, v in byc.items():
    a = sum(x[1] for x in v); b = sum(x[2] for x in v)
    worst = max(v, key=lambda x: abs(x[1]-x[2])/max(x[2],x[1],1))
    rows.append((abs(a-b)/max(a,b,1), c, a, b, worst))
rows.sort(reverse=True)
for r in rows[:30]:
    print("%.2f %5s %-42s fit solves %5d reported %5d worst %s" % (r[0], r[1], (raw.get(r[1],{}).get("contest_name") or "")[:42], r[2], r[3], r[4]))
