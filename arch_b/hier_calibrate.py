"""Hierarchical calibration: a per-contest and per-region level, partially pooled.

The shipped map (``calibrate.py``) is one global affine leg on top of the gym
shape: ``cf ~ A*f(b) + B``, fit by OLS over 185 anchor problems. Two things that
hides, both measured in the 2026-08-21 audit:

* Anchor problems are **clustered**: 185 problems in 15 contests, with a
  per-contest constant offset carrying 17.1% of the residual variance (offsets
  from -161 to +267 CF points). Plain OLS treats them as 185 independent points,
  so contest-level noise leaks into the slope.
* The affine leg is fit on **three regions** (Asia Pacific 93, Northern Eurasia
  50, Europe 42) and extrapolated onto the other five, including the 458-problem
  Asia East Continent and every one of the 896 supplemental problems. A region
  that sits systematically high or low has nowhere to say so.

This module fits ``cf_p = A*f(b_p) + B + u_contest + v_region`` with Gaussian
random effects on ``u`` and ``v``, by alternating a GLS-style affine step with
shrunken group means (the closed-form empirical-Bayes update
``u_c = n_c/(n_c + sigma^2/tau^2) * mean residual``). Variance components come
from a method-of-moments split of the residual. A contest with anchors estimates
its own level; one without shrinks to its region; a region without anchors
shrinks to the global mean -- so the extrapolation becomes an explicit, shrunk
estimate with a standard error rather than an assumed zero.

External per-contest level observations can be supplied with ``offsets=``: a
mapping ``{qoj_contest_id: offset_cf}`` measured by an instrument that has no
absolute scale of its own to drift (``llm_crosscontest.py``). They enter as one
extra pseudo-observation of ``u_c``, weighted by ``offset_weight``.

    python -m arch_b.hier_calibrate          # LOCO: plain affine vs hierarchical
"""

import json
import os
from collections import defaultdict

import numpy as np

from .calibrate import MODELS, _anchors, _gym_shape

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TAGGED = os.path.join(os.path.dirname(__file__), os.pardir, "data", "tagged.json")


def _regions():
    with open(TAGGED) as f:
        return {int(c["contest_id"]): (c.get("region") or "?") for c in json.load(f)}


def _group_stats(values, group, n_groups):
    """Per-group (count, mean) of ``values``."""
    total = np.zeros(n_groups)
    count = np.zeros(n_groups)
    np.add.at(total, group, values)
    np.add.at(count, group, 1.0)
    mean = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
    return count, mean


def _components(resid, contest, n_c, region, region_of_contest, n_r):
    """Method-of-moments (sigma2, tau_contest2, tau_region2).

    ``sigma2`` is the pooled *within-contest* residual variance. The group
    variances are debiased by subtracting the sampling variance of a group mean;
    estimating tau from the *shrunken* means instead collapses it to zero.
    """
    n_ci, m_c = _group_stats(resid, contest, n_c)
    within = resid - m_c[contest]
    live = n_ci > 0
    dof = max(len(resid) - int(live.sum()), 1)
    sigma2 = float(np.sum(within ** 2) / dof)

    m, n, r_of = m_c[live], n_ci[live], region_of_contest[live]
    per_region, m_r = _group_stats(m, r_of, n_r)
    tau_c2 = max(float(np.mean((m - m_r[r_of]) ** 2) - np.mean(sigma2 / n)), 0.0)
    filled = per_region > 0
    if int(filled.sum()) > 1:
        noise = np.mean((tau_c2 + sigma2 / float(n.mean())) / per_region[filled])
        tau_r2 = max(float(np.var(m_r[filled]) - noise), 0.0)
    else:
        tau_r2 = 0.0
    return sigma2, tau_c2, tau_r2


def _shrunk(resid, group, n_groups, sigma2, tau2, extra=None):
    """Empirical-Bayes group means: n_g/(n_g + sigma2/tau2) * mean residual.

    ``extra`` is an optional external observation of the same group effect,
    ``(offset, weight)`` arrays over groups, entering as ``weight``
    pseudo-observations of value ``offset``.
    """
    total = np.zeros(n_groups)
    count = np.zeros(n_groups)
    np.add.at(total, group, resid)
    np.add.at(count, group, 1.0)
    if extra is not None:
        offset, weight = extra
        total = total + weight * offset
        count = count + weight
    if tau2 <= 0:
        return np.zeros(n_groups)
    return total / (count + sigma2 / tau2)


