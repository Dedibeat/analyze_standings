"""The released fit and conversion must use the selected time dose and map."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from arch_b import shipped


class ShippedTest(unittest.TestCase):
    def tearDown(self):
        shipped.shipped_fit.cache_clear()
        shipped.release_metadata.cache_clear()

    def test_released_dose_and_shared_map(self):
        meta = {"setting": {"bins": 5, "time_weight": .25, "skip_partial": True},
                "map": {"slope": .867, "intercept": 605}}
        ds, uf = SimpleNamespace(), object()
        result = {"theta": np.array([2000.]), "b": np.array([1900.])}
        with patch.object(shipped, 'release_metadata', return_value=meta), \
             patch.object(shipped, 'load_joint_dataset', return_value=(ds, uf, None)), \
             patch.object(shipped, 'fit', return_value=result) as fit:
            fitted = shipped.shipped_fit()
            fit.assert_called_once_with(ds, (5, .25, True))
            self.assertIs(fitted[0], ds)
            self.assertIs(fitted[4], uf)
            self.assertAlmostEqual(shipped.to_cf(2000), 2339.)
            self.assertEqual(shipped.to_cf(-1000), 800.)
            self.assertEqual(shipped.to_cf(10000), 4000.)
