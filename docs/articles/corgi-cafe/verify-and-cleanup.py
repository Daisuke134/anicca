#!/usr/bin/env python3
"""
Self-verify the freshly created X Articles draft by:
  1. Opening the draft URL in the daily-driver
  2. Scrolling top->bottom, capturing screenshots every viewport
Then delete every OTHER draft that matches the title prefix (so only the new
draft remains).
"""
import json, pathlib, sys, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
DRAFT_URL = (HERE / "draft-url.txt").read_text().strip()
ARTICLE_JSON = json.loads((HERE / "article.json").read_text())
TITLE = ARTICLE_JSON["title"]
TITLE_PREFIX = TITLE[:18]
VERIFY_DIR = HERE / "verify"; VERIFY_DIR.mkdir(exist_ok=True)

def log(*a): print("[verify]", *a, flush=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.set_default_timeout(20000)
        log(f"navigating to {DRAFT_URL}")
        page.goto(DRAFT_URL, wait_until="domcontentloaded")
        time.sleep(5)

        # Take a FULL PAGE screenshot first
        page.screenshot(path=str(VERIFY_DIR / "full-page.png"), full_page=True)
        log("captured full-page.png")

        # Then scroll-step screenshots (better for very tall pages)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        h = page.evaluate("document.documentElement.scrollHeight")
        vh = page.evaluate("window.innerHeight")
        log(f"page height={h}  viewport={vh}")
        step = int(vh * 0.85)
        i = 0
        y = 0
        while y < h:
            page.evaluate(f"window.scrollTo(0, {y})")
            time.sleep(0.6)
            page.screenshot(path=str(VERIFY_DIR / f"section-{i:02d}.png"))
            log(f"section-{i:02d}.png  (y={y})")
            i += 1
            y += step
        log(f"verify done: {i} section screenshots in {VERIFY_DIR}")

        # ---- cleanup duplicate drafts ----
        log("navigating to Articles list to dedupe drafts")
        list_page = ctx.new_page()
        list_page.set_default_timeout(15000)
        list_page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
        time.sleep(4)
        # The freshest draft should appear FIRST (top of list). Skip index 0;
        # delete any other draft whose preview starts with TITLE_PREFIX.
        snippet = TITLE_PREFIX[:15]
        for _ in range(8):
            matches = list_page.get_by_text(snippet, exact=False)
            try:
                n = matches.count()
            except Exception:
                n = 0
            log(f"dedupe: {n} drafts match {snippet!r}")
            if n <= 1:
                break
            # delete the LAST match (= older)
            try:
                old = matches.nth(n - 1)
                old.scroll_into_view_if_needed()
                more = old.locator(
                    'xpath=ancestor::*[self::article or @role="link" or @role="article"][1]'
                    '//button[contains(translate(@aria-label,"MORE","more"),"more")]'
                )
                if more.count() == 0:
                    more = old.locator('xpath=ancestor::*[1]//button')
                more.first.click(timeout=3000)
                time.sleep(0.4)
                list_page.get_by_role("menuitem").filter(
                    has_text=__import__("re").compile(r"Delete|削除")
                ).first.click(timeout=3000)
                time.sleep(0.4)
                # confirm
                try:
                    list_page.get_by_role("button").filter(
                        has_text=__import__("re").compile(r"^Delete$|^削除$|^削除する$|^Yes")
                    ).last.click(timeout=2000)
                except Exception:
                    pass
                time.sleep(2)
            except Exception as e:
                log(f"dedupe error: {e}")
                break
        log("dedupe done")

if __name__ == "__main__":
    main()
