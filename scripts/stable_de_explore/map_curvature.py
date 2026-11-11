"""Is the affine CF map miscalibrated conditional on the prediction? LOCO with curved maps."""
import gzip, json, numpy as np
R = ""
anchors = json.load(open(R + "data/de_stability_anchors.json", encoding="utf-8"))
views = json.loads(gzip.decompress(open(R + "hier_binary_run/views_hb_s300_t800_sb600_tb400_hb_s400_t0_sb400_tb200.json.gz", "rb").read()))
hbj = json.load(open(R + "output/hier_binary.json", encoding="utf-8"))
full = hbj["field_stability"]["predictions"]["full"]
cf = np.array([a["cf"] for a in anchors]); con = np.array([a["cf_contest"] for a in anchors])
b = np.array(views["full"]["fits"]["hb"]["b"])
rid = {a["row_id"]: k for k, a in enumerate(anchors)}
hb_loco = np.zeros(len(cf)); de_loco = np.zeros(len(cf))
for r in full: hb_loco[rid[r["row_id"]]] = r["hb"]; de_loco[rid[r["row_id"]]] = r["DE"]
for name, pred in (("hb", hb_loco), ("DE", de_loco)):
    print(name, "residual (pred - CF) by predicted band:")
    for lo, hi in [(600,1400),(1400,1800),(1800,2200),(2200,2600),(2600,3000),(3000,3400),(3400,4100)]:
        m = (pred>=lo)&(pred<hi)
        if m.any(): print("   pred %d-%d n=%2d mean %+5.0f" % (lo,hi,m.sum(),(pred-cf)[m].mean()))
def loco(F):
    pred = np.zeros(len(cf))
    for c in np.unique(con):
        te = con == c
        w, *_ = np.linalg.lstsq(F[~te], cf[~te], rcond=None); pred[te] = F[te] @ w
    return np.sqrt(np.mean((pred-cf)**2))
z = (b - b.mean()) / b.std()
one = np.ones(len(b))
print("LOCO (by contest, not task-purged): affine %.1f | +quadratic %.1f | +cubic %.1f | +quad+cubic %.1f | hinge at median %.1f" % (
    loco(np.c_[one, z]), loco(np.c_[one, z, z**2]), loco(np.c_[one, z, z**3]), loco(np.c_[one, z, z**2, z**3]), loco(np.c_[one, z, np.maximum(z, 0)])))
