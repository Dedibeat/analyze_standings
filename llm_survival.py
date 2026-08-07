#!/usr/bin/env python3
"""Run and analyse the zero-shot Gemini/standings-survival experiment.

The paid path is deliberately separate from the rating fit.  Statements are
sanitized before they enter a prompt, comparisons are resumable, and the
survival/Codeforces fields stay in the local manifest rather than the request.

Typical workflow (the first two commands are read-only preflight calls)::

    ./.venv/bin/python llm_survival.py prepare --output llm_survival_run
    ./.venv/bin/python llm_survival.py count --project PROJECT \
        --run-dir llm_survival_run
    ./.venv/bin/python llm_survival.py run --project PROJECT \
        --run-dir llm_survival_run --stage pilot
    ./.venv/bin/python llm_survival.py pilot-check --run-dir llm_survival_run
    ./.venv/bin/python llm_survival.py run --project PROJECT \
        --run-dir llm_survival_run --stage full
    ./.venv/bin/python llm_survival.py analyse --run-dir llm_survival_run

Raw statements and responses belong in the gitignored run directory.  The
``analyse`` command writes a compact JSON result plus a human-readable report.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
from typing import Iterable

import numpy as np

from arch_b.calibrate import _gym_shape
from arch_b.external_validate import _cf_mapping, _cf_problemset, _norm
from pairwise_tuning import Vertex, count_url, generate_url, response_text


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
DEFAULT_RUN_DIR = ROOT / "llm_survival_run"
MODEL = "gemini-3.5-flash"
LOCATION = "global"
SYSTEM = (
    "Compare the inherent competitive-programming difficulty of the two "
    "statements. Judge algorithmic insight, proof burden, and implementation "
    "difficulty. Ignore ordering, labels, titles, contest context, popularity, "
    "and external knowledge. Return only the requested JSON."
)
SCHEMA = {
    "type": "OBJECT",
    "properties": {"harder": {"type": "STRING", "enum": ["A", "B"]}},
    "required": ["harder"],
}
PROMPT_VERSION = "statement-v1-20260807"
SEED = 20260807
INPUT_PRICE_PER_MILLION = 1.65
OUTPUT_PRICE_PER_MILLION = 9.90
MAX_OUTPUT_TOKENS = 64
DEFAULT_BUDGET_USD = 50.0

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
PAGE_RE = re.compile(r"^\s*(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\s*/\s*\d+)\s*$", re.I)
PROBLEM_HEADER_RE = re.compile(r"^\s*problem\s+[A-Z]\d*\s*[:.-]?\s*$", re.I)
PROBLEM_INLINE_RE = re.compile(r"\bproblem\s+[A-Z]\d*\b", re.I)
LIMIT_RE = re.compile(r"^\s*(?:time|memory)\s+limit\s*:", re.I)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _remove_title(text: str, title: str) -> str:
    if not title:
        return text
    # A title is metadata even when a PDF repeats it in a footer.  Removing an
    # inline occurrence is safer than allowing the exact title into a prompt.
    return re.sub(re.escape(title), "the problem", text, flags=re.IGNORECASE)


def sanitize_statement(problem: dict, *, strict: bool = True) -> str:
    """Return statement prose without problem/contest metadata.

    ``tagged.json`` stores PDF-to-text captures.  The sanitizer removes page
    furniture, title/index/contest lines, URLs, and time/memory limits while
    preserving the actual problem, input, output, and sample prose.
    """
    raw = str(problem.get("statement") or "")
    title = canonical_text(str(problem.get("problem_name") or ""))
    contest_name = canonical_text(str(problem.get("contest_name") or ""))
    lines: list[str] = []
    for raw_line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.replace("\x0c", "").strip()
        if not line:
            continue
        if PAGE_RE.match(line) or line.casefold() in {"read", "write"}:
            continue
        if LIMIT_RE.match(line) or PROBLEM_HEADER_RE.match(line):
            continue
        lower = line.casefold()
        # QOJ's PDF captures sometimes split a contest banner into many short
        # lines (year, region, sponsor names), so the full contest name is not
        # present on any one line.  These are source furniture, not statement
        # prose.  Removing a rare in-problem ICPC mention is preferable to
        # exposing contest identity to the model.
        if any(
            token in lower
            for token in (
                "icpc",
                "international collegiate",
                "sponsor",
                "multi-regional",
                "programming tools",
                "europe contests",
                "global contest",
                "swerc",
                "nwerc",
                "nerc",
                "hosted by",
            )
        ):
            continue
        if lower in {"contests", "contest", "the problem", "the problem."}:
            continue
        if re.fullmatch(
            r"\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds|ms|mb|gb|megabytes?)",
            lower,
        ):
            continue
        if re.search(
            r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
            r"nov(?:ember)?|dec(?:ember)?)\b.*\b(?:19|20)\d{2}\b",
            lower,
        ):
            continue
        if re.fullmatch(r"(?:19|20)\d{2}", line) or lower in {
            "europe",
            "asia",
            "northern eurasia",
            "championship",
        }:
            continue
        if URL_RE.search(line):
            line = URL_RE.sub("", line).strip()
        if contest_name and contest_name.casefold() in line.casefold():
            continue
        # PDF footers commonly contain ``... Problem A: <title>`` or an ICPC
        # contest header.  A line mentioning ICPC plus the problem title is
        # metadata, not algorithmic content.
        if title and title.casefold() in line.casefold():
            remainder = re.sub(re.escape(title), "", line, flags=re.IGNORECASE).strip(" :-–—")
            # A short ``H <title>``/``A. <title>`` line is a PDF header, not
            # prose.  Drop it entirely so the following sentence cannot
            # accidentally form the forbidden phrase ``problem A``.
            if not remainder or re.fullmatch(r"(?:problem\s+)?[A-Z]\d*\.?", remainder, re.I):
                continue
            line = remainder
        if title and line.casefold() == title.casefold():
            continue
        if re.search(r"\b(?:ICPC|Codeforces|QOJ)\b", line, re.I) and (
            "problem" in line.casefold() or "contest" in line.casefold()
        ):
            continue
        line = PROBLEM_INLINE_RE.sub("the problem", line)
        lines.append(line)
    text = canonical_text("\n".join(lines))
    # A PDF header can wrap the contest name across lines, so remove the
    # canonical form once more after whitespace normalization.
    if contest_name:
        text = re.sub(re.escape(contest_name), "", text, flags=re.IGNORECASE)
    if title:
        text = re.sub(re.escape(title), "the problem", text, flags=re.IGNORECASE)
    # Remove a numeric source id when it was printed in a footer/header.  Do
    # not remove ordinary constraint numbers throughout the statement.
    if problem.get("problem_id") is not None:
        source_id = str(problem["problem_id"])
        text = re.sub(rf"(?<!\d){re.escape(source_id)}(?!\d)", "", text)
    if strict:
        leaks = statement_leaks(problem, text)
        if leaks:
            raise ValueError(
                f"statement metadata leak for {problem.get('problem_id')}: "
                + ", ".join(leaks)
            )
    return text


def statement_leaks(problem: dict, text: str) -> list[str]:
    """Return prompt-contract violations for a sanitized statement."""
    leaks: list[str] = []
    if URL_RE.search(text):
        leaks.append("url")
    title = canonical_text(str(problem.get("problem_name") or ""))
    if title and title.casefold() in text.casefold():
        leaks.append("title")
    contest_name = canonical_text(str(problem.get("contest_name") or ""))
    if contest_name and contest_name.casefold() in text.casefold():
        leaks.append("contest_name")
    if PROBLEM_INLINE_RE.search(text):
        leaks.append("problem_label")
    return leaks


def prompt_text(statement_a: str, statement_b: str) -> str:
    return f"Statement A:\n{statement_a}\n\nStatement B:\n{statement_b}"


def prompt_payload(statement_a: str, statement_b: str) -> dict:
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt_text(statement_a, statement_b)}]}],
    }


def generation_payload(statement_a: str, statement_b: str) -> dict:
    payload = prompt_payload(statement_a, statement_b)
    payload["generationConfig"] = {
        "thinkingConfig": {"thinkingLevel": "MINIMAL"},
        "maxOutputTokens": MAX_OUTPUT_TOKENS,
        "responseMimeType": "application/json",
        "responseSchema": SCHEMA,
        "temperature": 0,
    }
    return payload


def _load_survival() -> dict[tuple[int, str], dict]:
    rows = json.loads((OUTPUT / "problem_ratings_survival.json").read_text(encoding="utf-8"))
    return {(int(r["contest_id"]), r["problem_label"]): r for r in rows}


def _load_contests() -> list[dict]:
    return json.loads((DATA / "tagged.json").read_text(encoding="utf-8"))


def _cf_mirror_mapping(contests: list[dict]) -> list[tuple[int, int, str, list[str]]]:
    region_of = {int(c["contest_id"]): c.get("region", "?") for c in contests}
    # _cf_mapping prints a useful table; suppress it in machine-readable
    # preparation and write the mapping into the manifest instead.
    with redirect_stdout(__import__("io").StringIO()):
        return _cf_mapping(contests, region_of, _cf_problemset())


def _problem_rows() -> tuple[list[dict], dict[str, str]]:
    contests = _load_contests()
    survival = _load_survival()
    by_contest = {int(c["contest_id"]): c for c in contests}
    rows: list[dict] = []
    statements: dict[str, str] = {}
    for cf_id, qoj_id, region, matched_names in _cf_mirror_mapping(contests):
        contest = by_contest[qoj_id]
        by_name = {_norm(p["problem_name"]): p for p in contest["problems"]}
        for name in matched_names:
            problem = by_name[name]
            key = (qoj_id, problem["problem_label"])
            rating = survival.get(key)
            if rating is None:
                raise ValueError(f"missing survival rating for {key}")
            # The contest record may also carry a single editorial covering
            # every problem.  It is intentionally never read: this run is a
            # statement-only zero-shot experiment.
            text = sanitize_statement(
                {
                    **problem,
                    "contest_name": contest.get("contest_name", ""),
                }
            )
            if len(text) < 40:
                raise ValueError(f"statement too short for {key}")
            pid = str(problem["problem_id"])
            if pid in statements and statements[pid] != text:
                raise ValueError(f"problem id reused with different statement: {pid}")
            statements[pid] = text
            rows.append(
                {
                    "problem_id": pid,
                    "contest_id": qoj_id,
                    "problem_label": problem["problem_label"],
                    "statement_sha256": sha256_text(text),
                    "statement_chars": len(text),
                    "survival_difficulty": float(rating["difficulty"]),
                    "survival_se": float(rating["difficulty_se"]),
                    "cf_contest_id": cf_id,
                    "cf_rating": None,
                    "region": region,
                }
            )
    # Join the official CF rating by the mapping's normalized problem name.
    cf_rating = _cf_problemset()
    for row in rows:
        contest = by_contest[row["contest_id"]]
        p = next(p for p in contest["problems"] if p["problem_id"] == int(row["problem_id"]))
        key = (row["cf_contest_id"], _norm(p["problem_name"]))
        if key not in cf_rating:
            raise ValueError(f"missing Codeforces rating for {key}")
        row["cf_rating"] = int(cf_rating[key])
    rows.sort(key=lambda r: (r["contest_id"], r["problem_label"], r["problem_id"]))
    if len(rows) != 185 or len({r["contest_id"] for r in rows}) != 15:
        raise ValueError(f"expected 185 problems in 15 mirrors, got {len(rows)}")
    return rows, statements


def _request_id(contest_id: int, first: str, second: str, orientation: int) -> str:
    return f"{contest_id}:{first}:{second}:{orientation}"


def _make_requests(rows: list[dict], statements: dict[str, str]) -> list[dict]:
    by_contest: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_contest[row["contest_id"]].append(row)
    requests: list[dict] = []
    for contest_id in sorted(by_contest):
        ps = sorted(by_contest[contest_id], key=lambda r: r["problem_label"])
        for i, left in enumerate(ps):
            for right in ps[i + 1 :]:
                digest = hashlib.sha256(
                    f"{SEED}:{contest_id}:{left['problem_id']}:{right['problem_id']}".encode()
                ).digest()
                first, second = (left, right) if digest[0] & 1 else (right, left)
                pair = (left["problem_id"], right["problem_id"])
                for orientation, a, b in (
                    (0, first, second),
                    (1, second, first),
                ):
                    ptxt = prompt_text(statements[a["problem_id"]], statements[b["problem_id"]])
                    requests.append(
                        {
                            "request_id": _request_id(contest_id, pair[0], pair[1], orientation),
                            "contest_id": contest_id,
                            "pair_key": [pair[0], pair[1]],
                            "display_a": a["problem_id"],
                            "display_b": b["problem_id"],
                            "orientation": orientation,
                            "statement_a_sha256": a["statement_sha256"],
                            "statement_b_sha256": b["statement_sha256"],
                            "prompt_sha256": sha256_text(SYSTEM + "\n" + ptxt),
                        }
                    )
    return requests


def prepare(args: argparse.Namespace) -> None:
    run_dir = args.output
    run_dir.mkdir(parents=True, exist_ok=True)
    rows, statements = _problem_rows()
    requests = _make_requests(rows, statements)
    (run_dir / "statements.json").write_text(
        json.dumps(statements, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": MODEL,
                "location": LOCATION,
                "prompt_version": PROMPT_VERSION,
                "seed": SEED,
                "system_sha256": sha256_text(SYSTEM),
                "source_files": {
                    "tagged.json": sha256_text((DATA / "tagged.json").read_text(encoding="utf-8")),
                    "survival": sha256_text(
                        (OUTPUT / "problem_ratings_survival.json").read_text(encoding="utf-8")
                    ),
                },
                "problems": rows,
                "requests": requests,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"problems": len(rows), "requests": len(requests), "run_dir": str(run_dir)}, indent=2))


def _manifest(run_dir: Path) -> tuple[dict, dict[str, str]]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    statements = json.loads((run_dir / "statements.json").read_text(encoding="utf-8"))
    # Recheck source hashes and every prompt hash before a paid call.
    for row in manifest["problems"]:
        text = statements[row["problem_id"]]
        if sha256_text(text) != row["statement_sha256"]:
            raise ValueError(f"statement hash mismatch for {row['problem_id']}")
    return manifest, statements


def _stage_requests(manifest: dict, stage: str) -> list[dict]:
    requests = manifest["requests"]
    if stage == "pilot":
        contest_ids = {3747}
        result = [r for r in requests if r["contest_id"] in contest_ids]
        if len(result) != 156:
            raise ValueError(f"pilot must contain 156 requests, got {len(result)}")
        return result
    if stage == "full":
        return requests
    raise ValueError(f"unknown stage {stage}")


def _count_one(vertex: Vertex, url: str, request: dict, statements: dict[str, str]) -> int:
    payload = prompt_payload(statements[request["display_a"]], statements[request["display_b"]])
    response = vertex.request(url, payload)
    return int(response["totalTokens"])


def _cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * INPUT_PRICE_PER_MILLION + output_tokens * OUTPUT_PRICE_PER_MILLION
    ) / 1_000_000


def count(args: argparse.Namespace) -> None:
    run_dir = args.run_dir
    manifest, statements = _manifest(run_dir)
    requests = _stage_requests(manifest, args.stage)
    vertex = Vertex(args.project)
    url = count_url(args.project, args.location, manifest["model"])
    counts = [None] * len(requests)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_count_one, vertex, url, request, statements): i
            for i, request in enumerate(requests)
        }
        for future in as_completed(futures):
            counts[futures[future]] = future.result()
    input_tokens = int(sum(counts))
    output_ceiling = len(requests) * MAX_OUTPUT_TOKENS
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "location": args.location,
        "model": manifest["model"],
        "stage": args.stage,
        "prompt_version": manifest["prompt_version"],
        "request_count": len(requests),
        "input_tokens": input_tokens,
        "minimum_request_tokens": min(counts),
        "maximum_request_tokens": max(counts),
        "output_token_ceiling": output_ceiling,
        "estimated_cost_usd": round(_cost(input_tokens, output_ceiling), 6),
        "budget_usd": args.budget_usd,
        "dispatch_allowed": _cost(input_tokens, output_ceiling) <= args.budget_usd,
    }
    (run_dir / f"preflight_{args.stage}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if not result["dispatch_allowed"]:
        raise SystemExit("cost preflight exceeds budget")


def _checkpoint_path(run_dir: Path, stage: str) -> Path:
    return run_dir / f"predictions_{stage}.json"


def _read_predictions(path: Path) -> dict:
    if not path.exists():
        return {"predictions": [], "errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_one(
    vertex: Vertex,
    url: str,
    request: dict,
    statements: dict[str, str],
) -> dict:
    payload = generation_payload(statements[request["display_a"]], statements[request["display_b"]])
    response = vertex.request(url, payload)
    decoded = json.loads(response_text(response))
    predicted = decoded.get("harder")
    if predicted not in {"A", "B"}:
        raise ValueError(f"invalid prediction {decoded!r}")
    usage = response.get("usageMetadata", {})
    return {
        **request,
        "predicted": predicted,
        "usage": usage,
        "response_sha256": sha256_text(json.dumps(response, ensure_ascii=False, sort_keys=True)),
    }


def run(args: argparse.Namespace) -> None:
    run_dir = args.run_dir
    manifest, statements = _manifest(run_dir)
    requests = _stage_requests(manifest, args.stage)
    preflight_path = run_dir / f"preflight_{'full' if args.stage == 'full' else 'pilot'}.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("dispatch_allowed"):
        raise SystemExit("preflight forbids dispatch")
    if preflight["model"] != manifest["model"]:
        raise ValueError("preflight model mismatch")
    path = _checkpoint_path(run_dir, args.stage)
    saved = _read_predictions(path)
    done = {p["request_id"] for p in saved.get("predictions", [])}
    requests = [r for r in requests if r["request_id"] not in done]
    vertex = Vertex(args.project)
    url = generate_url(args.project, manifest["model"], args.location)
    print(f"dispatching {len(requests)} requests ({len(done)} already cached)", flush=True)
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_run_one, vertex, url, request, statements): request
            for request in requests
        }
        for future in as_completed(futures):
            request = futures[future]
            try:
                item = future.result()
            except Exception as exc:  # leave the request absent so a rerun retries it
                errors.append({"request_id": request["request_id"], "error": repr(exc)})
                print(f"ERROR {request['request_id']}: {exc}", flush=True)
                continue
            saved.setdefault("predictions", []).append(item)
            saved.update(
                {
                    "project": args.project,
                    "location": args.location,
                    "model": manifest["model"],
                    "prompt_version": manifest["prompt_version"],
                    "manifest_sha256": sha256_text((run_dir / "manifest.json").read_text()),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
            print(
                f"[{len(saved['predictions'])}/{len(_stage_requests(manifest, args.stage))}] "
                f"{request['request_id']}",
                flush=True,
            )
    if errors:
        saved["last_errors"] = errors
        path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"{len(errors)} requests failed; rerun to retry")


def merge_pilot(args: argparse.Namespace) -> None:
    run_dir = args.run_dir
    pilot = _read_predictions(_checkpoint_path(run_dir, "pilot"))
    full_path = _checkpoint_path(run_dir, "full")
    full = _read_predictions(full_path)
    by_id = {p["request_id"]: p for p in full.get("predictions", [])}
    for p in pilot.get("predictions", []):
        by_id.setdefault(p["request_id"], p)
    full["predictions"] = list(by_id.values())
    full_path.write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"merged": len(pilot.get("predictions", [])), "full_cached": len(by_id)}, indent=2))


def _prediction_rows(run_dir: Path) -> list[dict]:
    manifest, _ = _manifest(run_dir)
    by_id = {}
    for stage in ("pilot", "full"):
        path = _checkpoint_path(run_dir, stage)
        if path.exists():
            for row in _read_predictions(path).get("predictions", []):
                by_id[row["request_id"]] = row
    expected = {r["request_id"] for r in manifest["requests"]}
    missing = expected - set(by_id)
    if missing:
        raise ValueError(f"missing {len(missing)} predictions; cannot analyse")
    return [by_id[r["request_id"]] for r in manifest["requests"]]


def _winner(row: dict) -> str:
    return row["display_a"] if row["predicted"] == "A" else row["display_b"]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def bt_fit(problem_ids: list[str], rows: list[dict], kappa: float = 400.0) -> tuple[dict[str, float], dict[str, float]]:
    """Bradley--Terry MAP with the paper's small symmetric pseudo-count."""
    index = {pid: i for i, pid in enumerate(problem_ids)}
    n = len(problem_ids)
    if n < 2:
        return {problem_ids[0]: 0.0}, {problem_ids[0]: float("inf")}
    # Aggregate two directed orientations into fractional observations.  The
    # alpha count keeps complete-consistency cases finite, as in the paper.
    edges: list[tuple[int, int, float, float]] = []
    counts: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        a, b = index[row["display_a"]], index[row["display_b"]]
        if row["predicted"] == "A":
            counts[(a, b)][0] += 1
        else:
            counts[(a, b)][1] += 1
    alpha = 0.01
    for (a, b), (wins, losses) in counts.items():
        edges.append((a, b, wins + alpha, losses + alpha))

    z = np.zeros(n - 1, dtype=float)  # x[-1] = -sum(z)
    for _ in range(100):
        grad = np.zeros(n - 1)
        hess = np.zeros((n - 1, n - 1))
        for a, b, wins, losses in edges:
            v = np.zeros(n - 1)
            if a < n - 1:
                v[a] += 1.0
            else:
                v -= 1.0
            if b < n - 1:
                v[b] -= 1.0
            else:
                v += 1.0
            xdiff = float(v @ z) / kappa
            p = _sigmoid(xdiff)
            total = wins + losses
            grad += (wins - total * p) * v / kappa
            hess += total * p * (1.0 - p) * np.outer(v, v) / (kappa * kappa)
        hess += np.eye(n - 1) * 1e-8
        step = np.linalg.solve(hess, grad)
        if np.max(np.abs(step)) < 1e-5:
            break
        # Newton ascent for the concave log likelihood.
        z += step
    x = np.empty(n)
    x[:-1] = z
    x[-1] = -float(np.sum(z))
    hess += np.eye(n - 1) * 1e-8
    covariance = np.linalg.inv(hess)
    jac = np.vstack([np.eye(n - 1), -np.ones(n - 1)])
    se = np.sqrt(np.maximum(0.0, np.diag(jac @ covariance @ jac.T)))
    return dict(zip(problem_ids, x)), dict(zip(problem_ids, se))


