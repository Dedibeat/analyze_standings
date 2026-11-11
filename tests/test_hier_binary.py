import unittest
from types import SimpleNamespace

import numpy as np

from arch_a import elo
from arch_b import hier_binary as hb
from arch_b import model


def simulate(seed=0, boards=((2400, 40), (1600, 40)), n_problems=8, linked=6):
    """Boards of single-appearance teams at different levels, plus a few linking teams."""
    rng = np.random.default_rng(seed)
    teams, t_row, c_row, true_t = [], [], [], []
    for c, (level, n) in enumerate(boards):
        for k in range(n):
            teams.append(f"c{c}t{k}")
            true_t.append(rng.normal(level, 150))
            t_row.append(len(teams) - 1)
            c_row.append(c)
    for k in range(linked):                        # teams seen on every board
        teams.append(f"link{k}")
        true_t.append(rng.normal(2000, 300))
        for c in range(len(boards)):
            t_row.append(len(teams) - 1)
            c_row.append(c)
    true_b = np.concatenate([np.linspace(lvl - 500, lvl + 500, n_problems) for lvl, _ in boards])
    p_c = np.repeat(np.arange(len(boards)), n_problems)
    obs_row, obs_prob, obs_y = [], [], []
    for r, (t, c) in enumerate(zip(t_row, c_row)):
        for p in np.flatnonzero(p_c == c):
            obs_row.append(r)
            obs_prob.append(p)
            obs_y.append(rng.random() < elo.pi(true_t[t], true_b[p]))
    t_row, c_row = np.array(t_row), np.array(c_row)
    solves = np.bincount(np.array(obs_row), np.array(obs_y, float), len(t_row))
    rank = np.zeros(len(t_row), int)
    for c in range(len(boards)):
        idx = np.flatnonzero(c_row == c)
        rank[idx] = 1 + np.argsort(np.argsort(-solves[idx], kind="stable"), kind="stable")
    ds = SimpleNamespace(teams=teams, contests=list(range(len(boards))),
                         problems=[(c, str(p), p, "") for p, c in enumerate(p_c)],
                         team_of_row=t_row, contest_of_row=c_row, rank_of_row=rank,
                         obs_row=np.array(obs_row), obs_prob=np.array(obs_prob),
                         obs_y=np.array(obs_y, bool), contest_of_problem=p_c)
    return ds, np.array(true_t), true_b


class FitTest(unittest.TestCase):
    def test_flat_settings_reproduce_model_fit(self):
        ds, _, _ = simulate()
        flat = hb.fit(ds, sigma=400, tau=0, sigma_b=400, tau_b=0)
        th, b, _ = model.fit(ds, verbose=False, eps=1e-5, max_iter=5000)
        self.assertTrue(np.all((b > elo.LO) & (b < elo.HI)))
        np.testing.assert_allclose(flat["b"], b, atol=0.05)
        np.testing.assert_allclose(flat["theta"], th, atol=0.05)

    def test_ability_level_is_anchored_on_board_means(self):
        ds, _, _ = simulate(seed=1)
        res = hb.fit(ds)
        self.assertAlmostEqual(float(res["mu"].mean()), hb.MU0, places=3)
        self.assertLess(res["max_step"], 1e-3)

    def test_board_mean_removes_strong_board_shrinkage(self):
        ds, _, true_b = simulate(seed=2)
        flat = hb.fit(ds, sigma=400, tau=0, sigma_b=400, tau_b=0)["b"]
        hier = hb.fit(ds, sigma=250, tau=600, sigma_b=400, tau_b=400)["b"]

        def gap(b):                                 # board 0 minus board 1 level
            return (b[:8].mean() - b[8:].mean())
        truth = gap(true_b)
        self.assertLess(abs(gap(hier) - truth), abs(gap(flat) - truth))

    def test_rows_mask_defines_board_membership(self):
        ds, _, _ = simulate(seed=3)
        rows = ds.contest_of_row == 0
        cells = rows[ds.obs_row]
        res = hb.fit(ds, obs=(ds.team_of_row[ds.obs_row][cells], ds.obs_prob[cells], ds.obs_y[cells]), rows=rows)
        only_board1 = [i for i, t in enumerate(ds.teams) if t.startswith("c1")]
        np.testing.assert_allclose(res["theta"][only_board1], hb.MU0, atol=1e-6)


    def test_row_prior_makes_board_means_levels(self):
        ds, _, _ = simulate(seed=6, linked=12)
        res = hb.fit(ds, sigma=300, tau=800, row_prior=True)
        # each mu is the 1/n_t-weighted mean ability of its board's teams, shrunk toward 2000
        n = np.bincount(ds.team_of_row)[ds.team_of_row]
        num = np.bincount(ds.contest_of_row, res["theta"][ds.team_of_row] / n) / 300 ** 2 + hb.MU0 / 800 ** 2
        den = np.bincount(ds.contest_of_row, 1 / n) / 300 ** 2 + 1 / 800 ** 2
        np.testing.assert_allclose(res["mu"], num / den, atol=0.01)

    def test_row_prior_changes_nothing_without_linking_teams(self):
        ds, _, _ = simulate(seed=7, linked=0)
        a, b = hb.fit(ds), hb.fit(ds, row_prior=True)
        for k in ("theta", "b", "mu"):
            np.testing.assert_allclose(a[k], b[k], atol=0.01)


class SplitAndScoreTest(unittest.TestCase):
    def test_split_holds_out_whole_appearances(self):
        ds, _, _ = simulate(seed=4)
        ds.team_of_row = np.r_[ds.team_of_row, ds.team_of_row[:3]]   # replay rows of one appearance group
        ds.contest_of_row = np.r_[ds.contest_of_row, ds.contest_of_row[:3]]
        held = hb.appearance_split(ds, 0)
        key = list(zip(ds.contest_of_row, ds.team_of_row))
        for k in set(key):
            vals = {bool(h) for h, kk in zip(held, key) if kk == k}
            self.assertEqual(len(vals), 1)

    def test_scores_count_linked_pairs_and_cells(self):
        ds, true_t, true_b = simulate(seed=5)
        held = np.zeros(len(ds.team_of_row), bool)
        held[-12:] = True                            # the linking teams' rows
        sc = hb.team_scores(ds, held, true_t, true_b, "binary")
        cells = held[ds.obs_row].sum()
        self.assertEqual(int(sc["all"][:, 2].sum()), cells)
        self.assertEqual(int(sc["linked"][:, 2].sum()), 0)    # every held team is unseen in training
        self.assertEqual(int(sc["pairs"][:, 1].sum()), 0)
        held[:] = False
        held[[0, 1, 2, 3]] = True                    # single-appearance teams: cold
        sc = hb.team_scores(ds, held, true_t, true_b, "binary")
        self.assertEqual(int(sc["cold"][:, 2].sum()), held[ds.obs_row].sum())


if __name__ == "__main__":
    unittest.main()
