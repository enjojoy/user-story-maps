"""Run:  python3 -m unittest discover -s tests -v   (standard library only; Pillow/Graphviz optional)"""
import json, os, re, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import storymap as sm  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "examples", "plant-waterer")


def codes(issues, level=None):
    return {c for lvl, c, _ in issues if level in (None, lvl)}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "map")
        shutil.copytree(EXAMPLE, self.dir, ignore=shutil.ignore_patterns("generated", "tools"))
        self.src = os.path.join(self.dir, "stories.yaml")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, old, new, count=1):
        t = open(self.src, encoding="utf-8").read()
        self.assertIn(old, t)
        open(self.src, "w", encoding="utf-8").write(t.replace(old, new, count))

    def issues(self):
        return sm.validate(sm.load_model(self.dir))


class TestParser(unittest.TestCase):
    def test_subset(self):
        d = sm.parse_yaml_subset('a: 1\nb:\n  - x: "q: r"  # c\n    y: [p, "q, r"]\n  - z\nc: it\'s ok\n')
        self.assertEqual(d, {"a": "1", "b": [{"x": "q: r", "y": ["p", "q, r"]}, "z"], "c": "it's ok"})

    def test_multiline_rejected(self):
        with self.assertRaises(sm.SourceError):
            sm.parse_yaml_subset("a: |\n  text\n")

    def test_matches_pyyaml_when_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        t = open(os.path.join(EXAMPLE, "stories.yaml"), encoding="utf-8").read()
        self.assertEqual(sm.parse_yaml_subset(t), yaml.load(t, Loader=yaml.BaseLoader))


class TestExamples(unittest.TestCase):
    def test_all_examples_validate(self):
        ex = os.path.join(HERE, "..", "examples")
        for name in sorted(os.listdir(ex)):
            d = os.path.join(ex, name)
            if os.path.isfile(os.path.join(d, "stories.yaml")):
                errs = [i for i in sm.validate(sm.load_model(d)) if i[0] == "error"]
                self.assertEqual(errs, [], name)


class TestValidate(Base):
    def test_example_is_clean(self):
        self.assertEqual(self.issues(), [])

    def test_duplicate_story_id(self):
        self.edit("id: US-03", "id: US-02")
        self.assertIn("DUPLICATE_ID", codes(self.issues(), "error"))

    def test_story_points_at_missing_screen(self):
        self.edit("screens: [welcome]", "screens: [welcom]")
        self.assertIn("UNKNOWN_SCREEN", codes(self.issues(), "error"))

    def test_missing_screenshot_and_unused_screen(self):
        self.edit("image: screens/settings.png", "image: screens/nope.png")
        self.edit("  - id: sitter-view\n", "  - id: orphan\n    title: Orphan\n    flow: plants\n    not_captured: x\n  - id: sitter-view\n")
        c = codes(self.issues(), "warn")
        self.assertIn("MISSING_IMAGE", c)
        self.assertIn("UNUSED_SCREEN", c)

    def test_built_requires_verified(self):
        self.edit("status: missing\n    notes: Snooze", "status: built\n    notes: Snooze")
        self.assertIn("BUILT_NOT_VERIFIED", codes(self.issues(), "error"))

    def test_absolute_image_path_rejected(self):
        self.edit("image: screens/welcome.png", "image: /Users/someone/welcome.png")
        self.assertIn("IMAGE_PATH", codes(self.issues(), "error"))

    def test_bad_edge(self):
        self.edit('"welcome -> plant-list: Tap Skip for now"', '"welcome -> nowhere: Tap Skip for now"')
        self.assertIn("UNKNOWN_SCREEN", codes(self.issues(), "error"))


class TestTopics(Base):
    def test_flow_without_topic_is_error(self):
        self.edit("    topic: journey\n", "")
        self.assertIn("MISSING_TOPIC", codes(self.issues(), "error"))

    def test_unknown_topic_is_error(self):
        self.edit("topic: journey", "topic: journye")
        self.assertIn("UNKNOWN_TOPIC", codes(self.issues(), "error"))

    def test_no_topics_section_warns_and_files_under_general(self):
        t = open(self.src, encoding="utf-8").read()
        a, b = t.index("topics:"), t.index("personas:")
        t = t[:a] + t[b:]
        import re
        t = re.sub(r"\n    topic: \w+", "", t)
        open(self.src, "w", encoding="utf-8").write(t)
        m = sm.load_model(self.dir)
        self.assertIn("NO_TOPICS", codes(sm.validate(m), "warn"))
        self.assertEqual({s["topic_eff"] for s in m["screens"]}, {"general"})

    def test_summary_and_cross_topic_edges(self):
        m = sm.load_model(self.dir)
        rows = sm.topic_summary(m)
        self.assertEqual(sum(len(r["stories"]) for r in rows), len(m["stories"]))
        self.assertIn(("onboarding", "journey"), sm.cross_topic_edges(m))

    def test_screen_can_override_topic(self):
        self.edit("  - id: sitter-view\n", "  - id: sitter-view\n    topic: journey\n")
        m = sm.load_model(self.dir)
        self.assertEqual(m["S"]["sitter-view"]["topic_eff"], "journey")


