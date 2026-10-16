---
name: user-story-maps
description: "Create, update or audit an app's user stories, story map, screen/flow inventory, architecture-by-topic diagram or screenshot journeys (iOS, Android, web) from one stories.yaml. Use for 'story map', 'user stories', 'what is actually built', 'screen inventory', or whenever a feature or screen changes and docs/story-map must stay in sync."
---

# User story maps

One `stories.yaml` → `REPORT.md`, HTML viewer, topic architecture and one-pager with real screenshots in device frames. Free tools, nothing uploaded.

## When

Use: app docs, "what is built" audit, gap planning, after any user-visible change. Skip: backlog tracking, pixel-perfect design.

**Do this first:** run `init docs/story-map --agents`. It adds a block to the repo's `AGENTS.md` (or `CLAUDE.md`) that tells coding agents to keep the map updated; without it they will not. No such file yet? Use `--agents AGENTS.md` to create one. `validate` warns when none mentions the map.

## Workflow

1. `python3 <skill>/scripts/storymap.py init docs/story-map --agents`. Fill `app` (note commit read), 2–4 `personas`.
2. Define 4–7 `topics`; every flow gets `topic:`.
3. Inventory screens from code (router, components, routes) incl. empty/error/paywall/permission states; `edges:` per flow.
4. Capture screenshots → `image:`; impossible → `not_captured: <why>`.
5. One story per user goal, start `unverified`; promote only what you checked.
6. `theme-from <app-source>` → `theme:`. Gaps, dead ends, risks → `gaps:`.
7. `validate [--strict]` → fix → `build` → open `generated/story-map.html` and `architecture.png`. Check cross-topic arrows against real navigation; isolated topics need edges. Report what is `unverified` and why.

Consider `validate --strict` in CI.

After edits: `validate && build`. Append new items with unique ids; screens need a flow edge and ≥1 story. Overwrite screenshots. Renamed id = find/replace; `validate` lists misses.

## Commands

`DIR` = story-map folder (default: script folder, `docs/story-map`, cwd).

| Command | Does |
|---|---|
| `init [DIR] [--vendor] [--agents [FILE]]` | Create folder + `.gitignore`; vendor script; update AGENTS.md/CLAUDE.md (`FILE` creates it) |
| `validate [DIR] [--strict]` | Exit 1 on errors (`--strict`: warnings too) |
| `build [DIR] [--profile lean\|full] [--formats LIST] [--clean] [--embed-fonts] [--no-graphviz] [--strict] [--force]` | Validate, then write `generated/` |
| `status [DIR]` | Counts per status / flow / persona |
| `set-status [--dir DIR] [--no-build] US-03 built --verified "app, 2026-10-15"` | Edit one story in place (keeps comments), rebuild |
| `theme-from APP_SOURCE [--limit N]` | Read-only scan of colours/fonts → draft `theme:` |

## Build outputs (`generated/`)

| Format | File | Default |
|---|---|---|
| `report` | `REPORT.md`: counts, topics, stories, gaps, image links; each fact once | yes |
| `html` | `story-map.html`: one file, filters, search, click for details, system fonts, screens ≤ 480 px | yes |
| `arch` | `architecture.png`: topic swimlanes | yes |
| `onepager` | `one-pager.png`: status, topics, top gaps, all screens | yes |
| `pdf`, `crops` | `one-pager.pdf`, `architecture/<topic>.png` | opt-in |
| `flows`, `overview`, `flow-map` | `flows/<flow>.png`, `overview.png`, `flow-map.png` (skipped > 300 MP) | opt-in |
| `csv`, `mermaid`, `dot` | `user-stories.csv`, `mermaid/*.mmd`, `dot/*.dot` | opt-in |
| `legacy-md` | old `story-map.md`, `user-stories.md`, `gaps-and-risks.md` | `full` only |

- `--formats a,b` replaces the set; `+csv,flows` / `-onepager` edit the profile; `--profile full` = everything.
- `--clean` deletes superseded files inside `generated/` only; without it they are listed. Graphviz thumbnails go to `<DIR>/.cache/` (gitignored). No `generated/README.md`.
- Details: [`references/outputs.md`](references/outputs.md).

## stories.yaml

One value per line, 2-space indent, `- ` items, `#` comments, `[a, b]` lists; quote values containing `: `. PyYAML if installed, else built-in subset parser.

