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

    def test_mirror_rule_spares_official_rows(self):
        ds = board()
        every = np.ones(len(CELLS), bool)
        ds.official_of_row = np.zeros(6, bool)
        self.assertEqual(marked(ds, sc.skipped(ds, every, "skip_mirror")), {(4, 0), (4, 1)})
        ds.official_of_row[4] = True
        self.assertFalse(sc.skipped(ds, every, "skip_mirror").any())

    def test_margin_rule_needs_a_clearly_easier_problem(self):
        ds = board()
        every = np.ones(len(CELLS), bool)
        # row 4: its solve P2 has failure odds 4/2, the skipped P0/P1 2/4: exactly 4 times lower
        self.assertEqual(marked(ds, sc.skipped(ds, every, "skip_margin")), {(4, 0), (4, 1)})
        with mock.patch.object(sc, "MARGIN", 4.5):
            self.assertFalse(sc.skipped(ds, every, "skip_margin").any())

    def test_early_rule_needs_an_early_median_solve(self):
        ds = board()
        every = np.ones(len(CELLS), bool)
        # P0 is solved at minutes 10, 20, 30, 40 (median 25); P1 at 50, 60, 70, 300 (median 65)
        minute = {(0, 0): 10, (1, 0): 20, (2, 0): 30, (3, 0): 40, (0, 1): 50, (1, 1): 60, (2, 1): 70, (5, 1): 300,
                  (2, 2): 100, (4, 2): 120}
        ds.obs_tau = np.array([60.0 * minute.get((r, p), np.nan) for r, p, _, _ in CELLS], dtype=np.float32)
        self.assertEqual(marked(ds, sc.skipped(ds, every, "skip_early")), {(4, 0)})
        with mock.patch.object(sc, "EARLY_MINUTES", 65.0):
            self.assertEqual(marked(ds, sc.skipped(ds, every, "skip_early")), {(4, 0), (4, 1)})
        ds.obs_tau[:] = np.nan
        self.assertFalse(sc.skipped(ds, every, "skip_early").any())

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
