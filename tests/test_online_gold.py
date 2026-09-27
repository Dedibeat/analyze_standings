import unittest

import numpy as np

from arch_b.online_gold import (
    load,
    logistic,
    online_strengths,
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


if __name__ == "__main__":
    unittest.main()
