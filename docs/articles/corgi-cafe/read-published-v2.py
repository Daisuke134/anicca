#!/usr/bin/env python3
"""Open the Published article via Articles list → Published tab → click row,
NOT via a text-search that can hit the drafts list. Capture URL + scroll
screenshots."""
import pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "verify-published"; OUT.mkdir(exist_ok=True)
def log(*a): print("[read-pub-v2]", *a, flush=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(25000)
    page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
    time.sleep(5)
    # Click Published tab specifically (role=tab)
    page.get_by_role("tab", name="Published").click()
    time.sleep(4)
    page.screenshot(path=str(OUT / "00b-published-tab.png"), full_page=True)
    # The newest Published row is at the top. Click into it.
    # Use the visible "Published · 50m" or "Published" label's first match
    # within the article list area, then walk up to a link/article ancestor.
    row = page.get_by_text("Corgi Cafe", exact=False).first
    row.scroll_into_view_if_needed()
    row.click()
    time.sleep(6)
    log(f"URL after click: {page.url}")
    (HERE / "published-url.txt").write_text(page.url + "\n")
    page.screenshot(path=str(OUT / "01-opened.png"), full_page=True)

    # If we landed on the editor (/compose/articles/edit/...) that's the edit
    # view of the published article — still readable. If we landed on the
    # public URL (/i/articles/...) all the better.
    # For the editor (Draft.js, inner-scroll container), use the same scroll
    # technique as the editor verify-scroll: find a contenteditable's parent
    # with overflow:auto/scroll AND scrollHeight > clientHeight.
    container_info = page.evaluate(
        """() => {
            const title = document.querySelector('textarea[name="Article Title"]');
            const composer = document.querySelector('div[data-testid="composer"]');
            const anchor = title || composer;
            if (!anchor) return {public: true, h: document.documentElement.scrollHeight, vh: window.innerHeight};
            let el = anchor.parentElement;
            while (el && el !== document.body) {
                const s = getComputedStyle(el);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 5) {
                    return {editor: true, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight};
                }
                el = el.parentElement;
            }
            return {public: true, h: document.documentElement.scrollHeight, vh: window.innerHeight};
        }"""
    )
    log(f"container: {container_info}")

    if container_info.get("editor"):
        sh = container_info["scrollHeight"]; ch = container_info["clientHeight"]
        step = int(ch * 0.85); i = 0; y = 0
        while y < sh:
            page.evaluate(
                f"""() => {{
                    const anchor = document.querySelector('textarea[name="Article Title"]') || document.querySelector('div[data-testid="composer"]');
                    let el = anchor.parentElement;
                    while (el && el !== document.body) {{
                        const s = getComputedStyle(el);
                        if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 5) {{
                            el.scrollTo({{top: {y}, behavior: 'instant'}}); return;
                        }}
                        el = el.parentElement;
                    }}
                }}"""
            )
            time.sleep(0.8)
            page.screenshot(path=str(OUT / f"scroll-{i:02d}.png"))
            log(f"editor scroll-{i:02d}.png  y={y}/{sh}")
            i += 1; y += step
    else:
        page.evaluate("window.scrollTo(0, 0)"); time.sleep(0.5)
        h = page.evaluate("document.documentElement.scrollHeight")
        vh = page.evaluate("window.innerHeight")
        step = int(vh * 0.85); i = 0; y = 0
        while y < h:
            page.evaluate(f"window.scrollTo(0, {y})")
            time.sleep(0.6)
            page.screenshot(path=str(OUT / f"scroll-{i:02d}.png"))
            log(f"page scroll-{i:02d}.png  y={y}/{h}")
            i += 1; y += step
    log("done")