def fuse_contest(
    problem_ids: list[str], rows: list[dict], b: dict[str, float], se: dict[str, float],
    tau: float, kappa: float,
) -> dict[str, float]:
    """MAP fusion around survival b with pairwise logistic observations."""
    n = len(problem_ids)
    index = {pid: i for i, pid in enumerate(problem_ids)}
    d = np.array([b[p] for p in problem_ids], dtype=float)
    var = np.array([se[p] * se[p] + tau * tau for p in problem_ids], dtype=float)
    edges: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        a, bb = index[row["display_a"]], index[row["display_b"]]
        if row["predicted"] == "A":
            edges[(a, bb)][0] += 1
        else:
            edges[(a, bb)][1] += 1
    for _ in range(100):
        grad = -(d - np.array([b[p] for p in problem_ids])) / var
        neg_hess = np.diag(1.0 / var)
        for (a, bb), (wins, losses) in edges.items():
            total = wins + losses
            xdiff = (d[a] - d[bb]) / kappa
            p = _sigmoid(float(xdiff))
            residual = (wins - total * p) / kappa
            h = total * p * (1.0 - p) / (kappa * kappa)
            grad[a] += residual
            grad[bb] -= residual
            neg_hess[a, a] += h
            neg_hess[bb, bb] += h
            neg_hess[a, bb] -= h
            neg_hess[bb, a] -= h
        step = np.linalg.solve(neg_hess, grad)
        step = np.clip(step, -500.0, 500.0)
        d += step
        d = np.clip(d, 800.0, 4000.0)
        if np.max(np.abs(step)) < 0.05:
            break
    return dict(zip(problem_ids, d))


