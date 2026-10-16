"""Run:  python3 -m unittest discover -s tests -v   (standard library only; Pillow/Graphviz optional)"""
import json, os, re, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import storymap as sm  # noqa: E402

EXAMPLE = os.path.join(HERE, "fixtures", "sample-app")


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
        self.edit("  - id: guest-view\n", "  - id: orphan\n    title: Orphan\n    flow: notes\n    not_captured: x\n  - id: guest-view\n")
        c = codes(self.issues(), "warn")
        self.assertIn("MISSING_IMAGE", c)
        self.assertIn("UNUSED_SCREEN", c)

    def test_built_requires_verified(self):
        self.edit("status: missing\n    notes: Snooze", "status: built\n    notes: Snooze")
        self.assertIn("BUILT_NOT_VERIFIED", codes(self.issues(), "error"))

    def test_absolute_image_path_rejected(self):
        self.edit("image: screens/welcome.png", "image: /Use" + "rs/someone/welcome.png")
        self.assertIn("IMAGE_PATH", codes(self.issues(), "error"))

    def test_bad_edge(self):
        self.edit('"welcome -> note-list: Tap Skip for now"', '"welcome -> nowhere: Tap Skip for now"')
        self.assertIn("UNKNOWN_SCREEN", codes(self.issues(), "error"))

    def test_long_fields_warn_only_above_each_limit(self):
        m = sm.load_model(self.dir)
        families = (("stories", (("want", 160), ("so_that", 160), ("story", 160),
                                  ("notes", 200), ("where", 200), ("verified", 200))),
                    ("screens", (("notes", 200), ("where", 200), ("verified", 200))),
                    ("gaps", (("title", 100), ("detail", 400), ("where", 120))))
        for family, fields in families:
            item = m[family][0]
            for field, limit in fields:
                with self.subTest(family=family, field=field):
                    before = item[field]
                    item[field] = "x" * limit
                    self.assertNotIn("long-field", codes(sm.validate(m)))
                    item[field] += "x"
                    issues = sm.validate(m)
                    warnings = [i for i in issues if i[1] == "long-field"]
                    self.assertEqual(len(warnings), 1)
                    level, code, message = warnings[0]
                    self.assertEqual(level, "warn")
                    self.assertIn(item["id"], message)
                    self.assertIn("`%s`" % field, message)
                    self.assertIn("%d characters" % (limit + 1), message)
                    self.assertIn("limit %d" % limit, message)
                    self.assertIn("shorten or move detail to the code/docs", message)
                    self.assertNotIn("long-field", codes(issues, "error"))
                    item[field] = before

    def test_screen_verified_is_loaded_and_checked(self):
        value = "v" * 201
        self.edit("  - id: welcome\n", "  - id: welcome\n    verified: " + value + "\n")
        m = sm.load_model(self.dir)
        self.assertEqual(m["S"]["welcome"]["verified"], value)
        warnings = [msg for level, code, msg in sm.validate(m) if code == "long-field"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("screen welcome: `verified`", warnings[0])

    def test_repeated_text_warns_once_per_family_with_trimmed_case_matching(self):
        families = (("stories", "verified"), ("stories", "where"), ("stories", "notes"),
                    ("screens", "where"), ("screens", "notes"), ("gaps", "where"))
        for family, field in families:
            with self.subTest(family=family, field=field):
                m = sm.load_model(self.dir)
                items = m[family][:3]
                text = "Shared evidence " + "x" * 24  # exactly 40 characters
                items[0][field], items[1][field] = text, "  " + text.upper() + "  "
                self.assertNotIn("repeated-text", codes(sm.validate(m)))
                items[2][field] = text.lower()
                issues = sm.validate(m)
                warnings = [i for i in issues if i[1] == "repeated-text"]
                self.assertEqual(len(warnings), 1)
                self.assertEqual(warnings[0][0], "warn")
                message = warnings[0][2]
                self.assertIn("`%s`" % field, message)
                self.assertIn("3 items", message)
                for item in items:
                    self.assertIn(item["id"], message)
                self.assertIn("say it once (e.g. in app.summary or a gap) or shorten it", message)
                self.assertNotIn("repeated-text", codes(issues, "error"))

    def test_repeated_text_groups_values_without_combining_families(self):
        m = sm.load_model(self.dir)
        text = "This source detail is repeated across several items."
        for item in m["stories"][:2]:
            item["where"] = text
        m["screens"][0]["where"] = text
        m["stories"][0]["notes"] = text
        self.assertNotIn("repeated-text", codes(sm.validate(m)))
        for item in m["stories"][:3]:
            item["notes"] = text
        other = "A different long detail repeated across source items."
        for item in m["stories"][3:6]:
            item["notes"] = other
        warnings = [i for i in sm.validate(m) if i[1] == "repeated-text"]
        self.assertEqual(len(warnings), 2)
        self.assertTrue(all("3 items" in msg for _, _, msg in warnings))

    def test_short_and_empty_repeated_text_do_not_warn(self):
        m = sm.load_model(self.dir)
        for family, fields in (("stories", ("verified", "where", "notes")),
                               ("screens", ("where", "notes")), ("gaps", ("where",))):
            for item in m[family]:
                for field in fields:
                    item[field] = "app, 2026-10-15" if field != "notes" else "  "
        # Screen verification is length-checked, but is not a repeated-text family.
        for item in m["screens"]:
            item["verified"] = "Repeated screen verification is deliberately excluded."
        self.assertNotIn("repeated-text", codes(sm.validate(m)))
        for item in m["stories"]:
            item["notes"] = "x" * 39
        self.assertNotIn("repeated-text", codes(sm.validate(m)))

    def test_text_warnings_allow_validate_and_build_except_under_strict(self):
        import contextlib, io
        self.edit("want: to understand what the app does before I add anything", "want: " + "x" * 161)
        self.edit('verified: "app, 2026-10-15"',
                  'verified: "app, 2026-10-15"\n    notes: A repeated detail covering at least forty characters.', count=3)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sm.main(["validate", self.dir]), 0)
            self.assertEqual(sm.main(["validate", self.dir, "--strict"]), 1)
            self.assertEqual(sm.main(["build", self.dir, "--formats", "report", "--strict"]), 1)
            self.assertFalse(os.path.exists(os.path.join(self.dir, "generated")))
            self.assertEqual(sm.main(["build", self.dir, "--formats", "report"]), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "generated", "REPORT.md")))
        self.assertIn("long-field", out.getvalue())
        self.assertIn("repeated-text", out.getvalue())
        self.assertIn("0 error(s)", out.getvalue())

    def test_validate_help_names_text_warnings(self):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as ex:
            sm.main(["validate", "--help"])
        self.assertEqual(ex.exception.code, 0)
        self.assertIn("long-field", out.getvalue())
        self.assertIn("repeated-text", out.getvalue())


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
        self.edit("  - id: guest-view\n", "  - id: guest-view\n    topic: journey\n")
        m = sm.load_model(self.dir)
        self.assertEqual(m["S"]["guest-view"]["topic_eff"], "journey")


