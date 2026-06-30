#!/usr/bin/env python3
"""READ-ONLY: open the existing R4 draft (URL from latest-en-draft-url.txt)
and wheel-scroll the editor end-to-end, capturing screenshots into
en-verify-r4-existing/. NO publish, NO edits — just inspection of what's
already in the draft."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "en-verify-r4-existing"
OUT.mkdir(exist_ok=True)
URL = (HERE / "latest-en-draft-url.txt").read_text().strip()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)
    page.mouse.move(1300, 500)
    time.sleep(0.5)
    for i in range(15):
        page.screenshot(path=str(OUT / f"r4-{i:02d}.png"))
        page.mouse.wheel(0, 700)
        time.sleep(0.8)
    print(f"done: 15 shots in {OUT}")
