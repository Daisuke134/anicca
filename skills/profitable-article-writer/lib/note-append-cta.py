#!/usr/bin/env python3
"""lib/note-append-cta.py -- REQ-27 fix (Sprint 5, post-adversary FIND-001): appends the monetization link
to the REMOTE note.com draft body via note_mcp's authenticated API, BEFORE the Mode-B publish click.

WHY this exists (FIND-001, fresh-context adversary, blocking): `run.sh`'s `insert_monetization_link` only
ever wrote the CTA link into the wake's LOCAL throwaway `draft.md`. That file is read into the real note.com
article body ONLY on the Mode-A path (`lib/note_publish.sh` -> `lib/note-create-rich-draft.py` uploads it
verbatim as the body of a BRAND-NEW draft). Mode B (`lib/note-mode-b-publish.py` -> `note_browser_common.
confirm_and_publish`) does NOT create/upload a body at all -- it only confirms an ALREADY-PREPARED remote
draft's eyecatch/visuals/price and clicks 投稿する/更新する on the note.com editor. The local draft.md's CTA
link therefore NEVER reached the real published Mode-B article; recording `cta_url` in STATE.md for that
path was recording a claim the system had not actually made true.

This tool closes that gap the SAME way the rest of this skill already extends note.com content
programmatically (`lib/note-create-rich-draft.py` also does an authenticated note_mcp GET/POST cycle, never
a new HTTP layer) -- it does NOT touch the browser or the publish click at all (that stays the single shared
`confirm_and_publish` unit, PROP-24's grep-count-1 invariant is unaffected):
  1. `note_mcp.api.articles.get_article_raw_html` -- authenticated GET of the draft's CURRENT raw HTML body
     (never Markdown-converted, so nothing is lost/mangled on round-trip).
  2. If `cta_url` is already present in that body (idempotency -- a re-run, e.g. after an UNCONFIRMED Mode-B
     wake, must never append a second, duplicate CTA block), this is a no-op success.
  3. Otherwise, append one `<p>` line (lead-in text + link) to the body and save it back via
     `note_mcp.api.articles.update_article_raw_html` (draft_save, is_temp_saved=true -- a DRAFT save, the
     SAME endpoint family `lib/note-create-rich-draft.py`'s image-append flow uses -- never the publish
     endpoint itself).

INTERFACE:
  argv: --draft-key KEY (required, explicit, no default/wildcard -- same REQ-21 convention)
        --cta-url URL   (required; caller is responsible for resolving the empty-string opt-out BEFORE
                         invoking this tool at all -- this tool's own job is "append this URL", not decide
                         whether to)
        --cta-text TEXT (optional, default "最新情報はこちら")
  env in:
    NOTE_COOKIES_FILE   default: $HOME/.cloak/note-work/note-cookies.json
    NOTE_MCP_SRC        default: $HOME/.openclaw/external/note-mcp/src
    NOTE_USER_ID        default "14651590"
    NOTE_USERNAME       default "anicca123"
  stdout on success (rc=0): CTA_APPENDED: true|already-present
  stderr + rc!=0 on any failure -- exact reason on the first line. NEVER raises uncaught, NEVER silently
  claims success (a caller MUST treat rc!=0 as "the remote body does not carry the link" and record that
  honestly, e.g. STATE.md's `cta_url:` left empty with a `cta_status: append_failed:<reason>` field --
  never a fabricated cta_url).
"""
import argparse
import asyncio
import html as html_escape_mod
import json
import os
import sys


def _build_cta_html(cta_text: str, cta_url: str) -> str:
    safe_text = html_escape_mod.escape(cta_text)
    safe_url = html_escape_mod.escape(cta_url, quote=True)
    return f'<p>{safe_text}: <a href="{safe_url}" target="_blank" rel="noopener">{safe_url}</a></p>'


