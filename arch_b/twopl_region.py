"""Prototype probe: does per-problem discrimination (2PL) vary by region, and is
it worth modelling?

Motivated by the observation that in some regions (the large Asia East Continent
online qualifiers) the solve rate almost determines difficulty, while others
(Asia Pacific / Japan) show much more spread. That is the signature of *problem
discrimination* a_p (eq. twopl) -- the one thing the shipped Rasch model cannot
represent (it fixes every slope at 1/s). This script:

  1. fits the UCup-anchored 2PL (twopl.fit_full) and reports alpha by region;
  2. compares its difficulties to the shipped Rasch fit (problem_ratings_b.json);
  3. runs the held-out solve-prediction head-to-head (Rasch vs 2PL) to say whether
     the extra parameter actually generalizes.

    python -m arch_b.twopl_region
"""

import json
import os

import numpy as np

from arch_a import elo
from arch_a.load import load
from . import model, twopl
from .anchor import estimate_anchored
from .predict_eval import _metrics

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
TAGGED = os.path.join(DATA, "tagged.json")
OUT_RASCH = os.path.join(os.path.dirname(__file__), os.pardir, "output", "problem_ratings_b.json")
MIN_SOLVE_HOURS = 3.5
REGIONS = ["Asia East Continent", "Asia Pacific", "Europe", "North America",
           "Northern Eurasia", "Asia West Continent", "Latin America"]


def _logit(x):
    x = np.clip(x, 0.01, 0.99)
    return np.log(x / (1 - x))


def main():
    region_of_cid = {c["contest_id"]: c["region"] for c in json.load(open(TAGGED))}

    # --- anchored 2PL fit (capture alpha through the drop-in fit_fn) ---
    cap = {}

    def fit_fn(ds, **kw):
        th, b, alpha, hist = twopl.fit_full(ds, **kw)
        cap.update(ds=ds, theta=th, b=b, alpha=alpha)   # last call == tagged fit
        return th, b, hist

    estimate_anchored(fit_fn=fit_fn, min_solve_hours=MIN_SOLVE_HOURS, verbose=False)
    ds, theta, b, alpha = cap["ds"], cap["theta"], cap["b"], cap["alpha"]

    reg = np.array([region_of_cid.get(ds.contests[ci], "?") for ci in ds.contest_of_problem])
    field = ds.solve_mask.sum(axis=0)
    solved = (ds.y & ds.solve_mask).sum(axis=0)
    rate = np.divide(solved, field, out=np.full(len(field), np.nan, float), where=field > 0)

    print(f"alpha: [{alpha.min():.2f}, {alpha.max():.2f}] median {np.median(alpha):.2f} "
          f"(Rasch == 1.0)\n")
    print("=== discrimination (alpha) and solve-rate->difficulty tightness by region ===")
    print(f"{'region':<22}{'nprob':>6}{'med_alpha':>10}{'alpha_IQR':>18}"
          f"{'resid_sd(b~rate)':>18}{'med_field':>10}")
    for r in REGIONS:
        m = (reg == r) & (field > 0)
        if m.sum() < 5:
            continue
        a = alpha[m]
        q1, q3 = np.percentile(a, [25, 75])
        X = _logit(rate[m]); Y = b[m]
        slope, inter = np.polyfit(X, Y, 1)
        resid_sd = (Y - (inter + slope * X)).std()
        print(f"{r:<22}{m.sum():>6}{np.median(a):>10.2f}"
              f"{f'[{q1:.2f}, {q3:.2f}]':>18}{resid_sd:>18.0f}{np.median(field[m]):>10.0f}")

    # correlation: does sharper discrimination go with a tighter region?
    print("\n(If observation #1 is real, regions with higher median alpha should have"
          "\n smaller resid_sd -- discrimination IS the tightness.)")

    # --- 2PL vs shipped Rasch difficulties (same anchored problem set) ---
    rasch = {(r["contest_id"], r["problem_label"]): r["difficulty"]
             for r in json.load(open(OUT_RASCH))}
    key = [(ds.contests[ci], ds.problems[i][1]) for i, ci in enumerate(ds.contest_of_problem)]
    rb = np.array([rasch.get(k, np.nan) for k in key])
    ok = ~np.isnan(rb)
    corr = np.corrcoef(b[ok], rb[ok])[0, 1]
    moved = np.abs(b[ok] - rb[ok])
    print(f"\n=== 2PL vs shipped Rasch difficulty (n={ok.sum()}) ===")
    print(f"Pearson corr {corr:.3f}; |db| median {np.median(moved):.0f}, "
          f"90th pct {np.percentile(moved, 90):.0f}, "
          f"#moved>100: {(moved > 100).sum()}")

    # --- held-out solve prediction: Rasch vs 2PL (unanchored, identical cells) ---
    print("\n=== held-out solve prediction (80/20, full tagged, unanchored) ===")
    dsf = load(TAGGED)
    ot, op, oy = model._observations(dsf)
    rng = np.random.default_rng(0)
    test = rng.random(len(oy)) < 0.2
    tr = (ot[~test], op[~test], oy[~test])
    yte, tte, pte = oy[test], ot[test], op[test]

    th_r, b_r, _ = model.fit(dsf, obs=tr, verbose=False)
    th_2, b_2, a_2, _ = twopl.fit_full(dsf, obs=tr, verbose=False)
    p_r = elo.pi(th_r[tte], b_r[pte])
    eta = a_2[pte] * (th_2[tte] - b_2[pte]) / elo.S
    p_2 = twopl._sigmoid(eta)

    print(f"{'model':<10}{'log-loss':>10}{'Brier':>9}{'AUC':>9}")
    for name, p in [("Rasch", p_r), ("2PL", p_2)]:
        ll, br, auc = _metrics(yte, p)
        print(f"{name:<10}{ll:>10.4f}{br:>9.4f}{auc:>9.4f}")


if __name__ == "__main__":
    main()
