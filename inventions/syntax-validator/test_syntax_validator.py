"""
test_syntax_validator.py — Unit tests for syntax_validator.py

Runs with the standard library only:
    python -m unittest test_syntax_validator -v
"""

import json
import os
import sys
import tempfile
import textwrap
import unittest

# Ensure the invention directory is importable regardless of cwd.
sys.path.insert(0, os.path.dirname(__file__))
from syntax_validator import (
    ValidationError,
    ValidationResult,
    validate_block,
    validate_blocks,
    validate_file,
    _run_smoke_tests,
)


# ---------------------------------------------------------------------------
# validate_block — success cases
# ---------------------------------------------------------------------------

class TestValidateBlockSuccess(unittest.TestCase):

    def test_empty_string(self):
        r = validate_block("")
        self.assertTrue(r.ok)
        self.assertIsNone(r.error)

    def test_simple_assignment(self):
        r = validate_block("x = 42")
        self.assertTrue(r.ok)
        self.assertIsNone(r.error)

    def test_function_definition(self):
        src = "def greet(name):\n    return f'Hello, {name}!'"
        r = validate_block(src)
        self.assertTrue(r.ok)
        self.assertIsNone(r.error)

    def test_class_definition(self):
        src = "class Dog:\n    def bark(self):\n        print('Woof!')"
        r = validate_block(src)
        self.assertTrue(r.ok)

    def test_multiline_ok(self):
        src = textwrap.dedent("""\
            import os
            x = 1
            y = 2
            z = x + y
            print(z)
        """)
        r = validate_block(src)
        self.assertTrue(r.ok)

    def test_dedent_strips_common_indent(self):
        # Code indented 4 spaces as it might appear in a markdown listing
        src = "    x = 1\n    y = 2\n"
        r = validate_block(src, dedent=True)
        self.assertTrue(r.ok)

    def test_tree_summary_populated_on_success(self):
        src = "x = 1\nimport os\ndef f(): pass"
        r = validate_block(src)
        self.assertTrue(r.ok)
        self.assertIsNotNone(r.tree_summary)
        self.assertIn("top_level_nodes", r.tree_summary)
        self.assertGreater(r.tree_summary["top_level_nodes"], 0)
        self.assertIn("by_type", r.tree_summary)

    def test_tree_summary_counts_nodes(self):
        src = "x = 1\ny = 2\nz = 3"
        r = validate_block(src)
        self.assertTrue(r.ok)
        self.assertEqual(r.tree_summary["top_level_nodes"], 3)
        self.assertEqual(r.tree_summary["by_type"].get("Assign"), 3)


# ---------------------------------------------------------------------------
# validate_block — failure cases
# ---------------------------------------------------------------------------

class TestValidateBlockFailure(unittest.TestCase):

    def test_syntax_error_missing_colon(self):
        r = validate_block("def f()\n    pass")
        self.assertFalse(r.ok)
        self.assertIsNotNone(r.error)
        self.assertEqual(r.error.type, "SyntaxError")

    def test_unclosed_parenthesis(self):
        r = validate_block("x = (1 + 2")
        self.assertFalse(r.ok)
        self.assertEqual(r.error.type, "SyntaxError")

    def test_indentation_error(self):
        r = validate_block("if True:\npass")
        self.assertFalse(r.ok)
        # IndentationError is a SyntaxError subclass; type name varies by Python version
        self.assertIn(r.error.type, ("IndentationError", "SyntaxError"))

    def test_error_has_lineno(self):
        r = validate_block("x = 1\ndef f(:\n    pass")
        self.assertFalse(r.ok)
        self.assertIsNotNone(r.error.lineno)
        self.assertGreater(r.error.lineno, 0)

    def test_error_has_message(self):
        r = validate_block("x ===== 1")
        self.assertFalse(r.ok)
        self.assertIsInstance(r.error.message, str)
        self.assertGreater(len(r.error.message), 0)

    def test_tree_summary_none_on_failure(self):
        r = validate_block("def f(:")
        self.assertFalse(r.ok)
        self.assertIsNone(r.tree_summary)


