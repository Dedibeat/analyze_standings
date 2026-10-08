import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import ecfinal_chance as ch  # noqa: E402


class MemberHistoryTest(unittest.TestCase):
    def test_latin_names_ignore_order_and_case(self):
        self.assertEqual(ch.person_key("Bat-yeruult Battsagaan"), ch.person_key("Battsagaan Bat-Yeruult"))
        self.assertEqual(ch.person_key("张琦"), "张琦")

    def test_num_english_and_chinese_names_are_one_school(self):
        self.assertEqual(ch.school_key("National University of Mongolia"),
                         ch.school_key("蒙古国立大学(Монгол Улсын Их Сургууль)"))

    def test_num_r3_history_includes_nanjing_2025(self):
        _, size = ch.official_ranks()
        h = ch.history("2026", "蒙古国立大学(Монгол Улсын Их Сургууль)",
                       ["Tamir Jamiyangarav", "Munkh-Erdene Bayarjargal", "Dugarjantsan Bilguun"],
                       ch.member_best(size))
        self.assertEqual(h[1], 1.0)
        self.assertAlmostEqual(1 / (1 + 2.718281828459045 ** -h[0]), 168 / size[("2025", "nanjing")], places=6)


class CombinedChanceTest(unittest.TestCase):
    def test_independent_sites_without_team_effect(self):
        self.assertAlmostEqual(ch.p_any([0.2, 0.3], 0.0), 1 - 0.8 * 0.7, places=6)

    def test_team_effect_keeps_marginal_and_lowers_any(self):
        self.assertAlmostEqual(ch.p_any([0.12], 1.0), 0.12, delta=0.003)
        self.assertLess(ch.p_any([0.12, 0.12], 1.0), 1 - 0.88 ** 2)


if __name__ == "__main__":
    unittest.main()
