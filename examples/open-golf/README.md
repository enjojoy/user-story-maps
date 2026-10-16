# Open Golf (iOS) - story map example (light theme)

> Unofficial illustration of the open-source Open Golf game by Michael Gerdes ([mgerdes/Open-Golf](https://github.com/mgerdes/Open-Golf), MIT licence); not affiliated with or endorsed by the author. Screenshots captured 2026-10-16 in the iOS simulator from commit `b9029f1e80c3110ae3d4fc9300854bdaeef96508` (the last commit, March 2022).

A small 3D game documented with the skill: 4 topics, 14 screens (all real screenshots), 14 stories, 5 factual gaps. The theme is taken from the game itself (button blue, aim-line green, sky blue, Fira Sans), so the map matches the screenshots.

| Look at | File |
|---|---|
| Architecture by topic (preview, 8000 px wide) | `generated/architecture-preview.png` |
| Architecture by topic (full resolution, 11203 px wide) | `generated/architecture.png` |
| One-page overview (preview / full resolution) | `generated/one-pager-preview.png` / `generated/one-pager.png` |
| Stories, gaps, topics (text) | `generated/REPORT.md` |
| Clickable viewer | `generated/story-map.html` |
| Source of truth | `stories.yaml` |

Rebuild (lean): `python3 scripts/storymap.py build examples/open-golf`. The two `*-preview.png` files are plain downscaled copies of the full-size images (GitHub-friendly; no tiles).

## Credits and licence
- **Game and code:** Open Golf, copyright (c) 2020 Michael Gerdes, MIT licence (checked in the repository's `LICENSE`). This example contains no game source, only screenshots, generated documents and a story file (MIT, like the rest of this repo).
- **Kenney art:** the upstream README lists "Kenney Art Assets" (<https://kenney.nl/assets>) under 3rd party libraries. In the repository, `data/models/nature_kit/License.txt` states **Kenney Nature Kit 2.1, Creative Commons Zero (CC0)**, and `data/models/flag_red.obj` carries a "Created by Kenney" header. The trees, rocks, plants and flag seen in the screenshots come from these, so they are CC0 (attribution is optional and given here anyway).
- **Not verified:** the repository ships no licence file for the sound effects (names such as `drop_003.ogg`), the UI icons (`data/textures/ui_icons`), the fonts (Fira Sans, Castle Rock, Font Awesome) or the pixel-pack textures. Their file names suggest Kenney packs or open fonts, but this was **not confirmed** from the repo, so nothing is claimed about them. The screenshots show the Castle Rock logo font, Fira Sans text and the icons; remove the example if you cannot accept that.

## How the screenshots were made
- Source: a shallow clone of the upstream repo, built for the iOS **simulator** (route 1; no macOS fallback was needed) with CMake's Xcode generator and `-DPLATFORM=SIMULATORARM64` (the upstream `build/build-ios.sh` targets a device). Run on an iPhone 18 Pro simulator with iOS 27, status bar at 09:41. Screens are saved at half resolution (603 x 1311); the game itself renders at 1x (see gap G-04).
- Local changes to the throwaway clone only (nothing was published): the hard-coded development team line removed from `CMakeLists.txt`; the bundled x86_64 `cembed` tool rebuilt for arm64 (no Rosetta on the machine); deployment target 15.0; the built binary's recorded SDK version set to 18.0 and re-signed ad hoc, because an app linked with the iOS 27 SDK must adopt the UIScene lifecycle and this 2022 code does not (gap G-01); and a small debug-only patch to `main.c` that reads tap and drag commands from a file so screens could be reached without a finger. No account is needed.
- Reached by real play on a fresh install: title, level select, loading, level banner, both hints, aiming, rolling, hole, success (2 strokes), level 2, pause, level select with "Best 2". **Level 10** was reached after editing the simulator's local save file so levels 1-9 were open; the other levels were not played.
