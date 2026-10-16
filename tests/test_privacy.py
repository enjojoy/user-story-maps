"""Check that fonts stay local unless a Google Fonts download is requested."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
import storymap as sm  # noqa: E402

FIXTURE = HERE / "fixtures" / "sample-app"


class TestFontPrivacy(unittest.TestCase):
    def tearDown(self):
        sm.load_model(str(FIXTURE))  # restore the shared module-level theme

    def test_examples_ship_their_heading_fonts(self):
        for name in ("open-golf", "wikipedia-ios"):
            folder = ROOT / "examples" / name
            with self.subTest(example=name):
                source = (folder / "stories.yaml").read_text(encoding="utf-8")
                theme = sm.parse_yaml_subset(source)["theme"]
                self.assertEqual(theme["google_font"], "false")
                for key in ("heading_font_file", "heading_font_file_bold"):
                    with self.subTest(key=key):
                        relative = theme[key]
                        self.assertFalse(os.path.isabs(relative))
                        self.assertNotIn("..", relative.replace("\\", "/").split("/"))
                        font = folder / relative
                        self.assertTrue(font.is_file(), str(font))
                        self.assertTrue((font.parent / "OFL.txt").is_file())

    def test_google_fonts_are_off_when_key_is_absent(self):
        model = sm.load_model(str(FIXTURE))
        model["raw"]["theme"] = {"font": "Foo"}
        with patch.object(sm, "_system_font", return_value=None), patch.object(
                sm, "_google_fetch", side_effect=AssertionError("unexpected font download")) as fetch:
            sm.apply_theme(model)
        fetch.assert_not_called()

    def test_google_fonts_are_fetched_once_when_enabled(self):
        model = sm.load_model(str(FIXTURE))
        model["raw"]["theme"] = {"font": "Foo", "google_font": "true"}
        with patch.object(sm, "_system_font", return_value=None), patch.object(
                sm, "_google_fetch", return_value=None) as fetch:
            sm.apply_theme(model)
        fetch.assert_called_once_with("Foo")


if __name__ == "__main__":
    unittest.main()
