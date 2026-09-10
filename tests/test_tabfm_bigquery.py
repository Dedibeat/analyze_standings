import tempfile
import unittest
from pathlib import Path

from arch_b.calibration_experiment import build_anchor_table
from arch_b.tabfm_bigquery import FEATURES, SubmissionLedger, build_manifest, inference_sql


class TabFMBigQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_anchor_table()
        cls.manifest = build_manifest(cls.rows)

    def test_manifest_has_frozen_nested_call_count_and_no_duplicate_query_keys(self):
        self.assertEqual(len(self.manifest["calls"]), 225)
        self.assertEqual(len({call["call_id"] for call in self.manifest["calls"]}), 225)
        self.assertEqual(len({(row["call_id"], row["prediction_row"])
                              for row in self.manifest["queries"]}), len(self.manifest["queries"]))
        sql = inference_sql("p", "d")
        self.assertIn("SELECT " + ", ".join(FEATURES) + ", CAST(residual AS FLOAT64)", sql)
        self.assertIn("SELECT prediction_row, " + ", ".join(FEATURES), sql)

    def test_outer_held_labels_do_not_change_that_outer_context_or_queries(self):
        outer = self.rows[0]["cf_contest"]
        changed = [dict(row) for row in self.rows]
        for row in changed:
            if row["cf_contest"] == outer:
                row["cf"] += 1_000_000
        after = build_manifest(changed)
        old_ids = {call["call_id"] for call in self.manifest["calls"] if call["outer_contest"] == outer}
        new_ids = {call["call_id"] for call in after["calls"] if call["outer_contest"] == outer}
        self.assertEqual(old_ids, new_ids)
        for key in ("contexts", "queries"):
            before_rows = [row for row in self.manifest[key] if row["call_id"] in old_ids]
            after_rows = [row for row in after[key] if row["call_id"] in old_ids]
            self.assertEqual(before_rows, after_rows)

    def test_task_purge_and_ledger_resume_are_enforced(self):
        call = next(call for call in self.manifest["calls"] if call["inner_contest"] is not None)
        held = [row for row in self.rows if row["cf_contest"] in (call["outer_contest"], call["inner_contest"])]
        held_tasks = {row["canonical_task"] for row in held}
        train_by_id = {row["row_id"]: row for row in self.rows}
        self.assertFalse(held_tasks & {train_by_id[row_id]["canonical_task"] for row_id in call["fit_rows"]})
        with tempfile.TemporaryDirectory() as directory:
            ledger = SubmissionLedger(Path(directory) / "ledger.json", limit=1)
            entry, new = ledger.reserve("job", "hash", "purpose")
            self.assertTrue(new)
            again, new = ledger.reserve("job", "hash", "purpose")
            self.assertFalse(new)
            self.assertEqual(entry["job_id"], again["job_id"])
            with self.assertRaises(RuntimeError):
                ledger.reserve("other", "hash", "purpose")


if __name__ == "__main__":
    unittest.main()
