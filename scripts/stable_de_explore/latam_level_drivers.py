import json, numpy as np, copy
from types import SimpleNamespace
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors]); cf = np.array([a["cf"] for a in anchors])
ci = {c: i for i, c in enumerate(ds.contests)}
latam = dict(A=3100, B=2200, C=1900, D=1100, E=2700, F=1500, G=2500, H=2300, I=1300, J=2400, K=2500, L=2300, M=1750)
lp = np.array([pi[(2574, l)] for l in latam]); lh = np.array(list(latam.values()), float)
mid_atl = np.flatnonzero(ds.contest_of_problem == ci[3504])
def report(name, d, **kw):
    res = hb.fit(d, **kw); s, i = np.polyfit(res["b"][idx], cf, 1); r = s * res["b"] + i
    c = ci[2574]
    print("%-44s map %.3f %+.0f | LATAM mu %5.0f nu %5.0f | LATAM-13 bias %+5.0f | I %4.0f F %4.0f M %4.0f | Mid-Atl 2024 mean %4.0f | LAC25 mu %.0f LAC26 mu %.0f" % (
        name, s, i, res["mu"][c], res["nu"][c], (r[lp] - lh).mean(), r[pi[(2574, "I")]], r[pi[(2574, "F")]], r[pi[(2574, "M")]], r[mid_atl].mean(), res["mu"][ci[2080]], res["mu"][ci[3762]]))
    return res
report("base", ds)
report("free hyperpriors (tau, tau_b = 4000)", ds, tau=4000, tau_b=4000)
report("tau 800, tau_b 4000 (set mean free)", ds, tau_b=4000)
report("tau 4000, tau_b 400 (board mean free)", ds, tau=4000)
def unlink(rows_mask):
    """give the selected rows fresh team ids"""
    d = SimpleNamespace(**vars(ds)); t = ds.team_of_row.copy()
    r = np.flatnonzero(rows_mask); t[r] = len(ds.teams) + np.arange(len(r))
    d.team_of_row = t; d.teams = list(ds.teams) + [f"x{k}" for k in range(len(r))]
    return d
c = ci[2574]; on = ds.contest_of_row == c
report("LATAM unofficial rows unlinked", unlink(on & ~ds.official_of_row))
report("LATAM official rows unlinked", unlink(on & ds.official_of_row))
report("LATAM all rows unlinked (prior only)", unlink(on))
