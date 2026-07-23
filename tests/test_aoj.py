import unittest

from arch_b.aoj import build_artifact, within_contest_spearman


class AojArtifactTest(unittest.TestCase):
    def test_requires_contest_corroboration(self):
        aoj = [
            {"id": str(i), "name": name, "solvedUser": 10, "submissions": 10 * i}
            for i, name in enumerate(("Alpha", "Beta", "Gamma", "Lonely"), start=1)
        ]
        contests = [
            {
                "contest_id": 1, "contest_name": "Safe", "year": 2025,
                "region": "Test", "problems": [
                    {"problem_label": "A", "problem_name": "Alpha"},
                    {"problem_label": "B", "problem_name": "Beta"},
                    {"problem_label": "C", "problem_name": "Gamma"},
                ],
            },
            {
                "contest_id": 2, "contest_name": "Unsafe", "year": 2025,
                "region": "Test", "problems": [
                    {"problem_label": "A", "problem_name": "Lonely"},
                ],
            },
        ]
        artifact = build_artifact(aoj, contests, "2026-01-01T00:00:00+00:00")

        self.assertEqual(artifact["matching"]["candidate_count"], 4)
        self.assertEqual(len(artifact["matches"]), 3)
        self.assertEqual({row["contest_id"] for row in artifact["matches"]}, {1})
        self.assertEqual(len(artifact["rejected_candidates"]), 1)
        self.assertEqual(
            artifact["rejected_candidates"][0]["match_confidence"],
            "title_only_candidate")
        self.assertIn("fewer_than_3", artifact["rejected_candidates"][0]["rejection_reason"])

    def test_within_contest_ranks_ignore_cross_contest_scale(self):
        pairs = [
            (1, 100, 1000),
            (1, 200, 2000),
            (2, 1000, 10),
            (2, 2000, 20),
        ]
        self.assertAlmostEqual(within_contest_spearman(pairs), 1.0)


if __name__ == "__main__":
    unittest.main()
