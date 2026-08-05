"""Dataset and metric primitives for Codeforces pairwise-difficulty tuning."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import random
import re
from typing import Iterable


UTC = timezone.utc
SEED = 20260805
TRAIN_COUNT = 600
PILOT_PROBLEM_COUNT = 200
PILOT_PAIR_COUNT = 400
TUNING_VALIDATION_PAIR_COUNT = 150

# Google's public cutoff is month-granular (January 2025), so February 1 is
# the first unambiguously post-cutoff instant.
POST_CUTOFF = datetime(2025, 2, 1, tzinfo=UTC)
FINAL_TEST_START = datetime(2025, 4, 1, tzinfo=UTC)
FINAL_TEST_END = datetime(2025, 5, 22, tzinfo=UTC)

SYSTEM = (
    "Compare the inherent competitive-programming difficulty of the two problem "
    "statements. Judge the algorithmic insight, proof burden, and implementation "
    "difficulty. Do not use problem order, title, contest position, popularity, "
    "or external knowledge. Return only the requested JSON."
)
SCHEMA = {
    "type": "OBJECT",
    "properties": {"harder": {"type": "STRING", "enum": ["A", "B"]}},
    "required": ["harder"],
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def statement_text(problem: dict) -> str:
    statement = problem.get("statement") or {}
    sections = []
    for label, key in (
        ("Problem", "legend"),
        ("Input", "input_spec"),
        ("Output", "output_spec"),
        ("Note", "note"),
    ):
        value = canonical_text(str(statement.get(key) or ""))
        if value:
            sections.append(f"[{label}]\n{value}")
    samples = statement.get("samples") or []
    if samples:
        sample_text = []
        for i, sample in enumerate(samples, 1):
            sample_text.append(
                f"Sample {i} input:\n{sample.get('input', '')}\n"
                f"Sample {i} output:\n{sample.get('output', '')}"
            )
        sections.append("[Samples]\n" + "\n\n".join(sample_text))
    return "\n\n".join(sections)


def statement_hash(problem: dict) -> str:
    return sha256_bytes(canonical_text(statement_text(problem)).encode("utf-8"))


def parse_start(problem: dict) -> datetime:
    return datetime.fromisoformat(problem["contest_start_time"].replace("Z", "+00:00"))


def partition_problems(problems: Iterable[dict]) -> dict[str, list[dict]]:
    """Chronological, exact-statement-deduplicated frozen partitions."""
    unique: dict[str, dict] = {}
    for problem in sorted(
        problems,
        key=lambda p: (parse_start(p), p["contest_id"], p["index"]),
        reverse=True,
    ):
        text = statement_text(problem)
        if problem.get("rating") is None or not text:
            continue
        unique.setdefault(statement_hash(problem), problem)

    train_candidates = [p for p in unique.values() if parse_start(p) < POST_CUTOFF]
    train_candidates.sort(
        key=lambda p: (parse_start(p), p["contest_id"], p["index"]), reverse=True
    )
    if len(train_candidates) < TRAIN_COUNT:
        raise ValueError(
            f"need {TRAIN_COUNT} usable pre-cutoff problems, found {len(train_candidates)}"
        )
    train = train_candidates[:TRAIN_COUNT]
    validation = sorted(
        (
            p
            for p in unique.values()
            if POST_CUTOFF <= parse_start(p) < FINAL_TEST_START
        ),
        key=lambda p: (parse_start(p), p["contest_id"], p["index"]),
    )
    test = sorted(
        (
            p
            for p in unique.values()
            if FINAL_TEST_START <= parse_start(p) < FINAL_TEST_END
        ),
        key=lambda p: (parse_start(p), p["contest_id"], p["index"]),
    )
    if not validation or not test:
        raise ValueError("post-cutoff validation/test partition is empty")
    ids = {
        part: {p["problem_id"] for p in rows}
        for part, rows in {"train": train, "validation": validation, "test": test}.items()
    }
    if ids["train"] & ids["validation"] or ids["train"] & ids["test"] or ids["validation"] & ids["test"]:
        raise ValueError("problem overlap between partitions")
    return {"train": train, "validation": validation, "test": test}


def problem_public(problem: dict) -> dict:
    return {
        "problem_id": problem["problem_id"],
        "contest_id": problem["contest_id"],
        "index": problem["index"],
        "name": problem["name"],
        "rating": problem["rating"],
        "contest_start_time": problem["contest_start_time"],
        "url": problem["url"],
        "statement_sha256": statement_hash(problem),
    }


def user_text(a: dict, b: dict) -> str:
    return f"Problem A:\n{statement_text(a)}\n\nProblem B:\n{statement_text(b)}"


def truth(a: dict, b: dict) -> str:
    if a["rating"] == b["rating"]:
        raise ValueError("equal-rated pair has no binary truth")
    return "A" if a["rating"] > b["rating"] else "B"


def tuning_example(pair: dict, by_id: dict[str, dict]) -> dict:
    a, b = by_id[pair["a"]], by_id[pair["b"]]
    target = json.dumps({"harder": truth(a, b)}, separators=(",", ":"))
    return {
        "systemInstruction": {"role": "system", "parts": [{"text": SYSTEM}]},
        "contents": [
            {"role": "user", "parts": [{"text": user_text(a, b)}]},
            {"role": "model", "parts": [{"text": target}]},
        ],
    }


def _gap_bucket(gap: int) -> str | None:
    if gap == 200:
        return "200"
    if gap == 300:
        return "300"
    if gap >= 400:
        return "400+"
    return None


def candidate_pairs(problems: list[dict]) -> dict[str, list[tuple[str, str]]]:
    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for i, a in enumerate(problems):
        for b in problems[i + 1 :]:
            bucket = _gap_bucket(abs(a["rating"] - b["rating"]))
            if bucket:
                buckets[bucket].append((a["problem_id"], b["problem_id"]))
    return buckets


def _orient(
    pairs: list[tuple[str, str]], by_id: dict[str, dict], rng: random.Random
) -> list[dict]:
    rng.shuffle(pairs)
    result = []
    target_a_wins = len(pairs) // 2
    a_wins = 0
    for x, y in pairs:
        x_harder = by_id[x]["rating"] > by_id[y]["rating"]
        want_a_win = a_wins < target_a_wins
        if x_harder != want_a_win:
            x, y = y, x
        if by_id[x]["rating"] > by_id[y]["rating"]:
            a_wins += 1
        result.append({
            "a": x,
            "b": y,
            "gap": abs(by_id[x]["rating"] - by_id[y]["rating"]),
            "truth": truth(by_id[x], by_id[y]),
        })
    rng.shuffle(result)
    return result


def sample_pairs(
    problems: list[dict], total: int, proportions: dict[str, float], seed: int
) -> list[dict]:
    rng = random.Random(seed)
    by_id = {p["problem_id"]: p for p in problems}
    buckets = candidate_pairs(problems)
    selected: list[tuple[str, str]] = []
    allocated = 0
    names = list(proportions)
    for i, name in enumerate(names):
        count = total - allocated if i == len(names) - 1 else round(total * proportions[name])
        allocated += count
        choices = buckets.get(name, [])[:]
        if len(choices) < count:
            raise ValueError(f"not enough {name} pairs: need {count}, found {len(choices)}")
        rng.shuffle(choices)
        selected.extend(choices[:count])
    return _orient(selected, by_id, rng)


def choose_pilot_problems(train: list[dict], count: int = PILOT_PROBLEM_COUNT) -> list[dict]:
    """Choose a deterministic rating-stratified subset for the pilot."""
    by_rating: dict[int, list[dict]] = defaultdict(list)
    for problem in train:
        by_rating[problem["rating"]].append(problem)
    ratings = sorted(by_rating)
    rng = random.Random(SEED)
    for rows in by_rating.values():
        rng.shuffle(rows)
    selected = []
    cursor = 0
    while len(selected) < count:
        rating = ratings[cursor % len(ratings)]
        rows = by_rating[rating]
        if rows:
            selected.append(rows.pop())
        cursor += 1
        if cursor > count * len(ratings) * 2:
            raise ValueError("unable to choose enough pilot problems")
    return selected


def swapped_pairs(pairs: list[dict]) -> list[dict]:
    result = []
    for pair in pairs:
        result.append(pair)
        result.append({
            **pair,
            "a": pair["b"],
            "b": pair["a"],
            "truth": "B" if pair["truth"] == "A" else "A",
        })
    return result


def accuracy(predictions: list[dict]) -> dict:
    valid = [p for p in predictions if p.get("predicted") in {"A", "B"}]
    result = {
        "count": len(predictions),
        "valid_count": len(valid),
        "accuracy": sum(p["predicted"] == p["truth"] for p in valid) / len(predictions)
        if predictions
        else 0.0,
    }
    for label, predicate in (
        ("exact_200", lambda gap: gap == 200),
        ("exact_300", lambda gap: gap == 300),
        ("at_least_300", lambda gap: gap >= 300),
        ("at_least_400", lambda gap: gap >= 400),
    ):
        rows = [p for p in predictions if predicate(p["gap"])]
        result[label] = {
            "count": len(rows),
            "accuracy": sum(p.get("predicted") == p["truth"] for p in rows) / len(rows)
            if rows
            else None,
        }
    paired: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in predictions:
        paired[tuple(sorted((row["a"], row["b"])))].append(row)
    complete = [rows for rows in paired.values() if len(rows) == 2]
    result["swapped_consistency"] = (
        sum(rows[0].get("predicted") != rows[1].get("predicted") for rows in complete)
        / len(complete)
        if complete
        else None
    )
    result["gap_counts"] = dict(Counter(p["gap"] for p in predictions))
    return result
