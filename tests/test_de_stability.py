import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from arch_b import de_stability as exp
from arch_b import de_stability_data as data


def fixture():
    full = []
    for c in range(6):
        for p in range(4):
            b = 1400 + 130 * c + 150 * p
            full.append({"row_id": f"{c}:{p}", "cf_contest": c, "canonical_task": f"task{c}:{p}",
                         "region": "A" if c < 3 else "B", "raw_b": float(b),
                         "b_bin": float(b + 20 * p), "binary_minus_survival": float(20 * p),
                         "conditional_fit_se": float(20 + 3 * p), "solve_rate": 0.8 - 0.15 * p,
                         "log_field_size": float(4 + c / 10), "cf": float(1.4 * b - 600 + 15 * p)})
    views = {}
    for i, name in enumerate(data.VIEWS):
        rows = copy.deepcopy(full)
        if name != "full":
            for r in rows:
                r["raw_b"] += 20 * ((i % 3) - 1)
                r["solve_rate"] += 0.02 * i
                r["conditional_fit_se"] += i
                r["log_field_size"] -= 0.1 * i
        views[name] = rows
    return full, views


class StabilityTest(unittest.TestCase):
    def test_penalty_reduces_changes_in_final_predictions(self):
        full, views = fixture()
        low = exp.fit_stable(full, views, 1, 0)
        high = exp.fit_stable(full, views, 1, 10000)
        def change(f):
            return sum(np.mean((f(views[v]) - f(full)) ** 2) for v in data.TRAIN[1:])
        self.assertLess(change(high), change(low) / 10)

    def test_duplicate_identical_views_do_not_multiply_task_weight(self):
        full, _ = fixture()
        single = {v: full if v == "full" else [] for v in data.TRAIN}
        repeated = {v: full for v in data.TRAIN}
        a = exp.fit_stable(full, single, 10, 0)
        b = exp.fit_stable(full, repeated, 10, 0)
        np.testing.assert_allclose(a(full), b(full), atol=1e-9)

    def test_outer_labels_and_reserved_views_do_not_select_settings(self):
        full, views = fixture()
        before = exp.outer_fold(full, views, 0)
        changed, altered = copy.deepcopy(full), copy.deepcopy(views)
        for r in changed:
            if r["cf_contest"] == 0:
                r["cf"] += 1e6
        for name, rows in altered.items():
            for r in rows:
                if r["cf_contest"] == 0:
                    r["cf"] += 1e6
                if name not in data.TRAIN:
                    r["raw_b"] += 1e5
                    r["solve_rate"] += 1e4
        after = exp.outer_fold(changed, altered, 0)
        self.assertEqual(before["selected"], after["selected"])
        for a, b in zip(before["predictions"]["full"], after["predictions"]["full"]):
            for name in exp.METHODS:
                self.assertAlmostEqual(a[name], b[name], places=8)

    def test_shared_canonical_tasks_are_purged_from_all_training_views(self):
        full, views = fixture()
        full[4]["canonical_task"] = full[0]["canonical_task"]
        for rows in views.values():
            rows[4]["canonical_task"] = full[0]["canonical_task"]
        before = exp.outer_fold(full, views, 0)
        self.assertNotIn(full[4]["row_id"], before["training_rows"])
        full[4]["cf"] += 1e7
        for rows in views.values():
            rows[4]["raw_b"] += 1e7
        after = exp.outer_fold(full, views, 0)
        self.assertEqual(before["selected"], after["selected"])

    def test_sampling_keeps_identity_groups_and_halves_disjoint(self):
        teams = np.repeat(np.arange(40), 2)
        ds = SimpleNamespace(team_of_row=teams, contest_of_row=np.zeros(80, int),
                             contests=[100], official_of_row=np.ones(80, bool))
        a = data.sample_rows(ds, np.zeros(80, int), [0], "half_a0")
        b = data.sample_rows(ds, np.zeros(80, int), [0], "half_b0")
        self.assertFalse(set(teams[a]) & set(teams[b]))
        self.assertEqual(len(a) + len(b), 80)
        # Independent strength stress only uses identities seen on both sides.
        eligible = np.arange(40) < 20
        selector = np.arange(40, dtype=float)
        strong = data.sample_rows(ds, np.zeros(80, int), [0], "strong", selector, eligible)
        weak = data.sample_rows(ds, np.zeros(80, int), [0], "weak", selector, eligible)
        self.assertEqual(set(teams[strong]), set(range(10, 20)))
        self.assertEqual(set(teams[weak]), set(range(10)))

    def test_cache_rejects_changed_payload_and_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(data, "RUN", Path(directory)):
            rec = {"fingerprint": "abc", "view": "full", "rows": []}
            payload = {**rec, "content_sha256": data.digest(rec)}
            path = Path(directory) / "full.json.gz"
            path.write_bytes(gzip.compress(json.dumps(payload).encode()))
            self.assertEqual(data.read_view("full", "abc"), rec)
            with self.assertRaisesRegex(RuntimeError, "stale or corrupt"):
                data.read_view("full", "other")
            payload["rows"] = [1]
            path.write_bytes(gzip.compress(json.dumps(payload).encode()))
            with self.assertRaisesRegex(RuntimeError, "stale or corrupt"):
                data.read_view("full", "abc")

    def test_drift_and_metrics_use_matched_tasks(self):
        full, _ = fixture()
        reference = [{**r, "m": r["cf"]} for r in full]
        changed = [{**r, "m": r["cf"] + 50} for r in full[1:]]
        drift = exp.drift(changed, reference, "m")
        self.assertEqual(drift["problems"], len(full) - 1)
        self.assertEqual(drift["rms"], 50)
        self.assertEqual(drift["order_reversals"], 0)
        self.assertEqual(exp.metrics(changed, "m")["rmse"], 50)


if __name__ == "__main__":
    unittest.main()
