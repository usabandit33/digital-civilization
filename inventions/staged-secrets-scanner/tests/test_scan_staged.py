from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import scan_staged


class PatternTests(unittest.TestCase):
    def test_detects_supported_high_confidence_patterns(self):
        source = "\n".join([
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_" + "A" * 36,
            "github_pat_" + "B" * 24,
            "xoxb-1234567890-1234567890",
            "AIza" + "C" * 35,
            "sk_live_" + "d" * 24,
            "npm_" + "E" * 36,
            "-----BEGIN PRIVATE KEY-----",
        ])
        findings, suppressed = scan_staged.scan_text(source, "sample.txt", {})
        self.assertEqual(suppressed, [])
        self.assertEqual({item["rule"] for item in findings}, set(scan_staged.PATTERNS))
        self.assertEqual(len(findings), len(scan_staged.PATTERNS))

    def test_reports_one_based_line_and_column(self):
        findings, _ = scan_staged.scan_text("prefix\nxx AKIAIOSFODNN7EXAMPLE", "a.txt", {})
        self.assertEqual(findings, [{
            "path": "a.txt", "line": 2, "column": 4, "rule": "aws_access_key_id"
        }])

    def test_ignores_partial_or_nonmatching_examples(self):
        source = "AKIA123\nghp_short\nnot-a-token sk_test_" + "a" * 24
        findings, _ = scan_staged.scan_text(source, "sample.txt", {})
        self.assertEqual(findings, [])

    def test_allowlist_is_exact_by_path_and_rule(self):
        allowed = {"tests/fixture.txt": {"aws_access_key_id"}}
        source = "AKIAIOSFODNN7EXAMPLE\nsk_live_" + "a" * 24
        findings, suppressed = scan_staged.scan_text(source, "tests/fixture.txt", allowed)
        self.assertEqual([item["rule"] for item in findings], ["stripe_live_secret"])
        self.assertEqual([item["rule"] for item in suppressed], ["aws_access_key_id"])

    def test_allowlist_does_not_apply_to_another_path(self):
        allowed = {"tests/fixture.txt": {"aws_access_key_id"}}
        findings, suppressed = scan_staged.scan_text(
            "AKIAIOSFODNN7EXAMPLE", "src/config.txt", allowed
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(suppressed, [])


class AllowlistTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "allowlist.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_loads_empty_allowlist(self):
        self.write({"version": 1, "entries": []})
        self.assertEqual(scan_staged.load_allowlist(self.path), {})

    def test_rejects_parent_traversal_and_wildcards(self):
        for value in ("../secret.txt", "src/*.txt", "/tmp/secret.txt", "a//b.txt"):
            with self.subTest(path=value):
                self.write({"version": 1, "entries": [{
                    "path": value, "rules": ["aws_access_key_id"], "reason": "test"
                }]})
                with self.assertRaises(scan_staged.ScanError):
                    scan_staged.load_allowlist(self.path)

    def test_rejects_unknown_rule(self):
        self.write({"version": 1, "entries": [{
            "path": "tests/fixture.txt", "rules": ["generic_password"], "reason": "test"
        }]})
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)

    def test_rejects_non_string_rule_without_crashing(self):
        self.write({"version": 1, "entries": [{
            "path": "tests/fixture.txt", "rules": [{"bad": "value"}], "reason": "test"
        }]})
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)

    def test_rejects_boolean_version_and_duplicate_json_keys(self):
        self.write({"version": True, "entries": []})
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)
        self.path.write_text('{"version":1,"version":1,"entries":[]}', encoding="utf-8")
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)

    def test_rejects_duplicate_rule_and_empty_reason(self):
        self.write({"version": 1, "entries": [{
            "path": "tests/fixture.txt",
            "rules": ["aws_access_key_id", "aws_access_key_id"],
            "reason": "test",
        }]})
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)
        self.write({"version": 1, "entries": [{
            "path": "tests/fixture.txt", "rules": ["aws_access_key_id"], "reason": " "
        }]})
        with self.assertRaises(scan_staged.ScanError):
            scan_staged.load_allowlist(self.path)


