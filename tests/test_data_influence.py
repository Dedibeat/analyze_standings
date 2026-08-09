import unittest

import numpy as np

from arch_b.data_influence import _bridge_subset, _loco_details


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


if __name__ == "__main__":
    unittest.main()
