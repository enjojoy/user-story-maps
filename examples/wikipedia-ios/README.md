# Wikipedia (iOS) - story map example (dark theme)

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator (app theme dark) from commit `ca8aaeb95639ca82105bcd5510277d8dde0e420e`; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

A real mobile app documented with the skill, and the example for the **dark theme** (`background: "#000000"`): 7 topics, 27 screens (22 real screenshots, 5 honest placeholders), 27 stories, 5 factual gaps. Colours come from the app's own design tokens (see `theme:` in `stories.yaml`); the app was captured in its own dark theme, so map and screenshots match.

| Look at | File |
|---|---|
| Architecture by topic (swimlanes + cross-topic arrows) | `generated/architecture.png` |
| One-page overview | `generated/one-pager.png` |
| Stories, gaps, topics (text) | `generated/REPORT.md` |
| Clickable viewer (Architecture tab, topic filter) | `generated/story-map.html` |
| Source of truth | `stories.yaml` |

Rebuild (lean): `python3 scripts/storymap.py build examples/wikipedia-ios --clean`. Per-flow diagrams, PDF, CSV etc.: add `--formats +flows,pdf,csv` or `--profile full`.

## How the screenshots were made
- Source: <https://github.com/wikimedia/wikipedia-ios> at the commit above, built with `xcodebuild` for an iPhone simulator (iOS 27, 6.3-inch class), status bar fixed to 09:41. Screens are shown at half resolution (603 x 1311).
- The app has its own UI-test suite (robot pattern, offline fixtures, test-plan configurations that pass `-WMFAppThemeName`). The onboarding screenshots come from its `testOnboardingScreenshots`; the rest from a small throwaway test class, [`capture/StoryMapShotsUITests.swift`](capture/StoryMapShotsUITests.swift), that opens each screen and attaches a screenshot. Run with the test plan's `English (Dark)` configuration (`xcodebuild test ... -only-test-configuration "English (Dark)"`) and exported from the `.xcresult` with `xcrun xcresulttool export attachments`. No account was used and nothing was typed except a search term ("Dog") and a find-in-article term.
- UI tests run in **fixture mode**, so feed and article content is bundled test data, not live Wikipedia (gap G-05).
- Local build tweaks (not part of this repo, listed so the run is reproducible): unsigned simulator build (`CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=NO`), and the `rive-ios` binary dependency pointed at a locally downloaded copy.
- Screens that would show device-specific information (Places map region, donation page country/currency) or only an offline error (For You feed, lead image viewer) are **not published**; they appear as dashed placeholders with the reason.

## Licence notes
- The app source is MIT (see the upstream repository). This example contains no app source, only screenshots, a test snippet written for this example, and generated documents (MIT, like the rest of this repo).
- Screenshots contain Wikipedia/Wikimedia trademarks and Wikipedia article content (CC BY-SA 4.0: the shown article extract and images come from Wikipedia and its contributors; attribution is given by this notice). Keep the notice if you redistribute them, and remove the example if you do not want to carry third-party content.
- Gelasio, used for headings in the generated PNGs/HTML, is licensed under the SIL Open Font License; it is downloaded on demand (never committed as a file) to draw the PNGs; the OFL permits redistribution. The HTML viewer uses a system font stack and embeds no font. (The app itself uses Georgia, which is proprietary and not bundled.)
