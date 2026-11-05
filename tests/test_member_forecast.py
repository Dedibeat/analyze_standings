import copy
import unittest

import numpy as np

from arch_b import member_forecast as mf


def board(cid, start, rosters):
    return {"contest_id": cid, "start": start, "end": start + 100,
            "n_problems": 4,
            "rows": [{"source_row": i, "roster": tuple(m), "key": tuple(m),
                      "rank": i + 1, "y": [1, 1, i == 0, 0]}
                     for i, m in enumerate(rosters)]}


class MemberForecastTest(unittest.TestCase):
    def setUp(self):
        self.old = board(1, 1000, [("a", "b", "c"), ("d", "e", "f")])
        self.target = board(2, 2000, [("a", "b", "g"), ("d", "e", "f")])

    def test_changed_roster_is_cold_and_shared_history_is_one_source(self):
        rows, manifest = mf.forecast([self.old, self.target], self.target)
        self.assertFalse(rows[0]["history"])
        self.assertEqual(rows[0]["known_members"], 2)
        self.assertEqual(rows[0]["prior_sources"], 1)
        self.assertTrue(rows[1]["history"])
        self.assertEqual(manifest["training_contests"], [1])

    def test_future_and_target_responses_cannot_change_forecasts(self):
        rows, _ = mf.forecast([self.old, self.target], self.target)
        poison = copy.deepcopy(self.target)
        for r in poison["rows"]:
            r["y"] = [0, 0, 0, 1]
        future = board(3, 3000, [("a", "d", "g"), ("b", "e", "f")])
        changed, _ = mf.forecast([self.old, poison, future], poison)
        self.assertEqual(rows, changed)

    def test_overlapping_and_same_end_contests_are_not_training(self):
        overlap = board(3, 1950, [("a", "b", "g")])
        same_end = board(4, 1900, [("a", "b", "g")])
        _, manifest = mf.forecast([self.old, overlap, same_end, self.target], self.target)
        self.assertEqual(manifest["training_contests"], [1])

    def test_ambiguous_latest_member_history_is_not_transferred(self):
        conflicting = board(3, 1000, [("a", "x", "y")])
        rows, _ = mf.forecast([self.old, conflicting, self.target], self.target)
        self.assertEqual(rows[0]["known_members"], 1)

    def test_roster_requires_three_distinct_normalized_people(self):
        self.assertEqual(mf.roster({"members": ["A", "a", "B"]}), ())
        self.assertEqual(mf.roster({"members": [" B ", "A", "C"]}), ("a", "b", "c"))
        self.assertEqual(mf.seconds(1700000000000), mf.seconds(1700000000))

    def test_pair_ties_and_cold_population(self):
        rows = [{"rank": rank, "history": hist, "static": f, "dynamic_q50": f,
                 "member_delta": delta} for rank, hist, f, delta in
                [(1, True, 2200, 0), (2, False, 2000, 100), (2, False, 2000, -100)]]
        s = mf.score(rows)
        self.assertEqual(s[1], 2)  # tied finishes are not ordered
        self.assertEqual(s[0], 2)
        self.assertEqual(mf.score(rows, population="cold_involving"), s)
        self.assertIsNone(mf.score(rows, population="cold"))
        rows[0]["static"] = 2000
        s = mf.score(rows)
        self.assertEqual(s[0], 1)  # forecast ties are half correct
        self.assertAlmostEqual(s[2] / s[1], np.log(2))

    def test_balanced_and_weighted_metrics_differ(self):
        scores = {1: [1, 1, 0.1], 2: [0, 9, 9]}
        agg = mf.aggregate(scores)
        self.assertEqual(agg["contest_accuracy"], 0.5)
        self.assertEqual(agg["accuracy"], 0.1)
        diff = mf.comparison(scores, scores)
        self.assertEqual(diff["pair_log_loss"], [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
