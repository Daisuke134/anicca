#!/usr/bin/env python3
"""
Corgi Cafe JP article -> X Articles DRAFT.
Connects to the live CloakBrowser daily-driver via CDP (port 9222), opens a new
tab as a logged-in X user, uploads cover, fills title, pastes HTML body,
inserts content images at the correct block_index, and saves as DRAFT.
NEVER publishes. Screenshots the editor for human verification.

Output: ./screenshots/x-draft-*.png + console summary.
"""
import json, time, sys, os, subprocess, pathlib, html as html_lib
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HERE = pathlib.Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"; SHOTS.mkdir(exist_ok=True)
ARTICLE_JSON = HERE / "article.json"
ARTICLE_HTML = HERE / "article.html"
PUBLISH = os.environ.get("X_PUBLISH", "0") == "1"
CDP_URL = "http://localhost:9222"

def log(*a): print("[x-draft]", *a, flush=True)

def main():
    data = json.loads(ARTICLE_JSON.read_text())
    title = data["title"]
    cover = HERE / data["cover_image"]
    images = data["content_images"]
    html_body = ARTICLE_HTML.read_text()
    log(f"title={title!r}  cover={cover.name}  images={len(images)}")

    # Copy HTML to clipboard as RICH TEXT via the skill helper (sets NSHTMLPboardType)
    subprocess.run([
        "python3",
        str(pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"),
        "html", "--file", str(ARTICLE_HTML),
    ], check=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        # daily-driver has one persistent context
        ctx = browser.contexts[0]
        log(f"attached: {len(ctx.pages)} existing pages")
        page = ctx.new_page()
        page.set_default_timeout(20000)

        page.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
        time.sleep(4)
        page.screenshot(path=str(SHOTS / "01-articles-landing.png"), full_page=True)

        # ---- CLEANUP: delete every "(Needs title)" empty draft from prior runs ----
        for _ in range(10):
            empties = page.get_by_text("(Needs title)", exact=False)
            try:
                n = empties.count()
            except Exception:
                n = 0
            if n == 0:
                log("cleanup: no empty drafts left")
                break
            log(f"cleanup: {n} empty draft(s) left, deleting first")
            try:
                empties.first.scroll_into_view_if_needed()
                # Find the ... menu in the same row
                row = empties.first.locator('xpath=ancestor::article[1]')
                if row.count() == 0:
                    row = empties.first.locator('xpath=ancestor::*[@role="link" or @role="article"][1]')
                # The ... menu is a sibling within the row — fallback: search for a button[role=button] near it
                menu = page.locator('div[role="button"][aria-label*="More" i]').first
                # easier: hover on row, click the ... that appears at the right
                row_el = row.first if row.count() else empties.first
                row_el.hover()
                time.sleep(0.5)
                # Click the row's ... menu
                more = row_el.locator('button[aria-haspopup], [data-testid*="caret" i], [aria-label*="More" i]').first
                if more.count() == 0:
                    # try by structure — the right-side ... is typically last clickable
                    more = page.locator('[aria-label*="More" i]').first
                more.click(timeout=3000)
                time.sleep(0.5)
                # Click Delete menu item
                page.get_by_role("menuitem", name=lambda s: s and ("Delete" in s or "削除" in s)).first.click(timeout=3000)
                time.sleep(0.5)
                # Confirm
                try:
                    page.get_by_role("button", name=lambda s: s and ("Delete" in s or "削除" in s)).first.click(timeout=2000)
                except Exception:
                    pass
                time.sleep(1.5)
            except Exception as e:
                log(f"cleanup loop error (giving up): {e}")
                break
        page.screenshot(path=str(SHOTS / "01b-after-cleanup.png"), full_page=True)

        # Click "Write" (or 書く) primary CTA — opens a fresh editor
        clicked = False
        for selector in [
            'div[role="button"]:has-text("Write"):not(:has-text("Writes"))',
            'button:has-text("Write"):not(:has-text("Writes"))',
            'a:has-text("Write")',
            'div[role="button"]:has-text("書く")',
            'a[href*="articles/new"]',
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click(); clicked = True; log(f"clicked create via {selector}")
                    break
            except Exception:
                continue
        if not clicked:
            # try by accessible name
            try:
                page.get_by_role("button", name="Write").first.click(timeout=3000)
                clicked = True; log("clicked Write via role")
            except Exception:
                page.goto("https://x.com/compose/articles/new", wait_until="domcontentloaded")
                log("fallback: goto /compose/articles/new")
        time.sleep(5)
        page.screenshot(path=str(SHOTS / "02-editor-open.png"), full_page=True)

        # Upload cover image
        cover_uploaded = False
        for selector in [
            'input[type="file"][data-testid="fileInput"]',
            'input[type="file"]',
        ]:
            try:
                inp = page.locator(selector).first
                if inp.count():
                    inp.set_input_files(str(cover))
                    cover_uploaded = True
                    log(f"cover uploaded via {selector}")
                    break
            except Exception as e:
                log(f"cover try {selector}: {e}")
        if cover_uploaded:
            # X opens an "Edit media" crop modal. Click Apply to confirm.
            try:
                page.wait_for_selector('text=Edit media', timeout=10000)
            except Exception:
                pass
            time.sleep(1)
            page.screenshot(path=str(SHOTS / "03-crop-modal.png"), full_page=True)
            applied = False
            for sel in [
                'button:has-text("Apply")',
                'div[role="button"]:has-text("Apply")',
                'button:has-text("適用")',
                'div[role="button"]:has-text("適用")',
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        btn.click(); applied = True; log(f"Apply clicked via {sel}")
                        break
                except Exception:
                    continue
            if not applied:
                log("WARN: Apply not clicked; trying ESC to dismiss")
                page.keyboard.press("Escape")
            time.sleep(3)
        page.screenshot(path=str(SHOTS / "03b-after-cover.png"), full_page=True)

        # Find TITLE textbox specifically (X uses placeholder "Add a title")
        title_filled = False
        for selector in [
            'div[contenteditable="true"][data-placeholder="Add a title"]',
            'div[contenteditable="true"][aria-placeholder="Add a title"]',
            'div[role="textbox"][aria-label="Add a title"]',
            'div[role="textbox"][aria-placeholder*="title" i]',
        ]:
            try:
                tb = page.locator(selector).first
                if tb.is_visible(timeout=2000):
                    tb.click(); time.sleep(0.3)
                    tb.type(title, delay=8)
                    title_filled = True
                    log(f"title typed via {selector}")
                    break
            except Exception:
                continue
        if not title_filled:
            # fallback by visible placeholder text scan
            try:
                tb = page.get_by_text("Add a title", exact=True).first
                tb.click(); time.sleep(0.3)
                page.keyboard.type(title, delay=8)
                title_filled = True
                log("title typed via get_by_text fallback")
            except Exception as e:
                log(f"TITLE FILL FAILED: {e}")
        time.sleep(1)
        page.screenshot(path=str(SHOTS / "04-title-typed.png"), full_page=True)

        # Click into BODY editor (must NOT be the title element).
        # X Articles body has placeholder like "Tell your story..." / aria-label "body"
        body_clicked = False
        body_selectors = [
            'div[contenteditable="true"][data-placeholder*="story" i]',
            'div[contenteditable="true"][aria-placeholder*="story" i]',
            'div[contenteditable="true"][data-placeholder*="Tell" i]',
            'div[role="textbox"][aria-label*="body" i]',
        ]
        for selector in body_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click(); body_clicked = True
                    log(f"body clicked via {selector}")
                    break
            except Exception:
                continue
        if not body_clicked:
            # Fallback: find ALL contenteditable=true, pick the one whose
            # placeholder/aria is not the title.
            handles = page.query_selector_all('div[contenteditable="true"]')
            log(f"fallback: {len(handles)} contenteditables found")
            for h in handles:
                ph = (h.get_attribute("data-placeholder") or "") + " " + (h.get_attribute("aria-placeholder") or "") + " " + (h.get_attribute("aria-label") or "")
                if "title" in ph.lower(): continue
                try:
                    h.scroll_into_view_if_needed()
                    h.click()
                    body_clicked = True
                    log(f"body clicked via fallback (placeholder={ph!r})")
                    break
                except Exception as e:
                    log(f"  fallback click err: {e}")
        time.sleep(0.6)
        if body_clicked:
            page.keyboard.press("Meta+v")
            time.sleep(3)
        page.screenshot(path=str(SHOTS / "05-body-pasted.png"), full_page=True)

        # Insert content images in REVERSE block_index order
        import re as _re
        def _strip_md(s):
            # Remove markdown markers and pick the longest contiguous plain run
            s = _re.sub(r'[`*_]', '', s)
            return s.strip()
        images_sorted = sorted(images, key=lambda x: -x["block_index"])
        for im in images_sorted:
            ip = HERE / im["path"]
            if not ip.exists():
                log(f"skip missing {ip}")
                continue
            raw = (im.get("after_text") or "").strip()
            after_text = _strip_md(raw)[:25]
            log(f"insert {ip.name} (block={im['block_index']}) after: {after_text!r}")
            inserted = False
            if after_text:
                try:
                    para = page.get_by_text(after_text, exact=False).last
                    para.scroll_into_view_if_needed()
                    para.click()
                    page.keyboard.press("End")
                    time.sleep(0.3)
                    # Copy image to clipboard then paste
                    subprocess.run([
                        "python3",
                        str(pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"),
                        "image", str(ip), "--quality", "85"
                    ], check=True)
                    page.keyboard.press("Meta+v")
                    # Wait for upload
                    try:
                        page.wait_for_selector('text=正在上传媒体', state="hidden", timeout=20000)
                    except Exception:
                        time.sleep(3)
                    inserted = True
                except Exception as e:
                    log(f"insert {ip.name} FAILED via text: {e}")
            if not inserted:
                log(f"WARN: could not insert {ip.name} (manual placement needed)")
            time.sleep(0.6)

        time.sleep(2)
        page.screenshot(path=str(SHOTS / "06-final-editor.png"), full_page=True)

        if PUBLISH:
            log("X_PUBLISH=1 set but publishing is DISABLED by HARD RULE. Skipping.")

        # Draft auto-saves on X Articles. Capture the URL.
        url = page.url
        log(f"draft URL: {url}")
        with (HERE / "draft-url.txt").open("w") as f:
            f.write(url + "\n")

        log("DONE. Screenshots in screenshots/. Review the editor and edit/publish manually.")

if __name__ == "__main__":
    main()
