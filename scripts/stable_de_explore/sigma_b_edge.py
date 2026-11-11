"""sigma_b beyond the grid edge: stage-1 log loss (split 0) and stage-2 relative drift (training views)."""
import gzip, json, numpy as np
from concurrent.futures import ProcessPoolExecutor
from arch_b import hier_binary as hb
from arch_b.de_stability_data import TRAIN
CFGS = [(300, 800, sb, 400) for sb in (600, 800, 1000, 1200, 1600)]
if __name__ == "__main__":
    with ProcessPoolExecutor(5, initializer=hb._init) as ex:
        ll = {hb.config_name(c): hb.summarize(sc) for (_, c), sc in ex.map(hb._team_job, [(0, c) for c in CFGS])}
    with ProcessPoolExecutor(10, initializer=hb._view_init) as ex:
        dr = {(v, hb.config_name(c)): np.array(b) for (v, c), b in ex.map(hb._drift_job, [(v, c) for c in CFGS for v in TRAIN])}
    for c in CFGS:
        n = hb.config_name(c); full = dr[("full", n)]
        rel = [np.sqrt(np.mean((dr[(v, n)] - full) ** 2)) / full.std() for v in TRAIN if v != "full"]
        s = ll[n]
        print(n, "logloss %.5f linked %.5f pairacc %.4f | rel drift %.4f | full sd %.0f" % (s["log_loss"], s["linked_log_loss"], s["linked_pair_accuracy"], np.mean(rel), full.std()))
