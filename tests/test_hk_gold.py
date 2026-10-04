import unittest

from arch_b import hk_gold as hg


class HkGoldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = hg.run()
        cls.field = {f["season"]: f for f in cls.res["field"]}

    def test_field_top_schools_and_earlier_golds(self):
        self.assertEqual((self.field["2024"]["top50_schools"], self.field["2025"]["top50_schools"]), (31, 33))
        self.assertEqual((self.field["2024"]["golds_with_earlier_gold"], self.field["2025"]["golds_with_earlier_gold"]),
                         (11, 9))

    def test_hk_model_calibrated_across_years_and_earlier_gold_helps(self):
        for season, b in self.res["gold_backtest"].items():
            v = b["variants"]
            self.assertLess(abs(v["hk_online_only"]["expected_golds"] - b["golds"]), 1.5, season)
            self.assertLess(v["hk_earlier_mainland_gold"]["log_loss"], v["hk_online_only"]["log_loss"], season)

    def test_simulated_field_does_not_beat_same_as_last_year(self):
        bt = self.res["field_backtest"]
        sim = sum(b["abs_log_error_simulated"] for b in bt)
        same = sum(b["abs_log_error_same_as_train"] for b in bt)
        self.assertGreater(sim, same)

    def test_forecast_decreases_with_online_rank(self):
        ps = [g["p"] for g in self.res["forecast_2026"]["grid"]]
        self.assertEqual(ps, sorted(ps, reverse=True))
        for g in self.res["forecast_2026"]["grid"]:
            self.assertLessEqual(g["p_harder_field"], g["p"])
            self.assertLessEqual(g["p"], g["p_easier_field"])


if __name__ == "__main__":
    unittest.main()
