#!/usr/bin/env python3
"""note_browser_common.py -- shared cloakbrowser bootstrap helpers for the note.com Mode-A browser scripts
(lib/note-set-eyecatch.py, lib/note-set-single-price.py) AND the Sprint-2.5 real-publish tool
(lib/note-publish-live.py, REQ-21/PROP-22).

Sprint-2 contract-review FIND-006 fix: both scripts, authored together for the same PROP-21 fix, duplicated
~20 lines of (1) cookie-file load + cookie-dict-to-cloakbrowser-cookie-list conversion and (2) cloakbrowser
session bootstrap + navigate + "wait up to N seconds for the editor's own 公開に進む button to appear"
polling loop, differing only in a viewport constant and a log string. This module is the single place that
shared logic now lives; both callers import it instead of re-implementing it.

This module is deliberately Mode-A-agnostic: it knows nothing about eyecatch/price/paid-line logic, only
how to load note.com session cookies and get a cloakbrowser page onto a note.com draft editor in a ready
state. Neither caller's own distinct error-message wording changes -- this module never prints/exits by
itself; it returns None/`(ctx, None)` so each caller keeps its own clearly-labeled diagnostic.

Sprint-2.5 addition (REQ-21/PROP-22): `select_paid_price()` below is the 記事タイプ=有料/価格 selection +
DOM-readback sequence, EXTRACTED from lib/note-set-single-price.py's own inline block (Sprint 2) so BOTH
that script (which stops right after this call and clicks キャンセル -- it must NEVER publish, per REQ-6)
and lib/note-publish-live.py (which, ONLY after this call confirms 有料/price, proceeds to click
投稿する/更新する for real) share the exact SAME selection sequence rather than one re-inventing it. Moving
this here changes nothing observable about note-set-single-price.py's own stdout/behavior.
"""
import json
import os
import time
from typing import Optional

from cloakbrowser import launch_context


def load_note_cookies(cookies_file: str) -> Optional[list]:
    """Load a note.com cookies JSON file (a flat name->value dict) into the list-of-dicts shape
    cloakbrowser's `ctx.add_cookies()` expects. Returns None if the file does not exist -- the caller
    decides how to report that (each of note-set-eyecatch.py/note-set-single-price.py keeps its own
    distinct stderr message naming itself)."""
    if not os.path.isfile(cookies_file):
        return None
    with open(cookies_file) as f:
        ck = json.load(f)
    return [{"name": k, "value": v, "domain": ".note.com", "path": "/"} for k, v in ck.items()]


def open_editor_ready(cookies: list, note_key: str, viewport: dict, timeout_s: int = 20):
    """Launch a headless cloakbrowser context, add `cookies`, navigate to the note.com editor for
    `note_key`, and poll (up to `timeout_s` seconds, 1s apart) until the editor's own "公開に進む"
    (proceed-to-publish) button text appears in the page body -- the readiness signal both
    note-set-eyecatch.py and note-set-single-price.py already independently polled for before this fix.

    Returns `(ctx, pg)` on success. Returns `(ctx, None)` if the editor never reached the ready state
    within `timeout_s` -- the caller is responsible for `ctx.close()` in BOTH cases (this function never
    closes the context itself, since a caller may still want the context alive for its own diagnostics).
    """
    ctx = launch_context(headless=True, humanize=False)
    ctx.add_cookies(cookies)
    pg = ctx.new_page()
    pg.set_viewport_size(viewport)
    pg.goto(f"https://editor.note.com/notes/{note_key}/edit/", wait_until="domcontentloaded", timeout=45000)
    for _ in range(timeout_s):
        if "公開に進む" in pg.evaluate("()=>document.body.innerText"):
            return ctx, pg
        time.sleep(1)
    return ctx, None


def select_paid_price(pg, price) -> dict:
    """Click 公開に進む (if the overlay is not already open), select the 記事タイプ=有料 radio row, fill
    the price field, and read the resulting DOM state back. Returns:
      {"row_found": bool, "paid_checked": bool, "price_filled": str|None}

    `row_found=False` means the 有料 radio row itself could not be located (note.com's editor DOM may have
    changed) -- the caller should treat this as a hard failure, distinct from `paid_checked=False` (the row
    was found and clicked, but the DOM readback did not confirm it as checked).

    HONEST LIMITATION (verified empirically, see lib/note-set-single-price.py's own docstring for the full
    writeup): note.com's 記事タイプ/価格 selection is PURE CLIENT REACT STATE -- it is never persisted
    server-side, and is NOT restored across a page reload, until the article is actually published. This
    means "confirm the draft's price/type" and "set the draft's price/type" are the SAME action on
    note.com: there is no separate read-only check to perform first. Both lib/note-set-single-price.py
    (Mode-A, REQ-6 -- never publishes, always discards this selection via キャンセル) and
    lib/note-publish-live.py (Sprint-2.5, REQ-21 -- publishes for real ONLY when this returns a confirmed
    有料/price match) call this SAME function so neither re-invents the selection sequence.
    """
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
        return {"row_found": False, "paid_checked": False, "price_filled": None}

    pg.mouse.click(box["x"] + 20, box["y"] + box["h"] / 2)
    time.sleep(1.5)

    paid_checked = pg.evaluate(
        """()=>{const r=[...document.querySelectorAll('input[type=radio][name="is_paid"]')];
                const p=r.find(i=>i.value==='paid'); return p? p.checked : false;}"""
    )

    price_filled = None
    if pg.query_selector("#price") is not None:
        pg.fill("#price", str(price))
        pg.locator("#price").blur()
        time.sleep(1)
        price_filled = pg.eval_on_selector("#price", "e=>e.value")

    return {"row_found": True, "paid_checked": bool(paid_checked), "price_filled": price_filled}