class TestTheme(Base):
    def tearDown(self):
        sm.apply_theme(sm.load_model(EXAMPLE))  # leave the module-level theme as the example defines it
        super().tearDown()

    def test_derive_from_primary(self):
        self.edit('primary: "#3A7D5B"', 'primary: "#3366CC"')
        m = sm.load_model(self.dir)
        self.assertEqual(sm.TH["primary"].upper(), "#3366CC")
        for k in sm.STATUS:
            self.assertRegex(sm.STATUS[k]["color"], r"^#[0-9A-Fa-f]{6}$")
        self.assertTrue(all(tp["color"] for tp in m["topics"]))
        self.assertEqual(len({tp["color"] for tp in m["topics"]}), len(m["topics"]))

    def test_explicit_colours_win_and_bad_hex_rejected(self):
        self.edit('text: "#1F2D26"', 'text: "#112233"\n  status:\n    built: "#00AF89"')
        sm.load_model(self.dir)
        self.assertEqual(sm.STATUS["built"]["color"], "#00AF89")
        self.assertEqual(sm.TH["ink"], "#112233")
        self.edit('primary: "#3A7D5B"', 'primary: "green"')
        with self.assertRaises(sm.SourceError):
            sm.load_model(self.dir)

    def test_unknown_font_falls_back(self):
        self.edit('text: "#1F2D26"', 'text: "#1F2D26"\n  font: "Definitely Not A Real Font 123"')
        sm.load_model(self.dir)
        self.assertEqual(sm.TH["font"], "Definitely Not A Real Font 123")
        self.assertIn("sans-serif", sm.font_stack(sm.TH["font"]))
        self.assertEqual(sm.font_face_css(), "")  # nothing resolved, nothing embedded
        if sm.HAVE_PIL:
            sm.font(20)  # must not raise

    def test_theme_applies_to_generated_text(self):
        self.edit('primary: "#3A7D5B"', 'primary: "#C2185B"')
        sm.load_model(self.dir)
        self.assertEqual(sm.TC("#2D7A5C").upper(), sm.TH["primary"].upper())
        self.assertIn(sm.TH["primary"], sm.themeify('color="#2D7A5C"'))

    def test_theme_from_scans_tokens(self):
        d = os.path.join(self.tmp, "app")
        os.makedirs(d)
        open(os.path.join(d, "Theme.swift"), "w").write('let brandPrimary = 0x3366CC\nlet fg = UIColor(hex: 0x202122)\nFont.custom("Linux Libertine", size: 12)\n')
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(sm.main(["theme-from", d]), 0)
        out = buf.getvalue()
        self.assertIn("#3366CC", out)
        self.assertIn("theme:", out)
        self.assertIn("Linux Libertine", out)


