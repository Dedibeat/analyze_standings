import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import qoj_clearance


class QOJClearanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(TemporaryDirectory())
        self.path = Path(self.directory) / ".qoj-clearance.json"

    def saved(self, **cookies):
        return {"user_agent": "UA", "cookies": cookies, "harvested_at": 1}

    def test_save_then_load_roundtrips_and_is_owner_only(self):
        clearance = self.saved(cf_clearance="cleared")
        qoj_clearance.save(clearance, self.path)
        self.assertEqual(qoj_clearance.load(self.path), clearance)
        if os.name == "posix":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_load_returns_none_without_a_file(self):
        self.assertIsNone(qoj_clearance.load(self.path))

    def test_load_rejects_a_record_without_cf_clearance(self):
        self.path.write_text(json.dumps({"user_agent": "UA", "cookies": {"other": "x"}}))
        self.assertIsNone(qoj_clearance.load(self.path))

    def test_load_rejects_corrupt_json(self):
        self.path.write_text("{not json")
        self.assertIsNone(qoj_clearance.load(self.path))

    def test_chrome_override_must_exist(self):
        with patch.dict(os.environ, {"QOJ_CHROME": "/nonexistent/chrome"}):
            with self.assertRaisesRegex(qoj_clearance.ClearanceError, "does not exist"):
                qoj_clearance.chrome_binary()

    def test_chrome_override_is_honoured(self):
        with patch.dict(os.environ, {"QOJ_CHROME": "/bin/sh"}):
            self.assertEqual(qoj_clearance.chrome_binary(), "/bin/sh")

    def test_harvest_refuses_without_a_display(self):
        environment = {k: v for k, v in os.environ.items() if k != "DISPLAY"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(qoj_clearance.ClearanceError, "DISPLAY"):
                qoj_clearance.harvest()


if __name__ == "__main__":
    unittest.main()
