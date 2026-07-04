#!/usr/bin/env python3
"""note-set-eyecatch.py -- REQ-3 (Sprint 2 fix, defect #2): set a note.com draft's eyecatch (cover image)
via the editor's own "画像を追加" (add image) button, PERSISTED server-side (verified empirically: the
image URL survives a full page reload AND shows up as `eyecatch` in `GET /v3/notes/{key}` -- unlike the
Sprint-2-fix single-price panel, which is pure client state until an actual publish).

WHY BROWSER, NOT note_mcp's upload_eyecatch_image API: this file's author tried the note_mcp API path
FIRST (note_mcp.api.images.upload_eyecatch_image) and it raises
  note_mcp.models.NoteAPIError: Image upload failed: API response missing required field 'url'
on every call (a live, reproducible 500-ish response shape mismatch, not a network hiccup) -- confirming
the OLDER SKILL.md note ("eyecatch endpoint is buggy, response lacks 'url'") is still accurate for THIS
endpoint, even though note_mcp's OTHER image functions (upload_body_image, create_draft) work fine via the
API. The editor's "画像を追加" button drives a DIFFERENT endpoint the browser flow already exercises
successfully (verified 2026-07-04 against a real draft: eyecatch URL present in both the reloaded editor
DOM and the /v3/notes/{key} API response) -- so this file reuses that proven browser recipe rather than
retrying a structurally-broken API call.

INTERFACE:
  argv: <note_key> <cover_image_path>
  env in: NOTE_COOKIES_FILE   default: $HOME/.cloak/note-work/note-cookies.json
          NOTE_WORK_DIR       default: $HOME/.cloak/note-work  (screenshot output dir)
  stdout: "EYECATCH_SET: true|false"  "EYECATCH_SCREENSHOT: <path>"
  exit: 0 if the editor reached a state where the image-add flow could be attempted (even if the upload
        itself failed -- that is reported via EYECATCH_SET: false on stdout, never a crash); non-zero
        only if the editor/cookies never loaded at all (a genuine wiring failure).
"""
import os
import sys
import time

from note_browser_common import load_note_cookies, open_editor_ready

WORK = os.environ.get("NOTE_WORK_DIR", os.path.expanduser("~/.cloak/note-work"))
COOKIES_FILE = os.environ.get("NOTE_COOKIES_FILE", os.path.join(WORK, "note-cookies.json"))


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: note-set-eyecatch.py <note_key> <cover_image_path>", file=sys.stderr)
        return 2
    note_key, cover_path = sys.argv[1], sys.argv[2]

    if not os.path.isfile(cover_path):
        print(f"note-set-eyecatch: cover image not found at {cover_path!r}", file=sys.stderr)
        return 1
    cookies = load_note_cookies(COOKIES_FILE)
    if cookies is None:
        print(f"note-set-eyecatch: NOTE_COOKIES_FILE missing at {COOKIES_FILE!r}", file=sys.stderr)
        return 1

    ctx, pg = open_editor_ready(cookies, note_key, {"width": 1280, "height": 1000})
    try:
        if pg is None:
            print("note-set-eyecatch: editor never reached a ready state", file=sys.stderr)
            return 1
        time.sleep(2)
        pg.evaluate("window.scrollTo(0,0)")
        time.sleep(1)

        set_ok = False
        btn = pg.query_selector('button[aria-label="画像を追加"]')
        if btn is None:
            print("note-set-eyecatch: no 画像を追加 button found (note.com DOM may have changed)", file=sys.stderr)
        else:
            btn.click()
            time.sleep(2)
            try:
                with pg.expect_file_chooser(timeout=8000) as fc:
                    pg.click("text=画像をアップロード")
                fc.value.set_files(cover_path)
                time.sleep(5)
                saved = pg.evaluate(
                    """()=>{const b=[...document.querySelectorAll('button')].find(x=>(x.textContent||'').trim()==='保存'&&x.offsetParent!==null);
                             if(b){b.click(); return true;} return false;}"""
                )
                time.sleep(4)
                set_ok = bool(saved)
            except Exception as e:
                print(f"note-set-eyecatch: upload flow failed: {e}", file=sys.stderr)

        print(f"EYECATCH_SET: {'true' if set_ok else 'false'}")
        pg.evaluate("window.scrollTo(0,0)")
        time.sleep(1)
        shot = os.path.join(WORK, f"eyecatch-{note_key}.png")
        pg.screenshot(path=shot)
        print(f"EYECATCH_SCREENSHOT: {shot}")
        # ★ NEVER submits/publishes. This file only touches the editor's own image-add button. ★
        return 0
    finally:
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
