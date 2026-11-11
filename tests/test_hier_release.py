import unittest
from unittest import mock

import numpy as np

from arch_a import elo
from arch_b import hier_release as hr
from tests.test_hier_binary import simulate


def dataset(seed=0):
    ds, _, _ = simulate(seed=seed)
    ds.obs_wrong = np.zeros(len(ds.obs_y), int)
    ds.solved_count = np.bincount(ds.obs_prob, ds.obs_y, len(ds.problems)).astype(int)
    ds.field_count = np.bincount(ds.obs_prob, minlength=len(ds.problems))
    ds.raw_solved_count = ds.solved_count
    ds.participation_of_row = [(int(c), r) for r, c in enumerate(ds.contest_of_row)]
    return ds


class ReleaseTest(unittest.TestCase):
    def test_problem_records_share_the_shipped_fields_and_one_map(self):
        ds = dataset()
        res, skip = hr.release_fit(ds)
        records = hr.problem_records(ds, res, skip, 0.9, 500.0)
        self.assertEqual(len(records), len(ds.problems))
        r = records[3]
        self.assertEqual((r["contest_id"], r["problem_label"], r["problem_id"]), (0, "3", 3))
        self.assertAlmostEqual(r["difficulty_cf"], np.clip(0.9 * res["b"][3] + 500, elo.LO, elo.HI), places=1)
        self.assertEqual(r["field_count"] + r["skipped_cells"], int(ds.field_count[3]))
        self.assertEqual(r["board_rows"], int(np.sum(ds.contest_of_row == 0)))
        self.assertFalse(r["small_board"])

    def test_skipped_cells_leave_the_fit(self):
        ds = dataset(seed=1)
        some = np.zeros(len(ds.obs_y), bool)
        some[:5] = True
        with mock.patch.object(hr, "skipped", return_value=some):
            res, skip = hr.release_fit(ds)
        records = hr.problem_records(ds, res, skip, 1.0, 0.0)
        self.assertEqual(sum(r["skipped_cells"] for r in records), 5)

    def test_cf_map_scores_each_contest_out_of_fold(self):
        b = np.array([1000.0, 1500, 2000, 2500, 3000, 3500])
        anchors = [{"row_id": i, "canonical_task": f"t{i}", "cf_contest": i // 2, "contest_id": 0,
                    "problem_label": str(i), "cf": 2 * b[i] - 100 + (300 if i == 5 else 0)} for i in range(6)]
        slope, icept, acc = hr.cf_map(b, anchors, {(0, str(i)): i for i in range(6)})
        self.assertEqual((acc["anchors"], acc["contests"]), (6, 3))
        self.assertGreater(acc["loco_rmse"], acc["fit_rmse"])   # the outlier is predicted without itself
        self.assertAlmostEqual(slope, 2.0, delta=0.2)

    def test_one_board_gap_is_measured_against_the_boards_own_teams(self):
        ds = dataset(seed=2)
        res, _ = hr.release_fit(ds)
        res["mu"] = res["mu"] + np.array([900.0, 0.0])   # board 0's mean far from its teams
        gaps = hr.one_off_prior_gaps(ds, res)
        one_board = np.bincount(ds.team_of_row)[ds.team_of_row] == 1
        self.assertEqual(len(gaps), int(one_board.sum()))
        self.assertTrue(np.all(gaps[ds.contest_of_row[one_board] == 0] > hr.MU_GAP))
        self.assertTrue(np.all(gaps[ds.contest_of_row[one_board] == 1] < hr.MU_GAP))

    def test_team_records_use_the_most_frequent_name(self):
        ds = dataset(seed=3)
        res, _ = hr.release_fit(ds)
        raw = {c: {"standings": [{"team_name": f"row{r}", "affiliation": "U"} for r in range(len(ds.team_of_row))]}
               for c in (0, 1)}
        link = len(ds.teams) - 1                         # a linking team: one row per board
        for r in np.flatnonzero(ds.team_of_row == link):
            raw[int(ds.contest_of_row[r])]["standings"][r]["team_name"] = "Linkers"
        teams = hr.team_records(ds, res, 1.0, 0.0, raw)
        hit = [t for t in teams if t["team_name"] == "Linkers"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["appearances"], 2)
        self.assertAlmostEqual(hit[0]["rating_cf"], res["theta"][link], places=1)
        self.assertEqual([t["rating_cf"] for t in teams], sorted((t["rating_cf"] for t in teams), reverse=True))


if __name__ == "__main__":
    unittest.main()
