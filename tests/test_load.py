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
        self.assertEqual(ds.participation_of_row, [(1, 0)])

    def _partial(self, problems):
        contest = {
            "contest_id": 2,
            "contest_name": "Partial metadata",
            "year": 2026,
            "region": "",
            "problems": problems,
            "standings": [
                {"rank": 1, "team_id": "team-2", "team_name": "team-2", "members": [],
                 "total_solved": 1,
                 "problems": {"B": {"solved": True, "time_seconds": 100, "wrong_attempts": 0}}},
                {"rank": 2, "team_id": "team-3", "team_name": "team-3", "members": [],
                 "total_solved": 0,
                 "problems": {"A": {"solved": False, "wrong_attempts": 2}}},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contest.json"
            path.write_text(json.dumps([contest]))
            return load(str(path))

    def test_unlisted_solve_retains_row_as_failure_of_listed_problems(self):
        # team-2 solved only the unlisted B: it took part, so it failed the listed A.
        # Dropping it would keep only rows that solved A (selection on the outcome).
        ds = self._partial([{"problem_id": 1, "problem_label": "A", "problem_name": "A",
                             "problem_solved_in_contest": 0}])
        self.assertEqual(ds.participation_of_row, [(2, 0)])   # the zero-solve row is still dropped
        self.assertEqual(ds.obs_y.tolist(), [False])
        self.assertEqual(ds.field_count.tolist(), [1])
        self.assertEqual(len(ds.problems), 1)

    def test_contest_without_listed_problems_keeps_no_rows(self):
        ds = self._partial([])
        self.assertEqual(len(ds.team_of_row), 0)
        self.assertEqual(len(ds.teams), 0)


if __name__ == "__main__":
    unittest.main()
