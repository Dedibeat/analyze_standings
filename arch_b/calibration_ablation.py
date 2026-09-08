"""Frozen research-only ridge feature-group ablation.

This module deliberately reuses the baseline experiment's anchor construction.
It does not change or write production calibration artifacts.
"""

import hashlib
import json
import os

import numpy as np

from .calibrate import _gym_shape
from .calibration_experiment import _affine, _load_json, build_anchor_table
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output",
                   "calibration_ablation.json")
PLAN = os.path.join(os.path.dirname(__file__), os.pardir,
                    "calibration_ablation_plan.md")
LAMDAS = (0.0, 0.25, 0.5, 0.75, 1.0)
RIDGE_ALPHAS = (0.1, 1.0, 10.0)
BUNDLES = ("D", "E", "T", "DE", "DT", "ET", "DET")
GROUPS = {
    "D": ("binary_minus_survival",),
    "E": ("conditional_fit_se", "solve_rate", "log_field_size"),
    "T": ("log_median_solve_seconds", "timing_missing"),
}
CONTROL_DET_RMSE = 229.6269246


def bundle_features(bundle):
    """Return raw difficulty plus the frozen residual feature bundle."""
    if bundle not in BUNDLES:
        raise ValueError(f"unknown fixed bundle {bundle}")
    return ("raw_b",) + tuple(feature for group in "DET"
                              if group in bundle for feature in GROUPS[group])


def _matrix(rows, bundle):
    return np.array([[row[feature] for feature in bundle_features(bundle)]
                     for row in rows], float)


def _purged_train(rows, held):
    held_ids = {row["row_id"] for row in held}
    held_tasks = {row.get("canonical_task") for row in held} - {None}
    train = [row for row in rows if row["row_id"] not in held_ids and
             row.get("canonical_task") not in held_tasks]
    if held_ids & {row["row_id"] for row in train}:
        raise RuntimeError("held row leaked into training")
    if held_tasks & {row.get("canonical_task") for row in train}:
        raise RuntimeError("held canonical task leaked into training")
    return train


def _ridge_prediction(train, test, bundle, alpha):
    base_train = _affine(train, train, None)
    x_train, x_test = _matrix(train, bundle), _matrix(test, bundle)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        raise ValueError("non-finite ridge feature")
    mean, scale = x_train.mean(0), x_train.std(0)
    scale[scale == 0] = 1.0
    x_train = np.column_stack((np.ones(len(train)), (x_train - mean) / scale))
    x_test = np.column_stack((np.ones(len(test)), (x_test - mean) / scale))
    penalty = np.diag([0.0] + [alpha] * (x_train.shape[1] - 1))
    residual = np.array([row["cf"] for row in train]) - base_train
    coef = np.linalg.solve(x_train.T @ x_train + penalty, x_train.T @ residual)
    return _affine(train, test, None) + x_test @ coef


def fit_predict_fixed(train, test, bundle, alpha, lam):
    """Fit one fixed residual bundle using only ``train`` labels and features."""
    prediction = _affine(train, test, None)
    corrected = _ridge_prediction(train, test, bundle, alpha)
    prediction = prediction + lam * (corrected - prediction)
    if prediction.shape != (len(test),) or not np.isfinite(prediction).all():
        raise ValueError("fixed ridge returned non-finite or wrong-shaped predictions")
    return prediction


def _inner_scores(train, bundle, alpha):
    raw, predicted, target = [], [], []
    for contest in sorted({row["cf_contest"] for row in train}):
        held = [row for row in train if row["cf_contest"] == contest]
        inner_train = _purged_train(train, held)
        if not inner_train:
            raise RuntimeError("inner task purge left no training anchors")
        raw.extend(_affine(inner_train, held, None))
        predicted.extend(_ridge_prediction(inner_train, held, bundle, alpha))
        target.extend(row["cf"] for row in held)
    raw, predicted, target = np.asarray(raw), np.asarray(predicted), np.asarray(target)
    # The unshrunk prediction above is raw + full correction.  Scoring all
    # lambdas here intentionally reuses that same fit, as in the old control.
    return {lam: float(np.mean((raw + lam * (predicted - raw) - target) ** 2))
            for lam in LAMDAS}


