import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from arch_a.load import load
from arch_b import model, survival
from arch_b.calibration_ablation import fit_predict_fixed, select_inner_contests
from arch_b.de_release_audit import DE, bisquare_location, method, nested
from arch_b.fit_mechanism_audit import b_given_theta, fit_offsets

ROOT = Path(__file__).resolve().parent.parent


def _attach_module():
    spec = importlib.util.spec_from_file_location("attach_online_rosters",
                                                  ROOT / "scripts" / "attach_online_rosters.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _anchor_rows():
    rows = []
    for contest in range(1, 8):
        for problem in range(5):
            raw = 1200.0 + 90.0 * contest + 40.0 * problem
            gap = float((contest * 7 + problem * 3) % 5 - 2)
            rate = (problem + 1.0) / 6.0
            rows.append({"row_id": f"{contest}-{problem}", "cf_contest": contest,
                         "canonical_task": f"task-{contest}-{problem}", "raw_b": raw,
                         "binary_minus_survival": gap, "conditional_fit_se": 30.0 + 5 * rate,
                         "solve_rate": rate, "log_field_size": 4.0 + 0.3 * (contest % 3),
                         "cf": 1.5 * raw + 60.0 * gap - 200.0 * rate + 11.0 * ((contest + problem) % 4)})
    return rows


def _standings(seed=0):
    rng = np.random.default_rng(seed)
    ability = rng.normal(0, 1.2, 14)
    contests = []
    for cid in (1, 2):
        difficulty = np.linspace(-1.5, 1.5, 6) + (0.3 if cid == 2 else 0.0)
        standings = []
        for team in range(14):
            cells = {}
            for k, d in enumerate(difficulty):
                if rng.random() < 1 / (1 + np.exp(d - ability[team])):
                    cells["ABCDEF"[k]] = {"solved": True, "time_seconds": int(rng.integers(300, 18000)),
                                          "wrong_attempts": 0}
            if not cells:
                cells["A"] = {"solved": True, "time_seconds": 17000, "wrong_attempts": 0}
            standings.append({"rank": team + 1, "team_id": f"$DEFAULT_DAT_PREFIX_{team}",
                              "team_name": f"t{team}", "members": [f"m{team}a", f"m{team}b"],
                              "total_solved": len(cells), "problems": cells})
        contests.append({"contest_id": cid, "contest_name": "Synthetic", "year": 2025, "region": "",
                         "problems": [{"problem_id": 10 * cid + k, "problem_label": "ABCDEF"[k],
                                       "problem_name": f"P{cid}{k}"} for k in range(6)],
                         "standings": standings})
    return contests


class AttachOnlineRostersTest(unittest.TestCase):
    def test_keys_solved_check_and_idempotence(self):
        attach = _attach_module().attach
        rosters = [{"season": "2025", "round": "1", "school": "甲大学", "team": "Alpha", "members": "a|b|c"},
                   {"season": "2025", "round": "1", "school": "乙大学", "team": "Beta", "members": "d|e|f"},
                   {"season": "2025", "round": "1", "school": "丙大学", "team": "Beta", "members": "g|h|i"},
                   {"season": "2025", "round": "1", "school": "丁大学", "team": "Gamma", "members": "j|k|l"},
                   {"season": "2025", "round": "1", "school": "戊大学", "team": "Zero", "members": "m|n|o"}]
        ranking = [{"season": "2025", "round": "1", "school": "甲大学", "team": "Alpha", "solved": "5"},
                   {"season": "2025", "round": "1", "school": "丁大学", "team": "Gamma", "solved": "4"}]
        contest = {"standings": [
            {"team_name": "Alpha", "total_solved": 5},               # unique name, solved agrees
            {"team_name": "Beta", "total_solved": 3},                # name at two schools: ambiguous
            {"team_name": "Gamma", "total_solved": 3},               # official ranking says 4
            {"team_name": "Zero", "total_solved": 0},                # unranked zero-solve team
            {"team_name": "Kept", "total_solved": 2, "members": ["x", "y"]}]}
        counts = attach(contest, "2025", "1", rosters, ranking)
        members = [s.get("members") for s in contest["standings"]]
        self.assertEqual(members, [["a", "b", "c"], None, None, ["m", "n", "o"], ["x", "y"]])
        self.assertEqual(counts, {"attached": 2, "ambiguous name": 1, "solved count disagrees": 1, "had members": 1})
        before = json.dumps(contest, ensure_ascii=False)
        attach(contest, "2025", "1", rosters, ranking)
        self.assertEqual(json.dumps(contest, ensure_ascii=False), before)

    def test_2024_boards_use_the_printed_school(self):
        attach = _attach_module().attach
        rosters = [{"season": "2024", "round": "2", "school": "甲大学", "team": "Beta", "members": "a|b|c"},
                   {"season": "2024", "round": "2", "school": "乙大学", "team": "Beta", "members": "d|e|f"}]
        ranking = [{"season": "2024", "round": "2", "school": "乙大学", "team": "Beta", "solved": "2"}]
        contest = {"standings": [{"team_name": "Beta (<b>乙大学</b>)", "total_solved": 2}]}
        attach(contest, "2024", "2", rosters, ranking)
        self.assertEqual(contest["standings"][0]["members"], ["d", "e", "f"])


class ReleaseAuditHelpersTest(unittest.TestCase):
    def test_bisquare_location_ignores_outliers(self):
        x = np.r_[np.linspace(-1, 1, 21), [40.0, 55.0, 60.0]]
        location, weights = bisquare_location(x)
        self.assertAlmostEqual(location, 0.0, places=6)
        self.assertTrue(np.all(weights[-3:] == 0))

    def test_generic_nested_ridge_matches_calibration_ablation_de(self):
        rows = _anchor_rows()
        held = [r for r in rows if r["cf_contest"] == 3]
        train = [r for r in rows if r["cf_contest"] != 3]
        grid, f = method("ridge", DE)
        prediction, (alpha, lam) = nested(rows, held, grid, f)
        setting = select_inner_contests(train, bundles=("DE",))["fixed"]["DE"]
        self.assertEqual((alpha, lam), (setting["alpha"], setting["lambda"]))
        np.testing.assert_allclose(prediction, fit_predict_fixed(train, held, "DE", alpha, lam), atol=1e-8)

    def test_clipping_only_changes_rows_outside_the_training_range(self):
        rows = _anchor_rows()
        train, test = rows[:25], rows[25:]
        _, ridge = method("ridge", DE)
        _, clip = method("clip", DE)
        inside = [r for r in test if all(min(t[f] for t in train) <= r[f] <= max(t[f] for t in train) for f in DE)]
        self.assertTrue(inside)
        np.testing.assert_allclose(ridge(train, inside, (1.0, 1.0)), clip(train, inside, (1.0, 1.0)))


class OffsetFitTest(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contests.json"
            path.write_text(json.dumps(_standings()))
            self.ds = load(str(path))

    def test_without_offsets_it_is_the_shipped_map(self):
        for kind, mod in (("binary", model), ("survival", survival)):
            theta, b, _ = mod.fit(self.ds, verbose=False, eps=1e-4)
            t2, delta, gamma, b2 = fit_offsets(self.ds, kind, eps=1e-4)
            np.testing.assert_allclose(b2, b, atol=0.05)
            np.testing.assert_allclose(t2, theta, atol=0.05)
            self.assertFalse(delta.any() or gamma.any())

    def test_frozen_ability_refit_reproduces_own_difficulties(self):
        for kind, mod in (("binary", model), ("survival", survival)):
            theta, b, _ = mod.fit(self.ds, verbose=False, eps=1e-4)
            np.testing.assert_allclose(b_given_theta(self.ds, theta, kind, np.full_like(b, 2000.0), tol=1e-4),
                                       b, atol=0.05)


if __name__ == "__main__":
    unittest.main()
