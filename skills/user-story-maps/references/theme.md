# Theme: look like the app

Optional `theme:` block in `stories.yaml`. Applies to every output (HTML, one-pager, architecture, flows, Mermaid). Only `primary` is required; status, severity and topic colours derive from it. No `theme:` → legacy green.

```yaml
theme:
  primary: "#3366CC"         # brand/accent
  text: "#202122"            # optional: background, text, muted, surface, border, secondary (#RRGGBB)
  # background: "#000000"    # dark app (or `mode: dark`), see Dark mode
  heading_font: "Gelasio"    # `font:` = body (default system sans)
  google_font: true          # fetch an open-licensed family (cached outside the repo)
  # font_file: tools/MyFont.ttf   # redistributable, relative; font_file_bold optional
  # embed_fonts: true        # HTML only: embed a WOFF2 subset (needs fontTools+brotli); default: system fonts
  # status:   { built: "#00AF89", partly: "#FFCC33", unverified: "#6699FF", missing: "#A2A9B1" }
  # severity: { high: "#DD3333", medium: "#FFCC33", low: "#A2A9B1" }
  # device:   { style: titanium, model: "", badge: label, frames: frames.json }
```

## Steps
1. `storymap.py theme-from <app-source>` (read-only scan) prints a draft block. By hand: iOS `Assets.xcassets/*.colorset`, Theme/Color/Font Swift; Android `res/values/colors.xml`, `themes.xml`, `res/font/`; web `tailwind.config.*`, CSS `:root { --… }`, token JSON.
2. `primary` = brand/accent; `text`/`border` of the app's own mode. Map success/warning/error → `status:` (built = success, partly = warning, missing = neutral gray) and `severity:`.
3. Fonts: real family name. Bundle only open-licensed (OFL/Apache, or your own file). Proprietary/system: name only (used if installed) or an open look-alike with `google_font: true` (Gelasio for Georgia).
4. Build; view `architecture.png`, `one-pager.png`; tune until readable and status colours stay distinguishable.

## Fonts
- PNG outputs use the resolved font (installed, `font_file`, or Google font). The HTML names the font and falls back to a system stack; it embeds nothing unless `embed_fonts: true` / `--embed-fonts`.
- `embed_fonts` writes at most body regular + bold (+ heading) as WOFF2 subsets of the glyphs the page uses. Without fontTools+brotli it prints a note and keeps system fonts.

## Dark mode
`background:` darker than 30% luminance (e.g. `"#000000"`) or `mode: dark` (`mode: light` forces light). Everything follows in all outputs: lanes mix toward the background, light text/border, lifted status/topic colours, black text on bright chips, titanium frames (`device.style: auto`). Set `text`/`muted`/`surface`/`border`/`status:` explicitly to override. Example: `examples/wikipedia-ios`.