def select_inner_contests(train, bundles=BUNDLES):
    """Select frozen settings from grouped inner-contest folds only.

    Exact-score ties retain input bundle order, then alpha/lambda grid order;
    adaptive selection additionally prefers fewer added features first.
    """
    bundles = tuple(bundles)
    if not bundles or any(bundle not in BUNDLES for bundle in bundles):
        raise ValueError("bundles must be nonempty frozen bundle names")
    fixed, candidates = {}, []
    for bundle in bundles:
        scores = {}
        for alpha in RIDGE_ALPHAS:
            scores.update({(alpha, lam): score
                           for lam, score in _inner_scores(train, bundle, alpha).items()})
        alpha, lam = min(scores, key=scores.get)
        fixed[bundle] = {"alpha": alpha, "lambda": lam,
                         "inner_mse": scores[(alpha, lam)],
                         "scores": {f"{a:g}/{l:g}": value
                                    for (a, l), value in scores.items()}}
        for (candidate_alpha, candidate_lam), score in scores.items():
            candidates.append((score, len(bundle_features(bundle)) - 1,
                               bundles.index(bundle), RIDGE_ALPHAS.index(candidate_alpha),
                               LAMDAS.index(candidate_lam), bundle, candidate_alpha,
                               candidate_lam))
    winner = min(candidates)
    adaptive = {"bundle": winner[5], "alpha": winner[6], "lambda": winner[7],
                "inner_mse": winner[0]}
    return {"fixed": fixed, "adaptive": adaptive}


def select_full_anchors(rows, bundles=BUNDLES):
    """All-anchor inner selection for transfer diagnostics only, never OOF."""
    return select_inner_contests(rows, bundles)


def _fold_result(rows, held, fold_name, shape):
    train = _purged_train(rows, held)
    settings = select_inner_contests(train)
    raw = _affine(train, held, None)
    gym = _affine(train, held, shape)
    values = {"raw_affine": raw, "gym_shape_affine": gym}
    for bundle, setting in settings["fixed"].items():
        values[f"ridge_{bundle}"] = fit_predict_fixed(
            train, held, bundle, setting["alpha"], setting["lambda"])
    adaptive = settings["adaptive"]
    values["ridge_adaptive"] = fit_predict_fixed(
        train, held, adaptive["bundle"], adaptive["alpha"], adaptive["lambda"])
    for name, value in values.items():
        if np.asarray(value).shape != (len(held),) or not np.isfinite(value).all():
            raise RuntimeError(f"non-finite or wrong-shaped {name} prediction")
    predictions = []
    for index, row in enumerate(held):
        entry = {"row_id": row["row_id"], "cf": row["cf"],
                 "cf_contest": row["cf_contest"], "contest_id": row["contest_id"],
                 "problem_id": row["problem_id"], "problem_label": row["problem_label"],
                 "canonical_task": row["canonical_task"], "region": row["region"],
                 "features": {name: float(row[name]) for name in bundle_features("DET")}}
        entry.update({name: float(value[index]) for name, value in values.items()})
        predictions.append(entry)
    return {"held": fold_name, "held_rows": [row["row_id"] for row in held],
            "training_rows": [row["row_id"] for row in train], "selected": settings,
            "predictions": predictions}


def _metrics(folds):
    flat = [entry for fold in folds.values() for entry in fold["predictions"]]
    if len(flat) != 185 or len({entry["row_id"] for entry in flat}) != 185:
        raise RuntimeError("protocol must produce exactly one OOF prediction for all 185 anchors")
    methods = sorted(key for key in flat[0] if key.startswith("ridge_") or key.endswith("affine"))
    rmse = lambda values, method: float(np.sqrt(np.mean([(row[method] - row["cf"]) ** 2
                                                          for row in values])))
    by_contest = {str(contest): {method: rmse([row for row in flat if row["cf_contest"] == contest], method)
                                 for method in methods}
                  for contest in sorted({row["cf_contest"] for row in flat})}
    by_region = {region: {method: rmse([row for row in flat if row["region"] == region], method)
                          for method in methods}
                 for region in sorted({row["region"] for row in flat})}
    return flat, methods, {method: rmse(flat, method) for method in methods}, by_contest, by_region