# ---------------------------------------------------------------------------
# validate_blocks — batch API
# ---------------------------------------------------------------------------

class TestValidateBlocks(unittest.TestCase):

    def test_all_valid(self):
        sources = ["x = 1", "y = 2", "def f(): pass"]
        results = validate_blocks(sources)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.ok for r in results))

    def test_mixed_valid_and_invalid(self):
        sources = ["x = 1", "def f(:", "y = 2"]
        results = validate_blocks(sources)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].ok)
        self.assertFalse(results[1].ok)
        self.assertTrue(results[2].ok)

    def test_empty_list(self):
        results = validate_blocks([])
        self.assertEqual(results, [])

    def test_preserves_order(self):
        sources = [f"x{i} = {i}" for i in range(10)]
        results = validate_blocks(sources)
        for i, r in enumerate(results):
            self.assertTrue(r.ok, f"Block {i} unexpectedly failed")


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------

class TestValidateFile(unittest.TestCase):

    def _write_tmp(self, content: str, suffix: str = ".py") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        return path

    def test_valid_file(self):
        path = self._write_tmp("x = 1\ny = 2\n")
        try:
            r = validate_file(path)
            self.assertTrue(r.ok)
        finally:
            os.unlink(path)

    def test_invalid_file(self):
        path = self._write_tmp("def broken(:\n    pass\n")
        try:
            r = validate_file(path)
            self.assertFalse(r.ok)
            self.assertIsNotNone(r.error)
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        r = validate_file("/nonexistent/path/that/does/not/exist.py")
        self.assertFalse(r.ok)
        self.assertEqual(r.error.type, "IOError")


# ---------------------------------------------------------------------------
# to_dict / JSON serialisability
# ---------------------------------------------------------------------------

class TestSerialization(unittest.TestCase):

    def test_ok_result_serialisable(self):
        r = validate_block("x = 1")
        d = r.to_dict()
        # Must round-trip through JSON without error
        s = json.dumps(d)
        parsed = json.loads(s)
        self.assertTrue(parsed["ok"])
        self.assertIsNone(parsed["error"])

    def test_error_result_serialisable(self):
        r = validate_block("def f(:")
        d = r.to_dict()
        s = json.dumps(d)
        parsed = json.loads(s)
        self.assertFalse(parsed["ok"])
        self.assertIsNotNone(parsed["error"])
        self.assertIn("type", parsed["error"])
        self.assertIn("message", parsed["error"])

    def test_validation_error_to_dict(self):
        err = ValidationError(type="SyntaxError", message="bad syntax", lineno=3, offset=5, text="bad line")
        d = err.to_dict()
        self.assertEqual(d["type"], "SyntaxError")
        self.assertEqual(d["lineno"], 3)
        self.assertEqual(d["offset"], 5)
        self.assertEqual(d["text"], "bad line")


# ---------------------------------------------------------------------------
# Built-in smoke tests
# ---------------------------------------------------------------------------

class TestSmokeTests(unittest.TestCase):

    def test_smoke_tests_all_pass(self):
        """The module's own built-in smoke tests must all pass."""
        passed = _run_smoke_tests()
        self.assertTrue(passed)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_unicode_source(self):
        src = "greeting = 'こんにちは世界'"
        r = validate_block(src)
        self.assertTrue(r.ok)

    def test_long_source(self):
        lines = [f"var_{i} = {i}" for i in range(500)]
        r = validate_block("\n".join(lines))
        self.assertTrue(r.ok)

    def test_only_comments(self):
        src = "# This is a comment\n# Another comment\n"
        r = validate_block(src)
        self.assertTrue(r.ok)

    def test_type_annotations(self):
        src = "from typing import List\ndef f(x: int) -> List[str]:\n    return [str(x)]"
        r = validate_block(src)
        self.assertTrue(r.ok)

    def test_walrus_operator(self):
        # Python 3.8+ syntax
        src = "data = [1, 2, 3]\nif n := len(data):\n    print(n)"
        r = validate_block(src)
        self.assertTrue(r.ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
