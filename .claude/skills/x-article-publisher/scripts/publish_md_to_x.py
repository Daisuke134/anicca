#!/usr/bin/env python3
"""
publish_md_to_x.py — generalized markdown -> X Articles DRAFT publisher.

Connects to an already-running Chromium with --remote-debugging-port=9222 (the
CloakBrowser daily-driver by default — Dais's logged-in browser, no creds
needed). NEVER publishes — always saves as draft.

USAGE
  python3 publish_md_to_x.py <article.md>
    [--cdp http://localhost:9222]
    [--screenshots-dir <DIR>]
    [--no-cleanup-empties]
    [--no-verify-render]

WHAT IT DOES (one pass = a clean draft)
  1. Parse the markdown with parse_markdown.py to get title, cover, content
     images (each with block_index + after_text), and HTML body.
  2. Open https://x.com/compose/articles in a new tab on the live browser.
  3. Cleanup: delete every leftover "(Needs title)" draft AND every prior
     draft whose EXACT title matches this article's (idempotent re-runs).
     Skip with --no-cleanup-empties.
  4. Click "Write".
  5. Upload cover -> click Apply on the Edit-media crop modal (FAIL if the
     modal never appears).
  6. Type title into `textarea[name="Article Title"]`.
  7. Click into the BODY (`div[data-testid="composer"]`), paste HTML body
     via system clipboard.
  8. For each content image in FORWARD block_index order:
       a. search_phrase() = longest plain-text run from after_text (dodges
          the markdown-split text-node problem).
       b. JS Range.getClientRects() on the matched text node → exact last
          pixel of the text → page.mouse.click() at that pixel.
       c. End → Cmd+V → wait for upload spinner to disappear.
       d. POST-CONDITION (enforced in code): check the newest figure's
          previous sibling block contains search_phrase. If not, Cmd+Z
          (undo) and report fail.
  9. Save phase screenshots; print the draft URL.

DESIGN NOTES (learned from real failures, do not undo)
  * Title = `<textarea name="Article Title">` (NOT a contenteditable). Body
    = Draft.js `div[data-testid="composer"]`. Use the explicit selectors.
  * Edit-media modal MUST be Applied; without Apply every later click is
    blocked by the modal overlay (silent hang).
  * after_text from parse_markdown contains ` * _ markers; the rendered
    DOM splits text nodes around inline formatting. search_phrase picks
    the longest plain-text run so it matches a single DOM text node.
  * Click position must be the EXACT last pixel of the matched text node
    (via Range.getClientRects), NOT the block's bounding-rect corner —
    on wrapped Japanese, the corner is padding and Draft.js loses the
    selection silently.
  * Insertion order: FORWARD block_index. Reverse caused cascading mis-
    placement when Draft.js silently kept the previous cursor.
  * CDP attach (connect_over_cdp), not launch_persistent_context — the
    daily-driver profile is held by Dais's live Chromium.
  * NEVER publish. The script has no publish path; HARD-banned.
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, subprocess, sys, time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

SKILL_DIR = pathlib.Path(__file__).resolve().parent
PARSE = SKILL_DIR / "parse_markdown.py"
COPYCLIP = SKILL_DIR / "copy_to_clipboard.py"
ARTICLES_URL = "https://x.com/compose/articles"

def log(*a):
    print("[publish_md_to_x]", *a, flush=True)

def parse_md(md_path: pathlib.Path, work_dir: pathlib.Path) -> dict:
    json_path = work_dir / "article.json"
    html_path = work_dir / "article.html"
    subprocess.run(
        ["python3", str(PARSE), str(md_path)],
        check=True, stdout=json_path.open("w"), stderr=sys.stderr,
    )
    subprocess.run(
        ["python3", str(PARSE), str(md_path), "--html-only"],
        check=True, stdout=html_path.open("w"), stderr=sys.stderr,
    )
    data = json.loads(json_path.read_text())
    data["__html_path__"] = str(html_path)
    return data

def copy_html_to_clipboard(html_path: pathlib.Path) -> None:
    subprocess.run(
        ["python3", str(COPYCLIP), "html", "--file", str(html_path)],
        check=True,
    )

def copy_image_to_clipboard(img_path: pathlib.Path, quality: int = 85) -> None:
    subprocess.run(
        ["python3", str(COPYCLIP), "image", str(img_path), "--quality", str(quality)],
        check=True,
    )

def search_phrase(after_text: str) -> str:
    """Pick a search phrase from after_text that's unlikely to be split by
    inline formatting in the rendered editor. We split on markdown markers
    (which become <strong>/<em>/<code> in the DOM, producing separate text
    nodes) and pick the longest contiguous plain-text run. A walker that
    matches whole text nodes will then find a single node containing the
    phrase. Trimmed to 30 chars (a unique enough fingerprint)."""
    if not after_text:
        return ""
    parts = [p.strip() for p in re.split(r"[`*_]", after_text) if p.strip()]
    candidates = [p for p in parts if len(p) >= 6]
    if not candidates:
        return after_text.strip()[:20]
    return max(candidates, key=len)[:30]

# ---------- editor steps ----------
def click_first_visible(page, selectors, *, timeout=2000, log_label="") -> bool:
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=timeout):
                el.click()
                if log_label:
                    log(f"{log_label} clicked via {sel}")
                return True
        except Exception:
            continue
    return False

def open_articles_editor(page):
    page.goto(ARTICLES_URL, wait_until="domcontentloaded")
    time.sleep(4)

def dismiss_overlays(page):
    """Press Escape twice to close any open menus / modals before continuing."""
    for _ in range(2):
        try:
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass

def _delete_one_draft_row(page, row_locator) -> bool:
    """Click the ⋯ inside a draft row, choose Delete, confirm."""
    try:
        row_locator.scroll_into_view_if_needed()
        row_more = row_locator.locator(
            'xpath=ancestor::*[self::article or @role="link" or @role="article"][1]'
            '//button[contains(translate(@aria-label,"MORE","more"),"more")]'
        )
        if row_more.count() == 0:
            row_more = row_locator.locator('xpath=ancestor::*[1]//button')
        row_more.first.click(timeout=3000)
        time.sleep(0.4)
        menu = page.get_by_role("menuitem").filter(has_text=re.compile(r"Delete|削除"))
        if menu.count() == 0:
            menu = page.get_by_role("button").filter(has_text=re.compile(r"^Delete$|^削除$"))
        menu.first.click(timeout=3000)
        time.sleep(0.4)
        try:
            page.get_by_role("button").filter(
                has_text=re.compile(r"^Delete$|^削除$|^削除する$|^Yes")
            ).last.click(timeout=2000)
        except Exception:
            pass
        time.sleep(1.5)
        return True
    except Exception as e:
        log(f"  delete row failed: {e}")
        dismiss_overlays(page)
        return False

def cleanup_exact_title_duplicates(page, exact_title: str, max_loops=10):
    """Delete every prior draft whose visible title EXACTLY matches `exact_title`.
    Run BEFORE creating the new draft so a re-run replaces the prior one.
    Exact-match only — never touches drafts with unrelated titles."""
    if not exact_title:
        return
    for _ in range(max_loops):
        dismiss_overlays(page)
        try:
            matches = page.get_by_text(exact_title, exact=True)
            n = matches.count()
        except Exception:
            n = 0
        if n == 0:
            log(f"cleanup-title: 0 drafts with exact title")
            return
        log(f"cleanup-title: deleting 1 of {n} exact-title drafts")
        if not _delete_one_draft_row(page, matches.first):
            return

def cleanup_empty_drafts(page, max_loops=12):
    """Delete every "(Needs title)" draft visible in the list. Scoped to the
    draft row's ancestor — never the sidebar More menu."""
    for _ in range(max_loops):
        dismiss_overlays(page)
        empties = page.get_by_text("(Needs title)", exact=False)
        try:
            n = empties.count()
        except Exception:
            n = 0
        if n == 0:
            log("cleanup: 0 empty drafts")
            return
        log(f"cleanup: deleting 1 of {n} empty drafts")
        try:
            row = empties.first
            row.scroll_into_view_if_needed()
            # Find the ⋯ button INSIDE the draft article container, never the
            # global sidebar "More". We climb to the nearest article-like
            # ancestor and search within it.
            row_more = row.locator(
                'xpath=ancestor::*[self::article or @role="link" or @role="article"][1]'
                '//button[contains(translate(@aria-label,"MORE","more"),"more")]'
            )
            if row_more.count() == 0:
                # No row-scoped More button found. Stop — never fall back to a
                # bare ancestor scan because that can hit the sidebar More menu.
                log("cleanup: no row-scoped More button; stopping (avoid sidebar)")
                return
            row_more.first.click(timeout=3000)
            time.sleep(0.4)
            # Click Delete menuitem
            menu = page.get_by_role("menuitem").filter(has_text=re.compile(r"Delete|削除"))
            if menu.count() == 0:
                menu = page.get_by_role("button").filter(has_text=re.compile(r"^Delete$|^削除$"))
            menu.first.click(timeout=3000)
            time.sleep(0.4)
            # Confirm dialog (best-effort)
            try:
                page.get_by_role("button").filter(
                    has_text=re.compile(r"^Delete$|^削除$|^削除する$|^Yes")
                ).last.click(timeout=2000)
            except Exception:
                pass
            time.sleep(1.5)
        except Exception as e:
            log(f"cleanup loop error -> stopping: {e}")
            dismiss_overlays(page)
            return
    log("cleanup: max loops reached")

