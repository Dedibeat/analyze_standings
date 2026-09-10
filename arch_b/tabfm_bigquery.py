"""Bounded managed TabFM experiment through BigQuery ``AI.PREDICT``.

This is deliberately separate from ``calibration_experiment``: it uses the
managed Preview backend and never replaces the shipped calibration artifact.
Run the synthetic gate first, then the frozen nested experiment, for example::

    ./.venv/bin/python -m arch_b.tabfm_bigquery smoke --project PROJECT --location us-central1
    ./.venv/bin/python -m arch_b.tabfm_bigquery run --project PROJECT --location us-central1

Every executable query has a 1 GiB byte cap and a deterministic job ID.  The
local ledger prevents more than 300 executable query submissions and lets a
later invocation recover an already submitted job instead of resubmitting it.
"""

import argparse
import hashlib
import json
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .calibration_ablation import _purged_train
from .calibration_experiment import FEATURES, LAMDAS, _affine, _matrix, build_anchor_table, run_experiment


BYTE_CAP = 1 << 30
QUERY_LIMIT = 300
TABLE_EXPIRATION_MS = 7 * 24 * 60 * 60 * 1000
OUT = Path(__file__).parent.parent / "output" / "calibration_tabfm_bigquery.json"
ARCHIVE_ROOT = Path(__file__).parent.parent / "tabfm_bigquery_run"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode()).hexdigest()


def _file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_id(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


class SubmissionLedger:
    """Append-safe local reservation log for potentially billable query jobs."""

    def __init__(self, path, limit=QUERY_LIMIT):
        self.path = Path(path)
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            "version": 1, "query_limit": limit, "entries": {}}
        if self.data["query_limit"] != limit:
            raise RuntimeError("ledger query limit differs from the frozen protocol")

    def _write(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True))
        tmp.replace(self.path)

    def reserve(self, job_id, input_hash, purpose):
        existing = self.data["entries"].get(job_id)
        if existing:
            if existing["input_hash"] != input_hash or existing["purpose"] != purpose:
                raise RuntimeError(f"job ID {job_id} has different recorded input")
            return existing, False
        if len(self.data["entries"]) >= self.limit:
            raise RuntimeError(f"refusing query {job_id}: {self.limit}-query ceiling reached")
        entry = {"job_id": job_id, "input_hash": input_hash, "purpose": purpose,
                 "reserved_at": _now(), "status": "reserved"}
        self.data["entries"][job_id] = entry
        self._write()
        return entry, True

    def finish(self, job_id, **values):
        entry = self.data["entries"][job_id]
        entry.update(values, completed_at=_now())
        self._write()


def _call_id(run_id, outer, inner):
    suffix = f"outer_{outer}_full" if inner is None else f"outer_{outer}_inner_{inner}"
    return f"{run_id}_{suffix}"


