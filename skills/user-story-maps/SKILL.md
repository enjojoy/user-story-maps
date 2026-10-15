---
name: user-story-maps
description: "Create, update or audit an app's user stories, story map, screen/flow inventory, architecture-by-topic overview or screenshot journey diagrams (iOS, Android, web) from one stories.yaml. Use for 'story map', 'user stories', 'what is actually built', 'screen inventory', or whenever a feature or screen changes and docs/story-map must stay in sync."
---

# User story maps

One `stories.yaml` → stories (md/csv by topic), flow + architecture diagrams with real screenshots, Mermaid, HTML viewer, PDF one-pager. Styled with the app's own palette and font. Free tools; nothing uploaded.

## When to use

- Use: new app docs, "what is built" audit, onboarding, gap planning, after any user-visible change.
- Skip: backlog tracking with assignees/estimates, pixel-perfect design.

## Inputs

App repo (code + runnable app/simulator), demo account with fake data, `scripts/storymap.py`. Examples: `examples/wikipedia-ios/` (real app), `examples/plant-waterer/` (quickstart).

## Workflow

1. `python3 <skill>/scripts/storymap.py init docs/story-map`. Fill `app` (note commit read), 2–4 `personas`.
2. Define 4–7 `topics`; every flow gets `topic:`.
3. Inventory screens from code (router, screen components, URL routes), incl. empty/error/paywall/permission states.
4. Write `edges:` per flow from code or click-through.
5. Capture screenshots → `image:`. Not possible → `not_captured: <why>`.
6. Write stories, one per user goal. Start `unverified`; promote only what you checked.
7. Check `architecture.png`: cross-topic arrows match real navigation; topic with no in/out arrows = missing edge.
8. `storymap.py theme-from <app-source>` → fill `theme:`.
9. Record dead ends, missing states, risks under `gaps:`.
10. `python3 docs/story-map/storymap.py validate [--strict]` → fix → `build` → open `generated/story-map.html`, check PNGs. Tell the user what is `unverified` and why.
11. Paste `templates/AGENTS-snippet.md` into `AGENTS.md`/`CLAUDE.md`. Consider `validate --strict` in CI.

After any later edit: `validate && build`. Add story/screen/flow/topic = append under its section (unique id; screen also needs a flow edge and ≥1 story). Replace screenshot = overwrite same filename. Rename id = find/replace everywhere; `validate` lists misses.

| Command (`DIR` default: script folder, `docs/story-map`, cwd) | Does |
|---|---|
| `init [DIR] [--no-vendor]` | Create folder from template |
| `validate [DIR] [--strict]` | Exit 1 on errors (`--strict`: warnings too) |
| `build [DIR] [--only docs,mermaid,diagrams,html,pdf] [--no-graphviz] [--strict] [--force]` | Validate, regenerate all. Refuses on errors |
| `status [DIR]` | Counts per status / flow / persona |
| `set-status [--dir DIR] [--no-build] US-03 built --verified "app, 2026-10-15"` | Edit one story in place (keeps comments), roll back if invalid, rebuild |
| `theme-from APP_SOURCE_DIR [--limit N]` | Read-only scan of colours/fonts → draft `theme:` |

## stories.yaml

One value per line, 2-space indent, `- ` items, `#` comments, `[a, b]` lists; quote values containing `: `. PyYAML if installed, else built-in subset parser.

| Section | Fields |
|---|---|
| `app` | `name`, `platform` (ios/android/web), `version`, `checked`, `summary`, `disclaimer`, `device` |
| `theme` | optional; see Theme |
| `topics[]` | `id`, `title`, `description`, `color` (override only), `order` (default list order) |
| `personas[]` | `id`, `name`, `as_a`, `description` |
| `flows[]` | `id`, `title`, `description`, **`topic`**, `edges: ["from -> to: action"]` (label starting `(` = dashed) |
| `screens[]` | `id`, `title`, `flow`, `image` (relative), `not_captured`, `notes`, `where`; overrides: `status`, `topic`, `device` |
| `stories[]` | `id`, `persona`, `want`, `so_that`, `screens: [ids]`, `status`, `verified`, `where`, `notes`; overrides: `story`, `flow`, `topic` |
| `gaps[]` | `id`, `severity` (high/medium/low), `title`, `detail`, `where`, `stories: [ids]` |