def _contest_groups(manifest: dict, predictions: list[dict]) -> dict[int, dict]:
    rows_by_contest: dict[int, list[dict]] = defaultdict(list)
    for row in predictions:
        rows_by_contest[row["contest_id"]].append(row)
    problem_by_contest: dict[int, list[dict]] = defaultdict(list)
    for row in manifest["problems"]:
        problem_by_contest[row["contest_id"]].append(row)
    result = {}
    for cid, ps in problem_by_contest.items():
        result[cid] = {
            "problems": sorted(ps, key=lambda r: r["problem_label"]),
            "predictions": rows_by_contest[cid],
        }
    return result


def _rmse(values: Iterable[float]) -> float:
    values = list(values)
    return float(math.sqrt(np.mean(np.square(values)))) if values else float("nan")


def _affine_fit(train_raw: dict[str, float], train_cf: dict[str, float], shape) -> tuple[float, float]:
    x = np.asarray([shape(v) for v in train_raw.values()], dtype=float)
    y = np.asarray([train_cf[k] for k in train_raw], dtype=float)
    if len(x) < 2 or np.ptp(x) == 0:
        return 1.0, float(np.mean(y - x))
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def _apply_affine(raw: dict[str, float], shape, fit: tuple[float, float]) -> dict[str, float]:
    slope, intercept = fit
    return {k: slope * float(shape(v)) + intercept for k, v in raw.items()}