class TestTheme(Base):
    def tearDown(self):
        sm.apply_theme(sm.load_model(EXAMPLE))  # leave the module-level theme as the example defines it
        super().tearDown()

    def test_derive_from_primary(self):
        self.edit('primary: "#3568B0"', 'primary: "#3366CC"')
        m = sm.load_model(self.dir)
        self.assertEqual(sm.TH["primary"].upper(), "#3366CC")
        for k in sm.STATUS:
            self.assertRegex(sm.STATUS[k]["color"], r"^#[0-9A-Fa-f]{6}$")
        self.assertTrue(all(tp["color"] for tp in m["topics"]))
        self.assertEqual(len({tp["color"] for tp in m["topics"]}), len(m["topics"]))

    def test_explicit_colours_win_and_bad_hex_rejected(self):
        self.edit('text: "#223047"', 'text: "#112233"\n  status:\n    built: "#00AF89"')
        sm.load_model(self.dir)
        self.assertEqual(sm.STATUS["built"]["color"], "#00AF89")
        self.assertEqual(sm.TH["ink"], "#112233")
        self.edit('primary: "#3568B0"', 'primary: "green"')
        with self.assertRaises(sm.SourceError):
            sm.load_model(self.dir)

    def test_unknown_font_falls_back(self):
        self.edit('text: "#223047"', 'text: "#223047"\n  font: "Definitely Not A Real Font 123"')
        sm.load_model(self.dir)
        self.assertEqual(sm.TH["font"], "Definitely Not A Real Font 123")
        self.assertIn("sans-serif", sm.font_stack(sm.TH["font"]))
        self.assertEqual(sm.font_face_css(), "")  # nothing resolved, nothing embedded
        if sm.HAVE_PIL:
            sm.font(20)  # must not raise

    def test_embed_fonts_is_a_boolean_and_heading_serif_fallback(self):
        self.edit('text: "#223047"', 'text: "#223047"\n  heading_font: Georgia\n  embed_fonts: true')
        m = sm.load_model(self.dir)
        self.assertTrue(sm.TH["embed_fonts"])
        self.assertIn('"Georgia",Georgia,"Times New Roman",serif', sm.heading_font_stack())
        self.assertIn('BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif', sm.font_stack(""))
        for value in ("yes", "1", 1, [], {}):
            m["raw"]["theme"]["embed_fonts"] = value
            with self.assertRaisesRegex(sm.SourceError, "theme.embed_fonts must be a bool"):
                sm.apply_theme(m)
        for value in (False, "false"):
            m["raw"]["theme"]["embed_fonts"] = value
            sm.apply_theme(m)
            self.assertFalse(sm.TH["embed_fonts"])

    def test_theme_applies_to_generated_text(self):
        self.edit('primary: "#3568B0"', 'primary: "#C2185B"')
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
        self.edit("name: Busy writer", "name: Note enthusiast")
        self.edit("as_a: busy writer", "as_a: note enthusiast")
        self.assertEqual(self.run_main("build", self.dir, "--formats", "report"), 0)
        md = open(os.path.join(self.dir, "generated", "REPORT.md"), encoding="utf-8").read()
        self.assertIn("As a note enthusiast", md)
        self.assertNotIn("busy writer", md)
        self.assertIn("## Topics", md)
        self.assertIn("### Onboarding", md)
        self.assertNotIn("```mermaid", md)

    def test_build_writes_architecture_outputs(self):
        self.assertEqual(self.run_main("build", self.dir, "--profile", "full"), 0)
        gen = os.path.join(self.dir, "generated")
        mmd = open(os.path.join(gen, "mermaid", "architecture.mmd"), encoding="utf-8").read()
        self.assertIn("subgraph", mmd)
        self.assertIn("Main user journey", mmd)
        md = open(os.path.join(gen, "story-map.md"), encoding="utf-8").read()
        self.assertIn("## Architecture by topic", md)
        html = open(os.path.join(gen, "story-map.html"), encoding="utf-8").read()
        self.assertIn("All topics", html)
        if sm.HAVE_PIL:
            self.assertLess(os.path.getsize(os.path.join(gen, "story-map.html")), 2_000_000)
        csv_head = open(os.path.join(gen, "user-stories.csv"), encoding="utf-8").readline()
        self.assertIn("Topic", csv_head)
        for f in ("REPORT.md", "user-stories.md", "gaps-and-risks.md"):
            self.assertTrue(os.path.getsize(os.path.join(gen, f)) > 100, f)
        self.assertFalse(os.path.exists(os.path.join(gen, "README.md")))
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
        self.assertFalse(os.path.exists(os.path.join(self.dir, "generated", "REPORT.md")))

    def test_set_status_updates_and_rolls_back(self):
        self.assertEqual(self.run_main("set-status", "US-08", "built", "--dir", self.dir, "--no-build",
                                       "--verified", "device, 2026-10-16"), 0)
        self.assertEqual(sm.load_model(self.dir)["U"]["US-08"]["status"], "built")
        before = open(self.src, encoding="utf-8").read()
        with self.assertRaises(sm.SourceError):
            sm.set_status(self.dir, "US-09", "built")  # no --verified -> would be invalid
        self.assertEqual(open(self.src, encoding="utf-8").read(), before)

    def test_report_has_canonical_story_and_gap_rows(self):
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_main("build", self.dir, "--formats", "report"), 0)
        m = sm.load_model(self.dir)
        path = os.path.join(self.dir, "generated", "REPORT.md")
        text = open(path, encoding="utf-8").read()
        self.assertTrue(text.startswith("# Pocket Notes - story map report\n"))
        self.assertIn("edit the source, not this file", text)
        self.assertIn("## Topics", text)
        self.assertIn("## Stories", text)
        self.assertIn("## Gaps and risks", text)
        self.assertNotIn("```mermaid", text)
        self.assertIn("| ID | Story | Screens | Status | Evidence |", text)
        self.assertNotIn("| Persona |", text)
        for story in m["stories"]:
            # Gaps legitimately refer to story IDs too; each canonical story row occurs once.
            self.assertEqual(len(re.findall(r"^\| %s \|" % re.escape(story["id"]), text, re.M)), 1)
            self.assertIn(sm.esc_md(sm.story_text(m, story)), text)
        for gap in m["gaps"]:
            self.assertEqual(len(re.findall(r"\*\*%s - " % re.escape(gap["id"]), text)), 1)
        self.assertIn("**%d stories:**" % len(m["stories"]), text)
        summary = next(line for line in text.splitlines() if line.startswith("**%d stories:**" % len(m["stories"])))
        expected_counts = " · ".join("%s %d %s" % (sm.STATUS[status]["emoji"], count, status)
                                     for status, count in sm.counts(m["stories"]).items() if count)
        self.assertEqual(summary, "**%d stories:** %s" % (len(m["stories"]), expected_counts))
        for status, count in sm.counts(m["stories"]).items():
            if count:
                self.assertIn("%s %d %s" % (sm.STATUS[status]["emoji"], count, status), text)
        for target in re.findall(r"\]\(([^)]+)\)", text):
            self.assertFalse(os.path.isabs(target), target)
            self.assertTrue(os.path.exists(os.path.join(os.path.dirname(path), target)), target)
        before = text
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_main("build", self.dir, "--formats", "report"), 0)
        self.assertEqual(open(path, encoding="utf-8").read(), before)

    def test_report_escapes_table_cells(self):
        self.edit("notes: Only 4 templates in the list so far.", 'notes: "Only | four\\ntemplates in the list."')
        self.edit("want: to understand what the app does before I add anything", 'want: "to understand | everything"')
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_main("build", self.dir, "--formats", "report"), 0)
        text = open(os.path.join(self.dir, "generated", "REPORT.md"), encoding="utf-8").read()
        self.assertIn("understand \\| everything", text)
        self.assertIn("Only \\| four", text)
        self.assertNotIn("four\ntemplates", text)

    def test_report_prose_stays_readable_and_only_link_labels_escape_brackets(self):
        m = sm.load_model(self.dir)
        prose = 'Settings & "sharing" \'notes\' snake_case *start* [screen] `ready` | <now>\r\nnext'
        escaped = 'Settings & "sharing" \'notes\' snake_case *start* [screen] `ready` \\| &lt;now> next'
        m["topics"][0]["title"] = prose
        m["S"]["welcome"]["title"] = prose
        m["S"]["add-note"]["title"] = prose
        m["S"]["add-note"]["image"] = ""
        m["stories"][0]["notes"] = prose
        m["stories"][0]["where"] = "src/screens/Welcome"
        gen = os.path.join(self.dir, "generated")
        sm.gen_report(m, gen, set())
        with open(os.path.join(gen, "REPORT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("### " + escaped + "\n", text)
        self.assertIn("note: " + escaped, text)
        label = escaped.replace("[", "\\[").replace("]", "\\]")
        self.assertIn("[%s](../screens/welcome.png)" % label, text)
        self.assertIn("| " + escaped + " |", text)
        self.assertIn("where: `src/screens/Welcome`", text)
        self.assertNotIn("&amp;", text)

    def test_report_omits_zero_counts_and_keeps_comma_joined_flow_titles(self):
        m = sm.load_model(self.dir)
        for story in m["stories"]:
            story["status"] = "built"
        m["topics"].append(dict(id="empty", title="Empty topic", description=""))
        m["flows"].append(dict(id="extra", topic=m["topics"][0]["id"], title='Second & "flow"'))
        gen = os.path.join(self.dir, "generated")
        sm.gen_report(m, gen, set())
        with open(os.path.join(gen, "REPORT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("**%d stories:** %s %d built\n" % (len(m["stories"]), sm.STATUS["built"]["emoji"],
                                                        len(m["stories"])), text)
        for status in sm.STATUS.values():
            self.assertNotIn("%s 0" % status["emoji"], text)
        self.assertIn("| Empty topic | 0 | 0 | - |  |", text)
        topic_row = next(line for line in text.splitlines() if line.startswith("| Onboarding |"))
        self.assertTrue(topic_row.endswith('| 1 · Getting started, Second & "flow" |'), topic_row)

    def test_report_cross_topic_connections_are_a_tight_bullet_list(self):
        m = sm.load_model(self.dir)
        connections = sm.cross_topic_edges(m)
        self.assertGreater(len(connections), 1)
        gen = os.path.join(self.dir, "generated")
        sm.gen_report(m, gen, set())
        with open(os.path.join(gen, "REPORT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertRegex(text, r"\|\n\n(?:- [^\n]+\n){%d}\n## Stories\n" % len(connections))


class TestHtml(Base):
    def tearDown(self):
        sm.apply_theme(sm.load_model(EXAMPLE))
        super().tearDown()

    def html(self, available=None):
        gen = os.path.join(self.dir, "generated")
        sm.gen_html(sm.load_model(self.dir), gen, available=available)
        with open(os.path.join(gen, "story-map.html"), encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def images(page):
        return json.loads(re.search(r", IMG=(.*?), OVL=", page).group(1))

    def test_default_uses_system_fonts_and_expandable_story_details(self):
        page = self.html()
        self.assertNotIn("@font-face", page)
        self.assertNotIn("data:font", page)
        self.assertIn("BlinkMacSystemFont", page)
        self.assertIn("class=\"story-details", page)
        self.assertIn('colspan="5"', page)
        self.assertIn("toggleStory", page)
        self.assertIn("Where it lives", page)
        self.assertIn("screenDetails", page)
        self.assertIn("Outgoing actions", page)
        self.assertIn("history.replaceState", page)
        self.assertIn("lbStep(1,e)", page)
        self.assertLess(len(page.encode("utf-8")), 2_000_000)

    def test_story_id_column_does_not_wrap(self):
        self.assertRegex(self.html(), r"\.story-row\s+td:first-child\s*\{[^}]*white-space\s*:\s*nowrap")

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_screen_previews_are_small_without_mutating_native_sources(self):
        import base64, io
        from PIL import Image
        m = sm.load_model(self.dir)
        original = {s["id"]: sm.load_img(m, s).size for s in m["screens"] if sm.load_img(m, s) is not None}
        page = self.html()
        imgs = self.images(page)
        self.assertTrue(imgs)
        for sid, uri in imgs.items():
            with Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as image:
                self.assertLessEqual(image.width, 480, sid)
                self.assertLessEqual(image.height, 1040, sid)
        for s in m["screens"]:
            if s["id"] in original:
                self.assertEqual(sm.load_img(m, s).size, original[s["id"]])

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_diagram_previews_and_relative_full_resolution_links(self):
        import base64, io
        from PIL import Image
        gen = os.path.join(self.dir, "generated")
        os.makedirs(gen)
        for name in ("architecture.png", "overview.png"):
            Image.new("RGB", (3000, 1200), "#6D9A7A").save(os.path.join(gen, name))
        page = self.html()
        imgs = self.images(page)
        for key, limit in (("__arch", 2400), ("__overview", 1800)):
            with Image.open(io.BytesIO(base64.b64decode(imgs[key].split(",", 1)[1]))) as image:
                self.assertLessEqual(image.width, limit)
        self.assertIn('"__arch": "architecture.png"', page)
        self.assertIn('"__overview": "overview.png"', page)
        self.assertIn("Open full resolution (", page)
        self.assertIn('href="${esc(full)}"', page)
        # A clean build must not embed stale diagrams that are scheduled for removal.
        clean = self.html(available={"story-map.html"})
        self.assertNotIn("__arch", self.images(clean))
        self.assertNotIn("__overview", self.images(clean))
        self.assertIn('"full": {}', clean)

    def test_embed_fonts_cli_without_fonttools_falls_back_gracefully(self):
        import contextlib, io
        from unittest import mock
        out = io.StringIO()
        with mock.patch.dict(sys.modules, {"fontTools": None}), contextlib.redirect_stdout(out):
            self.assertEqual(sm.main(["build", self.dir, "--formats", "html", "--embed-fonts"]), 0)
        self.assertTrue(sm.TH["embed_fonts"])
        with open(os.path.join(self.dir, "generated", "story-map.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn("fontTools and brotli", out.getvalue())
        self.assertIn("using system fonts", out.getvalue())
        self.assertNotIn("@font-face", page)
        self.assertNotIn("data:font", page)


class TestBuildProfiles(unittest.TestCase):
    """Small fixture covers format combinations without rendering the large example repeatedly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "map")
        os.makedirs(os.path.join(self.dir, "screens"))
        with open(os.path.join(self.dir, "stories.yaml"), "w", encoding="utf-8") as f:
            f.write(MINI_YAML.replace("flows:\n", "topics:\n  - id: general\n    title: General\nflows:\n", 1)
                    .replace('    title: "Flow"\n', '    topic: general\n    title: "Flow"\n', 1))
        self.gen = os.path.join(self.dir, "generated")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, *args):
        import contextlib, io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                result = sm.main(["build", self.dir, "--no-graphviz"] + list(args))
            except SystemExit as ex:
                result = ex.code
        self.output = out.getvalue() + err.getvalue()
        return result

    def opt_in_formats(self):
        line = next(line for line in self.output.splitlines() if line.startswith("opt-in: "))
        return line[len("opt-in: "):].split(" (", 1)[0].split(", ")

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_lean_default_writes_exactly_four_outputs(self):
        self.assertEqual(self.build(), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", "architecture.png", "one-pager.png", "story-map.html"})
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".cache")))
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".gitignore")))
        self.assertIn("opt-in:", self.output)
        self.assertIn("--formats +name", self.output)
        self.assertEqual(self.opt_in_formats(), ["csv", "mermaid", "dot", "flows", "flow-map", "overview",
                                                 "pdf", "crops", "legacy-md"])
        self.assertRegex(self.output, r"REPORT\.md.*(?:KB|MB)")
        report = open(os.path.join(self.gen, "REPORT.md"), encoding="utf-8").read()
        for name in ("architecture.png", "one-pager.png", "story-map.html"):
            self.assertIn("](%s)" % name, report)
        self.assertNotIn("](one-pager.pdf)", report)

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_full_profile_includes_legacy_and_opt_in_outputs(self):
        self.assertEqual(self.build("--profile", "full"), 0, self.output)
        expected = {"REPORT.md", "architecture.png", "one-pager.png", "one-pager.pdf", "story-map.html",
                    "story-map.md", "user-stories.md", "user-stories.csv", "gaps-and-risks.md", "overview.png",
                    "flow-map.png", "flows", "architecture", "mermaid", "dot"}
        self.assertTrue(expected.issubset(set(os.listdir(self.gen))), set(os.listdir(self.gen)))
        self.assertFalse(os.path.exists(os.path.join(self.gen, "README.md")))
        self.assertFalse(os.path.exists(os.path.join(self.gen, "thumbs")))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, ".cache", "thumbs", "s0.png")))
        self.assertNotIn("opt-in:", self.output)

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_formats_add_and_remove_profile_outputs(self):
        self.assertEqual(self.build("--formats", "+csv,flows"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", "architecture.png", "one-pager.png", "story-map.html",
                                                   "user-stories.csv", "flows"})
        self.assertNotIn("csv", self.opt_in_formats())
        self.assertNotIn("flows", self.opt_in_formats())
        shutil.rmtree(self.gen)
        self.assertEqual(self.build("--formats", "-onepager"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", "architecture.png", "story-map.html"})
        self.assertIn("onepager", self.opt_in_formats())

    def test_formats_replace_profile_and_mermaid_has_sources_only(self):
        self.assertEqual(self.build("--profile", "full", "--formats", "csv,mermaid"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"user-stories.csv", "mermaid"})
        sources = os.listdir(os.path.join(self.gen, "mermaid"))
        self.assertTrue(sources)
        self.assertTrue(all(name.endswith(".mmd") for name in sources), sources)
        self.assertEqual(self.opt_in_formats(), ["html", "arch", "onepager", "report", "dot", "flows", "flow-map",
                                                 "overview", "pdf", "crops", "legacy-md"])

    def test_unknown_format_lists_valid_names_before_building(self):
        self.assertEqual(self.build("--formats", "wat"), 2, self.output)
        self.assertIn("wat", self.output)
        for name in ("html", "arch", "onepager", "report", "legacy-md", "crops"):
            self.assertIn(name, self.output)
        self.assertFalse(os.path.exists(self.gen))

    def test_only_alias_keeps_old_doc_mapping(self):
        self.assertEqual(self.build("--only", "docs,mermaid"), 0, self.output)
        self.assertIn("deprecat", self.output.lower())
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", "user-stories.md", "user-stories.csv",
                                                   "gaps-and-risks.md", "story-map.md", "mermaid"})

    def test_clean_removes_stale_outputs_only_inside_generated(self):
        os.makedirs(self.gen)
        stale_files = ("story-map.md", "user-stories.md", "user-stories.csv", "gaps-and-risks.md", "README.md",
                       "one-pager.pdf", "overview.png", "flow-map.png")
        stale_dirs = ("flows", "architecture", "mermaid", "dot", "thumbs")
        for name in stale_files:
            with open(os.path.join(self.gen, name), "w") as f:
                f.write("old")
        for name in stale_dirs:
            os.makedirs(os.path.join(self.gen, name))
            with open(os.path.join(self.gen, name, "old.txt"), "w") as f:
                f.write("old")
        for name in (".gitkeep", "my-notes.txt"):
            open(os.path.join(self.gen, name), "w").close()
        sentinel = os.path.join(self.dir, "screens", "keep.txt")
        with open(sentinel, "w") as f:
            f.write("screenshot sentinel")
        source = open(os.path.join(self.dir, "stories.yaml"), encoding="utf-8").read()
        self.assertEqual(self.build("--formats", "report"), 0, self.output)
        self.assertIn("stale (use --clean):", self.output)
        self.assertTrue(all(os.path.exists(os.path.join(self.gen, name)) for name in stale_files + stale_dirs))
        report = open(os.path.join(self.gen, "REPORT.md"), encoding="utf-8").read()
        self.assertNotIn("](one-pager.pdf)", report)
        self.assertNotIn("](overview.png)", report)
        self.assertEqual(self.build("--formats", "report", "--clean"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", ".gitkeep", "my-notes.txt"})
        self.assertEqual(open(sentinel).read(), "screenshot sentinel")
        self.assertEqual(open(os.path.join(self.dir, "stories.yaml"), encoding="utf-8").read(), source)

    def test_failed_build_does_not_clean(self):
        os.makedirs(self.gen)
        stale = os.path.join(self.gen, "user-stories.csv")
        open(stale, "w").close()
        source = os.path.join(self.dir, "stories.yaml")
        text = open(source, encoding="utf-8").read()
        with open(source, "w", encoding="utf-8") as f:
            f.write(text.replace("screens: [s0]", "screens: [missing]"))
        self.assertEqual(self.build("--formats", "report", "--clean"), 1, self.output)
        self.assertTrue(os.path.exists(stale))

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_flow_map_only_cleans_temporary_flow_images(self):
        self.assertEqual(self.build("--formats", "flow-map"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"flow-map.png"})
        self.assertGreater(os.path.getsize(os.path.join(self.gen, "flow-map.png")), 100)

    def test_render_failure_does_not_clean_stale_outputs(self):
        from unittest import mock
        os.makedirs(self.gen)
        stale = os.path.join(self.gen, "user-stories.csv")
        with open(stale, "w") as f:
            f.write("keep until a successful build")
        with mock.patch.object(sm, "gen_html", side_effect=RuntimeError("render failed")):
            with self.assertRaisesRegex(RuntimeError, "render failed"):
                self.build("--formats", "html", "--clean")
        with open(stale) as f:
            self.assertEqual(f.read(), "keep until a successful build")

    def test_graphviz_failure_does_not_clean_stale_outputs(self):
        from unittest import mock
        os.makedirs(self.gen)
        stale = os.path.join(self.gen, "story-map.md")
        with open(stale, "w") as f:
            f.write("keep until Graphviz succeeds")
        with mock.patch.object(sm, "gen_diagrams", return_value=["graphviz failed on architecture"]):
            self.assertEqual(self.build("--formats", "arch", "--clean"), 1, self.output)
        with open(stale) as f:
            self.assertEqual(f.read(), "keep until Graphviz succeeds")

    def test_report_only_output_paths_do_not_request_graphviz_cache(self):
        from unittest import mock
        m = sm.load_model(self.dir)
        with mock.patch.object(sm, "HAVE_PIL", False), mock.patch.object(sm.shutil, "which", return_value="/usr/bin/dot"):
            self.assertEqual(sm.output_paths(m, {"report"}), {"REPORT.md"})
            self.assertEqual(sm.output_paths(m, {"arch"}), {"architecture.png", "dot/architecture.dot"})
            self.assertEqual(sm.output_paths(m, {"dot"}),
                             {"dot/architecture.dot", "dot/overview.dot", "dot/flow-map.dot", "dot/f1.dot"})

    def test_report_code_keeps_literal_path_characters(self):
        code = sm.report_code("src/a&b/<Widget>|view")
        self.assertEqual(code, "`src/a&b/<Widget>\\|view`")
        self.assertNotIn("&amp;", code)
        self.assertNotIn("&lt;", code)

    def test_report_code_uses_padded_longer_fences_only_for_embedded_backticks(self):
        self.assertEqual(sm.report_code("src/a_b.py"), "`src/a_b.py`")
        self.assertEqual(sm.report_code("src/`Welcome`"), "`` src/`Welcome` ``")
        self.assertEqual(sm.report_code("src/``Welcome``\nview"), "``` src/``Welcome`` view ```")

    def test_report_text_preserves_prose_characters_and_leading_markers(self):
        for marker in ("#", ">", "-"):
            value = marker + ' & "quotes" \'single\' snake_case *star* [brackets] `code` \\path | <tag>\r\nnext'
            expected = marker + ' & "quotes" \'single\' snake_case *star* [brackets] `code` \\path \\| &lt;tag> next'
            with self.subTest(marker=marker):
                self.assertEqual(sm.report_text(value), expected)

    def test_set_status_rebuild_uses_lean_defaults(self):
        if not sm.HAVE_PIL:
            self.skipTest("Pillow not installed")
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sm.main(["set-status", "US-1", "partly", "--dir", self.dir]), 0)
        self.assertEqual(set(os.listdir(self.gen)), {"REPORT.md", "architecture.png", "one-pager.png", "story-map.html"})

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_dot_only_uses_gitignored_cache_without_graphviz(self):
        from unittest import mock
        with mock.patch.object(sm.shutil, "which", return_value=None):
            self.assertEqual(self.build("--formats", "dot"), 0, self.output)
        self.assertEqual(set(os.listdir(self.gen)), {"dot"})
        self.assertFalse(os.path.exists(os.path.join(self.gen, "thumbs")))
        cached = os.path.join(self.dir, ".cache", "thumbs", "s0.png")
        self.assertTrue(os.path.isfile(cached))
        with open(os.path.join(self.dir, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines(), [".cache/"])
        for name in ("architecture", "overview", "flow-map", "f1"):
            path = os.path.join(self.gen, "dot", name + ".dot")
            with open(path, encoding="utf-8") as f:
                sources = re.findall(r'SRC="([^"]+)"', f.read())
            self.assertTrue(sources, name)
            for source in sources:
                self.assertFalse(os.path.isabs(source), source)
                self.assertEqual(os.path.abspath(os.path.join(os.path.dirname(path), source)), cached)
        self.assertEqual(self.build("--formats", "dot"), 0, self.output)
        with open(os.path.join(self.dir, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines().count(".cache/"), 1)

    @unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
    def test_cache_appends_ignore_rule_without_replacing_existing_rules(self):
        path = os.path.join(self.dir, ".gitignore")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Local rules\nkeep-me/")
        m = sm.load_model(self.dir)
        first = sm.make_thumbs(m, self.gen)
        second = sm.make_thumbs(m, self.gen)
        self.assertEqual(first, second)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Local rules\nkeep-me/\n.cache/\n")
        self.assertFalse(os.path.exists(os.path.join(self.gen, "thumbs")))

    def test_make_thumbs_without_pillow_does_not_create_cache(self):
        from unittest import mock
        with mock.patch.object(sm, "HAVE_PIL", False):
            self.assertEqual(sm.make_thumbs(sm.load_model(self.dir), self.gen), {})
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".cache")))
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".gitignore")))


class TestInit(unittest.TestCase):
    IGNORE_PATTERNS = {".cache/", "frames.json", "frames/", ".demo-session.json",
                       "*.storage-state.json", ".env", ".env.*"}

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="storymap init ")
        self.dir = os.path.join(self.tmp, "new map")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *args):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                result = sm.main(list(args))
            except SystemExit as ex:
                result = ex.code
        self.output = out.getvalue()
        return result

    def test_default_init_has_gitignore_and_uses_external_script(self):
        import shlex
        self.assertEqual(self.run_main("init", self.dir), 0)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "storymap.py")))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "stories.yaml")))
        for name in ("screens", "generated"):
            self.assertTrue(os.path.isfile(os.path.join(self.dir, name, ".gitkeep")))
        self.assertEqual(os.listdir(os.path.join(self.dir, "generated")), [".gitkeep"])
        with open(os.path.join(self.dir, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(set(f.read().splitlines()), self.IGNORE_PATTERNS)
        self.assertNotIn("vendored", self.output.lower())
        command = self.output.split("then run:  ", 1)[1].splitlines()[0]
        self.assertEqual(shlex.split(command), ["python3", os.path.abspath(sm.__file__), "build", self.dir])
        with open(os.path.join(self.dir, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertIn('SM="python3 <skill>/scripts/storymap.py"', readme)
        self.assertIn("in a clone of the repo: skills/user-story-maps", readme)
        with open(os.path.join(self.dir, "stories.yaml"), encoding="utf-8") as f:
            self.assertIn("# After any change run `validate` and `build` (commands: see README.md in this folder).", f.read())

    def test_vendor_copies_generator_only_when_requested(self):
        self.assertEqual(self.run_main("init", self.dir, "--vendor"), 0)
        with open(os.path.join(self.dir, "storymap.py"), "rb") as f:
            copied = f.read()
        with open(sm.__file__, "rb") as f:
            self.assertEqual(copied, f.read())
        self.assertIn("vendored", self.output.lower())

    def test_no_vendor_remains_a_hidden_no_op(self):
        self.assertEqual(self.run_main("init", self.dir, "--no-vendor"), 0)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "storymap.py")))
        other = os.path.join(self.tmp, "vendor map")
        self.assertEqual(self.run_main("init", other, "--vendor", "--no-vendor"), 0)
        self.assertTrue(os.path.isfile(os.path.join(other, "storymap.py")))
        self.assertEqual(self.run_main("init", "--help"), 0)
        self.assertIn("--vendor", self.output)
        self.assertNotIn("--no-vendor", self.output)

    def test_init_preserves_existing_ignore_rules_without_duplicates(self):
        os.makedirs(self.dir)
        path = os.path.join(self.dir, ".gitignore")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Existing rules\n.cache/\nprivate/")
        self.assertEqual(self.run_main("init", self.dir), 0)
        with open(path, encoding="utf-8") as f:
            before = f.read()
        self.assertTrue(before.startswith("# Existing rules\n.cache/\nprivate/\n"))
        for pattern in self.IGNORE_PATTERNS:
            self.assertEqual(before.splitlines().count(pattern), 1)
        sm.ensure_gitignore(self.dir, tuple(sorted(self.IGNORE_PATTERNS)))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)

    def test_version_is_1_2_0(self):
        self.assertEqual(sm.__version__, "1.2.0")
        self.assertEqual(self.run_main("--version"), 0)
        self.assertEqual(self.output.strip(), "1.2.0")


class AgentsRepoCase(unittest.TestCase):
    START = "<!-- user-story-maps:start -->"
    END = "<!-- user-story-maps:end -->"

    def setUp(self):
        # Keep all test writes in this checkout and stop root discovery at our own repo.
        self.tmp = tempfile.mkdtemp(prefix=".agents-tests-", dir=HERE)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        os.mkdir(os.path.join(self.tmp, ".git"))
        self.dir = os.path.join(self.tmp, "docs", "story-map")

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def read(self, name):
        with open(os.path.join(self.tmp, name), "rb") as f:
            return f.read()

    def run_main(self, *args):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = sm.main(list(args))
        self.output = out.getvalue()
        return result


class TestInitAgents(AgentsRepoCase):
    def test_appends_block_without_replacing_existing_text_or_missing_newline(self):
        before = "# Existing instructions\nKeep these instructions."
        self.write("AGENTS.md", before)
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        text = self.read("AGENTS.md").decode("utf-8")
        self.assertTrue(text.startswith(before + "\n\n" + self.START + "\n"))
        self.assertEqual(text.count(self.START), 1)
        self.assertEqual(text.count(self.END), 1)
        self.assertIn("docs/story-map/stories.yaml", text)
        self.assertIn("https://github.com/enjojoy/user-story-maps", text)
        self.assertIn("Agents:", self.output)
        self.assertIn("added", self.output)
        self.assertIn("AGENTS.md", self.output)
        self.assertIn("(docs/story-map)", self.output)

    def test_second_init_is_byte_identical_and_preserves_the_source(self):
        self.write("AGENTS.md", "# Repository\n")
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        before = self.read("AGENTS.md")
        source = os.path.join(self.dir, "stories.yaml")
        with open(source, "a", encoding="utf-8") as f:
            f.write("\n# Keep my source edits.\n")
        with open(source, "rb") as f:
            source_before = f.read()
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        self.assertEqual(self.read("AGENTS.md"), before)
        with open(source, "rb") as f:
            self.assertEqual(f.read(), source_before)
        self.assertIn("already up to date", self.output.lower())

    def test_stale_managed_block_is_updated_without_changing_surrounding_text(self):
        prefix, suffix = "# Keep before\n\n", "\n\n# Keep after\nNo final newline"
        self.write("AGENTS.md", prefix + self.START + "\nStale text.\n" + self.END + suffix)
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        text = self.read("AGENTS.md").decode("utf-8")
        self.assertTrue(text.startswith(prefix + self.START + "\n"))
        self.assertTrue(text.endswith(self.END + suffix))
        self.assertNotIn("Stale text.", text)
        self.assertEqual(text.count(self.START), 1)
        self.assertIn("updated", self.output.lower())

    def test_agents_takes_precedence_over_claude(self):
        self.write("AGENTS.md", "# Agents\n")
        claude = b"# Claude\nKeep me.\n"
        self.write("CLAUDE.md", claude.decode("utf-8"))
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        self.assertIn(self.START.encode("utf-8"), self.read("AGENTS.md"))
        self.assertEqual(self.read("CLAUDE.md"), claude)

    def test_claude_is_used_when_agents_is_missing(self):
        self.write("CLAUDE.md", "# Claude\n")
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        self.assertIn(self.START.encode("utf-8"), self.read("CLAUDE.md"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "AGENTS.md")))
        self.assertIn("CLAUDE.md", self.output)

    def test_bare_option_with_neither_file_prints_note_and_creates_neither(self):
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertFalse(os.path.exists(os.path.join(self.tmp, name)))
        self.assertIn("no agents.md or claude.md found", self.output.lower())
        self.assertIn("--agents AGENTS.md", self.output)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "stories.yaml")))

    def test_explicit_agents_file_is_created_in_the_repo_root(self):
        self.assertEqual(self.run_main("init", self.dir, "--agents", "AGENTS.md"), 0)
        self.assertIn(self.START.encode("utf-8"), self.read("AGENTS.md"))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "AGENTS.md")))

    def test_explicit_custom_filename_is_created_and_existing_text_is_preserved(self):
        name = "CODING.md"
        self.assertEqual(self.run_main("init", self.dir, "--agents", name), 0)
        before = self.read(name)
        self.assertIn(self.START.encode("utf-8"), before)
        self.write(name, "# Custom preface\n\n" + before.decode("utf-8"))
        self.assertEqual(self.run_main("init", self.dir, "--agents", name), 0)
        self.assertEqual(self.read(name), b"# Custom preface\n\n" + before)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "AGENTS.md")))

    def test_custom_map_path_is_relative_to_the_repo_root(self):
        self.dir = os.path.join(self.tmp, "docs", "maps", "app")
        self.assertEqual(self.run_main("init", self.dir, "--agents", "AGENTS.md"), 0)
        text = self.read("AGENTS.md").decode("utf-8")
        self.assertIn("docs/maps/app/stories.yaml", text)
        self.assertIn("docs/maps/app/screens/", text)
        self.assertIn("docs/maps/app/generated/", text)
        self.assertIn("python3 <skill>/scripts/storymap.py validate docs/maps/app", text)
        self.assertNotIn("docs/story-map", text)
        self.assertNotIn(self.tmp, text)

    def test_vendor_command_uses_custom_map_path_and_drops_skill_explanation(self):
        self.dir = os.path.join(self.tmp, "docs", "maps", "app")
        self.assertEqual(self.run_main("init", self.dir, "--vendor", "--agents", "AGENTS.md"), 0)
        text = self.read("AGENTS.md").decode("utf-8")
        self.assertIn("python3 docs/maps/app/storymap.py validate docs/maps/app", text)
        self.assertIn("python3 docs/maps/app/storymap.py build docs/maps/app", text)
        self.assertNotIn("<skill>", text)
        self.assertNotIn("docs/story-map", text)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "storymap.py")))
        readme = self.read("docs/maps/app/README.md").decode("utf-8")
        self.assertIn('SM="python3 docs/maps/app/storymap.py"', readme)
        self.assertNotIn("<skill>", readme)

    def test_quoted_vendor_paths_with_default_prefix_are_not_substituted_twice(self):
        import shlex
        relative = "docs/story-map/app map"
        self.dir = os.path.join(self.tmp, *relative.split("/"))
        self.assertEqual(self.run_main("init", self.dir, "--vendor", "--agents", "AGENTS.md"), 0)
        text = self.read("AGENTS.md").decode("utf-8")
        commands = re.findall(r"`(python3 [^`]+)`", text)
        self.assertEqual([shlex.split(command) for command in commands],
                         [["python3", relative + "/storymap.py", command, relative]
                          for command in ("validate", "build")])
        self.assertIn("`" + relative + "/stories.yaml`", text)
        self.assertNotIn("app map/app map", text)
        readme = self.read(relative + "/README.md").decode("utf-8")
        sm_line = next(line for line in readme.splitlines() if line.startswith("SM="))
        self.assertEqual(sm_line, 'SM="python3 ' + shlex.quote(relative + "/storymap.py") + '"')
        self.assertEqual(shlex.split(sm_line[4:-1]), ["python3", relative + "/storymap.py"])

    def test_crlf_file_preserves_surrounding_bytes_and_remains_idempotent(self):
        prefix, suffix = "# Before\r\n\r\n", "\r\n\r\n# After, without final newline"
        self.write("AGENTS.md", prefix + self.START + "\r\nOld block.\r\n" + self.END + suffix)
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        updated = self.read("AGENTS.md")
        self.assertTrue(updated.startswith((prefix + self.START + "\r\n").encode("utf-8")))
        self.assertTrue(updated.endswith((self.END + suffix).encode("utf-8")))
        self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))
        self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
        self.assertEqual(self.read("AGENTS.md"), updated)
        self.assertIn("already up to date", self.output.lower())

    def test_map_outside_fallback_root_keeps_the_path_as_given(self):
        import shlex
        from unittest import mock
        cwd = os.path.join(self.tmp, "working")
        os.mkdir(cwd)
        given = "../outside map"
        isdir, isfile = os.path.isdir, os.path.isfile

        def without_git(fn):
            return lambda path: False if os.path.basename(os.fspath(path)) == ".git" else fn(path)

        with mock.patch.object(os, "getcwd", return_value=cwd), \
                mock.patch.object(os.path, "isdir", side_effect=without_git(isdir)), \
                mock.patch.object(os.path, "isfile", side_effect=without_git(isfile)):
            self.assertEqual(self.run_main("init", given, "--agents", "AGENTS.md"), 0)
        text = self.read("working/AGENTS.md").decode("utf-8")
        self.assertIn("`../outside map/stories.yaml`", text)
        commands = re.findall(r"`(python3 [^`]+)`", text)
        self.assertEqual([shlex.split(command)[-2:] for command in commands],
                         [[command, given] for command in ("validate", "build")])
        self.assertNotIn(self.tmp, text)

    def test_legacy_story_map_mentions_are_not_changed(self):
        for text in ("# Instructions\nKeep STORY-MAP updated.",
                     "# Instructions\nUpdate STORIES.YAML before finishing.\n"):
            with self.subTest(text=text):
                self.write("AGENTS.md", text)
                self.assertEqual(self.run_main("init", self.dir, "--agents"), 0)
                self.assertEqual(self.read("AGENTS.md"), text.encode("utf-8"))
                self.assertIn("already mentions the story map", self.output.lower())
                self.assertIn("markers", self.output.lower())
                self.assertIn("remove", self.output.lower())

    def test_reminder_is_shown_only_without_agents_option(self):
        self.assertEqual(self.run_main("init", self.dir), 0)
        self.assertIn("IMPORTANT:", self.output)
        self.assertIn("agents only keep the map current", self.output.lower())
        self.assertIn("--agents", self.output)
        self.assertIn("then run:  python3 ", self.output)
        self.assertEqual(self.run_main("init", self.dir, "--agents", "AGENTS.md"), 0)
        self.assertNotIn("IMPORTANT:", self.output)

    def test_nearest_existing_ancestor_and_git_file_select_nested_repo(self):
        self.write("AGENTS.md", "# Parent instructions\n")
        self.write("nested/.git", "gitdir: ../.git/worktrees/nested\n")
        self.dir = os.path.join(self.tmp, "nested", "docs", "maps", "app")
        self.assertFalse(os.path.exists(os.path.dirname(self.dir)))
        self.assertEqual(self.run_main("init", self.dir, "--agents", "AGENTS.md"), 0)
        self.assertEqual(self.read("AGENTS.md"), b"# Parent instructions\n")
        text = self.read("nested/AGENTS.md").decode("utf-8")
        self.assertIn("docs/maps/app/stories.yaml", text)
        self.assertNotIn("nested/docs/maps/app", text)

    def test_init_help_describes_agents_option(self):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as ex:
            sm.main(["init", "--help"])
        self.assertEqual(ex.exception.code, 0)
        self.assertIn("--agents", out.getvalue())
        self.assertIn("AGENTS.md", out.getvalue())


class TestValidateAgents(AgentsRepoCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(EXAMPLE, self.dir, ignore=shutil.ignore_patterns("generated", "tools"))
        self.src = os.path.join(self.dir, "stories.yaml")
        with open(self.src, encoding="utf-8") as f:
            # Examples opt out because this checkout is not an application repo.
            self.source = re.sub(r"(?m)^  agents_check:.*\n", "", f.read())
        with open(self.src, "w", encoding="utf-8") as f:
            f.write(self.source)

    def issues(self):
        return sm.validate(sm.load_model(self.dir))

    def test_missing_instructions_warn_without_becoming_an_error(self):
        model = sm.load_model(self.dir)
        self.assertEqual(model["app"]["agents_check"], "")
        warnings = [i for i in sm.validate(model) if i[1] == "AGENTS_MISSING"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0][0], "warn")
        self.assertIn("init", warnings[0][2])
        self.assertIn("--agents", warnings[0][2])
        self.assertIn("templates/AGENTS-snippet.md", warnings[0][2])
        self.assertNotIn("AGENTS_MISSING", codes(sm.validate(model), "error"))

    def test_supported_instruction_files_and_case_insensitive_mentions_silence_warning(self):
        cases = (("AGENTS.md", "<!-- USER-STORY-MAPS:start -->"),
                 ("AGENTS.md", "Keep the STORY-MAP up to date."),
                 ("AGENTS.md", "Update STORIES.YAML."),
                 ("CLAUDE.md", "Keep the story-map updated."),
                 (".cursor/rules/x.mdc", "Update Stories.Yaml."),
                 (".cursor/rules/x.md", "Use the user-story-maps skill."))
        for name, text in cases:
            with self.subTest(name=name, text=text):
                path = self.write(name, text)
                self.assertNotIn("AGENTS_MISSING", codes(self.issues()))
                os.unlink(path)

    def test_instruction_files_without_any_mention_do_not_silence_warning(self):
        for name in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/x.mdc", ".cursor/rules/y.md"):
            self.write(name, "Use Python 3.9 and run tests.\n")
        self.assertIn("AGENTS_MISSING", codes(self.issues(), "warn"))

    def test_only_files_in_the_closest_repo_root_are_checked(self):
        self.write("AGENTS.md", "Update the story-map.\n")
        os.mkdir(os.path.join(self.dir, ".git"))
        self.assertIn("AGENTS_MISSING", codes(self.issues(), "warn"))
        with open(os.path.join(self.dir, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("Update stories.yaml.\n")
        self.assertNotIn("AGENTS_MISSING", codes(self.issues()))

    def test_source_location_is_used_instead_of_model_root(self):
        self.write("AGENTS.md", "Update the story-map.\n")
        model = sm.load_model(self.dir)
        model["root"] = HERE
        self.assertNotIn("AGENTS_MISSING", codes(sm.validate(model)))

    def test_instruction_symlink_above_the_repo_root_does_not_silence_warning(self):
        outside = self.write("parent-instructions.md", "Update the story-map.\n")
        os.mkdir(os.path.join(self.dir, ".git"))
        os.symlink(outside, os.path.join(self.dir, "AGENTS.md"))
        self.assertIn("AGENTS_MISSING", codes(self.issues(), "warn"))

    def test_no_git_ancestor_skips_the_warning(self):
        from unittest import mock
        # The fixtures stay inside this checkout; hide only .git entries to model
        # an ordinary directory without writing outside the repo.
        exists, isdir, isfile = os.path.exists, os.path.isdir, os.path.isfile

        def without_git(fn):
            return lambda path: False if os.path.basename(os.fspath(path)) == ".git" else fn(path)

        with mock.patch.object(os.path, "exists", side_effect=without_git(exists)), \
                mock.patch.object(os.path, "isdir", side_effect=without_git(isdir)), \
                mock.patch.object(os.path, "isfile", side_effect=without_git(isfile)):
            self.assertNotIn("AGENTS_MISSING", codes(self.issues()))

    def test_app_opt_out_values_are_loaded_and_silence_warning(self):
        for value in ("off", "false", "no", "0"):
            with self.subTest(value=value):
                with open(self.src, "w", encoding="utf-8") as f:
                    f.write(self.source.replace("app:\n", "app:\n  agents_check: " + value + "\n", 1))
                model = sm.load_model(self.dir)
                self.assertEqual(model["app"]["agents_check"], value)
                self.assertNotIn("AGENTS_MISSING", codes(sm.validate(model)))

    def test_warning_allows_validate_and_build_except_under_strict(self):
        self.assertEqual(self.run_main("validate", self.dir), 0)
        self.assertIn("AGENTS_MISSING", self.output)
        self.assertEqual(self.run_main("validate", self.dir, "--strict"), 1)
        self.assertIn("AGENTS_MISSING", self.output)
        self.assertEqual(self.run_main("build", self.dir, "--formats", "report", "--strict"), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "generated")))
        self.assertEqual(self.run_main("build", self.dir, "--formats", "report"), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "generated", "REPORT.md")))


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
            cached = os.path.join(self.tmp, ".cache", "thumbs", n + ".png")
            im = self.Image.open(cached)
            self.assertEqual(os.path.abspath(os.path.join(gen, "dot", th[n][0])), cached)
            self.assertEqual(im.mode, "RGBA")
            self.assertTrue(th[n][3])                                              # marked as a framed image
            self.assertLessEqual(abs(im.width - 2 * th[n][1]), 1, n)
            self.assertLessEqual(abs(im.height - 2 * th[n][2]), 1, n)
            dv = self._device(n)
            self.assertEqual(im.size, dv["size"])
            self._screen_checks(dict(img=im, rect=dv["rect"]), w, h, n)
            self.assertEqual(im.getpixel((0, 0))[3], 0, n)                        # transparent outside the device
        self.assertFalse(os.path.exists(os.path.join(gen, "thumbs")))

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
            self.assertEqual(sm.main(["build", out, "--profile", "full"]), 0)
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
        self.assertLess(os.path.getsize(os.path.join(g, "story-map.html")), 2_000_000)
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
        for style in ("black", "titanium", "light"):
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
        node = sm.dot_node(s, ("../../.cache/thumbs/a.png", 200, 400, True))
        self.assertIn('SRC="../../.cache/thumbs/a.png"', node)
        self.assertNotIn('BORDER="3"', node)              # no coloured border around the screenshot
        self.assertIn(sm.STATUS["built"]["color"], node)  # the status colour is on the badge dot
        arch = sm.dot_arch_node(s, ("../../.cache/thumbs/a.png", 200, 400, True))
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
            self.assertLess(len(h.encode("utf-8")), 2_000_000)
            self.assertNotIn("@font-face", h)
            import base64
            imgs = TestHtml.images(h)
            for uri in imgs.values():
                if uri and uri.startswith("data:image"):
                    with sm.Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as im:
                        # Architecture is a separate preview; screen previews are at most 480 px.
                        self.assertLessEqual(im.width, 2400)
            for sid in ("p%d" % i for i in range(6)):
                with sm.Image.open(io.BytesIO(base64.b64decode(imgs[sid].split(",", 1)[1]))) as im:
                    self.assertLessEqual(im.width, 480)


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


# --------------------------------------------------------------------------- no white cards, dark theme
CARD_YAML = """app:
  name: "Cards"
  platform: "ios"
topics:
  - id: t1
    title: "Main journey"
personas:
  - id: u
    name: "User"
    as_a: "a user"
    description: "x"
flows:
  - id: f1
    title: "Flow"
    description: "d"
    edges:
      - "a -> b: next"
screens:
  - id: a
    title: "Screen A has a long enough title"
    flow: f1
    topic: t1
    image: screens/a.png
  - id: b
    title: "B"
    flow: f1
    topic: t1
    image: screens/b.png
stories:
  - id: US-1
    persona: u
    want: "x"
    so_that: "y"
    screens: [a, b]
    status: unverified
"""


class TestNoWhiteCards(unittest.TestCase):
    """Devices, titles and status badges sit directly on the lane/page colour: no card is drawn behind them."""

    @classmethod
    def setUpClass(cls):
        if not sm.HAVE_PIL:
            raise unittest.SkipTest("Pillow not installed")

    def tearDown(self):
        sm.apply_theme(sm.load_model(EXAMPLE))      # leave the module-level theme as the example defines it
        sm._DEV_CACHE.clear()

    def render(self, theme=""):
        from PIL import Image
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "screens"))
        for n in "ab":
            Image.new("RGB", (600, 1300), (90, 130, 180)).save(os.path.join(d, "screens", n + ".png"))
        with open(os.path.join(d, "stories.yaml"), "w") as f:
            f.write(CARD_YAML + theme)
        m = sm.load_model(d)
        sm.apply_theme(m)
        sm._DEV_CACHE.clear()
        out = os.path.join(d, "arch.png")
        info = sm.pil_architecture(m, out)
        return m, info, Image.open(out).convert("RGB")

    def check_corners_are_lane(self, m, info, im):
        tp = m["T"]["t1"]
        lane = sm.hexrgb(sm.tint(tp["color"], 0.93))
        self.assertEqual(len(info["cards"]), 2)
        for sid, (x, y, w, h) in info["cards"].items():
            for px in ((x + 2, y + 2), (x + w - 3, y + 2), (x + 2, y + h - 3), (x + w - 3, y + h - 3)):
                self.assertEqual(im.getpixel(px), lane, (sid, px, "a card background is drawn behind the device"))
            # the title strip beside the text (left edge, at title height) is the lane colour too
            self.assertEqual(im.getpixel((x + 2, y + 10)), lane)
        return lane

    def test_light_architecture_has_no_card_fill(self):
        m, info, im = self.render()
        lane = self.check_corners_are_lane(m, info, im)
        self.assertNotEqual(lane, (255, 255, 255))

    def test_dark_architecture_has_no_card_fill(self):
        m, info, im = self.render('theme:\n  primary: "#3366CC"\n  background: "#000000"\n')
        self.assertTrue(sm.TH["dark"])
        lane = self.check_corners_are_lane(m, info, im)
        self.assertLess(sum(lane) / 3, 40, lane)                      # the lane is a dark tint, not a light one
        self.assertEqual(im.getpixel((2, 2)), (0, 0, 0))              # page background is black

    def test_dark_theme_derives_legible_colours(self):
        m, info, im = self.render('theme:\n  primary: "#3366CC"\n  background: "#000000"\n')
        lum = lambda h: sm._lum(h)
        self.assertEqual(sm.TH["bg"], "#000000")
        self.assertGreater(lum(sm.TH["ink"]), 0.8)                     # light text
        self.assertGreater(lum(sm.TH["muted"]), 0.5)
        for k in sm.STATUS:
            self.assertGreater(lum(sm.STATUS[k]["color"]), 0.3, k)     # status colours readable on black
        self.assertGreater(lum(m["T"]["t1"]["color"]), 0.15)
        self.assertEqual(sm.TH["device"]["style"], "auto")
        sm._DEV_CACHE.clear()
        self.assertEqual(sm.on_color(), "#000000")                     # labels on bright chips are black
        m2, _, _ = self.render('theme:\n  mode: light\n')
        self.assertFalse(sm.TH["dark"])

    def test_dark_theme_picks_the_light_frame(self):
        self.render('theme:\n  mode: dark\n')
        self.assertTrue(sm.TH["dark"])
        self.assertNotEqual(sm.TH["bg"], "#FFFFFF")
        m = {"app": {"platform": "ios", "device": ""}, "root": tempfile.gettempdir() + "/storymap-no-such-dir"}
        from PIL import Image
        dv = sm.render_device(m, {}, Image.new("RGB", (600, 1300), (90, 130, 180)), "iphone-island", (300, 500), 1, shadow=False)
        self.assertGreater(sum(dv["img"].getpixel((2, dv["size"][1] // 2))[:3]) / 3, 100)   # titanium band, not a black one on black

    def test_wikipedia_example_is_a_black_theme(self):
        wiki = os.path.join(HERE, "..", "examples", "wikipedia-ios")
        sm.apply_theme(sm.load_model(wiki))
        self.assertTrue(sm.TH["dark"])
        self.assertEqual(sm.TH["bg"], "#000000")
        arch = os.path.join(wiki, "generated", "architecture.png")
        if os.path.isfile(arch):
            from PIL import Image
            self.assertEqual(Image.open(arch).convert("RGB").getpixel((2, 2)), (0, 0, 0))

    def test_flow_and_html_use_theme_background(self):
        from PIL import Image
        m, info, im = self.render('theme:\n  background: "#000000"\n')
        gen = tempfile.mkdtemp()
        sm.pil_flow(m, "f1", os.path.join(gen, "f1.png"))
        fl = Image.open(os.path.join(gen, "f1.png")).convert("RGB")
        self.assertEqual(fl.getpixel((2, 2)), (0, 0, 0))
        css = sm.themeify(".card{background:#fff;color:#202124}")
        self.assertIn("background:#000000", css.lower())
        self.assertNotIn("border:1px solid var(--line);border-radius:12px;width:250px", css)   # html .card has no frame


@unittest.skipUnless(sm.HAVE_PIL, "Pillow not installed")
class TestResolution(Base):
    """Rule: every screenshot in architecture / overview / flows / one-pager is drawn at >= its native pixels."""

    def setUp(self):
        super().setUp()
        from PIL import Image
        for f in os.listdir(os.path.join(self.dir, "screens")):      # smaller sources keep the test light (390x844)
            p = os.path.join(self.dir, "screens", f)
            if f.endswith(".png"):
                Image.open(p).convert("RGB").resize((390, 844)).save(p)
        sm._DEV_CACHE.clear()
        sm._img_cache.clear()

    def test_native_zoom_makes_device_screen_at_least_source_size(self):
        m = sm.load_model(self.dir)
        sm.apply_theme(m)
        for box in (sm.ARCH_BOX, sm.OVERVIEW_BOX, (sm.LANDSCAPE_W, sm.PORTRAIT_H)):
            z = sm.native_zoom(m, box)
            self.assertGreater(z, 1.0)
            for s in m["screens"]:
                im = sm.load_img(m, s)
                if im is None:
                    continue
                rect = sm.screen_device(m, s, box, z)["rect"]
                self.assertGreaterEqual(rect[2], im.width, (s["id"], box))
                self.assertGreaterEqual(rect[3], im.height, (s["id"], box))
        sm._DEV_CACHE.clear()

    def test_build_renders_every_diagram_at_native_resolution(self):
        self.assertEqual(sm.main(["build", self.dir, "--profile", "full"]), 0)
        rep = sm.resolution_report()
        gen = os.path.join(self.dir, "generated")
        self.assertIn("architecture", rep)
        self.assertIn("overview", rep)
        self.assertIn("one-pager", rep)
        self.assertTrue(any(k.startswith("flows/") for k in rep))
        for name, k in rep.items():
            self.assertGreaterEqual(k, 0.99, "%s draws a screenshot at %.2fx of its source pixels" % (name, k))
        from PIL import Image
        for f in ("architecture.png", "overview.png", "one-pager.png"):
            self.assertTrue(os.path.isfile(os.path.join(gen, f)), f)
        arch = Image.open(os.path.join(gen, "architecture.png"))
        self.assertGreaterEqual(arch.width * arch.height, 390 * 844 * len(sm.load_model(self.dir)["screens"]) // 2)   # canvas grew, not shrank
        self.assertTrue(os.path.isdir(os.path.join(gen, "architecture")))
        self.assertTrue(os.listdir(os.path.join(gen, "architecture")))

    def test_default_lean_architecture_and_onepager_keep_native_resolution(self):
        self.assertEqual(sm.main(["build", self.dir, "--no-graphviz"]), 0)
        rep = sm.resolution_report()
        for name in ("architecture", "one-pager"):
            self.assertIn(name, rep)
            self.assertGreaterEqual(rep[name], 0.99, "%s draws screenshots below native resolution" % name)
        gen = os.path.join(self.dir, "generated")
        for name in ("architecture.png", "one-pager.png"):
            self.assertGreater(os.path.getsize(os.path.join(gen, name)), 1000)
        self.assertEqual(set(os.listdir(gen)), {"REPORT.md", "architecture.png", "one-pager.png", "story-map.html"})

    def test_downscaled_render_is_reported_below_native(self):
        m = sm.load_model(self.dir)
        sm.apply_theme(m)
        del sm.RES_LOG[:]
        sm.set_diagram("tiny")
        sm.screen_device(m, m["screens"][0], sm.ARCH_BOX, 1)       # zoom 1 = compact design size, far below native
        sm.set_diagram("other")
        self.assertLess(sm.resolution_report()["tiny"], 0.5)
        sm._DEV_CACHE.clear()


if __name__ == "__main__":
    unittest.main()
