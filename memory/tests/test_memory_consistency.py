"""Tests for the read-only memory consistency checker."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

MEMORY_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORY_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORY_ROOT))

import check_consistency as checker


SCHEMA = {
    "$schema": checker.DRAFT_2020_12,
    "type": "object",
    "additionalProperties": False,
    "required": sorted(checker.REQUIRED_RECORD_KEYS),
    "properties": {
        "schema_version": {"const": "1.0"},
        "id": {"$ref": "#/$defs/id"},
        "record_type": {"type": "string", "enum": sorted(checker.RECORD_TYPES)},
        "content": {"type": "string", "minLength": 1, "maxLength": 10000},
        "source": {"$ref": "#/$defs/source"},
        "created_at": {"type": "string", "format": "date-time"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "retention": {"$ref": "#/$defs/retention"},
        "tags": {"type": "array", "maxItems": 20, "uniqueItems": True,
                 "items": {"type": "string", "minLength": 1, "maxLength": 64}},
        "related_ids": {"type": "array", "maxItems": 50, "uniqueItems": True,
                        "items": {"$ref": "#/$defs/id"}},
    },
    "$defs": {
        "id": {"type": "string", "minLength": 1, "maxLength": 128,
               "pattern": checker.ID_PATTERN.pattern},
        "source": {
            "type": "object", "additionalProperties": False,
            "required": sorted(checker.SOURCE_KEYS),
            "properties": {
                "kind": {"type": "string", "enum": sorted(checker.SOURCE_KINDS)},
                "ref": {"type": "string", "minLength": 1, "maxLength": 2048},
                "captured_at": {"type": "string", "format": "date-time"},
            },
        },
        "retention": {
            "type": "object", "additionalProperties": False,
            "required": sorted(checker.RETENTION_KEYS),
            "properties": {
                "class": {"type": "string", "enum": sorted(checker.RETENTION_CLASSES)},
                "review_after": {"type": ["string", "null"], "format": "date-time"},
                "expires_at": {"type": ["string", "null"], "format": "date-time"},
            },
        },
    },
}

EXAMPLE = {
    "schema_version": "1.0",
    "id": "dc.fact.local-first",
    "record_type": "fact",
    "content": "Prefer small local-first tools.",
    "source": {
        "kind": "repository_file",
        "ref": "AGENT.md",
        "captured_at": "2026-11-12T22:40:00Z",
    },
    "created_at": "2026-11-12T22:45:00Z",
    "confidence": 1,
    "retention": {
        "class": "durable",
        "review_after": None,
        "expires_at": None,
    },
}


class MemoryConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.records = self.root / "records"
        self.records.mkdir()
        self.schema_path = self.root / "schema.json"
        self.schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_record(self, name, record):
        path = self.records / name
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def check(self, *paths):
        return checker.check_records(
            paths or (self.records,),
            self.schema_path,
        )

    def test_valid_record_passes(self):
        self.write_record("fact.json", EXAMPLE)
        report, code = self.check()
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["records_valid"], 1)

    def test_checked_in_example_passes_checked_in_schema(self):
        example_dir = Path(__file__).resolve().parents[1] / "examples"
        report, code = checker.check_records((example_dir,), checker.DEFAULT_SCHEMA_PATH)
        self.assertEqual(code, 0)
        self.assertEqual(report["records_valid"], 1)

    def test_missing_required_field_is_reported(self):
        record = copy.deepcopy(EXAMPLE)
        del record["source"]
        self.write_record("missing.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("missing_required_field", {item["code"] for item in report["findings"]})

    def test_unknown_field_is_rejected(self):
        record = dict(EXAMPLE, private_extra="unexpected")
        self.write_record("extra.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("unknown_field", {item["code"] for item in report["findings"]})

    def test_boolean_is_not_accepted_as_confidence(self):
        record = dict(EXAMPLE, confidence=True)
        self.write_record("bool.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("invalid_confidence", {item["code"] for item in report["findings"]})

    def test_confidence_outside_range_is_rejected(self):
        record = dict(EXAMPLE, confidence=1.1)
        self.write_record("confidence.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("invalid_confidence", {item["code"] for item in report["findings"]})

    def test_unhashable_enum_values_do_not_crash(self):
        record = copy.deepcopy(EXAMPLE)
        record["record_type"] = []
        record["source"]["kind"] = {}
        record["retention"]["class"] = []
        self.write_record("malformed.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertGreater(report["records_invalid"], 0)

    def test_timestamp_requires_timezone(self):
        record = copy.deepcopy(EXAMPLE)
        record["created_at"] = "2026-11-12T22:45:00"
        self.write_record("naive.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("invalid_timestamp", {item["code"] for item in report["findings"]})

    def test_duplicate_ids_are_reported(self):
        self.write_record("a.json", EXAMPLE)
        duplicate = copy.deepcopy(EXAMPLE)
        duplicate["content"] = "A second record with the same ID."
        self.write_record("b.json", duplicate)
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("duplicate_id", {item["code"] for item in report["findings"]})

    def test_unresolved_related_id_is_reported_as_warning(self):
        record = dict(EXAMPLE, related_ids=["dc.fact.missing"])
        self.write_record("reference.json", record)
        report, code = self.check()
        self.assertEqual(code, 1)
        warning = next(item for item in report["findings"] if item["code"] == "unresolved_related_id")
        self.assertEqual(warning["severity"], "warning")

    def test_related_ids_resolve_across_scanned_records(self):
        first = dict(EXAMPLE, related_ids=["dc.fact.second"])
        second = copy.deepcopy(EXAMPLE)
        second["id"] = "dc.fact.second"
        self.write_record("a.json", first)
        self.write_record("b.json", second)
        report, code = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(report["records_valid"], 2)

    def test_invalid_json_is_reported_without_echoing_contents(self):
        (self.records / "broken.json").write_text('{"secret":"do-not-print"', encoding="utf-8")
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("invalid_json", {item["code"] for item in report["findings"]})
        self.assertNotIn("do-not-print", json.dumps(report))

    def test_non_standard_json_constants_are_rejected(self):
        (self.records / "nan.json").write_text('{"confidence":NaN}', encoding="utf-8")
        report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("invalid_json_value", {item["code"] for item in report["findings"]})

    def test_schema_version_mismatch_is_a_scan_error(self):
        altered = copy.deepcopy(SCHEMA)
        altered["properties"]["confidence"]["maximum"] = 10
        self.schema_path.write_text(json.dumps(altered), encoding="utf-8")
        report, code = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "schema_unavailable_or_invalid")

    def test_schema_drift_with_same_version_is_rejected(self):
        altered = copy.deepcopy(SCHEMA)
        altered["properties"]["content"]["maxLength"] = 20000
        self.schema_path.write_text(json.dumps(altered), encoding="utf-8")
        report, code = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "schema_unavailable_or_invalid")

    def test_missing_explicit_input_is_a_scan_error(self):
        report, code = self.check(self.root / "missing")
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "input_not_found")

    def test_missing_default_records_directory_is_clean_empty_state(self):
        missing = self.root / "not-created-yet"
        report, code = checker.check_records(
            (missing,), self.schema_path, allow_missing_default=True
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["files_checked"], 0)

    def test_directory_scan_is_not_recursive(self):
        nested = self.records / "nested"
        nested.mkdir()
        (nested / "fact.json").write_text(json.dumps(EXAMPLE), encoding="utf-8")
        report, code = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(report["files_checked"], 0)

    def test_symlinked_record_is_ignored(self):
        target = self.root / "outside.json"
        target.write_text(json.dumps(EXAMPLE), encoding="utf-8")
        link = self.records / "linked.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        report, code = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(report["files_checked"], 0)

    def test_oversized_record_is_rejected(self):
        self.write_record("large.json", EXAMPLE)
        with patch.object(checker, "MAX_RECORD_BYTES", 8):
            report, code = self.check()
        self.assertEqual(code, 1)
        self.assertIn("record_too_large", {item["code"] for item in report["findings"]})

    def test_record_file_count_is_bounded(self):
        self.write_record("a.json", EXAMPLE)
        self.write_record("b.json", EXAMPLE)
        with patch.object(checker, "MAX_RECORD_FILES", 1):
            report, code = self.check()
        self.assertEqual(code, 2)
        self.assertIn("too_many_record_files", {item["code"] for item in report["scan_errors"]})

    def test_report_uses_relative_labels_and_omits_record_content(self):
        record = dict(EXAMPLE, content="private sentence that must not appear")
        self.write_record("private.json", record)
        report, _ = self.check()
        rendered = json.dumps(report)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn(record["content"], rendered)
        self.assertIn("records/private.json", rendered)

    def test_non_json_file_in_explicit_file_mode_is_rejected(self):
        note = self.root / "notes.txt"
        note.write_text("not a record", encoding="utf-8")
        report, code = self.check(note)
        self.assertEqual(code, 2)
        self.assertEqual(report["scan_errors"][0]["code"], "unsupported_file")


if __name__ == "__main__":
    unittest.main()
