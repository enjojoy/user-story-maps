# Story map

Living map of this app's user stories and screens, with real screenshots.

| What | Where |
|---|---|
| **Edit this** | `stories.yaml` (topics, optional theme, personas, flows, screens, stories, gaps) |
| Real screenshots | `screens/<screen-id>.png` |
| Generated - never edit | `generated/`: `REPORT.md` (stories, gaps, topics), `story-map.html`, `architecture.png`, `one-pager.png` |

## Update after any change
```bash
SM="python3 <skill>/scripts/storymap.py"   # <skill> = the user-story-maps skill folder (the one with SKILL.md; in a clone of the repo: skills/user-story-maps)
$SM validate docs/story-map     # missing screens/screenshots, duplicate ids, over-long or repeated text
$SM build docs/story-map        # lean default; add --formats +csv,flows or --profile full for more
$SM set-status --dir docs/story-map US-03 built --verified "app, 2026-10-15"   # one-line status change
```

`init --vendor` copies the script into this folder.

Rules: never mark a story `built` unless you verified it in code or on a running app (otherwise `unverified`);
keep fields short and say things once; screenshots are shown inside device frames drawn by the generator (never commit third-party frame images); screenshots come from a demo account only - no real emails, names, tokens or credentials.
Full guide: the `user-story-maps` skill (`SKILL.md`).
Run `init docs/story-map --agents` to add the map-update instructions to `AGENTS.md` or `CLAUDE.md`; pass `--agents AGENTS.md` to create the file.
