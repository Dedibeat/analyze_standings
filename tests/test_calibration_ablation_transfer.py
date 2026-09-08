import unittest

import numpy as np

from arch_b.calibration_ablation_transfer import _metric_rows, _solve_count_sanity


class CalibrationAblationTransferTest(unittest.TestCase):
    def test_solve_count_sanity_excludes_constant_contest_and_keeps_valid_one(self):
        rows = [
            {"contest_id": 1, "problem_label": label} for label in "ABC"
        ] + [
            {"contest_id": 2, "problem_label": label} for label in "ABC"
        ]
        for index, row in enumerate(rows):
            row["index"] = index
        records = [
            {"contest_id": 1, "problem_label": label, "solved_count": 2}
            for label in "ABC"
        ] + [
            {"contest_id": 2, "problem_label": label, "solved_count": solved}
            for label, solved in zip("ABC", (3, 2, 1))
        ]
        result = _solve_count_sanity(records, rows, {"method": np.array([1, 2, 3, 1, 2, 3.])})
        self.assertEqual(result, {"method": 1.0})

    def test_solve_count_sanity_rejects_no_valid_contest(self):
        rows = [{"contest_id": 1, "problem_label": label, "index": index}
                for index, label in enumerate("ABC")]
        records = [{"contest_id": 1, "problem_label": label, "solved_count": 2}
                   for label in "ABC"]
        with self.assertRaisesRegex(RuntimeError, "no valid solve-count"):
            _solve_count_sanity(records, rows, {"method": np.array([1., 2., 3.])})

    def test_proxy_metrics_reject_nonfinite_result(self):
        rows = [{"index": index} for index in range(3)]
        with self.assertRaisesRegex(RuntimeError, "non-finite cached proxy"):
            _metric_rows([(row, 2.0) for row in rows],
                         {"method": np.array([1., 2., 3.])}, "spearman")


if __name__ == "__main__":
    unittest.main()
