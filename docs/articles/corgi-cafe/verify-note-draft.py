#!/usr/bin/env python3
"""Open the Corgi note draft in the daily-driver CloakBrowser and wheel-scroll
the body, capturing screenshots. READ-ONLY: no clicks, no edits, no publish."""
import pathlib, time
from playwright.sync_api import sync_playwright

URL = "https://editor.note.com/notes/nb1148aabde59/edit/"
OUT = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/note-verify-r2")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(8)
    page.screenshot(path=str(OUT / "note-00.png"), full_page=False)
    page.mouse.move(700, 500)
    time.sleep(0.5)
    for i in range(1, 22):
        page.mouse.wheel(0, 600)
        time.sleep(0.9)
        page.screenshot(path=str(OUT / f"note-{i:02d}.png"), full_page=False)
    print(f"done: {len(list(OUT.glob('note-*.png')))} shots in {OUT}")