def _kendall(a: dict[str, float], b: dict[str, float]) -> float:
    keys = sorted(set(a) & set(b))
    concordant = discordant = 0
    for i, x in enumerate(keys):
        for y in keys[i + 1 :]:
            delta_a = a[x] - a[y]
            delta_b = b[x] - b[y]
            prod = delta_a * delta_b
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else float("nan")


def _schedule_rows(problem_ids: list[str], rows: list[dict], matches_per_problem: int) -> list[dict]:
    """Choose a deterministic sparse unordered-edge graph, retaining both orders."""
    rng = random.Random(SEED + matches_per_problem + len(problem_ids))
    edge_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        edge_rows[tuple(sorted((row["display_a"], row["display_b"])))].append(row)
    edges = list(edge_rows)
    rng.shuffle(edges)
    degree = defaultdict(int)
    selected: list[tuple[str, str]] = []
    remaining = set(problem_ids)
    while remaining:
        choices = [e for e in edges if e not in selected and (e[0] in remaining or e[1] in remaining)]
        if not choices:
            break
        edge = min(choices, key=lambda e: (degree[e[0]] + degree[e[1]], rng.random()))
        selected.append(edge)
        degree[edge[0]] += 1
        degree[edge[1]] += 1
        remaining.discard(edge[0])
        remaining.discard(edge[1])
    for edge in edges:
        if edge in selected:
            continue
        if degree[edge[0]] < matches_per_problem or degree[edge[1]] < matches_per_problem:
            selected.append(edge)
            degree[edge[0]] += 1
            degree[edge[1]] += 1
    selected = [e for e in selected if degree[e[0]] >= matches_per_problem and degree[e[1]] >= matches_per_problem]
    selected_set = set(selected)
    return [row for row in rows if tuple(sorted((row["display_a"], row["display_b"]))) in selected_set]


