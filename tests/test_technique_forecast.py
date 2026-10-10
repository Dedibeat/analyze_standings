import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import technique_forecast as tf  # noqa: E402

IDS = ["a", "b", "c"]
CATEGORY = {"a": "g", "b": "g", "c": "h"}
TRAIN = {1: [{"season": 2023, "tech": {"a"}}],
         2: [{"season": 2024, "tech": {"a"}}, {"season": 2024, "tech": {"b"}}]}


class ModelTest(unittest.TestCase):
    def test_presence_is_any_problem(self):
        self.assertEqual(tf.presence(TRAIN[2], IDS), {"a": 1, "b": 1, "c": 0})

    def test_fit_shrinks_weighted_rate_toward_category_mean(self):
        # weights 0.5 (2023) and 1 (2024); raw rates a 1, b 2/3, c 0; category g mean 5/6.
        p = tf.fit(TRAIN, IDS, CATEGORY, alpha=2, decay=0.5)
        self.assertAlmostEqual(p["a"], (1.5 + 2 * 5 / 6) / 3.5)
        self.assertAlmostEqual(p["b"], (1.0 + 2 * 5 / 6) / 3.5)
        self.assertAlmostEqual(p["c"], 0.0)

    def test_fit_limits(self):
        raw = tf.fit(TRAIN, IDS, CATEGORY, alpha=0, decay=0.5)
        self.assertAlmostEqual(raw["b"], 1 / 1.5)
        cat = tf.fit(TRAIN, IDS, CATEGORY, alpha=1e12, decay=0.5)
        self.assertAlmostEqual(cat["a"], 5 / 6)
        self.assertAlmostEqual(cat["b"], 5 / 6)

    def test_logloss_and_brier(self):
        ll, br = tf.logloss({"a": 0.5}, {1: [{"tech": {"a"}}]}, ["a"])
        self.assertAlmostEqual(ll, math.log(2))
        self.assertAlmostEqual(br, 0.25)

    def test_coverage_counts_problems_with_a_primary_technique(self):
        test = {1: [{"primary": {"a"}}, {"primary": {"c"}}, {"primary": set()}]}
        self.assertEqual(tf.coverage({"a": 0.9, "b": 0.5, "c": 0.1}, test, 1), (0.5, 2))

    def test_random_coverage(self):
        # 4 ids, top 2: one primary is hit with 1 - C(3,2)/C(4,2) = 1/2, two with 1 - 1/6.
        test = {1: [{"primary": {"a"}}, {"primary": {"a", "b"}}]}
        self.assertAlmostEqual(tf.random_coverage(test, 2, 4), (0.5 + 5 / 6) / 2)

    def test_holm_is_monotone_in_input_order(self):
        for x, y in zip(tf.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(x, y)


class DataTest(unittest.TestCase):
    def test_every_listed_contest_is_in_the_atlas_with_positions(self):
        problems, taxonomy, _ = tf.load()
        self.assertEqual(len(taxonomy), 128)
        for kind, table in (("regional", tf.REGIONALS), ("ccpc", tf.CCPC)):
            got = tf.contests(problems, kind)
            self.assertEqual(set(got), set(table))
            for ps in got.values():
                self.assertEqual(sorted(p["pos"] for p in ps), list(range(1, len(ps) + 1)))
        self.assertTrue(all(p["general"] is None for p in problems if p["kind"] == "ccpc"))


if __name__ == "__main__":
    unittest.main()
