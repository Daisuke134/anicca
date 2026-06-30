#!/usr/bin/env python3
"""Targeted v2: replace the 2 rotated images by INDEX (composer-img order).

Composer img order on this draft (cover excluded):
  0: IMG_4920 (window at night) — correct
  1: IMG_4926 (QR tablet)       ← rotated, replace
  2: IMG_4925 (LMGH WiFi code)  — correct
  3: IMG_4930 (counter + menus) — correct
  4: IMG_4931 (inside cafe)     — correct
  5: IMG_4927 (coffee cup)      — correct
  6: IMG_4928 (hiring flyer)    ← rotated, replace

For each rotated image:
  1. Find image by index, scroll into view, click its CENTER to focus the
     atomic block.
  2. Press Backspace to delete the block.
  3. Click the anchor paragraph (last text pixel), press End.
  4. Copy corrected JPG to clipboard, Cmd+V.
  5. Wait for upload spinner to clear, ArrowDown.
"""
import pathlib, subprocess, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
URL = (HERE / "latest-en-draft-url.txt").read_text().strip()
COPY = pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"
OUT = HERE / "en-replace-fix-v2"; OUT.mkdir(exist_ok=True)

JOBS = [
    {
        "key": "IMG_4926",
        "index": 1,
        "src": HERE / "assets/IMG_4926.jpg",
        "anchor": "Hold your iPhone up to the QR tablet on the counter and scan your order receipt.",
    },
    {
        "key": "IMG_4928",
        "index": 6,
        "src": HERE / "assets/IMG_4928.jpg",
        "anchor": "It was the",
    },
]

def log(*a): print("[replace-v2]", *a, flush=True)

def copy_image(p):
    subprocess.run(["python3", str(COPY), "image", str(p), "--quality", "90"],
                   check=True, capture_output=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)
    page.screenshot(path=str(OUT / "00-before.png"), full_page=True)

    # Count composer images
    count = page.evaluate(
        '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
    )
    log(f"composer img count = {count}")

    # IMPORTANT: process jobs in DESCENDING index order so deleting earlier
    # ones doesn't shift later indices.
    for job in sorted(JOBS, key=lambda j: -j["index"]):
        key = job["key"]; idx = job["index"]; src = job["src"]; anchor = job["anchor"]
        log(f"--- {key} (index {idx}) ---")

        coords = page.evaluate(
            """(idx) => {
                const imgs = document.querySelectorAll('div[data-testid="composer"] img');
                if (idx >= imgs.length) return null;
                const img = imgs[idx];
                img.scrollIntoView({block: 'center'});
                const r = img.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height};
            }""",
            idx,
        )
        if not coords:
            log(f"  {key}: index {idx} out of range, SKIP")
            continue
        log(f"  {key}: center=({coords['x']:.0f},{coords['y']:.0f}) size={coords['w']:.0f}x{coords['h']:.0f}")
        time.sleep(0.5)

        # Click image center to select the atomic block
        page.mouse.click(coords["x"], coords["y"])
        time.sleep(0.5)
        page.screenshot(path=str(OUT / f"a-{key}-selected.png"))
        # Delete the atomic block. Draft.js needs Backspace on a selected
        # atomic to remove it. Sometimes 2 presses needed.
        page.keyboard.press("Backspace"); time.sleep(0.4)
        before_after_delete = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        if before_after_delete >= count:
            page.keyboard.press("Backspace"); time.sleep(0.4)
        new_cnt = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        log(f"  {key}: count after delete = {new_cnt} (was {count})")
        count = new_cnt
        page.screenshot(path=str(OUT / f"b-{key}-after-delete.png"))

        # Find the anchor paragraph's last-pixel
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
                return {x: Math.min(last.right - 2, window.innerWidth - 4),
                        y: last.top + last.height / 2};
            }""",
            anchor,
        )
        if not target:
            log(f"  {key}: anchor text not found, SKIP paste")
            continue
        log(f"  {key}: anchor click @ ({target['x']:.0f},{target['y']:.0f})")
        page.keyboard.press("Escape"); time.sleep(0.2)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.keyboard.press("End"); time.sleep(0.2)

        copy_image(src)
        time.sleep(0.5)
        page.keyboard.press("Meta+v")
        try:
            page.wait_for_selector(
                'text=/uploading|アップロード中|正在上传媒体|업로드/i',
                state="hidden", timeout=40000,
            )
        except Exception:
            time.sleep(3)
        time.sleep(2.0)
        page.keyboard.press("ArrowDown"); time.sleep(0.4)
        new_count = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        log(f"  {key}: count after paste = {new_count}")
        count = new_count
        page.screenshot(path=str(OUT / f"c-{key}-after-paste.png"), full_page=True)

    page.screenshot(path=str(OUT / "99-after.png"), full_page=True)
    log(f"DONE. URL: {URL}")
