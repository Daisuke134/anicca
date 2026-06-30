#!/usr/bin/env python3
"""Find the inner scroll container of the published-article view (right pane
of /compose/articles/edit/<id> in published mode) and scroll-screenshot it."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "verify-published"; OUT.mkdir(exist_ok=True)
URL = (HERE / "published-url.txt").read_text().strip()
def log(*a): print("[pub-scroll]", *a, flush=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(25000)
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(5)

    # Find ANY scrollable container on the page with the article text.
    # Anchor on the article H1 (cover-image area) and walk up.
    info = page.evaluate(
        """() => {
            // The published view shows the article in a column; find an
            // element with scrollable overflow that contains 'Corgi Cafe'.
            const all = Array.from(document.querySelectorAll('div'));
            const candidates = [];
            for (const el of all) {
                const s = getComputedStyle(el);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
                    el.scrollHeight > el.clientHeight + 50 &&
                    (el.textContent || '').includes('Corgi')) {
                    candidates.push({
                        tag: el.tagName,
                        cls: (el.className || '').slice(0, 80),
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight,
                    });
                }
            }
            return candidates;
        }"""
    )
    log(f"candidates: {info}")
    if not info:
        log("FALLBACK: just take a tall full_page screenshot of the entire page once")
        page.screenshot(path=str(OUT / "fallback-full.png"), full_page=True)
        raise SystemExit(0)

    # Pick the candidate with the LARGEST scrollHeight (= main article column)
    target_cls = max(info, key=lambda c: c["scrollHeight"])["cls"]
    log(f"target container class: {target_cls}")
    sh = max(info, key=lambda c: c["scrollHeight"])["scrollHeight"]
    ch = max(info, key=lambda c: c["scrollHeight"])["clientHeight"]
    step = int(ch * 0.85); i = 0; y = 0
    while y < sh:
        page.evaluate(
            f"""(targetCls) => {{
                const all = Array.from(document.querySelectorAll('div'));
                for (const el of all) {{
                    if ((el.className || '') === targetCls) {{
                        el.scrollTo({{top: {y}, behavior: 'instant'}}); return;
                    }}
                }}
            }}""",
            target_cls,
        )
        time.sleep(0.8)
        page.screenshot(path=str(OUT / f"pub-{i:02d}.png"))
        log(f"pub-{i:02d}.png  y={y}/{sh}")
        i += 1; y += step
    log(f"done: {i} shots")
