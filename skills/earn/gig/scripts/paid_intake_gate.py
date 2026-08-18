#!/usr/bin/env python3
"""Name the real cause when the paid-work builder reports it is stuck.

C3b done condition (2): a blocked PAID_WORK pass must not be filed as
``paid_work_validation_failed``. That reason describes the deterministic
contract validator, which never ran -- the builder stopped one stage earlier.

The one cause the loop can attribute deterministically is the one measured on
order 90000004: the queue item claims the buyer is waiting on us
(``buyer_feedback_pending_artifact``), but nothing on disk holds what the buyer
actually asked for, so the prompt's "read the packet-bound current
buyer-feedback input" is an impossible instruction. That is
``paid_work_missing_buyer_intake``.

Anything else keeps its own honest name, ``paid_work_builder_blocked``: we know
the builder stopped, we do not know why, and inventing a cause would be the same
false attribution in the other direction.

Deliberately total: never raises, CLI never exits nonzero (it is called from
``gig_pass.sh``; an escaping exception would fail an otherwise healthy lane).
Unparseable input degrades to the non-committal reason, never to a claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MISSING_INTAKE = "paid_work_missing_buyer_intake"
BUILDER_BLOCKED = "paid_work_builder_blocked"


def _requirements_body(path_value: Any) -> str:
    if not isinstance(path_value, str) or not path_value.strip():
        return ""
    try:
        raw = Path(path_value).expanduser().read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""
    try:
        payload = json.loads(raw)
    except ValueError:
        # A non-JSON requirements file is still intake if it has content.
        return raw.strip()
    if isinstance(payload, dict):
        return str(payload.get("feedback_text") or "").strip()
    return str(payload or "").strip()


def intake_verdict(item: Any) -> dict[str, Any]:
    """Return ``{"intake_present": bool, "reason": str}`` for a paid queue item."""
    if not isinstance(item, dict):
        return {"intake_present": True, "reason": BUILDER_BLOCKED}
    # Only an item that claims a pending buyer request promised an intake file.
    # overdue_or_today_paid_deliverable / other_paid_work never did, so calling
    # their blocked an intake failure would be a second false attribution.
    if item.get("buyer_feedback_pending_artifact") is not True:
        return {"intake_present": True, "reason": BUILDER_BLOCKED}
    if _requirements_body(item.get("buyer_feedback_requirements_path")):
        return {"intake_present": True, "reason": BUILDER_BLOCKED}
    return {"intake_present": False, "reason": MISSING_INTAKE}


def main() -> int:
    try:
        item = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001 - see module docstring
        item = None
    try:
        verdict = intake_verdict(item)
    except Exception:  # noqa: BLE001
        verdict = {"intake_present": True, "reason": BUILDER_BLOCKED}
    print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
