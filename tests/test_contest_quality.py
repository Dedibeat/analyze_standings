import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import contest_quality as cq  # noqa: E402


class ContestQualityTest(unittest.TestCase):
    def test_auc(self):
        self.assertEqual(cq.auc([5, 4, 3, 2, 1, 0], [1, 1, 1, 0, 0, 0]), 1.0)
        self.assertEqual(cq.auc([1] * 6, [1, 1, 1, 0, 0, 0]), 0.5)
        self.assertIsNone(cq.auc([3, 2, 1, 0], [1, 1, 0, 0]))

    def test_discrimination_of_a_perfect_ladder_and_a_lottery_problem(self):
        problems = ["a", "b", "c"]
        solved = {t: set(problems[:k]) for t, k in enumerate([3, 3, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0])}
        # equal rest scores tie at each step of the ladder, so even a perfect ladder stays below 1
        self.assertEqual([round(a, 3) for a in cq.discrimination(problems, solved, list(solved))],
                         [0.833, 0.875, 0.833])
        for t in (9, 10, 11):  # the three weakest teams also solve a fourth problem
            solved[t].add("d")
        self.assertLess(cq.discrimination(problems + ["d"], solved, list(solved))[-1], 0.1)

    def test_tie_share_is_the_gold_lines_solve_group(self):
        field = {i: {"official_rank": i + 1, "solved": s, "medal": "gold" if i < 2 else ""}
                 for i, s in enumerate([5, 4, 4, 4, 3, 2, 1, 1, 1, 1])}
        self.assertEqual(cq.tie_share(field, (2, 0, 0)), 0.3)
        self.assertIsNone(cq.tie_share({0: dict(field[0], medal="")}, (0, 0, 0)))

    def test_consistency_pools_both_sides_of_each_pair(self):
        pairs = [({"link": "a", "pct": i / 40}, {"link": "b", "pct": (i + (i % 2)) / 40}) for i in range(40)]
        cons = cq.consistency(pairs)
        self.assertEqual(cons["a"][1], 40)
        self.assertGreater(cons["a"][0], 0.99)
        self.assertEqual(cons["a"], cons["b"])
        self.assertEqual(cq.consistency(pairs[:29]), {})

    def test_mirror_offset_bands_by_the_mean_of_both(self):
        ccpc, icpc = "ccpc/11th/jinan", "icpc/50th/nanjing"

        def perf(cid, solved, penalty):  # mirror reads 100 lower than the onsite board
            return 2500 + 10 * solved - (100 if cid == cq.QOJ[ccpc] else 0)
        pairs = [({"link": ccpc, "solved": 5, "penalty_minutes": 300},
                  {"link": icpc, "solved": "5", "penalty_minutes": "300"}),
                 ({"link": ccpc, "solved": 5, "penalty_minutes": 300},
                  {"link": icpc, "solved": "0", "penalty_minutes": "0"})]  # no solve: left out
        out = cq.mirror_offset(pairs, perf)
        self.assertEqual((out["n"], out["diff"]), (1, -100))
        self.assertEqual([b["n"] for b in out["bands"]], [0, 0, 1, 0, 0])

    def test_compare_uses_the_seasons_where_ccpc_has_the_metric(self):
        def row(kind, season, v):
            return {"kind": kind, "season": season, "mainland": True, **{k: v for k in (
                "auc", "flat", "dead", "tie_gold", "rejects", "consistency_rho")}, "diff_median": v, "diff_q75": v}
        rows = [row("ccpc", "2024", 1.0) for _ in range(3)] + [row("icpc", "2024", 2.0) for _ in range(3)]
        rows += [dict(row("icpc", "2023", 9.0), diff_median=9.0)] * 3
        rows += [dict(row("ccpc", "2023", 1.0), diff_median=None, diff_q75=None)] * 3
        out = cq.compare(rows, n_boot=10)
        self.assertEqual(out["diff_median"]["diff"], 1.0)  # 2023 ICPC left out: no CCPC difficulty that season
        self.assertEqual(out["auc"]["n"], (6, 6))


if __name__ == "__main__":
    unittest.main()
