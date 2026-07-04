#!/usr/bin/env python3
"""lib/note-publish-live.py -- REQ-21/PROP-22 (Sprint 2.5, Dais 2026-07-04: "the note is not actually
published, we have to have it actually published, after the verification"): the ONE-OFF, standalone,
human/main-agent-invoked tool that makes ONE already-prepared note.com draft PUBLIC for real.

★ THIS FILE IS STRUCTURALLY EXCLUDED FROM run.sh's CALL GRAPH ★ -- it is never imported/called/sourced by
run.sh, never reachable from the AUTONOMY branch, and never reachable from any unattended daily-wake path
(grep-verified by tests/test-prop22a-live-publish-wiring.sh, case (a)). It is invoked directly, by name, by
a human or the main agent -- naming the exact draft key -- and nothing else. This does NOT satisfy, and is
NOT claimed to satisfy, REQ-2's zero-human-in-Mode-B invariant (REQ-2 is scoped to run.sh's own automated
publish branch, REQ-7, which this tool is structurally excluded from).

SAFETY GATES (all fail-closed, cheapest/safest first, checked BEFORE any browser action):
  1. env NOTE_LIVE_PUBLISH=1 must be set -- checked FIRST, before argument parsing or any file/network I/O.
     Absent => refuse immediately, print why, exit 1. Zero side effects.
  2. --draft-key <KEY> is a REQUIRED, EXPLICIT CLI argument -- no default, no wildcard (unlike
     lib/note_publish.sh's Mode-A wiring, which reads $ARTICLE_NOTE_KEY with a "new" default -- REQ-21
     requires the caller to name the exact key every time).
  3. Pre-publish state confirmation, in this order:
       a. eyecatch present        -- an AUTHENTICATED GET /v3/notes/<key> (note_mcp's own NoteAPIClient,
                                      the SAME client class get_article()/create_draft() already use
                                      internally -- not a new HTTP layer). The public, logged-out endpoint
                                      404s for a DRAFT, so this must be the authenticated call (unlike
                                      PROP-23's post-publish verify, which is deliberately logged-out).
       b. >=1 visual figure       -- the SAME authenticated response's note_draft.body (raw HTML) contains
                                      at least one "<img" tag.
          Both (a) and (b) run with NO BROWSER at all -- if either fails, the tool refuses and exits
          before cloakbrowser/note_browser_common is ever imported.
       c. 記事タイプ=有料/価格=NOTE_PRICE -- note.com's price/type selection is PURE CLIENT REACT STATE,
          never persisted across a reload until an actual publish (see note-set-single-price.py's own
          docstring for the empirical writeup) -- so "confirm" and "set" are the SAME action here. This
          step opens the REAL browser session and calls note_browser_common.select_paid_price(), the
          EXACT shared DOM-read/select routine note-set-single-price.py itself uses (Sprint 2.5 extracted
          it into note_browser_common.py precisely so this file could reuse it, not re-invent it).
     ANY of (a)/(b)/(c) failing => refuse, close any open browser session, exit 1, and print the EXACT
     missing piece on stderr. No 投稿する/更新する click is ever attempted.
  Sprint-3 contract-review FIND-004 fix: the ENTIRE browser-session lifecycle below (from
    open_editor_ready() through the final click-or-refuse decision) runs inside one try/except/finally.
    ANY unexpected exception (a browser-launch failure, a cookie/navigation error, an unforeseen DOM
    change) is caught and re-reported through this SAME clean-refusal stderr path -- never a raw
    traceback -- and the browser context is always closed in `finally` (guarded so it never double-closes
    or crashes if the context was never created).
  4. Only when (a) AND (b) AND (c) all confirm does this file proceed, IN THE SAME BROWSER SESSION that
     just confirmed (c), to click 有料エリア設定 (note.com's next-step button once 有料/price are selected
     -- required to reach the screen the 投稿する/更新する button lives on; note-set-single-price.py
     deliberately never clicks this, since it must never get anywhere near publish) and then click
     whichever of 投稿する (brand-new draft) or 更新する (already-published draft being updated) is
     actually present -- this is a REAL side effect.

An always-refuse stub cannot satisfy this file's contract: PROP-22's own test suite requires a REAL
success path (tests/test-prop22b-live-publish-real-click.sh) against a real note.com TEST draft.

INTERFACE:
  argv: --draft-key KEY   (required, explicit, no default)
  env in:
    NOTE_LIVE_PUBLISH     required, must equal "1"
    NOTE_PRICE            default 500
    NOTE_COOKIES_FILE     default: $HOME/.cloak/note-work/note-cookies.json
    NOTE_WORK_DIR         default: $HOME/.cloak/note-work (screenshot output dir)
    NOTE_USER_ID          default "14651590" (same note_mcp Session convention lib/note_publish.sh and
    NOTE_USERNAME         default "anicca123"  note-create-rich-draft.py already use)
    NOTE_MCP_SRC          default: $HOME/.openclaw/external/note-mcp/src
  stdout on success (rc=0):
    NOTE_LIVE_URL: https://note.com/<username>/n/<key>
    NOTE_LIVE_SCREENSHOT: <path>
  stderr + rc!=0 on ANY refusal/failure, with the exact blocking reason on the first line. Never crashes
  silently, never fakes a URL.
"""
import argparse
import asyncio
import json
import os
import sys
import time


