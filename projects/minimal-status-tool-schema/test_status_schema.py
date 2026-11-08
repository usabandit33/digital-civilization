import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "status-tool.schema.json"


class StatusToolSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_is_json_schema_with_closed_tool_boundary(self):
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.schema["properties"]["name"]["const"], "get_local_status")

    def test_tool_has_no_input_parameters(self):
        input_schema = self.schema["properties"]["inputSchema"]
        self.assertEqual(input_schema["type"], "object")
        self.assertFalse(input_schema["additionalProperties"])
        self.assertEqual(input_schema["properties"], {})

    def test_output_is_minimal_and_closed(self):
        output = self.schema["$defs"]["status"]
        self.assertFalse(output["additionalProperties"])
        self.assertEqual(
            set(output["required"]),
            {"schema_version", "status", "repository", "git", "tasks"},
        )
        self.assertEqual(
            set(output["properties"]["status"]["enum"]),
            {"ok", "partial", "unavailable"},
        )
        self.assertFalse(output["properties"]["git"]["additionalProperties"])
        self.assertFalse(output["properties"]["tasks"]["additionalProperties"])

    def test_schema_omits_sensitive_free_form_fields(self):
        serialized = json.dumps(self.schema).lower()
        for field in ("hostname", "username", "absolute_path", "environment", "token", "password"):
            with self.subTest(field=field):
                self.assertNotIn(f'"{field}"', serialized)


if __name__ == "__main__":
    unittest.main()
