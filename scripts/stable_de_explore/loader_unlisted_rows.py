import json, numpy as np
import arch_a.load as L
from arch_b import hier_binary as hb, model
from arch_b.joint import load_joint_dataset
from arch_b.run import MIN_SOLVE_HOURS
anchors = json.load(open("data/de_stability_anchors.json", encoding="utf-8"))
def run(tag):
    ds, uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    pi = {(c, l): p for p, (c, l, _, _) in enumerate(ds.problems)}
    idx = np.array([pi[(a["contest_id"], a["problem_label"])] for a in anchors]); cf = np.array([a["cf"] for a in anchors])
    res = hb.fit(ds); s, i = np.polyfit(res["b"][idx], cf, 1)
    tb, bb, _ = model.fit(ds, verbose=False); s2, i2 = np.polyfit(bb[idx], cf, 1)
    out = {}
    for k in [(2575,"M"),(1482,"E"),(1482,"J"),(1482,"K"),(1482,"L"),(1115,"B"),(1115,"G"),(1121,"L"),(1481,"A"),(1481,"B"),(1481,"D"),(3294,"A"),(3294,"B"),(3294,"D")]:
        if k in pi:
            p = pi[k]; out[k] = (s*res["b"][p]+i, s2*bb[p]+i2, int(ds.solved_count[p]), int(ds.field_count[p]))
    print(tag, "rows", len(ds.team_of_row), "teams", len(ds.teams), "hb map %.3f %+.0f" % (s, i), "anchor rmse hb %.1f flat %.1f" % (np.sqrt(np.mean((s*res["b"][idx]+i-cf)**2)), np.sqrt(np.mean((s2*bb[idx]+i2-cf)**2))))
    return out, s*res["b"]+i, pi
a, ra, pia = run("guard (current)")
orig = L.row_solved_any
L.row_solved_any = lambda standing, problem_labels=None: orig(standing, None)
b, rb, pib = run("retain rows with unlisted solves")
for k in a:
    print(k, "hb %5.0f -> %5.0f | flat-binary affine %5.0f -> %5.0f | solved/field %d/%d -> %d/%d" % (a[k][0], b[k][0], a[k][1], b[k][1], a[k][2], a[k][3], b[k][2], b[k][3]))
common = [k for k in pia if k in pib]
d = np.array([rb[pib[k]] - ra[pia[k]] for k in common])
big = [(common[j], round(float(d[j]))) for j in np.argsort(-np.abs(d))[:25]]
print("all problems: max |change| %.0f, n>50: %d, n>20: %d" % (np.abs(d).max(), (np.abs(d)>50).sum(), (np.abs(d)>20).sum())); print(big)
