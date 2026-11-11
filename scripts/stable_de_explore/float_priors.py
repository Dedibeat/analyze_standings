from lab import *
import sys
cfgs = {"base": dict(), "tau_b4000": dict(tau_b=4000), "tau4000": dict(tau=4000), "tau200_tb4000": dict(tau=200, tau_b=4000),
        "sigma_b1200": dict(sigma_b=1200), "sigma600": dict(sigma=600), "sigma_b300": dict(sigma_b=300)}
for name, kw in cfgs.items():
    full, _ = fitv("full", **kw)
    for v in ("quarter_reserved", "eighth_reserved"):
        cut, _ = fitv(v, **kw)
        drift_report(full, cut, name + " " + v)
