import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from arch_b.calibration_audit import (
    _predictions, _support, influence_fold, select_examples, verify_provenance,
)
from arch_b.calibration_experiment import _file_sha256


def _rows():
    rows = []
    for contest in range(6):
        for problem in range(4):
            raw = 1000.0 + 100 * contest + 200 * problem
            disagreement = float((contest + problem) % 3)
            rows.append({
                "row_id": f"{contest}:{problem}", "cf_contest": contest,
                "canonical_task": "shared" if (contest, problem) in ((0, 0), (2, 0))
                else f"task:{contest}:{problem}",
                "raw_b": raw, "binary_minus_survival": disagreement,
                "conditional_fit_se": 2.0 + problem, "solve_rate": (4 - problem) / 5,
                "log_field_size": 4.0 + contest / 10,
                "cf": 1.5 * raw + 70 * disagreement + 10 * contest,
            })
    return rows


def _signature(fold):
    return {**fold, "predictions": [
        {key: value for key, value in row.items() if key != "cf"}
        for row in fold["predictions"]]}


class CalibrationAuditTest(unittest.TestCase):
    def test_excluded_and_outer_held_labels_cannot_affect_fit_or_selection(self):
        rows = _rows()
        before = influence_fold(rows, excluded_contest=0, held_contest=1)
        changed = [dict(row) for row in rows]
        for row in changed:
            # Also perturb the excluded contest's task duplicate elsewhere.
            if row["cf_contest"] in (0, 1) or row["canonical_task"] == "shared":
                row["cf"] += 1_000_000
        after = influence_fold(changed, excluded_contest=0, held_contest=1)
        self.assertEqual(_signature(before), _signature(after))

    def test_canonical_tasks_are_purged_at_excluded_and_outer_boundaries(self):
        rows = _rows()
        rows[3 * 4]["canonical_task"] = rows[1 * 4]["canonical_task"]
        fold = influence_fold(rows, excluded_contest=0, held_contest=1)
        train = set(fold["training_rows"])
        self.assertNotIn("2:0", train)  # excluded-contest shared task
        self.assertNotIn("3:0", train)  # held-contest shared task
        self.assertFalse(any(row_id.startswith(("0:", "1:")) for row_id in train))
        held_duplicate = influence_fold(rows, excluded_contest=0, held_contest=2)
        self.assertNotIn("2:0", held_duplicate["held_rows"])

    def test_top_examples_are_permutation_invariant_and_keep_overlap_reasons(self):
        rows = [
            {"row_id": "b", "raw_affine": 0, "ridge_DE": 10, "cf": 10},
            {"row_id": "a", "raw_affine": 0, "ridge_DE": 10, "cf": 0},
            {"row_id": "c", "raw_affine": 0, "ridge_DE": 0, "cf": 0},
        ]
        result = select_examples(rows, count=2)
        self.assertEqual(result, select_examples(rows[::-1], count=2))
        self.assertEqual(result["lists"], {
            "largest_correction": ["a", "b"],
            "largest_improvement": ["b"], "largest_deterioration": ["a"],
        })
        self.assertEqual(result["unique_rows"][0], {
            "row_id": "a", "reasons": ["largest_correction", "largest_deterioration"]})
        unlabeled = [{k: v for k, v in row.items() if k != "cf"} for row in rows]
        self.assertEqual(list(select_examples(unlabeled, False)["lists"]), ["largest_correction"])

    def test_support_uses_training_feature_range_only(self):
        rows = _rows()
        held = dict(rows[-1], raw_b=100_000)
        self.assertEqual(_support(held, rows)["raw_b"], [1000.0, 2100.0])

    def test_stale_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text("[]")
            saved = {"provenance_sha256": {source.name: _file_sha256(source)}}
            verify_provenance(saved, root)
            source.write_text("[1]")
            with self.assertRaisesRegex(RuntimeError, "stale saved provenance"):
                verify_provenance(saved, root)

    def test_nonfinite_control_predictions_are_rejected(self):
        rows = _rows()
        with patch("arch_b.calibration_audit._affine", return_value=np.array([np.nan])):
            with self.assertRaisesRegex(RuntimeError, "non-finite"):
                _predictions(rows[1:], rows[:1], None, {"alpha": 1, "lambda": 1})


if __name__ == "__main__":
    unittest.main()
