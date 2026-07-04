#!/usr/bin/env python3
"""note_browser_common.py -- shared cloakbrowser bootstrap helpers for the note.com Mode-A browser scripts
(lib/note-set-eyecatch.py, lib/note-set-single-price.py) AND the real-publish mechanism (REQ-21/PROP-22,
REQ-23/PROP-24) shared by lib/note-publish-live.py (the one-off tool) and lib/note-mode-b-publish.py
(run.sh's unattended Mode-B in-loop caller, Sprint 4).

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
and `confirm_and_publish()` (which, ONLY after this call confirms 有料/price, proceeds to click
投稿する/更新する for real) share the exact SAME selection sequence rather than one re-inventing it.

Sprint-4 addition (REQ-23/PROP-24, "wire that in"): `confirm_and_publish()` is THE single shared
publish-click unit. It moves the ENTIRE REQ-21 confirm->click sequence (eyecatch/visuals confirmation,
price/type confirmation+selection, the REAL 投稿する/更新する click, and the try/except/finally
exception-safety wrapper, Sprint-3 FIND-004) here so BOTH lib/note-publish-live.py (the human/main-agent
one-off tool) and lib/note-mode-b-publish.py (run.sh's unattended Mode-B branch) call the SAME function --
neither re-wraps or reimplements any part of it. The publish-click JS statement below is the ONLY occurrence
of that statement anywhere in this skill (PROP-24: grep count == 1).

`cloakbrowser` is imported LAZILY, inside `open_editor_ready()` only -- NOT at this module's top level. This
preserves REQ-21's "zero browser action" property for a draft that fails the eyecatch/visuals gate: a
caller can import this whole module (including `confirm_and_publish`) and have `confirm_and_publish` refuse
before ever touching cloakbrowser, even on a host where cloakbrowser is not installed at all.
"""
import asyncio
import json
import os
import sys
import time
from typing import Optional


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

    `cloakbrowser` is imported HERE (lazily), not at module top level -- see this module's own docstring
    for why (REQ-21's zero-browser-action refusal path must not require cloakbrowser to be importable).

    Sprint-3 contract-review FIND-004 fix: `launch_context()` succeeding but `add_cookies()`/`new_page()`/
    `goto()`/the readiness poll then raising (a realistic cloakbrowser-launch flake, a malformed-cookie
    exception, or a navigation timeout) used to leak that already-created context -- the exception propagated
    out of this function BEFORE it ever returned a `(ctx, ...)` tuple, so no caller could ever obtain a handle
    to close it. This function now closes any context IT created, best-effort, before re-raising, so no
    caller-side exception handler can ever inherit an orphaned headless browser process from this function.
    """
    from cloakbrowser import launch_context

    ctx = launch_context(headless=True, humanize=False)
    try:
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.set_viewport_size(viewport)
        pg.goto(f"https://editor.note.com/notes/{note_key}/edit/", wait_until="domcontentloaded", timeout=45000)
        for _ in range(timeout_s):
            if "公開に進む" in pg.evaluate("()=>document.body.innerText"):
                return ctx, pg
            time.sleep(1)
        return ctx, None
    except Exception:
        try:
            ctx.close()
        except Exception:
            pass
        raise


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
    `confirm_and_publish()` (REQ-21/REQ-23 -- publishes for real ONLY when this returns a confirmed
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


def _confirm_eyecatch_and_visuals(note_key: str, cookies_file: str, note_mcp_src: str, user_id: str, username: str):
    """Authenticated GET /v3/notes/<note_key> via note_mcp's own NoteAPIClient (no new HTTP layer).
    Returns (ok: bool, reason: str|None, status: str|None) -- `status` is the raw API status string
    ("draft"/"published"/...), used later only for logging.

    NO BROWSER is touched by this function -- cloakbrowser is never imported here (nor anywhere else in
    this module until `open_editor_ready()` is actually called).
    """
    if not os.path.isfile(cookies_file):
        return False, f"NOTE_COOKIES_FILE missing at {cookies_file!r}", None

    sys.path.insert(0, note_mcp_src)
    try:
        from note_mcp.api.client import NoteAPIClient
        from note_mcp.models import Session
    except Exception as e:
        return False, f"note_mcp import failed (NOTE_MCP_SRC={note_mcp_src!r}): {e}", None

    try:
        with open(cookies_file) as f:
            cookies = json.load(f)
    except Exception as e:
        return False, f"NOTE_COOKIES_FILE at {cookies_file!r} could not be read/parsed: {e}", None

    session = Session(cookies=cookies, user_id=user_id, username=username, created_at=0)

    async def _get():
        async with NoteAPIClient(session) as client:
            r = await client.get(f"/v3/notes/{note_key}")
            return r.get("data", {})

    try:
        data = asyncio.run(_get())
    except Exception as e:
        return False, f"authenticated GET /v3/notes/{note_key} failed: {e}", None

    status = data.get("status")
    eyecatch = data.get("eyecatch")
    note_draft = data.get("note_draft") or {}
    body_html = note_draft.get("body") or data.get("body") or ""
    img_count = body_html.count("<img") if isinstance(body_html, str) else 0

    if not eyecatch:
        return (
            False,
            f"eyecatch NOT set on draft {note_key!r} (confirmed via authenticated GET /v3/notes/{note_key}: "
            f"the 'eyecatch' field is empty)",
            status,
        )
    if img_count < 1:
        return (
            False,
            f"draft {note_key!r} has ZERO <img> tags in its body (confirmed via authenticated GET "
            f"/v3/notes/{note_key}: expected >=1 visual figure per REQ-21)",
            status,
        )
    return True, None, status


def confirm_and_publish(
    note_key: str,
    *,
    price,
    cookies_file: str,
    note_mcp_src: str,
    user_id: str,
    username: str,
    work_dir: str,
) -> dict:
    """THE single shared publish-click unit (REQ-21/REQ-23, PROP-22/PROP-24). Confirms REQ-21's 3
    pre-publish gates -- (a) eyecatch present, (b) >=1 visual figure, (c) 記事タイプ=有料/価格=price -- and,
    ONLY if all 3 confirm, performs the REAL 投稿する/更新する click. This is the ONE code path in this
    entire skill that ever reaches that click (grep-verifiable: the click statement below exists in exactly
    one file). Both lib/note-publish-live.py (the human/main-agent-invoked one-off tool, REQ-21) and
    lib/note-mode-b-publish.py (run.sh's unattended Mode-B in-loop caller, REQ-23) call this SAME function
    -- neither re-wraps nor reimplements any part of it; a future change here applies to both identically.

    Gates (a)/(b) run with NO BROWSER AT ALL -- cloakbrowser is only imported (lazily, inside
    `open_editor_ready`) once gates (a)/(b) already confirm, so a caller whose draft fails those gates never
    even imports the browser layer (preserves REQ-21's "zero browser action on refusal" property).

    Gate (c) and the click itself run inside ONE try/except/finally (Sprint-3 FIND-004 fix, now living
    HERE, the single shared unit, not re-wrapped per caller): ANY unexpected exception in the browser-session
    lifecycle is caught and reported as a clean refusal, never a raw traceback, and the browser context is
    ALWAYS closed in `finally` (guarded against double-close / never-created).

    Returns (never raises):
      {"ok": bool, "reason": str|None, "prefix": "REFUSED"|"REFUSED-AFTER-ATTEMPT"|None,
       "clicked_label": str|None, "url": str|None, "screenshot": str|None, "status": str|None}
    `ok=False` means no publish click was confirmed to have succeeded; `reason` names the exact blocking
    piece a caller should surface verbatim (callers prefix it with their own tool name + note_key).
    """
    ok, reason, status = _confirm_eyecatch_and_visuals(note_key, cookies_file, note_mcp_src, user_id, username)
    if not ok:
        return {
            "ok": False,
            "reason": f"{reason}. No browser opened, no click attempted.",
            "prefix": "REFUSED",
            "clicked_label": None,
            "url": None,
            "screenshot": None,
            "status": status,
        }

    cookies = load_note_cookies(cookies_file)
    if cookies is None:
        return {
            "ok": False,
            "reason": f"NOTE_COOKIES_FILE missing at {cookies_file!r}",
            "prefix": "REFUSED",
            "clicked_label": None,
            "url": None,
            "screenshot": None,
            "status": status,
        }

    ctx = None
    try:
        ctx, pg = open_editor_ready(cookies, note_key, {"width": 1280, "height": 1400})
        if pg is None:
            return {
                "ok": False,
                "reason": "the editor never reached the 公開に進む state. No click attempted.",
                "prefix": "REFUSED",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }
        time.sleep(2)

        sel = select_paid_price(pg, price)
        if not sel["row_found"]:
            return {
                "ok": False,
                "reason": "could not locate the 有料 radio row (note.com DOM may have changed). No click attempted.",
                "prefix": "REFUSED",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }
        if not sel["paid_checked"]:
            return {
                "ok": False,
                "reason": "記事タイプ could not be confirmed as 有料 after selection. No click attempted.",
                "prefix": "REFUSED",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }
        if sel["price_filled"] != str(price):
            return {
                "ok": False,
                "reason": (
                    f"price confirmed as {sel['price_filled']!r}, expected {str(price)!r}. No click attempted."
                ),
                "prefix": "REFUSED",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }

        # All 3 gates confirmed -- proceed, in the SAME session, to the screen the 投稿する/更新する button
        # lives on (note.com requires an explicit "次に進む" step -- 有料エリア設定 -- once 有料/price are
        # selected, before that button appears at all).
        area_clicked = pg.evaluate(
            """()=>{
              const b=[...document.querySelectorAll('button,a,div[role=button]')]
                .find(x=>(x.textContent||'').trim()==='有料エリア設定' && x.offsetParent!==null);
              if(b){b.click(); return true;} return false;
            }"""
        )
        if not area_clicked:
            return {
                "ok": False,
                "reason": (
                    "could not find/click 有料エリア設定 (note.com DOM may have changed). "
                    "No publish click attempted."
                ),
                "prefix": "REFUSED",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }
        time.sleep(2)
        pg.evaluate("window.scrollTo(0,0)")
        time.sleep(0.5)

        # *** THE REAL CLICK *** -- search for whichever of 投稿する (brand-new draft) / 更新する (a draft
        # already published once) is actually present, rather than hardcoding a branch on the pre-fetched
        # `status` value (which could be stale between the API check above and this click). THIS IS THE
        # ONLY OCCURRENCE OF THIS STATEMENT ANYWHERE IN THIS SKILL (PROP-24: grep count == 1).
        clicked_label = None
        for label in ("投稿する", "更新する"):
            posted = pg.evaluate(
                """(label)=>{
                  const el=[...document.querySelectorAll('button,a,div[role=button],span')]
                    .find(b=>(b.textContent||'').trim()===label && b.offsetParent!==null);
                  if(el){el.scrollIntoView({block:'center'}); el.click(); return true;} return false;
                }""",
                label,
            )
            if not posted:
                try:
                    pg.get_by_text(label, exact=True).first.click(timeout=4000)
                    posted = True
                except Exception:
                    posted = False
            if posted:
                clicked_label = label
                break

        if not clicked_label:
            return {
                "ok": False,
                "reason": (
                    f"neither 投稿する nor 更新する could be found/clicked on the 有料エリア設定 screen "
                    f"(note.com DOM may have changed; last known status={status!r})."
                ),
                "prefix": "REFUSED-AFTER-ATTEMPT",
                "clicked_label": None,
                "url": None,
                "screenshot": None,
                "status": status,
            }

        for _ in range(12):
            body_text = pg.evaluate("()=>document.body.innerText")
            if "/publish/" not in pg.url or "公開しました" in body_text:
                break
            time.sleep(1)
        time.sleep(5)

        shot = os.path.join(work_dir, f"live-publish-{note_key}.png")
        pg.screenshot(path=shot, full_page=False)

        return {
            "ok": True,
            "reason": None,
            "prefix": None,
            "clicked_label": clicked_label,
            "url": f"https://note.com/{username}/n/{note_key}",
            "screenshot": shot,
            "status": status,
        }
    except Exception as e:
        # Sprint-3 contract-review FIND-004 fix (now living in the single shared unit, Sprint 4): ANY
        # unexpected exception anywhere in the browser-session lifecycle above (open_editor_ready's own
        # launch/cookie/navigation failure, or an unforeseen DOM error during select_paid_price/the click
        # sequence) is caught HERE and re-reported through the SAME clean-refusal shape every other gate in
        # this function uses -- never a raw traceback.
        return {
            "ok": False,
            "reason": (
                f"an unexpected browser-session error occurred: {e}. No publish click can be confirmed to "
                f"have succeeded from this failure alone; if this happened after a click attempt, verify "
                f"the draft's live status independently via lib/note-verify-live.py before assuming either "
                f"outcome."
            ),
            "prefix": "REFUSED",
            "clicked_label": None,
            "url": None,
            "screenshot": None,
            "status": status,
        }
    finally:
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass
