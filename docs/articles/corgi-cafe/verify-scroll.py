#!/usr/bin/env python3
"""Scroll the X Articles editor's INNER scroll container and screenshot each
viewport. The editor pane has its own scrollbar (page height == viewport
height), so window.scrollTo() doesn't move the article content."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
DRAFT_URL = (HERE / "draft-url.txt").read_text().strip()
OUT = HERE / "verify"; OUT.mkdir(exist_ok=True)

def log(*a): print("[verify-scroll]", *a, flush=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(DRAFT_URL, wait_until="domcontentloaded")
    time.sleep(5)

    # Find the article scroll container — the ancestor of the title textarea
    # that has overflow:auto/scroll AND scrollHeight > clientHeight.
    container_info = page.evaluate("""
    () => {
        const title = document.querySelector('textarea[name="Article Title"]');
        if (!title) return null;
        let el = title.parentElement;
        while (el && el !== document.body) {
            const s = getComputedStyle(el);
            if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 5) {
                const r = el.getBoundingClientRect();
                return {
                    found: true,
                    tag: el.tagName,
                    class: (el.className || '').slice(0, 80),
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                };
            }
            el = el.parentElement;
        }
        return null;
    }
    """)
    log(f"container_info={container_info}")
    if not container_info:
        log("FAILED to find scroll container")
        raise SystemExit(1)

    sh = container_info["scrollHeight"]
    ch = container_info["clientHeight"]
    step = int(ch * 0.85)
    i = 0; y = 0
    while y < sh:
        page.evaluate(f"""
        () => {{
            const title = document.querySelector('textarea[name="Article Title"]');
            let el = title.parentElement;
            while (el && el !== document.body) {{
                const s = getComputedStyle(el);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 5) {{
                    el.scrollTo({{top: {y}, behavior: 'instant'}});
                    return;
                }}
                el = el.parentElement;
            }}
        }}
        """)
        time.sleep(0.8)
        path = OUT / f"scroll-{i:02d}.png"
        page.screenshot(path=str(path))
        log(f"{path.name}  y={y}/{sh}")
        i += 1
        y += step
    log(f"done: {i} screenshots in {OUT}")