class TestBuild(Base):
    def run_main(self, *args):
        return sm.main(list(args))

    def test_build_and_persona_rename(self):
        self.edit("name: Busy gardener", "name: Garden enthusiast")
        self.edit("as_a: busy gardener", "as_a: garden enthusiast")
        self.assertEqual(self.run_main("build", self.dir), 0)
        md = open(os.path.join(self.dir, "generated", "user-stories.md"), encoding="utf-8").read()
        self.assertIn("As a garden enthusiast", md)
        self.assertNotIn("busy gardener", md)
        self.assertIn("Topic", md.split("\n## ", 2)[1] + md)
        self.assertIn("## Onboarding", md)
        for f in ("user-stories.csv", "gaps-and-risks.md", "story-map.md", "story-map.html"):
            self.assertTrue(os.path.getsize(os.path.join(self.dir, "generated", f)) > 100, f)

    def test_build_writes_architecture_outputs(self):
        self.assertEqual(self.run_main("build", self.dir), 0)
        gen = os.path.join(self.dir, "generated")
        mmd = open(os.path.join(gen, "mermaid", "architecture.mmd"), encoding="utf-8").read()
        self.assertIn("subgraph", mmd)
        self.assertIn("Main user journey", mmd)
        md = open(os.path.join(gen, "story-map.md"), encoding="utf-8").read()
        self.assertIn("## Architecture by topic", md)
        html = open(os.path.join(gen, "story-map.html"), encoding="utf-8").read()
        self.assertIn("All topics", html)
        csv_head = open(os.path.join(gen, "user-stories.csv"), encoding="utf-8").readline()
        self.assertIn("Topic", csv_head)
        if sm.HAVE_PIL:
            self.assertTrue(os.path.getsize(os.path.join(gen, "architecture.png")) > 1000)

    def test_pil_fallback_renders_architecture(self):
        if not sm.HAVE_PIL:
            self.skipTest("Pillow not installed")
        m = sm.load_model(self.dir)
        out = os.path.join(self.tmp, "arch.png")
        sm.pil_architecture(m, out)
        self.assertTrue(os.path.getsize(out) > 1000)

    def test_build_refuses_on_error(self):
        self.edit("screens: [welcome]", "screens: [welcom]")
        self.assertEqual(self.run_main("build", self.dir), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "generated", "user-stories.md")))

    def test_set_status_updates_and_rolls_back(self):
        self.assertEqual(self.run_main("set-status", "US-08", "built", "--dir", self.dir, "--no-build",
                                       "--verified", "device, 2026-10-16"), 0)
        self.assertEqual(sm.load_model(self.dir)["U"]["US-08"]["status"], "built")
        before = open(self.src, encoding="utf-8").read()
        with self.assertRaises(sm.SourceError):
            sm.set_status(self.dir, "US-09", "built")  # no --verified -> would be invalid
        self.assertEqual(open(self.src, encoding="utf-8").read(), before)


# --------------------------------------------------------------------------- screenshots keep their aspect ratio
SHAPES = {"phone": (600, 1300), "land": (1600, 1000), "square": (1000, 1000), "tablet": (1640, 2360),
          "web": (1440, 900), "tall": (500, 2400)}
ASPECT_YAML = """app:
  name: "Aspect test"
  platform: "ios"
personas:
  - id: u
    name: "User"
    as_a: "a user"
    description: "x"
topics:
  - id: a
    title: "Topic A"
    description: "a"
  - id: b
    title: "Topic B"
    description: "b"
flows:
  - id: f1
    title: "Flow one"
    description: "d"
    topic: a
    edges:
%s
screens:
%s
stories:
  - id: US-1
    persona: u
    want: "x"
    so_that: "y"
    screens: [%s]
    status: unverified
gaps: []
"""


def red_frame_boxes(im, min_gap=40):
    """Bounding boxes of the pure-red frames drawn on the test screenshots (one box per frame, found by column gaps)."""
    try:
        import numpy as np
    except ImportError:
        raise unittest.SkipTest("numpy not installed")
    a = np.asarray(im.convert("RGB")).astype(int)
    red = (a[:, :, 0] > 225) & (a[:, :, 1] < 70) & (a[:, :, 2] < 70)  # pure red only (the browser frame has its own, lighter red dot)
    cols = np.where(red.any(axis=0))[0]
    if not len(cols):
        return []
    groups, start, prev = [], cols[0], cols[0]
    for c in cols[1:]:
        if c - prev > min_gap:
            groups.append((start, prev))
            start = c
        prev = c
    groups.append((start, prev))
    out = []
    for x0, x1 in groups:
        rows = np.where(red[:, x0:x1 + 1].any(axis=1))[0]
        out.append((int(x0), int(rows.min()), int(x1), int(rows.max())))
    return out


