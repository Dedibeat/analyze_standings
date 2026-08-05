import unittest
from datetime import datetime, timezone

from cf_pairwise import (
    accuracy,
    partition_problems,
    sample_pairs,
    statement_hash,
    statement_text,
    swapped_pairs,
)


UTC = timezone.utc


def problem(pid, rating, when, text=None):
    contest = int("".join(c for c in pid if c.isdigit()))
    index = pid[len(str(contest)) :]
    return {
        "problem_id": pid,
        "contest_id": contest,
        "index": index,
        "name": pid,
        "rating": rating,
        "contest_start_time": datetime(*when, tzinfo=UTC).isoformat(),
        "url": f"https://example.test/{pid}",
        "statement": {
            "legend": text or f"Statement {pid}",
            "input_spec": "Input",
            "output_spec": "Output",
            "note": None,
            "samples": [{"input": "1", "output": "2"}],
        },
    }


class PairwiseDatasetTest(unittest.TestCase):
    def test_statement_normalization_is_stable(self):
        a = problem("1A", 800, (2024, 1, 1), "x   y")
        b = problem("2A", 800, (2024, 1, 1), "x y")
        self.assertEqual(statement_text(a), statement_text(b))
        self.assertEqual(statement_hash(a), statement_hash(b))

    def test_partition_is_chronological_and_deduplicates(self):
        train = [problem(f"{i}A", 800 + i % 10 * 100, (2024, 1, 1)) for i in range(1, 602)]
        duplicate = problem("999A", 1200, (2024, 2, 1), text="Statement 1A")
        duplicate["statement"] = train[0]["statement"]
        validation = problem("1000A", 1800, (2025, 2, 2))
        test = problem("1001A", 2100, (2025, 4, 2))
        parts = partition_problems([*train, duplicate, validation, test])
        self.assertEqual(len(parts["train"]), 600)
        self.assertEqual([p["problem_id"] for p in parts["validation"]], ["1000A"])
        self.assertEqual([p["problem_id"] for p in parts["test"]], ["1001A"])

    def test_pair_sample_has_requested_gaps_and_balanced_orientation(self):
        rows = [problem(f"{i}A", 800 + i * 100, (2024, 1, 1)) for i in range(12)]
        pairs = sample_pairs(rows, 20, {"200": 0.25, "300": 0.35, "400+": 0.40}, 7)
        self.assertEqual(len(pairs), 20)
        self.assertLessEqual(abs(sum(p["truth"] == "A" for p in pairs) - 10), 1)
        self.assertTrue(all(p["gap"] >= 200 for p in pairs))

    def test_swapped_consistency(self):
        pair = {"a": "1A", "b": "2A", "gap": 300, "truth": "B"}
        rows = swapped_pairs([pair])
        predictions = [
            {**rows[0], "predicted": "B"},
            {**rows[1], "predicted": "A"},
        ]
        result = accuracy(predictions)
        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["swapped_consistency"], 1.0)


if __name__ == "__main__":
    unittest.main()
