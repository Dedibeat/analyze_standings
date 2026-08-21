import unittest

import numpy as np

from arch_a.load import Dataset
from arch_b.data_influence import (_bridge_subset, _loco_details,
                                   _without_cross_contest_links)


class DataInfluenceTest(unittest.TestCase):
    def test_loco_details_decomposes_pooled_error(self):
        z = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        cf = np.array([10.0, 12.0, 15.0, 16.0, 19.0, 23.0])
        groups = np.array([1, 1, 2, 2, 3, 3])

        pooled, detail = _loco_details(z, cf, groups)

        squared_error = sum(v["n"] * v["rmse"] ** 2 for v in detail.values())
        self.assertTrue(np.isclose(pooled, np.sqrt(squared_error / len(z))))
        self.assertEqual(set(detail), {"1", "2", "3"})

    def test_bridge_subset_uses_linked_rows_top_quartile(self):
        contests = [{"contest_id": cid} for cid in range(1, 5)]
        stats = [{"contest_id": cid, "tagged_linked_rows": linked}
                 for cid, linked in enumerate([1, 2, 3, 100], start=1)]

        self.assertEqual(_bridge_subset(contests, stats), [{"contest_id": 4}])

    def test_without_cross_contest_links_gives_every_row_an_identity(self):
        ds = Dataset(
            teams=["shared"], contests=[1, 2], problems=[],
            team_of_row=np.array([0, 0]), contest_of_row=np.array([0, 1]),
            rank_of_row=np.array([1, 1]),
            obs_row=np.array([], dtype=int), obs_prob=np.array([], dtype=int),
            obs_y=np.array([], dtype=bool), obs_tau=np.array([], dtype=np.float32),
            obs_wrong=np.array([], dtype=np.int32),
            solved_count=np.array([], dtype=int),
            field_count=np.array([], dtype=int),
            contest_of_problem=np.array([], dtype=int),
            raw_solved_count=np.array([], dtype=int))

        local = _without_cross_contest_links(ds)

        self.assertEqual(local.teams, ["row:0", "row:1"])
        self.assertEqual(local.team_of_row.tolist(), [0, 1])
        self.assertEqual(ds.team_of_row.tolist(), [0, 0])


if __name__ == "__main__":
    unittest.main()
