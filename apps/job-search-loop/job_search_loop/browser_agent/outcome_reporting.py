from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ..telegram import send_once
from .contracts import QueueRowReceiptV1


def _line(value: str) -> str:
    return " ".join(value.split())[:240]


def build_hourly_outcome_message(
    receipts: Sequence[QueueRowReceiptV1],
    evidence_classes: Mapping[str, str],
) -> str:
    lines = ["Codex::: Job Hunter hourly outcomes"]
    for receipt in receipts:
        if receipt.status == "submitted":
            evidence_class = evidence_classes.get(receipt.application_id, "")
            if evidence_class not in {"exact_completion_ui", "authoritative_receipt_email"}:
                raise ValueError("submitted Telegram row lacks authoritative evidence")
            label = f"submitted ({evidence_class})"
        elif receipt.status == "checkpointed":
            label = "blocked (recovering; queue continued)"
        elif receipt.status == "submit_unknown":
            label = "not submitted (submit status unknown; no retry)"
        elif receipt.status == "post_submit_verification":
            label = "not submitted (verification pending)"
        elif receipt.status == "ineligible":
            label = "not submitted (ineligible)"
        else:
            label = "not submitted"
        lines.append(f"- {_line(receipt.company)} — {_line(receipt.role)}: {label}")
    return "\n".join(lines)


def send_hourly_outcomes(
    *,
    database: Path,
    wake_id: str,
    receipts: Sequence[QueueRowReceiptV1],
    evidence_classes: Mapping[str, str],
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> dict[str, str | None]:
    message = build_hourly_outcome_message(receipts, evidence_classes)
    digest = hashlib.sha256(message.encode()).hexdigest()[:16]
    result = sender(
        database=database,
        event_key=f"job-search-hourly:{_line(wake_id)}:{digest}",
        message=message,
    )
    if result.get("status") != "sent" or not result.get("message_id"):
        raise RuntimeError("hourly Telegram outcome has no acknowledged message ID")
    return result
