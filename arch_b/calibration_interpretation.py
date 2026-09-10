"""Explain existing DE/TabFM predictions; no new candidate or backend search."""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from arch_a.elo import S
from .calibration_ablation import _purged_train, bundle_features, fit_predict_fixed
from .calibration_audit import verify_provenance
from .calibration_experiment import _affine, _file_sha256, build_anchor_table
from .model import MU0, SIGMA_B

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output/calibration_interpretation.json"
FEATURES = bundle_features("DE")


def _matrix(rows):
    return np.array([[row[feature] for feature in FEATURES] for row in rows])


def _decomposition(train, setting):
    x = _matrix(train)
    mean, scale = x.mean(0), x.std(0)
    scale[scale == 0] = 1
    design = np.column_stack((np.ones(len(x)), (x - mean) / scale))
    residual = np.array([row["cf"] for row in train]) - _affine(train, train, None)
    penalty = np.diag([0.0] + [setting["alpha"]] * len(FEATURES))
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ residual)
    return mean, scale, coef * setting["lambda"]


def run():
    files = ("output/calibration_audit.json", "output/calibration_ablation.json",
             "output/calibration_tabfm_bigquery.json", "output/shipped_fit_audit.json")
    audit, ablation, managed, readiness = [json.loads((ROOT / name).read_text()) for name in files]
    verify_provenance(readiness)
    anchors = build_anchor_table()
    setting = ablation["full_anchor_selection_not_oof_not_deployment"]["fixed"]["DE"]
    mean, scale, coef = _decomposition(anchors, setting)
    full = audit["full_refit_not_oof"]["rows"]
    contributions = (_matrix(full) - mean) / scale * coef[1:]
    reconstructed = _affine(anchors, full, None) + coef[0] + contributions.sum(1)
    expected = np.array([row["ridge_DE"] for row in full])
    direct = fit_predict_fixed(anchors, full, "DE", setting["alpha"], setting["lambda"])
    if not np.allclose(reconstructed, expected, rtol=0, atol=1e-7) or not np.allclose(
            reconstructed, direct, rtol=0, atol=1e-7):
        raise RuntimeError("DE coefficient decomposition does not reproduce predictions")
    fold_coefs = []
    for contest, fold in ablation["protocols"]["leave_one_cf_contest_out"]["folds"].items():
        train = _purged_train(anchors, [row for row in anchors if row["cf_contest"] == int(contest)])
        fold_coefs.append(_decomposition(train, fold["selected"]["fixed"]["DE"])[2][1:])
    fold_coefs = np.array(fold_coefs)
    examples = []
    for i, row in enumerate(full):
        if (row["contest_id"], row["problem_label"]) in ((1965, "H"), (1965, "L")) or (
                row["contest_id"] in (1661, 1662) and row["problem_id"] == 8674):
            examples.append({"row_id": row["row_id"], "name": row["problem_name"],
                             "features": {name: row[name] for name in FEATURES},
                             "contributions_from_anchor_mean": dict(zip(FEATURES, contributions[i].tolist())),
                             **{name: row[name] for name in ("raw_affine", "gym_shape_affine", "ridge_DE")}})

    # At an interior, unweighted survival MAP: sum(Lambda) = solves + s*(b-mu)/sigma_b^2.
    solves = np.array([row["solve_rate"] * np.expm1(row["log_field_size"]) for row in full])
    b = np.array([row["raw_b"] for row in full])
    se = np.array([row["conditional_fit_se"] for row in full])
    derived_se = (solves / S**2 + (b - MU0) / (S * SIGMA_B**2) + 1 / SIGMA_B**2) ** -.5
    oof = managed["predictions"]
    correction = {name: np.array([row[name] - row["raw_affine"] for row in oof])
                  for name in ("ridge_DE", "tabfm_residual")}
    groups = sorted({row["cf_contest"] for row in oof})
    group = np.array([row["cf_contest"] for row in oof])
    group_mean = np.array([correction["ridge_DE"][group == g].mean() for g in group])
    counts = np.array([sum(group == g) for g in groups])
    # Descriptive paired contest bootstrap of fixed saved predictions, not refitting
    # or adjusting for candidate selection on these reused labels.
    seed, repeats = 20260910, 20000
    indices = np.random.default_rng(seed).integers(0, len(groups), (repeats, len(groups)))
    bootstrap = {}
    for left, right in (("ridge_DE", "gym_shape_affine"), ("ridge_DE", "tabfm_residual"),
                        ("ridge_DET", "tabfm_residual")):
        sse = np.array([[sum((row[method] - row["cf"]) ** 2 for row in oof if row["cf_contest"] == g)
                         for g in groups] for method in (left, right)])
        scores = np.sqrt(sse[:, indices].sum(2) / counts[indices].sum(1))
        bootstrap[f"{left}_minus_{right}"] = {
            "percentiles_2_5_50_97_5": np.quantile(scores[0] - scores[1], [.025, .5, .975]).tolist()}
    paths = {ROOT / name for name in files} | {Path(__file__)}
    paths.update(ROOT / name for name in ("arch_a/elo.py", "arch_b/model.py", "arch_b/survival.py"))
    paths.update(ROOT / name for name in readiness["provenance_sha256"])
    result = {
        "research_only": True, "new_model_search": False, "fresh_confirmation": False,
        "coefficient_contributions_are_algebra_not_causal_attribution": True,
        "features": FEATURES, "affine_slope_intercept": np.polyfit(
            [row["raw_b"] for row in anchors], [row["cf"] for row in anchors], 1).tolist(),
        "coefficients": {name: {"mean": float(mean[i]), "sd": float(scale[i]),
                                "per_sd": float(coef[i + 1]), "per_unit": float(coef[i + 1] / scale[i]),
                                "outer_per_sd_range": [float(fold_coefs[:, i].min()), float(fold_coefs[:, i].max())]}
                         for i, name in enumerate(FEATURES)},
        "residual_intercept": float(coef[0]), "anchor_feature_correlation": np.corrcoef(_matrix(anchors).T).tolist(),
        "full_prediction_reconstruction_max_error": float(abs(reconstructed - expected).max()),
        "examples": examples,
        "conditional_se_identity": {"max_absolute_difference": float(abs(derived_se - se).max()),
                                    "median_absolute_difference": float(np.median(abs(derived_se - se))),
                                    "correlation": float(np.corrcoef(derived_se, se)[0, 1])},
        "full_mean_contribution": dict(zip(FEATURES, contributions.mean(0).tolist())),
        "full_mean_de_minus_raw": float(np.mean([row["ridge_DE"] - row["raw_affine"] for row in full])),
        "full_mean_raw_minus_gym": float(np.mean([row["raw_affine"] - row["gym_shape_affine"] for row in full])),
        "oof_de_correction_between_contest_variance_fraction": float(np.var(group_mean) / np.var(correction["ridge_DE"])),
        "oof_correction_correlation_de_tabfm": float(np.corrcoef(*correction.values())[0, 1]),
        "oof_correction_sd": {name: float(values.std()) for name, values in correction.items()},
        "tabfm_selected_lambda_counts": dict(Counter(str(value["tabfm_lambda"]) for value in
                                                     managed["selected_by_outer_contest"].values())),
        "fixed_prediction_contest_bootstrap": {"seed": seed, "resamples": repeats, "results": bootstrap,
                                              "accounts_for_model_selection_or_refitting": False},
        "provenance_sha256": {str(path.relative_to(ROOT)): _file_sha256(path) for path in sorted(paths)},
    }
    verify_provenance(result)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({name: result[name] for name in (
        "coefficients", "conditional_se_identity", "fixed_prediction_contest_bootstrap")}, indent=2))
