from lab import *
from concurrent.futures import ProcessPoolExecutor
import sys
def job(a):
    name, kw, seed, frac, drop = a
    if seed is None:
        active = np.ones(len(ds.team_of_row), bool); cells = np.ones(len(y), bool)
    else:
        active, cells = cut_rows(seed, frac)
    if drop: cells = info_cells(cells)
    r = hb.fit(ds, obs=(team[cells], prob[cells], y[cells]), rows=active, **kw)
    return (name, seed), {"b": r["b"][aidx], "mu": r["mu"][boards], "nu": r["nu"][boards], "theta": r["theta"]}
if __name__ == "__main__":
    frac = float(sys.argv[1]); seeds = list(range(100, 108))
    cfgs = {"base": (dict(), False), "base_dropzero": (dict(), True), "sb1e5": (dict(sigma_b=1e5, tau_b=0), False),
            "tau_both4000": (dict(tau=4000, tau_b=4000), False)}
    todo = [(n, kw, s, frac, d) for n, (kw, d) in cfgs.items() for s in [None] + seeds]
    with ProcessPoolExecutor(10) as ex:
        res = dict(ex.map(job, todo))
    for n in cfgs:
        full = res[(n, None)]
        D = np.array([res[(n, s)]["b"] - full["b"] for s in seeds])
        dm = np.array([res[(n, s)]["mu"] - full["mu"] for s in seeds])
        per = D.mean(1)
        print("%-16s frac %.3f mean %+6.1f (se %.1f) rms %6.1f | %s | dmu %+5.0f" % (
            n, frac, per.mean(), per.std(ddof=1)/np.sqrt(len(seeds)), np.sqrt((D**2).mean()),
            " ".join("%+5.0f" % D[:, (asr>=lo)&(asr<hi)].mean() for lo, hi in BINS), dm.mean()))
