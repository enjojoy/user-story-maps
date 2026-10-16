# Looks: what the images and viewer do

Rules the generator follows in every output (set once, nothing to configure unless noted).

## Device frames
- Every screenshot sits in a device frame drawn with Pillow (no artwork bundled; see `THIRD-PARTY-NOTICES.md`). Models: `iphone-island`, `iphone-notch`, `iphone-home-button`, `android-generic`, `tablet`, `browser-window`, `none`.
- Pick order: `screens[].device` > `app.device` > `theme.device.model` > auto. Auto: `web` → `browser-window`; `android` → `android-generic`; iOS portrait ratio 0.40–0.50 → `iphone-island` (`iphone-notch` for known sizes, e.g. 1125x2436, 1170x2532), 0.50–0.60 → `iphone-home-button`, 0.60–0.80 → `tablet`; else `browser-window`.
- Style `theme.device.style`: `auto` (black; titanium on dark), `black`, `titanium`, `light`.
- Landscape shots get a rotated frame. The whole screenshot is always visible: contained by its real aspect ratio, never cropped or stretched.
- Own frame PNG through `frames.json`: [`frames.md`](frames.md). Never commit it.

## Cards, status, placeholders
- No white cards: device, title and status badge sit directly on the lane/page background (transparent in every output, including HTML cards).
- Status = dot + label under the device (`theme.device.badge`: `label` or `dot`); no coloured border.
- `not_captured` → dashed empty device outline with the reason.

## Architecture (topic swimlanes)
- `architecture.png`: one coloured lane per topic, ordered by `topics[].order`; screens in an aligned grid of rows and columns.
- Cross-topic arrows are thick, in the source topic's colour, labelled; in-topic arrows are thin grey.

## Flow diagrams (tree layout, opt-in `flows`)
- 2+ outgoing edges → tree: one trunk, orthogonal bus, children on one aligned row (top→bottom flows) or column (left→right), centred on the parent, labels on the drops.
- One-to-one steps = straight arrow. Merges, back-links and skips = orthogonal polylines through a side channel, dashed if optional. No long diagonals.

## Resolution rule
- In `architecture.png`, `overview.png`, `flows/*.png`, `one-pager.png`/`.pdf` every screenshot is drawn at ≥ its native pixels (`native_zoom`); zoom reads all text. The canvas grows instead (tens to hundreds of megapixels, 1–30 MB PNG). `build` prints the zoom factors and warns below 1.0×.
- Capture sharp (web `--scale 2`); a 780×1688 phone shot gives device areas of ≥ 780×1688 px.
- Graphviz is not used when Pillow is present (it draws small).
- Only the HTML viewer embeds reduced copies (screens ≤ 480 px, architecture preview ≤ 2400 px) and links to the full-resolution PNG.
