# Your own device frame (optional, never committed)

Built-in frames are drawn with Pillow; no artwork is bundled (`THIRD-PARTY-NOTICES.md`). To use a real frame you may use locally, describe it in `frames.json`.

## Lookup order
1. `theme.device.frames` (relative path inside the map folder)
2. `$STORYMAP_FRAMES`
3. `frames.json` in the map folder
4. `~/.cache/storymap/frames/frames.json`

## Format
```json
{"frames": {"my-phone": {"image": "my-phone.png",
                         "screen": {"x": 62, "y": 54, "width": 1206, "height": 2622, "radius": 120}}},
 "defaults": {"iphone-island": "my-phone"}}
```
- `image`: transparent PNG; the screen area must be transparent.
- `screen`: screen rectangle in image pixels + corner radius.
- Screenshot is contained in that rectangle (letterboxed black if ratio differs), clipped to rounded corners, frame drawn on top.
- Use the frame name in `device:` (screen / app / `theme.device.model`) or map a built-in model to it in `defaults`.
- Built-in procedural frame stays the fallback.

## Rule
Do not commit frames you did not draw (Apple and most vendor bezels forbid redistribution). Add `frames.json` and the image to `.gitignore`.
