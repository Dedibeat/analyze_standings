"""Pre-release audit of the DE calibration on the roster-attached fit (2026-09-28).

Research only: writes ``output/de_release_audit.json``; ratings, calibration
and exports are unchanged. The candidate is the survival/binary pair refit on
``tagged.json`` with the EC online-round rosters attached
(``scripts/attach_online_rosters.py``), calibrated by DE (``raw_b`` +
binary-minus-survival + conditional SE + solve rate + ``log1p`` field size).

1. Provenance: a fresh baseline fit must reproduce the saved raw fits exactly.
2. DE protocols (``calibration_ablation``: task-purged nested LOCO and LORO) on
   the baseline and the candidate.
3. Safer variants under the same nested protocol: each evidence feature left
   out, a survival/binary blend with and without the evidence terms, features
   clipped to the training range, and a correction shrunk by Mahalanobis
   distance from the training anchors (cutoff quantile chosen in inner folds).
4. Support stress: the three anchor contests at either end of field size,
   solve rate or disagreement are held out together.
5. Catalog staging (full-anchor refit, not OOF): displayed change from the
   shipped ratings, feature support, and fields below any evidence.
6. Robust scaling against the CF-gym population (Halpin 2022, "Differential
   item functioning via robust scaling"): one linking line per method, then a
   Tukey-bisquare offset per contest. Gym difficulties never enter DE, so the
   spread of those offsets checks each method's contest levels independently.

    python3 scripts/attach_online_rosters.py data/tagged.json /tmp/tagged_rosters.json
    python3 -m arch_b.de_release_audit /tmp/tagged_rosters.json
"""

import hashlib
import json
import os
import sys
from collections import Counter

import numpy as np

from . import model, survival
from .aoj import spearman
from .calibrate import _gym_shape
from .calibration_ablation import LAMDAS, RIDGE_ALPHAS, _fold_result, _metrics, _purged_train
from .calibration_experiment import _affine, _full_rows, build_anchor_table
from .joint import TAGGED, estimate_joint
from .run import MIN_SOLVE_HOURS

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT = os.path.join(ROOT, "output", "de_release_audit.json")
GYM = os.path.join(ROOT, "output", "gym_difficulty.json")
DE = ("raw_b", "binary_minus_survival", "conditional_fit_se", "solve_rate", "log_field_size")
DE_NO_FIELD = DE[:-1]
SEED = 20260928


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def problem_records(ds, b, se_b):
    """Problem records exactly as ``arch_b.run`` writes them."""
    return [{"problem_id": pid, "problem_label": label, "problem_name": name,
             "contest_id": int(cid), "difficulty": round(float(b[p]), 1),
             "difficulty_se": round(float(se_b[p]), 1), "solved_count": int(ds.solved_count[p]),
             "reported_solved_in_contest": int(ds.raw_solved_count[p])}
            for p, (cid, label, pid, name) in enumerate(ds.problems)]


def fit_records(tagged=None):
    """{"binary"/"survival": records} for the shipped inputs or a replacement tagged file."""
    out = {}
    for name, mod in (("binary", model), ("survival", survival)):
        ds, theta, b, _, _ = estimate_joint(fit_fn=mod.fit, min_solve_hours=MIN_SOLVE_HOURS,
                                            verbose=False, tagged=tagged)
        out[name] = problem_records(ds, b, mod.laplace_se(ds, theta, b)[1])
    return out


def with_binary(rows, binary):
    key = {(r["contest_id"], r["problem_label"]): r["difficulty"] for r in binary}
    for r in rows:
        r["b_bin"] = key[(r["contest_id"], r["problem_label"])]
    return rows


# ---- generic nested protocol (same folds, purge and grids as calibration_ablation) ----

def _x(rows, feats):
    return np.array([[r[f] for f in feats] for r in rows], float)


def _y(rows):
    return np.array([r["cf"] for r in rows], float)


