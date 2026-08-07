import unittest

from llm_survival import bt_fit, fuse_contest, sanitize_statement, statement_leaks


class LlmSurvivalLocalTest(unittest.TestCase):
    def test_statement_sanitizer_removes_contest_furniture(self):
        problem = {
            "problem_id": 12345,
            "problem_name": "Hidden Title",
            "contest_name": "The 2025 ICPC Europe Championship",
            "editorial": "This editorial reveals the intended dynamic program.",
            "statement": (
                "Problem A. Hidden Title\nTime limit: 2 seconds\n"
                "The 2025 ICPC Europe Championship\nPage 1 of 2\n"
                "International Collegiate Programming Contest\n"
                "Given an array, compute its sum."
            ),
        }
        text = sanitize_statement(problem)
        self.assertEqual(statement_leaks(problem, text), [])
        self.assertIn("Given an array", text)
        self.assertNotIn("Hidden Title", text)
        self.assertNotIn("ICPC", text)
        self.assertNotIn("Time limit", text)
        self.assertNotIn("dynamic program", text)

    def test_bt_and_fusion_follow_consistent_comparisons(self):
        rows = [
            {"display_a": "hard", "display_b": "easy", "predicted": "A"},
            {"display_a": "easy", "display_b": "hard", "predicted": "B"},
        ]
        scores, errors = bt_fit(["easy", "hard"], rows)
        self.assertGreater(scores["hard"], scores["easy"])
        self.assertTrue(all(value >= 0 for value in errors.values()))
        fused = fuse_contest(
            ["easy", "hard"], rows,
            {"easy": 1800.0, "hard": 2200.0},
            {"easy": 20.0, "hard": 20.0},
            tau=50.0,
            kappa=400.0,
        )
        self.assertGreater(fused["hard"], fused["easy"])


if __name__ == "__main__":
    unittest.main()
