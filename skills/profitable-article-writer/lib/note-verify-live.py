#!/usr/bin/env python3
"""lib/note-verify-live.py -- REQ-22/PROP-23 (Sprint 2.5): INDEPENDENT post-publish verification of a live
note.com URL.

This is a SEPARATE process/invocation from lib/note-publish-live.py: it never imports, calls, or is called
by that file, and it never reads NOTE_COOKIES_FILE or any cookie at all -- a purely LOGGED-OUT HTTP fetch
(standard-library urllib only, no requests/cloakbrowser dependency). REQ-22 requires that the publish
tool's own stdout claim is not the thing that verifies a real publish happened; this file is the
independent second opinion.

Checks BOTH:
  1. HTTP status == 200 for the public URL.
  2. The response body contains the article's note KEY and/or its TITLE -- guards against an SPA shell
     returning a bare 200 for a URL that does not actually resolve to this specific article (REQ-22's
     explicit "not just any 200" requirement).

Also RECORDS the result to state (REQ-22: "The live URL + timestamp + this independent verification's
result SHALL be recorded to state for V4 (earn) tracking to begin against it") -- one JSON line appended to
NOTE_LIVE_STATE_FILE (default: <this skill>/state/live-publishes.jsonl). Recording is best-effort: a
failure to write state does NOT change this tool's own PASS/FAIL exit code (the verification result
itself is the source of truth; state recording is a side effect of it, not a precondition).

INTERFACE:
  argv: <note_key> [expected_title_substring]
    note_key alone: URL defaults to https://note.com/<NOTE_USERNAME>/n/<note_key>
                    (NOTE_USERNAME env, default "anicca123" -- same convention as the other lib/ scripts)
    expected_title_substring: optional; if given, ALSO checked as a substring of the page body (REQ-22
                    only requires "title OR note ID"; supplying a title lets both be checked)
  env in:
    NOTE_USERNAME          default "anicca123"
    NOTE_LIVE_STATE_FILE   default: <this skill>/state/live-publishes.jsonl
  stdout: one JSON line: {"key":..., "url":..., "http_status":..., "key_in_body": bool,
                          "title_in_body": bool|null, "PASS": bool, "ts": <unix ts>}
  exit: 0 if PASS (http_status==200 AND (key_in_body OR title_in_body)); 1 otherwise. Never raises
  uncaught -- a network error is reported as http_status: null, PASS: false, never a Python traceback.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_STATE_FILE = os.path.join(_SKILL_DIR, "state", "live-publishes.jsonl")


def verify_live(note_key: str, expected_title: str | None = None, username: str | None = None) -> dict:
    """Logged-out fetch of https://note.com/<username>/n/<note_key> -- NO cookies, NO auth headers, so a
    reader with zero note.com session state gets the exact same result this function computes."""
    username = username or os.environ.get("NOTE_USERNAME", "anicca123")
    url = f"https://note.com/{username}/n/{note_key}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    status = None
    body = ""
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
    except Exception:
        status = None
        body = ""

    key_in_body = note_key in body
    title_in_body = (expected_title in body) if expected_title else None
    content_confirmed = key_in_body or bool(title_in_body)
    passed = (status == 200) and content_confirmed

    return {
        "ts": int(time.time()),
        "key": note_key,
        "url": url,
        "http_status": status,
        "key_in_body": key_in_body,
        "title_in_body": title_in_body,
        "PASS": passed,
    }


def _record_to_state(result: dict, state_file: str) -> None:
    """Best-effort append of `result` as one JSON line to `state_file` (REQ-22's state-recording
    requirement). Never raises -- a state-write failure must not flip this tool's own exit code."""
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"note-verify-live: state recording to {state_file!r} failed (non-fatal): {e}", file=sys.stderr)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: note-verify-live.py <note_key> [expected_title_substring]", file=sys.stderr)
        return 2
    note_key = sys.argv[1]
    expected_title = sys.argv[2] if len(sys.argv) > 2 else None

    result = verify_live(note_key, expected_title)
    print(json.dumps(result, ensure_ascii=False))

    state_file = os.environ.get("NOTE_LIVE_STATE_FILE", _DEFAULT_STATE_FILE)
    _record_to_state(result, state_file)

    return 0 if result["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