def build_manifest(rows=None):
    """Freeze all 225 task-purged residual contexts without invoking a service."""
    rows = build_anchor_table() if rows is None else [dict(row) for row in rows]
    if len(rows) != 185 or len({row["row_id"] for row in rows}) != 185:
        raise RuntimeError("expected 185 unique anchor rows")
    if not np.isfinite(_matrix(rows)).all() or not np.isfinite([row["cf"] for row in rows]).all():
        raise RuntimeError("anchor features and labels must be finite")
    row_order = {row["row_id"]: index for index, row in enumerate(rows)}
    run_id = f"tabfm_{_digest({row['row_id']: [row[name] for name in FEATURES] for row in rows})[:16]}"
    calls, contexts, queries, membership = [], [], [], []
    for outer in sorted({row["cf_contest"] for row in rows}):
        held = [row for row in rows if row["cf_contest"] == outer]
        train = _purged_train(rows, held)
        for inner in sorted({row["cf_contest"] for row in train}) + [None]:
            test = held if inner is None else [row for row in train if row["cf_contest"] == inner]
            fit = train if inner is None else _purged_train(train, test)
            if not fit or not test:
                raise RuntimeError("task purge left an empty managed context or query")
            call_id = _call_id(run_id, outer, inner)
            base_train = _affine(fit, fit, None)
            for index, row in enumerate(fit):
                entry = {"call_id": call_id, "training_row_id": row["row_id"],
                         "residual": float(row["cf"] - base_train[index])}
                entry.update({name: float(row[name]) for name in FEATURES})
                contexts.append(entry)
                membership.append({"run_id": run_id, "outer_contest": outer,
                                   "inner_contest": inner, "row_id": row["row_id"], "role": "train"})
            for row in test:
                entry = {"call_id": call_id, "prediction_row": row_order[row["row_id"]]}
                entry.update({name: float(row[name]) for name in FEATURES})
                queries.append(entry)
                membership.append({"run_id": run_id, "outer_contest": outer,
                                   "inner_contest": inner, "row_id": row["row_id"], "role": "test"})
            baseline = _affine(fit, test, None)
            calls.append({"call_id": call_id, "outer_contest": outer, "inner_contest": inner,
                          "prediction_rows": [row_order[row["row_id"]] for row in test],
                          "fit_rows": [row["row_id"] for row in fit],
                          "baseline": {row_order[row["row_id"]]: float(baseline[index])
                                       for index, row in enumerate(test)}})
    if len(calls) != 225 or len({call["call_id"] for call in calls}) != 225:
        raise RuntimeError("frozen protocol must create exactly 225 unique calls")
    return {"run_id": run_id, "rows": rows, "row_order": row_order, "calls": calls,
            "contexts": contexts, "queries": queries, "fold_membership": membership}


def inference_sql(project, dataset):
    features = ", ".join(FEATURES)
    return f"""SELECT prediction_row, predicted_residual
FROM AI.PREDICT(
  (SELECT {features}, CAST(residual AS FLOAT64) AS residual
   FROM `{project}.{dataset}.contexts` WHERE call_id = @call_id),
  (SELECT prediction_row, {features}
   FROM `{project}.{dataset}.queries` WHERE call_id = @call_id),
  label_col => 'residual')"""


