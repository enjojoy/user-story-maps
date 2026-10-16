"""The generated story-map.html must stay usable on a phone."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "storymap.py"
CHECKER = ROOT / "scripts" / "check_viewer.py"
FIXTURE = ROOT / "tests" / "fixtures" / "sample-app"
EXAMPLES = [ROOT / "examples" / name / "generated" / "story-map.html" for name in ("wikipedia-ios", "open-golf")]


def build_fixture(folder):
    app = Path(folder) / "app"
    shutil.copytree(FIXTURE, app, ignore=shutil.ignore_patterns("generated"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", STORYMAP_NO_NETWORK="1")
    result = subprocess.run([sys.executable, str(SCRIPT), "build", str(app), "--formats", "html"],
                            env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return app / "generated" / "story-map.html"


class MobileMarkup:
    """Static checks, shared by the freshly built page and the shipped examples."""

    def page(self):
        raise NotImplementedError

    def test_viewport_meta_allows_zoom(self):
        meta = re.search(r'<meta name="viewport" content="([^"]*)"', self.page())
        self.assertIsNotNone(meta, "viewport meta is missing")
        content = meta.group(1).replace(" ", "").lower()
        self.assertIn("width=device-width", content)
        self.assertIn("initial-scale=1", content)
        self.assertNotIn("user-scalable=no", content)
        self.assertNotIn("user-scalable=0", content)
        self.assertNotRegex(content, r"maximum-scale=1(\.0)?(,|$)")

    def test_mobile_media_query_and_tap_targets(self):
        css = self.page().split("</style>")[0]
        self.assertIn("@media(max-width:720px)", css)
        self.assertRegex(css, r"min-height:44px")
        self.assertIn("#lb{", css)

    def test_no_external_requests(self):
        page = self.page()
        self.assertNotRegex(page, r"""(?:src|href)=["']https?://""")
        self.assertNotRegex(page, r"@import|url\(\s*['\"]?https?:")


class TestBuiltViewer(MobileMarkup, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.html = build_fixture(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def page(self):
        return self.html.read_text(encoding="utf-8")


@unittest.skipUnless(all(p.is_file() for p in EXAMPLES), "examples not present")
class TestShippedExamples(unittest.TestCase):
    def test_examples_have_the_mobile_viewer(self):
        for path in EXAMPLES:
            with self.subTest(example=path.parent.parent.name):
                page = path.read_text(encoding="utf-8")
                self.assertIn('<meta name="viewport" content="width=device-width,initial-scale=1">', page)
                self.assertIn("@media(max-width:720px)", page)


def playwright_ready():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            exe = os.environ.get("CHROMIUM_PATH")
            (pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()).close()
        return True
    except Exception:
        return False


@unittest.skipUnless(playwright_ready(), "Playwright with Chromium is not installed")
class TestPhoneBrowser(unittest.TestCase):
    def test_no_horizontal_scroll_and_big_tap_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = [build_fixture(tmp)] + [p for p in EXAMPLES if p.is_file()]
            result = subprocess.run([sys.executable, str(CHECKER)] + [str(p) for p in pages],
                                    capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("all checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
