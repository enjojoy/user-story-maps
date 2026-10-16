# Open Golf (iOS) - story map report

_Generated from `stories.yaml` by storymap.py - edit the source, not this file._

ios · master @ b9029f1 · checked 2026-10-16

An open-source 3D minigolf game in C - drag back to aim, release to putt, sink the ball in 20 hand-made holes.

> Unofficial illustration of the open-source Open Golf game by Michael Gerdes (MIT, github.com/mgerdes/Open-Golf); not affiliated with or endorsed by the author. Screenshots captured 2026-10-16 in the iOS simulator from commit b9029f1e80c3110ae3d4fc9300854bdaeef96508. Kenney Nature Kit models are CC0; see README.

**14 stories:** 🟢 12 built · 🟠 1 partly · ⚪ 1 missing
Built = checked in code/running app (see Verified); unverified = not checked yet.

[architecture.png](architecture.png) · [one-pager.png](one-pager.png) · [story-map.html](story-map.html)

## Topics

| Topic | Screens | Stories | Status counts | Flows |
|---|---|---|---|---|
| First launch | 1 | 1 | 🟢 1 | 1 · Start |
| Levels and progress | 4 | 4 | 🟢 3 · 🟠 1 | 2 · Level grid |
| Playing a hole | 8 | 7 | 🟢 7 | 3 · Play a hole |
| Pause and exit | 1 | 1 | 🟢 1 | 4 · Pause menu |

- First launch -> Levels and progress: Tap Play
- Levels and progress -> Playing a hole: Tap level 1
- Playing a hole -> Pause and exit: Tap the pause button

## Stories

### First launch

The title screen with its single Play button.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-01 | As a first-time player, I want to open the game and start playing with one tap so that I do not have to set anything up. | [Title screen](../screens/title.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/ui.c (title screen)`; note: No account, login or settings step exists. |

### Levels and progress

The level grid with locks and best scores, and the courses behind it.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-04 | As a casual player, I want to pick a level from a grid so that I can go straight to the hole I want. | [Level select (fresh install)](../screens/level-select.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/ui.c (level select scroll box)`; note: The grid scrolls; 20 tiles in rows of four. |
| US-05 | As a score chaser, I want to unlock the next level by finishing the current one so that I move through the game in order. | [Level select (fresh install)](../screens/level-select.png), [Level select (after level 1)](../screens/level-select-progress.png) | 🟢 built | verified: simulator, finished level 1, then level 2 opened, 2026-10-16; where: `src/golf/ui.c, storage key stroke_count_level_N` |
| US-06 | As a score chaser, I want to see my best stroke count on each level so that I know what to beat. | [Level select (after level 1)](../screens/level-select-progress.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/game.c (stores the lowest count)`; note: Best scores live in a local file only. |
| US-13 | As a casual player, I want to play later courses with new obstacles so that the game stays interesting. | [Level 2 start](../screens/level-2.png), [Level 10 start](../screens/level-10.png) | 🟠 partly | verified: simulator, opened levels 2 and 10 only, 2026-10-16; where: `data/levels/level-N.level`; note: Level 10 was opened after seeding the save; the other 18 levels were not played. |

### Playing a hole

Load a level, learn the controls, aim and putt, sink the ball, see the stroke count.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-02 | As a first-time player, I want to be told how to aim and set power so that I can take my first shot without guessing. | [Hint - aim and set power](../screens/tutorial-aim.png) | 🟢 built | verified: simulator, fresh install, 2026-10-16; where: `src/golf/ui.c (tutorial 0)` |
| US-03 | As a first-time player, I want to learn that I can rotate the camera so that I can see the hole from other angles. | [Hint - rotate the camera](../screens/tutorial-camera.png) | 🟢 built | verified: simulator, fresh install, 2026-10-16; where: `src/golf/ui.c (tutorial 2)`; note: The release-to-hit hint appears on the aiming screen. |
| US-07 | As a casual player, I want to see which level is loading and which one I am on so that I know the game is working. | [Loading a level](../screens/loading.png), [Level banner](../screens/level-intro.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/ui.c (loading level, level_num_text)` |
| US-08 | As a casual player, I want to drag back from the ball and see the power before I let go so that I can control the shot. | [Aiming](../screens/aiming.png) | 🟢 built | verified: simulator, scripted drag, 2026-10-16; where: `src/golf/ui.c (aim circle)`; note: Touch input was injected by a local capture patch, not by a finger. |
| US-09 | As a casual player, I want to watch the ball roll and move the camera while it does so that I can follow the shot. | [Ball rolling](../screens/watching-ball.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/ui.c (watching ball)` |
| US-10 | As a casual player, I want to see the ball drop into the hole so that the shot feels finished. | [Ball drops into the hole](../screens/in-hole.png) | 🟢 built | verified: simulator, 2026-10-16; where: `src/golf/game.c (celebration state)`; note: Captured mid-animation; the camera pulls in on the ball. |
| US-11 | As a casual player, I want to see my stroke count and choose Next, Retry or Exit so that I can carry on or try for a better score. | [Success panel](../screens/success.png) | 🟢 built | verified: simulator, 2 strokes then Next, 2026-10-16; where: `src/golf/ui.c (finished menu)`; note: Next is hidden on the last level. |

### Pause and exit

The pause menu. The game has no settings screen, account or store.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-12 | As a casual player, I want to pause, resume, retry or leave a hole so that I can stop without losing my place. | [Pause menu](../screens/paused.png) | 🟢 built | verified: simulator, Resume and Exit used, 2026-10-16; where: `src/golf/ui.c (paused menu)`; note: Retry was not tapped. |

### Unassigned

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-14 | As a casual player, I want to mute sound or change settings so that I can play quietly. |  | ⚪ missing | verified: code search, 2026-10-16; note: No settings screen exists; audio has per-sound volume in code only. |

## Gaps and risks

### High

- **G-01 - Not launchable when rebuilt with the iOS 27 SDK** - The 2022 Sokol iOS code uses a plain UIApplicationDelegate with no UIScene lifecycle, so a build made with Xcode 27 exits at launch. The captures only worked after the binary's recorded SDK version was set to 18 on a local copy. Where: `src/3rd_party/sokol/sokol_app.h (iOS)`. Stories: US-01.

### Medium

- **G-02 - No settings, sound control or reset** - There is no way to mute audio, change controls or clear saved progress from inside the game. Where: `whole app`. Stories: US-14.

### Low

- **G-03 - Pause button overlaps the status bar** - On an iPhone with a Dynamic Island the pause button sits under the clock and battery icons, because the layout ignores safe areas. Where: `Gameplay screens`. Stories: US-12.
- **G-04 - Scene is drawn at 1x resolution** - main.c sets high_dpi to false, so the 3D scene is rendered at 402 x 874 and upscaled on a 3x phone; edges look soft next to system text. Where: `src/golf/main.c`. Stories: US-08.
- **G-05 - Level grid does not scroll back flush** - After scrolling to the bottom and back up, the first row of tiles stayed partly cut off until the game was relaunched. Where: `Level select`. Stories: US-04.