class BigQueryService:
    """Small adapter kept injectable so protocol guards can run without cloud access."""

    def __init__(self, project, location, dataset, ledger):
        try:
            from google.cloud import bigquery
        except ImportError as error:
            raise RuntimeError("install google-cloud-bigquery in the project venv") from error
        self.bigquery, self.project, self.location, self.dataset = bigquery, project, location, dataset
        self.ledger = ledger
        self.client = bigquery.Client(project=project, location=location)

    @property
    def dataset_ref(self):
        return f"{self.project}.{self.dataset}"

    def setup(self):
        dataset = self.bigquery.Dataset(self.dataset_ref)
        dataset.location = self.location
        dataset.default_table_expiration_ms = TABLE_EXPIRATION_MS
        self.client.create_dataset(dataset, exists_ok=True)
        schemas = {
            "anchors": [("run_id", "STRING"), ("row_id", "STRING"), ("row_order", "INT64"),
                        ("cf_contest", "INT64"), ("contest_id", "INT64"), ("canonical_task", "STRING"),
                        ("region", "STRING"), ("cf", "FLOAT64")] + [(name, "FLOAT64") for name in FEATURES],
            "fold_membership": [("run_id", "STRING"), ("outer_contest", "INT64"), ("inner_contest", "INT64"),
                                ("row_id", "STRING"), ("role", "STRING")],
            "contexts": [("call_id", "STRING"), ("training_row_id", "STRING")] +
                        [(name, "FLOAT64") for name in FEATURES] + [("residual", "FLOAT64")],
            "queries": [("call_id", "STRING"), ("prediction_row", "INT64")] +
                       [(name, "FLOAT64") for name in FEATURES],
        }
        for name, fields in schemas.items():
            table = self.bigquery.Table(f"{self.dataset_ref}.{name}",
                                        schema=[self.bigquery.SchemaField(*field) for field in fields])
            table.expires = datetime.fromtimestamp((time.time() * 1000 + TABLE_EXPIRATION_MS) / 1000,
                                                   tz=timezone.utc)
            self.client.create_table(table, exists_ok=True)

    def upload(self, name, rows, run_id):
        config = self.bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        job_id = _safe_id(f"{run_id}_{self.dataset}_load_{name}")
        try:
            job = self.client.load_table_from_json(rows, f"{self.dataset_ref}.{name}", job_id=job_id,
                                                   location=self.location, job_config=config)
        except Exception as error:
            if error.__class__.__name__ != "Conflict":
                raise
            job = self.client.get_job(job_id, location=self.location)
        job.result(timeout=600)
        if job.errors:
            raise RuntimeError(f"load {name} failed: {job.errors}")

    def predict(self, call, sql):
        input_hash = _digest({"call": call, "sql": sql, "project": self.project,
                              "location": self.location, "cap": BYTE_CAP})
        job_id = _safe_id(f"{call['call_id']}_{input_hash[:12]}")
        entry, new = self.ledger.reserve(job_id, input_hash, f"predict:{call['call_id']}")
        parameter = self.bigquery.ScalarQueryParameter("call_id", "STRING", call["call_id"])
        dry = self.bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                           maximum_bytes_billed=BYTE_CAP, query_parameters=[parameter])
        self.client.query(sql, location=self.location, job_config=dry)
        config = self.bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=BYTE_CAP,
                                              query_parameters=[parameter])
        try:
            job = self.client.query(sql, location=self.location, job_id=job_id, job_config=config,
                                    job_retry=None)
        except Exception as error:
            if error.__class__.__name__ != "Conflict":
                self.ledger.finish(job_id, status="submission_error", error=str(error))
                raise
            job = self.client.get_job(job_id, location=self.location)
        result = list(job.result(timeout=1800))
        values = {int(row["prediction_row"]): float(row["predicted_residual"]) for row in result}
        expected = set(call["prediction_rows"])
        if set(values) != expected or len(values) != len(result) or not all(math.isfinite(x) for x in values.values()):
            raise RuntimeError(f"{call['call_id']}: missing, duplicate, or non-finite TabFM prediction rows")
        self.ledger.finish(job_id, status="complete", submitted_new=new,
                           bytes_billed=job.total_bytes_billed, bytes_processed=job.total_bytes_processed,
                           started=getattr(job, "started", None) and job.started.isoformat(),
                           ended=getattr(job, "ended", None) and job.ended.isoformat())
        return values

    def cleanup(self):
        self.client.delete_dataset(self.dataset_ref, delete_contents=True, not_found_ok=True)


def _anchors_for_upload(manifest):
    rows = []
    for row in manifest["rows"]:
        entry = {"run_id": manifest["run_id"], "row_id": row["row_id"],
                 "row_order": manifest["row_order"][row["row_id"]], "cf_contest": row["cf_contest"],
                 "contest_id": row["contest_id"], "canonical_task": row["canonical_task"],
                 "region": row["region"], "cf": row["cf"]}
        entry.update({name: row[name] for name in FEATURES})
        rows.append(entry)
    return rows