async def _append_cta(note_key: str, cta_url: str, cta_text: str, cookies_file: str, note_mcp_src: str, user_id: str, username: str) -> dict:
    sys.path.insert(0, note_mcp_src)
    try:
        from note_mcp.api.articles import get_article_raw_html, update_article_raw_html
        from note_mcp.models import NoteAPIError, Session
    except Exception as e:
        return {"ok": False, "reason": f"note_mcp import failed (NOTE_MCP_SRC={note_mcp_src!r}): {e}", "already_present": False}

    if not os.path.isfile(cookies_file):
        return {"ok": False, "reason": f"NOTE_COOKIES_FILE missing at {cookies_file!r}", "already_present": False}
    try:
        with open(cookies_file) as f:
            cookies = json.load(f)
    except Exception as e:
        return {"ok": False, "reason": f"NOTE_COOKIES_FILE at {cookies_file!r} could not be read/parsed: {e}", "already_present": False}

    session = Session(cookies=cookies, user_id=user_id, username=username, created_at=0)

    try:
        article = await get_article_raw_html(session, note_key)
    except NoteAPIError as e:
        return {"ok": False, "reason": f"authenticated GET /v3/notes/{note_key} failed: {e}", "already_present": False}
    except Exception as e:
        return {"ok": False, "reason": f"authenticated GET /v3/notes/{note_key} failed unexpectedly: {e}", "already_present": False}

    body = article.body or ""
    # Idempotency check must compare against what _build_cta_html actually WRITES into the body: the
    # HTML-escaped url (html.escape(cta_url, quote=True)). Comparing the raw cta_url would miss any url
    # containing &/</>/" (e.g. tracking params ?utm_source=note&utm_campaign=x), silently appending a
    # DUPLICATE CTA block on every re-run. Check the escaped form (raw kept too for pre-escape legacy bodies).
    safe_url = html_escape_mod.escape(cta_url, quote=True)
    if safe_url in body or cta_url in body:
        # Idempotent no-op: the link is ALREADY carried by the remote draft body (e.g. a re-run after an
        # UNCONFIRMED Mode-B wake) -- this counts as success (the invariant this tool exists to guarantee,
        # "the remote body carries the link", already holds), never a duplicate second append.
        return {"ok": True, "reason": None, "already_present": True}

    new_body = body + _build_cta_html(cta_text, cta_url)
    try:
        await update_article_raw_html(session, note_key, article.title, new_body)
    except NoteAPIError as e:
        return {"ok": False, "reason": f"draft_save (body update) for {note_key} failed: {e}", "already_present": False}
    except Exception as e:
        return {"ok": False, "reason": f"draft_save (body update) for {note_key} failed unexpectedly: {e}", "already_present": False}

    return {"ok": True, "reason": None, "already_present": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draft-key", required=True, dest="draft_key")
    parser.add_argument("--cta-url", required=True, dest="cta_url")
    parser.add_argument("--cta-text", default="最新情報はこちら", dest="cta_text")
    args = parser.parse_args()

    note_key = (args.draft_key or "").strip()
    cta_url = (args.cta_url or "").strip()
    if not note_key:
        print("note-append-cta: REFUSED -- --draft-key must be a non-empty, explicit key", file=sys.stderr)
        return 1
    if not cta_url:
        print("note-append-cta: REFUSED -- --cta-url must be non-empty (caller decides opt-out BEFORE invoking this tool)", file=sys.stderr)
        return 1

    cookies_file = os.environ.get("NOTE_COOKIES_FILE", os.path.expanduser("~/.cloak/note-work/note-cookies.json"))
    note_mcp_src = os.environ.get("NOTE_MCP_SRC", os.path.expanduser("~/.openclaw/external/note-mcp/src"))
    user_id = os.environ.get("NOTE_USER_ID", "14651590")
    username = os.environ.get("NOTE_USERNAME", "anicca123")

    result = asyncio.run(_append_cta(note_key, cta_url, args.cta_text, cookies_file, note_mcp_src, user_id, username))

    if not result.get("ok"):
        print(f"note-append-cta: FAILED for draft {note_key!r} -- {result.get('reason')}", file=sys.stderr)
        return 1

    if result.get("already_present"):
        print("CTA_APPENDED: already-present")
    else:
        print("CTA_APPENDED: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
