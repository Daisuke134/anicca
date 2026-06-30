#!/usr/bin/env python3
"""TARGETED FIX (no full publish):
Open the existing EN draft, find the 2 rotated images by src filename
(IMG_4926 = QR tablet, IMG_4928 = hiring flyer), for each:
  1) hover the image → click the ✕ Remove button overlayed on it
  2) click the paragraph that should sit IMMEDIATELY ABOVE the image
     (IMG_4926: "Hold your iPhone up to the QR tablet on the counter and scan your order receipt.")
     (IMG_4928: "The most San-Francisco thing in this cafe was not the coffee. It was the hiring flyer sitting on every table.")
  3) press End, copy corrected source JPG to clipboard, Cmd+V
  4) wait for upload spinner to clear
  5) screenshot before & after
Does NOT touch any other block. Does NOT re-create the draft."""
import pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
URL = (HERE / "latest-en-draft-url.txt").read_text().strip()
COPY = pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"
OUT = HERE / "en-replace-fix"; OUT.mkdir(exist_ok=True)

# Each entry: source JPG path (now portrait-correct), an anchor phrase that
# identifies the paragraph the image should follow, and a key for logging.
JOBS = [
    {
        "key": "IMG_4926",
        "src": HERE / "assets/IMG_4926.jpg",
        "anchor": "Hold your iPhone up to the QR tablet on the counter and scan your order receipt.",
    },
    {
        "key": "IMG_4928",
        "src": HERE / "assets/IMG_4928.jpg",
        "anchor": "The most San-Francisco thing in this cafe was not the coffee. It was the",
    },
]

def log(*a): print("[replace]", *a, flush=True)

def copy_to_clipboard(path):
    subprocess.run(
        ["python3", str(COPY), "image", str(path), "--quality", "90"],
        check=True, capture_output=True,
    )

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)
    page.screenshot(path=str(OUT / "00-before.png"))
    log(f"opened draft: {URL}")

    for i, job in enumerate(JOBS):
        key = job["key"]; src = job["src"]; anchor = job["anchor"]
        log(f"--- {key} ---")
        # ---- 1. Find the image by src filename, scroll into view, screenshot
        coords = page.evaluate(
            """(filename) => {
                const imgs = Array.from(document.querySelectorAll('div[data-testid="composer"] img'));
                const match = imgs.find(im => (im.src || '').includes(filename));
                if (!match) return null;
                match.scrollIntoView({block: 'center'});
                const r = match.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height,
                        rightX: r.right - 18, topY: r.top + 18};
            }""",
            key,
        )
        if not coords:
            log(f"  {key}: image not found in draft, SKIP")
            continue
        log(f"  {key}: img center=({coords['x']:.0f},{coords['y']:.0f}), size={coords['w']:.0f}x{coords['h']:.0f}")
        time.sleep(0.5)
        page.screenshot(path=str(OUT / f"{i+1:02d}a-{key}-found.png"))

        # ---- 2. Hover to surface the ✕ button (top-right ~18px inset)
        page.mouse.move(coords["x"], coords["y"])
        time.sleep(0.3)
        # Click the ✕ Remove
        page.mouse.click(coords["rightX"], coords["topY"])
        time.sleep(1.0)
        page.screenshot(path=str(OUT / f"{i+1:02d}b-{key}-after-x.png"))
        # X may show a confirmation dialog ("Delete this media?"). Click "Delete" if present.
        try:
            page.get_by_role("button", name=lambda n: n and n.lower() in ("delete", "remove", "削除")).first.click(timeout=1500)
            time.sleep(0.8)
        except Exception:
            pass
        page.screenshot(path=str(OUT / f"{i+1:02d}c-{key}-after-confirm.png"))

        # ---- 3. Click the anchor paragraph (last pixel of text node)
        target = page.evaluate(
            """(text) => {
                const editor = document.querySelector('div[data-testid="composer"]');
                if (!editor) return null;
                const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
                let n, found = null;
                while ((n = walker.nextNode())) {
                    if ((n.textContent || '').includes(text)) found = n;
                }
                if (!found) return null;
                (found.parentElement || found).scrollIntoView({block: 'center'});
                const r = document.createRange();
                r.selectNodeContents(found);
                const rects = r.getClientRects();
                if (!rects.length) return null;
                const last = rects[rects.length - 1];
                return {x: Math.min(last.right - 2, window.innerWidth - 4), y: last.top + last.height / 2};
            }""",
            anchor,
        )
        if not target:
            log(f"  {key}: anchor paragraph not found, SKIP rest")
            continue
        log(f"  {key}: anchor click @ ({target['x']:.0f},{target['y']:.0f})")
        page.keyboard.press("Escape"); time.sleep(0.2)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.keyboard.press("End"); time.sleep(0.2)

        # ---- 4. Copy corrected JPG to clipboard, paste
        copy_to_clipboard(src)
        time.sleep(0.5)
        page.keyboard.press("Meta+v")
        try:
            page.wait_for_selector(
                'text=/uploading|アップロード中|正在上传媒体|업로드/i',
                state="hidden", timeout=30000,
            )
        except Exception:
            time.sleep(3)
        time.sleep(1.5)
        page.keyboard.press("ArrowDown")
        time.sleep(0.5)
        page.screenshot(path=str(OUT / f"{i+1:02d}d-{key}-after-paste.png"))
        log(f"  {key}: replaced")

    page.screenshot(path=str(OUT / "99-after.png"))
    log(f"DONE. Draft URL: {URL}")
