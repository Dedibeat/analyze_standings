import json, pickle, numpy as np
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
f = pickle.load(open("hier_binary_run/explore/base_fit.pkl","rb")); th, b, mu, nu = f["theta"], f["b"], f["mu"], f["nu"]; A, B = 0.907, 515
ci = {c: i for i, c in enumerate(ds.contests)}; c = ci[2574]
rows = np.flatnonzero(ds.contest_of_row == c)
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
tot = np.bincount(ds.obs_row[ds.obs_y], minlength=len(ds.team_of_row))
print("LATAM 2023: rows", len(rows), "mu", mu[c].round(), "nu", nu[c].round(), "team CF: median %.0f p90 %.0f max %.0f" % tuple(np.percentile(A*th[ds.team_of_row[rows]]+B, [50, 90, 100])))
print("solves distribution:", np.bincount(tot[rows]))
S = hb.S
probs = np.flatnonzero(ds.contest_of_problem == c)
for r in rows[nb[ds.team_of_row[rows]] > 1]:
    t = ds.team_of_row[r]
    others = [(ds.contests[ds.contest_of_row[q]], int(ds.rank_of_row[q]), int(tot[q]), int((ds.contest_of_row == ds.contest_of_row[q]).sum())) for q in np.flatnonzero(ds.team_of_row == t) if q != r]
    exp_here = (1/(1+np.exp(-(th[t]-b[probs])/S))).sum()
    print("  rank %3d solved %2d (model expects %.1f) CF %4.0f key=%-38s other boards (cid, rank, solved, rows): %s" % (ds.rank_of_row[r], tot[r], exp_here, A*th[t]+B, str(ds.teams[t])[:38], [(o[0], o[1], o[2], o[3]) for o in others][:6]))
# what do other boards say about these teams? fit without LATAM 2023 cells for linkers -> their theta from elsewhere
team, prob, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
keep = ds.contest_of_row[ds.obs_row] != c
act = ds.contest_of_row != c
res = hb.fit(ds, obs=(team[keep], prob[keep], y[keep]), rows=act)
link_rows = rows[nb[ds.team_of_row[rows]] > 1]
th_out = res["theta"][ds.team_of_row[link_rows]]
print("linkers' CF from all other boards only: ", np.round(A*th_out+B).astype(int))
print("linkers' CF in the joint fit:            ", np.round(A*th[ds.team_of_row[link_rows]]+B).astype(int))
# level implied by linkers alone: find shift d so that sum over linkers of expected solves(th_out, b + d) = actual
act_solves = tot[link_rows].sum()
for d in range(-800, 401, 100):
    e = sum((1/(1+np.exp(-(t0-(b[probs]+d))/S))).sum() for t0 in th_out)
    print("   shift all 2574 difficulties by %+4d -> linkers expected solves %.1f (actual %d)" % (d, e, act_solves))