def _control_predictions(rows):
    baseline = run_experiment(rows=rows, use_tabfm=False)
    saved_baseline = json.loads((Path(__file__).parent.parent / "output" / "calibration_experiment.json").read_text())
    if baseline["provenance_sha256"] != saved_baseline["provenance_sha256"]:
        raise RuntimeError("frozen baseline provenance changed")
    for method, expected in (("raw_affine", 246.9061), ("gym_shape_affine", 245.4277),
                             ("ridge_residual", 229.6269246)):
        if not np.isclose(baseline["metrics_rmse"][method], saved_baseline["metrics_rmse"][method],
                          rtol=0, atol=1e-9):
            raise RuntimeError(f"saved {method} control does not replay")
        if not np.isclose(baseline["metrics_rmse"][method], expected, rtol=0, atol=1e-4):
            raise RuntimeError(f"frozen {method} control no longer reproduces")
    fold = baseline["folds"]
    de = json.loads((Path(__file__).parent.parent / "output" / "calibration_ablation.json").read_text())
    de_folds = de["protocols"]["leave_one_cf_contest_out"]["folds"]
    values = {}
    for contest, saved in fold.items():
        saved_by_id = {row["row_id"]: row for row in saved["predictions"]}
        de_by_id = {row["row_id"]: row for row in de_folds[contest]["predictions"]}
        if set(saved_by_id) != set(de_by_id):
            raise RuntimeError("DE artifact does not align to frozen baseline row IDs")
        expected_training = _purged_train(rows, [row for row in rows if row["cf_contest"] == int(contest)])
        if set(de_folds[contest]["training_rows"]) != {row["row_id"] for row in expected_training}:
            raise RuntimeError("DE artifact task-purged fold membership changed")
        for row_id, row in saved_by_id.items():
            source = next(candidate for candidate in rows if candidate["row_id"] == row_id)
            de_row = de_by_id[row_id]
            if de_row["cf"] != source["cf"] or de_row["features"] != {name: source[name] for name in FEATURES}:
                raise RuntimeError("DE artifact labels or features do not align to frozen anchors")
            values[row_id] = {"raw_affine": row["raw_affine"], "gym_shape_affine": row["gym_shape_affine"],
                              "ridge_DET": row["ridge_residual"], "ridge_DE": de_row["ridge_DE"]}
    return values, baseline


def _metrics(predictions, method):
    errors = [row[method] - row["cf"] for row in predictions]
    return {"rmse": float(np.sqrt(np.mean(np.square(errors)))), "mae": float(np.mean(np.abs(errors))),
            "signed_bias": float(np.mean(errors))}


def run(project, location, dataset="tabfm_research", cleanup=True):
    """Execute the frozen 225-call run.  Smoke must have passed in this project first."""
    manifest = build_manifest()
    archive = ARCHIVE_ROOT / manifest["run_id"]
    archive.mkdir(parents=True, exist_ok=True)
    smoke_path = archive / "smoke.json"
    if not smoke_path.exists() or not json.loads(smoke_path.read_text()).get("passed"):
        raise RuntimeError("managed run requires a passed synthetic smoke gate for this frozen manifest")
    (archive / "manifest.json").write_text(json.dumps(manifest, indent=2))
    ledger = SubmissionLedger(archive / "submission_ledger.json")
    service = BigQueryService(project, location, dataset, ledger)
    service.setup()
    service.upload("anchors", _anchors_for_upload(manifest), manifest["run_id"])
    service.upload("fold_membership", manifest["fold_membership"], manifest["run_id"])
    service.upload("contexts", manifest["contexts"], manifest["run_id"])
    service.upload("queries", manifest["queries"], manifest["run_id"])
    controls, baseline = _control_predictions(manifest["rows"])
    sql = inference_sql(project, dataset)
    prediction_by_row, selected = {}, {}
    calls_by_outer = defaultdict(list)
    for call in manifest["calls"]:
        calls_by_outer[call["outer_contest"]].append(call)
    completed = False
    try:
        for outer in sorted(calls_by_outer):
            calls = calls_by_outer[outer]
            inner = [call for call in calls if call["inner_contest"] is not None]
            full = next(call for call in calls if call["inner_contest"] is None)
            inner_values = {}
            for call in inner:
                values = service.predict(call, sql)
                inner_values[call["inner_contest"]] = values
                (archive / f"{call['call_id']}.json").write_text(json.dumps(values, indent=2, sort_keys=True))
            candidates = {}
            for lam in LAMDAS:
                errors = []
                for call in inner:
                    for order, residual in inner_values[call["inner_contest"]].items():
                        row = manifest["rows"][order]
                        errors.append((call["baseline"][order] + lam * residual - row["cf"]) ** 2)
                candidates[lam] = float(np.mean(errors))
            lam = min(LAMDAS, key=lambda value: candidates[value])
            selected[str(outer)] = {"tabfm_lambda": lam, "inner_mse": candidates[lam]}
            full_values = service.predict(full, sql)
            (archive / f"{full['call_id']}.json").write_text(json.dumps(full_values, indent=2, sort_keys=True))
            for order, residual in full_values.items():
                prediction_by_row[manifest["rows"][order]["row_id"]] = float(residual)
            print(f"completed outer CF contest {outer}", flush=True)
        completed = True
    finally:
        if cleanup and completed:
            service.cleanup()
    predictions = []
    for row in manifest["rows"]:
        control = controls[row["row_id"]]
        entry = {"row_id": row["row_id"], "cf": row["cf"], "cf_contest": row["cf_contest"],
                 "region": row["region"], "features": {name: row[name] for name in FEATURES}}
        entry.update(control)
        entry["tabfm_residual"] = control["raw_affine"] + selected[str(row["cf_contest"])]["tabfm_lambda"] * prediction_by_row[row["row_id"]]
        predictions.append(entry)
    methods = ("raw_affine", "gym_shape_affine", "ridge_DET", "ridge_DE", "tabfm_residual")
    result = {"research_only": True, "independent_confirmation": False,
              "not_for_production_promotion": True, "tabfm_status": "run",
              "backend": {"service": "BigQuery AI.PREDICT TabFM Preview", "project": project,
                          "location": location, "dataset": dataset, "unexposed": ["seed", "checkpoint_revision", "ensemble_count", "context_size"]},
              "run_id": manifest["run_id"], "query_limit": QUERY_LIMIT, "maximum_bytes_billed": BYTE_CAP,
              "anchor_coverage": {"problems": len(predictions), "contests": len(calls_by_outer)},
              "selected_by_outer_contest": selected, "metrics": {method: _metrics(predictions, method) for method in methods},
              "predictions": predictions, "baseline_provenance_sha256": baseline["provenance_sha256"],
              "source_sha256": {"module": _file_digest(__file__),
                                "plan": _file_digest(Path(__file__).parent.parent / "tabfm_cloud_plan.md")},
              "archive": str(archive), "tables_deleted_after_archive": cleanup}
    OUT.write_text(json.dumps(result, indent=2))
    return result