def _order_consistency(predictions: list[dict]) -> dict:
    grouped: dict[tuple[int, tuple[str, str]], list[dict]] = defaultdict(list)
    for row in predictions:
        grouped[(row["contest_id"], tuple(row["pair_key"]))].append(row)
    same = 0
    for rows in grouped.values():
        if len(rows) != 2:
            continue
        winners = {_winner(row) for row in rows}
        same += int(len(winners) == 1)
    return {"unordered_pairs": len(grouped), "consistent_pairs": same, "rate": same / len(grouped)}


def _bt_metrics(groups: dict[int, dict]) -> tuple[dict, dict[int, dict]]:
    per_contest = {}
    all_rows = []
    for cid, group in groups.items():
        ids = [p["problem_id"] for p in group["problems"]]
        scores, score_se = bt_fit(ids, group["predictions"])
        cf = {p["problem_id"]: p["cf_rating"] for p in group["problems"]}
        pairs = []
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                truth = cf[a] > cf[b]
                pred = scores[a] > scores[b]
                pairs.append(float(pred == truth))
        per_contest[cid] = {
            "problem_count": len(ids),
            "pairwise_accuracy": float(np.mean(pairs)),
            "bt_scores": scores,
            "bt_se": score_se,
        }
        all_rows.extend(pairs)
    return {"pairwise_accuracy": float(np.mean(all_rows)), "contests": len(per_contest)}, per_contest


