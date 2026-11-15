import json, numpy as np, collections
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
R = json.load(open("output/skip_cells_ratings.json", encoding="utf-8"))["problems"]
de = np.array([r["de_cf"] for r in R]); sp = np.array([r["skip_partial_cf"] for r in R]); base = np.array([r["base_cf"] for r in R])
sr = ds.solved_count / np.maximum(ds.field_count, 1)
name = lambda c: (raw.get(c, {}).get("contest_name") or str(c))[:38]
# (a) board-level mean gaps, mid-range only
mid = (sr >= .05) & (sr <= .95) & (ds.field_count >= 30)
print("(a) boards by mean (skip_partial - DE) over mid-range problems, |mean| >= 150")
rows = []
for c in range(len(ds.contests)):
    m = mid & (ds.contest_of_problem == c)
    if m.sum() >= 4: rows.append(((sp-de)[m].mean(), ds.contests[c], m.sum(), int(ds.field_count[m][0])))
for g, c, n, fld in sorted(rows):
    if abs(g) >= 150: print("   %+5.0f %5s %-38s n=%2d rows=%d" % (g, c, name(c), n, fld))
print("(a2) single mid-range problems with |skip_partial - DE| >= 350 (field >= 30)")
for p in np.argsort(-np.abs(sp-de)):
    if mid[p] and abs(sp[p]-de[p]) >= 350:
        c, lab, _, nm = ds.problems[p]; print("   %5s %s %-30s %-28s solved %3d/%3d de %4.0f sp %4.0f" % (c, lab, (nm or "")[:30], name(c)[:28], ds.solved_count[p], ds.field_count[p], de[p], sp[p]))
# (b) rating vs median solve time within a board
print("(b) within-board: rating rank vs median-solve-minute rank, problems with >= 15 solves; |rank shift| >= 5")
med = np.full(len(ds.problems), np.nan)
tau = ds.obs_tau.astype(float); ok = ds.obs_y & np.isfinite(tau)
order = np.argsort(ds.obs_prob[ok], kind="stable"); pp = ds.obs_prob[ok][order]; tt = tau[ok][order]
starts = np.r_[0, np.flatnonzero(np.diff(pp)) + 1, len(pp)]
for a, b_ in zip(starts[:-1], starts[1:]): med[pp[a]] = np.median(tt[a:b_]) / 60
out = []
for c in range(len(ds.contests)):
    ps = np.flatnonzero((ds.contest_of_problem == c) & (ds.solved_count >= 15) & np.isfinite(med))
    if len(ps) < 6: continue
    rr = np.argsort(np.argsort(sp[ps])); rt = np.argsort(np.argsort(med[ps]))
    for k, p in enumerate(ps):
        if abs(rr[k]-rt[k]) >= 5: out.append((rr[k]-rt[k], p, len(ps)))
for sh, p, n in sorted(out, key=lambda x: -abs(x[0]))[:30]:
    c, lab, _, nm = ds.problems[p]; print("   shift %+d of %2d | %5s %s %-28s %-26s solved %3d/%3d median min %3.0f sp %4.0f de %4.0f" % (sh, n, c, lab, (nm or "")[:28], name(c)[:26], ds.solved_count[p], ds.field_count[p], med[p], sp[p], de[p]))
