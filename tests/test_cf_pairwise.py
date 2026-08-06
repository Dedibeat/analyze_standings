import unittest
from datetime import datetime, timezone

from cf_pairwise import (
    accuracy,
    editorial_text,
    has_substantive_editorial,
    newest_substantive_train,
    partition_problems,
    problem_text,
    sample_pairs,
    sample_covering_pairs,
    split_by_contest,
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

    def test_enriched_text_uses_only_first_reference_solution(self):
        row = problem("1A", 800, (2024, 1, 1))
        row["editorial"] = {
            "tutorial": "Use   dynamic programming.",
            "solution_code": ["int main() {\n}\n", "ignored"],
        }
        self.assertEqual(editorial_text(row), "[Editorial]\nUse dynamic programming.")
        enriched = problem_text(row, "editorial_code")
        self.assertIn("[Statement]", enriched)
        self.assertIn("[Reference solution]\nint main() {\n}", enriched)
        self.assertNotIn("ignored", enriched)

    def test_enriched_text_requires_editorial(self):
        with self.assertRaisesRegex(ValueError, "missing editorial for 1A"):
            problem_text(problem("1A", 800, (2024, 1, 1)), "editorial")

    def test_substantive_editorial_rejects_title_only_and_video(self):
        row = problem("1A", 800, (2024, 1, 1))
        row["editorial"] = {"tutorial": "A. Problem — Video editorial"}
        self.assertFalse(has_substantive_editorial(row))
        row["editorial"] = {"tutorial": "x" * 200}
        self.assertTrue(has_substantive_editorial(row))

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

    def test_covering_pair_sample_uses_every_problem(self):
        rows = [problem(f"{i}A", 800 + i * 100, (2024, 1, 1)) for i in range(12)]
        pairs = sample_covering_pairs(
            rows, 10, {"200": 0.30, "300": 0.30, "400+": 0.40}, 11
        )
        used = {pid for pair in pairs for pid in (pair["a"], pair["b"])}
        self.assertEqual(used, {p["problem_id"] for p in rows})

    def test_contest_split_has_no_contest_overlap(self):
        rows = []
        for contest in range(1, 7):
            rows.extend(
                problem(f"{contest}{index}", 800 + contest * 100, (2025, 2, 1))
                for index in ("A", "B")
            )
        left, right = split_by_contest(rows, 13)
        self.assertFalse(
            {p["contest_id"] for p in left} & {p["contest_id"] for p in right}
        )
        self.assertEqual(len(left) + len(right), len(rows))

    def test_newest_substantive_train_skips_missing_editorials(self):
        rows = [problem(f"{i}A", 800 + i, (2024, 1, 1)) for i in range(1, 4)]
        rows[0]["editorial"] = {"tutorial": "x" * 200}
        rows[1]["editorial"] = {"tutorial": "x" * 200}
        with self.assertRaisesRegex(ValueError, "need 3"):
            newest_substantive_train(rows, 3)
        self.assertEqual(len(newest_substantive_train(rows, 2)), 2)

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
