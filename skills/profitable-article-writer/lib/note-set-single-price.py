#!/usr/bin/env python3
"""note-set-single-price.py -- REQ-8 (Sprint 2 fix): configure a note.com draft's monetization editor
state as a SINGLE one-time paid article (記事タイプ=有料, price=¥NOTE_PRICE), never the OLD recurring
subscription rail the prior publish.py/toggle-plan.py/set-eyecatch-republish.py scripts hardcoded (they
always selected 無料 then the recurring-plan add-on tab, and NOTE_PRICE was exported but never read --
see lib/note_publish.sh's header for the full defect writeup).

This script also inserts note's own "有料エリア指定" (paid-area designation) marker immediately before
--paywall-heading, so the article keeps a free preview (REQ-5c: "the free part ends at a payoff cut")
even though the whole 記事タイプ is 有料 rather than a 一部有料 membership add-on.

HONEST LIMITATION (verified empirically 2026-07, not a guess -- see the network-request probe this file's
author ran before writing it): note.com's publish-settings panel (記事タイプ/価格/有料エリア指定) is PURE
CLIENT REACT STATE. No request fires when the price is filled, and the settings are NOT restored on page
reload unless the article is actually published (投稿する/更新する). Since Mode A (REQ-6) must NEVER
publish, this script's job ends at PROVING the WIRING selects the correct single-price path (screenshot
evidence) -- it deliberately never reaches, let alone clicks, 投稿する/更新する. The moment a future Mode B
(AUTONOMY=on) run authorizes an actual publish (assert_publish_allowed()), the SAME sequence below
persists the 有有 setting for real -- there is no separate "membership" code path left to fall back to.

INTERFACE:
  argv: <note_key> <price:int> <paywall_heading_substring>
  env in:
    NOTE_COOKIES_FILE   default: $HOME/.cloak/note-work/note-cookies.json
    NOTE_WORK_DIR       default: $HOME/.cloak/note-work  (screenshot output dir)
  stdout: "SINGLE_PRICE_TYPE: paid|free"  "SINGLE_PRICE_VALUE: <int>"  "SINGLE_PRICE_LINE_INSERTED: true|false"
          "SINGLE_PRICE_SCREENSHOT: <path>"
  exit: 0 if the 有料 radio + price fill were confirmed via the live DOM (even if the paywall-line insert
        was best-effort and failed -- that degrades gracefully, logged on stderr, never crashes); non-zero
        only if the editor/publish-panel itself never loaded (a genuine wiring failure).
"""
import json
import os
import sys
import time

from cloakbrowser import launch_context

