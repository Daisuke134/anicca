#!/usr/bin/env python3
"""Probe latest Corgi draft (167454580 / nb1148aabde59) with hard reload +
console/network capture so we see WHY the editor is blank."""
import time
from playwright.sync_api import sync_playwright

# Try both URL forms
for label, URL in [
    ("by-id", "https://editor.note.com/notes/167454580/edit/"),
    ("by-key", "https://editor.note.com/notes/nb1148aabde59/edit/"),
]:
    print(f"\n========== {label}: {URL} ==========")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.set_default_timeout(20000)
        page.set_viewport_size({"width": 1400, "height": 900})

        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:200]}"))
        page.on("pageerror", lambda err: console_msgs.append(f"[PAGEERR] {str(err)[:200]}"))

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(8)
        # force hard reload
        page.reload(wait_until="networkidle")
        time.sleep(8)

        info = page.evaluate("""() => ({
            url: location.href,
            cookies_count: document.cookie.split(';').filter(Boolean).length,
            has_editor: !!document.querySelector('[class*="ProseMirror"], [contenteditable="true"]'),
            has_title_input: !!document.querySelector('input[placeholder*="タイトル"], textarea[placeholder*="タイトル"]'),
            body_text_len: document.body.innerText.length,
            body_first_300: document.body.innerText.slice(0, 300),
            img_count: document.querySelectorAll('img').length,
        })""")
        for k, v in info.items():
            print(f"  {k}: {v}")
        print(f"  console msgs ({len(console_msgs)}):")
        for m in console_msgs[:15]:
            print(f"    {m}")
        page.screenshot(path=f"/Users/anicca/anicca-project/docs/articles/corgi-cafe/note-verify-r1/diag-{label}.png", full_page=True)
        page.close()