def fit_hier(z, cf, contest, region, offsets=None, iters=50):
    """Fit cf ~ A*z + B + u_contest + v_region; returns the fitted components.

    ``contest`` / ``region`` are integer group codes aligned with ``z``.
    """
    n_c, n_r = int(contest.max()) + 1, int(region.max()) + 1
    region_of_contest = np.zeros(n_c, dtype=int)
    region_of_contest[contest] = region
    u = np.zeros(n_c)
    v = np.zeros(n_r)
    a = b = 0.0
    sigma2 = tau_c2 = tau_r2 = 0.0
    for _ in range(iters):
        a, b = np.polyfit(z, cf - u[contest] - v[region], 1)
        resid = cf - (a * z + b)
        sigma2, tau_c2, tau_r2 = _components(resid, contest, n_c,
                                             region, region_of_contest, n_r)
        v_new = _shrunk(resid - u[contest], region, n_r, sigma2, tau_r2)
        u_new = _shrunk(resid - v_new[region], contest, n_c, sigma2, tau_c2,
                        extra=offsets)
        done = (np.max(np.abs(u_new - u)) < 1e-3 and np.max(np.abs(v_new - v)) < 1e-3)
        u, v = u_new, v_new
        if done:
            break
    n_ci, _ = _group_stats(np.ones_like(cf), contest, n_c)
    return {"a": float(a), "b": float(b), "u": u, "v": v,
            "sigma": float(np.sqrt(sigma2)),
            "tau_contest": float(np.sqrt(tau_c2)),
            "tau_region": float(np.sqrt(tau_r2)),
            "n_per_contest": n_ci}


def loco(z, cf, contest, region, hier, offsets=None):
    """Leave-one-contest-out RMSE. The held-out contest never sees its own u."""
    errs = []
    for g in np.unique(contest):
        tr, te = contest != g, contest == g
        if not hier:
            a, b = np.polyfit(z[tr], cf[tr], 1)
            errs.append(a * z[te] + b - cf[te])
            continue
        # renumber training groups so the held-out contest has no parameter
        codes = {c: i for i, c in enumerate(sorted(set(contest[tr])))}
        ctr = np.array([codes[c] for c in contest[tr]])
        sub = None
        if offsets is not None:
            obs, weight = offsets
            sub = (np.array([obs[c] for c in sorted(codes)]),
                   np.array([weight[c] for c in sorted(codes)]))
        f = fit_hier(z[tr], cf[tr], ctr, region[tr], offsets=sub)
        # the held-out contest inherits its region's level, plus its own external
        # offset observation when one exists
        pred = f["a"] * z[te] + f["b"] + f["v"][region[te]]
        if offsets is not None:
            obs, weight = offsets
            held = int(np.unique(contest[te])[0])
            if weight[held] > 0:
                pred = pred + obs[held]
        errs.append(pred - cf[te])
    return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))


def _cf_to_region(records, region_of):
    """CF mirror contest id -> region of the qoj contest it maps to."""
    import contextlib
    import io

    from .external_validate import _cf_mapping, _cf_problemset
    contests_like = defaultdict(list)
    for r in records:
        contests_like[r["contest_id"]].append(
            {"problem_label": r["problem_label"], "problem_name": r["problem_name"]})
    contests_like = [{"contest_id": c, "problems": p} for c, p in contests_like.items()]
    with contextlib.redirect_stdout(io.StringIO()):
        mapping = _cf_mapping(contests_like, defaultdict(lambda: "?"), _cf_problemset())
    return {cid: region_of.get(qoj, "?") for cid, qoj, _r, _m in mapping}


