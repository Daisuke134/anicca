#!/usr/bin/env python3
"""Safely delete duplicate X Articles drafts that match the EXACT current
article title. Keeps the newest match. NEVER touches drafts with any other
title — guards against deleting unrelated drafts.
"""
import json, pathlib, re, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ARTICLE = json.loads((HERE / "article.json").read_text())
EXACT_TITLE = ARTICLE["title"]
print(f"[dedup] target EXACT title: {EXACT_TITLE!r}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
    time.sleep(4)

    for loop in range(10):
        try:
            page.keyboard.press("Escape"); time.sleep(0.2)
        except Exception:
            pass
        matches = page.get_by_text(EXACT_TITLE, exact=True)
        try:
            n = matches.count()
        except Exception:
            n = 0
        print(f"[dedup] iter {loop}: {n} drafts with exact title")
        if n <= 1:
            print("[dedup] done — 1 or 0 remain")
            break
        try:
            old = matches.nth(n - 1)
            old.scroll_into_view_if_needed()
            row_more = old.locator(
                'xpath=ancestor::*[self::article or @role="link" or @role="article"][1]'
                '//button[contains(translate(@aria-label,"MORE","more"),"more")]'
            )
            if row_more.count() == 0:
                row_more = old.locator('xpath=ancestor::*[1]//button')
            row_more.first.click(timeout=3000)
            time.sleep(0.4)
            page.get_by_role("menuitem").filter(
                has_text=re.compile(r"Delete|削除")
            ).first.click(timeout=3000)
            time.sleep(0.4)
            try:
                page.get_by_role("button").filter(
                    has_text=re.compile(r"^Delete$|^削除$|^削除する$|^Yes")
                ).last.click(timeout=2000)
            except Exception:
                pass
            time.sleep(2)
        except Exception as e:
            print(f"[dedup] error -> stop: {e}")
            break
    print(f"[dedup] done")
