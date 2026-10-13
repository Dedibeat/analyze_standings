import unittest
from types import SimpleNamespace

import numpy as np

from arch_a.fixedpoint import _performance_ratings
from arch_b.export_virtual_calc import (MIN_EVENT_FIELD, _event_participations, _performance_lookup,
                                        _rank_official_within_event)


class VirtualCalculatorExportTest(unittest.TestCase):
    def test_performance_is_keyed_by_source_participation_not_identity(self):
        ds = SimpleNamespace(
            team_of_row=np.array([0, 0]),
            participation_of_row=[(123, 4), (123, 9)],
        )

        lookup = _performance_lookup(ds, np.array([1500.0, 2500.0]), float)

        self.assertEqual(lookup[(123, 4)], (0, 1500.0))
        self.assertEqual(lookup[(123, 9)], (0, 2500.0))

    def test_official_rows_of_a_merged_board_are_ranked_within_their_event(self):
        n_mirror, n_official = 10, 40  # mirror entries finish on top of the board
        theta = np.linspace(3000, 1500, n_mirror + n_official)
        ds = SimpleNamespace(team_of_row=np.arange(50), rank_of_row=np.arange(1, 51),
                             official_of_row=np.arange(50) >= n_mirror)
        rows = [np.arange(50)]
        rho = _performance_ratings(theta, ds, rows)

        out = _rank_official_within_event(theta, ds, rows, rho)

        alone = SimpleNamespace(team_of_row=np.arange(n_official), rank_of_row=np.arange(1, n_official + 1))
        np.testing.assert_allclose(out[n_mirror:], _performance_ratings(theta[n_mirror:], alone, [np.arange(n_official)]))
        np.testing.assert_array_equal(out[:n_mirror], rho[:n_mirror])  # mirror rows keep the whole board

    def test_only_official_rows_of_a_merged_board_are_flagged_as_event_rows(self):
        n = MIN_EVENT_FIELD + 5
        ds = SimpleNamespace(contests=[1, 2], contest_of_row=np.repeat([0, 1], n),
                             official_of_row=np.concatenate([np.arange(n) >= 5, np.ones(n, bool)]),
                             participation_of_row=[(1, i) for i in range(n)] + [(2, i) for i in range(n)])
        # contest 1 merges 5 mirror rows with its official field; contest 2 is all official
        self.assertEqual(_event_participations(ds), {(1, i) for i in range(5, n)})

    def test_an_event_below_the_minimum_field_keeps_the_whole_board(self):
        n = MIN_EVENT_FIELD + 9  # MIN_EVENT_FIELD - 1 official rows
        ds = SimpleNamespace(team_of_row=np.arange(n), rank_of_row=np.arange(1, n + 1),
                             official_of_row=np.arange(n) >= 10)
        theta, rows = np.linspace(2600, 1500, n), [np.arange(n)]
        rho = _performance_ratings(theta, ds, rows)
        np.testing.assert_array_equal(_rank_official_within_event(theta, ds, rows, rho), rho)


if __name__ == "__main__":
    unittest.main()
