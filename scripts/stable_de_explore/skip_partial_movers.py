import json, numpy as np
from arch_b import hier_binary as hb, skip_cells as sc
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
R = json.load(open("output/skip_cells_ratings.json", encoding="utf-8"))["problems"]
de = np.array([r["de_cf"] for r in R]); sp = np.array([r["skip_partial_cf"] for r in R]); base = np.array([r["base_cf"] for r in R])
skip = sc.skipped(ds, np.ones(len(ds.obs_y), bool), "skip_partial")
nskip = np.bincount(ds.obs_prob[skip], minlength=len(ds.problems))
tau = ds.obs_tau.astype(float); ok = ds.obs_y & np.isfinite(tau)
med = np.full(len(ds.problems), np.nan)
for p in np.unique(ds.obs_prob[ok]):
    pass
order = np.argsort(ds.obs_prob[ok], kind="stable"); pp = ds.obs_prob[ok][order]; tt = tau[ok][order]
starts = np.r_[0, np.flatnonzero(np.diff(pp)) + 1, len(pp)]
for a, b_ in zip(starts[:-1], starts[1:]): med[pp[a]] = np.median(tt[a:b_]) / 60
# board earliest median (the board's fastest problem) for reference
d = base - sp
idx = np.argsort(-d)
print("problems with base - skip_partial >= 200:", int((d >= 200).sum()), "| >= 100:", int((d >= 100).sum()))
print("%5s %-2s %-26s %-24s %9s %5s %5s %5s %5s %4s" % ("cid", "", "name", "contest", "solved", "skip", "de", "base", "sp", "med"))
for p in idx[:60]:
    if d[p] < 200: break
    c, lab, _, nm = ds.problems[p]
    fails = ds.field_count[p] - ds.solved_count[p]
    print("%5s %-2s %-26s %-24s %4d/%4d %2d/%2d %5.0f %5.0f %5.0f %4.0f" % (c, lab, (nm or "")[:26], (raw.get(c, {}).get("contest_name") or "")[:24], ds.solved_count[p], ds.field_count[p], nskip[p], fails, de[p], base[p], sp[p], med[p]))
