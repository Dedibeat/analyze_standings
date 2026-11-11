"""Parametric bootstrap on the real design: is the estimator biased on weak / weakly linked boards?"""
import json, pickle, sys, numpy as np
from types import SimpleNamespace
from concurrent.futures import ProcessPoolExecutor
from arch_b import hier_binary as hb
S = hb.S
def job(a):
    name, widen, seed = a
    ds = hb._G["ds"]
    f = pickle.load(open("hier_binary_run/explore/base_fit.pkl", "rb")); th, b, mu = f["theta"], f["b"], f["mu"]
    n_rows = np.bincount(ds.team_of_row, minlength=len(ds.teams)).astype(float)
    m = np.bincount(ds.team_of_row, mu[ds.contest_of_row] / n_rows[ds.team_of_row], len(ds.teams))
    th_true = m + widen * (th - m)                      # widen the within-board spread around the prior mean
    rng = np.random.default_rng(seed)
    team, prob = ds.team_of_row[ds.obs_row], ds.obs_prob
    y = rng.random(len(prob)) < 1 / (1 + np.exp(-(th_true[team] - b[prob]) / S))
    solved_row = np.bincount(ds.obs_row[y], minlength=len(ds.team_of_row))
    keep_row = solved_row > 0                           # zero-solve rows are dropped, as in the loader
    cells = keep_row[ds.obs_row]
    res = hb.fit(ds, obs=(team[cells], prob[cells], y[cells].astype(float)), rows=keep_row)
    return a, {"b": res["b"], "theta": res["theta"], "th_true": th_true, "kept": keep_row, "solved": np.bincount(prob[cells], y[cells], len(b)), "field": np.bincount(prob[cells], None, len(b))}
if __name__ == "__main__":
    todo = [(n, w, s) for n, w in (("well-specified", 1.0), ("spread x1.4", 1.4), ("spread x1.8", 1.8)) for s in (1, 2, 3)]
    with ProcessPoolExecutor(9, initializer=hb._init) as ex:
        out = dict(ex.map(job, todo))
    pickle.dump(out, open("hier_binary_run/explore/weak_board_simulation.pkl", "wb"))
    hb._init(); ds = hb._G["ds"]
    f = pickle.load(open("hier_binary_run/explore/base_fit.pkl", "rb")); b0, mu = f["b"], f["mu"]
    anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
    pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors])
    ci = {c: i for i, c in enumerate(ds.contests)}
    nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
    rows_c = np.bincount(ds.contest_of_row, minlength=len(ds.contests))
    link_frac = np.bincount(ds.contest_of_row, (nb[ds.team_of_row] > 1).astype(float), len(ds.contests)) / np.maximum(rows_c, 1)
    cop = ds.contest_of_problem
    for n, w in (("well-specified", 1.0), ("spread x1.4", 1.4), ("spread x1.8", 1.8)):
        D = np.mean([out[(n, w, s)]["b"] - b0 for s in (1, 2, 3)], axis=0)
        sr = np.mean([out[(n, w, s)]["solved"] / np.maximum(out[(n, w, s)]["field"], 1) for s in (1, 2, 3)], axis=0)
        mid = (sr > .05) & (sr < .95)
        dropped = np.mean([1 - out[(n, w, s)]["kept"].mean() for s in (1, 2, 3)])
        # the anchor map absorbs a global shift/scale: report latent bias relative to the anchors' mean bias
        off = D[idx].mean()
        print("%s: zero-solve rows dropped %.1f%% | anchors mean bias %+.0f | by solve rate (all problems, minus anchor offset): %s" % (
            n, 100 * dropped, off, " ".join("%+4.0f" % (D[(sr >= lo) & (sr < hi)].mean() - off) for lo, hi in [(0, .02), (.02, .1), (.1, .3), (.3, .7), (.7, .95), (.95, 1.01)])))
        big = rows_c[cop] >= 30
        for lo, hi, lab in [(0, 1500, "board mu < 1500"), (1500, 1800, "1500-1800"), (1800, 2200, "1800-2200"), (2200, 9999, ">= 2200")]:
            k = mid & big & (mu[cop] >= lo) & (mu[cop] < hi)
            kl = k & (link_frac[cop] < 0.15); kh = k & (link_frac[cop] >= 0.15)
            print("    mid-range problems, %-16s n=%4d bias %+5.0f | weakly linked (<15%% rows) n=%3d %+5.0f | linked n=%4d %+5.0f" % (lab, k.sum(), D[k].mean() - off, kl.sum(), (D[kl].mean() - off) if kl.any() else 0, kh.sum(), (D[kh].mean() - off) if kh.any() else 0))
        for cid in (2574, 3504, 3502, 1844, 2080, 3762):
            k = mid & (cop == ci[cid]); print("    board %5d mid-range bias %+5.0f (n=%d, link frac %.2f)" % (cid, D[k].mean() - off, k.sum(), link_frac[ci[cid]]))
