import json
import tempfile
import unittest
from pathlib import Path

from arch_a.load import load


class LoadTest(unittest.TestCase):
    def test_unattempted_contest_problems_are_censored_non_solves(self):
        contest = {
            "contest_id": 1,
            "contest_name": "Test",
            "year": 2026,
            "region": "",
            "problems": [
                {"problem_id": 1, "problem_label": "A", "problem_name": "A",
                 "problem_solved_in_contest": 1},
                {"problem_id": 2, "problem_label": "B", "problem_name": "B",
                 "problem_solved_in_contest": 0},
                {"problem_id": 3, "problem_label": "C", "problem_name": "C",
                 "problem_solved_in_contest": 0},
            ],
            "standings": [{
                "rank": 1,
                "team_id": "team-1",
                "team_name": "team-1",
                "members": [],
                "total_solved": 1,
                "problems": {
                    "A": {"solved": True, "time_seconds": 100,
                          "wrong_attempts": 0},
                },
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contest.json"
            path.write_text(json.dumps([contest]))
            ds = load(str(path))

        self.assertEqual(ds.solve_mask[0].tolist(), [True, True, True])
        self.assertEqual(ds.y[0].tolist(), [True, False, False])


if __name__ == "__main__":
    unittest.main()
