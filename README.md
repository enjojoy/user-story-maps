# user-story-maps

**One editable `stories.yaml` → a story map of your app with real screenshots, topic swimlanes and the app's own look.** Topics, personas, flows, screens and user stories live in one file; one command writes a canonical `REPORT.md`, a clickable HTML viewer, an architecture-by-topic image and a one-pager. Free tools only (Python 3, optional Pillow). Nothing leaves your machine.

![Architecture by topic of the Wikipedia iOS example](examples/wikipedia-ios/generated/architecture.png)

*[Wikipedia iOS](https://github.com/wikimedia/wikipedia-ios) (dark theme), from [`examples/wikipedia-ios/stories.yaml`](examples/wikipedia-ios/stories.yaml): simulator screenshots in topic swimlanes, thick arrows where users cross topics. Unofficial illustration of the open-source app (MIT); not affiliated with the Wikimedia Foundation. Captured 2026-10-15 from commit `ca8aaeb95639ca82105bcd5510277d8dde0e420e`; trademarks and content belong to their owners (Wikipedia content CC BY-SA).*

## Quick start
```bash
python3 scripts/storymap.py build examples/plant-waterer           # fictional quickstart
python3 scripts/storymap.py build examples/wikipedia-ios           # real-app example (dark)
python3 scripts/storymap.py init docs/story-map                    # your app: stories.yaml, screens/, .gitignore
python3 scripts/storymap.py theme-from path/to/app/source          # optional: draft theme: from the app's tokens
python3 scripts/storymap.py validate docs/story-map && python3 scripts/storymap.py build docs/story-map
```
Add [`templates/AGENTS-snippet.md`](templates/AGENTS-snippet.md) to your `AGENTS.md` so coding agents keep the map current. Agents: read [`skills/user-story-maps/SKILL.md`](skills/user-story-maps/SKILL.md).

## What you get (lean by default)
| In `generated/` | |
|---|---|
| `REPORT.md` | **the** text output: status counts, topics, every story once (evidence, screens), gaps by severity |
| `story-map.html` | one file (< 2 MB), filters, search, click a story or screen for details |
| `architecture.png` | screens in device frames, coloured topic swimlanes, cross-topic arrows |
| `one-pager.png` | status, topic map, top gaps, every screen |

Opt-in with `--formats +name` or `--profile full`: `pdf`, `crops` (per-topic architecture crops), `flows`, `overview`, `flow-map`, `csv`, `mermaid`, `dot`, `legacy-md`. `--clean` removes superseded files in `generated/`. Details: [`references/outputs.md`](skills/user-story-maps/references/outputs.md).

## Features
- **Topics:** every flow has a topic; swimlanes show how the app is structured and where users cross areas.
- **Theme from the app:** `theme-from` scans design tokens; only `primary` is needed; app font and palette in every output.
- **Dark mode:** `background: "#000000"` (or `mode: dark`) darkens page, lanes, text, colours and frames.
- **Device frames:** every screenshot framed (iPhone, Android, tablet, browser), auto-detected, drawn with Pillow (no artwork bundled); no white cards behind devices.
- **Tree layout:** branching flows draw one trunk, an orthogonal bus and aligned children.
- **Full resolution:** image outputs draw each screenshot at ≥ native pixels so zoom reads all text; only the HTML embeds reduced copies (≤ 480 px).
- **Honest by design:** `built · partly · unverified · missing`; `built` requires `verified:` (how and when). The validator also warns about over-long and repeated text.

Rules and options: [`looks.md`](skills/user-story-maps/references/looks.md), [`theme.md`](skills/user-story-maps/references/theme.md).

## Examples
| Example | Shows |
|---|---|
| [`examples/wikipedia-ios/`](examples/wikipedia-ios/) | Real app captured in the iOS simulator, dark theme: 7 topics, 27 screens, 27 stories (20 built / 1 partly / 6 unverified), 5 gaps |
| [`examples/plant-waterer/`](examples/plant-waterer/) | Fictional quickstart with mock screens (16 stories, 4 topics) |

## Layout
```
skills/user-story-maps/SKILL.md    workflow, schema, rules (+ references/: outputs, looks, theme, frames, capture)
scripts/storymap.py                the generator (one file; stdlib + optional Pillow/PyYAML/Graphviz)
scripts/capture/                   screenshot helpers: iOS Simulator, Android emulator, web (Playwright)
templates/                         stories.yaml skeleton, AGENTS.md snippet, .gitignore snippet
examples/                          wikipedia-ios, plant-waterer
tests/                             python3 -m unittest discover -s tests
```
`storymap.py` is not copied into your repo by default; `init --vendor` copies it.

## Requirements
Python 3.8+. Optional: `pillow` (images, frames, one-pager; tests skip numpy checks without `numpy`), `pyyaml`, Graphviz, mermaid-cli, `fonttools`+`brotli` (`--embed-fonts`). A `google_font: true` font is cached in `~/.cache/storymap/fonts`, never in the repo.

## Privacy and third-party content
Screenshots and stories end up in your repo: demo account and fake data only, no credentials or session files. For someone else's app add `app.disclaimer` and check the screenshot licence ([`examples/wikipedia-ios/README.md`](examples/wikipedia-ios/README.md), [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)).

## License
MIT, see [LICENSE](LICENSE). Example screenshots show third-party content under its own terms.
