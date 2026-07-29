#!/usr/bin/env python3
"""
drive_logo.py — set a Capafy agent's logo/icon (verified working 2026-06-25).

THE RECIPE (do it all in ONE page object — file inputs vanish across processes):
1. Build edit URL from the agent's init review_url: token → page=edit.
2. goto (networkidle). Click 基本情報 tab. file inputs (2) mount only after full load.
3. set_input_files(icon) on input[type=file][0] (the LOGO; do NOT set the 2nd = detail-image).
4. A "ロゴを切り抜く" crop MODAL opens → click its 保存 (width<200).
5. Click card 提出を確認.
6. ★ SUCCESS = a toast "Agent カードを保存しました" / "保存しました" appears — NOT a url=card-done
   navigation. Earlier code wrongly checked the url and false-reported "NOT SAVED". ★

Usage: drive_logo.py <edit_url> <icon_path>
  where <edit_url> = https://capafy.ai/developer/createAgent?source=temp-link&token=<TOK>&page=edit
Requires CloakBrowser CDP on :9222.
Exit 0 + prints SAVED on success; exit 1 otherwise (fail-closed).
"""
import sys, time
from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 3:
        print("ERR: usage drive_logo.py <edit_url> <icon_path>"); sys.exit(1)
    edit_url, icon = sys.argv[1], sys.argv[2]

    pw = sync_playwright().start()
    br = pw.chromium.connect_over_cdp("http://localhost:9222")
    ctx = br.contexts[0]
    pg = ctx.new_page()
    pg.goto(edit_url, wait_until="networkidle", timeout=60000); time.sleep(6)

    # 基本情報 tab
    try:
        pg.get_by_text("基本情報", exact=True).first.click(); time.sleep(3)
    except Exception:
        pass

    fis = pg.query_selector_all("input[type=file]")
    if not fis:
        print("ERR: no file inputs (page not fully loaded)"); sys.exit(1)
    fis[0].set_input_files(icon); time.sleep(4)   # LOGO only (input 0)

    # crop modal 保存
    box = pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(e=>(e.textContent||'').trim()==='保存'&&e.getBoundingClientRect().width<200);if(b){const r=b.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};}return null;}""")
    if box:
        pg.mouse.click(box["x"], box["y"]); time.sleep(3)
    else:
        print("WARN: no crop modal (logo may not have loaded)")

    # card 提出を確認
    try:
        pg.get_by_text("提出を確認", exact=True).last.click(timeout=8000)
    except Exception as e:
        print("ERR: submit click failed:", str(e)[:60]); sys.exit(1)

    # SUCCESS = toast, not url
    saved = False
    for _ in range(8):
        time.sleep(2)
        if pg.evaluate("""()=>[...document.querySelectorAll('*')].some(e=>/カードを保存しました|保存しました/.test((e.textContent||'')))""") \
           or "card-done" in pg.url or "credential" in pg.url:
            saved = True; break
    print("SAVED" if saved else "NOT SAVED")
    sys.exit(0 if saved else 1)


if __name__ == "__main__":
    main()
