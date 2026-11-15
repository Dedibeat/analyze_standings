import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ccpc_difficulty_rank as cr  # noqa: E402


class CcpcDifficultyRankTest(unittest.TestCase):
    def test_needed_inverts_expected(self):
        b = [1200, 1800, 2400, 3000, 3500]
        self.assertAlmostEqual(cr.expected(b, 2400), 2.5, places=1)
        self.assertAlmostEqual(cr.expected(b, cr.needed(b, 3.2)), 3.2, places=6)

    def test_rank_counts_easy_problems_then_breaks_ties_by_expected_solves(self):
        diffs = {"easy": [1500, 2000, 2300, 3000], "hardest": [2500, 2900, 3000, 3100],
                 "tie_harder": [2400, 2600, 3000, 3200], "tie_easier": [1000, 2600, 3000, 3200]}
        self.assertEqual(cr.rank(diffs), ["hardest", "tie_harder", "tie_easier", "easy"])

    def test_verdict_uses_the_middle_half(self):
        ref = [0, 10, 20, 30, 40]  # middle half 10..30
        self.assertEqual([cr.verdict(v, ref) for v in (31, 30, 10, 9)], ["harder", "same", "same", "easier"])

    def test_problem_gap_is_positive_for_a_harder_set(self):
        regional = [[1400 + 150 * i for i in range(12)]] * 3
        self.assertAlmostEqual(cr.problem_gaps(regional[0], regional, 2400), 0, places=6)
        self.assertAlmostEqual(cr.problem_gaps([d + 100 for d in regional[0]], regional, 2400), 100, places=6)
        self.assertLess(cr.problem_gaps([d - 50 for d in regional[0]], regional, 2400), 0)

    def test_link_takes_the_team_sharing_most_member_pairs(self):
        pairs = {("a", "b"): 1, ("a", "c"): 1, ("b", "d"): 2, ("d", "e"): 3}
        self.assertEqual(cr.link(["A", "B", "C"], pairs), 1)
        self.assertIsNone(cr.link(["B", "D", "E"], pairs))  # one pair each for teams 2 and 3
        self.assertIsNone(cr.link(["X", "Y"], pairs))

    def test_fixed_difficulty_recovers_the_solve_rate_point(self):
        theta = np.full(2000, 2400.0)
        y = np.arange(2000) % 2  # half solve: b = theta, pulled slightly to the 2000 prior
        b = cr.fixed_difficulty(theta, y)
        self.assertLess(b, 2400)
        self.assertGreater(b, 2390)
        self.assertGreater(cr.fixed_difficulty(theta, (np.arange(2000) % 4 == 0)), b)  # fewer solves: harder

    def test_calibration_recovers_a_line(self):
        alpha, beta = cr.calibration([(x, 100 + 0.9 * x) for x in (1500, 2000, 2500, 3000)])
        self.assertAlmostEqual(alpha, 100, places=6)
        self.assertAlmostEqual(beta, 0.9, places=9)

    def test_onsite_lines_rank_among_linked_teams_only(self):
        field = {t: {"official_rank": i + 1, "solved": 5 - i, "penalty_minutes": 100} for i, t in enumerate("wxyz")}
        board = {"field": field, "counts": (2, 1, 1), "linked": [("x", 0.0), ("y", 0.0), ("z", 0.0)]}  # w unlinked
        with mock.patch.object(cr.elo, "performance_rating", lambda rank, th: rank):
            self.assertEqual(cr.onsite_lines(board, float), {"gold": 1, "silver": 2, "bronze": 3})


if __name__ == "__main__":
    unittest.main()
