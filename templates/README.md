# Story map

Living map of this app's user stories and screens, with real screenshots.

| What | Where |
|---|---|
| **Edit this** | `stories.yaml` (topics, optional theme incl. `device:` frame style, personas, flows, screens, stories, gaps) |
| Real screenshots | `screens/<screen-id>.png` |
| Generated - never edit | `generated/` (open `generated/story-map.html`, `generated/architecture.png` or `generated/one-pager.pdf`) |

## Update after any change
```bash
python3 docs/story-map/storymap.py validate   # flags missing screens/screenshots, duplicate ids, unused screens
python3 docs/story-map/storymap.py build      # regenerates everything in generated/
python3 docs/story-map/storymap.py set-status US-03 built --verified "app, 2026-10-15"   # one-line status change
```

Rules: never mark a story `built` unless you verified it in code or on a running app (otherwise `unverified`);
screenshots are shown inside device frames drawn by the generator (never commit third-party frame images); screenshots come from a demo account only - no real emails, names, tokens or credentials.
Full guide: the `user-story-maps` skill (`SKILL.md`).
