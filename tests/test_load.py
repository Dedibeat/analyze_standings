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

    def test_unknown_problem_solve_retains_row_as_failure(self):
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

        self.assertEqual(len(ds.team_of_row), 1)
        self.assertEqual(len(ds.problems), 1)
        self.assertEqual(ds.obs_y.tolist(), [False])

    def test_pre_start_solves_and_minute_rows(self):
        problems = [{"problem_id": i, "problem_label": l, "problem_name": l, "problem_solved_in_contest": 0}
                    for i, l in enumerate("AB")]

        def row(team, cells):
            return {"rank": 1, "team_id": team, "team_name": team, "members": [], "total_solved": 1,
                    "problems": {l: {"solved": True, "time_seconds": t, "wrong_attempts": 0} for l, t in cells.items()}}
        contests = [
            {"contest_id": 1483, "contest_name": "minutes", "year": 2023, "region": "", "problems": problems,
             "standings": [row("$DEFAULT_1", {"A": 4}), row("guest", {"A": 240})]},
            {"contest_id": 7, "contest_name": "early", "year": 2026, "region": "", "problems": problems,
             "standings": [row("before", {"A": -500}), row("mixed", {"A": -500, "B": 90})]},
            {"contest_id": 8, "contest_name": "no list", "year": 2026, "region": "", "problems": [],
             "standings": [row("x", {"A": 10})]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contest.json"
            path.write_text(json.dumps(contests))
            ds = load(str(path))

        # official rows of a minute board are converted; a pre-start solve is no solve;
        # a board that lists no problem keeps no row
        self.assertEqual(ds.participation_of_row, [(1483, 0), (1483, 1), (7, 1)])
        self.assertEqual(ds.obs_y.tolist(), [True, False, True, False, False, True])
        self.assertEqual(ds.obs_tau[ds.obs_y].tolist(), [240.0, 240.0, 90.0])

    def test_two_shared_members_never_merge_rows_of_one_contest(self):
        problems = [{"problem_id": 1, "problem_label": "A", "problem_name": "A", "problem_solved_in_contest": 1}]

        def row(n, members):
            return {"rank": n, "team_id": f"$DEFAULT_{n}", "team_name": f"t{n}", "members": members,
                    "total_solved": 1, "problems": {"A": {"solved": True, "time_seconds": 60, "wrong_attempts": 0}}}
        contests = [
            # a substitute: two shared members, different contests -> one team
            {"contest_id": 1, "contest_name": "one", "year": 2023, "region": "", "problems": problems,
             "standings": [row(1, ["a", "b", "c"])]},
            {"contest_id": 2, "contest_name": "two", "year": 2024, "region": "", "problems": problems,
             "standings": [row(1, ["a", "b", "d"]), row(2, ["b", "d", "e"])]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contest.json"
            path.write_text(json.dumps(contests))
            ds = load(str(path))

        # abc and abd link; bde shares b, d with abd but played contest 2 beside it
        self.assertEqual(ds.team_of_row[0], ds.team_of_row[1])
        self.assertNotEqual(ds.team_of_row[1], ds.team_of_row[2])


if __name__ == "__main__":
    unittest.main()
