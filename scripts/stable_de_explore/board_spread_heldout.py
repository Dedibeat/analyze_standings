"""Per-board ability spread (EB): held-out team prediction on splits 0-2, CF anchors, floors, hand panels."""
import json, pickle, sys, numpy as np
from concurrent.futures import ProcessPoolExecutor
from fitsig import *
VARIANTS = {"base": None, "eb_rms300": dict(scale=300.0), "eb_raw": dict(scale=None), "sigma383": "flat383"}
def job(a):
    split, name = a
    ds = hb._G["ds"]
    team, prob, y = ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float)
    if split is None:
        obs = (team, prob, y); held = None
    else:
        held = hb.appearance_split(ds, split); tr = ~held[ds.obs_row]; obs = (team[tr], prob[tr], y[tr])
    v = VARIANTS[name]
    res = hb.fit(ds, obs=obs) if v is None else hb.fit(ds, obs=obs, sigma=383.0) if v == "flat383" else fit_eb(ds, obs=obs, **v)
    if split is None:
        return a, {"theta": res["theta"], "b": res["b"], "mu": res["mu"], "sig_c": res.get("sig_c")}
    return a, hb.team_scores(ds, held, res["theta"], res["b"], "binary")
if __name__ == "__main__":
    todo = [(s, n) for s in (0, 1, 2, None) for n in VARIANTS]
    with ProcessPoolExecutor(12, initializer=hb._init) as ex:
        res = dict(ex.map(job, todo))
    pickle.dump(res, open("hier_binary_run/explore/board_spread.pkl", "wb"))
    for s in (0, 1, 2):
        for n in VARIANTS:
            sm = hb.summarize(res[(s, n)])
            line = "split %d %-10s logloss %.5f linked %.5f cold %.5f count-rmse %.4f pairacc %.4f" % (s, n, sm["log_loss"], sm["linked_log_loss"], sm["cold_log_loss"], sm["solve_count_rmse"], sm["linked_pair_accuracy"])
            if n != "base":
                d = hb.paired_bootstrap(res[(s, n)], res[(s, "base")])
                line += " | vs base: ll %+.5f [%+.5f,%+.5f] pair %+.4f [%+.4f,%+.4f]" % (*d["log_loss"], *d["linked_pair_accuracy"])
            print(line)