@unittest.skipUnless(shutil.which("git"), "Git is required for staged-index integration tests")
class GitIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._git("init", "-q")
        self._git("config", "user.name", "Scanner Tests")
        self._git("config", "user.email", "scanner@example.invalid")
        self.allowlist = self.root / "allowlist.json"
        self.allowlist.write_text('{"version":1,"entries":[]}', encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _git(self, *args, input_data=None):
        options = {
            "cwd": self.root, "check": True,
            "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
        }
        if input_data is None:
            options["stdin"] = subprocess.DEVNULL
        else:
            options["input"] = input_data
        return subprocess.run(["git", *args], **options)

    def stage(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        self._git("add", "--", relative)
        return path

    def scan(self, allowlist=None):
        return scan_staged.scan_staged(self.root, allowlist or self.allowlist)

    def test_scans_staged_blob_not_working_tree(self):
        path = self.stage("config.txt", "AKIAIOSFODNN7EXAMPLE")
        path.write_text("safe after staging", encoding="utf-8")
        report, code = self.scan()
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["rule"], "aws_access_key_id")

    def test_does_not_scan_unstaged_working_tree_changes(self):
        path = self.stage("config.txt", "safe staged content")
        path.write_text("AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
        report, code = self.scan()
        self.assertEqual(code, 0)
        self.assertEqual(report["findings"], [])

    def test_clean_index_returns_success(self):
        report, code = self.scan()
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["files_checked"], 0)

    def test_binary_and_non_utf8_files_are_skipped(self):
        self.stage("binary.dat", b"\x00AKIAIOSFODNN7EXAMPLE")
        self.stage("legacy.dat", b"\xff\xfe\x01")
        report, code = self.scan()
        self.assertEqual(code, 0)
        self.assertEqual(report["binary_or_non_utf8_skipped"], 2)

    def test_symlink_target_is_not_followed_or_scanned(self):
        target = self.root / "target.txt"
        target.write_text("AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
        link = self.root / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this host")
        self._git("add", "--", "link.txt")
        report, code = self.scan()
        self.assertEqual(code, 0)
        self.assertEqual(report["findings"], [])

    def test_allowlisted_synthetic_fixture_is_suppressed(self):
        fixture = HERE / "tests" / "fixtures" / "synthetic-secrets.txt"
        relative = "inventions/staged-secrets-scanner/tests/fixtures/synthetic-secrets.txt"
        self.stage(relative, fixture.read_bytes())
        allowlist = HERE / "allowlist.json"
        report, code = self.scan(allowlist)
        self.assertEqual(code, 0)
        self.assertEqual(report["findings"], [])
        self.assertGreaterEqual(len(report["suppressed"]), 5)

    def test_oversized_staged_file_fails_closed(self):
        self.stage("large.txt", b"x" * (scan_staged.MAX_FILE_BYTES + 1))
        report, code = self.scan()
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "staged_file_too_large")

    def test_cli_json_smoke_test_in_temporary_repository(self):
        self.stage("clean.txt", "ordinary documentation")
        command = [
            sys.executable, str(HERE / "scan_staged.py"),
            "--repo", str(self.root), "--allowlist", str(self.allowlist), "--json",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["files_checked"], 1)

    def test_json_report_never_contains_matched_secret_value(self):
        secret = "AKIA" + "IOSFODNN7EXAMPLE"
        self.stage("config.txt", "AWS_ACCESS_KEY_ID=" + secret)
        command = [
            sys.executable, str(HERE / "scan_staged.py"),
            "--repo", str(self.root), "--allowlist", str(self.allowlist), "--json",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn(secret, completed.stdout)
        self.assertNotIn(secret, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["findings"][0]["rule"], "aws_access_key_id")

    def test_unmerged_index_fails_closed(self):
        self.stage("conflict.txt", "base")
        self._git("commit", "-qm", "base")
        blob = self._git("hash-object", "-w", "--stdin", input_data=b"conflict")
        oid = blob.stdout.decode("ascii").strip()
        self._git("update-index", "--add", "--cacheinfo", f"100644,{oid},conflict.txt")
        self._git("update-index", "--force-remove", "conflict.txt")
        self._git(
            "update-index", "--index-info",
            input_data=b"100644 " + oid.encode() + b" 1\tconflict.txt\n",
        )
        report, code = self.scan()
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "unmerged_index_entries")

    def test_deleted_file_is_not_scanned(self):
        self.stage("config.txt", "safe")
        self._git("commit", "-qm", "initial")
        (self.root / "config.txt").unlink()
        self._git("add", "-u", "--", "config.txt")
        report, code = self.scan()
        self.assertEqual(code, 0)
        self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
