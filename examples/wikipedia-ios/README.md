# Wikipedia (iOS) - story map example

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator from commit `ca8aaeb95639ca82105bcd5510277d8dde0e420e`; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

A real mobile app documented with the skill: 7 topics, 30 screens (26 real screenshots, 4 honest placeholders), 29 stories, 5 factual gaps. The map is styled with the app's own design tokens (see `theme:` in `stories.yaml`).

| Look at | File |
|---|---|
| Architecture by topic (swimlanes + cross-topic arrows) | `generated/architecture.png` |
| One-page overview | `generated/one-pager.png` / `.pdf` |
| One diagram per flow | `generated/flows/reading.png`, `first-run.png`, ... |
| Clickable viewer (Architecture tab, topic filter) | `generated/story-map.html` |
| Source of truth | `stories.yaml` |

Rebuild: `python3 scripts/storymap.py build examples/wikipedia-ios`

## How the screenshots were made
- Source: <https://github.com/wikimedia/wikipedia-ios> at the commit above, built with `xcodebuild` for an iPhone simulator (iOS 27, 6.3-inch class), light mode, status bar fixed to 09:41. Screens shown at half resolution (603 x 1311).
- The app has its own UI-test suite (robot pattern, offline fixtures, `-WMFAppThemeName light|dark` launch option). The screenshots come from its onboarding screenshot test plus a small throwaway test class, [`capture/StoryMapShotsUITests.swift`](capture/StoryMapShotsUITests.swift), that opens each screen and attaches a screenshot; they were exported from the `.xcresult` with `xcrun xcresulttool export attachments`. No account was used and nothing was typed except a search term ("Dog") and a find-in-article term.
- Because the UI tests run in **fixture mode**, feed and article content is bundled test data, not live Wikipedia. That is recorded as gap G-05 and in the story notes.
- Local build tweaks (not part of this repo, listed so the run is reproducible): ad-hoc code signing for the simulator, and the `rive-ios` binary dependency pointed at a locally downloaded copy because the Swift package fetch waited on a keychain prompt.
- Screens that would show device-specific information (Places map region, donation page country/currency) are **not published**; they appear as dashed placeholders with the reason.

## Licence notes
- The app source is MIT (see the upstream repository). This example contains no app source, only screenshots, a test snippet written for this example, and generated documents (MIT, like the rest of this repo).
- Screenshots contain Wikipedia/Wikimedia trademarks and Wikipedia article content (CC BY-SA 4.0: the shown article extract and images come from Wikipedia and its contributors; attribution is given by this notice). Keep the notice if you redistribute them, and remove the example if you do not want to carry third-party content.
- Gelasio, used for headings in the generated PNGs/HTML, is licensed under the SIL Open Font License; it is downloaded on demand (never committed as a file); the OFL permits redistribution, and two weights are embedded as data URIs in `generated/story-map.html` so the viewer works offline. (The app itself uses Georgia, which is proprietary and not bundled.)
