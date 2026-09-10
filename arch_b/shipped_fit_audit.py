"""Offline TabFM/DE replay and a reviewable DE candidate, without promotion.

Run ``python -m arch_b.shipped_fit_audit`` from the repository root. Requires
the archived managed responses; never imports a cloud client or submits jobs.
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from .calibrate import _gym_shape
from .calibration_ablation import _purged_train, fit_predict_fixed, select_inner_contests
from .calibration_ablation_transfer import _reorderings
from .calibration_audit import _index, _support, verify_provenance
from .calibration_experiment import _affine, _file_sha256, _full_rows, build_anchor_table
from .tabfm_bigquery import BYTE_CAP, FEATURES, LAMDAS, _digest, _metrics, build_manifest, inference_sql

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output/shipped_fit_audit.json"
METHODS = ("raw_affine", "gym_shape_affine", "ridge_DET", "ridge_DE", "tabfm_residual")


def _read(path):
    return json.loads(Path(path).read_text())


def _close(actual, expected, description):
    if not np.isfinite(actual).all() or not np.isfinite(expected).all() or not np.allclose(
            actual, expected, rtol=0, atol=1e-7):
        raise RuntimeError(f"replay mismatch: {description}")


def replay_tabfm(manifest, saved, archive):
    """Recompute inner selection and outer predictions from every saved call."""
    values = {}
    for call in manifest["calls"]:
        response = _read(archive / f"{call['call_id']}.json")
        expected = {str(i) for i in call["prediction_rows"]}
        if set(response) != expected or not np.isfinite(list(response.values())).all():
            raise RuntimeError(f"invalid archived prediction rows: {call['call_id']}")
        values[call["call_id"]] = response
    previous = _index(saved["predictions"], lambda row: row["row_id"])
    if set(previous) != {row["row_id"] for row in manifest["rows"]}:
        raise RuntimeError("TabFM outer row coverage differs")
    selected, replay_error = {}, 0.0
    for outer in sorted({call["outer_contest"] for call in manifest["calls"]}):
        calls = [call for call in manifest["calls"] if call["outer_contest"] == outer]
        scores = {}
        for lam in LAMDAS:
            errors = [(call["baseline"][i] + lam * values[call["call_id"]][str(i)] -
                       manifest["rows"][i]["cf"]) ** 2
                      for call in calls if call["inner_contest"] is not None
                      for i in call["prediction_rows"]]
            scores[lam] = float(np.mean(errors))
        lam = min(LAMDAS, key=scores.get)
        setting = saved["selected_by_outer_contest"][str(outer)]
        if lam != setting["tabfm_lambda"]:
            raise RuntimeError(f"TabFM selected shrinkage differs: {outer}")
        _close(scores[lam], setting["inner_mse"], f"TabFM inner score {outer}")
        selected[str(outer)] = lam
        full = next(call for call in calls if call["inner_contest"] is None)
        for i in full["prediction_rows"]:
            row = manifest["rows"][i]
            old = previous[row["row_id"]]
            if old["cf"] != row["cf"] or old["cf_contest"] != outer or old["features"] != {
                    name: row[name] for name in FEATURES}:
                raise RuntimeError("TabFM saved labels/features differ")
            prediction = full["baseline"][i] + lam * values[full["call_id"]][str(i)]
            _close(prediction, old["tabfm_residual"], f"TabFM outer row {row['row_id']}")
            replay_error = max(replay_error, abs(prediction - old["tabfm_residual"]))
    for method in METHODS:
        for metric, value in _metrics(saved["predictions"], method).items():
            _close(value, saved["metrics"][method][metric], f"{method} {metric}")
    return {"calls": len(values), "selected_lambdas": selected,
            "max_prediction_replay_error": replay_error}


def _ledger_check(manifest, saved, archive):
    ledger = _read(archive / "submission_ledger.json")
    if ledger["query_limit"] != 300 or len(ledger["entries"]) != len(manifest["calls"]):
        raise RuntimeError("managed ledger coverage/limit differs")
    backend = saved["backend"]
    sql = inference_sql(backend["project"], backend["dataset"])
    billed = 0
    for call in manifest["calls"]:
        digest = _digest({"call": call, "sql": sql, "project": backend["project"],
                          "location": backend["location"], "cap": BYTE_CAP})
        job_id = f"{call['call_id']}_{digest[:12]}"
        entry = ledger["entries"][job_id]
        if (entry["status"] != "complete" or entry["input_hash"] != digest or
                entry["purpose"] != f"predict:{call['call_id']}" or
                not 0 <= entry["bytes_billed"] <= BYTE_CAP):
            raise RuntimeError(f"invalid ledger entry: {job_id}")
        billed += entry["bytes_billed"]
    smoke = _read(archive / "smoke.json")
    if not smoke["passed"] or any(set(smoke[key]) != {"0", "1"} or
                                   not np.isfinite(list(smoke[key].values())).all()
                                   for key in ("first", "second")):
        raise RuntimeError("invalid duplicate-feature smoke evidence")
    smoke_ledger = _read(archive / "smoke_ledger.json")
    if len(smoke_ledger["entries"]) != 2 or any(
            entry["status"] != "complete" for entry in smoke_ledger["entries"].values()):
        raise RuntimeError("invalid smoke ledger")
    return {"experiment_jobs": len(ledger["entries"]), "experiment_bytes_billed": billed,
            "smoke_jobs": 2, "smoke_bytes_billed": sum(
                entry["bytes_billed"] for entry in smoke_ledger["entries"].values()),
            "billing_invoice_and_remote_cleanup_independently_verified": False}


def _comparison(rows):
    result = {"metrics": {method: _metrics(rows, method) for method in METHODS}}
    for field in ("cf_contest", "region"):
        result[f"per_{field}"] = {
            str(group): {method: _metrics([row for row in rows if row[field] == group], method)["rmse"]
                         for method in METHODS} for group in sorted({row[field] for row in rows})}
    result["de_contest_wins"] = {method: sum(
        part["ridge_DE"] < part[method] for part in result["per_cf_contest"].values())
        for method in METHODS if method != "ridge_DE"}
    return result


def run_audit():
    names = ("calibration_experiment", "calibration_ablation", "calibration_ablation_transfer",
             "calibration_audit", "calibration_tabfm_bigquery")
    artifacts = {name: _read(ROOT / f"output/{name}.json") for name in names}
    paths = {ROOT / f"output/{name}.json" for name in names}
    for name in names[:-1]:
        verify_provenance(artifacts[name])
        paths.update(ROOT / path for path in artifacts[name]["provenance_sha256"])
    tabfm = artifacts["calibration_tabfm_bigquery"]
    verify_provenance({"provenance_sha256": tabfm["baseline_provenance_sha256"]})
    for key, path in (("module", "arch_b/tabfm_bigquery.py"), ("plan", "tabfm_cloud_plan.md")):
        if _file_sha256(ROOT / path) != tabfm["source_sha256"][key]:
            raise RuntimeError(f"stale TabFM source: {path}")
        paths.add(ROOT / path)
    archive = ROOT / "tabfm_bigquery_run" / tabfm["run_id"]
    paths.update(archive.glob("*.json"))
    # Snapshot every existing output, including viewers, before staging anything.
    paths.update(path for path in (ROOT / "output").iterdir() if path.is_file() and path != OUT)
    paths.add(Path(__file__))
    paths.update(ROOT / path for path in (
        "shipped_fit_update_plan.md", "tests/test_shipped_fit_audit.py",
        "arch_b/export_viewer.py", "arch_b/export_ucup_only.py",
        "arch_b/export_virtual_calc.py", "arch_b/medals.py", "arch_b/metric.py",
        "arch_b/hier_calibrate.py"))
    provenance = {str(path.relative_to(ROOT)): _file_sha256(path) for path in sorted(paths)}

    anchors = build_anchor_table()
    manifest = build_manifest(anchors)
    # JSON object keys deserialize as strings (the in-memory baseline uses ints).
    if json.loads(json.dumps(manifest)) != _read(archive / "manifest.json"):
        raise RuntimeError("archived managed manifest differs from current inputs")
    managed = replay_tabfm(manifest, tabfm, archive)
    managed["ledger"] = _ledger_check(manifest, tabfm, archive)
    print("Replayed 225 managed calls and checked ledger/provenance", flush=True)

    ablation = artifacts["calibration_ablation"]
    records = _read(ROOT / "output/problem_ratings_survival.json")
    shape = _gym_shape(records)
    if shape is None:
        raise RuntimeError("locked gym shape unavailable")
    tab_by_id = _index(tabfm["predictions"], lambda row: row["row_id"])
    for contest, fold in ablation["protocols"]["leave_one_cf_contest_out"]["folds"].items():
        held = [row for row in anchors if row["cf_contest"] == int(contest)]
        train = _purged_train(anchors, held)
        if set(fold["training_rows"]) != {row["row_id"] for row in train}:
            raise RuntimeError("DE training membership differs")
        setting = select_inner_contests(train, bundles=("DE",))["fixed"]["DE"]
        if setting != fold["selected"]["fixed"]["DE"]:
            raise RuntimeError("DE nested selection differs")
        values = {"ridge_DE": fit_predict_fixed(train, held, "DE", setting["alpha"], setting["lambda"]),
                  "raw_affine": _affine(train, held, None), "gym_shape_affine": _affine(train, held, shape)}
        old = _index(fold["predictions"], lambda row: row["row_id"])
        for method, predictions in values.items():
            _close(predictions, [old[row["row_id"]][method] for row in held], f"DE fold {contest} {method}")
            _close(predictions, [tab_by_id[row["row_id"]][method] for row in held], f"TabFM control {contest} {method}")
        baseline = artifacts["calibration_experiment"]["folds"][contest]["predictions"]
        for row in baseline:
            _close(row["ridge_residual"], tab_by_id[row["row_id"]]["ridge_DET"], "DET saved control")

    full = _full_rows(records)
    setting = select_inner_contests(anchors, bundles=("DE",))["fixed"]["DE"]
    if setting != ablation["full_anchor_selection_not_oof_not_deployment"]["fixed"]["DE"]:
        raise RuntimeError("DE full selection differs")
    candidate = fit_predict_fixed(anchors, full, "DE", setting["alpha"], setting["lambda"])
    key = lambda row: (int(row["contest_id"]), row["problem_label"])
    shipped = _index(_read(ROOT / "output/problem_ratings_calibrated.json"), key)
    previous = _index(artifacts["calibration_audit"]["full_refit_not_oof"]["rows"], key)
    if set(shipped) != {key(row) for row in full} or set(previous) != set(shipped):
        raise RuntimeError("shipped/full-refit appearance coverage differs")
    _close(candidate, [previous[key(row)]["ridge_DE"] for row in full], "DE full refit")
    current = np.array([shipped[key(row)]["difficulty_cf"] for row in full])
    _close(current, np.round(np.clip(_affine(anchors, full, shape), 800, 4000), 1), "shipped gym ratings")
    proposed = np.round(np.clip(candidate, 800, 4000), 1)
    staged = [{"contest_id": row["contest_id"], "problem_label": row["problem_label"],
               "problem_id": row["problem_id"], "region": row["region"],
               "shipped_cf": float(current[i]), "candidate_de_unclipped": float(candidate[i]),
               "candidate_de_display_cf": float(proposed[i]), "display_delta": round(float(proposed[i] - current[i]), 1),
               "outside_training_feature_ranges": list(_support(row, anchors))}
              for i, row in enumerate(full)]
    delta = proposed - current
    impact = {"rows": len(full), "contests": len({row["contest_id"] for row in full}),
              "selected": setting, "display_policy": "existing clip [800,4000], round 1 decimal; no support fallback",
              "mean_display_delta": float(delta.mean()),
              "absolute_display_delta_quantiles_50_90_95_99_100": np.quantile(abs(delta), [.5, .9, .95, .99, 1]).tolist(),
              "absolute_display_delta_at_least": {str(n): int((abs(delta) >= n).sum()) for n in (100, 200, 400)},
              "clipped_low": int((candidate < 800).sum()), "clipped_high": int((candidate > 4000).sum()),
              "outside_any_training_feature_range": sum(bool(row["outside_training_feature_ranges"]) for row in staged),
              "outside_by_feature": dict(Counter(f for row in staged for f in row["outside_training_feature_ranges"])),
              "display_reorderings_vs_shipped": _reorderings(full, current, proposed), "rows_for_review": staged}
    result = {"research_only": True, "production_changed": False, "fresh_confirmation": False,
              "ready_for_global_promotion": False, "tabfm_replay": managed,
              "oof_comparison": _comparison(tabfm["predictions"]), "de_candidate_not_oof": impact,
              "provenance_sha256": provenance}
    verify_provenance(result)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    result = run_audit()
    print(json.dumps({"oof": result["oof_comparison"]["metrics"],
                      "impact": {k: v for k, v in result["de_candidate_not_oof"].items() if k != "rows_for_review"}}, indent=2))
