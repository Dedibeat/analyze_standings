import pickle, json, numpy as np
from arch_b import hier_binary as hb
from arch_b.context_fit import raw_by_contest
hb._init(); ds = hb._G["ds"]; raw = raw_by_contest()
f = pickle.load(open("hier_binary_run/explore/base_fit.pkl","rb")); mu, nu, th, b = f["mu"], f["nu"], f["theta"], f["b"]
cnt = np.bincount(ds.contest_of_row, minlength=len(ds.contests))
nb = np.bincount(ds.team_of_row, minlength=len(ds.teams))
link = np.bincount(ds.contest_of_row, (nb[ds.team_of_row]>1).astype(float), len(ds.contests))
hbr = {(p["contest_id"], p["problem_label"]): p for p in json.load(open("output/hier_binary_ratings.json"))["problems"]}
order = np.argsort(-mu)
print("top board means (base fit)")
for i in order[:14]:
    c = ds.contests[i]; pm = ds.contest_of_problem == i
    r = [hbr[(int(c), ds.problems[p][1])] for p in np.flatnonzero(pm)]
    print("%5s %-40s rows %4d linkers %4d mu %5.0f nu %5.0f | theta med %5.0f | hb-de mean %+5.0f | solved/field %s" % (
        c, (raw.get(c,{}).get("contest_name") or "")[:40], cnt[i], link[i], mu[i], nu[i], np.median(th[ds.team_of_row[ds.contest_of_row==i]]),
        np.mean([x["hier_cf"]-x["de_cf"] for x in r]), " ".join(f'{x["solved"]}' for x in r)))
