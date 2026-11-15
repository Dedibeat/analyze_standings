import time, numpy as np, json
from fitsig import *
hb._init(); ds = hb._G["ds"]
base = hb.fit(ds); chk = fit_sig(ds)
print("fit_sig reproduces fit: max |db|", np.abs(base["b"]-chk["b"]).max(), "max |dtheta|", np.abs(base["theta"]-chk["theta"]).max())
t0=time.time(); eb = fit_eb(ds); print("eb", round(time.time()-t0,1))
from arch_b.context_fit import raw_by_contest
raw = raw_by_contest(); s = eb["sig_c"]; cnt = np.bincount(ds.contest_of_row, minlength=len(ds.contests))
print("EB board sd: row-weighted rms %.0f, min %.0f, median %.0f, max %.0f" % (np.sqrt((cnt*s**2).sum()/cnt.sum()), s.min(), np.median(s), s.max()))
order = np.argsort(s)
for i in list(order[:12]) + list(order[-12:]):
    c = ds.contests[i]; print("%5s %-45s rows %4d sd %4.0f mu %4.0f" % (c, (raw.get(c,{}).get("contest_name") or "")[:45], cnt[i], s[i], eb["mu"][i]))
