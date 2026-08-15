#!/usr/bin/env python3
"""The last check a follow-up passes, run against the live thread.

Selection cannot decide this. The inbox snapshot carries no message text, so
``followup_candidates`` shortlists on silence alone -- a buyer who wrote 「他の方探して下さい。」
looks exactly like one who is still deciding. The difference is only visible once the
browser opens the thread, which is here, one step before the body is typed.

Two refusals, in this order:

``stopped``   the buyer said no. Nothing we could write is appropriate, so the draft is
              never even requested. Checked first because it is the only refusal that is
              about the person rather than the words.
``violations`` the draft breaks a platform rule (external contact, off-platform payment,
              a deliverable promised before purchase). Checked by ``followup_draft``.

Silence is also re-checked here. The shortlist may have been built from ``buyer_sent_at``,
which sits earlier than our reply and therefore over-states how long a buyer has been
quiet; the thread the browser just read knows better.

Returns a decision rather than raising. A refusal is a normal outcome that the pass has to
report -- a thread that vanishes without a reason is indistinguishable from a bug.
"""
from __future__ import annotations

from typing import Any

import os
import sys

# Loaded dynamically by reply_lane, which uses spec_from_file_location and does not
# put this directory on the path. Importing a sibling then fails with
# ModuleNotFoundError -- measured, not guessed. Running as a script happens to work
# because sys.path[0] is already here, and depending on that is depending on how the
# caller was launched.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import followup_draft
import stop_signal

# Same floor as followup_candidates.MIN_SILENT_DAYS; imported rather than restated so the
# two gates cannot drift apart.
from followup_candidates import MIN_SILENT_DAYS


def decide(
    *,
    conversation: Any,
    body: Any,
    silent_days: Any = None,
) -> dict[str, Any]:
    """Whether this follow-up may be sent, and why not when it may not."""
    stopped = stop_signal.stopped_by(conversation)
    if stopped:
        return {
            "ok": False,
            "reason": "stopped:" + stopped["reason"],
            "evidence": stopped["text"],
        }
    if isinstance(silent_days, (int, float)) and silent_days < MIN_SILENT_DAYS:
        return {
            "ok": False,
            "reason": "too_soon",
            "evidence": f"silent_days={float(silent_days):.2f}",
        }
    check = followup_draft.check_draft(body)
    if not check.get("ok"):
        violations = check.get("violations") or []
        return {
            "ok": False,
            "reason": "draft_violation",
            "violations": violations,
            "evidence": ",".join(str(item) for item in violations),
        }
    return {"ok": True, "reason": None}
