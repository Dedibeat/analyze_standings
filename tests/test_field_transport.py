import unittest
from types import SimpleNamespace

import numpy as np

from arch_a import elo
from arch_b import field_transport as ft


class FieldTransportTest(unittest.TestCase):
    def test_fixed_ability_refit_does_not_depend_on_who_attempted(self):
        rng = np.random.default_rng(5)
        b_true = np.array([1700.0, 2100.0, 2500.0])
        theta = rng.normal(2100, 400, 6000)
        prob = np.tile(np.arange(3), len(theta))
        a = np.repeat(theta, 3)
        y = (rng.random(len(a)) < elo.pi(a, b_true[prob])).astype(float)
        strong = a > np.median(theta)
        b_strong, _ = ft.refit_b(prob[strong], y[strong], a[strong], n_problems=3)
        b_weak, _ = ft.refit_b(prob[~strong], y[~strong], a[~strong], n_problems=3)
        np.testing.assert_allclose(b_strong, b_true, atol=40)
        np.testing.assert_allclose(b_weak, b_true, atol=40)

    def test_refit_converges_where_a_plain_newton_step_bounces(self):
        # a strong field solving a hard problem rarely: Newton from 2000 jumps to the bounds
        theta = np.full(50, 2800.0)
        y = np.r_[np.ones(10), np.zeros(40)]
        b, _ = ft.refit_b(np.zeros(50, int), y, theta, n_problems=1)
        grad = -np.sum(y - elo.pi(theta, b[0])) / elo.S - (b[0] - 2000.0) / 400.0 ** 2
        self.assertLess(abs(grad), 1e-9)
        self.assertTrue(2800 < b[0] < 3500)

    def test_survival_refit_has_finite_difficulties_and_shrinking_errors(self):
        prob = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y = np.array([1, 1, 0, 0, 1, 0, 0, 0], float)
        theta = np.full(8, 2000.0)
        rho = np.where(y > 0, 0.5, 1.0)
        b, se = ft.refit_b(prob, y, theta, rho=rho, n_problems=2)
        _b, se_more = ft.refit_b(np.tile(prob, 4), np.tile(y, 4), np.tile(theta, 4), rho=np.tile(rho, 4),
                                 n_problems=2)
        self.assertTrue(np.all(np.isfinite(b)))
        self.assertLess(b[0], b[1])
        self.assertTrue(np.all(se_more < se))

    def test_reference_rate_is_a_decreasing_function_of_difficulty_only(self):
        r = ft.reference_rate([1800.0, 2000.0, 2600.0])
        self.assertTrue(np.all(np.diff(r) < 0))
        self.assertAlmostEqual(r[1], 0.5, places=6)    # symmetric population centred at the difficulty

    def test_a_team_never_sits_on_both_sides_of_the_target_split(self):
        exp = ft.Experiment.__new__(ft.Experiment)
        exp.ds = SimpleNamespace(team_of_row=np.array([0, 0, 1, 2, 2, 2, 3, 4, 5, 6, 7, 8, 9, 9]))
        rows = np.arange(14)
        for seed in range(20):
            target, pool, rows_of = exp.split_teams(rows, np.random.default_rng(seed))
            pool_rows = rows_of(pool)
            self.assertEqual(len(target) + len(pool_rows), 14)
            self.assertFalse(set(exp.ds.team_of_row[target]) & set(exp.ds.team_of_row[pool_rows]))

    def test_target_solve_times_do_not_change_training_exposures(self):
        exp = ft.Experiment.__new__(ft.Experiment)
        y = np.array([1, 1, 0, 1, 1, 0], bool)
        exp.ds = SimpleNamespace(obs_y=y, obs_row=np.array([0, 0, 1, 1, 2, 2]))
        cells = np.arange(6)
        exp.tau = np.array([100.0, 200.0, 0.0, 300.0, 900.0, 0.0])
        rho = exp.board_rho(cells, np.array([2]))
        exp.tau = np.array([100.0, 200.0, 0.0, 300.0, 9000.0, 0.0])
        np.testing.assert_allclose(exp.board_rho(cells, np.array([2]))[:4], rho[:4])
        np.testing.assert_allclose(rho[:4], [1 / 3, 2 / 3, 1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
