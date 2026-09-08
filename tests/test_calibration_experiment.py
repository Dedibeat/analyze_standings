import os
import sys
import types
import unittest
from unittest import mock

import numpy as np

import arch_b.calibration_experiment as calibration_experiment
from arch_b.calibration_experiment import (FEATURES, _affine, _matrix,
                                           _default_tabfm_predictor,
                                           build_anchor_table, run_experiment)
from arch_b.calibrate import _anchors, _gym_shape, _loco_rmse


def _rows(include_shared_task=False):
    rows = []
    for contest in range(1, 5):
        for problem in range(3):
            raw_b = 1100.0 + 150.0 * contest + problem
            rows.append({
                "row_id": f"{contest}-{problem}",
                "cf_contest": contest,
                "contest_id": 100 + contest,
                "problem_id": 1000 + 10 * contest + problem,
                "problem_label": chr(ord("A") + problem),
                "cf": 1.7 * raw_b + 30.0 + problem,
                "raw_b": raw_b,
                "binary_minus_survival": float(problem - 1),
                "conditional_fit_se": 10.0 + problem,
                "solve_rate": (problem + 1) / 4.0,
                "log_field_size": 4.0,
                "log_median_solve_seconds": 5.0 + problem,
                "timing_missing": float(problem == 2),
            })
    if include_shared_task:
        rows[0]["canonical_task"] = "shared"
        rows[3]["canonical_task"] = "shared"
    return rows


class CalibrationExperimentTest(unittest.TestCase):
    def test_outer_heldout_labels_do_not_change_its_predictions_or_selection(self):
        rows = _rows()

        def fake_tabfm(train_x, train_y, test_x):
            # A deterministic, target-sensitive adapter makes the optional path
            # testable on CPU while exposing target leakage.
            value = np.dot(train_x[:, 1], train_y) / (100.0 * len(train_y))
            return np.full(len(test_x), value)

        before = run_experiment(rows, tabfm_predictor=fake_tabfm)
        changed = [dict(row) for row in rows]
        for row in changed:
            if row["cf_contest"] == 1:
                row["cf"] += 100000.0
        after = run_experiment(changed, tabfm_predictor=fake_tabfm)

        self.assertEqual(before["selected_by_outer_contest"]["1"],
                         after["selected_by_outer_contest"]["1"])
        for old, new in zip(before["folds"]["1"]["predictions"],
                            after["folds"]["1"]["predictions"]):
            self.assertEqual(old["row_id"], new["row_id"])
            for method in ("raw_affine", "gym_shape_affine", "ridge_residual",
                           "tabfm_residual"):
                self.assertAlmostEqual(old[method], new[method])

    def test_inner_context_excludes_outer_labels_and_shared_canonical_task(self):
        rows = _rows(include_shared_task=True)
        calls = []

        def fake_tabfm(train_x, train_y, test_x):
            calls.append((np.array(train_x), np.array(train_y), np.array(test_x)))
            return np.full(len(test_x), np.dot(train_x[:, 1], train_y) / 100.0)

        run_experiment(rows, tabfm_predictor=fake_tabfm)
        by_raw_b = {row["raw_b"]: row for row in rows}
        for train_x, train_y, _test_x in calls:
            train = [by_raw_b[value] for value in train_x[:, 0]]
            expected = np.array([row["cf"] for row in train]) - _affine(train, train, None)
            np.testing.assert_allclose(train_y, expected)
        self.assertTrue(any(abs(np.dot(x[:, 1], y)) > 1e-8 for x, y, _ in calls))
        # raw_b is the first prespecified feature and uniquely identifies these rows.
        outer_one_calls = [call for call in calls if np.any(call[2][:, 0] == 1250.0)]
        self.assertTrue(outer_one_calls)
        for train_x, _train_y, _test_x in outer_one_calls:
            self.assertFalse(np.any(train_x[:, 0] == 1250.0))
            # Contest 2's occurrence of the canonical shared task is excluded too.
            self.assertFalse(np.any(train_x[:, 0] == 1400.0))

    def test_features_are_aligned_and_required_values_are_not_defaulted(self):
        row = _rows()[0]
        self.assertEqual(_matrix([row]).shape, (1, len(FEATURES)))
        np.testing.assert_allclose(_matrix([row])[0], [row[name] for name in FEATURES])
        missing = dict(row)
        missing.pop("conditional_fit_se")
        with self.assertRaises(KeyError):
            _matrix([missing])

    def test_nonfinite_optional_predictor_is_rejected(self):
        with self.assertRaises(ValueError):
            run_experiment(_rows(), tabfm_predictor=lambda _x, _y, test_x:
                           np.full(len(test_x), np.nan))

    def test_missing_pinned_checkpoint_fails_before_tabfm_load(self):
        fake_tabfm = types.ModuleType("tabfm")
        fake_tabfm.__version__ = "test"
        fake_loader = mock.Mock()
        fake_tabfm.TabFMRegressor = object
        fake_tabfm.tabfm_v1_0_0_pytorch = types.SimpleNamespace(load=fake_loader)
        with mock.patch.dict(os.environ, {"TABFM_CHECKPOINT_DIR": ""}), \
             mock.patch.dict(sys.modules, {"tabfm": fake_tabfm}), \
             mock.patch.object(calibration_experiment, "_TABFM_MODEL", None), \
             mock.patch.object(calibration_experiment, "_TABFM_BACKEND", None):
            with self.assertRaisesRegex(RuntimeError, "TABFM_CHECKPOINT_DIR"):
                _default_tabfm_predictor(np.zeros((1, len(FEATURES))), np.zeros(1),
                                         np.zeros((1, len(FEATURES))))
        fake_loader.assert_not_called()

    def test_anchor_table_has_unique_raw_provenance_and_complete_features(self):
        rows = build_anchor_table()
        self.assertEqual(len(rows), 185)
        self.assertEqual(len({row["cf_contest"] for row in rows}), 15)
        self.assertEqual(len({row["row_id"] for row in rows}), len(rows))
        self.assertTrue(np.isfinite(_matrix(rows)).all())
        self.assertTrue(all("difficulty_cf" not in key for row in rows for key in row))

    def test_locked_raw_and_gym_controls_reproduce_documented_loco(self):
        with open("output/problem_ratings_survival.json") as f:
            records = __import__("json").load(f)
        raw, cf, groups = _anchors(records)
        shape = _gym_shape(records)
        self.assertIsNotNone(shape)
        self.assertAlmostEqual(_loco_rmse(raw, cf, groups), 246.9061, places=4)
        self.assertAlmostEqual(_loco_rmse(shape(raw), cf, groups), 245.4277, places=4)


if __name__ == "__main__":
    unittest.main()
