import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "docs" / "world" / "index.html"


class ViewerAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_document_has_mobile_viewport_and_language(self):
        self.assertIn('<html lang="en">', self.html)
        self.assertIn('name="viewport"', self.html)

    def test_canvas_has_accessible_name_and_fallback(self):
        self.assertIn('role="img"', self.html)
        self.assertIn('aria-label="Isometric map', self.html)
        self.assertIn("Use the landmark buttons below", self.html)

    def test_landmark_buttons_are_native_controls(self):
        self.assertIn('id="building-list"', self.html)
        self.assertIn('type="button"', self.html)
        self.assertIn('aria-pressed', self.html)

    def test_keyboard_navigation_is_present(self):
        self.assertIn('addEventListener("keydown"', self.html)
        self.assertIn('ArrowRight', self.html)

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion:reduce", self.html)
        self.assertIn("prefers-reduced-motion: reduce", self.html)

    def test_viewer_is_explicitly_read_only(self):
        self.assertIn("observational only", self.html)
        self.assertIn("cannot assign work", self.html)

    def test_no_external_runtime_dependencies(self):
        self.assertNotIn("<script src=", self.html)
        self.assertNotIn("<link rel=", self.html)


if __name__ == "__main__":
    unittest.main()
