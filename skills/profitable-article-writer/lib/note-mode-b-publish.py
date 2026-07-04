#!/usr/bin/env python3
"""lib/note-mode-b-publish.py -- REQ-23/PROP-24 (Sprint 4, Dais 2026-07-04: "then wire that in, yes, we
have to"): the ONLY entrypoint run.sh's Mode-B branch uses to reach a real note.com publish click. It
imports and calls `lib/note_browser_common.confirm_and_publish()` -- the SAME shared unit
lib/note-publish-live.py's one-off tool (REQ-21/PROP-22) also imports. This file contains NO copy of the
pre-publish-check/click/exception-safety sequence itself; see confirm_and_publish's own docstring for the
single source of truth (PROP-24: the click statement exists in exactly one file, note_browser_common.py).

Unlike lib/note-publish-live.py, this file has NO NOTE_LIVE_PUBLISH manual-trigger gate: run.sh's own
ratio-derived effective-mode resolution (REQ-25) is what decides whether this file is even invoked for a
given wake. Requiring a SECOND manual human trigger here would defeat REQ-2's zero-human-in-Mode-B
invariant, which this wiring exists to finally satisfy end-to-end. Safety instead comes from (a) --draft-key
being required and explicit (no default/wildcard, same REQ-21 convention) -- run.sh only ever calls this
with a caller-supplied ARTICLE_MODEB_NOTE_KEY, never a wildcard, and (b) confirm_and_publish's own
pre-publish gates (eyecatch/visuals/price/type) refusing on anything not already fully prepared.

INTERFACE:
  argv: --draft-key KEY   (required, explicit, no default -- same REQ-21 no-wildcard convention)
        --price PRICE     (default: $NOTE_PRICE env or 500)
  env in:
    NOTE_COOKIES_FILE                default: $HOME/.cloak/note-work/note-cookies.json
    NOTE_WORK_DIR                    default: $HOME/.cloak/note-work
    NOTE_USER_ID                     default "14651590"
    NOTE_USERNAME                    default "anicca123"
    NOTE_MCP_SRC                     default: $HOME/.openclaw/external/note-mcp/src
    ARTICLE_NOTE_BROWSER_COMMON_DIR  TEST-INJECTION ONLY: if set, inserted at the FRONT of sys.path ahead of
                                      this file's own directory, so a test can substitute a fake
                                      note_browser_common module -- e.g. to dynamically COUNT calls to
                                      confirm_and_publish without ever touching a real browser (PROP-24's
                                      fault-injection call-count test uses this). Production never sets it.
  stdout on success (rc=0): NOTE_LIVE_URL / NOTE_LIVE_SCREENSHOT (same shape as note-publish-live.py)
  stderr + rc!=0 on refusal/failure, exact reason on first line. Never crashes silently, never fakes a URL.
"""
import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--draft-key",
        required=True,
        dest="draft_key",
        help="the EXACT note.com draft key to publish (no default, no wildcard)",
    )
    parser.add_argument("--price", default=os.environ.get("NOTE_PRICE", "500"))
    args = parser.parse_args()

    note_key = (args.draft_key or "").strip()
    if not note_key:
        print("note-mode-b-publish: REFUSED -- --draft-key must be a non-empty, explicit key", file=sys.stderr)
        return 1

    # Sprint-4 test-injection seam (PROP-24 fault-injection test): the OWN directory is inserted first (the
    # normal, production import path), then the override -- if set -- is inserted AFTER, at position 0 as
    # well, so it wins. Production never sets ARTICLE_NOTE_BROWSER_COMMON_DIR.
    own_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, own_dir)
    override_dir = os.environ.get("ARTICLE_NOTE_BROWSER_COMMON_DIR")
    if override_dir:
        sys.path.insert(0, override_dir)
    from note_browser_common import confirm_and_publish  # noqa: E402

    work_dir = os.environ.get("NOTE_WORK_DIR", os.path.expanduser("~/.cloak/note-work"))
    cookies_file = os.environ.get("NOTE_COOKIES_FILE", os.path.join(work_dir, "note-cookies.json"))
    note_mcp_src = os.environ.get("NOTE_MCP_SRC", os.path.expanduser("~/.openclaw/external/note-mcp/src"))
    user_id = os.environ.get("NOTE_USER_ID", "14651590")
    username = os.environ.get("NOTE_USERNAME", "anicca123")

    result = confirm_and_publish(
        note_key,
        price=args.price,
        cookies_file=cookies_file,
        note_mcp_src=note_mcp_src,
        user_id=user_id,
        username=username,
        work_dir=work_dir,
    )

    if not result.get("ok"):
        prefix = result.get("prefix") or "REFUSED"
        print(f"note-mode-b-publish: {prefix} for draft {note_key!r} -- {result.get('reason')}", file=sys.stderr)
        return 1

    print(f"NOTE_LIVE_URL: {result['url']}")
    print(f"NOTE_LIVE_SCREENSHOT: {result['screenshot']}")
    print(f"NOTE_LIVE_CLICKED: {result['clicked_label']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