| Section | Fields |
|---|---|
| `app` | `name`, `platform` (ios/android/web), `version`, `checked`, `summary`, `disclaimer`, `device`, `agents_check` |
| `theme` | optional → [`references/theme.md`](references/theme.md) |
| `topics[]` | `id`, `title`, `description`, `color` (override), `order` |
| `personas[]` | `id`, `name`, `as_a`, `description` |
| `flows[]` | `id`, `title`, `description`, **`topic`**, `edges: ["from -> to: action"]` (label starting `(` = dashed) |
| `screens[]` | `id`, `title`, `flow`, `image` (relative), `not_captured`, `notes`, `where`; overrides: `status`, `topic`, `device` |
| `stories[]` | `id`, `persona`, `want`, `so_that`, `screens: [ids]`, `status`, `verified`, `where`, `notes`; overrides: `story`, `flow`, `topic` |
| `gaps[]` | `id`, `severity` (high/medium/low), `title`, `detail`, `where`, `stories: [ids]` |

- Sentence: "As a {persona.as_a}, I want {want} so that {so_that}." (`want` starts "to …"); `story:` replaces it.
- Defaults: story topic = its first screen's flow topic; screen topic = flow topic; screen status derives from its stories.

| Status | Meaning |
|---|---|
| `built` | Verified in code or running app. `verified:` = how/when (`"code + app, 2026-10-15"`); `where:` = file/PR/endpoint |
| `partly` | Incomplete; `notes` says what is missing |
| `unverified` | Not confirmed (default) |
| `missing` | Not built / planned |

- `validate` errors: missing/duplicate id, unknown refs/topic, bad edge/status/severity/colour, no `want`/`story`, `built` without `verified:`, absolute or `..` image path. Warnings: unused/orphan items, missing screenshot without `not_captured`, `built` without `where:`, `long-field`, `repeated-text` (same ≥ 40-char text in ≥ 3 items), `AGENTS_MISSING` (no repo instruction file mentions the map; silence with `app.agents_check: off`). Full list: [`references/outputs.md`](references/outputs.md).

## Rules

- Never `built` without `verified:`. Unsure → `unverified`. Dead button, stub, untested flagged feature ≠ built.
- Code and app disagree → say so in `notes`. Bump `app.checked` on re-verify. Keep fields short, say things once (the validator warns).
- `stories.yaml` is the only source; never hand-edit `generated/`; commit it.
- Topics, standard set (list order = swimlane order): `onboarding`, `access`, `journey`, `library`, `settings`, `payments`, `support`.
- Never retouch screenshots. Demo account only: no real names, emails, tokens, absolute paths, internal URLs. Third-party app → `app.disclaimer`.

## Looks (all outputs)

Details: [`references/looks.md`](references/looks.md), [`theme.md`](references/theme.md), own frame PNG [`frames.md`](references/frames.md).

- **Theme from the app:** `theme-from` scans tokens; only `primary` required; app font + palette everywhere.
- **Dark mode:** `background:` < 30% luminance or `mode: dark` → black page/lanes, light text, lifted colours, titanium frames.
- **Device frames:** every screenshot framed (iPhone island/notch/home button, Android, tablet, browser, `none`); auto-detected, override with `device:`.
- **No white cards:** device, title, status badge sit on the lane/page background.
- **Topic swimlanes:** `architecture.png` = one coloured lane per topic in `order`, screens in an aligned grid, thick labelled cross-topic arrows.
- **Tree layout:** 2+ outgoing edges → trunk, orthogonal bus, aligned children centred on the parent.
- **Resolution:** screenshots ≥ native pixels (zoom reads all text); never downscaled, the canvas grows. Only HTML embeds reduced copies.
- **Huge images in a repo or PR:** ship one GitHub-friendly preview (≤ ~8000 px wide, e.g. `architecture-preview.png`) plus the full-resolution original as a download link. Never split an image into tiles.

## Capture

Files: `docs/story-map/screens/<screen-id>.png`, one device size per app. More: [`references/capture-details.md`](references/capture-details.md).

| Platform | Helper |
|---|---|
| iOS Simulator | `scripts/capture/ios-simulator.sh <id> [-o DIR] [-d "iPhone 16"] [-u deep-link] [-w SECS] [-m light\|dark]` |
| Android | `scripts/capture/android-emulator.sh <id> [-o DIR] [-s serial] [-u deep-link] [-w SECS] [-n]` |
| Web | `scripts/capture/web-playwright.py --base-url URL --shots capture.json [--out DIR] [--scale 2] [--dark] [--storage-state FILE]` |

## Dependencies and gotchas

- Python 3.8+. Optional: Pillow (all images), PyYAML, fontTools+brotli (`--embed-fonts`), Graphviz (only without Pillow), mermaid-cli.
- "no stories.yaml found" → pass the folder. "multi-line … not supported" → one line per value or install PyYAML. Images skipped → install Pillow. Dashed screen → no image or its stories are `missing`.
