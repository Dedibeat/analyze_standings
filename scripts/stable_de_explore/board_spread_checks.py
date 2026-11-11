import json, pickle, numpy as np
from arch_b import hier_binary as hb
from scripts.problem_rating_audit import HAND, FRESH, hand_scores
hb._init(); ds = hb._G["ds"]
res = pickle.load(open("hier_binary_run/explore/board_spread.pkl", "rb"))
anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors]); cf = np.array([a["cf"] for a in anchors]); con = np.array([a["cf_contest"] for a in anchors])
ratings = {}
for n in ("base", "eb_rms300", "eb_raw"):
    b = res[(None, n)]["b"]; s, i = np.polyfit(b[idx], cf, 1); ratings[n] = s*b+i
    pred = np.zeros(len(cf))
    for c in np.unique(con):
        te = con == c; w = np.polyfit(b[idx][~te], cf[~te], 1); pred[te] = np.polyval(w, b[idx][te])
    print("%-10s map %.3f %+.0f | anchor rmse in-sample %.1f, LOCO (not task-purged) %.1f | 1041 A %.0f I %.0f (hand 1200/1350) | 955 M %.0f" % (
        n, s, i, np.sqrt(np.mean((ratings[n][idx]-cf)**2)), np.sqrt(np.mean((pred-cf)**2)), ratings[n][pi[(1041,"A")]], ratings[n][pi[(1041,"I")]], ratings[n][pi[(955,"M")]]))
for nm, panel in (("old", HAND), ("fresh", FRESH)):
    sc = hand_scores(pi, ratings, panel)
    for g, v in sc.items(): print("  ", nm, "%-13s" % g, {k: (x["bias"], x["rmse"]) for k, x in v.items() if k != "n"})
