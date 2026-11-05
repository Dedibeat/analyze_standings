import unittest

import numpy as np

from arch_a import elo
from arch_b import context_fit as cf
from arch_b import model
from tests.test_dynamic_rating import _contests, _load


def _fields(n_teams=60, n_contests=6, mirror_lift=150.0, seed=3):
    """Every team plays every contest; in the last three, odd teams play as mirrors, ``mirror_lift`` stronger."""
    rng = np.random.default_rng(seed)
    theta = {f"t{i}": float(v) for i, v in enumerate(rng.normal(2100, 350, n_teams))}
    fields = []
    for c in range(n_contests):
        fields.append({t: v + (mirror_lift if c >= 3 and int(t[1:]) % 2 else 0.0) for t, v in theta.items()})
    return fields


class ContextFitTest(unittest.TestCase):
    def setUp(self):
        raw = _contests(_fields(), n_problems=12, seed=4)
        self.ds = _load(raw)
        by_id = {c["contest_id"]: c for c in raw}
        team = np.array([int(by_id[cid]["standings"][r]["team_id"][1:]) for cid, r in self.ds.participation_of_row])
        self.ctx = ((self.ds.contest_of_row >= 3) & (team % 2 == 1)).astype(int)

    def test_no_context_reproduces_the_binary_fit(self):
        theta, b, delta, gamma, _ = cf.fit(self.ds, np.zeros_like(self.ctx), 1)
        theta0, b0, _ = model.fit(self.ds, verbose=False)
        np.testing.assert_allclose(theta, theta0, atol=1e-6)
        np.testing.assert_allclose(b, b0, atol=1e-6)
        self.assertEqual(delta.tolist(), [0.0])

    def test_a_planted_mirror_lift_is_recovered_within_team(self):
        _theta, _b, delta, _gamma, _ = cf.fit(self.ds, self.ctx, 2)
        self.assertGreater(delta[1], 60.0)
        self.assertLess(delta[1], 260.0)
        _theta, _b, null, _gamma, _ = cf.fit(_load(_contests(_fields(mirror_lift=0.0), n_problems=12, seed=4)),
                                             self.ctx, 2)
        self.assertLess(abs(null[1]), 60.0)

    def test_offsets_apply_only_to_the_chosen_teams(self):
        apply = np.zeros(len(self.ds.teams), bool)
        theta, b, delta, _gamma, _ = cf.fit(self.ds, self.ctx, 2, apply=apply)
        theta0, b0, _ = model.fit(self.ds, verbose=False)
        np.testing.assert_allclose(b, b0, atol=1e-6)
        self.assertEqual(delta[1], 0.0)

    def test_a_team_seen_only_as_a_mirror_is_converted_to_the_reference_context(self):
        theta, delta, gamma = np.array([2300.0]), np.array([0.0, 150.0]), np.zeros(2)
        seen = np.array([[0, 4]])
        apply = np.zeros(1, bool)
        team, k = np.array([0, 0]), np.array([1, 0])
        np.testing.assert_allclose(cf.row_ability(theta, delta, gamma, team, k, apply, seen), [2300.0, 2150.0])
        np.testing.assert_allclose(cf.row_ability(theta, delta, gamma, team, k, ~apply, seen), [2450.0, 2300.0])

    def test_entry_groups_follow_the_contexts_a_team_was_seen_in(self):
        seen = np.array([[0, 0, 0], [3, 0, 0], [0, 2, 0], [0, 0, 1], [1, 1, 0]])
        self.assertEqual(cf.entry_groups(seen).tolist(), [0, 0, 1, 2, 3])

    def test_a_group_prior_mean_follows_its_teams(self):
        group = np.zeros(len(self.ds.teams), int)
        strong = np.argsort(model.fit(self.ds, verbose=False)[0])[-20:]
        group[strong] = 1
        theta, *_ = cf.fit(self.ds, np.zeros_like(self.ctx), 1, group=group)
        mu = cf.group_means(theta, group)
        self.assertEqual(mu[0], cf.MU0)
        self.assertAlmostEqual(mu[1], theta[strong].mean(), delta=1.0)
        theta0, *_ = cf.fit(self.ds, np.zeros_like(self.ctx), 1)
        self.assertGreater(theta[strong].mean(), theta0[strong].mean())   # less shrinkage toward MU0

    def test_slope_keeps_the_response_increasing_in_ability(self):
        theta, b, delta, gamma, _ = cf.fit(self.ds, self.ctx, 2, slope=True)
        self.assertGreater(1.0 + gamma[1], 0.0)
        a = cf.row_ability(np.array([1800.0, 2600.0]), delta, gamma, np.array([0, 1]), np.array([1, 1]),
                           np.ones(2, bool), np.ones((2, 2), int))
        self.assertLess(a[0], a[1])

    def test_mirror_rows_need_an_event_field_of_minimum_size(self):
        def board(cid, n_official):
            rows = [{"team_id": f"$DEFAULT_DAT_PREFIX_{i}", "members": [], "rank": i + 1,
                     "problems": {"A": {"solved": True, "time_seconds": 60}}} for i in range(n_official)]
            rows += [{"team_id": "ucup-team9", "members": [], "rank": n_official + 1,
                      "problems": {"A": {"solved": True, "time_seconds": 60}}},
                     {"team_id": "someone", "members": [], "rank": n_official + 2,
                      "problems": {"A": {"solved": True, "time_seconds": 60}}}]
            return {"contest_id": cid, "contest_name": str(cid), "year": 2024, "region": "",
                    "problems": [{"problem_id": cid, "problem_label": "A", "problem_name": "A"}],
                    "standings": rows}
        raw = [board(1, cf.MIN_EVENT_FIELD), board(2, cf.MIN_EVENT_FIELD - 1)]
        ds = _load(raw)
        ctx = cf.row_context(ds, {c["contest_id"]: c for c in raw})
        by_contest = {cid: sorted(ctx[ds.contest_of_row == ci].tolist()) for ci, cid in enumerate(ds.contests)}
        self.assertEqual(by_contest[1], [0] * cf.MIN_EVENT_FIELD + [1, 2])
        self.assertEqual(by_contest[2], [0] * (cf.MIN_EVENT_FIELD + 1))

    def test_transfer_drops_a_held_out_event_teams_other_rows_on_that_board(self):
        contest = np.array([0, 0, 0, 1, 1, 1])
        team = np.array([5, 5, 6, 5, 7, 7])
        event = np.array([True, False, True, True, False, True])
        test, train = cf.transfer_masks(contest, team, event, np.array([0]))
        self.assertEqual(test.tolist(), [True, False, True, False, False, False])
        self.assertEqual(train.tolist(), [False, False, False, True, True, True])

    def test_split_half_never_uses_the_scored_cell(self):
        import dataclasses
        cells = np.ones(len(self.ds.obs_y), bool)
        _theta, b, _ = model.fit(self.ds, verbose=False)
        idx, p = cf.split_half_probs(self.ds, b, cells)
        flipped = self.ds.obs_y.copy()
        flipped[7] = ~flipped[7]
        _idx, q = cf.split_half_probs(dataclasses.replace(self.ds, obs_y=flipped), b, cells)
        self.assertEqual(p[7], q[7])
        self.assertNotEqual(p[6], q[6])     # cell 6 is in the other half of the same row

if __name__ == "__main__":
    unittest.main()
