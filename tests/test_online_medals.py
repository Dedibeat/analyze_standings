import unittest

import numpy as np

from arch_b import online_medals as om


class ClassProbsTest(unittest.TestCase):
    def test_crossing_cumulatives_give_valid_classes(self):
        p = om.class_probs(np.array([0.4, 0.3, 0.7]))  # P(>= silver) below P(gold)
        self.assertAlmostEqual(float(p.sum()), 1.0)
        self.assertTrue((p >= 0).all())


class OnlineMedalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = om.run()

    def test_gold_level_reproduces_online_gold(self):
        deltas = [self.res["backtest"][t]["levels"]["gold"]["variants"]["rules_line_quota_adjusted"]
                  ["delta_vs_online_only"] for t in ("2024", "2025")]
        self.assertEqual([round(d, 4) for d in deltas], [-0.0003, -0.0010])
        self.assertAlmostEqual(self.res["forecast_2026"]["grid"]["xian"][100]["gold"]["p"], 0.5521, places=4)

    def test_medal_chances_fall_with_online_rank(self):
        for site, grid in self.res["forecast_2026"]["grid"].items():
            medal = [grid[k]["any_medal"] for k in om.FORECAST_RANKS]
            self.assertEqual(medal, sorted(medal, reverse=True), site)

    def test_hong_kong_hardest_gold_but_not_hardest_medal(self):
        g = self.res["forecast_2026"]["grid"]
        mainland = [s for s in g if s != "hongkong"]
        self.assertLess(g["hongkong"][100]["gold"]["p"], min(g[s][100]["gold"]["p"] for s in mainland))
        self.assertGreater(g["hongkong"][500]["any_medal"], min(g[s][500]["any_medal"] for s in mainland))


if __name__ == "__main__":
    unittest.main()
