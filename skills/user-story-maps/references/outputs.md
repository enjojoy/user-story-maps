# Build outputs, profiles, HTML viewer

## Profiles and formats
- `--profile lean` (default): `html`, `arch`, `onepager`, `report`.
- `--profile full`: lean + `pdf`, `crops`, `flows`, `overview`, `flow-map`, `csv`, `mermaid`, `dot`, `legacy-md` (the old behaviour; `REPORT.md` is still written).
- `--formats a,b` replaces the set. `--formats +csv,flows` adds to, `--formats -onepager` removes from the profile. Unknown names → error listing the valid ones.
- Deprecated `--only docs,mermaid,diagrams,html,pdf` maps to formats.
- `--clean`: after a successful build, delete files in `generated/` that this build did not write and that older versions produced. Never touches `screens/` or `stories.yaml`. Without it, stale files are only listed.

## REPORT.md
One text file, each fact once, GitHub-renderable, deterministic (no timestamps), no Mermaid:
1. Title, source note, platform · version · checked, summary, disclaimer.
2. Status counts (built / partly / unverified / missing).
3. Links to the images/viewer written by this build.
4. `## Topics` table (screens, stories, status counts, flows) + cross-topic connections.
5. `## Stories` per topic: `ID | Story | Screens | Status | Evidence` (evidence = verified, where, notes).
6. `## Gaps and risks` by severity.
Need CSV (`csv`), Mermaid for GitHub diagrams (`mermaid`), or the old three Markdown files (`legacy-md`)? Opt in.

## HTML viewer (`story-map.html`)
- One self-contained file, typically < 2 MB, no network. System font stack unless `embed_fonts`.
- Screens embedded at ≤ 480 px; architecture preview ≤ 2400 px with a link to the full-resolution `architecture.png` next to it.
- Tabs: Architecture, Flows, Stories (compact rows; click a row for where/verified/notes), Map, Gaps, Overview (only when `overview.png` exists). Click a screen for its details. Filters: topic, status, persona; search; keyboard navigation.

## Cache and git
- Graphviz node thumbnails (`dot` format or Graphviz fallback only) go to `<DIR>/.cache/thumbs/`; the build adds `.cache/` to `<DIR>/.gitignore`.
- `init` writes `<DIR>/.gitignore` (`.cache/`, `frames.json`, `frames/`, session and env files). `storymap.py` is no longer copied into the app repo unless `init --vendor`.
- Commit `stories.yaml`, `screens/`, `generated/`.

## Validator
- Errors: missing/duplicate id; flow/screen without a known topic; unknown screen/persona/flow/topic/story/device refs; bad edge syntax, status, severity or `theme:` colour; no `want`/`story`; `built` without `verified:`; absolute or `..` image path.
- Warnings: no `topics:` (→ "General"), unused topic, bad `theme.device.style` (→ `black`), missing screenshot without `not_captured`, unused screen, screen in no flow, story without screens (unless `missing`), `built` without `where:`, empty flow, persona without stories, `AGENTS_MISSING` (no instruction file in the repo mentions the story map; run `init <dir> --agents` or paste `templates/AGENTS-snippet.md`; silence with `app.agents_check: off`).
- Text warnings: `long-field`: story want/so_that/story > 160 chars; story/screen notes, where, verified > 200; gap title > 100, detail > 400, where > 120. `repeated-text`: the same text ≥ 40 chars in ≥ 3 items of one field. Fix by shortening or saying it once.
