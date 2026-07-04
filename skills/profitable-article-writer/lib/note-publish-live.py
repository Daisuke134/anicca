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

Sprint 4 (REQ-23/PROP-24, "wire that in"): the confirm->click sequence below (pre-publish state
confirmation + the actual click + the try/except/finally exception-safety) now lives in
`lib/note_browser_common.confirm_and_publish()` -- the SAME shared function `lib/note-mode-b-publish.py`
(run.sh's unattended Mode-B in-loop caller) also imports and calls. This file contains NO copy of that
sequence anymore; it only owns its OWN two gates that make it a distinct, safe ONE-OFF tool:

SAFETY GATES owned by THIS file (checked BEFORE ever calling the shared function):
  1. env NOTE_LIVE_PUBLISH=1 must be set -- checked FIRST, before argument parsing or any file/network I/O.
     Absent => refuse immediately, print why, exit 1. Zero side effects.
  2. --draft-key <KEY> is a REQUIRED, EXPLICIT CLI argument -- no default, no wildcard (unlike
     lib/note_publish.sh's Mode-A wiring, which reads $ARTICLE_NOTE_KEY with a "new" default -- REQ-21
     requires the caller to name the exact key every time).

Everything else (eyecatch/visuals confirmation, price/type confirmation+selection, the real
投稿する/更新する click, and the exception-safety wrapper) is `note_browser_common.confirm_and_publish()`'s
job -- see that function's own docstring for the full gate sequence and PROP-24's single-source guarantee.

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
import os
import sys


def main() -> int:
    # Gate 1 (REQ-21): NOTE_LIVE_PUBLISH=1 -- checked FIRST, before ANY other I/O (argparse included), so
    # an unset trigger refuses with ZERO side effects -- not even a cookies-file read, not even an import of
    # note_browser_common.
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

    # Sprint 4 (REQ-23/PROP-24): the confirm->click sequence itself is the SHARED unit -- imported here,
    # never reimplemented. This import is deliberately deferred to AFTER gates 1/2 above (env var + CLI
    # arg): note_browser_common itself has no eager cloakbrowser dependency (imported lazily only inside
    # open_editor_ready), but keeping this import late preserves this file's own historical "zero I/O
    # before both gates pass" shape.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from note_browser_common import confirm_and_publish  # noqa: E402

    result = confirm_and_publish(
        note_key,
        price=price,
        cookies_file=cookies_file,
        note_mcp_src=note_mcp_src,
        user_id=user_id,
        username=username,
        work_dir=work_dir,
    )

    if not result["ok"]:
        prefix = result.get("prefix") or "REFUSED"
        print(f"note-publish-live: {prefix} for draft {note_key!r} -- {result['reason']}", file=sys.stderr)
        return 1

    print(f"NOTE_LIVE_URL: {result['url']}")
    print(f"NOTE_LIVE_SCREENSHOT: {result['screenshot']}")
    print(f"NOTE_LIVE_CLICKED: {result['clicked_label']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
