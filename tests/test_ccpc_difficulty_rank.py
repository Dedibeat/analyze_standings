import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
