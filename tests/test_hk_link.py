import unittest

from arch_b import hk_link as hk


class PinyinTest(unittest.TestCase):
    def test_both_name_orders(self):
        v = hk.pinyin_variants("姜奕豪")
        self.assertIn(hk.canon_person("Yihao Jiang"), v)
        self.assertIn(hk.canon_person("Jiang Yihao"), v)

    def test_u_umlaut_spellings_merge(self):
        v = hk.pinyin_variants("吕思远")
        for s in ("Siyuan Lyu", "Siyuan Lv", "Siyuan Lu"):
            self.assertIn(hk.canon_person(s), v)

    def test_compound_surname_and_heteronym(self):
        self.assertIn(hk.canon_person("Ming Ouyang"), hk.pinyin_variants("欧阳明"))
        self.assertIn(hk.canon_person("Weijun Zeng"), hk.pinyin_variants("曾伟军"))
        self.assertIn(hk.canon_person("Qing'an Lu"), hk.pinyin_variants("卢庆安"))


class LinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = hk.run()
        cls.by = {(s["season"], s["site"]): s for s in cls.res["summary"]}

    def test_member_link_rates(self):
        for key, linked, golds in ((("2024", "hongkong"), 118, 13), (("2025", "hongkong"), 97, 12)):
            s = self.by[key]
            self.assertEqual((s["linked"], s["golds_linked"]), (linked, golds), key)

    def test_school_check_only_campus_alias_differs(self):
        diff = [r for r in self.res["rows"] if r["school_check"] == "different"]
        self.assertEqual([(r["school"], r["online_school"]) for r in diff],
                         [("Beijing Jiaotong University, Weihai", "北京交通大学威海校区")])

    def test_boards_without_members_link_by_name_only(self):
        for key in (("2022", "hongkong"), ("2023", "macau")):
            self.assertEqual((self.by[key]["with_members"], self.by[key]["by_members"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