def _ridge(train, feats, alpha, blend=None):
    """Residual ridge on a linear baseline; returns predict(test, clip) -> (base, correction, distance)."""
    def z(rows):
        s = _x(rows, ("raw_b",))[:, 0]
        return s if blend is None else blend * s + (1 - blend) * _x(rows, ("b_bin",))[:, 0]
    slope, icept = np.polyfit(z(train), _y(train), 1)
    xtr = _x(train, feats)
    mu, sd = xtr.mean(0), xtr.std(0)
    sd[sd == 0] = 1.0
    ztr = (xtr - mu) / sd
    a = np.column_stack((np.ones(len(train)), ztr))
    coef = np.linalg.solve(a.T @ a + np.diag([0.0] + [alpha] * len(feats)),
                           a.T @ (_y(train) - slope * z(train) - icept))
    icov = np.linalg.inv(np.atleast_2d(np.cov(ztr.T)) + 1e-9 * np.eye(len(feats)))
    dist = lambda zz: np.sqrt(np.einsum("ij,jk,ik->i", zz, icov, zz))
    lo, hi = xtr.min(0), xtr.max(0)

    def predict(test, clip=False):
        xt = _x(test, feats)
        zt = ((np.clip(xt, lo, hi) if clip else xt) - mu) / sd
        return (slope * z(test) + icept, np.column_stack((np.ones(len(test)), zt)) @ coef,
                dist((xt - mu) / sd))
    return predict, dist(ztr)


def method(kind, feats=DE):
    """(grid, predict(train, test, setting)) for one prespecified calibration rule."""
    ridge_grid = [(a, lam) for a in RIDGE_ALPHAS for lam in LAMDAS]
    if kind in ("ridge", "clip"):
        def f(tr, te, p):
            base, corr, _ = _ridge(tr, feats, p[0])[0](te, clip=kind == "clip")
            return base + p[1] * corr
        return ridge_grid, f
    if kind == "shrink":   # correction * min(1, (c/d)^2), c = a training-distance quantile
        def f(tr, te, p):
            predict, dtrain = _ridge(tr, feats, p[0])
            base, corr, d = predict(te)
            k = 1.0 if p[2] is None else np.minimum(1.0, (np.quantile(dtrain, p[2]) / np.maximum(d, 1e-9)) ** 2)
            return base + p[1] * k * corr
        return [(a, lam, q) for a, lam in ridge_grid for q in (0.9, 0.95, 1.0, None)], f
    if kind == "blend":    # affine of w*survival + (1-w)*binary, no evidence terms
        def f(tr, te, w):
            z = lambda rows: w * _x(rows, ("raw_b",))[:, 0] + (1 - w) * _x(rows, ("b_bin",))[:, 0]
            slope, icept = np.polyfit(z(tr), _y(tr), 1)
            return slope * z(te) + icept
        return [round(w, 1) for w in np.linspace(0, 1, 11)], f
    if kind == "blend+E":  # blend baseline + ridge on the evidence terms
        def f(tr, te, p):
            base, corr, _ = _ridge(tr, ("raw_b",) + DE[2:], p[1], blend=p[0])[0](te)
            return base + p[2] * corr
        return [(round(w, 1), a, lam) for w in np.linspace(0, 1, 11) for a, lam in ridge_grid], f
    raise ValueError(kind)


def nested(pool, held, grid, f):
    """Choose the setting by inner contest folds of the purged training pool, then predict ``held``."""
    train = _purged_train(pool, held)
    inner = [(_purged_train(train, part), part) for c in sorted({r["cf_contest"] for r in train})
             for part in [[r for r in train if r["cf_contest"] == c]]]
    best = None
    for p in grid:
        se = sum(float(np.sum((f(tr, te, p) - _y(te)) ** 2)) for tr, te in inner)
        if best is None or se < best[0] - 1e-9:
            best = (se, p)
    return f(train, held, best[1]), best[1]


