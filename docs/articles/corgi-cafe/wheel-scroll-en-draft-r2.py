#!/usr/bin/env python3
"""Wheel-scroll the EN draft editor end-to-end and capture screenshots.

Reads the draft URL from `en-draft-url.txt` (or uses the hardcoded one
below). Connects to CloakBrowser daily-driver via CDP and physically
mouse-wheel scrolls the editor's right pane so EVERY block of the article
is captured. Programmatic scrollTo gets reset on this view; wheel events
do not.
"""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "en-verify-r2"
OUT.mkdir(exist_ok=True)
url_file = HERE / "en-draft-url.txt"
URL = url_file.read_text().strip() if url_file.exists() else \
    "https://x.com/compose/articles/edit/2070888979722121216"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)
    # Position mouse over the editor column.
    page.mouse.move(1300, 500)
    time.sleep(0.5)
    # Wheel down step by step; screenshot at each stop.
    for i in range(20):
        page.screenshot(path=str(OUT / f"en-{i:02d}.png"))
        page.mouse.wheel(0, 700)
        time.sleep(0.8)
    print(f"done: 20 shots in {OUT}")
