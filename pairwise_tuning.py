#!/usr/bin/env python3
"""Collect, freeze, preflight, run, and score CF pairwise Gemini tuning."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from cf_pairwise import (
    FINAL_TEST_END,
    FINAL_TEST_START,
    PILOT_PAIR_COUNT,
    POST_CUTOFF,
    SCHEMA,
    SEED,
    SYSTEM,
    TRAIN_COUNT,
    TUNING_VALIDATION_PAIR_COUNT,
    accuracy,
    choose_pilot_problems,
    content_hash,
    editorial_text,
    has_substantive_editorial,
    newest_substantive_train,
    parse_start,
    partition_problems,
    problem_public,
    sample_pairs,
    sample_covering_pairs,
    sha256_bytes,
    statement_hash,
    statement_text,
    split_by_contest,
    swapped_pairs,
    tuning_example,
    user_text,
)


ROOT = Path(__file__).parent
DATA = ROOT / "data" / "cf_pairwise"
PROBLEMS = DATA / "problems"
DEFAULT_CF_INTEGRATION = ROOT.parent / "codeforces_integration"
MODEL = "gemini-3.5-flash"
TUNING_LOCATION = "us-central1"
PILOT_EPOCHS = 2
TRAINING_PRICE_PER_MILLION = 10.0
BASE_INPUT_PRICE_PER_MILLION = 1.65
BASE_OUTPUT_PRICE_PER_MILLION = 9.90
TUNED_MULTIPLIER = 1.5
PILOT_TRAINING_CAP_USD = 15.0
PILOT_TOTAL_CAP_USD = 25.0
PILOT_EVAL_RESERVE_USD = 10.0
BASELINE_UNORDERED_COUNT = 100
PRO_BASELINE_UNORDERED_COUNT = 10
PRO_MODEL = "gemini-3.1-pro-preview"
PHASE2_PAIR_COUNT = 400
PHASE2_TUNING_VALIDATION_PAIR_COUNT = 75
PHASE2_DEV_UNORDERED_COUNT = 50


def iso_utc(timestamp: int | float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def load_problem_files() -> list[dict]:
    rows = []
    for path in sorted(PROBLEMS.glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid problem cache file {path}: {exc}") from exc
    return rows


def collect(args: argparse.Namespace) -> None:
    integration = args.cf_integration.resolve()
    if not (integration / "cf_problems" / "api.py").exists():
        raise SystemExit(f"Codeforces integration not found: {integration}")
    sys.path.insert(0, str(integration))
    try:
        from cf_problems import CodeforcesAPI, Scraper
        from cf_problems.scraper import FetchError
        from cf_problems.transport import build_session
    except ImportError as exc:
        raise SystemExit(
            "Install codeforces_integration/requirements.txt into the active Python environment"
        ) from exc

    PROBLEMS.mkdir(parents=True, exist_ok=True)
    session = build_session(cookies=args.cookies)
    api = CodeforcesAPI(delay=args.delay, session=session)
    scraper = Scraper(delay=args.delay, session=session)
    metas = [p for p in api.problemset_problems() if p.rating is not None and p.type != "QUESTION"]
    contests = api._get("contest.list", gym="false")  # same official API client/throttle
    starts = {
        int(c["id"]): int(c["startTimeSeconds"])
        for c in contests
        if c.get("phase") == "FINISHED" and c.get("startTimeSeconds") is not None
    }
    metas = [p for p in metas if p.contest_id in starts]
    metas.sort(key=lambda p: (starts[p.contest_id], p.contest_id, p.index), reverse=True)
    post_ids = {
        p.problem_id
        for p in metas
        if POST_CUTOFF.timestamp() <= starts[p.contest_id] < FINAL_TEST_END.timestamp()
    }

    existing = {p["problem_id"]: p for p in load_problem_files()}
    usable_pre_hashes = {
        statement_hash(p)
        for p in existing.values()
        if starts.get(p["contest_id"], 0) < POST_CUTOFF.timestamp() and statement_text(p)
    }
    done_post = {pid for pid in existing if pid in post_ids}
    selected = []
    for meta in metas:
        is_post = meta.problem_id in post_ids
        is_pre = starts[meta.contest_id] < POST_CUTOFF.timestamp()
        if not is_post and (not is_pre or len(usable_pre_hashes) >= args.target_pre_cutoff):
            continue
        if is_post and meta.problem_id in done_post:
            continue
        if is_pre and meta.problem_id in existing:
            continue
        selected.append(meta)

    print(
        f"existing usable pre-cutoff unique={len(usable_pre_hashes)}; "
        f"post-cutoff cached={len(done_post)}/{len(post_ids)}; queued={len(selected)}",
        flush=True,
    )
    fetched = Counter()
    for i, meta in enumerate(selected, 1):
        is_post = meta.problem_id in post_ids
        if not is_post and len(usable_pre_hashes) >= args.target_pre_cutoff:
            continue
        try:
            statement = scraper.fetch_statement(meta)
        except FetchError as exc:
            fetched["error"] += 1
            print(f"[{i}/{len(selected)}] {meta.problem_id} error: {exc}", flush=True)
            continue
        if not statement:
            fetched["missing"] += 1
            print(f"[{i}/{len(selected)}] {meta.problem_id} missing", flush=True)
            continue
        problem = {
            **meta.__dict__,
            "problem_id": meta.problem_id,
            "url": meta.url,
            "contest_start_time": iso_utc(starts[meta.contest_id]),
            "statement": {
                "title": statement.title,
                "time_limit": statement.time_limit,
                "memory_limit": statement.memory_limit,
                "legend": statement.legend,
                "input_spec": statement.input_spec,
                "output_spec": statement.output_spec,
                "note": statement.note,
                "samples": [sample.__dict__ for sample in statement.samples],
            },
            "fetch": {"statement": "ok"},
        }
        text = statement_text(problem)
        if not text:
            fetched["empty"] += 1
            print(f"[{i}/{len(selected)}] {meta.problem_id} empty", flush=True)
            continue
        (PROBLEMS / f"{meta.problem_id}.json").write_text(
            json.dumps(problem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        existing[meta.problem_id] = problem
        if is_post:
            done_post.add(meta.problem_id)
        else:
            usable_pre_hashes.add(statement_hash(problem))
        fetched["ok"] += 1
        print(
            f"[{i}/{len(selected)}] {meta.problem_id} ok; "
            f"pre_unique={len(usable_pre_hashes)}, post={len(done_post)}/{len(post_ids)}",
            flush=True,
        )
        if len(usable_pre_hashes) >= args.target_pre_cutoff:
            break

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "codeforces_integration": str(integration),
        "rated_metadata_count": len(metas),
        "required_train_unique": args.target_pre_cutoff,
        "usable_pre_cutoff_unique": len(usable_pre_hashes),
        "post_cutoff_metadata": len(post_ids),
        "post_cutoff_cached": len(done_post),
        "fetched": dict(fetched),
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "collection_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if len(usable_pre_hashes) < args.target_pre_cutoff:
        raise SystemExit("collection incomplete; rerun to retry missing/transient fetches")


def enrich(args: argparse.Namespace) -> None:
    """Add problem-scoped editorials to frozen train/development records."""
    integration = args.cf_integration.resolve()
    if not (integration / "cf_problems" / "scraper.py").exists():
        raise SystemExit(f"Codeforces integration not found: {integration}")
    sys.path.insert(0, str(integration))
    try:
        from cf_problems import Scraper
        from cf_problems.models import ProblemMeta
        from cf_problems.scraper import FetchError
        from cf_problems.transport import build_session
    except ImportError as exc:
        raise SystemExit(
            "Install codeforces_integration/requirements.txt into the active Python environment"
        ) from exc

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if "test" in args.partitions:
        raise SystemExit("final-test enrichment is forbidden before the development decision")
    expected = {
        row["problem_id"]: row["statement_sha256"]
        for part in args.partitions
        for row in manifest["partitions"][part]["problems"]
    }
    if args.extra_pre_cutoff:
        expected.update(
            {
                p["problem_id"]: statement_hash(p)
                for p in load_problem_files()
                if parse_start(p) < POST_CUTOFF
            }
        )
    cached = {p["problem_id"]: p for p in load_problem_files()}
    missing = sorted(set(expected) - set(cached))
    if missing:
        raise ValueError(f"missing {len(missing)} frozen problem records")
    for pid, digest in expected.items():
        if statement_hash(cached[pid]) != digest:
            raise ValueError(f"cached statement mismatch for {pid}")

    session = build_session(cookies=args.cookies)
    scraper = Scraper(delay=args.delay, session=session)
    fetch_uncached = scraper._fetch
    blog_pages = {}

    def fetch_with_blog_cache(url: str):
        if "/blog/entry/" not in url:
            return fetch_uncached(url)
        if url not in blog_pages:
            blog_pages[url] = fetch_uncached(url)
        return deepcopy(blog_pages[url])

    scraper._fetch = fetch_with_blog_cache
    counts = Counter()
    targets = [cached[pid] for pid in sorted(expected)]
    blog_by_contest = {
        p["contest_id"]: p["editorial"]["url"]
        for p in targets
        if (p.get("editorial") or {}).get("url")
    }
    for i, problem in enumerate(targets, 1):
        old_status = (problem.get("fetch") or {}).get("editorial")
        if old_status == "ok" or (old_status == "missing" and not args.retry_missing):
            counts[f"cached_{old_status}"] += 1
            continue
        meta = ProblemMeta(
            contest_id=problem["contest_id"],
            index=problem["index"],
            name=problem["name"],
            rating=problem.get("rating"),
            tags=problem.get("tags") or [],
            points=problem.get("points"),
            type=problem.get("type"),
        )
        try:
            blog_url = blog_by_contest.get(meta.contest_id)
            editorial = (
                scraper.fetch_editorial_by_url(blog_url, meta.problem_id)
                if blog_url
                else scraper.fetch_editorial(meta)
            )
        except FetchError as exc:
            problem.setdefault("fetch", {})["editorial"] = "error"
            counts["error"] += 1
            print(f"[{i}/{len(targets)}] {meta.problem_id} error: {exc}", flush=True)
        else:
            data = asdict(editorial) if editorial else None
            if data and data.get("url"):
                blog_by_contest[meta.contest_id] = data["url"]
            problem["editorial"] = data
            status = "ok" if has_substantive_editorial(problem) else "missing"
            problem.setdefault("fetch", {})["editorial"] = status
            counts[status] += 1
            code_count = len((data or {}).get("solution_code") or [])
            print(
                f"[{i}/{len(targets)}] {meta.problem_id} {status}; code={code_count}",
                flush=True,
            )
        (PROBLEMS / f"{meta.problem_id}.json").write_text(
            json.dumps(problem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    refreshed = {p["problem_id"]: p for p in load_problem_files() if p["problem_id"] in expected}
    coverage = {
        "target_count": len(expected),
        "editorial_count": sum(
            has_substantive_editorial(p) for p in refreshed.values()
        ),
        "code_count": sum(
            bool((p.get("editorial") or {}).get("solution_code")) for p in refreshed.values()
        ),
    }
    summary = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256_bytes(args.manifest.read_bytes()),
        "partitions": args.partitions,
        "counts": dict(counts),
        "coverage": coverage,
        "final_test_touched": False,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "phase2_enrichment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def jsonl_bytes(examples: list[dict]) -> bytes:
    return b"".join(
        (json.dumps(example, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        for example in examples
    )


def prepare(args: argparse.Namespace) -> None:
    problems = load_problem_files()
    parts = partition_problems(problems)
    by_id = {p["problem_id"]: p for p in problems}
    pilot_problems = choose_pilot_problems(parts["train"])
    pilot_pairs = sample_pairs(
        pilot_problems,
        PILOT_PAIR_COUNT,
        {"200": 0.25, "300": 0.35, "400+": 0.40},
        SEED,
    )
    tuning_validation_pairs = sample_pairs(
        parts["validation"],
        TUNING_VALIDATION_PAIR_COUNT,
        {"200": 0.30, "300": 0.35, "400+": 0.35},
        SEED + 1,
    )
    baseline_unordered = sample_pairs(
        parts["validation"],
        500,
        {"200": 0.20, "300": 0.30, "400+": 0.50},
        SEED + 2,
    )
    pro_baseline_unordered = sample_pairs(
        parts["validation"],
        50,
        {"200": 0.20, "300": 0.30, "400+": 0.50},
        SEED + 4,
    )
    test_unordered = sample_pairs(
        parts["test"],
        500,
        {"200": 0.30, "300": 0.30, "400+": 0.40},
        SEED + 3,
    )
    baseline_pairs = swapped_pairs(baseline_unordered[:BASELINE_UNORDERED_COUNT])
    pro_baseline_pairs = swapped_pairs(
        pro_baseline_unordered[:PRO_BASELINE_UNORDERED_COUNT]
    )
    test_pairs = swapped_pairs(test_unordered)

    args.output.mkdir(parents=True, exist_ok=True)
    train_data = jsonl_bytes([tuning_example(pair, by_id) for pair in pilot_pairs])
    validation_data = jsonl_bytes(
        [tuning_example(pair, by_id) for pair in tuning_validation_pairs]
    )
    (args.output / "pilot_train.jsonl").write_bytes(train_data)
    (args.output / "pilot_validation.jsonl").write_bytes(validation_data)

    source_rows = [problem_public(p) for p in problems if statement_text(p)]
    source_hash = sha256_bytes(
        json.dumps(source_rows, sort_keys=True, separators=(",", ":")).encode()
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "model": MODEL,
        "pro_baseline_model": PRO_MODEL,
        "knowledge_cutoff_policy": {
            "google_documented_cutoff": "January 2025",
            "first_unambiguously_post_cutoff": POST_CUTOFF.isoformat(),
        },
        "partitions": {
            name: {
                "count": len(rows),
                "contest_count": len({p["contest_id"] for p in rows}),
                "problems": [problem_public(p) for p in rows],
            }
            for name, rows in parts.items()
        },
        "source_snapshot_sha256": source_hash,
        "pilot_problem_ids": [p["problem_id"] for p in pilot_problems],
        "pilot_pairs": pilot_pairs,
        "tuning_validation_pairs": tuning_validation_pairs,
        "baseline_pairs": baseline_pairs,
        "pro_baseline_pairs": pro_baseline_pairs,
        "test_pairs": test_pairs,
        "files": {
            "pilot_train.jsonl": {
                "sha256": sha256_bytes(train_data),
                "bytes": len(train_data),
                "examples": len(pilot_pairs),
            },
            "pilot_validation.jsonl": {
                "sha256": sha256_bytes(validation_data),
                "bytes": len(validation_data),
                "examples": len(tuning_validation_pairs),
            },
        },
        "test_upload_forbidden": True,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "partitions": {
                    k: {"problems": len(v), "contests": len({p['contest_id'] for p in v})}
                    for k, v in parts.items()
                },
                "pilot_pairs": len(pilot_pairs),
                "tuning_validation_pairs": len(tuning_validation_pairs),
                "baseline_requests": len(baseline_pairs),
                "pro_baseline_requests": len(pro_baseline_pairs),
                "frozen_test_requests": len(test_pairs),
            },
            indent=2,
        )
    )


def prepare_phase2(args: argparse.Namespace) -> None:
    problems = load_problem_files()
    parts = partition_problems(problems)
    try:
        phase2_train = newest_substantive_train(problems, None)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    enriched_validation = [p for p in parts["validation"] if has_substantive_editorial(p)]
    tuning_rows, development_rows = split_by_contest(enriched_validation, SEED + 20)
    if not tuning_rows or not development_rows:
        raise ValueError("contest-disjoint Phase 2 validation split is empty")

    train_pairs = sample_covering_pairs(
        phase2_train,
        args.pair_count,
        {"200": 0.25, "300": 0.35, "400+": 0.40},
        SEED + 21,
    )
    tuning_pairs = sample_pairs(
        tuning_rows,
        PHASE2_TUNING_VALIDATION_PAIR_COUNT,
        {"200": 0.30, "300": 0.35, "400+": 0.35},
        SEED + 22,
    )
    development_unordered = sample_pairs(
        development_rows,
        PHASE2_DEV_UNORDERED_COUNT,
        {"200": 0.30, "300": 0.40, "400+": 0.30},
        SEED + 23,
    )
    development_pairs = swapped_pairs(development_unordered)
    by_id = {p["problem_id"]: p for p in problems}
    args.output.mkdir(parents=True, exist_ok=True)

    files = {}
    for mode in ("editorial", "editorial_code"):
        train_data = jsonl_bytes([tuning_example(pair, by_id, mode) for pair in train_pairs])
        validation_data = jsonl_bytes(
            [tuning_example(pair, by_id, mode) for pair in tuning_pairs]
        )
        for kind, data, count in (
            ("train", train_data, len(train_pairs)),
            ("validation", validation_data, len(tuning_pairs)),
        ):
            name = f"phase2_{mode}_{kind}.jsonl"
            (args.output / name).write_bytes(data)
            files[name] = {
                "sha256": sha256_bytes(data),
                "bytes": len(data),
                "examples": count,
            }

    split_rows = {
        "train": phase2_train,
        "tuning_validation": tuning_rows,
        "development": development_rows,
        "test": parts["test"],
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "model": MODEL,
        "input_modes": ["editorial", "editorial_code"],
        "partitions": {
            name: {
                "count": len(rows),
                "contest_count": len({p["contest_id"] for p in rows}),
                "problems": [
                    {
                        **problem_public(p),
                        "editorial_sha256": content_hash(p, "editorial"),
                        "editorial_code_sha256": content_hash(p, "editorial_code"),
                    }
                    if has_substantive_editorial(p)
                    else problem_public(p)
                    for p in rows
                ],
            }
            for name, rows in split_rows.items()
        },
        "train_pairs": train_pairs,
        "training_pair_count": args.pair_count,
        "tuning_validation_pairs": tuning_pairs,
        "phase2_dev_pairs": development_pairs,
        "files": files,
        "coverage": {
            "training_problems": len(phase2_train),
            "training_problems_with_code": sum(
                bool((p.get("editorial") or {}).get("solution_code")) for p in phase2_train
            ),
            "enriched_validation_problems": len(enriched_validation),
        },
        "split_contract": {
            "tuning_development_contest_disjoint": not (
                {p["contest_id"] for p in tuning_rows}
                & {p["contest_id"] for p in development_rows}
            ),
            "all_training_problems_used": {
                p["problem_id"] for p in phase2_train
            }
            == {pid for pair in train_pairs for pid in (pair["a"], pair["b"])},
            "final_test_enriched": False,
            "final_test_upload_forbidden": True,
        },
    }
    (args.output / "phase2_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "training_pairs": len(train_pairs),
                "training_problems": len(phase2_train),
                "tuning_validation_pairs": len(tuning_pairs),
                "development_requests": len(development_pairs),
                "coverage": manifest["coverage"],
                "split_contract": manifest["split_contract"],
            },
            indent=2,
        )
    )


class Vertex:
    def __init__(self, project: str):
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleRequest
        except ImportError as exc:
            raise RuntimeError("Vertex commands require google-auth") from exc
        self.project = project
        self.credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.auth_request = GoogleRequest()
        if not self.credentials.valid or self.credentials.expired:
            self.credentials.refresh(self.auth_request)

    def request(self, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                if not self.credentials.valid or self.credentials.expired:
                    self.credentials.refresh(self.auth_request)
                req = Request(
                    url,
                    data=json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
                    headers={
                        "Authorization": f"Bearer {self.credentials.token}",
                        "Content-Type": "application/json",
                        "User-Agent": "cf-pairwise-tuning/1.0",
                    },
                    method="POST" if payload is not None else "GET",
                )
                with urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode())
            except HTTPError as exc:
                body = exc.read().decode(errors="replace")
                last_error = RuntimeError(f"HTTP {exc.code}: {body}")
                if exc.code not in {408, 409, 429, 500, 502, 503, 504}:
                    raise last_error
            except (URLError, TimeoutError, socket.timeout) as exc:
                last_error = exc
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
        raise last_error or RuntimeError("request failed")


def count_url(project: str, location: str, model: str) -> str:
    if location == "global":
        host = "aiplatform.googleapis.com"
    elif location in {"us", "eu"}:
        host = f"aiplatform.{location}.rep.googleapis.com"
    else:
        host = f"{location}-aiplatform.googleapis.com"
    return (
        f"https://{host}/v1/projects/{quote(project, safe='')}/locations/"
        f"{quote(location, safe='')}/publishers/google/models/{quote(model, safe='')}:countTokens"
    )


def count_dataset(args: argparse.Namespace) -> None:
    examples = [json.loads(line) for line in args.dataset.read_text().splitlines()]
    vertex = Vertex(args.project)
    url = count_url(args.project, args.location, args.model)

    def one(example: dict) -> int:
        return int(vertex.request(url, example)["totalTokens"])

    counts = [0] * len(examples)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, example): i for i, example in enumerate(examples)}
        for future in as_completed(futures):
            counts[futures[future]] = future.result()
    tokens = sum(counts)
    training_cost = tokens * PILOT_EPOCHS * TRAINING_PRICE_PER_MILLION / 1_000_000
    planned = training_cost + args.eval_reserve_usd
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "location": args.location,
        "model": args.model,
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_bytes(args.dataset.read_bytes()),
        "examples": len(examples),
        "tokens_per_epoch": tokens,
        "epochs": PILOT_EPOCHS,
        "estimated_training_cost_usd": round(training_cost, 6),
        "evaluation_reserve_usd": args.eval_reserve_usd,
        "planned_pilot_total_usd": round(planned, 6),
        "pilot_training_cap_usd": args.training_cap_usd,
        "pilot_total_cap_usd": args.total_cap_usd,
        "dispatch_allowed": training_cost <= args.training_cap_usd and planned <= args.total_cap_usd,
        "minimum_example_tokens": min(counts),
        "maximum_example_tokens": max(counts),
        "mean_example_tokens": tokens / len(counts),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["dispatch_allowed"]:
        raise SystemExit("pilot cost cap exceeded; dispatch forbidden")


def generate_url(project: str, target: str, location: str) -> str:
    if target.startswith("projects/"):
        endpoint_location = target.split("/")[3]
        host = (
            f"aiplatform.{endpoint_location}.rep.googleapis.com"
            if endpoint_location in {"us", "eu"}
            else f"{endpoint_location}-aiplatform.googleapis.com"
        )
        return f"https://{host}/v1/{target}:generateContent"
    if location == "global":
        host = "aiplatform.googleapis.com"
    elif location in {"us", "eu"}:
        host = f"aiplatform.{location}.rep.googleapis.com"
    else:
        host = f"{location}-aiplatform.googleapis.com"
    return (
        f"https://{host}/v1/projects/{quote(project, safe='')}/locations/"
        f"{quote(location, safe='')}/publishers/google/models/{quote(target, safe='')}:generateContent"
    )


def response_text(response: dict) -> str:
    candidates = response.get("candidates") or []
    if not candidates:
        raise ValueError("response has no candidates")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts if not part.get("thought"))


def load_manifest_problems(manifest: dict, input_mode: str = "statement") -> dict[str, dict]:
    cached = {p["problem_id"]: p for p in load_problem_files()}
    expected = {
        p["problem_id"]: p["statement_sha256"]
        for part in manifest["partitions"].values()
        for p in part["problems"]
    }
    for pid, digest in expected.items():
        if pid not in cached or statement_hash(cached[pid]) != digest:
            raise ValueError(f"cached statement mismatch for {pid}")
    if input_mode != "statement":
        hash_key = f"{input_mode}_sha256"
        enriched_expected = {
            p["problem_id"]: p[hash_key]
            for part in manifest["partitions"].values()
            for p in part["problems"]
            if hash_key in p
        }
        if not enriched_expected:
            raise ValueError(f"manifest has no frozen hashes for input mode {input_mode}")
        for pid, digest in enriched_expected.items():
            if content_hash(cached[pid], input_mode) != digest:
                raise ValueError(f"cached {input_mode} mismatch for {pid}")
    return cached


def evaluate(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text())
    pairs = manifest[args.pairs_key]
    by_id = load_manifest_problems(manifest, args.input_mode)
    saved = json.loads(args.output.read_text()) if args.output.exists() else {"predictions": []}
    for key, expected in (
        ("target", args.target),
        ("pairs_key", args.pairs_key),
        ("input_mode", args.input_mode),
        ("manifest_sha256", sha256_bytes(args.manifest.read_bytes())),
    ):
        if saved.get("predictions") and saved.get(key) != expected:
            raise ValueError(f"existing prediction checkpoint has different {key}")
    done = {(p["a"], p["b"]) for p in saved["predictions"]}
    vertex = Vertex(args.project)
    url = generate_url(args.project, args.target, args.location)

    def one(pair: dict) -> dict:
        a, b = by_id[pair["a"]], by_id[pair["b"]]
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [
                {"role": "user", "parts": [{"text": user_text(a, b, args.input_mode)}]}
            ],
            "generationConfig": {
                "thinkingConfig": {"thinkingLevel": args.thinking_level.upper()},
                "maxOutputTokens": 1024 if "pro" in args.target else 64,
                "responseMimeType": "application/json",
                "responseSchema": SCHEMA,
                "temperature": 0,
            },
        }
        response = vertex.request(url, payload)
        decoded = json.loads(response_text(response))
        predicted = decoded.get("harder")
        if predicted not in {"A", "B"}:
            raise ValueError(f"invalid prediction: {decoded!r}")
        return {
            **pair,
            "predicted": predicted,
            "request_location": args.location,
            "usage": response.get("usageMetadata", {}),
        }

    remaining = [p for p in pairs if (p["a"], p["b"]) not in done]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, pair): pair for pair in remaining}
        for future in as_completed(futures):
            item = future.result()
            saved["predictions"].append(item)
            saved.update({
                "project": args.project,
                "target": args.target,
                "location": args.location,
                "pairs_key": args.pairs_key,
                "thinking_level": args.thinking_level,
                "input_mode": args.input_mode,
                "manifest_sha256": sha256_bytes(args.manifest.read_bytes()),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            args.output.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
            print(f"[{len(saved['predictions'])}/{len(pairs)}] {item['a']} vs {item['b']}", flush=True)


def submit(args: argparse.Namespace) -> None:
    preflight = json.loads(args.preflight.read_text())
    if not preflight.get("dispatch_allowed"):
        raise SystemExit("preflight forbids tuning dispatch")
    if preflight.get("epochs") != PILOT_EPOCHS:
        raise ValueError("preflight epoch count mismatch")
    if preflight.get("dataset_sha256") != sha256_bytes(args.train_file.read_bytes()):
        raise ValueError("training file changed after countTokens preflight")
    if args.output.exists():
        raise SystemExit(f"submission already exists: {args.output}")
    payload = {
        "baseModel": args.model,
        "supervisedTuningSpec": {
            "trainingDatasetUri": args.train_uri,
            "validationDatasetUri": args.validation_uri,
            "hyperParameters": {
                "epochCount": PILOT_EPOCHS,
            },
            "exportLastCheckpointOnly": True,
        },
        "tunedModelDisplayName": args.display_name,
    }
    request_path = args.output.with_name("tuning_request.json")
    request_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    url = (
        f"https://{args.location}-aiplatform.googleapis.com/v1/projects/"
        f"{quote(args.project, safe='')}/locations/{quote(args.location, safe='')}/tuningJobs"
    )
    response = Vertex(args.project).request(url, payload)
    args.output.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(response, indent=2))


def status(args: argparse.Namespace) -> None:
    submission = json.loads(args.submission.read_text())
    name = submission["name"]
    location = name.split("/")[3]
    url = f"https://{location}-aiplatform.googleapis.com/v1/{name}"
    response = Vertex(args.project).request(url)
    args.output.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(response, indent=2))


def usage_cost(predictions: list[dict], multiplier: float) -> dict:
    usage = Counter()
    for item in predictions:
        for key, value in item.get("usage", {}).items():
            if isinstance(value, int):
                usage[key] += value
    input_tokens = usage["promptTokenCount"]
    output_tokens = usage["candidatesTokenCount"] + usage["thoughtsTokenCount"]
    cost = multiplier * (
        input_tokens * BASE_INPUT_PRICE_PER_MILLION
        + output_tokens * BASE_OUTPUT_PRICE_PER_MILLION
    ) / 1_000_000
    return {"usage": dict(usage), "estimated_cost_usd": round(cost, 6)}


def score(args: argparse.Namespace) -> None:
    base = json.loads(args.base.read_text())
    tuned = json.loads(args.tuned.read_text())
    key = lambda p: (p["a"], p["b"])
    base_by = {key(p): p for p in base["predictions"]}
    tuned_by = {key(p): p for p in tuned["predictions"]}
    if set(base_by) != set(tuned_by):
        raise ValueError("base and tuned predictions are not paired")
    order = [key(p) for p in base["predictions"]]
    base_rows = [base_by[k] for k in order]
    tuned_rows = [tuned_by[k] for k in order]
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base": {**accuracy(base_rows), **usage_cost(base_rows, 1.0)},
        "tuned": {**accuracy(tuned_rows), **usage_cost(tuned_rows, TUNED_MULTIPLIER)},
    }
    result["gain"] = {
        "accuracy": result["tuned"]["accuracy"] - result["base"]["accuracy"],
        "exact_200": result["tuned"]["exact_200"]["accuracy"] - result["base"]["exact_200"]["accuracy"],
        "exact_300": result["tuned"]["exact_300"]["accuracy"] - result["base"]["exact_300"]["accuracy"],
        "at_least_300": result["tuned"]["at_least_300"]["accuracy"] - result["base"]["at_least_300"]["accuracy"],
    }
    if args.preflight:
        preflight = json.loads(args.preflight.read_text())
        result["cost_ledger"] = {
            "estimated_training_cost_usd": preflight["estimated_training_cost_usd"],
            "estimated_inference_cost_usd": round(
                result["base"]["estimated_cost_usd"] + result["tuned"]["estimated_cost_usd"], 6
            ),
            "pilot_total_cap_usd": PILOT_TOTAL_CAP_USD,
        }
        result["cost_ledger"]["estimated_total_usd"] = round(
            result["cost_ledger"]["estimated_training_cost_usd"]
            + result["cost_ledger"]["estimated_inference_cost_usd"],
            6,
        )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--cf-integration", type=Path, default=DEFAULT_CF_INTEGRATION)
    c.add_argument("--delay", type=float, default=2.0)
    c.add_argument("--cookies")
    c.add_argument("--target-pre-cutoff", type=int, default=TRAIN_COUNT)
    x = sub.add_parser("enrich")
    x.add_argument("--manifest", type=Path, required=True)
    x.add_argument("--cf-integration", type=Path, default=DEFAULT_CF_INTEGRATION)
    x.add_argument("--partitions", nargs="+", choices=("train", "validation", "test"), default=("train", "validation"))
    x.add_argument("--delay", type=float, default=2.0)
    x.add_argument("--cookies")
    x.add_argument("--retry-missing", action="store_true")
    x.add_argument("--extra-pre-cutoff", action="store_true")
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p2 = sub.add_parser("prepare-phase2")
    p2.add_argument("--output", type=Path, required=True)
    p2.add_argument("--pair-count", type=int, default=PHASE2_PAIR_COUNT)
    n = sub.add_parser("count")
    n.add_argument("--project", required=True)
    n.add_argument("--location", default="global")
    n.add_argument("--model", default=MODEL)
    n.add_argument("--dataset", type=Path, required=True)
    n.add_argument("--output", type=Path, required=True)
    n.add_argument("--workers", type=int, default=4)
    n.add_argument("--training-cap-usd", type=float, default=PILOT_TRAINING_CAP_USD)
    n.add_argument("--total-cap-usd", type=float, default=PILOT_TOTAL_CAP_USD)
    n.add_argument("--eval-reserve-usd", type=float, default=PILOT_EVAL_RESERVE_USD)
    e = sub.add_parser("evaluate")
    e.add_argument("--project", required=True)
    e.add_argument("--target", required=True)
    e.add_argument("--location", default="global")
    e.add_argument("--manifest", type=Path, required=True)
    e.add_argument(
        "--pairs-key",
        choices=("baseline_pairs", "pro_baseline_pairs", "test_pairs", "phase2_dev_pairs"),
        default="baseline_pairs",
    )
    e.add_argument(
        "--input-mode",
        choices=("statement", "editorial", "editorial_code"),
        default="statement",
    )
    e.add_argument("--thinking-level", choices=("minimal", "low", "medium", "high"), default="minimal")
    e.add_argument("--output", type=Path, required=True)
    e.add_argument("--workers", type=int, default=4)
    s = sub.add_parser("submit")
    s.add_argument("--project", required=True)
    s.add_argument("--location", default=TUNING_LOCATION)
    s.add_argument("--model", default=MODEL)
    s.add_argument("--train-file", type=Path, required=True)
    s.add_argument("--train-uri", required=True)
    s.add_argument("--validation-uri", required=True)
    s.add_argument("--display-name", required=True)
    s.add_argument("--preflight", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)
    st = sub.add_parser("status")
    st.add_argument("--project", required=True)
    st.add_argument("--submission", type=Path, required=True)
    st.add_argument("--output", type=Path, required=True)
    sc = sub.add_parser("score")
    sc.add_argument("--base", type=Path, required=True)
    sc.add_argument("--tuned", type=Path, required=True)
    sc.add_argument("--preflight", type=Path)
    sc.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "collect":
        collect(args)
    elif args.command == "enrich":
        enrich(args)
    elif args.command == "prepare":
        prepare(args)
    elif args.command == "prepare-phase2":
        prepare_phase2(args)
    elif args.command == "count":
        count_dataset(args)
    elif args.command == "evaluate":
        evaluate(args)
    elif args.command == "submit":
        submit(args)
    elif args.command == "status":
        status(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
