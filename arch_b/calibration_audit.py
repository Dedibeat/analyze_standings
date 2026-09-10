"""Frozen DE correction audit and nested calibration-label influence study."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .calibrate import _gym_shape
from .calibration_ablation import (
    _purged_train, bundle_features, fit_predict_fixed, select_inner_contests,
)
from .calibration_ablation_transfer import LUXOR_IDS, _reorderings
from .calibration_experiment import (
    _affine, _file_sha256, _full_rows, _load_json, build_anchor_table,
)
from .external_validate import _norm
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, load_joint_dataset
from .run import MIN_SOLVE_HOURS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output/calibration_audit.json"
PLAN = ROOT / "calibration_audit_plan.md"
METHODS = ("raw_affine", "gym_shape_affine", "ridge_DE")
TOLERANCE = 1e-7


def verify_provenance(saved, root=ROOT):
    for name, expected in saved["provenance_sha256"].items():
        if _file_sha256(root / name) != expected:
            raise RuntimeError(f"stale saved provenance: {name}")


def _index(rows, key):
    result = {key(row): row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("duplicate row identity in audit input")
    return result


def _table_sha256(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _predictions(train, held, shape, setting):
    values = {
        "raw_affine": _affine(train, held, None),
        "gym_shape_affine": _affine(train, held, shape),
        "ridge_DE": fit_predict_fixed(
            train, held, "DE", setting["alpha"], setting["lambda"]),
    }
    if any(np.asarray(value).shape != (len(held),) or not np.isfinite(value).all()
           for value in values.values()):
        raise RuntimeError("non-finite or wrong-shaped audit prediction")
    return [{"row_id": row["row_id"], "cf_contest": row.get("cf_contest"),
             **({"cf": row["cf"]} if "cf" in row else {}),
             **{name: float(value[i]) for name, value in values.items()}}
            for i, row in enumerate(held)]


def influence_fold(rows, excluded_contest, held_contest, shape=None):
    """Remove an anchor group before any nested setting selection or fitting."""
    excluded = [row for row in rows if row["cf_contest"] == excluded_contest]
    remaining = _purged_train(rows, excluded)
    held = [row for row in remaining if row["cf_contest"] == held_contest]
    train = _purged_train(remaining, held)
    if not held or len({row["cf_contest"] for row in train}) < 2:
        raise RuntimeError("insufficient contests after influence/task purges")
    setting = select_inner_contests(train, bundles=("DE",))["fixed"]["DE"]
    return {"held": held_contest, "held_rows": [row["row_id"] for row in held],
            "training_rows": [row["row_id"] for row in train], "selected": setting,
            "predictions": _predictions(train, held, shape, setting)}


def _rmse(rows):
    return {name: float(np.sqrt(np.mean([(row[name] - row["cf"]) ** 2
                                        for row in rows]))) for name in METHODS}


def select_examples(rows, with_labels=True, count=10):
    """Select deterministic top lists, retaining every reason for overlaps."""
    criteria = {"largest_correction": lambda r: abs(r["ridge_DE"] - r["raw_affine"])}
    if with_labels:
        criteria.update({
            "largest_improvement": lambda r: abs(r["raw_affine"] - r["cf"]) - abs(r["ridge_DE"] - r["cf"]),
            "largest_deterioration": lambda r: abs(r["ridge_DE"] - r["cf"]) - abs(r["raw_affine"] - r["cf"]),
        })
    selected, lists = {}, {}
    for reason, magnitude in criteria.items():
        eligible = [row for row in rows if reason == "largest_correction" or magnitude(row) > 0]
        ranked = sorted(eligible, key=lambda row: (-magnitude(row), row["row_id"]))[:count]
        lists[reason] = [row["row_id"] for row in ranked]
        for row in ranked:
            selected.setdefault(row["row_id"], []).append(reason)
    return {"lists": lists, "unique_rows": [
        {"row_id": row_id, "reasons": reasons} for row_id, reasons in selected.items()]}


def _support(row, train):
    return {feature: [float(min(r[feature] for r in train)),
                      float(max(r[feature] for r in train))]
            for feature in bundle_features("DE")
            if row[feature] < min(r[feature] for r in train) or
            row[feature] > max(r[feature] for r in train)}


def _source_audit(records, binary, full, anchors):
    key = lambda row: (int(row["contest_id"]), row["problem_label"])
    survival_by_key, binary_by_key = _index(records, key), _index(binary, key)
    if survival_by_key.keys() != binary_by_key.keys():
        raise RuntimeError("binary/survival appearance coverage differs")
    sources = {}
    for path in (TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP):
        for contest in _load_json(path):
            sources.setdefault(int(contest["contest_id"]), (path, contest))
    ds, _, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    loader_keys = {(int(cid), label): (int(pid), name)
                   for cid, label, pid, name in ds.problems}
    if loader_keys.keys() != survival_by_key.keys():
        raise RuntimeError("saved fit and current joint loader coverage differs")
    field = Counter(int(ds.contests[ci]) for ci in ds.contest_of_row)
    solves = np.bincount(ds.obs_prob, weights=ds.obs_y, minlength=len(ds.problems))
    loader_solves = {(int(cid), label): int(solves[i])
                     for i, (cid, label, _pid, _name) in enumerate(ds.problems)}
    metadata = {}
    for row in full:
        k = key(row)
        record, other = survival_by_key[k], binary_by_key[k]
        path, source = sources[k[0]]
        problem = _index(source["problems"], lambda p: p["problem_label"])[k[1]]
        if any(int(item["problem_id"]) != row["problem_id"] or
               item["problem_name"] != record["problem_name"] for item in (other, problem)):
            raise RuntimeError(f"source/binary task or title mismatch: {k}")
        if loader_keys[k] != (row["problem_id"], record["problem_name"]):
            raise RuntimeError(f"loader task mismatch: {k}")
        if any(int(item["solved_count"]) != loader_solves[k] for item in (record, other)):
            raise RuntimeError(f"binary/survival/loader solve-count mismatch: {k}")
        if not np.isclose(row["log_field_size"], np.log1p(field[k[0]]), rtol=0, atol=1e-12):
            raise RuntimeError(f"feature/loader field mismatch: {k}")
        metadata[k] = {
            "problem_name": record["problem_name"], "contest_name": source["contest_name"],
            "source_path": str(Path(path).resolve().relative_to(ROOT)),
            "source_problem_label": k[1], "field_size": field[k[0]],
            "solved_count": loader_solves[k],
            "qoj_url": f"https://qoj.ac/contest/{k[0]}/problem/{k[1]}",
        }
    cf = _load_json(ROOT / "data/cf_problemset.json")
    for row in anchors:
        k = key(row)
        name = metadata[k]["problem_name"]
        matching = [p for p in cf if p.get("contestId") == row["cf_contest"] and
                    _norm(p["name"]) == _norm(name)]
        source = sources[k[0]][1]
        if len(matching) != 1 or sum(_norm(p["problem_name"]) == _norm(name)
                                     for p in source["problems"]) != 1:
            raise RuntimeError(f"ambiguous cached anchor title: {row['row_id']}")
        if matching[0].get("rating") != row["cf"]:
            raise RuntimeError(f"cached CF label mismatch: {row['row_id']}")
        metadata[k]["cf_url"] = f"https://codeforces.com/contest/{row['cf_contest']}/problem/{matching[0]['index']}"
    return metadata, {"appearances_checked": len(full), "anchors_checked": len(anchors),
                      "joint_contests": len(ds.contests), "joint_rows": len(ds.team_of_row),
                      "checks": "unique cached joins; task/title/count/field consistency with joint loader",
                      "not_established": ["external task-version equivalence", "recorded contest duration",
                                          "adjudicated roster identity", "fresh confirmation labels"]}


def run_audit(output_path=None, progress=False):
    saved = _load_json(ROOT / "output/calibration_ablation.json")
    transfer = _load_json(ROOT / "output/calibration_ablation_transfer.json")
    verify_provenance(saved)
    verify_provenance(transfer)
    paths = set(saved["provenance_sha256"]) | set(transfer["provenance_sha256"])
    paths.update(("output/calibration_ablation.json", "output/calibration_ablation_transfer.json",
                  "calibration_audit_plan.md", "arch_b/calibration_audit.py", "arch_a/load.py",
                  "arch_b/joint.py", "arch_b/run.py", "arch_b/calibrate.py",
                  "arch_b/external_validate.py"))
    provenance = {path: _file_sha256(ROOT / path) for path in sorted(paths)}
    anchors = sorted(build_anchor_table(), key=lambda row: row["row_id"])
    records = _load_json(ROOT / "output/problem_ratings_survival.json")
    full = _full_rows(records)
    for row in full:
        row["row_id"] = f"{row['contest_id']}:{row['problem_label']}:{row['problem_id']}"
    full.sort(key=lambda row: row["row_id"])
    input_tables = {"anchor_features_and_labels": _table_sha256(anchors),
                    "full_appearance_features": _table_sha256(full)}
    metadata, source_checks = _source_audit(
        records, _load_json(ROOT / "output/problem_ratings_b.json"), full, anchors)
    shape = _gym_shape(records)
    if shape is None:
        raise RuntimeError("locked gym shape unavailable")
    original = saved["protocols"]["leave_one_cf_contest_out"]["folds"]
    oof, replay_error = [], 0.0
    for contest, fold in original.items():
        held = [row for row in anchors if row["cf_contest"] == int(contest)]
        train = _purged_train(anchors, held)
        if {row["row_id"] for row in train} != set(fold["training_rows"]):
            raise RuntimeError("saved training membership differs")
        previous = _index(fold["predictions"], lambda row: row["row_id"])
        if set(previous) != {row["row_id"] for row in held}:
            raise RuntimeError("saved held membership differs")
        replay = _predictions(train, held, shape, fold["selected"]["fixed"]["DE"])
        for row, prediction in zip(held, replay):
            old = previous[row["row_id"]]
            if old["cf"] != row["cf"] or any(old["features"][f] != row[f] for f in bundle_features("DET")):
                raise RuntimeError("saved anchor labels/features differ")
            replay_error = max(replay_error, *(abs(prediction[name] - old[name]) for name in METHODS))
            oof.append({**row, **{name: old[name] for name in METHODS},
                        **metadata[(row["contest_id"], row["problem_label"])],
                        "outside_training_feature_ranges": _support(row, train)})
    if replay_error > TOLERANCE:
        raise RuntimeError(f"saved OOF replay differs by {replay_error}")
    full_setting = select_inner_contests(anchors, bundles=("DE",))["fixed"]["DE"]
    for field in ("alpha", "lambda"):
        if full_setting[field] != saved["full_anchor_selection_not_oof_not_deployment"]["fixed"]["DE"][field]:
            raise RuntimeError("full-refit selection differs")
    full_predictions = _predictions(anchors, full, shape, full_setting)
    full_table = [{**row, **prediction, **metadata[(row["contest_id"], row["problem_label"])],
                   "outside_training_feature_ranges": _support(row, anchors)}
                  for row, prediction in zip(full, full_predictions)]
    luxor = {str(task): [row["row_id"] for row in full_table if row["problem_id"] == task
                        and row["contest_id"] in (1661, 1662)] for task in LUXOR_IDS}
    if any(len(pair) != 2 for pair in luxor.values()):
        raise RuntimeError("missing Luxor shared-task appearance")
    baseline = _index(oof, lambda row: row["row_id"])
    influence = {}
    contests = sorted({row["cf_contest"] for row in anchors})
    for excluded in contests:
        remaining = _purged_train(anchors, [row for row in anchors if row["cf_contest"] == excluded])
        folds = {str(held): influence_fold(anchors, excluded, held, shape)
                 for held in contests if held != excluded and any(r["cf_contest"] == held for r in remaining)}
        predicted = [row for fold in folds.values() for row in fold["predictions"]]
        if len(predicted) != len(remaining) or {r["row_id"] for r in predicted} != {r["row_id"] for r in remaining}:
            raise RuntimeError("influence OOF coverage differs from remaining cohort")
        matched = [baseline[row["row_id"]] for row in predicted]
        before, after = _rmse(matched), _rmse(predicted)
        shifts = np.array([row["ridge_DE"] - baseline[row["row_id"]]["ridge_DE"] for row in predicted])
        influence[str(excluded)] = {
            "remaining_anchors": len(remaining), "folds": folds,
            "original_oof_same_cohort_rmse": before, "refitted_oof_rmse": after,
            "rmse_change_from_refitting": {name: after[name] - before[name] for name in METHODS},
            "per_cf_contest_rmse": {held: _rmse(fold["predictions"]) for held, fold in folds.items()},
            "de_prediction_shift": {"rms": float(np.sqrt(np.mean(shifts ** 2))),
                                    "max_absolute": float(np.max(np.abs(shifts)))},
            "investigate": abs(after["ridge_DE"] - before["ridge_DE"]) > 5 or
                           after["ridge_DE"] >= min(after["raw_affine"], after["gym_shape_affine"]),
        }
        if progress:
            print(f"excluded CF {excluded}: raw/gym/DE RMSE "
                  f"{after['raw_affine']:.2f}/{after['gym_shape_affine']:.2f}/{after['ridge_DE']:.2f}; "
                  f"DE matched-cohort refit change {after['ridge_DE'] - before['ridge_DE']:+.2f}", flush=True)
    result = {
        "research_only": True, "fresh_confirmation": False, "production_changed": False,
        "target": "completed-contest CF difficulty calibration",
        "provenance_sha256": provenance, "input_table_sha256": input_tables,
        "source_checks": source_checks,
        "oof": {"replay_max_absolute_error": replay_error, "metrics_rmse": _rmse(oof),
                "selection": select_examples(oof), "rows": oof},
        "full_refit_not_oof": {"selected": full_setting, "selection": select_examples(full_table, False),
                               "luxor_shared_task_rows": luxor, "rows": full_table},
        "anchor_contest_influence_not_confirmation": influence,
    }
    for section in ("oof", "full_refit_not_oof"):
        rows = result[section]["rows"]
        result[section]["row_table_sha256"] = _table_sha256(rows)
        result[section]["marginal_support_summary"] = {
            "any_feature_outside": sum(bool(row["outside_training_feature_ranges"]) for row in rows),
            "by_feature": dict(Counter(feature for row in rows
                                       for feature in row["outside_training_feature_ranges"])),
        }
        result[section]["within_contest_order_changes"] = _reorderings(
            rows, np.array([row["raw_affine"] for row in rows]), np.array([row["ridge_DE"] for row in rows]))
    # Detect accidental input changes during the run before publishing evidence.
    verify_provenance(result)
    if output_path:
        with open(output_path, "w") as destination:
            json.dump(result, destination, indent=2, allow_nan=False)
            destination.write("\n")
    return result


if __name__ == "__main__":
    result = run_audit(OUT, progress=True)
    print(json.dumps({"oof_rmse": result["oof"]["metrics_rmse"],
                      "source_checks": result["source_checks"]}, sort_keys=True))
