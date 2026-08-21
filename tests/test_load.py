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

        # all three contest problems are observed cells for the single row,
        # even though only A was attempted
        self.assertEqual(ds.obs_row.tolist(), [0, 0, 0])
        self.assertEqual(ds.obs_prob.tolist(), [0, 1, 2])
        self.assertEqual(ds.obs_y.tolist(), [True, False, False])

    def test_unknown_problem_solve_does_not_retain_row(self):
        contest = {
            "contest_id": 2,
            "contest_name": "Partial metadata",
            "year": 2026,
            "region": "",
            "problems": [
                {"problem_id": 1, "problem_label": "A", "problem_name": "A",
                 "problem_solved_in_contest": 0},
            ],
            "standings": [{
                "rank": 1,
                "team_id": "team-2",
                "team_name": "team-2",
                "members": [],
                "total_solved": 1,
                "problems": {
                    "B": {"solved": True, "time_seconds": 100,
                          "wrong_attempts": 0},
                },
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contest.json"
            path.write_text(json.dumps([contest]))
            ds = load(str(path))

        self.assertEqual(len(ds.team_of_row), 0)
        self.assertEqual(len(ds.problems), 1)


if __name__ == "__main__":
    unittest.main()
