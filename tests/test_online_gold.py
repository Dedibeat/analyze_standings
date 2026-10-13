import math
import unittest
from unittest import mock

import numpy as np

from arch_b.online_gold import (
    contest_difficulty,
    load,
    logistic,
    online_strengths,
    quota_split,
    rules_line,
    school_slots,
)


class OnlineGoldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()
        cls.strengths = online_strengths(cls.data["online_teams"])

    def test_logistic_recovers_coefficients(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=20000)
        y = rng.random(20000) < 1 / (1 + np.exp(-(0.5 + 2.0 * x)))
        w = logistic([[1, v] for v in x], y)
        np.testing.assert_allclose(w, [0.5, 2.0], atol=0.1)

    def test_num_gets_one_rank_band_slot_at_every_2026_mainland_site(self):
        for (season, site), rule in self.data["rules"].items():
            if season == "2026" and rule.get("online_bands"):
                slots = school_slots("2026", rule, self.data)
                num = [k for s, k in slots.items() if s.startswith("蒙古国立大学")]
                self.assertEqual(num, [1], site)

    def test_wider_two_slot_band_lowers_the_gold_line(self):
        # 2025 Shenyang doubled its two-slot band (1-50 -> 1-100) versus 2024
        line_2024 = rules_line("2024", "shenyang", self.data, self.strengths)
        line_2025 = rules_line("2025", "shenyang", self.data, self.strengths)
        self.assertLess(line_2025, line_2024)


class QuotaRhoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()
        cls.strengths = online_strengths(cls.data["online_teams"])

    def test_rho_moves_the_line_from_capacity_to_band_share(self):
        # rho=0: all capacity golds go to band teams (deepest line); rho=1:
        # quota teams keep their seat share of golds (shallowest line)
        lines = [rules_line("2026", "xian", self.data, self.strengths, rho) for rho in (0.0, 0.44, 1.0)]
        self.assertLessEqual(lines[0], lines[1])
        self.assertLessEqual(lines[1], lines[2])

    def test_quota_rho_is_estimated_between_zero_and_one(self):
        _, rho = quota_split(self.data, self.strengths, ["2023", "2024"])
        self.assertGreater(rho, 0.2)
        self.assertLess(rho, 0.7)


class ContestDifficultyTest(unittest.TestCase):
    def test_fit_minus_online_is_read_on_the_gold_line_not_the_bar(self):
        rng = np.random.default_rng(1)
        rows = []
        for site, even in (("a", 40.0), ("b", 80.0), ("c", 160.0)):  # online rank with a 50% gold chance
            x = rng.normal(-math.log(even), 1.0, 4000)
            p = 1 / (1 + np.exp(-2.0 * (x + math.log(even))))
            rows += [dict(season="2025", site=site, x=v, gold=int(u < q)) for v, u, q in zip(x, rng.random(4000), p)]
        lines = {("2025", "a"): 2800.0, ("2025", "b"): 2700.0, ("2025", "c"): 2600.0}  # linear in log rank
        bars = {("2025", "a"): 2500.0, ("2025", "b"): 2900.0, ("2025", "c"): 2700.0}
        with mock.patch("arch_b.online_gold.cf_gold_bars", lambda line=False: lines if line else bars):
            cd = contest_difficulty(rows)
        for o in cd["contests"]:
            self.assertAlmostEqual(o["fit_minus_online"], 0, delta=15)
            self.assertEqual(o["cf_gold_bar"], bars[(o["season"], o["site"])])
        self.assertEqual(cd["spearman_rank_vs_line"], -1.0)


if __name__ == "__main__":
    unittest.main()
