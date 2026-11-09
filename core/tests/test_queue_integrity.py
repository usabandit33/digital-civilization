"""Tests for the read-only task queue integrity checker."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.queue_integrity import inspect_queue, main


VALID_SCHEMA = """
CREATE TABLE tasks (
    id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    priority INTEGER,
    status TEXT,
    title TEXT
)
"""


class QueueIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "queue.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_database(self, schema=VALID_SCHEMA, rows=()):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(schema)
            for row in rows:
                connection.execute(
                    "INSERT INTO tasks (id, created_at, updated_at, priority, status, title) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    row,
                )
        return self.db_path

    @staticmethod
    def valid_row(task_id=1, status="pending", title="Example"):
        return (task_id, "2026-11-08T00:00:00+00:00", "2026-11-08T00:00:00+00:00", 100, status, title)

    def test_valid_queue_passes(self):
        self.create_database(rows=[self.valid_row(), self.valid_row(2, "running")])
        report = inspect_queue(self.db_path)
        self.assertTrue(report["ok"])
        self.assertEqual(report["task_count"], 2)
        self.assertEqual(report["issues"], [])

    def test_duplicate_ids_are_reported(self):
        self.create_database(rows=[self.valid_row(), self.valid_row()])
        report = inspect_queue(self.db_path)
        self.assertFalse(report["ok"])
        duplicate = [item for item in report["issues"] if item["code"] == "duplicate_task_id"]
        self.assertEqual(duplicate[0]["task_id"], 1)
        self.assertEqual(duplicate[0]["occurrences"], 2)

    def test_invalid_status_is_reported(self):
        self.create_database(rows=[self.valid_row(status="complete")])
        report = inspect_queue(self.db_path)
        self.assertFalse(report["checks"]["valid_statuses"])
        self.assertIn("invalid_task_status", [item["code"] for item in report["issues"]])

    def test_null_and_blank_required_values_are_reported(self):
        row = (1, None, "   ", 100, "pending", "  ")
        self.create_database(rows=[row])
        report = inspect_queue(self.db_path)
        missing = [item["field"] for item in report["issues"] if item["code"] == "missing_required_value"]
        self.assertEqual(set(missing), {"created_at", "updated_at", "title"})
        self.assertFalse(report["checks"]["required_values_present"])

    def test_missing_required_columns_are_reported_without_crashing(self):
        self.create_database(schema="CREATE TABLE tasks (id INTEGER, status TEXT, title TEXT)")
        report = inspect_queue(self.db_path)
        issue = next(item for item in report["issues"] if item["code"] == "required_columns_missing")
        self.assertEqual(set(issue["columns"]), {"created_at", "updated_at", "priority"})
        self.assertFalse(report["checks"]["required_columns_present"])

    def test_missing_tasks_table_is_reported(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("CREATE TABLE other (id INTEGER)")
        report = inspect_queue(self.db_path)
        self.assertFalse(report["checks"]["tasks_table_present"])
        self.assertIn("tasks_table_missing", [item["code"] for item in report["issues"]])

    def test_missing_database_is_reported(self):
        report = inspect_queue(self.db_path)
        self.assertIn("database_not_found", [item["code"] for item in report["issues"]])

    def test_corrupt_file_is_reported_as_unreadable(self):
        self.db_path.write_bytes(b"not a sqlite database")
        report = inspect_queue(self.db_path)
        self.assertIn("database_unreadable", [item["code"] for item in report["issues"]])

    def test_inspection_does_not_change_database_bytes(self):
        self.create_database(rows=[self.valid_row()])
        before = self.db_path.read_bytes()
        report = inspect_queue(self.db_path)
        after = self.db_path.read_bytes()
        self.assertTrue(report["ok"])
        self.assertEqual(before, after)

    def test_json_cli_emits_machine_readable_report(self):
        self.create_database(rows=[self.valid_row()])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["--db", str(self.db_path), "--json"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["task_count"], 1)

    def test_human_cli_returns_nonzero_for_issues(self):
        self.create_database(rows=[self.valid_row(status="unknown")])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["--db", str(self.db_path)])
        self.assertEqual(exit_code, 1)
        self.assertIn("ISSUES FOUND", output.getvalue())


if __name__ == "__main__":
    unittest.main()
