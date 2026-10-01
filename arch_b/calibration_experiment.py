"""Bounded, research-only LOCO calibration comparison.

This does not write ratings or alter the shipped calibration.  It compares
affine maps, the locked external gym shape, and residual corrections on the
existing 185 CF anchors.  Every outer-fold prediction is made without that
contest's CF labels.  The feature table deliberately excludes IDs, regions,
titles, and all CF-calibrated output fields.

Run ``python -m arch_b.calibration_experiment --baseline-only``. Results go to
the research file ``output/calibration_experiment.json`` unless another path is
passed. TabFM requires ``--tabfm --tabfm-license-ack``; callers may also supply its small adapter as
``tabfm_predictor(train_x, train_y, test_x)``.
"""

import json
import os
import contextlib
import io
import hashlib
from importlib.metadata import version
from collections import defaultdict

import numpy as np

from .calibrate import _gym_shape
from .external_validate import _cf_mapping, _cf_problemset, _norm
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF
from arch_a.load import row_solved_any

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output",
                   "calibration_experiment.json")
LAMDAS = (0.0, 0.25, 0.5, 0.75, 1.0)
RIDGE_ALPHAS = (0.1, 1.0, 10.0)
FEATURES = ("raw_b", "binary_minus_survival", "conditional_fit_se",
            "solve_rate", "log_field_size", "log_median_solve_seconds", "timing_missing")


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def _raw_problem_features():
    """Completed-contest evidence keyed by canonical (contest, label).

    Time is the median among recorded solves; a zero-time/missing solve is not
    silently treated as a fast solve.  Field strength is intentionally absent:
    the saved artifacts do not contain a provenance-safe ability summary.
    """
    contests = {}
    for path in (TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP):
        for contest in _load_json(path):
            contests.setdefault(int(contest["contest_id"]), contest)
    result = {}
    for cid, contest in contests.items():
        labels = {p["problem_label"] for p in contest["problems"]}
        retained = [row for row in contest["standings"] if row_solved_any(row, labels)]
        field = len(retained)
        for problem in contest["problems"]:
            label = problem["problem_label"]
            times, missing = [], False
            solved = 0
            for standing in retained:
                cell = standing.get("problems", {}).get(label, {})
                if cell.get("solved"):
                    solved += 1
                    seconds = cell.get("time_seconds")
                    if seconds is None or seconds <= 0:
                        missing = True
                    else:
                        times.append(seconds)
            result[(cid, label)] = (solved, field, solved / max(field, 1), float(np.log1p(field)),
                                    float(np.log1p(np.median(times))) if times else 0.0,
                                    float(missing or not times), contest.get("region", "?"))
    return result


