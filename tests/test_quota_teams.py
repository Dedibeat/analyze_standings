import unittest

from arch_b import quota_teams as qt
from arch_b import online_gold as og
from arch_b.online_gold import norm_school


class NormSchoolTest(unittest.TestCase):
    def test_campuses_stay_distinct(self):
        self.assertNotEqual(norm_school("哈尔滨工业大学"), norm_school("哈尔滨工业大学（威海）"))
        self.assertNotEqual(norm_school("香港中文大学"), norm_school("香港中文大学(深圳)"))

    def test_spelling_variants_merge(self):
        self.assertEqual(norm_school("大连理工大学（盘锦校区）"), norm_school("大连理工大学盘锦校区"))
        self.assertEqual(norm_school("齐鲁工业大学(山东省科学院)"), norm_school("齐鲁工业大学"))
        self.assertEqual(norm_school("香港中文大學"), norm_school("香港中文大学"))


class QuotaTeamsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.res = qt.run()

    def test_band_slots_match_shanghai_published_online_seats(self):
        for season, check in self.res["shanghai_check"].items():
            matched, total = map(int, check["band_slots_match"].split("/"))
            self.assertEqual(matched, total, season)

    def test_wf_and_host_explain_most_published_reward_schools(self):
        for season, check in self.res["shanghai_check"].items():
            self.assertGreaterEqual(check["reward_schools_explained_by_wf_or_host"],
                                    0.9 * check["reward_schools_published"], season)

    def test_every_quota_team_has_a_channel_and_band_teams_none(self):
        for r in self.rows:
            if r["admission"] == "quota":
                self.assertIn(r["channel"], qt.CHANNELS)
            else:
                self.assertEqual(r["channel"], "")

    def test_school_channel_seats_are_not_exceeded(self):
        per = {}
        for r in self.rows:
            if r["channel"] in qt.CHANNEL_SEATS:
                key = (r["season"], r["site"], r["school"], r["channel"])
                per[key] = per.get(key, 0) + 1
        for (season, site, school, channel), n in per.items():
            self.assertLessEqual(n, qt.CHANNEL_SEATS[channel], (season, site, school, channel))


class SchoolRankModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = og.load()
        cls.strengths = og.online_strengths(cls.data["online_teams"])
        cls.ev = qt.load_evidence()
        rows = qt.team_table(cls.data, cls.strengths, cls.ev)
        cls.model = qt.school_rank_quota_model(rows, cls.data, cls.ev)

    def test_top50_quota_teams_beat_band_teams_and_the_rest_do_not(self):
        m = self.model
        self.assertGreater(m["rho_top50"], 1.0)
        self.assertLess(m["rho_rest"], 0.2)
        self.assertLess(m["rho_rest"], m["rho_pooled"])
        self.assertGreater(m["kappa"], 1.0)

    def test_zero_top50_seats_reduces_to_the_pooled_line(self):
        pooled = og.rules_line("2025", "nanjing", self.data, self.strengths, 0.44)
        split = og.rules_line("2025", "nanjing", self.data, self.strengths, 0.44, top50_seats=0, rho_top50=1.4)
        self.assertEqual(pooled, split)

    def test_2026_entitlement_uses_2026_wf_and_host_lists(self):
        self.assertGreater(qt.elite_entitlement("2026", "xian", self.data, self.ev), 0)


if __name__ == "__main__":
    unittest.main()
