#!/usr/bin/env python3
"""Scroll the published-article column with REAL mouse wheel events
(programmatic scrollTo gets reset by X). Screenshot at each step."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "verify-published"; OUT.mkdir(exist_ok=True)
URL = (HERE / "published-url.txt").read_text().strip()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)
    # Move mouse to the article column (right pane) so wheel scrolls there.
    page.mouse.move(1300, 500)
    time.sleep(0.5)
    # Wheel down ~700px at a time, screenshot each step.
    for i in range(20):
        page.screenshot(path=str(OUT / f"wheel-{i:02d}.png"))
        page.mouse.wheel(0, 700)
        time.sleep(0.8)
    print(f"done: 20 shots in {OUT}")