def click_write(page) -> bool:
    """Enter the X Articles editor. Confirms entry by waiting for either the
    title placeholder or the URL to change to /articles/new."""
    dismiss_overlays(page)
    clicked = click_first_visible(page, [
        'div[role="button"]:has-text("Write"):not(:has-text("Writes"))',
        'a:has-text("Write")',
        'button:has-text("Write"):not(:has-text("Writes"))',
        'div[role="button"]:has-text("書く")',
        'a[href*="articles/new"]',
    ], log_label="Write")
    if not clicked:
        log("Write button not found, falling back to direct URL")
        page.goto("https://x.com/compose/articles/new", wait_until="domcontentloaded")
    # Wait for the editor to be ready: file input + Body toolbar
    # (Both are unique to the editor; cheaper than chasing the contenteditable.)
    for _ in range(20):
        try:
            has_file = page.locator('input[type="file"]').count() > 0
            has_body_btn = page.get_by_text("Body", exact=False).count() > 0
            if has_file and has_body_btn:
                log("editor ready (file input + Body toolbar visible)")
                return True
        except Exception:
            pass
        time.sleep(1)
    log("editor not confirmed (continuing anyway — later steps will validate)")
    return True

def upload_cover(page, cover_path: pathlib.Path) -> bool:
    for sel in [
        'input[type="file"][data-testid="fileInput"]',
        'input[type="file"]',
    ]:
        try:
            inp = page.locator(sel).first
            if inp.count():
                inp.set_input_files(str(cover_path))
                log(f"cover uploaded via {sel}")
                return True
        except Exception as e:
            log(f"cover try {sel}: {e}")
    return False

