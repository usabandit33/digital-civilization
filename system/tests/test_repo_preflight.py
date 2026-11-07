"""Unit tests for the read-only repository preflight."""

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "repo_preflight.py"
SPEC = importlib.util.spec_from_file_location("repo_preflight", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class RepoPreflightTests(unittest.TestCase):
    def make_repo(self, root: Path) -> Path:
        (root / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
        for name in preflight.REQUIRED_DIRECTORIES:
            (root / name).mkdir()
        return root

    def test_find_repo_root_from_nested_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            nested = root / "system" / "tests"
            nested.mkdir()
            self.assertEqual(preflight.find_repo_root(nested), root.resolve())

    def test_find_repo_root_returns_none_without_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(preflight.find_repo_root(Path(directory)))

    def test_python_version_requirement(self):
        result = preflight.check_python((99, 0))
        self.assertFalse(result["ok"])
        self.assertIn("minimum 99.0", result["detail"])

    def test_required_directories_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_repo(Path(directory))
            result = preflight.check_required_directories(root)
            self.assertTrue(result["ok"])
            self.assertEqual(result["missing"], [])

    def test_required_directories_report_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core").mkdir()
            result = preflight.check_required_directories(root)
            self.assertFalse(result["ok"])
            self.assertIn("memory", result["missing"])

    def test_git_missing_is_reported(self):
        with mock.patch.object(preflight.shutil, "which", return_value=None):
            result, git_dir = preflight.check_git(Path("/unused"))
        self.assertFalse(result["ok"])
        self.assertIsNone(git_dir)
        self.assertIn("not found", result["detail"])

    def test_git_success_checks_worktree_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            git_dir = root / ".git"
            responses = [
                subprocess.CompletedProcess([], 0, "git version 2.40.0\n", ""),
                subprocess.CompletedProcess([], 0, str(root) + "\n", ""),
                subprocess.CompletedProcess([], 0, str(git_dir) + "\n", ""),
            ]
            with mock.patch.object(preflight.shutil, "which", return_value="/usr/bin/git"):
                with mock.patch.object(preflight.subprocess, "run", side_effect=responses) as run:
                    result, actual_git_dir = preflight.check_git(root)
        self.assertTrue(result["ok"])
        self.assertEqual(actual_git_dir, git_dir)
        self.assertEqual(run.call_count, 3)

    def test_writable_state_checks_permissions_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = root / ".git"
            metadata.mkdir()
            with mock.patch.object(preflight.os, "access", return_value=False):
                result = preflight.check_writable_state(root, metadata)
        self.assertFalse(result["ok"])
        self.assertIn("repository root", result["detail"])
        self.assertIn("Git metadata", result["detail"])

    def test_cli_json_returns_machine_readable_result(self):
        expected = {
            "ok": True,
            "repository": "digital-civilization",
            "checks": [{"name": "sample", "ok": True, "detail": "ready"}],
        }
        output = io.StringIO()
        with mock.patch.object(preflight, "find_repo_root", return_value=Path("/tmp/digital-civilization")):
            with mock.patch.object(preflight, "run_preflight", return_value=expected):
                with contextlib.redirect_stdout(output):
                    code = preflight.main(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_cli_fails_when_repository_root_is_missing(self):
        output = io.StringIO()
        with mock.patch.object(preflight, "find_repo_root", return_value=None):
            with contextlib.redirect_stdout(output):
                code = preflight.main(["--json"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
