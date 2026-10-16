# Third-party notices

This repository (MIT, see [LICENSE](LICENSE)) bundles **no third-party device artwork or code from other projects**. The examples bundle the open-licensed fonts listed below. This file records what was evaluated, what was decided, and the content that appears in the examples.

## Device frames (mockups): decision

**Chosen: frames drawn procedurally with Pillow** (`scripts/storymap.py`, "device frames"). Rounded rectangles, ellipses and gradients are computed from scratch at 3x resolution and downsampled; they are original drawings of generic phone/tablet/browser shapes, licensed MIT with the rest of the repository. No Apple, Google or Meta artwork, no downloaded files.

**Optional: user-supplied frames** via `frames.json` (see `skills/user-story-maps/references/frames.md`). A user may download a frame they are entitled to use and point the generator at it. Such files are read from the user's disk, **never committed**, and `.gitignore` / `templates/gitignore-snippet.txt` exclude `frames.json` and `frames/`.

**Why no real iPhone frame is bundled.** A real iPhone frame found online was preferred if its licence allows redistribution in a public repository. Every candidate was checked (licence text or terms page, 2026-10-15). None gives a clear right to redistribute iPhone-shaped artwork:

| Candidate | Source | Licence / terms found | Verdict |
|---|---|---|---|
| Apple Design Resources (device bezels / product frames) | https://developer.apple.com/design/resources/ | Apple's licence for Design Resources restricts use to creating mockups and prohibits redistributing the files; Apple trade dress | **Not bundled** (redistribution restricted). Users may download them for themselves. |
| Meta Design device frames | https://design.facebook.com/ (device frames) | "Copyright (c) 2022 Meta. All rights reserved", with a note that the underlying device designs belong to the manufacturers | **Not bundled** (all rights reserved). |
| `jonnyjackson26/device-frames-media` | https://github.com/jonnyjackson26/device-frames-media | GitHub shows no licence and the repo has no LICENSE file; the frames are derived from Apple/Google marketing assets (marketing colour names) | **Not bundled** (no licence, derived artwork). |
| `jamesjingyi/mockup-device-frames` | https://github.com/jamesjingyi/mockup-device-frames | Credits Apple Developer Resources and Meta frames as its sources | **Not bundled** (inherits the restrictions above). |
| `sneas/telephone` | https://github.com/sneas/telephone | MIT (c) 2024 Dimah Snisarenko for the package; inline SVG frames (iPhone 16 Max, Pixel 9 Pro, iPad Air 13, Android tablet) with undocumented provenance, plausibly traced from Apple's bezels | **Not bundled**: the MIT notice cannot be relied on for artwork whose origin is unknown. |
| `neogeek/ios-device-svg-templates` | https://github.com/neogeek/ios-device-svg-templates | MIT, archived; iPhone 5c only | Licence fine, but an obsolete device that matches none of the supported models. |
| `devices.css` (picturepan2, marvelapp) | https://github.com/picturepan2/devices.css | MIT; CSS-only original drawings | Compatible licence, but CSS cannot be rasterised by the Pillow renderer; the procedural frames cover the same ground. |
| Getscreeny frames, Fra.me | https://getscreeny.app/frames , https://withfra.me | Free to use in your own work; **redistributing the frames as an asset pack is prohibited** | **Not bundled.** |
| Generic CC0 phone frame (Pixy) | pixy.org | CC0, but a generic non-iPhone phone | Not needed; the procedural frame is equivalent. |

Result: **no suitably licensed iPhone frame exists for redistribution in a public repository**, so the procedural Pillow frame is the default and the fallback, and real frames are supported only as an uncommitted, user-supplied option. If you add a frame to a private fork, record its source URL and licence here.

Device and product names (iPhone, Dynamic Island, Android, ...) are trademarks of their owners and are used only descriptively; the drawn frames are generic and unaffiliated.

