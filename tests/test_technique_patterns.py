import os
import random
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import technique_patterns as tp  # noqa: E402


class StatsTest(unittest.TestCase):
    def test_p2_is_two_sided_and_capped(self):
        null = list(range(100))
        self.assertAlmostEqual(tp.p2(99, null), 2 * 2 / 101)
        self.assertAlmostEqual(tp.p2(0, null), 2 * 2 / 101)
        self.assertEqual(tp.p2(50, null), 1.0)

    def test_similarities(self):
        self.assertAlmostEqual(tp.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        self.assertEqual(tp.jaccard(set(), set()), 0.0)
        self.assertAlmostEqual(tp.cosine(Counter(a=1, b=1), Counter(a=2, b=2)), 1.0)
        self.assertEqual(tp.cosine(Counter(a=1), Counter(b=1)), 0.0)

    def test_gap_stats_cycle_ignores_a_linear_drift(self):
        same, drift, cycle = tp.gap_stats({0: 0.9, 1: 0.8, 2: 0.7, 3: 0.6})
        self.assertAlmostEqual(same, 0.1)
        self.assertAlmostEqual(drift, -0.1)
        self.assertAlmostEqual(cycle, 0.0)
        self.assertAlmostEqual(tp.gap_stats({0: 1, 1: 0, 2: 1, 3: 0})[2], 1.0)

    def test_lag1(self):
        self.assertLess(tp.lag1([1, 0, 1, 0]), 0)
        self.assertGreater(tp.lag1([0, 0, 1, 1]), 0)
        self.assertEqual(tp.lag1([2, 2, 2, 2]), 0.0)


class ShuffleTest(unittest.TestCase):
    def test_shuffled_keeps_values_inside_blocks(self):
        labels = {1: "x", 2: "y", 3: "z", 4: "w"}
        block = {1: 0, 2: 0, 3: 1, 4: 1}
        for seed in range(20):
            out = tp.shuffled(labels, random.Random(seed), block)
            self.assertEqual({out[1], out[2]}, {"x", "y"})
            self.assertEqual({out[3], out[4]}, {"z", "w"})

    def test_deal_keeps_sizes_and_season_pools(self):
        group = {1: [{"season": 1, "n": i} for i in range(3)],
                 2: [{"season": 1, "n": i} for i in range(3, 5)],
                 3: [{"season": 2, "n": i} for i in range(5, 9)]}
        out = tp.deal(group, random.Random(0))
        self.assertEqual({c: len(ps) for c, ps in out.items()}, {1: 3, 2: 2, 3: 4})
        self.assertEqual(sorted(p["n"] for p in out[1] + out[2]), list(range(5)))
        self.assertEqual(sorted(p["n"] for p in out[3]), list(range(5, 9)))


if __name__ == "__main__":
    unittest.main()
