"""Focused standard-library checks for the versioned memory-record contract."""
import json
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "memory-record.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "fact-v1.json"


def _has_timezone(value):
    """Return whether a date-time string parses and includes an explicit offset."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


class MemoryRecordSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def test_schema_declares_draft_2020_12_and_v1_identifier(self):
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertTrue(self.schema["$id"].endswith("/memory-record-v1.json"))

    def test_root_contract_is_versioned_and_closed(self):
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            set(self.schema["required"]),
            {
                "schema_version", "id", "record_type", "content",
                "source", "created_at", "confidence", "retention",
            },
        )

    def test_record_type_and_confidence_are_bounded(self):
        props = self.schema["properties"]
        self.assertEqual(
            set(props["record_type"]["enum"]),
            {"fact", "decision", "hypothesis", "observation", "lesson"},
        )
        self.assertEqual(props["confidence"]["minimum"], 0)
        self.assertEqual(props["confidence"]["maximum"], 1)

    def test_source_requires_provenance_and_timestamp(self):
        source = self.schema["$defs"]["source"]
        self.assertFalse(source["additionalProperties"])
        self.assertEqual(
            set(source["required"]),
            {"kind", "ref", "captured_at"},
        )
        self.assertEqual(source["properties"]["captured_at"]["format"], "date-time")

    def test_retention_has_class_review_and_expiry_fields(self):
        retention = self.schema["$defs"]["retention"]
        self.assertFalse(retention["additionalProperties"])
        self.assertEqual(
            set(retention["required"]),
            {"class", "review_after", "expires_at"},
        )
        self.assertEqual(
            set(retention["properties"]["class"]["enum"]),
            {"ephemeral", "working", "durable"},
        )
        for field in ("review_after", "expires_at"):
            self.assertEqual(
                set(retention["properties"][field]["type"]),
                {"string", "null"},
            )

    def test_example_uses_only_declared_fields(self):
        self.assertTrue(set(self.example).issubset(self.schema["properties"]))
        self.assertTrue(set(self.schema["required"]).issubset(self.example))
        self.assertTrue(
            set(self.example["source"]).issubset(
                self.schema["$defs"]["source"]["properties"]
            )
        )
        self.assertTrue(
            set(self.example["retention"]).issubset(
                self.schema["$defs"]["retention"]["properties"]
            )
        )

    def test_example_matches_core_contract_constraints(self):
        record = self.example
        self.assertEqual(record["schema_version"], "1.0")
        self.assertRegex(record["id"], self.schema["$defs"]["id"]["pattern"])
        self.assertIn(
            record["record_type"],
            self.schema["properties"]["record_type"]["enum"],
        )
        self.assertGreaterEqual(len(record["content"]), 1)
        self.assertLessEqual(
            len(record["content"]),
            self.schema["properties"]["content"]["maxLength"],
        )
        self.assertIsInstance(record["confidence"], (int, float))
        self.assertFalse(isinstance(record["confidence"], bool))
        self.assertGreaterEqual(record["confidence"], 0)
        self.assertLessEqual(record["confidence"], 1)
        self.assertIn(
            record["source"]["kind"],
            self.schema["$defs"]["source"]["properties"]["kind"]["enum"],
        )
        self.assertIn(
            record["retention"]["class"],
            self.schema["$defs"]["retention"]["properties"]["class"]["enum"],
        )

    def test_example_timestamps_are_timezone_aware(self):
        self.assertTrue(_has_timezone(self.example["created_at"]))
        self.assertTrue(_has_timezone(self.example["source"]["captured_at"]))

    def test_nullable_retention_timestamps_are_valid_in_example(self):
        retention = self.example["retention"]
        self.assertIsNone(retention["review_after"])
        self.assertIsNone(retention["expires_at"])

    def test_schema_does_not_add_runtime_or_sensitive_fields(self):
        serialized = json.dumps(self.schema).lower()
        for field in ("password", "api_key", "authorization", "absolute_path", "hostname"):
            with self.subTest(field=field):
                self.assertNotIn(f'"{field}"', serialized)


if __name__ == "__main__":
    unittest.main()
