import json
import unittest

import numpy as np

from arch_b.calibration_ablation import (
    BUNDLES,
    CONTROL_DET_RMSE,
    _fold_result,
    _matrix,
    _purged_train,
    bundle_features,
    fit_predict_fixed,
    run_ablation,
)


def _rows():
    """Small, complete rows for fit-context tests (not a main-run fixture)."""
    rows = []
    for contest in range(1, 10):
        region = ("Asia", "Europe", "North")[((contest - 1) // 3)]
        for problem in range(4):
            raw = 1000.0 + 100.0 * contest + problem
            disagreement = float(problem - 1.5)
            evidence = float((contest + problem) % 3 - 1)
            timing = float(problem % 2)
            rows.append({
                "row_id": f"{contest}-{problem}", "cf_contest": contest,
                "contest_id": 100 + contest, "problem_id": 1000 + 10 * contest + problem,
                "problem_label": chr(ord("A") + problem),
                "canonical_task": "shared" if (contest, problem) in ((1, 0), (4, 0))
                else f"task-{contest}-{problem}",
                "region": region, "raw_b": raw,
                "binary_minus_survival": disagreement,
                "conditional_fit_se": 5.0 + evidence,
                "solve_rate": (problem + 1.0) / 5.0,
                "log_field_size": 4.0 + (contest % 2),
                "log_median_solve_seconds": 5.0 + timing,
                "timing_missing": timing,
                "cf": 1.6 * raw + 90.0 * disagreement + 35.0 * evidence + 20.0 * timing,
            })
    return rows


def _fold_signature(fold):
    return {
        "selected": fold["selected"],
        "training_rows": fold["training_rows"],
        "predictions": [(row["row_id"], tuple(sorted(
            (key, value) for key, value in row.items()
            if key.startswith("ridge_") or key.endswith("affine"))))
                        for row in fold["predictions"]],
    }


class CalibrationAblationTest(unittest.TestCase):
    def test_fixed_bundles_have_only_raw_plus_their_declared_groups(self):
        self.assertEqual(BUNDLES, ("D", "E", "T", "DE", "DT", "ET", "DET"))
        self.assertEqual(bundle_features("D"), ("raw_b", "binary_minus_survival"))
        self.assertEqual(bundle_features("E"),
                         ("raw_b", "conditional_fit_se", "solve_rate", "log_field_size"))
        self.assertEqual(bundle_features("T"),
                         ("raw_b", "log_median_solve_seconds", "timing_missing"))
        self.assertEqual(bundle_features("DET"),
                         ("raw_b", "binary_minus_survival", "conditional_fit_se",
                          "solve_rate", "log_field_size", "log_median_solve_seconds",
                          "timing_missing"))

    def test_held_row_ids_and_canonical_tasks_are_purged_by_stable_identity(self):
        rows = _rows()
        held = [dict(row) for row in rows if row["cf_contest"] == 1]
        # A copied held row with a changed target must still identify the same held row.
        held[1]["cf"] += 1_000_000.0  # Its canonical task is unique.
        train = _purged_train(rows, held)
        self.assertFalse({row["row_id"] for row in held} & {row["row_id"] for row in train})
        self.assertNotIn("shared", {row["canonical_task"] for row in train})

    def test_outer_contest_labels_cannot_change_predictions_or_feature_selection(self):
        rows = _rows()
        held = [row for row in rows if row["cf_contest"] == 1]
        before = _fold_result(rows, held, 1, None)
        changed = [dict(row) for row in rows]
        for row in changed:
            if row["cf_contest"] == 1:
                row["cf"] += 1_000_000.0
        after = _fold_result(changed, [row for row in changed if row["cf_contest"] == 1], 1, None)
        self.assertEqual(_fold_signature(before), _fold_signature(after))

    def test_held_region_labels_cannot_change_predictions_or_feature_selection(self):
        rows = _rows()
        held = [row for row in rows if row["region"] == "Asia"]
        before = _fold_result(rows, held, "Asia", None)
        changed = [dict(row) for row in rows]
        for row in changed:
            if row["region"] == "Asia":
                row["cf"] -= 1_000_000.0
        after = _fold_result(changed, [row for row in changed if row["region"] == "Asia"], "Asia", None)
        self.assertEqual(_fold_signature(before), _fold_signature(after))

    def test_required_feature_and_finite_guards_are_enforced(self):
        rows = _rows()
        broken = dict(rows[0])
        broken.pop("solve_rate")
        with self.assertRaises(KeyError):
            _matrix([broken], "E")
        nonfinite = [dict(row) for row in rows]
        nonfinite[0]["binary_minus_survival"] = np.nan
        with self.assertRaises(ValueError):
            fit_predict_fixed(nonfinite[1:], nonfinite[:1], "D", 1.0, 1.0)

    def test_det_matches_frozen_baseline_per_anchor_and_selection(self):
        result = run_ablation()
        with open("output/calibration_experiment.json") as source:
            old = json.load(source)
        folds = result["protocols"]["leave_one_cf_contest_out"]["folds"]
        for contest, fold in folds.items():
            expected = old["folds"][contest]
            self.assertEqual(fold["selected"]["fixed"]["DET"]["alpha"],
                             expected["selected"]["ridge_alpha"])
            self.assertEqual(fold["selected"]["fixed"]["DET"]["lambda"],
                             expected["selected"]["ridge_lambda"])
            previous = {row["row_id"]: row["ridge_residual"] for row in expected["predictions"]}
            for row in fold["predictions"]:
                self.assertAlmostEqual(row["ridge_DET"], previous[row["row_id"]], places=10)
        self.assertAlmostEqual(
            result["protocols"]["leave_one_cf_contest_out"]["metrics_rmse"]["ridge_DET"],
            CONTROL_DET_RMSE, places=7)


if __name__ == "__main__":
    unittest.main()