def _confirm_eyecatch_and_visuals(note_key: str, cookies_file: str, note_mcp_src: str, user_id: str, username: str):
    """Authenticated GET /v3/notes/<note_key> via note_mcp's own NoteAPIClient (no new HTTP layer).
    Returns (ok: bool, reason: str|None, status: str|None) -- `status` is the raw API status string
    ("draft"/"published"/...), used later only for logging (the actual click searches for whichever of
    投稿する/更新する is present, not a hardcoded branch on this value -- see main()).

    NO BROWSER is touched by this function -- cloakbrowser/note_browser_common are not imported here.
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


def main() -> int:
    # Gate 1 (REQ-21): NOTE_LIVE_PUBLISH=1 -- checked FIRST, before ANY other I/O (argparse included), so
    # an unset trigger refuses with ZERO side effects -- not even a cookies-file read.
    if os.environ.get("NOTE_LIVE_PUBLISH") != "1":
        print(
            "note-publish-live: REFUSED -- NOTE_LIVE_PUBLISH=1 is not set in the environment. This tool "
            "performs a deliberate, ONE-OFF real-publish action (REQ-21) and requires the explicit "
            "trigger. No browser/network action was taken.",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--draft-key",
        required=True,
        dest="draft_key",
        help="the EXACT note.com draft key to publish (no default, no wildcard)",
    )
    args = parser.parse_args()  # argparse itself exits(2) with a clear stderr message if --draft-key is missing

    note_key = (args.draft_key or "").strip()
    if not note_key:
        print("note-publish-live: REFUSED -- --draft-key must be a non-empty, explicit key", file=sys.stderr)
        return 1

    price = os.environ.get("NOTE_PRICE", "500")
    work_dir = os.environ.get("NOTE_WORK_DIR", os.path.expanduser("~/.cloak/note-work"))
    cookies_file = os.environ.get("NOTE_COOKIES_FILE", os.path.join(work_dir, "note-cookies.json"))
    note_mcp_src = os.environ.get("NOTE_MCP_SRC", os.path.expanduser("~/.openclaw/external/note-mcp/src"))
    user_id = os.environ.get("NOTE_USER_ID", "14651590")
    username = os.environ.get("NOTE_USERNAME", "anicca123")

    # Gate 3a/3b (REQ-21): eyecatch + visuals, via the authenticated API only -- NO browser touched yet.
    ok, reason, status = _confirm_eyecatch_and_visuals(note_key, cookies_file, note_mcp_src, user_id, username)
    if not ok:
        print(
            f"note-publish-live: REFUSED for draft {note_key!r} -- {reason}. No browser opened, no click attempted.",
            file=sys.stderr,
        )
        return 1

    # Gate 3c (REQ-21): 記事タイプ=有料/価格 -- the ONLY gate that genuinely needs a browser, because this
    # state is pure client React state on note.com (never persisted). EXTENDS
    # note_browser_common.select_paid_price(), the SAME function note-set-single-price.py uses -- not
    # re-invented here.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from note_browser_common import load_note_cookies, open_editor_ready, select_paid_price  # noqa: E402

    cookies = load_note_cookies(cookies_file)
    if cookies is None:
        print(f"note-publish-live: REFUSED -- NOTE_COOKIES_FILE missing at {cookies_file!r}", file=sys.stderr)
        return 1

    ctx = None
    try:
        ctx, pg = open_editor_ready(cookies, note_key, {"width": 1280, "height": 1400})
        if pg is None:
            print(
                f"note-publish-live: REFUSED for draft {note_key!r} -- the editor never reached the "
                f"公開に進む state. No click attempted.",
                file=sys.stderr,
            )
            return 1
        time.sleep(2)

        sel = select_paid_price(pg, price)
        if not sel["row_found"]:
            print(
                f"note-publish-live: REFUSED for draft {note_key!r} -- could not locate the 有料 radio row "
                f"(note.com DOM may have changed). No click attempted.",
                file=sys.stderr,
            )
            return 1
        if not sel["paid_checked"]:
            print(
                f"note-publish-live: REFUSED for draft {note_key!r} -- 記事タイプ could not be confirmed as "
                f"有料 after selection. No click attempted.",
                file=sys.stderr,
            )
            return 1
        if sel["price_filled"] != str(price):
            print(
                f"note-publish-live: REFUSED for draft {note_key!r} -- price confirmed as "
                f"{sel['price_filled']!r}, expected {price!r}. No click attempted.",
                file=sys.stderr,
            )
            return 1

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
            print(
                f"note-publish-live: REFUSED for draft {note_key!r} -- could not find/click 有料エリア設定 "
                f"(note.com DOM may have changed). No publish click attempted.",
                file=sys.stderr,
            )
            return 1
        time.sleep(2)
        pg.evaluate("window.scrollTo(0,0)")
        time.sleep(0.5)

        # ★ THE REAL CLICK ★ -- search for whichever of 投稿する (brand-new draft) / 更新する (a draft
        # already published once) is actually present, rather than hardcoding a branch on the pre-fetched
        # `status` value (which could be stale between the API check above and this click).
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
            print(
                f"note-publish-live: REFUSED-AFTER-ATTEMPT for draft {note_key!r} -- neither 投稿する nor "
                f"更新する could be found/clicked on the 有料エリア設定 screen (note.com DOM may have changed; "
                f"last known status={status!r}).",
                file=sys.stderr,
            )
            return 1

        for _ in range(12):
            body_text = pg.evaluate("()=>document.body.innerText")
            if "/publish/" not in pg.url or "公開しました" in body_text:
                break
            time.sleep(1)
        time.sleep(5)

        shot = os.path.join(work_dir, f"live-publish-{note_key}.png")
        pg.screenshot(path=shot, full_page=False)

        print(f"NOTE_LIVE_URL: https://note.com/{username}/n/{note_key}")
        print(f"NOTE_LIVE_SCREENSHOT: {shot}")
        print(f"NOTE_LIVE_CLICKED: {clicked_label}", file=sys.stderr)
        return 0
    except Exception as e:
        # Sprint-3 contract-review FIND-004 fix: ANY unexpected exception anywhere in the browser-session
        # lifecycle above (open_editor_ready's own launch/cookie/navigation failure, or an unforeseen DOM
        # error during select_paid_price/the click sequence) is caught HERE and re-reported through the
        # SAME clean-refusal stderr shape every other gate in this file uses -- never a raw traceback.
        print(
            f"note-publish-live: REFUSED for draft {note_key!r} -- an unexpected browser-session error "
            f"occurred: {e}. No publish click can be confirmed to have succeeded from this failure alone; "
            f"if this happened after a click attempt, verify the draft's live status independently via "
            f"lib/note-verify-live.py before assuming either outcome.",
            file=sys.stderr,
        )
        return 1
    finally:
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
