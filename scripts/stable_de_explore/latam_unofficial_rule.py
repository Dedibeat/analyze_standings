import json, pickle, numpy as np
from arch_b import hier_binary as hb, skip_cells as sc
from arch_b.context_fit import raw_by_contest
from scripts.problem_rating_audit import HAND, FRESH, hand_scores
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors]); cf = np.array([a["cf"] for a in anchors])
every = np.ones(len(ds.obs_y), bool)
row, prob, y = ds.obs_row, ds.obs_prob, ds.obs_y
tried = y | (ds.obs_wrong > 0)
ntried = np.bincount(row[tried], minlength=len(ds.team_of_row)); nsolved = np.bincount(row[y], minlength=len(ds.team_of_row))
nprob = np.bincount(ds.contest_of_problem, minlength=len(ds.contests))[ds.contest_of_row]
last = np.zeros(len(ds.team_of_row)); np.maximum.at(last, row[y & np.isfinite(ds.obs_tau)], ds.obs_tau[y & np.isfinite(ds.obs_tau)].astype(float))
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
ci = {c: i for i, c in enumerate(ds.contests)}
off = ds.official_of_row
for cid in (2574, 3504, 3502, 2151, 1844):
    rows = np.flatnonzero(ds.contest_of_row == ci[cid])
    u = rows[~off[rows]]; o = rows[off[rows]]
    print("%5d %-28s rows %3d official %3d unofficial %3d | unofficial: linked %d, tried==solved %d, median tried %.0f, median last-solve min %.0f | official: median tried %.0f, last-solve min %.0f" % (
        cid, (raw[cid]["contest_name"])[:28], len(rows), len(o), len(u), (nb[ds.team_of_row[u]] > 1).sum(), (ntried[u] == nsolved[u]).sum(), np.median(ntried[u]) if len(u) else 0, np.median(last[u]) / 60 if len(u) else 0, np.median(ntried[o]) if len(o) else 0, np.median(last[o]) / 60 if len(o) else 0))
print("all boards: unofficial rows %d (%.0f%%); of them tried==solved %.0f%%; official rows tried==solved %.0f%%" % ((~off).sum(), 100 * (~off).mean(), 100 * (ntried[~off] == nsolved[~off]).mean(), 100 * (ntried[off] == nsolved[off]).mean()))
print("median last-solve minute: unofficial %.0f, official %.0f" % (np.median(last[~off]) / 60, np.median(last[off]) / 60))
rules = {"skip_partial": sc.skipped(ds, every, "skip_partial")}
rules["unofficial_attempted_only"] = rules["skip_partial"] | ((~off)[row] & ~tried)
latam = dict(A=3100, B=2200, C=1900, D=1100, E=2700, F=1500, G=2500, H=2300, I=1300, J=2400, K=2500, L=2300, M=1750)
ratings = {}
for name, skip in rules.items():
    res = sc._fit(ds, ~skip); s, i = np.polyfit(res["b"][idx], cf, 1); ratings[name] = s * res["b"] + i
    e = np.array([ratings[name][pi[(2574, l)]] - h for l, h in latam.items()])
    print("%-26s cells missing %6d | map %.3f %+.0f | anchor rmse %.1f | LATAM-13 bias %+5.0f rmse %4.0f" % (name, skip.sum(), s, i, np.sqrt(np.mean((ratings[name][idx]-cf)**2)), e.mean(), np.sqrt((e**2).mean())))
for nm, panel in (("old", HAND), ("fresh", FRESH)):
    scs = hand_scores(pi, ratings, panel)
    for g, v in scs.items(): print("  ", nm, "%-13s" % g, {k: (round(x["bias"]), round(x["rmse"])) for k, x in v.items() if k != "n"})
