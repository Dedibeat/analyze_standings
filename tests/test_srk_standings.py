import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import srk_standings as ss  # noqa: E402


def row(tid, solved, ms, official=True):
    return {"user": {"id": tid, "name": {"fallback": tid}, "official": official,
                     "teamMembers": [{"name": "a"}, {"name": "c", "role": "coach"}]},
            "score": {"value": solved, "time": [ms, "ms"]}}


class SrkStandingsTest(unittest.TestCase):
    def test_minute_ties_share_rank_and_medals_skip_unofficial_and_zero(self):
        srk = {"series": [{"title": "#", "rule": {"preset": "ICPC", "options": {"count": {"value": [1, 1, 1]}}}}],
               "rows": [row("A", 3, 100 * 60000 + 59999), row("X", 3, 101 * 60000, official=False),
                        row("B", 2, 50 * 60000 + 1), row("C", 2, 50 * 60000 + 30000), row("D", 0, 0)]}
        got = [(r["team_id"], r["rank"], r["official_rank"], r["medal"]) for r in ss.standings(srk)]
        self.assertEqual(got, [("A", 1, 1, "gold"), ("X", 2, "", ""), ("B", 3, 2, "silver"),
                               ("C", 3, 2, "silver"), ("D", 5, 4, "")])
        self.assertEqual(ss.standings(srk)[0]["members"], "a")


if __name__ == "__main__":
    unittest.main()
