"""Exploration: a timing term at the floor on top of the hierarchical difficulty (nested LOCO by CF contest)."""
import gzip, json, numpy as np
R = ""
anchors = json.load(open(R + "data/de_stability_anchors.json", encoding="utf-8"))
views = json.loads(gzip.decompress(open(R + "hier_binary_run/views_hb_s300_t800_sb600_tb400_hb_s400_t0_sb400_tb200.json.gz", "rb").read()))
hbj = json.load(open(R + "output/hier_binary.json", encoding="utf-8"))
de_full = {r["row_id"]: r["DE"] for r in hbj["field_stability"]["predictions"]["full"]}
cf = np.array([a["cf"] for a in anchors]); con = np.array([a["cf_contest"] for a in anchors])
hb_b = np.array(views["full"]["fits"]["hb"]["b"]); surv = np.array([a["raw_b"] for a in anchors])
sr = np.array([a["solve_rate"] for a in anchors]); lt = np.array([a["log_median_solve_seconds"] for a in anchors])
miss = np.array([a["timing_missing"] for a in anchors]).astype(bool)
de = np.array([de_full[a["row_id"]] for a in anchors])
print("timing missing", miss.sum(), "sr>=.9:", (sr>=.9).sum(), "sr>=.95:", (sr>=.95).sum())
def loco(X):
    pred = np.zeros(len(cf))
    for c in np.unique(con):
        te = con == c; tr = ~te
        A = np.c_[np.ones(tr.sum()), X[tr]]; w, *_ = np.linalg.lstsq(A, cf[tr], rcond=None)
        pred[te] = np.c_[np.ones(te.sum()), X[te]] @ w
    return pred
def rep(name, pred):
    e = pred - cf
    fl = sr >= 0.9
    print("%-34s all %6.1f | floor(sr>=.9, n=%d) bias %+5.0f rmse %5.1f | rest rmse %6.1f | CF<=1300 (n=%d) bias %+5.0f rmse %5.1f" % (
        name, np.sqrt((e**2).mean()), fl.sum(), e[fl].mean(), np.sqrt((e[fl]**2).mean()), np.sqrt((e[~fl]**2).mean()), (cf<=1300).sum(), e[cf<=1300].mean(), np.sqrt((e[cf<=1300]**2).mean())))
rep("DE (LOCO, shipped features)", de)
rep("hb affine", loco(hb_b[:, None]))
for thr in (0.8, 0.9, 0.95):
    fl = (sr >= thr).astype(float)
    ltc = np.where(miss, np.nanmean(lt[~miss]), lt)
    rep(f"hb + floor*(logtime) thr {thr}", loco(np.c_[hb_b, fl, fl * (ltc - 7.5)]))
    rep(f"hb + floor*(surv-hb) thr {thr}", loco(np.c_[hb_b, fl, fl * (surv - hb_b)]))
rep("hb + surv (all problems)", loco(np.c_[hb_b, surv]))
rep("hb + logtime (all problems)", loco(np.c_[hb_b, np.where(miss, np.nanmean(lt[~miss]), lt)]))
# smooth weight: information-poor floor weight w = clip((sr-0.8)/0.2,0,1)
w = np.clip((sr - 0.8) / 0.2, 0, 1)
rep("hb + ramp*(surv-hb)", loco(np.c_[hb_b, w, w * (surv - hb_b)]))
rep("hb + ramp*(logtime)", loco(np.c_[hb_b, w, w * (np.where(miss, np.nanmean(lt[~miss]), lt) - 7.5)]))
