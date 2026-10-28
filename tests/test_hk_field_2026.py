import unittest

from arch_b import hk_field_2026 as hf


class HkField2026Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = hf.run()
        cls.teams = {(t["school"], t["team"]): t for t in cls.res["teams"]}

    def test_links_by_members_per_round(self):
        self.assertEqual(self.res["registered"], 144)
        self.assertEqual(len(self.res["teams"]), 123)
        num = next(t for t in self.res["teams"] if t["team"] == "NUM-R^3")
        self.assertEqual(num["online_ranks"], {"1": 544, "2": 349})
        # line-up renamed between the rounds keeps both ranks
        swpu = self.teams[("西南石油大学", "All Last 才是开始")]
        self.assertEqual(swpu["online_teams"], {"1": "昇天", "2": "接地"})
        self.assertEqual(swpu["online_ranks"], {"1": 1608, "2": 632})

    def test_round1_takes_one_team_per_school(self):
        self.assertEqual(self.res["extra_teams"], [("福建师范大学", "BBQ team")])  # local schools may enter two
        self.assertIsNone(self.teams[("福建师范大学", "BBQ team")]["scenario_position"])
        self.assertEqual((self.res["cut_now"]["round1_nonlocal"], self.res["cut_now"]["cut"]), (136, 41))

    def test_export_online_ranking_is_the_combined_school_rank(self):
        self.assertEqual(self.res["rank_check"], {"rows": 144, "mismatches": []})
        self.assertEqual(self.res["selection"]["NUM-R^3"]["school_rank"], 128)

    def test_cut_risk_from_the_registration_pace(self):
        self.assertAlmostEqual(hf.binom_tail([(2, 0.5), (1, 0.5)], 2), 0.5)
        v = self.res["selection"]["NUM-R^3"]
        c = v["cut_risk"]
        self.assertEqual((v["ahead"], c["need"], v["unregistered_ahead"]), (59, 36, 64))
        self.assertEqual([c["groups"][g]["registered_since"] for g in ("past_hk", "other")], [1, 0])
        self.assertEqual([c["groups"][g]["withdrawn"] for g in ("past_hk", "other")], [1, 0])  # 浙江理工大学
        cuts = [r["p_cut"] for r in c["scenarios"]]
        self.assertEqual(cuts, sorted(cuts))
        self.assertLess(cuts[-1], 0.01)
        self.assertEqual(c["others_needed"], 11)  # with every past-HK school back, 11 of the 39 others
        self.assertLess(c["break_even_p_other"]["0.05"], c["break_even_p_other"]["0.5"])

    def test_early_list_is_weaker_and_scenario_restores_the_gold_line(self):
        f = {r["field"][:4] + ("s" if "scenario" in r["field"] else ""): r for r in self.res["field"]}
        past = [f["2024"]["line_online_rank"]["gold"], f["2025"]["line_online_rank"]["gold"]]
        self.assertGreater(f["2026"]["line_online_rank"]["gold"], 2 * max(past))
        self.assertLess(f["2026s"]["line_online_rank"]["gold"], 1.5 * max(past))

    def test_chances_fall_with_online_rank(self):
        for model in ("absolute", "field_relative_scenario"):
            golds = [t[model]["gold"] for t in self.res["teams"]]
            self.assertEqual(golds, sorted(golds, reverse=True), model)


if __name__ == "__main__":
    unittest.main()
