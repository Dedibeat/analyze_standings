import unittest

import numpy as np

from arch_a import elo
from arch_b import hier_binary as hb
from arch_b import hier_time as ht
from tests.test_hier_binary import simulate


def timed(seed=0, d=(2.5, 1.0)):
    """simulate() plus solve times drawn from the slice model with thresholds ``d``."""
    ds, true_t, true_b = simulate(seed=seed, boards=((2400, 150), (1600, 150)))
    rng = np.random.default_rng(seed + 100)
    g = (true_t[ds.team_of_row[ds.obs_row]] - true_b[ds.obs_prob]) / elo.S
    cdf = 1 / (1 + np.exp(-(g[:, None] - np.r_[d, 0.0])))        # P(solved by the end of slice k)
    u = rng.random(len(g))
    k = 1 + np.sum(u[:, None] > cdf, axis=1)                     # len(d) + 2 means unsolved
    ds.obs_y = k <= len(d) + 1
    ds.obs_tau = np.where(ds.obs_y, (k - 0.5) / (len(d) + 1) * 18000.0, np.nan)
    ds.obs_tau[np.flatnonzero(ds.obs_y)[-1]] = 18000.0           # one solve at the bell fixes T_c
    ds.obs_wrong = np.zeros(len(g), int)
    return ds, true_b


class IntervalLikelihoodTest(unittest.TestCase):
    def test_binary_intervals_reproduce_the_binary_fit(self):
        ds, _, _ = simulate(seed=6)
        y = ds.obs_y
        cuts = (np.where(y, 0.0, -np.inf), np.where(y, np.inf, 0.0))
        plain, cut = hb.fit(ds), hb.fit(ds, cuts=cuts)
        np.testing.assert_allclose(cut["b"], plain["b"], atol=1e-3)
        np.testing.assert_allclose(cut["theta"], plain["theta"], atol=1e-3)

    def test_zero_weight_ignores_the_intervals(self):
        ds, _, _ = simulate(seed=7)
        cuts = (np.full(len(ds.obs_y), -1.0), np.full(len(ds.obs_y), 1.0))
        np.testing.assert_allclose(hb.fit(ds, cuts=cuts, cut_weight=0.0)["b"], hb.fit(ds)["b"], atol=1e-6)

    def test_warm_start_returns_the_same_optimum(self):
        ds, _, _ = simulate(seed=8)
        cold = hb.fit(ds)
        warm = hb.fit(ds, start=cold["x"])
        self.assertEqual(warm["newton"], 1)
        np.testing.assert_allclose(warm["b"], cold["b"], atol=1e-3)


class TimeFitTest(unittest.TestCase):
    def test_thresholds_recover_the_simulated_values(self):
        rng = np.random.default_rng(1)
        g, d = rng.normal(0, 2, 40000), np.array([3.0, 1.2])
        cdf = 1 / (1 + np.exp(-(g[:, None] - np.r_[d, 0.0])))
        k = 1 + np.sum(rng.random(len(g))[:, None] > cdf, axis=1)
        solved = k <= 3
        np.testing.assert_allclose(ht.thresholds(g[solved], k[solved], np.array([2.0, 0.5])), d, atol=0.08)

    def test_base_setting_is_the_frozen_binary_fit(self):
        ds, _ = timed(seed=2)
        np.testing.assert_array_equal(ht.fit(ds, ht.BASE)["b"], hb.fit(ds)["b"])

    def test_time_fit_orders_thresholds_and_keeps_the_scale(self):
        ds, true_b = timed(seed=3)
        res = ht.fit(ds, (3, 1.0, False))
        self.assertEqual(len(res["d"]), 2)
        self.assertTrue(res["d"][0] > res["d"][1] > 0)
        np.testing.assert_allclose(res["d"], [2.5, 1.0], atol=0.35)
        base = hb.fit(ds)["b"]
        # same generating scale: the time fit must not stretch or shift the difficulties
        slope, icept = np.polyfit(base, res["b"], 1)
        self.assertAlmostEqual(slope, 1.0, delta=0.1)
        self.assertLess(np.sqrt(np.mean((res["b"] - true_b) ** 2)), np.sqrt(np.mean((base - true_b) ** 2)) + 10)

    def test_names(self):
        self.assertEqual(ht.name(ht.BASE), "base")
        self.assertEqual(ht.name((5, 0.25, True)), "k5_w0.25_skip")


if __name__ == "__main__":
    unittest.main()
