"""Frozen stability-penalized DE experiment. See de_stability_plan.md."""

import argparse
import collections
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .calibration_ablation import _purged_train
from .de_release_audit import DE, contest_bootstrap, method, nested
from .de_stability_data import (ROOT, RUN, TRAIN, VIEWS, check_inputs, digest,
                                initialize, prepare_view, read_view)

ALPHAS = (0.1, 1.0, 10.0)
BETAS = (0.0, 0.1, 1.0, 10.0)


def matrix(rows):
    return np.array([[r[f] for f in DE] for r in rows], float).reshape(-1, len(DE))


def fit_stable(train, views, alpha, beta):
    """Weighted augmented ridge, penalizing changes in final predictions."""
    full = {r["row_id"]: r for r in train}
    x = matrix(train)
    mean, scale = x.mean(0), x.std(0)
    scale[scale == 0] = 1
    lo, hi = x.min(0), x.max(0)
    slope, intercept = np.polyfit(x[:, 0], [r["cf"] for r in train], 1)

    def design(rows):
        return np.column_stack((np.ones(len(rows)), (np.clip(matrix(rows), lo, hi) - mean) / scale))

    def baseline(rows):
        return slope * matrix(rows)[:, 0] + intercept

    selected = {name: [r for r in views[name] if r["row_id"] in full] for name in TRAIN}
    counts = collections.Counter(r["row_id"] for rows in selected.values() for r in rows)
    a = np.diag([0.0] + [alpha / len(train)] * len(DE))
    rhs = np.zeros(len(DE) + 1)
    for name, rows in selected.items():
        if not rows:
            continue
        z, base = design(rows), baseline(rows)
        w = np.array([1 / (len(train) * counts[r["row_id"]]) for r in rows])
        residual = np.array([full[r["row_id"]]["cf"] for r in rows]) - base
        a += z.T @ (w[:, None] * z)
        rhs += z.T @ (w * residual)
        if name != "full":
            reference = [full[r["row_id"]] for r in rows]
            d = z - design(reference)
            delta_base = base - baseline(reference)
            ws = np.array([1 / (len(train) * (counts[r["row_id"]] - 1)) for r in rows])
            a += beta * d.T @ (ws[:, None] * d)
            rhs -= beta * d.T @ (ws * delta_base)
    coef = np.linalg.solve(a, rhs)

    def predict(rows):
        p = baseline(rows) + design(rows) @ coef
        if not np.isfinite(p).all():
            raise RuntimeError("non-finite stable calibration")
        return p
    return predict


def view_errors(predict, held, views):
    """One equally weighted error per task, averaging its available views."""
    errors = {r["row_id"]: [] for r in held}
    for name in TRAIN:
        rows = [r for r in views[name] if r["row_id"] in errors]
        for r, p in zip(rows, predict(rows)):
            errors[r["row_id"]].append((p - r["cf"]) ** 2)
    return [float(np.mean(v)) for v in errors.values()]


def select(train, views):
    scores = {(alpha, beta): [] for alpha in ALPHAS for beta in BETAS}
    for contest in sorted({r["cf_contest"] for r in train}):
        held = [r for r in train if r["cf_contest"] == contest]
        inner = _purged_train(train, held)
        for (alpha, beta), errors in scores.items():
            errors.extend(view_errors(fit_stable(inner, views, alpha, beta), held, views))
    ordered = sorted(scores, key=lambda p: (np.mean(scores[p]), p[1], p[0]))
    return {"stable": ordered[0], "augmented": next(p for p in ordered if p[1] == 0),
            "scores": {f"{a:g}/{b:g}": float(np.mean(v)) for (a, b), v in scores.items()}}


def outer_fold(full, views, contest):
    held = [r for r in full if r["cf_contest"] == contest]
    train = _purged_train(full, held)
    picks = select(train, views)
    grid, de = method("clip", DE)
    _, de_pick = nested(full, held, grid, de)
    slope, intercept = np.polyfit([r["b_bin"] for r in train], [r["cf"] for r in train], 1)
    predictors = {name: fit_stable(train, views, *picks[name]) for name in ("stable", "augmented")}
    held_ids = {r["row_id"] for r in held}
    predictions = {}
    for name, available in views.items():
        rows = [r for r in available if r["row_id"] in held_ids]
        values = {m: f(rows) for m, f in predictors.items()}
        values["DE"] = de(train, rows, de_pick) if rows else []
        values["binary_affine"] = slope * np.array([r["b_bin"] for r in rows]) + intercept
        predictions[name] = [{"row_id": r["row_id"], "canonical_task": r["canonical_task"],
                              "cf_contest": r["cf_contest"], "cf": r["cf"], "region": r["region"],
                              **{m: float(v[i]) for m, v in values.items()}} for i, r in enumerate(rows)]
    return {"selected": {**picks, "DE": de_pick}, "training_rows": [r["row_id"] for r in train],
            "held_rows": sorted(held_ids), "predictions": predictions}


METHODS = ("DE", "binary_affine", "augmented", "stable")


