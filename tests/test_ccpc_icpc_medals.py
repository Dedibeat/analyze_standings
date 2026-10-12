import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ccpc_icpc_medals as cm  # noqa: E402


def ccpc_row(school="北京大学", names="张三|李四|王五", season="2025", medal="gold", pct=0.05):
    return {"season": season, "s": cm.og.norm_school(school), "m": cm.members(names),
            "py": [cm.hk.pinyin_variants(n) for n in names.split("|")], "medal": medal, "pct": pct}


def icpc_row(site="nanjing", school="北京大学", names="张三|李四|赵六", season="2025", rank=10, medal="gold"):
    mainland = site not in cm.og.EXCLUDED_SITES
    m = cm.members(names) if mainland else frozenset(cm.hk.canon_person(n) for n in names.split("|"))
    return {"season": season, "site": site, "s": cm.og.norm_school(school), "m": m, "mainland": mainland,
            "rank": rank, "medal": medal}


class CcpcIcpcMedalsTest(unittest.TestCase):
    def test_ccpc_preset_is_the_ceil_rule(self):
        rows = [{"official": 1, "solved": 1}] * 259 + [{"official": 1, "solved": 0}]
        self.assertEqual(cm.bd.medal_counts(None, {"medal": "ccpc"}, rows)[:3], (26, 52, 78))
        board = {"medal": {"official": {"gold": 24, "silver": 48, "bronze": 72}}}
        self.assertEqual(cm.bd.medal_counts(None, board, rows), (24, 48, 72, "board"))

    def test_medal_of_needs_a_solve(self):
        self.assertEqual(cm.medal_of(26, 5, (26, 52, 78)), "gold")
        self.assertEqual(cm.medal_of(78, 4, (26, 52, 78)), "silver")
        self.assertEqual(cm.medal_of(156, 3, (26, 52, 78)), "bronze")
        self.assertEqual(cm.medal_of(157, 3, (26, 52, 78)), "")
        self.assertEqual(cm.medal_of(5, 0, (26, 52, 78)), "")

    def test_link_needs_same_season_school_and_two_members(self):
        c = ccpc_row()
        self.assertEqual(len(cm.link([c], [icpc_row()])), 1)
        self.assertEqual(cm.link([c], [icpc_row(names="张三|赵六|孙七")]), [])
        self.assertEqual(cm.link([c], [icpc_row(school="清华大学")]), [])
        self.assertEqual(cm.link([c], [icpc_row(season="2024")]), [])

    def test_link_takes_one_entry_per_site_most_shared_first(self):
        two, three = icpc_row(names="张三|李四|赵六"), icpc_row(names="张三|李四|王五")
        other_site = icpc_row(site="xian")
        pairs = cm.link([ccpc_row()], [two, three, other_site])
        self.assertEqual([r for _, r in pairs], [three, other_site])

    def test_hong_kong_links_by_pinyin(self):
        hk = icpc_row(site="hongkong", school="", names="San Zhang|Si Li|Liu Zhao")
        hk["s"] = cm.og.norm_school("北京大学")  # mapped from the English name in icpc_rows
        self.assertEqual(len(cm.link([ccpc_row()], [hk])), 1)

    def test_outcomes_use_the_site_line(self):
        self.assertTrue(cm.outcomes(icpc_row(rank=75, medal="silver"))["ecf_line"])
        self.assertFalse(cm.outcomes(icpc_row(rank=76, medal="silver"))["ecf_line"])
        hk = icpc_row(site="hongkong", rank=33, medal="silver")
        self.assertFalse(cm.outcomes(hk)["ecf_line"])
        self.assertTrue(cm.outcomes(dict(hk, season="2024"))["ecf_line"])

    def test_station_offset_is_positive_when_its_teams_beat_the_pooled_curve(self):
        models = {k: ((0.0, 0.0), []) for k in cm.OUTCOMES}  # pooled curve: P = 50% everywhere
        pairs = [(dict(ccpc_row(), board="a"), icpc_row(rank=10, medal="gold")),
                 (dict(ccpc_row(), board="a"), icpc_row(rank=10, medal="gold")),
                 (dict(ccpc_row(), board="a"), icpc_row(rank=100, medal="")),
                 (dict(ccpc_row(), board="b"), icpc_row(rank=10, medal="gold")),
                 (dict(ccpc_row(), board="b"), icpc_row(rank=100, medal=""))]
        offs = cm.station_offsets(pairs, models)
        self.assertAlmostEqual(offs["a"]["gold"], cm.math.log(2), places=6)
        self.assertAlmostEqual(offs["b"]["gold"], 0.0, places=6)

    def test_place_ranks_a_virtual_run_among_official_teams(self):
        board = [{"solved": s, "penalty_minutes": p, "official_rank": i + 1}
                 for i, (s, p) in enumerate([(6, 800), (5, 500), (4, 400), (4, 500), (3, 100)])]
        info = {"gold": 1, "silver": 2, "bronze": 2, "effective": 5}
        run = cm.place(board, info, 4, 450)
        self.assertEqual((run["rank"], run["medal"]), (4, "bronze"))
        self.assertEqual(run["lines"]["silver"], {"rank": 3, "solved": 4, "penalty": 400})
        self.assertEqual(cm.place(board, info, 4, 400)["rank"], 3)  # a tie shares the better rank


if __name__ == "__main__":
    unittest.main()