- Sentence: "As a {persona.as_a}, I want {want} so that {so_that}." → `want` starts "to …". `story:` replaces it whole.
- Defaults: story topic = first screen's flow topic; screen topic = flow topic.
- Screen status derives from its stories (all built → built; built+unverified → unverified; partly/missing mix → partly) unless set.

| Status | Meaning |
|---|---|
| `built` | Verified in code or running app. `verified:` = how/when (`"code + app, 2026-10-15"`); `where:` = file/PR/endpoint |
| `partly` | Incomplete; `notes` says what is missing |
| `unverified` | Not confirmed (default) |
| `missing` | Not built / planned |

`validate` errors: missing/duplicate id; flow/screen without known topic; unknown screen/persona/flow/topic/story/device refs; bad edge syntax, status, severity, `theme:` colour; no `want`/`story`; `built` without `verified:`; absolute or `..` image path. Warnings: no `topics:` (→ "General"), unused topic, bad `theme.device.style` (→ `black`), missing screenshot without `not_captured`, unused screen, screen in no flow, story without screens (unless `missing`), `built` without `where:`, empty flow, persona without stories.

## Rules

- Never `built` without `verified:`. Unsure → `unverified`. Dead button, stub, untested flagged feature ≠ built.
- Code and app disagree → write it in `notes`. Bump `app.checked` on re-verify.
- `stories.yaml` is the only source of truth. Never hand-edit `generated/`; commit it.
- Topics standard set (keep what applies; list order = swimlane order): `onboarding`, `access`, `journey` (core value), `library`, `settings`, `payments`, `support`.
- Never edit screenshots to look better than the app. Demo account only: no real names, emails, tokens, absolute paths, internal URLs. Third-party app → `app.disclaimer`.

## Theme

Look like the app: app font, app background (light or dark), app palette incl. status/gap colours. Only `primary` required; status, severity, topic colours derive from it. No `theme:` → legacy green.

```yaml
theme:
  primary: "#3366CC"         # brand/accent
  text: "#202122"            # optional: background, text, muted, surface, border, secondary (#RRGGBB)
  # background: "#000000"    # dark app: black page + lanes (or `mode: dark`); see Dark below
  heading_font: "Gelasio"    # `font:` = body (default system sans)
  google_font: true          # fetch open-licensed family (cached outside repo)
  # font_file: tools/MyFont.ttf   # redistributable, relative; font_file_bold optional
  # status:   { built: "#00AF89", partly: "#FFCC33", unverified: "#6699FF", missing: "#A2A9B1" }
  # severity: { high: "#DD3333", medium: "#FFCC33", low: "#A2A9B1" }
  # device:   { style: titanium, model: "", badge: label, frames: frames.json }
```

1. Run `theme-from`. By hand: iOS `Assets.xcassets/*.colorset`, Theme/Color/Font Swift; Android `res/values/colors.xml`, `themes.xml`, `res/font/`; web `tailwind.config.*`, CSS `:root { --… }`, token JSON.
2. `primary` = brand/accent; `text`/`border` of the app's own mode. Map success/warning/error → `status:` (built=success, partly=warning, missing=neutral gray) and `severity:`.
3. Fonts: real family name. Bundle only open-licensed (OFL/Apache, or own file). Proprietary/system: name only (used if installed, else fallback) or open look-alike + `google_font: true` (Gelasio for Georgia).
4. Build; view `architecture.png`, `one-pager.png`; tune until readable and status colours stay distinguishable.
5. **Dark**: `background:` darker than 30% luminance (e.g. `"#000000"`) or `mode: dark` (`mode: light` forces light). Everything follows in all outputs: lanes mix toward the background, light text/border, lifted status/topic colours, black text on bright chips, titanium frames (`style: auto`). Give `text`/`muted`/`surface`/`border`/`status:` explicitly to override.

## Looks

