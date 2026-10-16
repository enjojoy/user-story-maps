<!-- Paste this block into the repo's AGENTS.md (or CLAUDE.md / CONTRIBUTING.md). -->
## Story map is part of "done"

This repo keeps its user stories and screen map in `docs/story-map/stories.yaml`
(source of truth) with screenshots in `docs/story-map/screens/` and outputs in `docs/story-map/generated/`.

Whenever you add, change, hide or remove a user-visible feature or screen, **before you call the task done**:

1. Update `docs/story-map/stories.yaml`: add/adjust the story (persona, want, so_that, screens, status, where),
   add/rename the screen and its flow edge (every flow belongs to a `topic:`; a new area of the app = a new topic), and add any new gap or risk you noticed.
2. Capture or refresh the screenshot in `docs/story-map/screens/<screen-id>.png` from a running app using a demo
   account (never real credentials or personal data; see the capture guide in the `user-story-maps` skill).
   If you cannot capture it, set `not_captured: <reason>` instead of leaving a broken link.
3. Run `python3 <skill>/scripts/storymap.py validate docs/story-map` and fix every error (and warning), then
   `python3 <skill>/scripts/storymap.py build docs/story-map` (`<skill>` = the installed `user-story-maps` skill; use
   `docs/story-map/storymap.py` if it was vendored). Commit `stories.yaml`, `screens/` and `generated/` together.
   Default outputs: `REPORT.md`, `story-map.html`, `architecture.png`, `one-pager.png`; extras are opt-in (`--formats +csv`).
4. **Honesty rule:** only set `status: built` after you verified the behaviour in code or on a running app, and fill
   `verified:` with how and when (e.g. `"code + app, 2026-10-15"`). If you did not check it, use `unverified`.
   Use `partly` for incomplete work (say what is missing in `notes`) and `missing` for planned work.
5. If the app's look changes (brand colour, font), update the optional `theme:` block so the generated map keeps matching it. Screenshots are framed as devices automatically; override per screen with `device:` (never commit third-party frame images).
6. Never hand-edit files in `generated/`; edit the source and rebuild.
