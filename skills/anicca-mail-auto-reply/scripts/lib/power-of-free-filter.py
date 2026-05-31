"""FR-014 — Power-Of-Free permanent BAN filter.

Source: profile.lateness.stakeholders[2] note + Dais 2026-05-26 directive.

Power-Of-Free (U&C / live_entry@yahoo.co.jp) は永久 BAN。 reply も archive も
しない — INBOX に残して Dais の手動 audit 対象にする。

Public API:
    is_banned(thread: dict) -> bool

CLI usage (for run.sh wiring):
    echo '{"from":"...","subject":"..."}' | python3 power-of-free-filter.py
    # prints 'BANNED' or 'OK' to stdout
"""
from __future__ import annotations
import json
import re
import sys

BANNED_SENDER_RE = re.compile(r"live_entry@yahoo\.co\.jp", re.IGNORECASE)
BANNED_SUBJECT_RE = re.compile(
    r"パワーオブフリー|U&C\s*ライブ|live_entry",
    re.IGNORECASE,
)


def is_banned(thread: dict) -> bool:
    """True if the thread must NOT be replied to or archived.

    Fail-OPEN on missing fields (returns False) — we only block when we have
    a positive BAN marker, otherwise the caller proceeds to normal triage.
    """
    if not isinstance(thread, dict):
        return False
    sender = thread.get("from") or ""
    subject = thread.get("subject") or ""
    if BANNED_SENDER_RE.search(sender):
        return True
    if BANNED_SUBJECT_RE.search(subject):
        return True
    return False


def _main() -> int:
    try:
        thread = json.loads(sys.stdin.read())
    except Exception:
        # malformed input → fail-OPEN (don't block real mail because of bad JSON)
        print("OK")
        return 0
    print("BANNED" if is_banned(thread) else "OK")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
