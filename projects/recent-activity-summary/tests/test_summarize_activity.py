import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from summarize_activity import summarize

class SummaryTests(unittest.TestCase):
    def test_newest_first_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/"old").write_text("older"); (p/"new").write_text("newer")
            os.utime(p/"old", (100,100)); os.utime(p/"new", (200,200))
            result = summarize(p, 1)
            self.assertIn("new", result); self.assertNotIn("old", result)
    def test_secret_redaction_and_no_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"entry").write_text("api_key=supersecret-value")
            result=summarize(p)
            self.assertIn("[REDACTED]", result); self.assertNotIn("supersecret-value", result); self.assertNotIn(str(p), result)
    def test_symlinks_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"target").write_text("data")
            try: (p/"link").symlink_to(p/"target")
            except OSError: self.skipTest("symlinks unavailable")
            self.assertNotIn("link:", summarize(p))
    def test_invalid_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): summarize(Path(d)/"missing")

if __name__ == "__main__": unittest.main()