def _tune_fusion(groups: dict[int, dict], train_ids: set[int], shape, candidates: list[tuple[float, float]]) -> tuple[float, float]:
    """Inner contest-CV selector; CF values from ``train_ids`` only."""
    train = sorted(train_ids)
    if len(train) < 3:
        return candidates[0]
    scores = []
    for tau, kappa in candidates:
        errors = []
        for inner_holdout in train:
            inner_train = [cid for cid in train if cid != inner_holdout]
            raw_train = {}
            cf_train = {}
            raw_test = {}
            cf_test = {}
            for cid in inner_train:
                g = groups[cid]
                b = {p["problem_id"]: p["survival_difficulty"] for p in g["problems"]}
                se = {p["problem_id"]: p["survival_se"] for p in g["problems"]}
                fused = fuse_contest(list(b), g["predictions"], b, se, tau, kappa)
                raw_train.update(fused)
                cf_train.update({p["problem_id"]: p["cf_rating"] for p in g["problems"]})
            fit = _affine_fit(raw_train, cf_train, shape)
            g = groups[inner_holdout]
            b = {p["problem_id"]: p["survival_difficulty"] for p in g["problems"]}
            se = {p["problem_id"]: p["survival_se"] for p in g["problems"]}
            fused = fuse_contest(list(b), g["predictions"], b, se, tau, kappa)
            pred = _apply_affine(fused, shape, fit)
            errors.extend(pred[k] - p["cf_rating"] for k, p in ((p["problem_id"], p) for p in g["problems"]))
        scores.append((_rmse(errors), tau, kappa))
    scores.sort()
    return scores[0][1], scores[0][2]