def metrics(rows, name):
    if not rows:
        return {"problems": 0}
    errors = np.array([r[name] - r["cf"] for r in rows])
    groups = np.array([r["cf_contest"] for r in rows])
    by_contest = {str(g): {"rmse": float(np.sqrt(np.mean(errors[groups == g] ** 2))),
                          "mean_error": float(np.mean(errors[groups == g]))} for g in sorted(set(groups))}
    by_region = {g: float(np.sqrt(np.mean([errors[i] ** 2 for i, r in enumerate(rows) if r["region"] == g])))
                 for g in sorted({r["region"] for r in rows})}
    return {"problems": len(rows), "contests": len(by_contest), "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "mean_error": float(errors.mean()), "contest_balanced_rmse": float(np.sqrt(np.mean(
                [v["rmse"] ** 2 for v in by_contest.values()]))),
            "contest_balanced_mean_error": float(np.mean([v["mean_error"] for v in by_contest.values()])),
            "predicted_sd": float(np.std([r[name] for r in rows])),
            "target_sd": float(np.std([r["cf"] for r in rows])),
            "per_contest": by_contest, "per_region_rmse": by_region,
            "tail_cf_ge_2800_rmse": float(np.sqrt(np.mean([errors[i] ** 2 for i, r in enumerate(rows)
                                                          if r["cf"] >= 2800]))) if any(r["cf"] >= 2800 for r in rows) else None}


def drift(rows, reference, name):
    by_id = {r["row_id"]: r for r in reference}
    common = [r for r in rows if r["row_id"] in by_id]
    if not common:
        return {"problems": 0}
    delta = np.array([r[name] - by_id[r["row_id"]][name] for r in common])
    reversals = pairs = 0
    for c in sorted({r["cf_contest"] for r in common}):
        part = [r for r in common if r["cf_contest"] == c]
        i, j = np.triu_indices(len(part), 1)
        a = np.array([r[name] for r in part])
        b = np.array([by_id[r["row_id"]][name] for r in part])
        reversals += int(np.sum((a[i] - a[j]) * (b[i] - b[j]) < 0))
        pairs += len(i)
    return {"problems": len(common), "signed_mean": float(delta.mean()),
            "median_absolute": float(np.median(np.abs(delta))), "rms": float(np.sqrt(np.mean(delta ** 2))),
            "order_reversals": reversals, "within_contest_pairs": pairs}


def evaluate():
    snapshot = check_inputs()
    cache = {name: read_view(name, digest(snapshot)) for name in VIEWS}
    views = {name: rec["rows"] for name, rec in cache.items()}
    full = views["full"]
    folds = {}
    for c in sorted({r["cf_contest"] for r in full}):
        folds[c] = outer_fold(full, views, c)
        print(f"evaluated CF contest {c}", flush=True)
    predictions = {v: [r for f in folds.values() for r in f["predictions"][v]] for v in VIEWS}
    scorecard = {}
    for v, rows in predictions.items():
        ref = predictions["strength_pool" if v in ("strong", "weak", "strength_pool") else "full"]
        scorecard[v] = {}
        for name in METHODS:
            entry = {**metrics(rows, name), "drift": drift(rows, ref, name)}
            if rows:
                for baseline in ("DE", "augmented"):
                    entry[f"rmse_minus_{baseline}"] = contest_bootstrap(
                        rows, np.array([r[name] for r in rows]), np.array([r[baseline] for r in rows]), n=2000)
            scorecard[v][name] = entry
    out = {"research_only": True, "independent_confirmation": False, "fingerprint": digest(snapshot),
           "training_views": TRAIN, "reserved_views": [v for v in VIEWS if v not in TRAIN],
           "coverage": {v: rec["missing_rows"] for v, rec in cache.items()},
           "folds": folds, "scorecard": scorecard}
    path = RUN / "evaluation.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)
    md = ["# DE stability development experiment", "", "Research only; not fresh confirmation.", "",
          "| View | Method | Problems | CF RMSE | Contest-balanced RMSE | Drift RMS |",
          "|---|---|---:|---:|---:|---:|"]
    for v, results in scorecard.items():
        for name, s in results.items():
            if s["problems"]:
                md.append(f"| {v} | {name} | {s['problems']} | {s['rmse']:.2f} | "
                          f"{s['contest_balanced_rmse']:.2f} | {s['drift']['rms']:.2f} |")
    zero = sum(f["selected"]["stable"][1] == 0 for f in folds.values())
    md += ["", f"Selected beta=0 in {zero}/{len(folds)} folds. Inspect whether the penalty adds",
           "anything beyond augmented ridge. Full predictions, intervals, tail/region errors,",
           "spread and order reversals are in evaluation.json. No production promotion.", ""]
    (RUN / "evaluation.md").write_text("\n".join(md))
    print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    p = sub.add_parser("prepare")
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--view", action="append", choices=VIEWS)
    sub.add_parser("evaluate")
    args = parser.parse_args()
    snapshot = check_inputs()
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text())
    if len(anchors) != 185 or len({r["cf_contest"] for r in anchors}) != 15:
        raise RuntimeError("frozen anchor coverage changed")
    if args.command == "check":
        print(f"verified {len(snapshot['sha256'])} frozen inputs; 185 anchors / 15 contests")
        for v in VIEWS:
            if (RUN / f"{v}.json.gz").exists():
                rec = read_view(v, digest(snapshot))
                print(f"{v}: cached, {len(rec['rows'])} problems")
            else:
                print(f"{v}: not prepared")
    elif args.command == "prepare":
        if args.jobs < 1:
            parser.error("--jobs must be positive")
        jobs = list(dict.fromkeys(args.view or VIEWS))
        if args.jobs == 1:
            initialize()
            for v in jobs:
                print(prepare_view(v), flush=True)
        else:
            with ProcessPoolExecutor(max_workers=args.jobs, initializer=initialize) as pool:
                for message in pool.map(prepare_view, jobs):
                    print(message, flush=True)
    else:
        evaluate()


if __name__ == "__main__":
    main()