def _sha(path):
    with open(path, "rb") as source:
        return hashlib.sha256(source.read()).hexdigest()


def run_ablation(rows=None, output_path=None, progress=False):
    """Run the two frozen exploratory development protocols."""
    rows = build_anchor_table() if rows is None else [dict(row) for row in rows]
    if len(rows) != 185 or len({row["cf_contest"] for row in rows}) != 15:
        raise RuntimeError("expected exactly 185 anchors from 15 CF contests")
    if not np.isfinite(_matrix(rows, "DET")).all() or not np.isfinite([row["cf"] for row in rows]).all():
        raise RuntimeError("non-finite anchor feature or label")
    regions = sorted({row["region"] for row in rows})
    if len(regions) != 3:
        raise RuntimeError("expected exactly three anchor regions")
    shape = _gym_shape(_load_json(os.path.join(os.path.dirname(__file__), os.pardir,
                                               "output", "problem_ratings_survival.json")))
    if shape is None:
        raise RuntimeError("locked gym shape unavailable")
    # Freeze the plan/source/input provenance before any outer candidate runs.
    paths = [TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP,
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "problem_ratings_survival.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "problem_ratings_b.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "gym_difficulty.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "data", "cf_problemset.json"), PLAN,
             os.path.join(os.path.dirname(__file__), os.pardir, "data", "cf_team_contests.txt"),
             os.path.join(os.path.dirname(__file__), "calibration_experiment.py"), __file__]
    paths.append(os.path.join(os.path.dirname(__file__), os.pardir, "output",
                              "calibration_experiment.json"))
    provenance = {os.path.relpath(path): _sha(path) for path in paths}
    protocols = {}
    contest_folds = {}
    for contest in sorted({row["cf_contest"] for row in rows}):
        held = [row for row in rows if row["cf_contest"] == contest]
        contest_folds[str(contest)] = _fold_result(rows, held, contest, shape)
        if progress:
            print(f"completed CF contest {contest}", flush=True)
    protocols["leave_one_cf_contest_out"] = {"folds": contest_folds}
    region_folds = {}
    for region in regions:
        held = [row for row in rows if row["region"] == region]
        region_folds[region] = _fold_result(rows, held, region, shape)
        if progress:
            print(f"completed region {region}", flush=True)
    protocols["leave_one_region_out"] = {"folds": region_folds}
    for protocol in protocols.values():
        flat, methods, metrics, by_contest, by_region = _metrics(protocol["folds"])
        protocol.update({"anchor_coverage": len(flat), "methods": methods,
                         "metrics_rmse": metrics, "per_cf_contest_rmse": by_contest,
                         "per_region_rmse": by_region})
    control = protocols["leave_one_cf_contest_out"]["metrics_rmse"]["ridge_DET"]
    if not np.isclose(control, CONTROL_DET_RMSE, rtol=0, atol=1e-7):
        raise RuntimeError(f"DET control mismatch: {control:.10f} != {CONTROL_DET_RMSE:.10f}")
    full_selection = select_full_anchors(rows)
    result = {"research_only": True, "independent_confirmation": False,
              "not_for_production_promotion": True,
              "config": {"bundles": {bundle: bundle_features(bundle) for bundle in BUNDLES},
                         "ridge_alphas": RIDGE_ALPHAS, "lambdas": LAMDAS,
                         "residual_baseline": "raw_affine",
                         "protocols": "exploratory_development_not_fresh_confirmation"},
              "provenance_sha256": provenance,
              "protocols": protocols,
              "full_anchor_selection_not_oof_not_deployment": full_selection}
    if output_path:
        with open(output_path, "w") as destination:
            json.dump(result, destination, indent=2)
    return result


def main():
    result = run_ablation(output_path=OUT, progress=True)
    print(json.dumps({name: value["metrics_rmse"] for name, value in result["protocols"].items()},
                     sort_keys=True))


if __name__ == "__main__":
    main()
