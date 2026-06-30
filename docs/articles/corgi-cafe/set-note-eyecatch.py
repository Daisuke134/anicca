#!/usr/bin/env python3
"""Set the Corgi note draft's eyecatch (見出し画像) via the browser UI.
note-mcp upload_eyecatch_image is buggy (returns no 'url' field); this
clicks the top 「画像を追加」 button → uploads IMG_4922.jpg → crops → 保存."""
import pathlib, time
from playwright.sync_api import sync_playwright

URL = "https://editor.note.com/notes/nb1148aabde59/edit/"
COVER = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/assets/IMG_4922.jpg")
OUT = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/note-verify-r2/eyecatch")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(30000)
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(8)
    page.screenshot(path=str(OUT / "00-loaded.png"), full_page=False)

    # Click the eyecatch placeholder ("画像を追加" / picture frame icon at top
    # of the editor, above the title). Try several locators.
    clicked = False
    for locator_desc, fn in [
        ("aria-label 画像を追加", lambda: page.get_by_role("button", name="画像を追加").first),
        ("text 画像を追加", lambda: page.get_by_text("画像を追加").first),
        ("svg/icon at top-left of title area", None),
    ]:
        if fn is None:
            continue
        try:
            loc = fn()
            loc.scroll_into_view_if_needed()
            loc.click(timeout=2500)
            clicked = True
            print(f"OK: clicked via {locator_desc}")
            break
        except Exception as e:
            print(f"  miss {locator_desc}: {str(e)[:80]}")
    if not clicked:
        # Last-resort: the eyecatch slot is the icon at top center above the
        # title. Click that area directly. The diag screenshot shows it at
        # roughly (700, 130) in this viewport.
        print("falling back to coord click @ (700, 130)")
        page.mouse.click(700, 130)
        time.sleep(0.8)
    time.sleep(1.5)
    page.screenshot(path=str(OUT / "01-after-click-placeholder.png"), full_page=False)

    # Click the "画像をアップロード" entry in the dialog; then file_chooser
    try:
        with page.expect_file_chooser(timeout=10000) as fc:
            try:
                page.get_by_role("button", name="画像をアップロード").first.click(timeout=3000)
            except Exception:
                page.get_by_text("画像をアップロード").first.click(timeout=3000)
        chooser = fc.value
        chooser.set_files(str(COVER))
        print(f"uploaded: {COVER}")
    except Exception as e:
        print(f"file chooser FAILED: {str(e)[:200]}")
        page.screenshot(path=str(OUT / "02-chooser-FAILED.png"), full_page=False)
        raise SystemExit(1)

    time.sleep(4)  # wait for upload + crop dialog
    page.screenshot(path=str(OUT / "03-after-upload.png"), full_page=False)

    # Click 「保存」 on the crop dialog
    saved = False
    for n in ("保存", "適用", "Save", "Apply"):
        try:
            page.get_by_role("button", name=n).first.click(timeout=2500)
            saved = True
            print(f"clicked 保存 button: {n}")
            break
        except Exception:
            pass
    if not saved:
        print("crop save button NOT found — image may already be saved")
    time.sleep(3)
    page.screenshot(path=str(OUT / "04-after-save.png"), full_page=False)

    # Verify eyecatch is now set
    eyecatch_present = page.evaluate("""() => {
        const slot = document.querySelector('[class*="EyeCatch"], [class*="eyecatch"], img[alt*="アイキャッチ"], img[alt*="見出し"]');
        return slot ? slot.outerHTML.slice(0, 200) : null;
    }""")
    print(f"eyecatch slot HTML: {eyecatch_present}")
    page.screenshot(path=str(OUT / "05-final.png"), full_page=False)
