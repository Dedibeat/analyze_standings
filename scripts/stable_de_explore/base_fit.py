import time, json, pickle, os, numpy as np
os.makedirs("hier_binary_run/explore", exist_ok=True)
from pathlib import Path
t0=time.time()
from arch_b import hier_binary as hb
hb._init()
ds = hb._G["ds"]
print("load", round(time.time()-t0,1))
print([k for k in vars(ds).keys()])
t0=time.time()
res = hb.fit(ds)
print("fit", round(time.time()-t0,1), res["newton"], res["cg"], "nu0", res["nu0"])
mu, nu = res["mu"], res["nu"]
n_c = len(ds.contests)
# linkers per board: rows whose team appears on >1 board
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
rows_c = np.bincount(ds.contest_of_row, minlength=n_c)
link_c = np.bincount(ds.contest_of_row, (nb[ds.team_of_row]>1).astype(float), n_c)
print("mu: mean %.0f sd %.0f ; nu: mean %.0f sd %.0f ; corr %.3f" % (mu.mean(), mu.std(), nu.mean(), nu.std(), np.corrcoef(mu,nu)[0,1]))
w = link_c>=30
print("well-linked boards", w.sum(), "corr", np.corrcoef(mu[w],nu[w])[0,1].round(3), "slope nu on mu", np.polyfit(mu[w],nu[w],1).round(3), "sd(mu-nu)", (mu-nu)[w].std().round(0), "mean(mu-nu)", (mu-nu)[w].mean().round(0))
anchors = json.loads(Path("data/de_stability_anchors.json").read_text(encoding="utf-8"))
ci = {c:i for i,c in enumerate(ds.contests)}
for c in sorted({a["contest_id"] for a in anchors}):
    i = ci[c]; print(c, "rows", rows_c[i], "linkers", int(link_c[i]), "mu %.0f nu %.0f" % (mu[i], nu[i]))
# least linked boards
order = np.argsort(link_c)
from arch_b.context_fit import raw_by_contest
raw = raw_by_contest()
for i in order[:25]:
    c = ds.contests[i]; print(c, (raw.get(c,{}).get("contest_name") or "")[:50], "rows", rows_c[i], "linkers", int(link_c[i]), "mu %.0f nu %.0f" % (mu[i], nu[i]))
pickle.dump({"mu":mu,"nu":nu,"theta":res["theta"],"b":res["b"],"nu0":res["nu0"]}, open("hier_binary_run/explore/base_fit.pkl","wb"))
