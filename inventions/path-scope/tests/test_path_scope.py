"""Tests for the path-scope helper."""
from pathlib import Path
import tempfile
import unittest

from path_scope import PathScopeError, resolve_scoped_path


class ResolveScopedPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "allowed"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_resolves_relative_path_inside_root(self):
        expected = (self.root / "reports" / "today.json").resolve()
        self.assertEqual(
            resolve_scoped_path(self.root, "reports/today.json"), expected
        )

    def test_accepts_absolute_path_inside_root(self):
        target = self.root / "notes.txt"
        self.assertEqual(resolve_scoped_path(self.root, target), target.resolve())

    def test_allows_root_itself(self):
        self.assertEqual(resolve_scoped_path(self.root, "."), self.root.resolve())

    def test_rejects_absolute_path_outside_root(self):
        with self.assertRaisesRegex(PathScopeError, "outside"):
            resolve_scoped_path(self.root, self.outside / "secret.txt")

    def test_rejects_parent_component_even_when_it_normalizes_inside(self):
        with self.assertRaisesRegex(PathScopeError, "traversal"):
            resolve_scoped_path(self.root, "reports/../notes.txt")

    def test_rejects_parent_component_that_escapes_root(self):
        with self.assertRaises(PathScopeError):
            resolve_scoped_path(self.root, "../outside/secret.txt")

    def test_missing_destination_is_allowed_by_default(self):
        result = resolve_scoped_path(self.root, "new/output.txt")
        self.assertEqual(result, self.root / "new" / "output.txt")
        self.assertFalse(result.exists())

    def test_must_exist_requires_an_existing_target(self):
        existing = self.root / "present.txt"
        existing.write_text("safe", encoding="utf-8")
        self.assertEqual(
            resolve_scoped_path(self.root, "present.txt", must_exist=True),
            existing.resolve(),
        )
        with self.assertRaisesRegex(PathScopeError, "does not exist"):
            resolve_scoped_path(self.root, "missing.txt", must_exist=True)

    def test_rejects_non_directory_root(self):
        file_path = self.base / "not-a-directory"
        file_path.write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(PathScopeError, "existing directory"):
            resolve_scoped_path(file_path, "child")

    def test_rejects_missing_root(self):
        with self.assertRaisesRegex(PathScopeError, "existing directory"):
            resolve_scoped_path(self.base / "missing", "child")

    def test_rejects_empty_or_invalid_candidate(self):
        for value in ("", b"file", None, "bad\x00path"):
            with self.subTest(value=value):
                with self.assertRaises(PathScopeError):
                    resolve_scoped_path(self.root, value)

    def test_rejects_non_boolean_must_exist(self):
        with self.assertRaisesRegex(PathScopeError, "boolean"):
            resolve_scoped_path(self.root, "file", must_exist=1)

    def test_rejects_symlink_that_escapes_root(self):
        link = self.root / "external"
        try:
            link.symlink_to(self.outside, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")
        with self.assertRaisesRegex(PathScopeError, "outside"):
            resolve_scoped_path(self.root, "external/secret.txt")

    def test_accepts_symlink_that_stays_inside_root(self):
        actual = self.root / "actual"
        actual.mkdir()
        link = self.root / "alias"
        try:
            link.symlink_to(actual, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")
        self.assertEqual(
            resolve_scoped_path(self.root, "alias/new.txt"),
            actual / "new.txt",
        )

    def test_rejects_missing_child_beneath_a_file(self):
        parent = self.root / "not-a-directory"
        parent.write_text("file", encoding="utf-8")
        with self.assertRaises(PathScopeError):
            resolve_scoped_path(self.root, "not-a-directory/child")

    def test_rejects_dangling_symlink(self):
        link = self.root / "dangling"
        try:
            link.symlink_to(self.outside / "missing")
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaises(PathScopeError):
            resolve_scoped_path(self.root, "dangling/new-file")

    def test_rejects_symlink_loop(self):
        first, second = self.root / "first", self.root / "second"
        try:
            first.symlink_to(second)
            second.symlink_to(first)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaises(PathScopeError):
            resolve_scoped_path(self.root, "first/child")


if __name__ == "__main__":
    unittest.main()
