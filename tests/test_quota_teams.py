import unittest

from arch_b import quota_teams as qt
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


if __name__ == "__main__":
    unittest.main()
