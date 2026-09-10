import copy
import json
import tempfile
import unittest
from pathlib import Path

from arch_b.shipped_fit_audit import FEATURES, METHODS, _metrics, replay_tabfm


class ShippedFitAuditTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.archive = Path(self.directory.name)
        rows = [{"row_id": str(i), "cf_contest": i, "cf": 100.0 + i,
                 **{name: 1.0 for name in FEATURES}} for i in range(2)]
        calls = []
        for outer in range(2):
            for inner, index in ((1 - outer, 1 - outer), (None, outer)):
                call_id = f"{outer}_{inner}"
                calls.append({"call_id": call_id, "outer_contest": outer,
                              "inner_contest": inner, "prediction_rows": [index],
                              "baseline": {index: rows[index]["cf"] - 10}})
                (self.archive / f"{call_id}.json").write_text(json.dumps({str(index): 20.0}))
        self.manifest = {"rows": rows, "calls": calls}
        predictions = [{"row_id": row["row_id"], "cf_contest": row["cf_contest"],
                        "cf": row["cf"], "features": {name: row[name] for name in FEATURES},
                        **{method: row["cf"] for method in METHODS}} for row in rows]
        self.saved = {"predictions": predictions,
                      "selected_by_outer_contest": {str(i): {"tabfm_lambda": .5, "inner_mse": 0.0}
                                                    for i in range(2)},
                      "metrics": {method: _metrics(predictions, method) for method in METHODS}}

    def test_offline_replay_recovers_inner_selection_and_outer_predictions(self):
        result = replay_tabfm(self.manifest, self.saved, self.archive)
        self.assertEqual(result["selected_lambdas"], {"0": .5, "1": .5})
        self.assertEqual(result["max_prediction_replay_error"], 0)

    def test_missing_archive_fails_instead_of_invoking_a_backend(self):
        (self.archive / "0_None.json").unlink()
        with self.assertRaises(FileNotFoundError):
            replay_tabfm(self.manifest, self.saved, self.archive)

    def test_extra_prediction_id_and_nonfinite_response_are_rejected(self):
        for response in ({"0": 20.0, "99": 20.0}, {"0": float("nan")}):
            with self.subTest(response=response):
                (self.archive / "0_None.json").write_text(json.dumps(response))
                with self.assertRaisesRegex(RuntimeError, "invalid archived prediction rows"):
                    replay_tabfm(self.manifest, self.saved, self.archive)

    def test_corrupt_outer_prediction_is_rejected(self):
        (self.archive / "0_None.json").write_text('{"0": 200.0}')
        with self.assertRaisesRegex(RuntimeError, "TabFM outer row"):
            replay_tabfm(self.manifest, self.saved, self.archive)

    def test_corrupt_selection_metric_and_duplicate_identity_are_rejected(self):
        for defect in ("selection", "metric", "duplicate"):
            with self.subTest(defect=defect):
                saved = copy.deepcopy(self.saved)
                if defect == "selection":
                    saved["selected_by_outer_contest"]["0"]["tabfm_lambda"] = 1
                elif defect == "metric":
                    saved["metrics"]["tabfm_residual"]["rmse"] = 100
                else:
                    saved["predictions"].append(saved["predictions"][0])
                with self.assertRaises(RuntimeError):
                    replay_tabfm(self.manifest, saved, self.archive)


if __name__ == "__main__":
    unittest.main()