| Look | Rule |
|---|---|
| Device frames | Every screenshot, all outputs: `iphone-island`, `iphone-notch`, `iphone-home-button`, `android-generic`, `tablet`, `browser-window`, `none` |
| Frame style | `theme.device.style`: `auto` (default: black; titanium on dark), `black`, `titanium`, `light` |
| No white cards | No white cards behind devices: device, title and status badge sit directly on the lane/page background (transparent in every output, incl. HTML cards and thumbs) |
| Status | Dot + label under device (`theme.device.badge`: `label`/`dot`). No coloured border |
| Not captured | Dashed empty device outline + reason |
| Scaling | Contain by real aspect ratio; never crop/stretch; landscape → rotated frame |
| Resolution | Every screenshot at ≥ native pixels in `architecture.png`, `overview.png`, `flows/*.png`, `one-pager.png`/`.pdf`; zoom reads all text. Never downscale the map; the canvas grows (large PNGs; `architecture/<topic>.png` = full-res crops per topic) |
| Swimlanes | `architecture.png`: one coloured lane per topic, ordered by `topics[].order`; screens in aligned grid rows/columns |
| Architecture arrows | Cross-topic thick, source-topic colour, labelled; in-topic thin grey |
| Branches | 2+ outgoing edges → tree: trunk, orthogonal bus, children on one aligned row (top→bottom) or column (left→right), centred on parent, labels on drops |
| Linear steps | One-to-one = straight arrow. Merges/back-links/skips = orthogonal polylines via side channel, dashed if optional. No long diagonals |

- Device pick: `screens[].device` > `app.device` > `theme.device.model` > auto. Auto: `web` → `browser-window`; `android` → `android-generic`; iOS portrait ratio 0.40–0.50 → `iphone-island` (`iphone-notch` for known sizes, e.g. 1125x2436, 1170x2532), 0.50–0.60 → `iphone-home-button`, 0.60–0.80 → `tablet`; else `browser-window`.
- Own frame PNG via `frames.json`: [`references/frames.md`](references/frames.md). Never commit it.

## Capture

Files: `docs/story-map/screens/<screen-id>.png`. One device size per app. Raw commands, XCUITest, third-party apps: [`references/capture-details.md`](references/capture-details.md).

| Platform | Helper |
|---|---|
| iOS Simulator (macOS + Xcode) | `scripts/capture/ios-simulator.sh <id> [-o DIR] [-d "iPhone 16"] [-u deep-link] [-w SECS] [-m light\|dark]`, `--list` |
| Android | `scripts/capture/android-emulator.sh <id> [-o DIR] [-s serial] [-u deep-link] [-w SECS] [-n]` (adb demo mode unless `-n`) |
| Web | `scripts/capture/web-playwright.py --base-url URL --shots capture.json [--out DIR] [--viewport 1280x800] [--scale 2] [--dark] [--storage-state FILE]`; shots = `[{id, path, wait_for?, click?}]`, default 390×844 @2x |

## Outputs

`generated/`: `story-map.html`, `architecture.png` (+ `architecture/<topic>.png` crops), `one-pager.pdf`/`.png`, `flows/<flow>.png`, `overview.png`, `flow-map.png` (skipped above 300 MP), `story-map.md` (topic table + Mermaid), `user-stories.md`/`.csv`, `gaps-and-risks.md`, `mermaid/*.mmd`, `dot/*.dot`, `thumbs/`.

## Resolution

`build` draws diagrams with Pillow at a zoom chosen so each device's screenshot area is ≥ its source pixels (`native_zoom`), prints the zoom factors and warns if any is below 1.0×. Capture sharp (web 2×); a 780×1688 phone shot gives device areas of at least 780×1688 px, so maps are tens to hundreds of megapixels (10–30 MB PNG). `story-map.html` embeds reduced copies; the PNGs are the full-res files. Graphviz is not used when Pillow is present (it draws small).

## Dependencies

Python 3.8+ (md, csv, Mermaid, HTML). Optional, with fallbacks:
- Pillow → thumbnails, PNG diagrams, PDF, device frames, tree layout (required for trees).
- Graphviz → best layout; else built-in Pillow renderer.
- PyYAML → full YAML; else subset parser.
- mermaid-cli → `.mmd` to PNG (not needed for GitHub).

## Gotchas

- "no stories.yaml found" → pass folder: `build docs/story-map`.
- "multi-line … not supported" → one line per value, or install PyYAML.
- Diagram step skipped → install Pillow or Graphviz. Huge flow PNG → split the flow.
- Grey/dashed screen → no image (`not_captured`) or its stories are `missing`.
- Public repo: no secrets, real user data, internal hostnames, absolute paths; review `screens/` and `where:`.
