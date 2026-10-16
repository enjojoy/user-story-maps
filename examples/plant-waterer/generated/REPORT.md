# Plant Waterer - story map report

_Generated from `stories.yaml` by storymap.py - edit the source, not this file._

ios · demo build 1.0 · checked 2026-10-15

A fictional app that reminds people to water their houseplants.

**16 stories:** 🟢 6 built · 🟠 4 partly · 🟣 2 unverified · ⚪ 4 missing
Built = checked in code/running app (see Verified); unverified = not checked yet.

[architecture.png](architecture.png) · [one-pager.png](one-pager.png) · [story-map.html](story-map.html)

## Topics

| Topic | Screens | Stories | Status counts | Flows |
|---|---|---|---|---|
| Onboarding | 2 | 3 | 🟢 2 · 🟠 1 | 1 · Getting started |
| Main user journey | 4 | 5 | 🟢 2 · 🟠 3 | 2 · Plants and watering |
| Reminders | 3 | 3 | 🟢 1 · 🟣 1 · ⚪ 1 | 3 · Reminders |
| Settings & sharing | 3 | 5 | 🟢 1 · 🟣 1 · ⚪ 3 | 4 · Settings and sharing |

- Onboarding -> Main user journey: Tap Skip for now, Tap Save
- Main user journey -> Onboarding: Tap +
- Main user journey -> Reminders: Tap Edit reminder
- Reminders -> Main user journey: Tap the notification
- Main user journey -> Settings & sharing: Tap Settings tab
- Settings & sharing -> Reminders: Tap Default reminder time

## Stories

### Onboarding

First launch up to the first plant.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-01 | As a plant beginner, I want to understand what the app does before I add anything so that I know it is worth my time. | [Welcome](../screens/welcome.png) | 🟢 built | verified: app, 2026-10-15; where: `src/screens/Welcome` |
| US-02 | As a plant beginner, I want to add my first plant by typing its name so that I can start tracking it in under a minute. | [Welcome](../screens/welcome.png), [Add a plant](../screens/add-plant.png) | 🟢 built | verified: code + app, 2026-10-15; where: `src/screens/AddPlant` |
| US-03 | As a plant beginner, I want to pick my plant from a list of common houseplants so that I get a sensible watering schedule without guessing. | [Add a plant](../screens/add-plant.png) | 🟠 partly | where: `src/data/species.json`; note: Only 4 species in the list so far. |

### Main user journey

Seeing plants and watering them - the reason people open the app.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-04 | As a busy gardener, I want to see all my plants and which ones are thirsty today so that I water the right ones first. | [My plants](../screens/plant-list.png) | 🟢 built | verified: app, 2026-10-15; where: `src/screens/PlantList` |
| US-05 | As a busy gardener, I want to mark a plant as watered in one tap so that logging never feels like a chore. | [Plant detail](../screens/plant-detail.png), [Watered! (confirmation)](../screens/watered.png) | 🟢 built | verified: code + tests, 2026-10-15; where: `src/screens/PlantDetail, tests/water.test`; note: No undo (see G-02). |
| US-06 | As a busy gardener, I want to see how often I watered a plant so that I can spot over- or under-watering. | [Plant detail](../screens/plant-detail.png), Watering history | 🟠 partly | where: `src/screens/History`; note: Screen exists but shows a raw list, no chart. |
| US-10 | As a plant beginner, I want to see light and water tips for my plant so that I give it the right care. | [Plant detail](../screens/plant-detail.png) | 🟠 partly | where: `src/screens/PlantDetail`; note: Light tip only; no watering-amount tip. |
| US-11 | As a busy gardener, I want to remove a plant I no longer own so that my list stays relevant. | [My plants](../screens/plant-list.png) | 🟠 partly | where: `src/screens/PlantList`; note: Swipe-to-delete works but asks for no confirmation. |

### Reminders

Custom topic - watering reminders and notification permission.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-07 | As a busy gardener, I want to set a custom reminder time for each plant so that reminders fit my day. | [Reminder schedule](../screens/reminders.png), [Plant detail](../screens/plant-detail.png) | 🟢 built | verified: app, 2026-10-15; where: `src/screens/Reminders` |
| US-08 | As a plant beginner, I want to get a push reminder when a plant is thirsty so that I do not have to remember anything. | [Allow notifications (system alert)](../screens/notif-permission.png), [Reminder notification](../screens/push.png) | 🟣 unverified | where: `src/notifications`; note: Push delivery not checked on a device after the last release. |
| US-09 | As a busy gardener, I want to snooze a reminder for a day so that I am not nagged when it rains. | [Reminder notification](../screens/push.png), [Reminder schedule](../screens/reminders.png) | ⚪ missing | note: Snooze row on the Reminders screen is a disabled placeholder. |

### Settings & sharing

Preferences and sharing the garden with a plant sitter.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-12 | As a busy gardener, I want to change the default reminder time for all plants so that I set it once. | [Settings](../screens/settings.png), [Reminder schedule](../screens/reminders.png) | 🟢 built | verified: app, 2026-10-15; where: `src/screens/Settings` |
| US-13 | As a busy gardener, I want to invite a plant sitter to my garden so that my plants survive my holiday. | [Settings](../screens/settings.png), Share my garden | ⚪ missing |  |
| US-14 | As a friend who waters plants while the owner is away, I want to see which plants to water this week so that I do not have to ask the owner. | Sitter checklist | ⚪ missing |  |
| US-15 | As a friend who waters plants while the owner is away, I want to tick plants off and notify the owner so that the owner knows everything is fine. | Sitter checklist, [Watered! (confirmation)](../screens/watered.png) | ⚪ missing |  |
| US-16 | As a busy gardener, I want to export my plants and watering log so that my data is never locked in. | [Settings](../screens/settings.png) | 🟣 unverified | where: `src/export`; note: Code exists; never run against real data. |

## Gaps and risks

### High

- **G-01 - Reminders silently fail when notifications are denied** - If the user taps Don't Allow, the app never says reminders are off and offers no in-app fallback. Where: `src/notifications`. Stories: US-08.

### Medium

- **G-02 - No undo after Water now** - An accidental tap logs a watering and resets the schedule, with no way to reverse it. Where: `src/screens/PlantDetail`. Stories: US-05.
- **G-03 - Empty plant list after Skip for now has no guidance** - Users who skip onboarding land on a blank list with no hint to tap +. Stories: US-01, US-04.

### Low

- **G-04 - Watering history not captured** - The screen needs 30 days of demo data before it can be screenshotted. Stories: US-06.
