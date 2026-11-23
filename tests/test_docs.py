"""Docs stay navigable: relative links resolve and the journal index is complete."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)")


def tracked_markdown():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / p for p in out.stdout.split() if not p.startswith(("data/", "output/"))]


class DocsTest(unittest.TestCase):
    def test_relative_links_resolve(self):
        broken = []
        for md in tracked_markdown():
            text = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.S)
            for target in LINK.findall(text):
                path = target.split("#", 1)[0]
                if not path or re.match(r"^[a-z]+:", path) or "/" not in path and "." not in path:
                    continue  # web links, in-page anchors, and math such as [z^n](1−z)
                if not (md.parent / path).exists():
                    broken.append(f"{md.relative_to(ROOT)}: {target}")
        self.assertEqual(broken, [])

    def test_journal_index_lists_every_entry(self):
        journal = ROOT / "docs" / "journal"
        index = (journal / "INDEX.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"\]\(([^)]+\.md)\)", index)) - {"../STATUS.md"}
        files = {p.name for p in journal.glob("*.md")} - {"INDEX.md"}
        self.assertEqual(sorted(files - listed), [], "journal files missing from INDEX.md")
        self.assertEqual(sorted(listed - files), [], "INDEX.md lines without a file")


if __name__ == "__main__":
    unittest.main()
