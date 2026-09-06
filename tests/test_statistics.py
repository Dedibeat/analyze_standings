import unittest

import numpy as np

from arch_b.aoj import spearman
from arch_b.metric import (EXPECTED_ANCHOR_CONTESTS, EXPECTED_ANCHOR_PROBLEMS,
                           GUARDS, _guard_failures)
from arch_b.model import _require_converged
from arch_b.predict_eval import _grouped_test_mask, _metrics
from arch_b.external_validate import _kattis_matches
from llm_crosscontest import _predict_heldout_contest


class StatisticsTest(unittest.TestCase):
    def test_spearman_uses_average_ranks_for_ties(self):
        value = spearman([0, 0, 1, 1], [0, 1, 2, 3])
        self.assertAlmostEqual(value, 0.8944271909999159)
        self.assertAlmostEqual(
            value, spearman([1, 1, 0, 0], [3, 2, 1, 0]))

    def test_auc_is_half_when_predictions_are_tied(self):
        self.assertAlmostEqual(_metrics([0, 1], [0.5, 0.5])[2], 0.5)
        self.assertAlmostEqual(_metrics([1, 0], [0.5, 0.5])[2], 0.5)

    def test_response_group_split_keeps_duplicate_keys_together(self):
        team = np.array([0, 0, 1, 1, 1])
        problem = np.array([2, 2, 2, 3, 3])
        test = _grouped_test_mask(team, problem, seed=4, test_frac=0.5)
        self.assertEqual(test[0], test[1])
        self.assertEqual(test[3], test[4])

    def test_metric_guards_reject_nonfinite_values_and_wrong_coverage(self):
        passing = {name: floor for name, floor in GUARDS.items()}
        coverage = (EXPECTED_ANCHOR_PROBLEMS, EXPECTED_ANCHOR_CONTESTS)
        self.assertEqual(_guard_failures(passing, 250.0, 245.0, coverage), [])

        bad = dict(passing)
        bad["gym_ec_spearman"] = np.nan
        failures = _guard_failures(bad, np.nan, np.inf, (184, 15))
        self.assertEqual(
            set(failures),
            {"gym_ec_spearman", "raw_loco_cf_rmse",
             "calibrated_loco_cf_rmse", "anchor_coverage"},
        )

    def test_fit_convergence_guard_rejects_nonfinite_and_limited_runs(self):
        _require_converged(np.array([2000.0]), np.array([2100.0]), [0.4], 0.5)
        with self.assertRaises(RuntimeError):
            _require_converged(np.array([np.nan]), np.array([2100.0]), [0.4], 0.5)
        with self.assertRaises(RuntimeError):
            _require_converged(np.array([2000.0]), np.array([2100.0]), [0.5], 0.5)

    def test_survival_duration_can_be_derived_from_training_events_only(self):
        ds = type("Dataset", (), {
            "team_of_row": np.array([0, 1]),
            "obs_row": np.array([0, 1]),
            "obs_prob": np.array([0, 0]),
            "obs_y": np.array([True, True]),
            "obs_tau": np.array([100.0, 200.0]),
            "contest_of_problem": np.array([0]),
            "contests": [1],
        })()
        from arch_b.survival import _survival_observations

        rho = _survival_observations(ds, duration_mask=[True, False])[3]
        np.testing.assert_allclose(rho, [1.0, 2.0])

    def test_llm_heldout_prediction_does_not_read_heldout_labels(self):
        z = np.array([1.0, 2.0, 2.0, 3.0, 4.0, 5.0])
        bt = np.array([1.2, 1.8, 2.4, 2.8, 4.5, 4.7])
        cf = np.array([1000.0, 1300.0, 1400.0, 1700.0, 2100.0, 2400.0])
        groups = np.array([1, 1, 2, 2, 3, 3])

        before = _predict_heldout_contest(z, bt, cf, groups, 3)[:2]
        changed = cf.copy()
        changed[groups == 3] += 10000.0
        after = _predict_heldout_contest(z, bt, changed, groups, 3)[:2]

        np.testing.assert_allclose(before[0], after[0])
        np.testing.assert_allclose(before[1], after[1])

    def test_kattis_join_rejects_title_collisions_and_isolated_matches(self):
        artifact = {
            "a": {"name": "Alpha", "difficulty": 1},
            "b": {"name": "Beta", "difficulty": 2},
            "c": {"name": "Gamma", "difficulty": 3},
            "dup1": {"name": "Shared", "difficulty": 4},
            "dup2": {"name": "Shared!", "difficulty": 5},
            "lonely": {"name": "Lonely", "difficulty": 6},
        }
        contests = [
            {"contest_id": 1, "problems": [
                {"problem_name": "Alpha"}, {"problem_name": "Beta"},
                {"problem_name": "Gamma"}, {"problem_name": "Shared"},
            ]},
            {"contest_id": 2, "problems": [{"problem_name": "Lonely"}]},
        ]

        matches = _kattis_matches(contests, artifact)

        self.assertEqual(set(matches), {(1, "alpha"), (1, "beta"), (1, "gamma")})


if __name__ == "__main__":
    unittest.main()