def loco(rows, kind, feats=DE):
    grid, f = method(kind, feats)
    pred, picks = np.zeros(len(rows)), {}
    for c in sorted({r["cf_contest"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["cf_contest"] == c]
        pred[idx], picks[c] = nested(rows, [rows[i] for i in idx], grid, f)
    return pred, picks


def rmse(pred, rows):
    return float(np.sqrt(np.mean((pred - _y(rows)) ** 2)))


def contest_bootstrap(rows, a, b, n=20000):
    """Paired resampling of the 15 anchor contests with predictions fixed: RMSE(a) - RMSE(b)."""
    y, g = _y(rows), np.array([r["cf_contest"] for r in rows])
    groups = [np.flatnonzero(g == c) for c in sorted(set(g))]
    ea, eb = (a - y) ** 2, (b - y) ** 2
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(n):
        k = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        draws.append(np.sqrt(ea[k].mean()) - np.sqrt(eb[k].mean()))
    return {"difference": float(np.sqrt(ea.mean()) - np.sqrt(eb.mean())),
            "bootstrap_2.5_97.5": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]}


def full_anchor_fit(rows, full, kind, feats=DE):
    """Non-OOF: select on all anchors' inner contest folds, then predict every appearance."""
    grid, f = method(kind, feats)
    held_all = [[r for r in rows if r["cf_contest"] == c] for c in sorted({r["cf_contest"] for r in rows})]
    inner = [(_purged_train(rows, part), part) for part in held_all]
    scores = {p: sum(float(np.sum((f(tr, te, p) - _y(te)) ** 2)) for tr, te in inner) for p in grid}
    best = min(grid, key=lambda p: (scores[p], grid.index(p)))
    return f(rows, full, best), best


# ---- robust scaling (Halpin 2022) ----

def bisquare_location(x, c=4.685, iters=100):
    """Tukey-bisquare M-estimate of location with a MAD scale; returns (location, weights)."""
    x = np.asarray(x, float)
    mu = float(np.median(x))
    scale = 1.4826 * float(np.median(np.abs(x - mu))) or 1.0
    w = np.ones_like(x)
    for _ in range(iters):
        u = (x - mu) / (c * scale)
        w = np.where(np.abs(u) < 1, (1 - u ** 2) ** 2, 0.0)
        new = float(np.sum(w * x) / np.sum(w))
        if abs(new - mu) < 1e-9:
            break
        mu = new
    return mu, w


def gym_scaling(full, preds, anchors):
    """Per method: one gym linking line, then bisquare contest offsets by support segment."""
    idx = {(r["contest_id"], r["problem_label"]): i for i, r in enumerate(full)}
    anchor_contests = {r["contest_id"] for r in anchors}
    anchor_tasks = {r["canonical_task"] for r in anchors}
    lo = {f: min(r[f] for r in anchors) for f in DE}
    hi = {f: max(r[f] for r in anchors) for f in DE}
    items = [(g["difficulty"], idx[(g["contest_id"], g["problem_label"])], g["contest_id"]) for g in _read(GYM)
             if (g["contest_id"], g["problem_label"]) in idx and g["contest_id"] not in anchor_contests
             and full[idx[(g["contest_id"], g["problem_label"])]]["canonical_task"] not in anchor_tasks]
    y = np.array([t[0] for t in items])
    ii = np.array([t[1] for t in items])
    cc = np.array([t[2] for t in items])
    field = np.array([full[i]["log_field_size"] for i in ii])
    inside = np.array([all(lo[f] <= full[i][f] <= hi[f] for f in DE) for i in ii])
    segments = {"all": np.ones(len(ii), bool), "inside_all_anchor_ranges": inside,
                "field_below_anchor_min": field < lo["log_field_size"],
                "field_above_anchor_max": field > hi["log_field_size"]}
    out = {"items": len(items), "contests": len(set(cc)),
           "segment_items": {k: int(m.sum()) for k, m in segments.items()}, "methods": {}}
    for name, p in preds.items():
        x = p[ii]
        slope, icept = np.polyfit(x, y, 1)
        e = y - (icept + slope * x)
        res = {"linking_slope": float(slope)}
        for seg, m in segments.items():
            offsets, within = [], []
            for c in sorted(set(cc[m])):
                ec = e[m & (cc == c)]
                if len(ec) >= 5:
                    mu, _ = bisquare_location(ec)
                    offsets.append(mu)
                    within.extend(ec - mu)
            res[seg] = {"rmse": float(np.sqrt(np.mean(e[m] ** 2))), "contests_with_5_items": len(offsets),
                        "contest_offset_sd": float(np.std(offsets)),
                        "within_contest_robust_sd": float(1.4826 * np.median(np.abs(within))),
                        "spearman": float(spearman(list(x[m]), list(y[m])))}
        out["methods"][name] = res
    return out


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(tagged):
    shipped_fit = {"binary": _read(os.path.join(ROOT, "output", "problem_ratings_b.json")),
                   "survival": _read(os.path.join(ROOT, "output", "problem_ratings_survival.json"))}
    base = fit_records()
    if base != shipped_fit:
        raise RuntimeError("a fresh baseline fit does not reproduce the saved raw fits")
    cand = fit_records(tagged)
    print("fits done; baseline reproduces the saved raw fits", flush=True)

    result = {"research_only": True, "production_changed": False, "fresh_confirmation": False,
              "provenance_sha256": {os.path.relpath(p, ROOT).replace(os.sep, "/"): _sha(p) for p in
                                    (TAGGED, GYM, os.path.join(ROOT, "output", "problem_ratings_calibrated.json"),
                                     os.path.join(ROOT, "data", "cf_problemset.json"), __file__)},
              "candidate_tagged_sha256": _sha(tagged)}
    protocols = {}
    for name, recs in (("baseline", base), ("candidate", cand)):
        rows = build_anchor_table(recs["survival"], recs["binary"])
        shape = _gym_shape(recs["survival"])
        protocols[name] = {}
        for proto, key in (("leave_one_cf_contest_out", "cf_contest"), ("leave_one_region_out", "region")):
            folds = {str(g): _fold_result(rows, [r for r in rows if r[key] == g], g, shape)
                     for g in sorted({r[key] for r in rows}, key=str)}
            _, _, metrics, by_contest, _ = _metrics(folds)
            protocols[name][proto] = {
                "rmse": {m: metrics[m] for m in ("raw_affine", "gym_shape_affine", "ridge_DE", "ridge_DET", "ridge_adaptive")},
                "adaptive_bundles": dict(Counter(f["selected"]["adaptive"]["bundle"] for f in folds.values()))}
            if proto == "leave_one_cf_contest_out":
                protocols[name][proto]["de_wins_vs_gym"] = sum(v["ridge_DE"] < v["gym_shape_affine"] for v in by_contest.values())
        print(f"{name}: {protocols[name]['leave_one_cf_contest_out']['rmse']}", flush=True)
    result["de_protocols"] = protocols

    rows = with_binary(build_anchor_table(cand["survival"], cand["binary"]), cand["binary"])
    specs = {"raw_affine": ("ridge", ("raw_b",)), "DE": ("ridge", DE),
             "DE_without_conditional_se": ("ridge", tuple(f for f in DE if f != "conditional_fit_se")),
             "DE_without_solve_rate": ("ridge", tuple(f for f in DE if f != "solve_rate")),
             "DE_without_field_size": ("ridge", DE_NO_FIELD),
             "blend": ("blend", DE), "blend_plus_evidence": ("blend+E", DE),
             "DE_clipped_to_training_range": ("clip", DE), "DE_support_shrunk": ("shrink", DE)}
    oof, variants = {}, {}
    for name, (kind, feats) in specs.items():
        oof[name], picks = loco(rows, kind, feats)
        variants[name] = {"loco_rmse": rmse(oof[name], rows),
                          "settings": dict(Counter(str(p) for p in picks.values()))}
        print(f"variant {name}: {variants[name]['loco_rmse']:.2f}", flush=True)
    for name in specs:
        if name != "DE":
            variants[name]["minus_DE"] = contest_bootstrap(rows, oof[name], oof["DE"])
    result["candidate_variants_nested_loco"] = variants

    field = {r["cf_contest"]: r["log_field_size"] for r in rows}
    per_contest = lambda f: {c: float(np.mean([r[f] for r in rows if r["cf_contest"] == c])) for c in field}
    stress = {}
    for label, score in (("field_size", field), ("solve_rate", per_contest("solve_rate")),
                         ("disagreement", per_contest("binary_minus_survival"))):
        order = sorted(score, key=score.get)
        for tail, held_c in (("low", order[:3]), ("high", order[-3:])):
            held = [r for r in rows if r["cf_contest"] in held_c]
            entry = {"held_cf_contests": held_c, "anchors": len(held)}
            for name, (kind, feats) in (("raw_affine", ("ridge", ("raw_b",))), ("DE", ("ridge", DE)),
                                        ("DE_clipped_to_training_range", ("clip", DE)),
                                        ("DE_support_shrunk", ("shrink", DE)),
                                        ("DE_without_field_size", ("ridge", DE_NO_FIELD)), ("blend", ("blend", DE))):
                grid, f = method(kind, feats)
                entry[name] = rmse(nested(rows, held, grid, f)[0], held)
            stress[f"{label}_{tail}_3"] = entry
    result["support_stress_nested"] = stress
    print("stress done", flush=True)

    full = with_binary(_full_rows(cand["survival"], cand["binary"]), cand["binary"])
    shape = _gym_shape(cand["survival"])
    shipped = {(r["contest_id"], r["problem_label"]): r["difficulty_cf"]
               for r in _read(os.path.join(ROOT, "output", "problem_ratings_calibrated.json"))}
    ship = np.array([shipped[(r["contest_id"], r["problem_label"])] for r in full])
    preds, settings = {"raw_affine": _affine(rows, full, None), "gym_shape_affine": _affine(rows, full, shape)}, {}
    for name, (kind, feats) in (("DE", ("ridge", DE)), ("DE_clipped_to_training_range", ("clip", DE)),
                                ("DE_without_field_size", ("ridge", DE_NO_FIELD))):
        preds[name], settings[name] = full_anchor_fit(rows, full, kind, feats)
    lo = {f: min(r[f] for r in rows) for f in DE}
    hi = {f: max(r[f] for r in rows) for f in DE}
    # field sizes with any evidence: CF anchors, or a gym-population contest with >= 5 matched problems
    gym_items = Counter(g["contest_id"] for g in _read(GYM))
    by_key = {(r["contest_id"], r["problem_label"]): r for r in full}
    evidence = [by_key[(g["contest_id"], g["problem_label"])]["log_field_size"] for g in _read(GYM)
                if (g["contest_id"], g["problem_label"]) in by_key and gym_items[g["contest_id"]] >= 5]
    ev_lo, ev_hi = min(evidence + [lo["log_field_size"]]), max(evidence + [hi["log_field_size"]])
    field = np.array([r["log_field_size"] for r in full])
    tails = {"below": field < ev_lo, "above": field > ev_hi}
    online = np.isin([r["contest_id"] for r in full], [1485, 1794, 1799, 2513, 2524])
    catalog = {"appearances": len(full), "contests": len({r["contest_id"] for r in full}),
               "field_range_with_any_evidence": [float(np.expm1(ev_lo)), float(np.expm1(ev_hi))]}
    for tail, m in tails.items():
        catalog[f"field_{tail}_all_evidence"] = {"appearances": int(m.sum()),
                                                  "contests": len({r["contest_id"] for r, t in zip(full, m) if t})}
    for name, p in preds.items():
        disp = np.round(np.clip(p, 800, 4000), 1)
        d = disp - ship
        feats = DE_NO_FIELD if name == "DE_without_field_size" else DE
        entry = {"setting": str(settings.get(name)), "mean_display_change": float(d.mean()),
                 "abs_change_quantiles_50_90_95_100": np.quantile(np.abs(d), [.5, .9, .95, 1]).round(1).tolist(),
                 "abs_change_at_least": {str(k): int((np.abs(d) >= k).sum()) for k in (100, 200, 400)},
                 "outside_any_anchor_feature_range": int(sum(any(not lo[f] <= r[f] <= hi[f] for f in feats) for r in full)),
                 "field_below_all_evidence_mean_change": float(d[tails["below"]].mean()),
                 "field_above_all_evidence_mean_change": float(d[tails["above"]].mean()),
                 "online_round_mean_change": float(d[online].mean())}
        aob = [i for i, r in enumerate(full) if (r["contest_id"], r["problem_label"]) == (1965, "H")]
        entry["aobayama_1965_H"] = float(disp[aob[0]])
        catalog[name] = entry
    result["catalog_vs_shipped_not_oof"] = catalog
    result["gym_robust_scaling_non_anchor"] = gym_scaling(full, preds | {"shipped_gym": ship}, rows)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    return result


if __name__ == "__main__":
    out = run(sys.argv[1])
    print(json.dumps({k: v["loco_rmse"] for k, v in out["candidate_variants_nested_loco"].items()}, indent=1))
