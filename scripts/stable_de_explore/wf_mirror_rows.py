import json, pickle, numpy as np
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
f = pickle.load(open("hier_binary_run/explore/base_fit.pkl","rb")); th, b = f["theta"], f["b"]; A, B = 0.907, 515
ci = {c: i for i, c in enumerate(ds.contests)}
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
hbr = {(p["contest_id"], p["problem_label"]): p for p in json.load(open("output/hier_binary_ratings.json"))["problems"]}
for cid in (1966, 1662, 2522, 1661):
    c = ci[cid]; rows = np.flatnonzero(ds.contest_of_row == c)
    rc = raw[cid]
    ids = [str(rc["standings"][ds.participation_of_row[r][1]].get("team_id")) for r in rows]
    kinds = np.array(["ucup" if i.startswith("ucup") else "default" if i.startswith("$DEFAULT") else "other" for i in ids])
    tot = np.bincount(ds.obs_row[ds.obs_y], minlength=len(ds.team_of_row))[rows]
    print(cid, rc["contest_name"], "rows", len(rows), {k: int((kinds==k).sum()) for k in set(kinds)}, "example ids", ids[:2], [i for i in ids if not i.startswith("$DEFAULT")][:4])
    for k in sorted(set(kinds)):
        m = kinds == k
        print("   %-8s n=%3d mean solves %.2f, team CF median %.0f, boards median %d" % (k, m.sum(), tot[m].mean(), np.median(A*th[ds.team_of_row[rows[m]]]+B), np.median(nb[ds.team_of_row[rows[m]]])))
    probs = np.flatnonzero(ds.contest_of_problem == c)
    line = []
    for p in probs:
        cells = ds.obs_prob == p; r = ds.obs_row[cells]; y = ds.obs_y[cells]
        km = {rr: k for rr, k in zip(rows, kinds)}
        kk = np.array([km[x] for x in r])
        d = hbr[(cid, ds.problems[p][1])]
        line.append("%s onsite %d/%d other %d/%d (reported %s) hb %.0f de %.0f" % (ds.problems[p][1], y[kk=="default"].sum(), (kk=="default").sum(), y[kk!="default"].sum(), (kk!="default").sum(), ds.raw_solved_count[p], d["hier_cf"], d["de_cf"]))
    print("   " + "\n   ".join(line))