def build_anchor_table(records=None, binary_records=None):
    """Return only anchor labels and deployment-available completed-contest inputs.

    ``records`` / ``binary_records`` default to the saved survival / binary fits.
    """
    if records is None:
        base = os.path.join(os.path.dirname(__file__), os.pardir, "output")
        records = _load_json(os.path.join(base, "problem_ratings_survival.json"))
    base = os.path.join(os.path.dirname(__file__), os.pardir, "output")
    if binary_records is None:
        binary_records = _load_json(os.path.join(base, "problem_ratings_b.json"))
    binary = {(int(r["contest_id"]), r["problem_label"]): float(r["difficulty"])
              for r in binary_records}
    evidence = _raw_problem_features()
    by_name = {(int(r["contest_id"]), _norm(r["problem_name"])): r for r in records}
    contests_like = defaultdict(list)
    for r in records:
        contests_like[int(r["contest_id"])].append({"problem_label": r["problem_label"],
                                                      "problem_name": r["problem_name"]})
    ratings = _cf_problemset()
    with contextlib.redirect_stdout(io.StringIO()):
        mapping = _cf_mapping([{"contest_id": cid, "problems": ps}
                               for cid, ps in contests_like.items()],
                              defaultdict(lambda: "?"), ratings)
    mapped = [(cfid, qoj) for cfid, qoj, _region, _matched in mapping if qoj is not None]
    if len({cfid for cfid, _qoj in mapped}) != len(mapped) or len({qoj for _cfid, qoj in mapped}) != len(mapped):
        raise RuntimeError("CF/QOJ anchor mapping is not one-to-one")
    rows = []
    for cf_contest, contest_id, _region, matched in mapping:
        for name in matched:
            r = by_name.get((int(contest_id), name))
            if r is None:
                continue
            key = (int(r["contest_id"]), r["problem_label"])
            if key not in binary or key not in evidence or "difficulty_se" not in r:
                raise RuntimeError(f"missing prespecified feature for anchor {key}")
            solved, field, solve_rate, log_field, log_time, time_missing, region = evidence[key]
            if solved != int(r["solved_count"]):
                raise RuntimeError(f"source solve count disagrees with saved fit for {key}")
            rows.append({"row_id": f"{cf_contest}:{key[0]}:{r['problem_id']}",
                         "cf_contest": int(cf_contest), "cf": float(ratings[(cf_contest, name)]),
                         "contest_id": key[0], "problem_label": key[1],
                         "problem_id": int(r["problem_id"]), "canonical_task": f"qoj:{r['problem_id']}",
                         "region": region,
                         "raw_b": float(r["difficulty"]),
                         "binary_minus_survival": binary[key] - float(r["difficulty"]),
                         "conditional_fit_se": float(r["difficulty_se"]),
                         "solve_rate": solve_rate, "log_field_size": log_field,
                         "log_median_solve_seconds": log_time,
                         "timing_missing": time_missing})
    if len(rows) != 185 or len({r["cf_contest"] for r in rows}) != 15:
        raise RuntimeError("expected exactly 185 anchors in 15 CF contests")
    if not np.isfinite(_matrix(rows)).all() or not np.isfinite([r["cf"] for r in rows]).all():
        raise RuntimeError("non-finite anchor feature or label")
    return rows


def _matrix(rows):
    return np.array([[r[name] for name in FEATURES] for r in rows], float)


def _full_rows(records, binary_records=None):
    """Unlabeled completed-contest rows for explicitly non-OOF diagnostics only."""
    base = os.path.join(os.path.dirname(__file__), os.pardir, "output")
    if binary_records is None:
        binary_records = _load_json(os.path.join(base, "problem_ratings_b.json"))
    binary = {(int(r["contest_id"]), r["problem_label"]): float(r["difficulty"])
              for r in binary_records}
    evidence = _raw_problem_features()
    rows = []
    for r in records:
        key = (int(r["contest_id"]), r["problem_label"])
        if key not in binary or key not in evidence or "difficulty_se" not in r:
            raise RuntimeError(f"missing prespecified full diagnostic feature for {key}")
        solved, _field, rate, log_field, log_time, missing, region = evidence[key]
        if solved != int(r["solved_count"]):
            raise RuntimeError(f"source solve count disagrees with saved fit for {key}")
        rows.append({"contest_id": key[0], "problem_id": int(r["problem_id"]),
                     "problem_label": key[1], "canonical_task": f"qoj:{r['problem_id']}",
                     "region": region, "raw_b": float(r["difficulty"]),
                     "binary_minus_survival": binary[key] - float(r["difficulty"]),
                     "conditional_fit_se": float(r["difficulty_se"]), "solve_rate": rate,
                     "log_field_size": log_field, "log_median_solve_seconds": log_time,
                     "timing_missing": missing})
    return rows


def _affine(train, test, shape):
    z = shape(np.array([r["raw_b"] for r in train])) if shape else np.array([r["raw_b"] for r in train])
    slope, intercept = np.polyfit(z, [r["cf"] for r in train], 1)
    ztest = shape(np.array([r["raw_b"] for r in test])) if shape else np.array([r["raw_b"] for r in test])
    return slope * ztest + intercept


