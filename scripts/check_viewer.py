#!/usr/bin/env python3
"""Check that a generated story-map.html works on a phone.

    python3 scripts/check_viewer.py docs/story-map/generated/story-map.html [more.html or https://...] [--shots DIR]

Opens each page in headless Chromium at 390x844 (iPhone) and 360x800 (small Android), on every tab and in the screen
detail view, and fails (exit 1) on: a missing viewport meta, pinch-zoom blocked, horizontal page scroll, or a tappable
control smaller than 44x44 px. Needs Playwright: `pip install playwright && playwright install chromium`.
"""
import argparse
import json
import os
import sys

SIZES = ((390, 844, 3), (360, 800, 3))
MIN_TAP = 44

MEASURE = """() => {
  const de = document.documentElement, vw = de.clientWidth;
  const vis = e => { const r = e.getBoundingClientRect(); if (!r.width || !r.height) return null;
    const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') return null; return r; };
  const clipped = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if ((o === 'auto' || o === 'scroll') && p.scrollWidth > p.clientWidth) {
      const pr = p.getBoundingClientRect(), r = e.getBoundingClientRect(); return r.right < pr.left || r.left > pr.right; } } return false; };
  const scroller = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll') return true; } return false; };
  const small = [];
  const sel = 'button,select,input,a[href],[onclick],[tabindex]:not([tabindex="-1"]),summary';
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest('.hidden')) continue;
    if (e.closest('#lb') && getComputedStyle(document.getElementById('lb')).display === 'none') continue;
    const r = vis(e); if (!r || clipped(e)) continue;
    if (r.width < %d - 0.5 || r.height < %d - 0.5) small.push({tag: e.tagName.toLowerCase(), cls: String(e.className).slice(0, 30),
      text: (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 24), w: Math.round(r.width), h: Math.round(r.height)});
  }
  const wide = [];
  for (const e of document.body.querySelectorAll('*')) { if (e.closest('.row,.thumbs,#lb')) continue; const r = vis(e);
    if (r && r.right > vw + 1 && !scroller(e)) { wide.push(e.tagName.toLowerCase() + '.' + String(e.className).slice(0, 20)); if (wide.length > 5) break; } }
  const tiny = [...document.querySelectorAll('#main *,header *')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && vis(e) && parseFloat(getComputedStyle(e).fontSize) < 11).length;
  return {scrollWidth: de.scrollWidth, clientWidth: vw, bodyScrollWidth: document.body.scrollWidth, small, wide, tinyText: tiny};
}""" % (MIN_TAP, MIN_TAP)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="+", help="story-map.html paths or URLs")
    ap.add_argument("--shots", help="folder for PNG screenshots")
    ap.add_argument("--tag", default="", help="prefix for screenshot names")
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2
    results, failed = [], False
    with sync_playwright() as pw:
        exe = os.environ.get("CHROMIUM_PATH")   # optional: use an already installed Chromium
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        for page_ref in a.pages:
            url = page_ref if "://" in page_ref else "file://" + os.path.abspath(page_ref)
            label = (os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(page_ref)))) if "://" not in page_ref
                     else page_ref.rstrip("/").split("/")[-3]) or "page"
            for w, h, dsf in SIZES:
                ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf, is_mobile=True, has_touch=True)
                page = ctx.new_page()
                requests = []
                page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("data:", "file:", url.split("#")[0])) else None)
                page.goto(url, wait_until="load")
                meta = page.evaluate("() => (document.querySelector('meta[name=viewport]')||{}).content || ''")
                props = dict((x.split("=", 1) + [""])[:2] for x in meta.replace(" ", "").lower().split(",") if x)
                try:
                    max_scale = float(props.get("maximum-scale", "10"))
                except ValueError:
                    max_scale = 10.0
                meta_ok = props.get("width") == "device-width" and props.get("user-scalable", "yes") not in ("no", "0") and max_scale >= 2
                tabs = page.evaluate("() => TABS")
                views = [(t, t) for t in tabs] + [("story-open", "stories"), ("detail", None), ("diagram", None)]
                for name, tab in views:
                    if name == "story-open":
                        page.evaluate("() => {S.tab='stories'; OPEN.add(D.stories[0].id); render(); window.scrollTo(0,0)}")
                    elif tab:
                        page.evaluate("t => {S.tab=t; render(); window.scrollTo(0,0)}", tab)
                    elif name == "detail":
                        page.evaluate("() => {S.tab='flows'; render(); window.scrollTo(0,0); const k=keys(); if(k.length) lb(k[0])}")
                    elif not page.evaluate("() => !!IMG.__arch"):
                        continue
                    else:
                        page.evaluate("() => {S.tab='arch'; render(); window.scrollTo(0,0); lb('__arch')}")
                    page.wait_for_timeout(250)
                    r = page.evaluate(MEASURE)
                    r.update(page=label, size="%dx%d" % (w, h), view=name, viewport_meta=meta, meta_ok=meta_ok)
                    r["overflow"] = r["scrollWidth"] > r["clientWidth"] or r["bodyScrollWidth"] > r["clientWidth"]
                    if name == "detail":
                        r["detail_visible"] = page.evaluate("() => { const d=document.getElementById('lbdetails'); if(!d||getComputedStyle(d).display==='none') return false; const q=d.getBoundingClientRect(); return q.left>=-1 && q.right<=innerWidth+1 && q.width>=innerWidth*0.8 }")
                    r["ok"] = meta_ok and not r["overflow"] and not r["small"] and not r["wide"] and r.get("detail_visible", True)
                    failed |= not r["ok"]
                    results.append(r)
                    if a.shots:
                        os.makedirs(a.shots, exist_ok=True)
                        stem = "%s%s-%dx%d-%s" % (a.tag + "-" if a.tag else "", label, w, h, name)
                        page.screenshot(path=os.path.join(a.shots, stem + ".png"))
                    if name in ("detail", "diagram"):
                        page.evaluate("closeLb()")
                if requests:
                    failed = True
                    print("EXTERNAL REQUESTS:", requests[:5], file=sys.stderr)
                ctx.close()
        browser.close()
    if a.json:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            print("%-14s %-8s %-9s scrollWidth %d / clientWidth %d  small taps %d  wide %d  meta %s  %s" % (
                r["page"], r["size"], r["view"], r["scrollWidth"], r["clientWidth"], len(r["small"]), len(r["wide"]),
                "ok" if r["meta_ok"] else "BAD", "OK" if r["ok"] else "FAIL"))
            for s in r["small"][:4]:
                print("    small tap target: %(tag)s.%(cls)s '%(text)s' %(w)dx%(h)d" % s)
            if r["wide"]:
                print("    overflowing:", ", ".join(r["wide"]))
    print("FAILED" if failed else "all checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
