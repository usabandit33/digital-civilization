import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import path_sanitizer as sanitizer


class SanitizeTextTests(unittest.TestCase):
    def test_posix_home_is_replaced_inside_text(self):
        value = "opened /home/alice/Documents/report.txt successfully"
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=["/home/alice"]),
            "opened ~/Documents/report.txt successfully",
        )

    def test_windows_home_is_case_insensitive_and_accepts_both_slashes(self):
        value = 'saved to "c:/USERS/Alice/Desktop/a.txt"'
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=[r"C:\Users\Alice"]),
            'saved to "~/Desktop/a.txt"',
        )

    def test_prefix_collision_and_embedded_word_are_not_replaced(self):
        value = "/home/alice2/file /tmp/home/alice/file"
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=["/home/alice"]), value
        )

    def test_longest_nested_root_wins(self):
        value = "/srv/private/project/notes.txt"
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=["/srv", "/srv/private"]),
            "~/project/notes.txt",
        )

    def test_unc_root_is_replaced(self):
        value = r"\\server\share\private\file.txt"
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=[r"\\server\share\private"]),
            r"~\file.txt",
        )

    def test_posix_root_matching_remains_case_sensitive(self):
        value = "/home/Alice/file.txt"
        self.assertEqual(sanitizer.sanitize_text(value, roots=["/home/alice"]), value)

    def test_relative_paths_are_unchanged(self):
        value = "reports/output.json and ./cache/file.txt"
        self.assertEqual(sanitizer.sanitize_text(value, roots=["/home/alice"]), value)

    def test_empty_roots_disable_default_discovery(self):
        value = "/home/alice/file.txt"
        self.assertEqual(sanitizer.sanitize_text(value, roots=[]), value)

    def test_non_absolute_and_filesystem_roots_are_ignored(self):
        value = "/home/alice/file.txt"
        self.assertEqual(
            sanitizer.sanitize_text(value, roots=["home/alice", "/"]), value
        )


class SanitizeValueTests(unittest.TestCase):
    def test_nested_values_are_sanitized_without_changing_keys_or_scalars(self):
        value = {
            "path": "/home/alice/file.txt",
            "items": ["/home/alice/a", 7, {"nested": "/home/alice/b"}],
            "flag": True,
        }
        result = sanitizer.sanitize_value(value, roots=["/home/alice"])
        self.assertEqual(result, {
            "path": "~/file.txt",
            "items": ["~/a", 7, {"nested": "~/b"}],
            "flag": True,
        })

    def test_root_generator_is_consumed_once_for_nested_values(self):
        roots = (root for root in ["/home/alice"])
        result = sanitizer.sanitize_value(
            ["/home/alice/a", "/home/alice/b"], roots=roots
        )
        self.assertEqual(result, ["~/a", "~/b"])

    def test_mapping_keys_are_preserved(self):
        value = {"/home/alice/key": "/home/alice/value"}
        result = sanitizer.sanitize_value(value, roots=["/home/alice"])
        self.assertEqual(result, {"/home/alice/key": "~/value"})


class CliTests(unittest.TestCase):
    def test_cli_reads_and_writes_json(self):
        stdin = io.StringIO('{"file": "/opt/private/a.txt"}')
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            code = sanitizer.main(["--root", "/opt/private"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"file": "~/a.txt"})

    def test_cli_invalid_json_returns_two_without_echoing_input(self):
        stdin = io.StringIO("not-json /home/alice/secret")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout), redirect_stderr(stderr):
            code = sanitizer.main([])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid JSON input", stderr.getvalue())
        self.assertNotIn("secret", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
