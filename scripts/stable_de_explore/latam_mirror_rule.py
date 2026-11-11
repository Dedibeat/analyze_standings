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
ntried = np.bincount(row[tried], minlength=len(ds.team_of_row))
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
ci = {c: i for i, c in enumerate(ds.contests)}
c = ci[2574]; rows = np.flatnonzero(ds.contest_of_row == c)
print("LATAM 2023 rows: official %d, unofficial %d; unofficial with <=2 tried: %d (linked: %d)" % (ds.official_of_row[rows].sum(), (~ds.official_of_row[rows]).sum(), ((~ds.official_of_row[rows]) & (ntried[rows] <= 2)).sum(), ((~ds.official_of_row[rows]) & (ntried[rows] <= 2) & (nb[ds.team_of_row[rows]] > 1)).sum()))
for r in rows[nb[ds.team_of_row[rows]] > 1]:
    print("   rank %3d official=%d tried=%d key=%s" % (ds.rank_of_row[r], ds.official_of_row[r], ntried[r], str(ds.teams[ds.team_of_row[r]])[:40]))
has_flag = np.zeros(len(ds.contests), bool); has_flag[np.unique(ds.contest_of_row[ds.official_of_row])] = True
print("boards with an official flag:", has_flag.sum(), "of", len(ds.contests))
dab = (~ds.official_of_row) & (ntried <= 2)
print("unofficial rows with <=2 tried problems: %d of %d rows; on flagged boards %d; linked %d" % (dab.sum(), len(dab), (dab & has_flag[ds.contest_of_row]).sum(), (dab & (nb[ds.team_of_row] > 1)).sum()))
rules = {"base": np.zeros(len(y), bool), "skip_partial": sc.skipped(ds, every, "skip_partial")}
rules["mirror_attempted"] = rules["skip_partial"] | (dab[row] & ~tried)
rules["mirror_attempted_flagged"] = rules["skip_partial"] | ((dab & has_flag[ds.contest_of_row])[row] & ~tried)
latam = dict(A=3100, B=2200, C=1900, D=1100, E=2700, F=1500, G=2500, H=2300, I=1300, J=2400, K=2500, L=2300, M=1750)
ratings = {}; fits = {}
for name, skip in rules.items():
    res = sc._fit(ds, ~skip); s, i = np.polyfit(res["b"][idx], cf, 1); ratings[name] = s * res["b"] + i; fits[name] = res
    e = np.array([ratings[name][pi[(2574, l)]] - h for l, h in latam.items()])
    print("%-26s cells missing %6d | map %.3f %+.0f | anchor rmse %.1f | LATAM-13 bias %+5.0f rmse %4.0f" % (name, skip.sum(), s, i, np.sqrt(np.mean((ratings[name][idx]-cf)**2)), e.mean(), np.sqrt((e**2).mean())))
for nm, panel in (("old", HAND), ("fresh", FRESH)):
    scs = hand_scores(pi, ratings, panel)
    for g, v in scs.items(): print("  ", nm, "%-13s" % g, {k: (round(x["bias"]), round(x["rmse"])) for k, x in v.items() if k != "n"})
# board-level mean shift vs skip_partial
d = ratings["mirror_attempted"] - ratings["skip_partial"]
sh = [(d[ds.contest_of_problem == k].mean(), ds.contests[k], int((ds.contest_of_row == k).sum())) for k in range(len(ds.contests)) if (ds.contest_of_problem == k).any()]
sh.sort()
print("boards moved most by mirror_attempted vs skip_partial:")
for v, cid, n in sh[:14] + sh[-4:]: print("   %+5.0f %5s %-40s rows %d" % (v, cid, (raw.get(cid, {}).get("contest_name") or "")[:40], n))
pickle.dump({k: v for k, v in ratings.items()}, open("hier_binary_run/explore/ratings_mirror.pkl", "wb"))
