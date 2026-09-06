import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arch_a.load import _UnionFind
from arch_b.cf_prior import team_abilities


class CfPriorTest(unittest.TestCase):
    def test_roster_completeness_requires_evidence_for_the_same_row(self):
        appearance = {
            "contest_id": 7,
            "team_id": "team-7",
            "year": 2025,
            "roster": ["Alice", "Bob"],
            "identity_evidence": {"status": "roster_corroborated"},
        }
        history = [{"newRating": 2000, "ratingUpdateTimeSeconds": 1}]
        artifact = {"participants": [
            {"normalized_name": "alice", "cf_handle": "alice_cf",
             "rating_history": history, "tagged_appearances": [appearance]},
            {"normalized_name": "bob", "cf_handle": "bob_cf",
             "rating_history": history, "tagged_appearances": []},
        ]}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "participants.json"
            path.write_text(json.dumps(artifact))
            with patch("arch_b.cf_prior.CPHOF", str(path)):
                abilities = team_abilities(_UnionFind())

        self.assertEqual(abilities, {})


if __name__ == "__main__":
    unittest.main()
