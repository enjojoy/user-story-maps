"""Keep the standalone skill copies in sync and check their first run without a repo."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "user-story-maps"
FIXTURE = ROOT / "tests" / "fixtures" / "sample-app"
SYNC_COMMAND = (
    "mkdir -p skills/user-story-maps/scripts skills/user-story-maps/templates && "
    "cp -R scripts/storymap.py scripts/capture skills/user-story-maps/scripts/ && "
    "cp -R templates/. skills/user-story-maps/templates/"
)


def source_files(folder):
    # Bytecode is a runtime cache, not part of either source tree.
    return {path.relative_to(folder): path for path in folder.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


class TestSkillBundle(unittest.TestCase):
    def test_bundled_files_match_sources(self):
        for name in ("scripts", "templates"):
            source = source_files(ROOT / name)
            bundled = source_files(SKILL / name)
            with self.subTest(folder=name):
                self.assertEqual(set(source), set(bundled), SYNC_COMMAND)
            for relative in source.keys() & bundled.keys():
                with self.subTest(file=str(Path(name) / relative)):
                    path = source[relative]
                    copy = bundled[relative]
                    self.assertFalse(copy.is_symlink(), SYNC_COMMAND)
                    self.assertEqual(path.read_bytes(), copy.read_bytes(), SYNC_COMMAND)
                    self.assertEqual(path.stat().st_mode & 0o111,
                                     copy.stat().st_mode & 0o111, SYNC_COMMAND)

    def test_first_run_from_skill_only_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            skill = folder / "skill"
            shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            app = folder / "app"
            app.mkdir()
            self.assertFalse((folder / ".git").exists())
            self.assertFalse((app / ".git").exists())
            self.assertFalse((folder / "scripts").exists())
            self.assertFalse((folder / "templates").exists())
            script = skill / "scripts" / "storymap.py"
            story_map = app / "docs" / "story-map"
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", STORYMAP_NO_NETWORK="1")

            def run(*args):
                result = subprocess.run([sys.executable, str(script), *map(str, args)],
                                        cwd=app, env=env, capture_output=True, text=True,
                                        timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            run("init", story_map, "--agents", "AGENTS.md")
            for path in (story_map / "stories.yaml", story_map / "README.md", app / "AGENTS.md"):
                self.assertTrue(path.is_file(), str(path))
            agents = (app / "AGENTS.md").read_text(encoding="utf-8")
            for command in ("validate", "build"):
                self.assertIn("python3 <skill>/scripts/storymap.py " + command + " docs/story-map", agents)

            # The skeleton has unused topics; use the existing complete fixture for a clean build.
            shutil.copy2(FIXTURE / "stories.yaml", story_map / "stories.yaml")
            shutil.copytree(FIXTURE / "screens", story_map / "screens", dirs_exist_ok=True)
            self.assertIn("0 error(s), 0 warning(s)", run("validate", story_map))
            run("build", story_map)
            for name in ("REPORT.md", "story-map.html"):
                self.assertTrue((story_map / "generated" / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
