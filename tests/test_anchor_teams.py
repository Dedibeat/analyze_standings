import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)  # ecfinal_cutoff reads data/ relative to the working directory
import anchor_teams as at  # noqa: E402

TEAM = {"s": at.og.norm_school("蒙古国立大学"), "m": at.members(["A", "B", "C"]), "team": "NUM-R^3"}


def regional(medal="", rank="100", site="nanjing", season="2026", names="A|B|D"):
    return {"season": season, "site": site, "official": "1", "school": "蒙古国立大学", "members": names,
            "medal": medal, "official_rank": rank}


class AnchorTest(unittest.TestCase):
    def test_actual_result_needs_a_51st_season_row_with_two_shared_members(self):
        self.assertIsNone(at.actual_results({"regional_teams": [regional(medal="gold", season="2025")]}, TEAM))
        self.assertIsNone(at.actual_results({"regional_teams": [regional(medal="gold", names="A|X|Y")]}, TEAM))
        self.assertEqual(at.actual_results({"regional_teams": [regional()]}, TEAM), "none")

    def test_best_actual_result_wins(self):
        rows = [regional(rank="70"), regional(medal="gold", rank="20", site="xian")]
        self.assertEqual(at.actual_results({"regional_teams": rows}, TEAM), "gold")
        self.assertEqual(at.actual_results({"regional_teams": [regional(rank="75")]}, TEAM), "ecfinal")
        self.assertEqual(at.actual_results({"regional_teams": [regional(rank="20", site="hongkong")]}, TEAM),
                         "none")

    def test_match_is_one_to_one_roster_first(self):
        rows = [{"s": TEAM["s"], "m": at.members(["X", "Y", "Z"]), "team": "NUM-R^3"},
                {"s": TEAM["s"], "m": at.members(["A", "C", "Q"]), "team": "renamed"}]
        self.assertEqual(at.match([TEAM], rows), [(TEAM, rows[1])])
        self.assertEqual(at.match([TEAM], rows[:1]), [(TEAM, rows[0])])
        self.assertEqual(at.match([TEAM], [dict(rows[1], s="other")]), [])
        other = dict(TEAM, m=at.members(["A", "C", "E"]), team="other")  # reshuffled roster, same school
        board = [{"s": TEAM["s"], "m": at.members(["A", "B", "C"]), "team": "x"}]
        self.assertEqual(at.match([other, TEAM], board), [(TEAM, board[0])])

    def test_pool_pairs_each_registration_once(self):
        teams = at.pool(at.og.load())
        keys = [(t["s"], t["team"]) for t in teams]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreater(len(teams), 2000)


if __name__ == "__main__":
    unittest.main()
