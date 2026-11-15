import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

from journal_index import JournalEntry, collect_entries, main, render_index


class JournalIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.journal = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_entry(self, name, content):
        path = self.journal / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_reads_bold_date_and_topics_metadata(self):
        self.write_entry(
            "0007-task-queue.md",
            "# Queue Reliability\n\n**Date:** 2026-11-12\n"
            "**Topics:** queue, reliability\n",
        )
        entry = collect_entries(self.journal)[0]
        self.assertEqual(entry.entry_date, date(2026, 11, 12))
        self.assertEqual(entry.title, "Queue Reliability")
        self.assertEqual(entry.topics, ("queue", "reliability"))

    def test_supports_date_bolded_with_colon_inside(self):
        self.write_entry("0001-first.md", "# First\n\n**Date:** 2026-10-30\n")
        self.assertEqual(collect_entries(self.journal)[0].entry_date, date(2026, 10, 30))

    def test_falls_back_to_filename_topic_and_title(self):
        self.write_entry("0002-local-health-check.md", "No heading or metadata\n")
        entry = collect_entries(self.journal)[0]
        self.assertEqual(entry.title, "Local Health Check")
        self.assertEqual(entry.topics, ("Local Health Check",))
        self.assertIsNone(entry.entry_date)

    def test_sorts_newest_first_then_undated(self):
        self.write_entry("0001-old.md", "# Old\n\nDate: 2026-01-01\n")
        self.write_entry("0002-new.md", "# New\n\nDate: 2026-11-01\n")
        self.write_entry("0003-undated.md", "# Undated\n")
        self.assertEqual(
            [entry.filename for entry in collect_entries(self.journal)],
            ["0002-new.md", "0001-old.md", "0003-undated.md"],
        )

    def test_invalid_date_is_treated_as_undated(self):
        self.write_entry("0001-invalid.md", "# Invalid\n\nDate: 2026-99-99\n")
        self.assertIsNone(collect_entries(self.journal)[0].entry_date)

    def test_ignores_unmatched_files_and_nested_directories(self):
        self.write_entry("INDEX.md", "# Generated index\n")
        self.write_entry("notes.md", "# Notes\n")
        nested = self.journal / "nested"
        nested.mkdir()
        (nested / "0003-hidden.md").write_text("# Hidden\n", encoding="utf-8")
        self.write_entry("0001-visible.md", "# Visible\n")
        self.assertEqual(
            [entry.filename for entry in collect_entries(self.journal)],
            ["0001-visible.md"],
        )

    def test_skips_symlinked_entries(self):
        target = self.write_entry("target.md", "# Target\n")
        link = self.journal / "0001-linked.md"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available on this platform")
        self.assertEqual(collect_entries(self.journal), [])

    def test_index_contains_date_table_and_topic_groups(self):
        entries = [
            JournalEntry(2, "0002-b.md", "Second Entry", date(2026, 11, 2), ("memory",)),
            JournalEntry(1, "0001-a.md", "First Entry", date(2026, 11, 1), ("memory", "tools")),
        ]
        output = render_index(entries)
        self.assertIn("## By date", output)
        self.assertIn("## By topic", output)
        self.assertIn("### memory", output)
        self.assertIn("### tools", output)
        self.assertIn("[Second Entry](0002-b.md)", output)

    def test_escapes_markdown_metadata(self):
        entries = [
            JournalEntry(1, "0001-a.md", "Title | with [markup]", date(2026, 1, 1), ("ops | admin",))
        ]
        output = render_index(entries)
        self.assertIn(r"ops \| admin", output)
        self.assertIn(r"Title \| with \[markup\]", output)

    def test_empty_directory_has_explanatory_output(self):
        self.assertIn("No numbered journal entries", render_index([]))

    def test_missing_directory_returns_cli_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--journal-dir", str(self.journal / "missing")])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("journal directory", stderr.getvalue())

    def test_cli_writes_only_to_stdout(self):
        self.write_entry("0001-first.md", "# First\n\nDate: 2026-11-01\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--journal-dir", str(self.journal)])
        self.assertEqual(code, 0)
        self.assertIn("[First](0001-first.md)", stdout.getvalue())
        self.assertEqual(sorted(path.name for path in self.journal.iterdir()), ["0001-first.md"])


if __name__ == "__main__":
    unittest.main()
