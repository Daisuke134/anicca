#!/usr/bin/env python3
"""v2: more targeted eyecatch upload. Look for the crop dialog explicitly
(role=dialog) and click its 保存 button inside that scope."""
import pathlib, time
from playwright.sync_api import sync_playwright

URL = "https://editor.note.com/notes/nb1148aabde59/edit/"
COVER = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/assets/IMG_4922.jpg")
OUT = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/note-verify-r2/eyecatch-v2")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(30000)
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(8)
    page.screenshot(path=str(OUT / "00-loaded.png"))

    # Click 画像を追加 (eyecatch slot)
    page.get_by_role("button", name="画像を追加").first.click()
    time.sleep(1.2)
    page.screenshot(path=str(OUT / "01-modal-open.png"))

    # Pick 画像をアップロード menu item → file chooser
    with page.expect_file_chooser(timeout=10000) as fc:
        page.get_by_text("画像をアップロード").first.click()
    fc.value.set_files(str(COVER))
    print("uploaded file")
    time.sleep(5)
    page.screenshot(path=str(OUT / "02-crop-dialog.png"))

    # Find the crop dialog (role=dialog) and click its 保存 button INSIDE it
    dialog = page.get_by_role("dialog").last
    try:
        dialog.get_by_role("button", name="保存").click()
        print("clicked dialog's 保存")
    except Exception as e:
        print(f"dialog 保存 click failed: {e!r}; falling back to global first 保存")
        page.get_by_role("button", name="保存").first.click()
    time.sleep(5)
    page.screenshot(path=str(OUT / "03-after-save.png"))

    # Wait for the eyecatch IMG element to appear above the title
    try:
        page.wait_for_selector('img[src*="assets.st-note"], img[src*="note.com"][alt!=""]', timeout=15000)
        print("eyecatch img element appeared")
    except Exception as e:
        print(f"eyecatch img wait timeout: {e!r}")
    time.sleep(3)
    page.screenshot(path=str(OUT / "04-final.png"), full_page=False)

    # Probe DOM
    info = page.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        return imgs.slice(0, 6).map(i => ({src: i.src.slice(0, 100), alt: i.alt.slice(0, 60)}));
    }""")
    print("top-6 images on page:")
    for i, m in enumerate(info):
        print(f"  [{i}] {m}")
