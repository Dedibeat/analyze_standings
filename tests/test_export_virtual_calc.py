import unittest
from types import SimpleNamespace

import numpy as np

from arch_b.export_virtual_calc import _performance_lookup


class VirtualCalculatorExportTest(unittest.TestCase):
    def test_performance_is_keyed_by_source_participation_not_identity(self):
        ds = SimpleNamespace(
            team_of_row=np.array([0, 0]),
            participation_of_row=[(123, 4), (123, 9)],
        )

        lookup = _performance_lookup(ds, np.array([1500.0, 2500.0]), float)

        self.assertEqual(lookup[(123, 4)], (0, 1500.0))
        self.assertEqual(lookup[(123, 9)], (0, 2500.0))


if __name__ == "__main__":
    unittest.main()