def analyse(args: argparse.Namespace) -> None:
    run_dir = args.run_dir
    manifest, _ = _manifest(run_dir)
    predictions = _prediction_rows(run_dir)
    groups = _contest_groups(manifest, predictions)
    consistency = _order_consistency(predictions)
    bt_summary, bt_contests = _bt_metrics(groups)
    # Learn the already-locked gym shape from the complete survival output,
    # not just the 185 CF anchors in this experiment.  Otherwise the join would
    # silently discard gym-only contests and change the repository metric.
    shape = _gym_shape(json.loads(
        (OUTPUT / "problem_ratings_survival.json").read_text(encoding="utf-8")
    ))
    if shape is None:
        raise RuntimeError("locked gym shape is unavailable")
    candidates = [(tau, kappa) for tau in (0.0, 25.0, 50.0, 100.0, 200.0, 400.0) for kappa in (100.0, 200.0, 400.0, 600.0, 800.0)]
    cids = sorted(groups)
    outer = []
    per_contest = {}
    for holdout in cids:
        train_ids = set(cids) - {holdout}
        tau, kappa = _tune_fusion(groups, train_ids, shape, candidates)
        raw_surv_train = {}
        cf_train = {}
        raw_fused_train = {}
        raw_surv_test = {}
        raw_fused_test = {}
        cf_test = {}
        for cid in cids:
            g = groups[cid]
            b = {p["problem_id"]: p["survival_difficulty"] for p in g["problems"]}
            se = {p["problem_id"]: p["survival_se"] for p in g["problems"]}
            fused = fuse_contest(list(b), g["predictions"], b, se, tau, kappa)
            if cid == holdout:
                raw_surv_test.update(b)
                raw_fused_test.update(fused)
                cf_test.update({p["problem_id"]: p["cf_rating"] for p in g["problems"]})
            else:
                raw_surv_train.update(b)
                raw_fused_train.update(fused)
                cf_train.update({p["problem_id"]: p["cf_rating"] for p in g["problems"]})
        surv_fit = _affine_fit(raw_surv_train, cf_train, shape)
        fused_fit = _affine_fit(raw_fused_train, cf_train, shape)
        surv_pred = _apply_affine(raw_surv_test, shape, surv_fit)
        fused_pred = _apply_affine(raw_fused_test, shape, fused_fit)
        surv_err = [surv_pred[k] - v for k, v in cf_test.items()]
        fused_err = [fused_pred[k] - v for k, v in cf_test.items()]
        per_contest[holdout] = {
            "survival_rmse": _rmse(surv_err),
            "fused_rmse": _rmse(fused_err),
            "delta_fused_minus_survival": _rmse(fused_err) - _rmse(surv_err),
            "tau": tau,
            "kappa": kappa,
            "n": len(cf_test),
        }
        outer.extend((a, b) for a, b in zip(surv_err, fused_err))
    surv_all = [a for a, _ in outer]
    fused_all = [b for _, b in outer]
    contest_deltas = [per_contest[c]["fused_rmse"] ** 2 - per_contest[c]["survival_rmse"] ** 2 for c in cids]
    rng = np.random.default_rng(SEED)
    bootstrap = []
    for _ in range(10000):
        sample = rng.choice(contest_deltas, size=len(contest_deltas), replace=True)
        bootstrap.append(float(np.mean(sample)))
    bootstrap_prob_worse = float(np.mean(np.asarray(bootstrap) > 0))

    sparse = {}
    for k in (4, 6, 8, 10):
        taus = []
        for cid, g in groups.items():
            ids = [p["problem_id"] for p in g["problems"]]
            full, _ = bt_fit(ids, g["predictions"])
            sampled = _schedule_rows(ids, g["predictions"], k)
            sparse_scores, _ = bt_fit(ids, sampled)
            taus.append(_kendall(full, sparse_scores))
        sparse[str(k)] = {"mean_kendall": float(np.nanmean(taus)), "minimum_kendall": float(np.nanmin(taus))}
    selected_sparse = next(
        (
            int(k)
            for k, value in sorted(sparse.items(), key=lambda item: int(item[0]))
            if value["mean_kendall"] >= 0.90 and value["minimum_kendall"] >= 0.90
        ),
        None,
    )

    # Bill only successful generation requests; the pilot checkpoint is merged
    # into full by request id, so no call is counted twice.
    usage = defaultdict(int)
    for row in predictions:
        for key, value in row.get("usage", {}).items():
            if isinstance(value, int):
                usage[key] += value
    input_tokens = usage["promptTokenCount"]
    output_tokens = usage["candidatesTokenCount"] + usage["thoughtsTokenCount"]
    actual_cost = _cost(input_tokens, output_tokens)
    preflights = {}
    for stage in ("pilot", "full"):
        path = run_dir / f"preflight_{stage}.json"
        if path.exists():
            preflights[stage] = json.loads(path.read_text())
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": manifest["model"],
        "prompt_version": manifest["prompt_version"],
        "request_count": len(predictions),
        "problem_count": len(manifest["problems"]),
        "contest_count": len(groups),
        "order_consistency": consistency,
        "bt": {**bt_summary, "per_contest": bt_contests},
        "sparse_schedule": sparse,
        "selected_sparse_matches_per_problem": selected_sparse,
        "nested_loco": {
            "survival_rmse": _rmse(surv_all),
            "fused_rmse": _rmse(fused_all),
            "improvement_points": _rmse(surv_all) - _rmse(fused_all),
            "bootstrap_probability_fused_worse": bootstrap_prob_worse,
            "per_contest": per_contest,
        },
        "usage": dict(usage),
        "estimated_actual_cost_usd": round(actual_cost, 6),
        "budget_usd": args.budget_usd,
        "preflights": preflights,
        "gates": {
            "loco_improvement_ge_5": _rmse(surv_all) - _rmse(fused_all) >= 5.0,
            "bootstrap_worse_lt_10pct": bootstrap_prob_worse < 0.10,
            "order_consistency_ge_80pct": consistency["rate"] >= 0.80,
            "sparse_kendall_ge_090": selected_sparse is not None,
            "under_budget": actual_cost <= args.budget_usd,
        },
    }
    (run_dir / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Gemini zero-shot × survival experiment",
        "",
        f"Model: `{manifest['model']}`; requests: {len(predictions)}; problems: {len(manifest['problems'])}; contests: {len(groups)}.",
        f"Actual estimated inference cost: **${actual_cost:.4f}** (budget ${args.budget_usd:.2f}).",
        "",
        f"A/B order consistency: {consistency['rate']:.3f} ({consistency['consistent_pairs']}/{consistency['unordered_pairs']}).",
        f"BT pairwise accuracy vs official CF ratings: {bt_summary['pairwise_accuracy']:.3f}.",
        f"Nested LOCO survival RMSE: {result['nested_loco']['survival_rmse']:.2f}; fused RMSE: {result['nested_loco']['fused_rmse']:.2f}; improvement: {result['nested_loco']['improvement_points']:.2f} CF points.",
        f"Contest bootstrap probability fusion is worse: {bootstrap_prob_worse:.3f}.",
        "",
        "## Sparse BT stability",
        "",
    ]
    if selected_sparse is not None:
        report += [
            f"Selected robust sparse schedule: **{selected_sparse} unordered matches/problem** "
            "(mean and minimum Kendall both at least 0.90).",
            "",
        ]
    else:
        report += [
            "Selected robust sparse schedule: **none** (no target met both Kendall thresholds).",
            "",
        ]
    report += [
        "| unordered matches/problem target | mean Kendall | minimum Kendall |",
        "|---:|---:|---:|",
    ]
    for k, value in sparse.items():
        report.append(f"| {k} | {value['mean_kendall']:.3f} | {value['minimum_kendall']:.3f} |")
    report += ["", "## Gate result", ""]
    for key, value in result["gates"].items():
        report.append(f"- `{key}`: {'PASS' if value else 'FAIL'}")
    (run_dir / "analysis.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def pilot_check(args: argparse.Namespace) -> None:
    run_dir = args.run_dir
    manifest, _ = _manifest(run_dir)
    path = _checkpoint_path(run_dir, "pilot")
    rows = _read_predictions(path).get("predictions", [])
    expected = _stage_requests(manifest, "pilot")
    if len(rows) != len(expected):
        raise ValueError(f"pilot incomplete: {len(rows)}/{len(expected)}")
    consistency = _order_consistency(rows)
    if consistency["rate"] < args.minimum_order_consistency:
        raise SystemExit(f"pilot order consistency {consistency['rate']:.3f} below gate")
    print(json.dumps({"requests": len(rows), "order_consistency": consistency, "passed": True}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, default=DEFAULT_RUN_DIR)
    c = sub.add_parser("count")
    c.add_argument("--project", required=True)
    c.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    c.add_argument("--stage", choices=("pilot", "full"), default="full")
    c.add_argument("--location", default=LOCATION)
    c.add_argument("--workers", type=int, default=8)
    c.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    r = sub.add_parser("run")
    r.add_argument("--project", required=True)
    r.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    r.add_argument("--stage", choices=("pilot", "full"), default="pilot")
    r.add_argument("--location", default=LOCATION)
    r.add_argument("--workers", type=int, default=8)
    m = sub.add_parser("merge-pilot")
    m.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    pc = sub.add_parser("pilot-check")
    pc.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    pc.add_argument("--minimum-order-consistency", type=float, default=0.80)
    a = sub.add_parser("analyse")
    a.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    a.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    elif args.command == "count":
        count(args)
    elif args.command == "run":
        run(args)
    elif args.command == "merge-pilot":
        merge_pilot(args)
    elif args.command == "pilot-check":
        pilot_check(args)
    else:
        analyse(args)


if __name__ == "__main__":
    main()
