import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import iccpc_standings as ist  # noqa: E402


def team(tid, tkind=0):
    return {"team_id": tid, "name": tid, "school": "S", "tmember": "a、b", "coach": "c", "tkind": tkind}


def run(sid, tid, pid, result, hms):
    return {"solution_id": sid, "team_id": tid, "problem_id": pid, "result": result,
            "in_date": f"2026-10-18 {hms}"}


class IccpcStandingsTest(unittest.TestCase):
    def setUp(self):
        self.data = {
            "contest": {"start_time": "2026-10-18 09:00:00", "award_ratio": 30020010,
                        "flg_award_base": 1, "flg_award_qty_mode": 0},
            "team": [team("A"), team("B"), team("C"), team("X", tkind=2), team("D"), team("E")],
            "solution": [
                run(1, "A", 1, 11, "09:01:00"),   # CE: no penalty
                run(2, "A", 1, 6, "09:02:00"),    # WA: +20 min
                run(3, "A", 1, 4, "09:10:30"),    # AC at 630 s -> 1830 s
                run(4, "A", 1, 6, "09:20:00"),    # after AC: ignored
                run(5, "B", 1, 4, "09:30:59"),    # 1859 s: same minute as A
                run(6, "C", 1, 4, "09:31:00"),    # 1860 s
                run(7, "X", 1, 4, "09:00:10"),    # star team, unranked
                run(8, "D", 1, 6, "09:05:00"),    # submitted, 0 solved
            ],
        }

    def test_ranks_tie_on_minutes_and_skip_star_teams(self):
        got = [(r["team_id"], r["rank"], r["official_rank"], r["penalty_minutes"]) for r in ist.standings(self.data)]
        self.assertEqual(got, [("X", 1, "", 0), ("A", 2, 1, 30), ("B", 2, 1, 30), ("C", 4, 3, 31),
                               ("D", 5, 4, 0), ("E", 5, 4, 0)])

    def test_medal_base_is_official_teams_that_submitted(self):
        # A, B, C, D submitted (E did not, X is a star team): B = 4 -> ceil(.4), ceil(1.2), ceil(2.4)
        self.assertEqual(ist.medal_lines(self.data), [1, 2, 3])
        medals = {r["team_id"]: r["medal"] for r in ist.standings(self.data)}
        self.assertEqual(medals, {"X": "", "A": "gold", "B": "gold", "C": "bronze", "D": "", "E": ""})


if __name__ == "__main__":
    unittest.main()