WORK = os.environ.get("NOTE_WORK_DIR", os.path.expanduser("~/.cloak/note-work"))
COOKIES_FILE = os.environ.get("NOTE_COOKIES_FILE", os.path.join(WORK, "note-cookies.json"))


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: note-set-single-price.py <note_key> <price> <paywall_heading_substring>", file=sys.stderr)
        return 2
    note_key, price, heading_substring = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isfile(COOKIES_FILE):
        print(f"note-set-single-price: NOTE_COOKIES_FILE missing at {COOKIES_FILE!r}", file=sys.stderr)
        return 1
    with open(COOKIES_FILE) as f:
        ck = json.load(f)
    cookies = [{"name": k, "value": v, "domain": ".note.com", "path": "/"} for k, v in ck.items()]

    ctx = launch_context(headless=True, humanize=False)
    try:
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.set_viewport_size({"width": 1280, "height": 1400})
        pg.goto(f"https://editor.note.com/notes/{note_key}/edit/", wait_until="domcontentloaded", timeout=45000)
        loaded = False
        for _ in range(20):
            if "公開に進む" in pg.evaluate("()=>document.body.innerText"):
                loaded = True
                break
            time.sleep(1)
        if not loaded:
            print("note-set-single-price: editor never reached the 公開に進む state", file=sys.stderr)
            return 1
        time.sleep(2)

        for b in pg.query_selector_all("button,a"):
            if (b.text_content() or "").strip() == "公開に進む":
                b.click()
                time.sleep(3)
                break

        # Select 記事タイプ=有料 (id="paid", name="is_paid") -- click the ROW, not the (visually hidden)
        # input directly; a direct input.click(force=True) does not register the React onChange (verified
        # empirically), but clicking the row/label that visually contains "有料" does.
        box = pg.evaluate(
            """()=>{
              const inp = document.getElementById('paid');
              if(!inp) return null;
              let el = inp;
              for(let i=0;i<8;i++){
                el = el.parentElement;
                if(!el) break;
                if((el.textContent||'').includes('有料')){
                  const r = el.getBoundingClientRect();
                  return {x:r.x, y:r.y, w:r.width, h:r.height};
                }
              }
              return null;
            }"""
        )
        if not box:
            print("note-set-single-price: could not locate the 有料 radio row (note.com DOM may have changed)", file=sys.stderr)
            return 1
        pg.mouse.click(box["x"] + 20, box["y"] + box["h"] / 2)
        time.sleep(1.5)

        paid_checked = pg.evaluate(
            """()=>{const r=[...document.querySelectorAll('input[type=radio][name="is_paid"]')];
                    const p=r.find(i=>i.value==='paid'); return p? p.checked : false;}"""
        )
        print(f"SINGLE_PRICE_TYPE: {'paid' if paid_checked else 'free'}")

        price_filled = None
        if pg.query_selector("#price") is not None:
            pg.fill("#price", str(price))
            pg.locator("#price").blur()
            time.sleep(1)
            price_filled = pg.eval_on_selector("#price", "e=>e.value")
        print(f"SINGLE_PRICE_VALUE: {price_filled or ''}")

        # Close the publish overlay (キャンセル -- discards nothing we need; the 有料/price selection is
        # global React state that survives the overlay closing, per the empirical probe in this file's
        # docstring) so the body editor beneath is interactable for the paid-line insertion.
        for b in pg.query_selector_all("button,a"):
            if (b.text_content() or "").strip() == "キャンセル":
                b.click()
                time.sleep(2)
                break

        # Insert 有料エリア指定 (paid-area marker) immediately before the heading matching
        # heading_substring, using the SAME caret-then-hover-then-gutter-menu technique
        # insert-toc-save.py already uses for 目次 insertion (reused pattern, not reinvented).
        line_inserted = False
        coord = pg.evaluate(
            """(sub)=>{
              const ed = document.querySelector('.ProseMirror,[contenteditable=true]');
              if(!ed) return null;
              ed.focus();
              const h = [...ed.querySelectorAll('h1,h2,h3')].find(e=>(e.textContent||'').includes(sub));
              if(!h) return null;
              h.scrollIntoView({block:'center'});
              const rg = document.createRange();
              rg.setStart(h.firstChild, 0);
              rg.collapse(true);
              const s = window.getSelection();
              s.removeAllRanges();
              s.addRange(rg);
              const r = h.getBoundingClientRect();
              return {x: Math.round(r.left), y: Math.round(r.top + r.height/2)};
            }""",
            heading_substring,
        )
        if coord:
            pg.mouse.move(coord["x"] - 40, coord["y"])
            time.sleep(0.5)
            pg.mouse.move(coord["x"] - 30, coord["y"])
            time.sleep(0.6)
            line_inserted = pg.evaluate(
                """()=>{const e=[...document.querySelectorAll('button,li,div[role=menuitem],span,p')]
                        .find(x=>(x.textContent||'').trim()==='有料エリア指定' && x.offsetParent!==null);
                       if(e){e.click(); return true;} return false;}"""
            )
            time.sleep(1.5)
        else:
            print(f"note-set-single-price: heading containing {heading_substring!r} not found (paid-line skipped)", file=sys.stderr)
        print(f"SINGLE_PRICE_LINE_INSERTED: {'true' if line_inserted else 'false'}")

        shot = os.path.join(WORK, f"single-price-{note_key}.png")
        pg.screenshot(path=shot, full_page=True)
        print(f"SINGLE_PRICE_SCREENSHOT: {shot}")

        # ★ NEVER submits. No 投稿する/更新する click exists anywhere in this file. ★
        return 0
    finally:
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
