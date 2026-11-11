"""Tests for the standard-library repository test runner."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import run_tests


class FindRepositoryRootTests(unittest.TestCase):
    def test_finds_root_from_nested_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
            (root / "system").mkdir()
            nested = root / "system" / "tests"
            nested.mkdir()
            marker = nested / "test_example.py"
            marker.write_text("", encoding="utf-8")

            self.assertEqual(run_tests.find_repo_root(marker), root.resolve())

    def test_rejects_directory_without_repository_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(run_tests.find_repo_root(Path(directory)))


class DiscoverSuitesTests(unittest.TestCase):
    def test_groups_test_directories_by_project_and_ignores_generated_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
            locations = [
                "core/tests/test_core.py",
                "inventions/demo/tests/test_demo.py",
                "inventions/other/test_other.py",
                "projects/schema/test_schema.py",
            ]
            for relative in locations:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            ignored = root / ".venv" / "lib" / "test_ignored.py"
            ignored.parent.mkdir(parents=True)
            ignored.write_text("", encoding="utf-8")
            generated = root / "core" / "__pycache__" / "test_cached.py"
            generated.parent.mkdir()
            generated.write_text("", encoding="utf-8")

            suites = run_tests.discover_suites(root)
            names = [suite["name"] for suite in suites]
            self.assertEqual(names, [
                "core",
                "inventions/demo",
                "inventions/other",
                "projects/schema",
            ])
            self.assertEqual(sum(suite["test_files"] for suite in suites), 4)
            self.assertEqual(
                suites[0]["test_directories"],
                [root.resolve() / "core" / "tests"],
            )

    def test_empty_repository_has_no_suites(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_tests.discover_suites(Path(directory)), [])


class RunSuiteTests(unittest.TestCase):
    def make_suite(self, root):
        suite_root = root / "inventions" / "demo"
        tests = suite_root / "tests"
        tests.mkdir(parents=True)
        (tests / "test_demo.py").write_text("", encoding="utf-8")
        return {
            "name": "inventions/demo",
            "root": suite_root,
            "test_directories": [tests],
            "test_files": 1,
        }

    def test_runs_unittest_without_a_shell_and_reports_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            suite = self.make_suite(root)
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Ran 3 tests\n", stderr="OK\n"
            )
            with mock.patch.object(run_tests.subprocess, "run", return_value=completed) as run:
                result = run_tests.run_suite(root, suite, timeout_seconds=15)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["return_codes"], [0])
            args, kwargs = run.call_args
            self.assertEqual(args[0][1:4], ["-m", "unittest", "discover"])
            self.assertEqual(kwargs["cwd"], str(root))
            self.assertGreater(kwargs["timeout"], 14)
            self.assertLessEqual(kwargs["timeout"], 15)
            self.assertTrue(kwargs["capture_output"])
            self.assertNotIn("shell", kwargs)
            python_path = kwargs["env"]["PYTHONPATH"].split(os.pathsep)
            self.assertEqual(python_path[:2], [str(suite["root"]), str(root)])

    def test_nonzero_exit_is_reported_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            suite = self.make_suite(root)
            completed = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="FAILED (failures=1)\n"
            )
            with mock.patch.object(run_tests.subprocess, "run", return_value=completed):
                result = run_tests.run_suite(root, suite)
            self.assertEqual(result["status"], "failed")
            self.assertIn("FAILED", result["output"])

    def test_timeout_is_reported_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            suite = self.make_suite(root)
            timeout = subprocess.TimeoutExpired(
                cmd=["python"], timeout=1, output=b"partial output", stderr=b""
            )
            with mock.patch.object(run_tests.subprocess, "run", side_effect=timeout):
                result = run_tests.run_suite(root, suite, timeout_seconds=1)
            self.assertEqual(result["status"], "timed_out")
            self.assertIn("partial output", result["output"])

    def test_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            suite = self.make_suite(root)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="x" * (run_tests.MAX_OUTPUT_CHARACTERS + 100),
                stderr="",
            )
            with mock.patch.object(run_tests.subprocess, "run", return_value=completed):
                result = run_tests.run_suite(root, suite)
            self.assertLessEqual(
                len(result["output"]),
                run_tests.MAX_OUTPUT_CHARACTERS + 30,
            )
            self.assertTrue(result["output"].startswith("[earlier output omitted]"))


class CliTests(unittest.TestCase):
    def test_timeout_argument_is_bounded(self):
        self.assertEqual(run_tests._positive_timeout("30"), 30)
        with self.assertRaises(argparse.ArgumentTypeError):
            run_tests._positive_timeout("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            run_tests._positive_timeout(str(run_tests.MAX_TIMEOUT_SECONDS + 1))

    def test_json_cli_reports_missing_repository(self):
        with mock.patch.object(run_tests, "find_repo_root", return_value=None):
            output = io.StringIO()
            with mock.patch("sys.stdout", output):
                code = run_tests.main(["--root", "/not-a-repository", "--json"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
