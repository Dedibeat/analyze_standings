import gzip, json, numpy as np
from pathlib import Path
R = Path("hier_binary_run")
v = json.loads(gzip.decompress((R/"views_hb_s300_t800_sb600_tb400_hb_s400_t0_sb400_tb200.json.gz").read_bytes()))
anchors = json.loads(Path("data/de_stability_anchors.json").read_text(encoding="utf-8"))
print(anchors[0].keys())
full = np.array(v["full"]["fits"]["hb"]["b"])
sr = np.array([a["solve_rate"] for a in anchors])
cid = np.array([a["contest_id"] for a in anchors])
for name in ["half_reserved","quarter_reserved","eighth_reserved","quarter0","quarter1","event_small","mirror_balanced"]:
    rec = v[name]
    b = np.array(rec["fits"]["hb"]["b"]); has = np.array(rec["has_field"])
    d = (b-full)[has]
    print(name, "n", has.sum(), "mean", d.mean().round(1), "rms", np.sqrt((d**2).mean()).round(1))
    for lo,hi in [(0,.02),(.02,.1),(.1,.3),(.3,.7),(.7,.95),(.95,1.01)]:
        m = has & (sr>=lo)&(sr<hi)
        print("   sr %.2f-%.2f n=%d mean %.1f" % (lo,hi,m.sum(), (b-full)[m].mean() if m.any() else 0))
    bb = (b - np.array(v[name]["fits"]["binary"]["b"]))
    print("   flat-binary mean drift", (np.array(rec["fits"]["binary"]["b"])-np.array(v["full"]["fits"]["binary"]["b"]))[has].mean().round(1))
# per board at quarter
rec = v["quarter_reserved"]; b=np.array(rec["fits"]["hb"]["b"])
for c in sorted(set(cid)):
    m = cid==c
    print(c, anchors[int(np.flatnonzero(m)[0])].get("region"), m.sum(), (b-full)[m].mean().round(1))