def _ridge_fit_predict(train, test, shape, alpha):
    base_train = _affine(train, train, shape)
    x_train, x_test = _matrix(train), _matrix(test)
    mean, scale = x_train.mean(0), x_train.std(0)
    scale[scale == 0] = 1.0
    x_train, x_test = (x_train - mean) / scale, (x_test - mean) / scale
    x_train = np.column_stack((np.ones(len(train)), x_train))
    x_test = np.column_stack((np.ones(len(test)), x_test))
    penalty = np.diag([0.0] + [alpha] * (x_train.shape[1] - 1))
    coef = np.linalg.solve(x_train.T @ x_train + penalty,
                           x_train.T @ (np.array([r["cf"] for r in train]) - base_train))
    return _affine(train, test, shape) + x_test @ coef


def _select_ridge(train, predictor=None):
    """Inner contest folds choose alpha and residual shrinkage together."""
    groups = sorted({r["cf_contest"] for r in train})
    scores = {}
    alphas = RIDGE_ALPHAS if predictor is None else (None,)
    for alpha in alphas:
        base, corrected, target = [], [], []
        for group in groups:
            inner_test = [r for r in train if r["cf_contest"] == group]
            held_tasks = {r.get("canonical_task") for r in inner_test} - {None}
            inner_train = [r for r in train if r["cf_contest"] != group and
                           r.get("canonical_task") not in held_tasks]
            baseline = _affine(inner_train, inner_test, None)
            if predictor is None:
                pred = _ridge_fit_predict(inner_train, inner_test, None, alpha)
            else:
                baseline_train = _affine(inner_train, inner_train, None)
                pred = baseline + predictor(_matrix(inner_train),
                                            np.array([r["cf"] for r in inner_train]) - baseline_train,
                                            _matrix(inner_test))
            pred = np.asarray(pred, float)
            if pred.shape != (len(inner_test),) or not np.isfinite(pred).all():
                raise ValueError("residual predictor returned non-finite or wrong-shaped predictions")
            base.extend(baseline)
            corrected.extend(pred)
            target.extend(r["cf"] for r in inner_test)
        base, corrected, target = np.array(base), np.array(corrected), np.array(target)
        for lam in LAMDAS:
            scores[(alpha, lam)] = float(np.mean((base + lam * (corrected - base) - target) ** 2))
    return min(scores, key=scores.get), scores


_TABFM_MODEL = None
_TABFM_BACKEND = None
TABFM_REVISION = "77cb9cc1b4fd3a9c77fbb9552c218200bb4dab83"
TABFM_CHECKPOINT_SHA256 = "bd5a615b0322a8f04a895038de6df6fbd71430eca750e1d792f31048654674a9"


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pinned_tabfm_checkpoint():
    root = os.environ.get("TABFM_CHECKPOINT_DIR")
    if not root:
        raise RuntimeError("TabFM requires TABFM_CHECKPOINT_DIR for a pinned local checkpoint")
    root = os.path.abspath(root)
    model_path = os.path.join(root, "regression", "model.safetensors")
    config_path = os.path.join(root, "regression", "config.json")
    if not os.path.isfile(model_path) or not os.path.isfile(config_path):
        raise RuntimeError("pinned TabFM checkpoint must contain regression/model.safetensors and config.json")
    model_sha256 = _file_sha256(model_path)
    if model_sha256 != TABFM_CHECKPOINT_SHA256:
        raise RuntimeError("pinned TabFM checkpoint SHA-256 does not match the frozen expected hash")
    return root, model_sha256, _file_sha256(config_path)


def _default_tabfm_predictor(train_x, train_y, test_x):
    global _TABFM_MODEL, _TABFM_BACKEND
    import tabfm
    from tabfm import TabFMRegressor, tabfm_v1_0_0_pytorch
    if _TABFM_MODEL is None:
        checkpoint_dir, model_sha256, config_sha256 = _pinned_tabfm_checkpoint()
        _TABFM_BACKEND = {
            "package_version": getattr(tabfm, "__version__", None) or version("tabfm"),
            "model": "tabfm_v1_0_0_pytorch regression cpu", "n_estimators": 1,
            "batch_size": 1, "seed": 20260907, "revision": TABFM_REVISION,
            "checkpoint_dir": checkpoint_dir, "checkpoint_dir_realpath": os.path.realpath(checkpoint_dir),
            "checkpoint_sha256_expected": TABFM_CHECKPOINT_SHA256,
            "checkpoint_sha256_verified": model_sha256, "config_sha256_verified": config_sha256,
        }
        _TABFM_MODEL = tabfm_v1_0_0_pytorch.load(model_type="regression",
                                                  checkpoint_path=checkpoint_dir, device="cpu")
    return np.asarray(TabFMRegressor(model=_TABFM_MODEL, max_num_rows=185,
                                     n_estimators=1, batch_size=1, random_state=20260907)
                      .fit(train_x, train_y).predict(test_x), float)


