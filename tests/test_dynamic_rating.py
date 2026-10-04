import json
import os
import tempfile
import unittest

import numpy as np

from arch_a import elo
from arch_a.load import load
from arch_b import dynamic_rating as dr
from arch_b import model, survival

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)


def _contests(abilities, n_problems=8, seed=0):
    """Rasch-simulated contests; ``abilities[c][team]`` is a team's ability in contest c."""
    rng = np.random.default_rng(seed)
    out = []
    for c, field in enumerate(abilities):
        labels = [chr(65 + p) for p in range(n_problems)]
        b = np.linspace(1500, 2600, n_problems)
        rows = []
        for team, theta in field.items():
            solved = rng.random(n_problems) < elo.pi(theta, b)
            if not solved.any():
                solved[0] = True
            rows.append({"team_id": team, "team_name": team, "members": [f"{team}-x", f"{team}-y"],
                         "total_solved": int(solved.sum()),
                         "problems": {l: {"solved": bool(s), "time_seconds": 600 if s else None,
                                          "wrong_attempts": 0} for l, s in zip(labels, solved)}})
        rows.sort(key=lambda r: -r["total_solved"])
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        out.append({"contest_id": 100 + c, "contest_name": f"Contest {c}", "year": 2024, "region": "",
                    "problems": [{"problem_id": 1000 * c + p, "problem_label": l, "problem_name": l,
                                  "problem_solved_in_contest": 0} for p, l in enumerate(labels)],
                    "standings": rows})
    return out


def _load(contests):
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "contests.json")
        with open(path, "w") as f:
            json.dump(contests, f)
        return load(path)


class DynamicRatingTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        base = {f"t{i}": float(v) for i, v in enumerate(rng.normal(2000, 300, 40))}
        fields = []
        for c in range(4):
            field = dict(base)
            field["riser"] = 1600.0 + 400.0 * c        # improves by 400 per contest
            fields.append(field)
        self.ds = _load(_contests(fields))
        self.day = np.array([dr._day("2024-01-01") + 180.0 * c for c in range(4)])

    def test_q0_is_the_static_fit(self):
        for kind, mod in (("binary", model), ("survival", survival)):
            theta, b, _ = mod.fit(self.ds, verbose=False)
            node_theta, node_b, node_of_row, _, _ = dr.smooth_fit(self.ds, self.day, q=0.0, kind=kind)
            np.testing.assert_allclose(node_b, b, atol=1e-3, err_msg=kind)
            np.testing.assert_allclose(node_theta[node_of_row], theta[self.ds.team_of_row], atol=1e-3,
                                       err_msg=kind)

    def test_random_walk_tracks_an_improving_team(self):
        riser = self.ds.teams.index(next(t for t in self.ds.teams if "riser" in t))
        rows = np.flatnonzero(self.ds.team_of_row == riser)
        node_theta, _, node_of_row, _, _ = dr.smooth_fit(self.ds, self.day, q=400.0)
        path = node_theta[node_of_row[rows]][np.argsort(self.day[self.ds.contest_of_row[rows]])]
        self.assertTrue(np.all(np.diff(path) > 0), path)
        self.assertGreater(path[-1] - path[0], 300)

    def test_chain_solve_matches_dense_solve(self):
        rng = np.random.default_rng(2)
        first = np.array([1, 0, 0, 1, 1, 0, 0, 0], bool)
        n = len(first)
        off = np.where(first, 0.0, -rng.random(n))
        diag, rhs = 3 + rng.random(n), rng.random(n)
        pos = np.zeros(n, int)
        for i in np.flatnonzero(~first):
            pos[i] = pos[i - 1] + 1
        dense = np.diag(diag)
        for i in np.flatnonzero(~first):
            dense[i, i - 1] = dense[i - 1, i] = off[i]
        x = dr._chain_solve(diag, off, rhs, first, [np.flatnonzero(pos == k) for k in range(pos.max() + 1)])
        np.testing.assert_allclose(x, np.linalg.solve(dense, rhs), atol=1e-12)

    def test_filter_first_contest_is_its_own_map(self):
        snaps = dr.filter_ratings(self.ds, self.day, q=100.0, snapshots=[self.day[1]])
        rating, last = snaps[0]
        first = self.ds.obs_row[self.ds.contest_of_row[self.ds.obs_row] == 0]
        cells = np.isin(self.ds.obs_row, first)
        theta, _, _ = model.fit(self.ds, verbose=False, obs=(self.ds.team_of_row[self.ds.obs_row[cells]],
                                                             self.ds.obs_prob[cells],
                                                             self.ds.obs_y[cells].astype(float)))
        played = ~np.isnan(rating)
        np.testing.assert_allclose(rating[played], theta[played], atol=1.0)
        self.assertTrue(np.all(last[played] == self.day[0]))

    def test_perfect_forecast_orders_every_pair(self):
        rows = np.flatnonzero(self.ds.contest_of_row == 1)
        forecast = -self.ds.rank_of_row.astype(float)
        s = dr.summarize(dr.contest_scores(self.ds, rows, forecast, np.zeros(len(self.ds.problems))))
        self.assertEqual(s["accuracy"], 1.0)
        reverse = dr.summarize(dr.contest_scores(self.ds, rows, -forecast, np.zeros(len(self.ds.problems))))
        self.assertEqual(reverse["accuracy"], 0.0)

    def test_contest_day_rules(self):
        day = lambda iso: dr._day(iso)
        self.assertEqual(dr.contest_day({"contest_id": 1821, "year": 2017, "contest_name": "X"}, "ucup"),
                         day("2024-10-27"))
        self.assertEqual(dr.contest_day({"contest_id": 2524, "year": 2025, "contest_name": "EC Online (II)"},
                                        "tagged"), day("2025-09-21"))
        # uploaded a year after the event: falls back to the season's typical day
        self.assertEqual(dr.contest_day({"contest_id": 2605, "year": 2023, "contest_name": "NWERC"}, "tagged"),
                         day("2023-11-15"))
        self.assertEqual(dr.contest_day({"contest_id": 1967, "year": 2024,
                                         "contest_name": "The 2024 ICPC Europe Championship"}, "tagged"),
                         day("2024-04-15"))
        self.assertEqual(dr.contest_day({"contest_id": 1885, "year": 2024, "contest_name": "Hong Kong"}, "tagged"),
                         day("2024-12-22"))
        self.assertEqual(dr.contest_day({"contest_id": 3541, "year": 2026,
                                         "contest_name": "Petrozavodsk Winter 2026. Day 3"}, "petroz"),
                         day("2026-02-01"))


