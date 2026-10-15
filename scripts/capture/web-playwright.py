#!/usr/bin/env python3
"""Capture screenshots of a web app with Playwright (free, open source).

    pip install playwright && playwright install chromium

    web-playwright.py --base-url http://localhost:3000 --shots capture.json [options]

capture.json is a list; one entry per screen (the id matches `id:` in stories.yaml):
    [ {"id": "welcome",    "path": "/"},
      {"id": "plant-list", "path": "/plants", "wait_for": "[data-testid=plant-card]"},
      {"id": "add-plant",  "path": "/plants/new", "click": "text=Add plant"} ]
Optional keys per entry: url (absolute URL instead of base-url + path), wait_for (CSS selector), click (selector
clicked after load), full_page (bool), delay_ms, wait_until (load | domcontentloaded | networkidle).

Options:
  --out DIR            output folder (default docs/story-map/screens)
  --viewport 390x844   default 390x844 (phone-like); use 1280x800 for desktop
  --scale 2            device pixel ratio (default 2)
  --dark               prefers-color-scheme: dark
  --storage-state F    Playwright storage-state JSON for a signed-in DEMO session (keep it OUT of git!)
  --wait-until E       load | domcontentloaded | networkidle (default)
  --executable-path P  use an installed Chrome/Chromium instead of Playwright's download

Signing in: create the storage-state file once with a demo account
    playwright codegen --save-storage=.demo-session.json http://localhost:3000
then add `.demo-session.json` to .gitignore. NEVER pass passwords on the command line or commit them.
No Playwright? A one-off alternative is:  google-chrome --headless --screenshot=welcome.png --window-size=390,844 URL
"""
import argparse, json, os, sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--shots", required=True, help="JSON file listing the screens to capture")
    ap.add_argument("--out", default="docs/story-map/screens")
    ap.add_argument("--viewport", default="390x844")
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--storage-state")
    ap.add_argument("--executable-path")
    ap.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle"],
                    help="page load condition (default networkidle; use domcontentloaded for sites with long-polling)")
    ap.add_argument("--timeout-ms", type=int, default=45000)
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright is not installed: pip install playwright && playwright install chromium")
    w, h = (int(x) for x in a.viewport.lower().split("x"))
    with open(a.shots, encoding="utf-8") as f:
        shots = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.executable_path) if a.executable_path else p.chromium.launch()
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=a.scale,
                                  color_scheme="dark" if a.dark else "light",
                                  storage_state=a.storage_state if a.storage_state else None)
        page = ctx.new_page()
        page.set_default_timeout(a.timeout_ms)
        for s in shots:
            page.goto(s["url"] if s.get("url") else a.base_url.rstrip("/") + s.get("path", "/"),
                      wait_until=s.get("wait_until", a.wait_until))
            if s.get("wait_for"):
                page.wait_for_selector(s["wait_for"])
            if s.get("click"):
                page.click(s["click"])
            page.wait_for_timeout(int(s.get("delay_ms", 300)))
            out = os.path.join(a.out, s["id"] + ".png")
            page.screenshot(path=out, full_page=bool(s.get("full_page")))
            print("saved", out)
        browser.close()


if __name__ == "__main__":
    main()
