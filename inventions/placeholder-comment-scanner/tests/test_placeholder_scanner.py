"""Tests for the read-only Python placeholder comment scanner."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import placeholder_scanner as scanner


class ScanSourceTests(unittest.TestCase):
    def test_finds_default_marker_with_one_based_location(self):
        findings = scanner.scan_source("x = 1  # TODO: finish this\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0],
            scanner.Finding("<string>", line=1, column=10, marker="TODO"),
        )

    def test_finds_multiple_markers_and_normalizes_case(self):
        findings = scanner.scan_source("# todo and FIXME, then xxx\n")
        self.assertEqual([item.marker for item in findings], ["TODO", "FIXME", "XXX"])

    def test_ignores_strings_docstrings_and_string_contents_that_look_like_comments(self):
        source = '''"""TODO in a module docstring is prose, not a comment token."""\nmessage = "# FIXME: not a comment"\n# TODO: this is a comment\n'''
        findings = scanner.scan_source(source)
        self.assertEqual([item.marker for item in findings], ["TODO"])
        self.assertEqual(findings[0].line, 3)

    def test_marker_names_must_be_separate_tokens(self):
        findings = scanner.scan_source("# TODOLIST FIXMEs MYTODO XXX2 _HACK HACK_\n")
        self.assertEqual(findings, [])

    def test_custom_marker_can_be_added(self):
        findings = scanner.scan_source("# REVIEW: check this\n", markers=("REVIEW",))
        self.assertEqual([item.marker for item in findings], ["REVIEW"])

    def test_rejects_invalid_marker_configuration(self):
        for markers in ((), "TODO", ("",), ("not a marker",), (None,)):
            with self.subTest(markers=markers):
                with self.assertRaises(ValueError):
                    scanner.scan_source("# TODO\n", markers=markers)

    def test_rejects_non_string_source(self):
        with self.assertRaises(TypeError):
            scanner.scan_source(b"# TODO")

    def test_reports_unterminated_string_as_tokenization_error(self):
        with self.assertRaises(scanner.SourceTokenizationError):
            scanner.scan_source("value = 'unterminated\n")


class ScanFileTests(unittest.TestCase):
    def test_scans_explicit_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("# FIXME: repair\n", encoding="utf-8")
            findings = scanner.scan_file(path)
        self.assertEqual(findings[0].path, str(path))
        self.assertEqual(findings[0].marker, "FIXME")

    def test_honors_python_encoding_cookie(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latin1.py"
            path.write_bytes(b"# coding: latin-1\n# TODO: caf\xe9\n")
            findings = scanner.scan_file(path)
        self.assertEqual([item.marker for item in findings], ["TODO"])

    def test_missing_file_raises_io_error(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.py"
            with self.assertRaises(OSError):
                scanner.scan_file(missing)


class CliTests(unittest.TestCase):
    def test_json_cli_returns_zero_for_clean_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.py"
            path.write_text("print('TODO is only a string')\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = scanner.main([str(path), "--json"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["files_scanned"], 1)
        self.assertEqual(report["finding_count"], 0)

    def test_cli_returns_one_when_markers_are_found(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unfinished.py"
            path.write_text("# TODO: finish\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = scanner.main([str(path)])
        self.assertEqual(code, 1)

    def test_cli_returns_two_for_unreadable_or_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.py"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = scanner.main([str(path), "--json"])
        self.assertEqual(code, 2)

    def test_custom_cli_marker_adds_to_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("# TODO and REVIEW\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = scanner.main([str(path), "--marker", "REVIEW", "--json"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual([item["marker"] for item in report["findings"]], ["TODO", "REVIEW"])

    def test_cli_returns_two_for_invalid_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("# TODO\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = scanner.main([str(path), "--marker", "bad marker", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["errors"][0]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
