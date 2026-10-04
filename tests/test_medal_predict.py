import unittest

from arch_b.medal_predict import (
    REGIONALS_BY_YEAR,
    Predictor,
    load_rows,
)


class MedalPredictTest(unittest.TestCase):
    def setUp(self):
        self.predictor = Predictor()

    def test_qoj_host_override_keeps_2022_hong_kong_out_of_macau(self):
        row = next(r for r in load_rows() if r["cid"] == 1099)
        self.assertEqual(row["city"], "Hong Kong")

    def test_regular_city_mean_excludes_ec_final(self):
        self.assertEqual(self.predictor.city_n["Shanghai"], 1)
        self.assertEqual(self.predictor.city_mean["Shanghai"], 2482.1)

    def test_city_estimate_is_partially_pooled(self):
        raw = self.predictor.city_mean["Wuhan"]
        pooled = self.predictor.predict(city="Wuhan")["gold_cf"]
        self.assertGreater(raw, pooled)
        self.assertGreater(pooled, self.predictor.grand_mean)

    def test_year_and_position_do_not_change_recommendation(self):
        early = self.predictor.predict(city="Nanjing", year=2026, position=1)
        late = self.predictor.predict(city="Nanjing", year=2030, position=9)
        self.assertEqual(early["gold_cf"], late["gold_cf"])
        self.assertEqual(early["order_effect"], 0)

    def test_2026_recommendations_are_sorted_and_complete(self):
        rows = self.predictor.recommend(REGIONALS_BY_YEAR[2026])
        self.assertEqual(len(rows), 8)
        self.assertEqual({r["city"] for r in rows}, set(REGIONALS_BY_YEAR[2026]))
        self.assertEqual(
            [r["target_cf"] for r in rows],
            sorted(r["target_cf"] for r in rows),
        )
        self.assertEqual(
            [r["city"] for r in rows[:3]],
            ["Hong Kong", "Shanghai", "Shenyang"],
        )

    def test_forward_validation_is_finite_and_has_expected_coverage(self):
        gold = self.predictor.validation["gold"]
        self.assertEqual(gold["n"], 19)
        self.assertEqual(gold["n_pairs"], 48)
        self.assertLess(gold["rmse"], 120)
        self.assertGreaterEqual(gold["pairwise_accuracy"], 0.0)
        self.assertLessEqual(gold["pairwise_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
