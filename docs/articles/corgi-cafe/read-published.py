#!/usr/bin/env python3
"""Open Dais's @aniccaxxx Articles → Published tab on the live daily-driver,
find the Corgi article, scroll-screenshot it top to bottom, and persist the
shots under verify-published/."""
import pathlib, re, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "verify-published"; OUT.mkdir(exist_ok=True)
def log(*a): print("[read-published]", *a, flush=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(25000)

    # Try the Articles list -> Published tab first
    page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
    time.sleep(5)
    try:
        page.get_by_text("Published", exact=True).first.click()
        time.sleep(3)
    except Exception as e:
        log(f"Published tab click failed: {e}")
    page.screenshot(path=str(OUT / "00-published-list.png"), full_page=True)

    # Find the Corgi article entry and click it
    candidates = [
        "24時間営業のスタートアップカフェ",
        "Corgi Cafe",
        "Corgi",
    ]
    opened = False
    for kw in candidates:
        try:
            loc = page.get_by_text(kw, exact=False).first
            if loc.is_visible(timeout=2000):
                loc.click()
                time.sleep(5)
                opened = True
                log(f"opened via keyword: {kw!r}")
                break
        except Exception:
            continue
    if not opened:
        log("could not click Corgi entry in Published list; will try profile articles")
        # Fall back: visit profile and look for the article card
        page.goto("https://x.com/aniccaxxx", wait_until="domcontentloaded")
        time.sleep(4)
        for kw in candidates:
            try:
                loc = page.get_by_text(kw, exact=False).first
                if loc.is_visible(timeout=2000):
                    loc.click()
                    time.sleep(5)
                    opened = True
                    log(f"opened via profile + {kw!r}")
                    break
            except Exception:
                continue

    log(f"URL now: {page.url}")
    (HERE / "published-url.txt").write_text(page.url + "\n")

    # Take full-page screenshot first
    page.screenshot(path=str(OUT / "full-page.png"), full_page=True)

    # Then scroll-step through the article body. Published articles render in
    # the normal page scroll (not an inner container), so window.scrollTo works.
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)
    h = page.evaluate("document.documentElement.scrollHeight")
    vh = page.evaluate("window.innerHeight")
    log(f"page height={h}  viewport={vh}")
    step = int(vh * 0.85)
    i = 0; y = 0
    while y < h:
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.7)
        page.screenshot(path=str(OUT / f"scroll-{i:02d}.png"))
        log(f"scroll-{i:02d}.png  y={y}/{h}")
        i += 1; y += step
    log(f"done: {i} screenshots in {OUT}")