class DynamicRatingResultTest(unittest.TestCase):
    """The recorded findings in output/dynamic_rating.json (see details.md, 2026-10-04)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "output", "dynamic_rating.json"), encoding="utf-8") as f:
            cls.out = json.load(f)

    def test_static_rating_is_too_high_early_and_too_low_late(self):
        r = self.out["retrospective"]
        span = list(r["static_residual_by_span_fraction"].values())
        self.assertLess(span[0][0], 0)
        self.assertGreater(span[-1][0], 0)
        self.assertGreater(r["static_residual_slope"]["all"], 0)
        self.assertGreater(r["q50"]["b_shift_by_year"]["2025"], r["q50"]["b_shift_by_year"]["2022"])

    def test_member_prior_beats_flat_prior_for_new_rosters(self):
        test = self.out["forecast"]["history_plus_new_with_members/test_2024_2026"]
        delta = test["static+members"]["minus_static+cold_MU0"]
        self.assertGreater(delta["accuracy"][1], 0)        # whole interval above zero
        self.assertLess(delta["cell_log_loss"][2], 0)

    def test_cf_rmse_q0_is_the_shipped_metric(self):
        cf = self.out["cf_rmse"]
        self.assertAlmostEqual(cf["0"]["survival"]["gym_shaped"], 244.6, delta=0.05)   # arch_b.metric
        self.assertAlmostEqual(cf["0"]["survival"]["raw_affine"], 246.7, delta=0.05)
        for q in ("25", "50", "100"):
            self.assertEqual(cf[q]["survival"]["anchors"], [185, 15])

    def test_cf_filter_loses_to_the_joint_fit(self):
        test = self.out["forecast"]["history/test_2024_2026"]
        self.assertLess(test["cf_filter_q100"]["accuracy"], test["static"]["accuracy"])


if __name__ == "__main__":
    unittest.main()