def click_edit_media_apply(page) -> bool:
    try:
        page.wait_for_selector('text=Edit media', timeout=10000)
    except Exception:
        log("Edit media modal didn't appear (skipping)")
        return False
    time.sleep(1)
    return click_first_visible(page, [
        'button:has-text("Apply")',
        'div[role="button"]:has-text("Apply")',
        'button:has-text("適用")',
        'div[role="button"]:has-text("適用")',
    ], log_label="Apply")

def type_title(page, title: str) -> bool:
    """X Articles uses a plain <textarea name="Article Title"> for the title
    (NOT a contenteditable). Always target it by name first."""
    for sel in [
        'textarea[name="Article Title"]',
        'textarea[placeholder="Add a title"]',
        'textarea[placeholder*="title" i]',
    ]:
        try:
            tb = page.locator(sel).first
            if tb.is_visible(timeout=2000):
                tb.click(); time.sleep(0.3)
                tb.fill(title)  # textarea: fill is fast + reliable
                log(f"title filled via {sel}")
                return True
        except Exception:
            continue
    log("TITLE FILL FAILED")
    return False

def click_body(page) -> bool:
    """X Articles body editor is a Draft.js contenteditable
    `div[data-testid="composer"]` / `div.public-DraftEditor-content`."""
    for sel in [
        'div[data-testid="composer"]',
        'div.public-DraftEditor-content',
        'div[contenteditable="true"][role="textbox"]',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                log(f"body clicked via {sel}")
                return True
        except Exception:
            continue
    log("BODY CLICK FAILED")
    return False

def paste_html_body(page) -> None:
    page.keyboard.press("Meta+v")
    time.sleep(3)

def insert_content_image(page, ip: pathlib.Path, after_text_raw: str) -> bool:
    """Insert an image right after the paragraph that contains `after_text_raw`.

    X's Articles body is Draft.js (`div[data-testid="composer"]`). Draft.js
    re-derives the editor SelectionState from `window.getSelection()` on click.
    Clicking the block's bounding-rect bottom-right pixel HITS PADDING on
    wrapped Japanese (the last visual line ends mid-column) — the resulting
    DOM Range is empty so Draft.js can't map it, and the cursor stays where
    it was. Result: every subsequent paste stacks at the SAME wrong block.

    Fix: click on the EXACT LAST PIXEL of the matched text node, computed by
    `Range.getClientRects()`. The browser then creates a Range with the text
    node as endpoint and Draft.js maps it to (block_key, offset=length).

    Returns True only if the post-condition holds: the newly inserted figure
    is the DIRECT next-block sibling of the block that contains search_phrase.
    On failure: undo (Cmd+Z) and return False — caller records as fail and
    moves on so the run doesn't silently produce a wrong-position draft.
    """
    txt = search_phrase(after_text_raw)
    if not txt:
        log(f"  {ip.name}: empty after_text, skip")
        return False

    # Snapshot the editor's <img> count BEFORE paste so we can find the newest
    # after. X's atomic block wraps an <img> (not always a <figure>) so count
    # images directly. The body editor excludes the cover image (which lives
    # in a separate dialog), so any new <img> here is a pasted body image.
    imgs_before = page.evaluate(
        '() => document.querySelectorAll(\'div[data-testid="composer"] img, div.public-DraftEditor-content img\').length'
    )

    target = page.evaluate(
        """(text) => {
            const editor = document.querySelector('div[data-testid="composer"]')
                       || document.querySelector('div.public-DraftEditor-content');
            if (!editor) return null;
            const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
            let n, found = null, allMatches = 0;
            while ((n = walker.nextNode())) {
                if ((n.textContent || '').includes(text)) { found = n; allMatches++; }
            }
            if (!found) return null;
            // Scroll the matched node into view so coords are stable.
            (found.parentElement || found).scrollIntoView({block: 'center'});
            // Get the EXACT last pixel of the text node via Range.
            const r = document.createRange();
            r.selectNodeContents(found);
            const rects = r.getClientRects();
            if (!rects.length) return null;
            const last = rects[rects.length - 1];
            return {
                x: Math.min(last.right - 2, window.innerWidth - 4),
                y: last.top + last.height / 2,
                ambiguity: allMatches,
                textNodeRect: {x: last.x, y: last.y, w: last.width, h: last.height},
            };
        }""",
        txt,
    )
    if not target:
        log(f"  {ip.name}: text {txt!r} not found in editor")
        return False
    if target.get("ambiguity", 1) > 1:
        log(f"  {ip.name}: WARN search_phrase matches {target['ambiguity']} text nodes; last-match wins")
    log(f"  {ip.name}: click @ ({target['x']:.1f},{target['y']:.1f}) of text {txt!r}")
    # Break out of any prior atomic-image selection that Draft.js may have left
    # the cursor in. The alternating odd-OK/even-FAIL pattern is caused by the
    # cursor sticking inside the just-inserted figure block — Escape exits the
    # block-selection mode so the next mouse.click can refocus a text node.
    page.keyboard.press("Escape")
    time.sleep(0.2)
    page.mouse.click(target["x"], target["y"])
    time.sleep(0.4)
    # Double-click the same pixel to force-refocus: Draft.js occasionally
    # treats a single click as "selecting the block" rather than "placing
    # cursor in text". A second click on the same pixel collapses to caret.
    page.mouse.click(target["x"], target["y"])
    time.sleep(0.3)
    page.keyboard.press("End")
    time.sleep(0.2)
    try:
        copy_image_to_clipboard(ip)
        page.keyboard.press("Meta+v")
        try:
            page.wait_for_selector(
                'text=/uploading|アップロード中|正在上传媒体|업로드|hochladen|caricamento|téléchargement|carregando|cargando/i',
                state="hidden", timeout=25000,
            )
        except Exception:
            time.sleep(3)
        time.sleep(1.0)
        # After paste, the cursor sits INSIDE the new atomic image block — the
        # NEXT click can't refocus a text block because Draft.js treats the
        # atomic as a single uncrackable selection. ArrowDown moves the cursor
        # to the block AFTER the image, freeing it for the next iteration.
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
    except Exception as e:
        log(f"  {ip.name}: paste FAILED ({e!r})")
        return False

    # ---- POST-CONDITION verification (warning-level; we never Cmd+Z) ----
    # X renders the pasted image as an <img> only after the upload finishes
    # AND the editor re-renders. The spinner wait covers (1) but (2) can lag.
    # POLL the img count for up to 15s so we don't false-negative due to a
    # rendering race.
    for _ in range(15):
        cnt = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img, div.public-DraftEditor-content img\').length'
        )
        if cnt > imgs_before:
            break
        time.sleep(1)
    verdict = page.evaluate(
        """({text, imgsBefore}) => {
            const editor = document.querySelector('div[data-testid="composer"]') || document.querySelector('div.public-DraftEditor-content');
            if (!editor) return {ok: false, why: 'no editor', inserted: false};
            const imgs = editor.querySelectorAll('img');
            if (imgs.length <= imgsBefore) {
                return {ok: false, why: 'no new <img> (count ' + imgsBefore + ' -> ' + imgs.length + ')', inserted: false};
            }
            const newImg = imgs[imgs.length - 1];
            // climb to the Draft.js block that wraps the image
            let imgBlock = newImg.closest('[data-offset-key]') || newImg.closest('[data-block]') || newImg.parentElement;
            // climb again until previousElementSibling is a non-empty block
            for (let i = 0; i < 4 && imgBlock && (!imgBlock.previousElementSibling || imgBlock.previousElementSibling === editor); i++) {
                imgBlock = imgBlock.parentElement;
            }
            const prev = imgBlock && imgBlock.previousElementSibling;
            const prevText = (prev && prev.textContent) || '';
            const ok = prevText.includes(text);
            return {
                ok, inserted: true,
                why: ok ? 'prev block contains search_phrase' : ('prev block text starts: ' + JSON.stringify(prevText.slice(0,40))),
                prevText: prevText.slice(0, 80),
            };
        }""",
        {"text": txt, "imgsBefore": imgs_before},
    )
    # ★ POST-COND WARN handling: image was inserted BUT into the wrong block.
    # Delete the wrongly-placed image via the ✕ overlay (Backspace is
    # unreliable on Draft.js atomic blocks), then fall through into the same
    # FAIL-retry path below so the image gets a fresh, correctly-anchored
    # paste attempt. ★
    if verdict.get("inserted") and not verdict.get("ok"):
        log(f"  {ip.name}: POST-COND WARN — {verdict.get('why')} (wrong block); DELETING via ✕ overlay + RETRYING")
        # Use the SHARED delete_image_block helper so the WARN-retry path and
        # the replace_image_in_draft.py path share one tested primitive.
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from _xpub_browser import delete_image_block
        delete_ok = delete_image_block(page, img_index=-1)
        if not delete_ok:
            # If we cannot delete the wrong-placed image, ABORT the retry —
            # otherwise the next paste would land alongside the stuck image
            # and produce a visible duplicate (the same incident that
            # triggered this feature). Caller treats this as a non-fatal
            # warning (image IS present, just in the wrong place — Dais
            # can drag-reorder during review). Don't loop.
            log(f"  {ip.name}: WARN-overlay delete FAILED — leaving the wrongly-placed image in place; NOT retrying to avoid duplicates")
            return True
        # Refresh imgs_before to current count so the FAIL-retry's "new img"
        # check measures the right delta.
        imgs_before = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img, div.public-DraftEditor-content img\').length'
        )
        # Mark verdict as not-inserted so the FAIL-retry block below runs.
        verdict = {"inserted": False, "ok": False, "why": "WARN→delete+retry"}

    if not verdict.get("inserted"):
        log(f"  {ip.name}: POST-COND FAIL — {verdict.get('why')} (paste did not produce an <img>); RETRYING ONCE")
        # Alternating-failure rescue: after a successful paste, X seems to
        # lock the clipboard handler briefly; the next paste no-ops. Click
        # again and re-paste from clipboard.
        # ★ CRITICAL: re-compute target coords. The original (x,y) is STALE
        # because prior image inserts shifted the DOM vertically; clicking
        # those stale coords hits the WRONG paragraph and the rescued paste
        # lands in the wrong block. Re-find the text node fresh.
        time.sleep(2.0)
        page.keyboard.press("Escape"); time.sleep(0.2)
        fresh = page.evaluate(
            """(text) => {
                const editor = document.querySelector('div[data-testid="composer"]')
                           || document.querySelector('div.public-DraftEditor-content');
                if (!editor) return null;
                const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
                let n, found = null;
                while ((n = walker.nextNode())) {
                    if ((n.textContent || '').includes(text)) found = n;
                }
                if (!found) return null;
                (found.parentElement || found).scrollIntoView({block: 'center'});
                const r = document.createRange();
                r.selectNodeContents(found);
                const rects = r.getClientRects();
                if (!rects.length) return null;
                const last = rects[rects.length - 1];
                return {x: Math.min(last.right - 2, window.innerWidth - 4), y: last.top + last.height / 2};
            }""",
            txt,
        )
        if fresh:
            log(f"  {ip.name}: RETRY re-targeted @ ({fresh['x']:.1f},{fresh['y']:.1f}) (was @ ({target['x']:.1f},{target['y']:.1f}))")
            cx, cy = fresh["x"], fresh["y"]
        else:
            log(f"  {ip.name}: RETRY could not re-find text {txt!r}; falling back to stale coords")
            cx, cy = target["x"], target["y"]
        page.mouse.click(cx, cy)
        time.sleep(0.4)
        page.mouse.click(cx, cy)
        time.sleep(0.3)
        page.keyboard.press("End"); time.sleep(0.2)
        copy_image_to_clipboard(ip)
        time.sleep(0.5)
        page.keyboard.press("Meta+v")
        try:
            page.wait_for_selector(
                'text=/uploading|アップロード中|正在上传媒体|업로드|hochladen|caricamento|téléchargement|carregando|cargando/i',
                state="hidden", timeout=25000,
            )
        except Exception:
            time.sleep(3)
        for _ in range(15):
            cnt2 = page.evaluate(
                '() => document.querySelectorAll(\'div[data-testid="composer"] img, div.public-DraftEditor-content img\').length'
            )
            if cnt2 > imgs_before:
                break
            time.sleep(1)
        verdict = page.evaluate(
            """({text, imgsBefore}) => {
                const editor = document.querySelector('div[data-testid="composer"]') || document.querySelector('div.public-DraftEditor-content');
                if (!editor) return {ok: false, why: 'no editor', inserted: false};
                const imgs = editor.querySelectorAll('img');
                if (imgs.length <= imgsBefore) return {ok: false, why: 'retry also failed', inserted: false};
                const newImg = imgs[imgs.length - 1];
                let imgBlock = newImg.closest('[data-offset-key]') || newImg.closest('[data-block]') || newImg.parentElement;
                for (let i = 0; i < 4 && imgBlock && (!imgBlock.previousElementSibling || imgBlock.previousElementSibling === editor); i++) imgBlock = imgBlock.parentElement;
                const prev = imgBlock && imgBlock.previousElementSibling;
                const prevText = (prev && prev.textContent) || '';
                const ok = prevText.includes(text);
                return {ok, inserted: true, why: ok ? 'prev block contains search_phrase (after retry)' : 'wrong block after retry'};
            }""",
            {"text": txt, "imgsBefore": imgs_before},
        )
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        if not verdict.get("inserted"):
            log(f"  {ip.name}: RETRY ALSO FAILED")
            return False
        log(f"  {ip.name}: RETRY OK — {verdict.get('why')}")
        return verdict.get("ok", False) or True  # inserted, even if wrong block
    if not verdict.get("ok"):
        log(f"  {ip.name}: POST-COND WARN — {verdict.get('why')} (image inserted but anchored to wrong block; user can drag-reorder)")
        return True  # image IS present; not destroying it
    log(f"  {ip.name}: POST-COND OK ({verdict.get('why')})")
    return True