def _coded(records, region_of):
    """(z, cf, contest_code, region_code, contest_ids, region_names)."""
    our, cf, grp = _anchors(records)
    shape = _gym_shape(records)
    z = shape(our) if shape else our
    to_region = _cf_to_region(records, region_of)
    contest_ids = sorted(set(int(g) for g in grp))
    region_names = sorted({to_region[c] for c in contest_ids})
    contest = np.array([contest_ids.index(int(g)) for g in grp])
    region = np.array([region_names.index(to_region[int(g)]) for g in grp])
    return z, cf, contest, region, contest_ids, region_names


def level_sd(records, region_of=None):
    """Calibration *level* uncertainty per contest, in CF points.

    Returns ``(by_contest, default)``: the posterior sd of ``u_c`` for each qoj
    contest that has CF anchors, and the sd to use for every other contest,
    ``sqrt(tau_contest^2 + tau_region^2)`` -- what is not known about the level
    of a contest the anchors never saw. This is the uncertainty the shipped
    ``difficulty_cf_se`` used to omit entirely: it reported only the Laplace SE
    of ``b`` scaled through the map, as if the map itself were exact.
    """
    if region_of is None:
        region_of = _regions()
    z, cf, contest, region, contest_ids, _names = _coded(records, region_of)
    f = fit_hier(z, cf, contest, region)
    sigma2 = f["sigma"] ** 2
    tau_c2 = f["tau_contest"] ** 2
    tau_r2 = f["tau_region"] ** 2
    to_region = _cf_to_region(records, region_of)
    qoj_of_cf = _cf_to_qoj(records)
    by_contest = {}
    if tau_c2 > 0:
        for i, cfid in enumerate(contest_ids):
            n = float(f["n_per_contest"][i])
            post = 1.0 / (n / sigma2 + 1.0 / tau_c2)
            qoj = qoj_of_cf.get(cfid)
            if qoj is not None:
                by_contest[qoj] = float(np.sqrt(post))
    del to_region
    return by_contest, float(np.sqrt(tau_c2 + tau_r2))


def _cf_to_qoj(records):
    """CF mirror contest id -> the qoj contest id it maps to."""
    import contextlib
    import io

    from .external_validate import _cf_mapping, _cf_problemset
    contests_like = defaultdict(list)
    for r in records:
        contests_like[r["contest_id"]].append(
            {"problem_label": r["problem_label"], "problem_name": r["problem_name"]})
    contests_like = [{"contest_id": c, "problems": p} for c, p in contests_like.items()]
    with contextlib.redirect_stdout(io.StringIO()):
        mapping = _cf_mapping(contests_like, defaultdict(lambda: "?"), _cf_problemset())
    return {cid: qoj for cid, qoj, _r, _m in mapping}


def main():
    region_of = _regions()
    for name, fname in MODELS:
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            continue
        records = json.load(open(path))
        z, cf, contest, region, contest_ids, region_names = _coded(records, region_of)
        plain = loco(z, cf, contest, region, hier=False)
        hier = loco(z, cf, contest, region, hier=True)
        f = fit_hier(z, cf, contest, region)
        print(f"{name:16} LOCO plain={plain:6.1f}  hierarchical={hier:6.1f}   "
              f"sigma={f['sigma']:5.1f} tau_contest={f['tau_contest']:5.1f} "
              f"tau_region={f['tau_region']:5.1f}  "
              f"(n={len(cf)}/{len(contest_ids)} contests, {len(region_names)} regions)")
    print("\nper-region level of the shipped survival fit (partially pooled):")
    records = json.load(open(os.path.join(OUT, "problem_ratings_survival.json")))
    z, cf, contest, region, contest_ids, region_names = _coded(records, region_of)
    f = fit_hier(z, cf, contest, region)
    for i, r in enumerate(region_names):
        print(f"  {r:<20} v={f['v'][i]:+7.1f}")
    print(f"  {'(unanchored region)':<20} v=   +0.0  predictive sd "
          f"{np.hypot(f['tau_region'], f['tau_contest']):.1f} CF "
          f"(tau_region (+) tau_contest)")
    print("\nper-contest level (shrunk):")
    for i, cid in enumerate(contest_ids):
        print(f"  CF {cid}: n={int(f['n_per_contest'][i]):3d}  u={f['u'][i]:+7.1f}")


if __name__ == "__main__":
    main()
