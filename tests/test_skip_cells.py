import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from arch_b import hier_binary as hb
from arch_b import skip_cells as sc
from tests.test_hier_binary import simulate

# One board, three problems. (row, problem, solved, wrong attempts).
# Solves: P0 rows 0-3 (4), P1 rows 0-2 and 5 (4), P2 rows 2 and 4 (2).
CELLS = [
    (0, 0, 1, 0), (0, 1, 1, 0), (0, 2, 0, 1),
    (1, 0, 1, 0), (1, 1, 1, 0), (1, 2, 0, 0),
    (2, 0, 1, 0), (2, 1, 1, 0), (2, 2, 1, 0),
    (3, 0, 1, 0), (3, 1, 0, 0), (3, 2, 0, 0),
    (4, 0, 0, 0), (4, 1, 0, 0), (4, 2, 1, 0),   # mirror account: solved only P2
    (5, 0, 0, 2), (5, 1, 1, 0), (5, 2, 0, 1),
]


def board():
    r, p, y, w = (np.array(v) for v in zip(*CELLS))
    return SimpleNamespace(teams=[f"t{i}" for i in range(6)], problems=[(0, str(i), i, "") for i in range(3)],
                           team_of_row=np.arange(6), contest_of_row=np.zeros(6, int),
                           obs_row=r, obs_prob=p, obs_y=y.astype(bool), obs_wrong=w)


def marked(ds, mask):
    return {(int(ds.obs_row[i]), int(ds.obs_prob[i])) for i in np.flatnonzero(mask)}


class SkipTest(unittest.TestCase):
    def test_skip_all_marks_unsubmitted_easier_cells(self):
        ds = board()
        # row 4 never submitted P0/P1, both solved more than its P2; row 3's unsubmitted
        # P1/P2 are not easier than its hardest solve; row 5's P0 had attempts
        self.assertEqual(marked(ds, sc.skipped(ds, np.ones(len(CELLS), bool), "skip_all")), {(4, 0), (4, 1)})

    def test_base_marks_nothing(self):
        ds = board()
        self.assertFalse(sc.skipped(ds, np.ones(len(CELLS), bool), "base").any())

    def test_partial_rule_depends_on_submission_count(self):
        ds = board()
        every = np.ones(len(CELLS), bool)
        self.assertEqual(marked(ds, sc.skipped(ds, every, "skip_partial")), {(4, 0), (4, 1)})  # tried 1
        with mock.patch.object(sc, "PARTIAL_MAX", 0):
            self.assertFalse(sc.skipped(ds, every, "skip_partial").any())

    def test_solve_counts_come_from_the_given_cells_only(self):
        ds = board()
        cells = ~np.isin(ds.obs_row, [0, 1, 3])   # P0 now 1 solve, P1 2, P2 2: nothing easier for row 4
        skip = sc.skipped(ds, cells, "skip_all")
        self.assertFalse(skip.any())

    def test_cell_mask_restricts_team_scores(self):
        ds, _, _ = simulate(seed=3)
        res = hb.fit(ds)
        held = np.zeros(len(ds.team_of_row), bool)
        held[::5] = True
        mask = ds.obs_prob % 2 == 0
        full = hb.summarize(hb.team_scores(ds, held, res["theta"], res["b"], "binary"))
        part = hb.summarize(hb.team_scores(ds, held, res["theta"], res["b"], "binary", mask))
        self.assertEqual(part["cells"], int((held[ds.obs_row] & mask).sum()))
        self.assertLess(part["cells"], full["cells"])


if __name__ == "__main__":
    unittest.main()