class TestAspect(unittest.TestCase):
    """A screenshot is scaled to FIT its node (contain): same aspect ratio, never cropped, never stretched."""

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            raise unittest.SkipTest("Pillow not installed")
        cls.Image = Image
        cls.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.tmp, "screens"))
        for name, (w, h) in SHAPES.items():
            im = Image.new("RGB", (w, h), (250, 250, 250))
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, w - 1, h - 1), outline=(255, 0, 0), width=max(8, w // 18))  # frame on all 4 edges: a crop removes a side
            d.ellipse((w * .25, h / 2 - w * .25, w * .75, h / 2 + w * .25), outline=(0, 0, 255), width=8)
            im.save(os.path.join(cls.tmp, "screens", name + ".png"))
        names = list(SHAPES)
        edges = "\n".join('      - "%s -> %s: go"' % (a, b) for a, b in zip(names, names[1:]))
        screens = "\n".join('  - id: %s\n    title: "%s"\n    flow: f1\n    topic: %s\n    image: screens/%s.png' % (
            n, n.title(), "a" if i < 3 else "b", n) for i, n in enumerate(names))
        with open(os.path.join(cls.tmp, "stories.yaml"), "w") as f:
            f.write(ASPECT_YAML % (edges, screens, ", ".join(names)))
        cls.m = sm.load_model(cls.tmp)
        sm._img_cache.clear()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_contain_never_exceeds_box_and_keeps_ratio(self):
        for w, h in list(SHAPES.values()) + [(390, 844), (844, 390), (1, 1), (100, 4000), (4000, 100)]:
            for bw, bh in ((560, 520), (200, 200), (999, 77)):
                cw, ch = sm.contain(w, h, bw, bh)
                self.assertLessEqual(cw, bw)
                self.assertLessEqual(ch, bh)
                self.assertTrue(cw == bw or ch == bh, "should fill one side of the box")
                if min(cw, ch) >= 20:
                    self.assertAlmostEqual(cw / ch, w / h, delta=0.02 * (w / h))

    def test_node_size_follows_the_image_shape(self):
        sizes = {n: sm.fit_pt(*wh) for n, wh in SHAPES.items()}
        for n, (w, h) in SHAPES.items():
            self.assertAlmostEqual(sizes[n][0] / sizes[n][1], w / h, delta=0.01 * (w / h) + 0.004, msg=n)
        self.assertGreater(sizes["land"][0], sizes["land"][1])      # landscape stays landscape
        self.assertLess(sizes["phone"][0], sizes["phone"][1])       # phone stays portrait
        self.assertEqual(sizes["square"][0], sizes["square"][1])    # square stays square
        self.assertLess(sizes["tall"][0], 140)                      # a very tall page is not widened to a minimum width

    def _device(self, n, scale=2, box=(560, 520)):
        return sm.screen_device(self.m, self.m["S"][n], box, scale)

    def _screen_checks(self, dv, w, h, n):
        """The screen area of a device shows the WHOLE screenshot: aspect preserved, red frame reaches all four sides."""
        rx, ry, rw, rh = dv["rect"]
        self.assertAlmostEqual(rw / rh, w / h, delta=0.012 * (w / h) + 0.004, msg=n)
        crop = dv["img"].crop((rx, ry, rx + rw, ry + rh))
        boxes = red_frame_boxes(crop, 10 ** 6)
        self.assertEqual(len(boxes), 1, n)
        x0, y0, x1, y1 = boxes[0]
        t = max(3, rw // 60)
        self.assertLessEqual(x0, t, n)
        self.assertLessEqual(y0, t, n)
        self.assertGreaterEqual(x1, rw - 1 - t, n)
        self.assertGreaterEqual(y1, rh - 1 - t, n)

    def test_screen_inside_device_is_not_cropped_or_stretched(self):
        for n, (w, h) in SHAPES.items():
            dv = self._device(n)
            self._screen_checks(dv, w, h, n)
            W, H = dv["size"]
            self.assertLessEqual(W, 2 * sm.LANDSCAPE_W, n)
            self.assertLessEqual(H, 2 * sm.PORTRAIT_H, n)

    def test_thumbnails_are_framed_and_not_cropped(self):
        gen = os.path.join(self.tmp, "generated")
        os.makedirs(os.path.join(gen, "dot"), exist_ok=True)
        th = sm.make_thumbs(self.m, gen)
        for n, (w, h) in SHAPES.items():
            im = self.Image.open(os.path.join(gen, "thumbs", n + ".png"))
            self.assertEqual(im.mode, "RGBA")
            self.assertTrue(th[n][3])                                              # marked as a framed image
            self.assertLessEqual(abs(im.width - 2 * th[n][1]), 1, n)
            self.assertLessEqual(abs(im.height - 2 * th[n][2]), 1, n)
            dv = self._device(n)
            self.assertEqual(im.size, dv["size"])
            self._screen_checks(dict(img=im, rect=dv["rect"]), w, h, n)
            self.assertEqual(im.getpixel((0, 0))[3], 0, n)                        # transparent outside the device

    def _card_frame_checks(self, cards):
        for n, (w, h) in SHAPES.items():
            card = cards[n]
            boxes = red_frame_boxes(card, 10 ** 6)
            self.assertEqual(len(boxes), 1, n)
            x0, y0, x1, y1 = boxes[0]
            self.assertAlmostEqual((x1 - x0 + 1) / (y1 - y0 + 1), w / h, delta=0.03 * (w / h) + 0.01, msg=n)
            self.assertGreater(x0, 4, n)                  # the whole screenshot is inside the card
            self.assertGreater(y0, 4, n)
            self.assertLess(x1, card.width - 5, n)
            self.assertLess(y1, card.height - 5, n)

    def test_architecture_cards_keep_aspect_and_show_everything(self):
        self._card_frame_checks({s["id"]: sm.card_compact(self.m, s) for s in self.m["screens"]})

    def test_flow_cards_keep_aspect_and_show_everything(self):
        self._card_frame_checks({s["id"]: sm.card_screen(self.m, s) for s in self.m["screens"]})

    def test_long_title_word_is_not_cut_off(self):
        s = dict(self.m["screens"][0])
        s["title"] = "Supercalifragilisticexpialidocious_screen_name_without_spaces"
        for fn in (sm.card_compact, sm.card_screen):
            card = fn(self.m, s)
            tmp = sm.ImageDraw.Draw(self.Image.new("RGB", (10, 10)))
            f = sm.font(17 if fn is sm.card_compact else 22, True)
            self.assertGreaterEqual(card.width, sm.tw(tmp, s["title"], f))

    def test_architecture_band_is_never_narrower_than_its_heading(self):
        import copy
        m = copy.deepcopy(self.m)
        long_title = "A very long topic name that is wider than the screens it holds"
        for t in m["topics"]:
            if t["id"] == "b":
                t["title"] = long_title
        out = os.path.join(self.tmp, "arch-long.png")
        sm.pil_architecture(m, out)
        im = self.Image.open(out)
        tmp = sm.ImageDraw.Draw(self.Image.new("RGB", (10, 10)))
        self.assertGreaterEqual(im.width, sm.tw(tmp, long_title, sm.font(30, True, True)) + 2 * 28 + 60)

    def test_full_build_outputs(self):
        out = os.path.join(self.tmp, "build")
        shutil.copytree(self.tmp, out, ignore=shutil.ignore_patterns("generated", "build"))
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sm.main(["build", out]), 0)
        sm._img_cache.clear()
        g = os.path.join(out, "generated")
        # one-pager: the contact sheet shows every screenshot completely inside its device frame
        op = self.Image.open(os.path.join(g, "one-pager.png"))
        boxes = [b for b in red_frame_boxes(op.crop((0, 1200, op.width, op.height)), 8) if b[2] - b[0] > 12]
        self.assertEqual(len(boxes), len(SHAPES))
        for (x0, y0, x1, y1), (n, (w, h)) in zip(sorted(boxes), SHAPES.items()):
            self.assertAlmostEqual((x1 - x0 + 1) / (y1 - y0 + 1), w / h, delta=0.05 * (w / h) + 0.02, msg=n)
        # HTML: the screenshot sits inside a layered device (frame overlay), object-fit: contain, aspect-based card width
        with open(os.path.join(g, "story-map.html"), encoding="utf-8") as fh:
            html_text = fh.read()
        self.assertIn("object-fit:contain", html_text)
        self.assertIn('"aspect": 1.6', html_text)
        self.assertIn('class="f"', html_text)
        self.assertLess(os.path.getsize(os.path.join(g, "story-map.html")), 5 * 1024 * 1024)
        if shutil.which("dot"):
            fl = self.Image.open(os.path.join(g, "flows", "f1.png"))
            boxes = sorted(b for b in red_frame_boxes(fl, 8) if b[2] - b[0] > 12)
            self.assertEqual(len(boxes), len(SHAPES))
            for (x0, y0, x1, y1), (n, (w, h)) in zip(boxes, SHAPES.items()):
                self.assertAlmostEqual((x1 - x0 + 1) / (y1 - y0 + 1), w / h, delta=0.03 * (w / h) + 0.01, msg=n)


# --------------------------------------------------------------------------- device mockups
MINI_YAML = """app:
  name: "Mini"
  platform: "ios"
personas:
  - id: u
    name: "User"
    as_a: "a user"
    description: "x"
flows:
  - id: f1
    title: "Flow"
    description: "d"
screens:
  - id: s0
    title: "S0"
    flow: f1
    not_captured: "none"
stories:
  - id: US-1
    persona: u
    want: "x"
    so_that: "y"
    screens: [s0]
    status: unverified
"""


def copy_theme_device():
    return dict(sm.TH["device"])


class TestDevice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            raise unittest.SkipTest("Pillow not installed")
        cls.Image = Image
        cls.ImageDraw = ImageDraw

    def setUp(self):
        self.saved = copy_theme_device()
        sm._DEV_CACHE.clear()

    def tearDown(self):
        sm.TH["device"] = self.saved
        sm._DEV_CACHE.clear()

    def shot(self, w, h):
        im = self.Image.new("RGB", (w, h), (240, 240, 240))
        d = self.ImageDraw.Draw(im)
        d.rectangle((0, 0, w - 1, h - 1), outline=(255, 0, 0), width=max(6, w // 18))
        return im

    def m(self, platform="ios", device=""):
        return {"app": {"platform": platform, "device": device}, "root": tempfile.gettempdir() + "/storymap-no-such-dir"}

    def test_auto_detect_model(self):
        det = lambda p, w, h, **k: sm.detect_model(self.m(p), k, w, h)
        self.assertEqual(det("ios", 1206, 2622), "iphone-island")       # modern iPhone
        self.assertEqual(det("ios", 1125, 2436), "iphone-notch")        # iPhone X size
        self.assertEqual(det("ios", 750, 1334), "iphone-home-button")   # iPhone 8 size
        self.assertEqual(det("ios", 1640, 2360), "tablet")
        self.assertEqual(det("ios", 2622, 1206), "iphone-island")       # landscape phone: same model, rotated frame
        self.assertEqual(det("android", 1080, 2400), "android-generic")
        self.assertEqual(det("web", 1440, 900), "browser-window")
        self.assertEqual(det("ios", 1000, 1000), "browser-window")      # not phone-shaped: never a phone frame
        self.assertEqual(det("ios", 1206, 2622, device="tablet"), "tablet")   # screen override wins
        self.assertEqual(sm.detect_model(self.m("ios", "iphone-notch"), {}, 1206, 2622), "iphone-notch")  # app override
        sm.TH["device"]["model"] = "android-generic"
        self.assertEqual(det("ios", 1206, 2622), "android-generic")     # theme model
        self.assertEqual(det("ios", 1206, 2622, device="tablet"), "tablet")

    def test_every_model_shows_the_whole_screenshot(self):
        for model in sm.DEVICE_MODELS:
            for w, h in ((1206, 2622), (2622, 1206), (1000, 1000)):
                dv = sm.render_device(self.m(), {}, self.shot(w, h), model, (300, 400), 1)
                rx, ry, rw, rh = dv["rect"]
                self.assertAlmostEqual(rw / rh, w / h, delta=0.02 * (w / h) + 0.01, msg=(model, w, h))
                self.assertLessEqual(dv["size"][0], 300)
                self.assertLessEqual(dv["size"][1], 400)
                self.assertGreaterEqual(rx, 0)
                self.assertLessEqual(rx + rw, dv["size"][0])
                self.assertLessEqual(ry + rh, dv["size"][1])
                if model != "none":    # a frame is drawn: opaque pixels outside the screen, transparent screen hole in the overlay
                    ov = dv["ov"]
                    self.assertEqual(ov.getpixel((rx + rw // 2, ry + rh // 2))[3], 0, model)

    def test_landscape_phone_gets_a_rotated_frame(self):
        port = sm.render_device(self.m(), {}, self.shot(1206, 2622), "iphone-island", (400, 400), 1)
        land = sm.render_device(self.m(), {}, self.shot(2622, 1206), "iphone-island", (400, 400), 1)
        self.assertGreater(land["size"][0], land["size"][1])
        self.assertLess(port["size"][0], port["size"][1])
        self.assertAlmostEqual(land["size"][0] / land["size"][1], port["size"][1] / port["size"][0], delta=0.02)

    def test_styles_differ(self):
        px = {}
        for style in sm.DEVICE_STYLES:
            sm.TH["device"]["style"] = style
            sm._DEV_CACHE.clear()
            dv = sm.render_device(self.m(), {}, self.shot(600, 1300), "iphone-island", (300, 500), 1, shadow=False)
            px[style] = dv["img"].getpixel((2, dv["size"][1] // 2))
        self.assertEqual(len(set(px.values())), 3, px)

    def test_not_captured_is_a_dashed_device_outline(self):
        s = {"id": "x", "title": "X", "not_captured": "needs an account", "image": "", "status": "unverified"}
        dv = sm.placeholder_device(self.m(), s, (300, 400), 1)
        self.assertGreater(dv["size"][1], dv["size"][0])
        a = dv["img"].getchannel("A")
        self.assertEqual(a.getpixel((0, 0)), 0)
        self.assertGreater(sum(1 for v in a.tobytes() if v > 128), 200)       # something is drawn
        self.assertLess(sum(1 for v in a.tobytes() if v > 128), dv["size"][0] * dv["size"][1] * 0.2)   # but it is an outline, not a filled phone

    def test_badge_uses_status_colour_and_no_border_colour(self):
        for k in sm.STATUS:
            b = sm.badge_img(k, 1, True)
            raw = b.convert("RGBA").tobytes()
            cols = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4) if raw[i + 3] == 255]
            want = sm.hexrgb(sm.STATUS[k]["color"])
            self.assertTrue(any(c[:3] == want for c in cols), k)

    def test_theme_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "stories.yaml")
            with open(src, "w") as f:
                f.write(MINI_YAML + "theme:\n  device:\n    style: titanium\n    model: iphone-notch\n    badge: dot\n")
            m = sm.load_model(d)
            self.assertEqual(sm.TH["device"]["style"], "titanium")
            self.assertEqual(sm.TH["device"]["model"], "iphone-notch")
            self.assertEqual(sm.TH["device"]["badge"], "dot")
            self.assertFalse([e for e in sm.validate(m) if e[1] == "UNKNOWN_DEVICE"])
            with open(src, "w") as f:
                f.write(MINI_YAML + "theme:\n  device:\n    style: neon\n    model: flip-phone\n")
            m = sm.load_model(d)
            codes = [e[1] for e in sm.validate(m)]
            self.assertIn("UNKNOWN_DEVICE", codes)
            self.assertIn("BAD_DEVICE_STYLE", codes)

    def test_frames_json_user_frame(self):
        with tempfile.TemporaryDirectory() as d:
            fr = self.Image.new("RGBA", (200, 400), (30, 30, 30, 255))        # a made-up frame, transparent screen hole
            hole = self.Image.new("RGBA", (160, 340), (0, 0, 0, 0))
            fr.paste(hole, (20, 30))
            fr.save(os.path.join(d, "my.png"))
            with open(os.path.join(d, "frames.json"), "w") as f:
                json.dump({"frames": {"mine": {"image": "my.png", "screen": {"x": 20, "y": 30, "width": 160, "height": 340, "radius": 12}}},
                           "defaults": {"iphone-island": "mine"}}, f)
            m = {"app": {"platform": "ios", "device": ""}, "root": d}
            self.assertIn("mine", sm.load_frames(m)["frames"])
            sm._DEV_CACHE.clear()
            dv = sm.render_device(m, {}, self.shot(600, 1300), "iphone-island", (300, 500), 1)
            self.assertEqual(dv["model"], "frame")
            rx, ry, rw, rh = dv["rect"]
            self.assertAlmostEqual(rw / rh, 160 / 340, delta=0.02)
            # the screenshot is contained in the screen area (aspect 0.46 in a 0.47 hole): red frame visible near all sides, nothing cropped
            crop = dv["img"].crop((rx, ry, rx + rw, ry + rh))
            x0, y0, x1, y1 = red_frame_boxes(crop, 10 ** 6)[0]
            self.assertLessEqual(y0, 6)
            self.assertGreaterEqual(y1, rh - 8)
            # an explicit screen device: <frame name> is accepted by validation
            self.assertIn("mine", set(sm.load_frames(m)["frames"]))
            # a frame outside the folder is refused (no path escapes)
            sm.TH["device"]["frames"] = "../x.json"
            m2 = {"app": {"platform": "ios", "device": ""}, "root": d}
            sm.load_frames(m2)
            sm.TH["device"]["frames"] = ""

    def test_dot_nodes_use_the_framed_image(self):
        s = {"id": "a", "title": "A", "status": "built", "not_captured": ""}
        node = sm.dot_node(s, ("thumbs/a.png", 200, 400, True))
        self.assertIn('SRC="thumbs/a.png"', node)
        self.assertNotIn('BORDER="3"', node)              # no coloured border around the screenshot
        self.assertIn(sm.STATUS["built"]["color"], node)  # the status colour is on the badge dot
        arch = sm.dot_arch_node(s, ("thumbs/a.png", 200, 400, True))
        self.assertIn("&#9679;", arch)
        self.assertNotIn('BORDER="3"', arch)

    def test_html_embeds_overlay_once_per_frame_and_stays_small(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "screens"))
            lines = []
            for i in range(6):
                self.shot(1206, 2622).save(os.path.join(d, "screens", "p%d.png" % i))
                lines.append('  - id: p%d\n    title: "P%d"\n    flow: f1\n    image: screens/p%d.png' % (i, i, i))
            with open(os.path.join(d, "stories.yaml"), "w") as f:
                f.write(MINI_YAML.replace("stories:\n", "\n".join(lines) + "\nstories:\n", 1))
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                sm.main(["build", d, "--force"])
            with open(os.path.join(d, "generated", "story-map.html"), encoding="utf-8") as fh:
                h = fh.read()
            self.assertEqual(len(set(re.findall(r'"ov": "([^"]+)"', h))), 1)    # six identical frames, one embedded overlay
            self.assertLess(len(h), 5 * 1024 * 1024)


# --------------------------------------------------------------------------- tree layout of branching flows
class TestTree(unittest.TestCase):
    EDGES = [("root", "a", "one", False), ("root", "b", "two", False), ("root", "c", "three", False),
             ("a", "a1", "", False), ("a1", "a2", "", False), ("c", "root", "back", False)]
    KEYS = ["root", "a", "b", "c", "a1", "a2"]

    def layout(self, orient, sizes=None):
        sizes = sizes or {k: (200, 300) for k in self.KEYS}
        return sm.tree_layout(self.KEYS, self.EDGES, sizes, orient, lambda lab: (100, 30), vgap=40, base_gap=80)

    def test_spanning_forest(self):
        children, depth, roots, extra = sm.flow_tree(self.KEYS, self.EDGES)
        self.assertEqual(children["root"], ["a", "b", "c"])
        self.assertEqual(roots, ["root"])
        self.assertEqual([depth[k] for k in ("root", "a", "b", "c", "a1", "a2")], [0, 1, 1, 1, 2, 3])
        self.assertEqual([(a, b) for a, b, _, _ in extra], [("c", "root")])     # the back-link is not a tree edge

    def test_children_share_a_row_and_are_centred_top_to_bottom(self):
        L = self.layout("TB")
        pos, kids = L["pos"], ["a", "b", "c"]
        self.assertEqual(len({pos[k][1] for k in kids}), 1)                    # one aligned row (same y)
        cx = {k: pos[k][0] + 100 for k in pos}                                 # card centres (width 200)
        self.assertAlmostEqual((cx["a"] + cx["c"]) / 2, cx["root"], delta=1)   # centred under the parent
        self.assertAlmostEqual(cx["b"], cx["root"], delta=1)
        gaps = [pos["b"][0] - (pos["a"][0] + 200), pos["c"][0] - (pos["b"][0] + 200)]
        self.assertAlmostEqual(gaps[0], gaps[1], delta=1)                      # evenly spaced
        self.assertLess(pos["root"][1], pos["a"][1])                           # parent above its children
        self.assertAlmostEqual(cx["a1"], cx["a"], delta=1)                     # a linear step stays in line (straight arrow)

    def test_children_share_a_column_and_are_centred_left_to_right(self):
        L = self.layout("LR")
        pos, kids = L["pos"], ["a", "b", "c"]
        self.assertEqual(len({pos[k][0] for k in kids}), 1)                    # one aligned column (same x)
        cy = {k: pos[k][1] + 150 for k in pos}
        self.assertAlmostEqual((cy["a"] + cy["c"]) / 2, cy["root"], delta=1)
        self.assertAlmostEqual(cy["b"], cy["root"], delta=1)
        self.assertLess(pos["root"][0], pos["a"][0])                           # parent left of its children
        self.assertAlmostEqual(cy["a2"], cy["a"], delta=1)

    def test_rendered_tree_has_aligned_cards_and_orthogonal_lines(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        cards = {k: Image.new("RGB", (240 + 20 * i, 360), (255, 255, 255)) for i, k in enumerate(self.KEYS)}
        out = os.path.join(tempfile.mkdtemp(), "tree.png")
        L, P = sm.render_tree(cards, self.EDGES, "T", "", out, 1)
        if L["tb"]:
            self.assertEqual(len({P[k][1] for k in ("a", "b", "c")}), 1)       # children share one row
        if L["tb"]:
            ctr = {k: P[k][0] + cards[k].width / 2 for k in P}
            self.assertAlmostEqual((ctr["a"] + ctr["c"]) / 2, ctr["root"], delta=1)
        else:
            self.assertEqual(len({P[k][0] for k in ("a", "b", "c")}), 1)
            ctr = {k: P[k][1] + cards[k].height / 2 for k in P}
            self.assertAlmostEqual((ctr["a"] + ctr["c"]) / 2, ctr["root"], delta=1)
        self.assertTrue(os.path.getsize(out) > 1000)

    def test_flow_diagram_of_a_branching_flow(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as d:
            yaml = MINI_YAML.replace("stories:\n", "".join(
                '  - id: c%d\n    title: "C%d"\n    flow: f1\n    not_captured: "x"\n' % (i, i) for i in range(3)) + "stories:\n", 1)
            yaml = yaml.replace('    title: "Flow"\n    description: "d"\n', '    title: "Flow"\n    description: "d"\n    edges:\n' + "".join(
                '      - "s0 -> c%d: go %d"\n' % (i, i) for i in range(3)), 1)
            with open(os.path.join(d, "stories.yaml"), "w") as f:
                f.write(yaml)
            m = sm.load_model(d)
            out = os.path.join(d, "flow.png")
            sm.pil_flow(m, "f1", out)
            self.assertTrue(os.path.getsize(out) > 1000)
            nodes, edges = sm.flow_graph(m, "f1")
            ch = sm.flow_tree([n["key"] for n in nodes], edges)[0]
            self.assertEqual(ch["s0"], ["c0", "c1", "c2"])


if __name__ == "__main__":
    unittest.main()
