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

PROBLEM_ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{3,5}[A-Z]\d{0,2}(?![A-Za-z0-9])")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EDITORIAL_HEADER_RE = re.compile(
    r"^\s*(?:problem\s+)?(?:\d{3,5}[A-Z]\d{0,2}|[A-Z]\d{0,2})\s*[-:–—]",
    re.IGNORECASE,
)
EDITORIAL_METADATA_LINE_RE = re.compile(
    r"^\s*(?:problem\s+)?(?:credits?|author|analysis|idea|prepared|"
    r"written\s+by|solution\s+by|editorial(?:ist)?)\b.*$",
    re.IGNORECASE,
)

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


def sanitize_editorial(problem: dict, value: str, preserve_layout: bool = False) -> str:
    """Remove source metadata from tutorial prose while keeping its method."""
    title = canonical_text(str(problem.get("name") or ""))
    lines = []
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("rate the problem"):
            break
        metadata_line = line.strip("()[] ")
        title_header = len(title) >= 3 and title.casefold() in line.casefold()
        if (
            EDITORIAL_HEADER_RE.match(line)
            or EDITORIAL_METADATA_LINE_RE.match(metadata_line)
            or (title_header and re.match(r"^\s*[A-Z]\d{0,2}\s*[.:–—-]", line))
        ):
            continue
        line = URL_RE.sub("", line)
        line = PROBLEM_ID_RE.sub("", line)
        if len(title) >= 3:
            line = re.sub(re.escape(title), "", line, flags=re.IGNORECASE)
        line = line.strip()
        if not line or re.fullmatch(r"[-:–—|]+", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip() if preserve_layout else canonical_text(" ".join(lines))


def editorial_metadata_leaks(problem: dict, text: str) -> list[str]:
    """Return metadata tokens that must not reach an editorial prompt."""
    leaks = []
    if PROBLEM_ID_RE.search(text):
        leaks.append("problem_id")
    if URL_RE.search(text):
        leaks.append("url")
    title = canonical_text(str(problem.get("name") or ""))
    if len(title) >= 3 and title.casefold() in text.casefold():
        leaks.append("title")
    return leaks


def editorial_text(problem: dict, include_code: bool = False) -> str:
    """Return metadata-sanitized editorial input, optionally with one solution."""
    editorial = problem.get("editorial") or {}
    tutorial = sanitize_editorial(problem, str(editorial.get("tutorial") or ""))
    if not tutorial:
        return ""
    sections = [f"[Editorial]\n{tutorial}"]
    if include_code:
        solutions = editorial.get("solution_code") or []
        code = (
            sanitize_editorial(problem, str(solutions[0]), preserve_layout=True)
            if solutions
            else ""
        )
        if code:
            sections.append(f"[Reference solution]\n{code}")
    result = "\n\n".join(sections)
    leaks = editorial_metadata_leaks(problem, result)
    if leaks:
        raise ValueError(
            f"editorial metadata leak for {problem.get('problem_id', '<unknown>')}: "
            + ", ".join(leaks)
        )
    return result


def has_substantive_editorial(problem: dict) -> bool:
    """Reject title-only and video-only tutorial captures."""
    tutorial = sanitize_editorial(
        problem, str(((problem.get("editorial") or {}).get("tutorial") or ""))
    )
    return len(tutorial) >= 200 and "video editorial" not in tutorial.lower()


def problem_text(problem: dict, input_mode: str = "statement") -> str:
    text = statement_text(problem)
    if input_mode == "statement":
        return text
    if input_mode not in {"editorial", "editorial_code"}:
        raise ValueError(f"unknown input mode: {input_mode}")
    extra = editorial_text(problem, include_code=input_mode == "editorial_code")
    if not extra:
        raise ValueError(f"missing editorial for {problem.get('problem_id', '<unknown>')}")
    return f"[Statement]\n{text}\n\n{extra}"


def content_hash(problem: dict, input_mode: str) -> str:
    return sha256_bytes(canonical_text(problem_text(problem, input_mode)).encode("utf-8"))


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


def newest_substantive_train(
    problems: Iterable[dict], count: int | None = TRAIN_COUNT
) -> list[dict]:
    """Select the newest exact-statement-unique pre-cutoff tutorial records."""
    unique: dict[str, dict] = {}
    for problem in sorted(
        problems,
        key=lambda p: (parse_start(p), p["contest_id"], p["index"]),
        reverse=True,
    ):
        if problem.get("rating") is not None and statement_text(problem):
            unique.setdefault(statement_hash(problem), problem)
    train = [
        problem
        for problem in unique.values()
        if parse_start(problem) < POST_CUTOFF and has_substantive_editorial(problem)
    ]
    train.sort(key=lambda p: (parse_start(p), p["contest_id"], p["index"]), reverse=True)
    if count is None:
        return train
    if len(train) < count:
        raise ValueError(f"need {count} substantive-editorial pre-cutoff problems, found {len(train)}")
    return train[:count]


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


def user_text(a: dict, b: dict, input_mode: str = "statement") -> str:
    return f"Problem A:\n{problem_text(a, input_mode)}\n\nProblem B:\n{problem_text(b, input_mode)}"


def truth(a: dict, b: dict) -> str:
    if a["rating"] == b["rating"]:
        raise ValueError("equal-rated pair has no binary truth")
    return "A" if a["rating"] > b["rating"] else "B"


def tuning_example(
    pair: dict, by_id: dict[str, dict], input_mode: str = "statement"
) -> dict:
    a, b = by_id[pair["a"]], by_id[pair["b"]]
    target = json.dumps({"harder": truth(a, b)}, separators=(",", ":"))
    return {
        "systemInstruction": {"role": "system", "parts": [{"text": SYSTEM}]},
        "contents": [
            {"role": "user", "parts": [{"text": user_text(a, b, input_mode)}]},
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


def sample_covering_pairs(
    problems: list[dict], total: int, proportions: dict[str, float], seed: int
) -> list[dict]:
    """Sample quota-balanced pairs while using every problem at least once."""
    if total * 2 < len(problems):
        raise ValueError(f"{total} pairs cannot cover {len(problems)} problems")
    rng = random.Random(seed)
    by_id = {p["problem_id"]: p for p in problems}
    buckets = candidate_pairs(problems)
    names = list(proportions)
    quota = {}
    allocated = 0
    for i, name in enumerate(names):
        count = total - allocated if i == len(names) - 1 else round(total * proportions[name])
        quota[name] = count
        allocated += count

    candidates = []
    for bucket, edges in buckets.items():
        shuffled = edges[:]
        rng.shuffle(shuffled)
        candidates.extend((a, b, bucket) for a, b in shuffled)
    rng.shuffle(candidates)
    selected: list[tuple[str, str]] = []
    selected_keys: set[tuple[str, str]] = set()
    bucket_used = Counter()
    degree = Counter()
    uncovered = set(by_id)
    while uncovered:
        choices = [
            row
            for row in candidates
            if quota.get(row[2], 0) > bucket_used[row[2]]
            and tuple(sorted(row[:2])) not in selected_keys
            and (row[0] in uncovered or row[1] in uncovered)
        ]
        if not choices:
            raise ValueError(f"unable to cover {len(uncovered)} problems within pair quotas")
        best_score = max((a in uncovered) + (b in uncovered) for a, b, _ in choices)
        a, b, bucket = next(
            row for row in choices if (row[0] in uncovered) + (row[1] in uncovered) == best_score
        )
        selected.append((a, b))
        selected_keys.add(tuple(sorted((a, b))))
        bucket_used[bucket] += 1
        degree[a] += 1
        degree[b] += 1
        uncovered.discard(a)
        uncovered.discard(b)

    for bucket in names:
        need = quota[bucket] - bucket_used[bucket]
        for _ in range(need):
            choices = [
                (a, b)
                for a, b in buckets.get(bucket, [])
                if tuple(sorted((a, b))) not in selected_keys
            ]
            if not choices:
                raise ValueError(f"not enough unused {bucket} pairs: need {need}")
            a, b = min(
                choices,
                key=lambda edge: (
                    degree[edge[0]] + degree[edge[1]],
                    max(degree[edge[0]], degree[edge[1]]),
                ),
            )
            selected.append((a, b))
            selected_keys.add(tuple(sorted((a, b))))
            bucket_used[bucket] += 1
            degree[a] += 1
            degree[b] += 1
    return _orient(selected, by_id, rng)


def split_by_contest(problems: list[dict], seed: int) -> tuple[list[dict], list[dict]]:
    """Deterministically balance whole contests across tuning and development."""
    by_contest: dict[int, list[dict]] = defaultdict(list)
    for problem in problems:
        by_contest[problem["contest_id"]].append(problem)
    contests = list(by_contest)
    random.Random(seed).shuffle(contests)
    left: list[dict] = []
    right: list[dict] = []
    for contest in contests:
        target = left if len(left) <= len(right) else right
        target.extend(by_contest[contest])
    return left, right


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