def smoke(project, location):
    """Run the required bounded native-function gate using two duplicate feature rows."""
    manifest = build_manifest()
    ledger = SubmissionLedger(ARCHIVE_ROOT / manifest["run_id"] / "smoke_ledger.json", limit=10)
    dataset = "tabfm_research_smoke"
    service = BigQueryService(project, location, dataset, ledger)
    service.setup()
    train, queries = [], []
    for call_id in ("smoke_a", "smoke_b"):
        for index in range(40):
            entry = {name: float(index + feature) for feature, name in enumerate(FEATURES)}
            entry["residual"] = float(2 * index + 1)
            entry.update({"call_id": call_id, "training_row_id": f"{call_id}-train-{index}"})
            train.append(entry)
        for row_id in (0, 1):
            entry = {name: 21.0 + feature for feature, name in enumerate(FEATURES)}
            entry.update({"call_id": call_id, "prediction_row": row_id})
            queries.append(entry)
    try:
        service.upload("contexts", train, manifest["run_id"])
        service.upload("queries", queries, manifest["run_id"])
        first = service.predict({"call_id": "smoke_a", "prediction_rows": [0, 1]},
                                inference_sql(project, dataset))
        second = service.predict({"call_id": "smoke_b", "prediction_rows": [0, 1]},
                                 inference_sql(project, dataset))
        report = {"passed": set(first) == {0, 1} and set(second) == {0, 1}, "first": first, "second": second,
                  "repeatability_equal": first == second, "ledger": str(ledger.path)}
        if not report["passed"]:
            raise RuntimeError("synthetic TabFM smoke did not preserve both prediction IDs")
        (ledger.path.parent / "smoke.json").write_text(json.dumps(report, indent=2))
        return report
    finally:
        service.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke", "run"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--dataset", default="tabfm_research")
    parser.add_argument("--keep-tables", action="store_true")
    args = parser.parse_args()
    if args.command == "smoke":
        print(json.dumps(smoke(args.project, args.location), indent=2))
    else:
        result = run(args.project, args.location, args.dataset, cleanup=not args.keep_tables)
        print(json.dumps({name: value["rmse"] for name, value in result["metrics"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