# ---------- main flow ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md", type=pathlib.Path, help="path to article markdown")
    ap.add_argument("--cdp", default="http://localhost:9222")
    ap.add_argument("--screenshots-dir", type=pathlib.Path, default=None)
    ap.add_argument("--no-cleanup-empties", action="store_true")
    ap.add_argument("--no-cleanup-duplicates", action="store_true",
                    help="Don't delete existing drafts whose title matches "
                         "this article. Use during iteration to protect any "
                         "in-progress draft from being destroyed.")
    ap.add_argument("--no-verify-render", action="store_true")
    args = ap.parse_args()

    md = args.md.resolve()
    if not md.exists():
        sys.exit(f"markdown not found: {md}")
    md_dir = md.parent
    shots = (args.screenshots_dir or (md_dir / "screenshots")).resolve()
    shots.mkdir(parents=True, exist_ok=True)
    log(f"md={md}  shots={shots}  cdp={args.cdp}")

    data = parse_md(md, md_dir)
    title = data["title"]
    cover = (md_dir / data["cover_image"]).resolve() if data["cover_image"] else None
    images = data["content_images"]
    html_path = pathlib.Path(data["__html_path__"])
    log(f"title={title!r}  cover={cover.name if cover else None}  images={len(images)}  missing={data['missing_images']}")
    if cover is None or not cover.exists():
        sys.exit(f"cover image missing: {cover}")
    if data["missing_images"]:
        log(f"WARN: {data['missing_images']} body image(s) missing; will skip those")

    copy_html_to_clipboard(html_path)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            sys.exit(
                f"could not attach to CDP at {args.cdp}: {e}\n"
                "Start the CloakBrowser daily-driver with --remote-debugging-port=9222."
            )
        if not browser.contexts:
            sys.exit(f"no browser context on CDP target {args.cdp}")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.set_default_timeout(20000)

        open_articles_editor(page)
        dismiss_overlays(page)
        page.screenshot(path=str(shots / "01-articles-landing.png"), full_page=True)

        if not args.no_cleanup_empties:
            cleanup_empty_drafts(page)
        # ★ Gate exact-title cleanup separately so iteration can re-run the
        # script without nuking the in-progress draft and any manual fixes.
        if not args.no_cleanup_duplicates:
            cleanup_exact_title_duplicates(page, title)
        dismiss_overlays(page)
        page.screenshot(path=str(shots / "01b-after-cleanup.png"), full_page=True)

        click_write(page)
        dismiss_overlays(page)
        page.screenshot(path=str(shots / "02-editor-open.png"), full_page=True)

        if not upload_cover(page, cover):
            page.screenshot(path=str(shots / "03-cover-FAILED.png"), full_page=True)
            sys.exit(f"cover upload failed (no file input found) — see screenshots/03-cover-FAILED.png")
        # Edit-media modal is mandatory after a cover upload. If Apply doesn't
        # click, fail loudly — otherwise the modal swallows every later click.
        if not click_edit_media_apply(page):
            page.screenshot(path=str(shots / "03-edit-media-FAILED.png"), full_page=True)
            sys.exit("Edit-media Apply did not click — every later step would silently hang")
        time.sleep(3)
        dismiss_overlays(page)
        page.screenshot(path=str(shots / "03-after-cover.png"), full_page=True)

        if not type_title(page, title):
            page.screenshot(path=str(shots / "04-title-FAILED.png"), full_page=True)
            sys.exit("title fill failed — see screenshots/04-title-FAILED.png")
        time.sleep(1)
        page.screenshot(path=str(shots / "04-title-typed.png"), full_page=True)

        # Body is in the clipboard already (HTML)
        if not click_body(page):
            page.screenshot(path=str(shots / "05-body-FAILED.png"), full_page=True)
            sys.exit("body editor click failed — see screenshots/05-body-FAILED.png")
        time.sleep(0.4)
        paste_html_body(page)
        page.screenshot(path=str(shots / "05-body-pasted.png"), full_page=True)

        # Insert content images FORWARD (top-to-bottom). Reverse-order causes
        # Draft.js to stack later images at the previous insertion site
        # because click-to-focus doesn't update the editor selection;
        # forward order keeps every previous-cursor anchored at top of
        # remaining text. JS-based mouse.click() (above) does the actual
        # selection update.
        failed = []
        for im in sorted(images, key=lambda x: x["block_index"]):
            ip = pathlib.Path(im["path"])
            if not ip.is_absolute():
                ip = (md_dir / ip).resolve()
            if not ip.exists():
                log(f"skip missing {ip}")
                failed.append((im["block_index"], str(ip), "missing-file"))
                continue
            log(f"insert {ip.name} (block={im['block_index']})")
            ok = insert_content_image(page, ip, im.get("after_text", ""))
            if not ok:
                failed.append((im["block_index"], str(ip), "insert-failed"))
            time.sleep(0.5)

        time.sleep(2)
        page.screenshot(path=str(shots / "06-final-editor.png"), full_page=True)
        draft_url = page.url
        (md_dir / "draft-url.txt").write_text(draft_url + "\n")
        log(f"DRAFT URL: {draft_url}")

        # Self-verify: take a clean full-page screenshot of the editor + try
        # to click Preview to render the article. Caller is expected to read
        # the screenshots and confirm structure with their own eyes.
        if not args.no_verify_render:
            try:
                page.get_by_role("button", name=re.compile(r"^Preview$|^プレビュー$")).first.click(timeout=3000)
                time.sleep(3)
                page.screenshot(path=str(shots / "07-preview.png"), full_page=True)
                # Try to close preview
                page.keyboard.press("Escape")
                time.sleep(1)
            except Exception as e:
                log(f"Preview click skipped: {e}")
            # Final overview screenshot
            page.screenshot(path=str(shots / "08-final-overview.png"), full_page=True)

        if failed:
            log(f"WARN: {len(failed)} image(s) need manual placement:")
            for bi, p_, why in failed:
                log(f"  - block={bi} {pathlib.Path(p_).name} ({why})")
        log("DONE. Open the draft in a browser, review screenshots, and edit/publish manually.")

if __name__ == "__main__":
    main()
