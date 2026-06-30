#!/usr/bin/env python3
"""Open Articles list in CloakBrowser daily-driver, find the newest EN draft
(title contains 'Inside Corgi Cafe'), report its URL. Read-only inspection.
DOES NOT publish, modify, or re-create."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
    time.sleep(4)
    # Click the EN draft entry
    page.get_by_text("Inside Corgi Cafe", exact=False).first.click()
    time.sleep(5)
    print("URL:", page.url)
    (HERE / "latest-en-draft-url.txt").write_text(page.url + "\n")
    page.screenshot(path=str(HERE / "latest-en-first-view.png"), full_page=True)
    print("saved first-view screenshot")
