import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import validate_world


VALID = {
    "generated": "2026-11-10T01:56:54.741342+00:00",
    "demo": False,
    "districts": [{"name": "Research", "tasks": [{"n": 1, "title": "Read safely"}]}],
    "inventions": [{"name": "sample-tool", "task": None, "summary": "A short summary."}],
    "branches": ["main", "feature/example"],
    "journal": ["Journal Entry 0001"],
    "counts": {"pending": 1, "running": 0, "done": 2, "failed": 0},
    "working": [{"agent": "core", "task": 3, "stalled": False}],
    "agents": [{"id": "visitor-ab12", "external": True, "approved": False, "reputation": 0}],
    "pending_contributions": 0,
}


class ValidateSnapshotTests(unittest.TestCase):
    def test_valid_snapshot_passes(self):
        self.assertEqual(validate_world.validate_snapshot(VALID), [])

    def test_non_object_is_rejected(self):
        self.assertIn("$: expected a JSON object", validate_world.validate_snapshot([]))

    def test_missing_required_field_is_reported(self):
        snapshot = dict(VALID)
        del snapshot["counts"]
        self.assertTrue(any("$.counts: missing required field" == e for e in validate_world.validate_snapshot(snapshot)))

    def test_timestamp_must_be_iso8601_and_timezone_aware(self):
        for value in ("yesterday", "2026-11-10T01:00:00"):
            snapshot = dict(VALID, generated=value)
            self.assertTrue(validate_world.validate_snapshot(snapshot))

    def test_boolean_is_not_accepted_as_count(self):
        snapshot = dict(VALID, counts={**VALID["counts"], "pending": True})
        self.assertTrue(any("$.counts.pending" in e for e in validate_world.validate_snapshot(snapshot)))

    def test_negative_count_is_rejected(self):
        snapshot = dict(VALID, pending_contributions=-1)
        self.assertTrue(any("$.pending_contributions" in e for e in validate_world.validate_snapshot(snapshot)))

    def test_task_and_agent_fields_are_checked(self):
        snapshot = dict(VALID)
        snapshot["districts"] = [{"name": "Research", "tasks": [{"n": 0, "title": ""}]}]
        snapshot["agents"] = [{"id": "", "external": "yes", "approved": False, "reputation": "high"}]
        errors = validate_world.validate_snapshot(snapshot)
        self.assertTrue(any("districts[0].tasks[0].n" in e for e in errors))
        self.assertTrue(any("agents[0].external" in e for e in errors))
        self.assertTrue(any("agents[0].reputation" in e for e in errors))

    def test_nullable_invention_task_is_allowed(self):
        self.assertEqual(validate_world.validate_snapshot(VALID), [])

    def test_list_bounds_are_enforced(self):
        snapshot = dict(VALID, branches=["main"] * (validate_world.LIMITS["branches"] + 1))
        self.assertTrue(any("$.branches" in e and "limit is" in e for e in validate_world.validate_snapshot(snapshot)))

    def test_string_bounds_are_enforced(self):
        snapshot = dict(VALID, journal=["x" * 121])
        self.assertTrue(any("$.journal[0]" in e and "exceeds" in e for e in validate_world.validate_snapshot(snapshot)))

    def test_cli_json_success_and_read_only_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            original = json.dumps(VALID).encode("utf-8")
            path.write_bytes(original)
            result = subprocess.run(
                [sys.executable, str(Path(validate_world.__file__)), str(path), "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"ok": True, "errors": []})
            self.assertEqual(path.read_bytes(), original)

    def test_cli_rejects_oversized_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-large.json"
            path.write_bytes(b" " * (validate_world.MAX_SNAPSHOT_BYTES + 1))
            result = subprocess.run(
                [sys.executable, str(Path(validate_world.__file__)), str(path), "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertIn("byte limit", payload["errors"][0])

    def test_cli_missing_file_does_not_echo_private_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-machine-path" / "missing.json"
            result = subprocess.run(
                [sys.executable, str(Path(validate_world.__file__)), str(path), "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(str(path), result.stdout)
            self.assertIn("OS error", json.loads(result.stdout)["errors"][0])

    def test_cli_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(validate_world.__file__)), str(path), "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid snapshot input", json.loads(result.stdout)["errors"][0])


if __name__ == "__main__":
    unittest.main()