## Fonts
- **Gelasio Regular + Bold** (copyright 2022 The Gelasio Project Authors, SIL Open Font License 1.1, https://fonts.google.com/specimen/Gelasio): committed under `examples/wikipedia-ios/fonts/`, with `OFL.txt`. Used for headings in the Wikipedia example (a look-alike for the app's Georgia).
- **Fira Sans Regular + Bold** (copyright 2012-2015 The Mozilla Foundation and Telefonica S.A., SIL Open Font License 1.1, https://fonts.google.com/specimen/Fira+Sans): committed under `examples/open-golf/fonts/`, with `OFL.txt`. Used for headings in the Open Golf example (the game's own UI font).
- These font files are unmodified from Google Fonts and are used only to draw the PNGs. The HTML viewer uses system fonts and embeds no font by default (opt-in `embed_fonts` embeds a WOFF2 subset, which the OFL allows). Proprietary fonts (Georgia, SF Pro, ...) are only referenced by name, never bundled.
- `google_font` is opt-in and off by default. Any font you name in `theme:` with `google_font: true` is fetched only if its licence is open (OFL/Apache) and is cached outside the repository.

## Example content
- `examples/wikipedia-ios/`: screenshots and names of the open-source **Wikipedia iOS app** (MIT, https://github.com/wikimedia/wikipedia-ios), captured in the iOS Simulator on 2026-10-15 (app theme dark) from commit `ca8aaeb95639ca82105bcd5510277d8dde0e420e`.
  - Unofficial illustration; not affiliated with or endorsed by the Wikimedia Foundation. Trademarks and content belong to their owners.
  - The app source is MIT (see the upstream repository). The example contains no app source, only screenshots, a test snippet written for this example (`examples/wikipedia-ios/capture/StoryMapShotsUITests.swift`) and generated documents (MIT, like the rest of this repo).
  - Screenshots contain Wikipedia/Wikimedia trademarks and Wikipedia article content (CC BY-SA 4.0: the shown article extract and images come from Wikipedia and its contributors; attribution is given by this notice). Keep this notice if you redistribute them, and remove the example if you do not want to carry third-party content.
  - Gelasio (headings in the generated PNGs) is covered under Fonts above. The app itself uses Georgia, which is proprietary and not bundled.
- `examples/open-golf/`: screenshots and names of the open-source **Open Golf** game (MIT, copyright (c) 2020 Michael Gerdes, https://github.com/mgerdes/Open-Golf), captured in the iOS Simulator on 2026-10-16 from commit `b9029f1e80c3110ae3d4fc9300854bdaeef96508` (the last commit, March 2022).
  - Unofficial illustration; not affiliated with or endorsed by the author. The example contains no game source, only screenshots, generated documents and a story file (MIT, like the rest of this repo); the screens are screenshots of MIT-licensed software (licence checked in the upstream `LICENSE`).
  - Art, as verified in the upstream repo (2026-10-16): the upstream README lists "Kenney Art Assets" (https://kenney.nl/assets) under 3rd party libraries without naming packs. `data/models/nature_kit/License.txt` states **Kenney Nature Kit 2.1, Creative Commons Zero (CC0)**, and `data/models/flag_red.obj` carries a "Created by Kenney" header. The trees, rocks, plants and flag seen in the screenshots come from these, so they are CC0 (attribution is optional and given here anyway).
  - Not verified: the repo ships no licence file for the sound effects (names such as `drop_003.ogg`), the UI icons (`data/textures/ui_icons`), the fonts (Fira Sans, Castle Rock, Font Awesome) or the pixel-pack textures. Their file names suggest Kenney packs or open fonts, but this was **not confirmed**, so no licence is claimed for them. The screenshots show the Castle Rock logo font, Fira Sans text and the icons; remove the example if you cannot accept that. Fira Sans (headings in the generated images) is covered under Fonts above.
- `tests/fixtures/sample-app/`: fictional app, solid-colour placeholder images drawn for tests; nothing third-party.

## Tooling used at run time (not bundled)
Python standard library; optional Pillow (HPND licence), Graphviz (EPL), PyYAML (MIT), Playwright, mermaid-cli. They are installed by the user, not shipped here.