def run_experiment(rows=None, tabfm_predictor=None, output_path=None, use_tabfm=None,
                   progress=False):
    """Nested contest-LOCO experiment; returns JSON-safe results and optionally writes them."""
    rows = build_anchor_table() if rows is None else [dict(r) for r in rows]
    shape = _gym_shape(_load_json(os.path.join(os.path.dirname(__file__), os.pardir,
                                               "output", "problem_ratings_survival.json")))
    if shape is None:
        raise RuntimeError("locked gym shape unavailable")
    predictions = defaultdict(list)
    selected = {}
    use_tabfm = tabfm_predictor is not None if use_tabfm is None else use_tabfm
    tabfm = tabfm_predictor if use_tabfm else None
    if tabfm is None and use_tabfm:
        try:
            import tabfm
            from tabfm import TabFMRegressor, tabfm_v1_0_0_pytorch  # noqa: F401
            tabfm = _default_tabfm_predictor
        except (ImportError, ModuleNotFoundError):
            raise RuntimeError("TabFM unavailable; run with --baseline-only for controls")
    tabfm_available = tabfm is not None
    for group in sorted({r["cf_contest"] for r in rows}):
        test = [r for r in rows if r["cf_contest"] == group]
        held_tasks = {r.get("canonical_task") for r in test} - {None}
        train = [r for r in rows if r["cf_contest"] != group and
                 r.get("canonical_task") not in held_tasks]
        raw = _affine(train, test, None)
        gym = _affine(train, test, shape)
        (alpha, lam), _ = _select_ridge(train)
        ridge = raw + lam * (_ridge_fit_predict(train, test, None, alpha) - raw)
        values = {"raw_affine": raw, "gym_shape_affine": gym, "ridge_residual": ridge}
        if tabfm_available:
            (_unused, tab_lam), _ = _select_ridge(train, tabfm)
            base_train = _affine(train, train, None)
            correction = np.asarray(tabfm(_matrix(train), np.array([r["cf"] for r in train]) - base_train,
                                            _matrix(test)), float)
            if correction.shape != (len(test),) or not np.isfinite(correction).all():
                raise ValueError("residual predictor returned non-finite or wrong-shaped predictions")
            tab = raw + tab_lam * correction
            values["tabfm_residual"] = tab
            selected[str(group)] = {"ridge_alpha": alpha, "ridge_lambda": lam,
                                    "tabfm_lambda": tab_lam}
        else:
            selected[str(group)] = {"ridge_alpha": alpha, "ridge_lambda": lam,
                                    "tabfm": "unavailable"}
        for i, row in enumerate(test):
            entry = {"row_id": row.get("row_id"), "cf_contest": group, "cf": row["cf"],
                     "contest_id": row.get("contest_id"), "problem_id": row.get("problem_id"),
                     "problem_label": row.get("problem_label"), "region": row.get("region", "?")}
            entry.update({name: float(value[i]) for name, value in values.items()})
            entry["features"] = {name: float(row[name]) for name in FEATURES}
            entry["selected"] = selected[str(group)]
            predictions[str(group)].append(entry)
        if progress:
            print(f"completed outer CF contest {group}", flush=True)
    flat = [r for value in predictions.values() for r in value]
    methods = sorted({key for r in flat for key in r if key.endswith("affine") or key.endswith("residual")})
    metrics = {name: float(np.sqrt(np.mean([(r[name] - r["cf"]) ** 2 for r in flat if name in r])))
               for name in methods}
    by_contest, by_region = {}, {}
    for label, key, dest in (("cf_contest", "cf_contest", by_contest), ("region", "region", by_region)):
        for value in sorted({r.get(key, "?") for r in flat}, key=str):
            part = [r for r in flat if r.get(key, "?") == value]
            dest[str(value)] = {name: float(np.sqrt(np.mean([(r[name] - r["cf"]) ** 2
                                                               for r in part if name in r])))
                                for name in methods}
    diagnostics = {}
    if rows and all("cf" in r for r in rows) and len(rows) == 185:
        # This refit is a post-OOF research diagnostic, never a deployment output.
        (alpha, lam), _ = _select_ridge(rows)
        full_records = _load_json(os.path.join(os.path.dirname(__file__), os.pardir,
                                              "output", "problem_ratings_survival.json"))
        full_rows = _full_rows(full_records)
        raw_all = _affine(rows, full_rows, None)
        ridge_all = raw_all + lam * (_ridge_fit_predict(rows, full_rows, None, alpha) - raw_all)
        lo, hi = min(r["raw_b"] for r in rows), max(r["raw_b"] for r in rows)
        changed = sorted((dict(row, raw_affine=float(raw_all[i]), ridge_residual=float(ridge_all[i]),
                               correction=float(ridge_all[i] - raw_all[i]))
                          for i, row in enumerate(full_rows)), key=lambda r: abs(r["correction"]), reverse=True)
        shared = [r for r in changed if r["contest_id"] in (1661, 1662)]
        diagnostics = {"all_anchor_inner_selected": {"ridge_alpha": alpha, "ridge_lambda": lam},
                       "not_oof_not_deployment": True, "anchor_raw_range": [lo, hi],
                       "out_of_anchor_range": sum(r["raw_b"] < lo or r["raw_b"] > hi for r in full_rows),
                       "largest_absolute_corrections": changed[:20],
                       "luxor_shared_task_rows": [r for r in shared if r["problem_id"] in
                                                  {8680, 8683, 8677, 8676, 8674}]}
    paths = [TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP,
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "problem_ratings_survival.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "problem_ratings_b.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "output", "gym_difficulty.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "data", "cf_problemset.json"),
             os.path.join(os.path.dirname(__file__), os.pardir, "data", "cf_team_contests.txt")]
    def sha(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    hashes = {os.path.relpath(path): sha(path) for path in paths}
    hashes[os.path.relpath(__file__)] = sha(__file__)
    result = {"research_only": True, "independent_confirmation": False,
              "config": {"features": FEATURES, "lambdas": LAMDAS,
                         "ridge_alphas": RIDGE_ALPHAS, "tabfm_context_max_rows": 185,
                         "tabfm_estimators": 1, "tabfm_seed": 20260907, "tabfm_device": "cpu",
                         "tabfm_batch_size": 1, "tabfm_revision": TABFM_REVISION,
                         "tabfm_checkpoint_sha256_expected": TABFM_CHECKPOINT_SHA256,
                         "field_strength": "omitted_no_saved_provenance",
                         "outer_split": "CF contest; explicit canonical_task rows are purged from training"},
              "anchor_coverage": {"problems": len(rows), "contests": len(predictions)},
              "tabfm_status": "run" if tabfm_available else "not_run_baseline_only",
              "tabfm_backend": _TABFM_BACKEND if tabfm_available else None,
              "provenance_sha256": hashes,
              "metrics_rmse": metrics, "per_cf_contest_rmse": by_contest,
              "per_region_rmse": by_region, "research_diagnostics": diagnostics,
              "selected_by_outer_contest": selected,
              "folds": {group: {"predictions": value, "selected": selected[group]}
                        for group, value in predictions.items()}}
    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
    return result


def main():
    import sys
    if "--tabfm" in sys.argv and "--tabfm-license-ack" not in sys.argv:
        raise RuntimeError("TabFM requires explicit --tabfm-license-ack after license approval")
    result = run_experiment(output_path=OUT, use_tabfm="--tabfm" in sys.argv, progress=True)
    print(json.dumps(result["metrics_rmse"], sort_keys=True))


if __name__ == "__main__":
    main()
