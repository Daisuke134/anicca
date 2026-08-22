from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from .ledger import Ledger
from .browser_agent.contracts import QueueRowReceiptV1
from .browser_agent.outcome_reporting import build_hourly_outcome_message
from .telegram import send_document_once, send_once


def deliver_reconciled_outcomes(
    *,
    ledger_path: Path,
    outbox_path: Path,
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> list[dict[str, str | None]]:
    ledger = Ledger(ledger_path)
    try:
        rows = ledger.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              submission_confirmations.message_id
            FROM submission_confirmations
            JOIN submit_intents
              ON submit_intents.intent_id = submission_confirmations.intent_id
            JOIN applications
              ON applications.id = submit_intents.application_id
            WHERE applications.current_state = 'submitted'
            ORDER BY submission_confirmations.received_at,
                     submission_confirmations.message_id
            """
        ).fetchall()
    finally:
        ledger.close()

    deliveries = []
    for row in rows:
        application_id = str(row["application_id"])
        message_id = str(row["message_id"])
        message = build_hourly_outcome_message(
            (
                QueueRowReceiptV1(
                    application_id,
                    str(row["company"]),
                    str(row["title"]),
                    "submitted",
                ),
            ),
            {application_id: "authoritative_receipt_email"},
        )
        delivery = sender(
            database=outbox_path,
            event_key=f"application-submitted:{application_id}:{message_id}",
            message=message,
        )
        deliveries.append(
            {
                "application_id": application_id,
                "receipt_message_id": message_id,
                "status": delivery["status"],
                "message_id": delivery["message_id"],
            }
        )
    return deliveries


def deliver_submitted_resumes(
    *,
    ledger_path: Path,
    outbox_path: Path,
    media_root: Path,
    sender: Callable[..., dict[str, str | None]] = send_document_once,
) -> list[dict[str, str | None]]:
    ledger = Ledger(ledger_path)
    try:
        reports = ledger.submitted_resume_reports()
    finally:
        ledger.close()

    deliveries = []
    for report in reports:
        message = (
            "📎 Resume used for submitted application\n"
            f"{report['company']} — {report['title']}\n"
            f"{report['canonical_url']}"
        )
        delivery = sender(
            database=outbox_path,
            event_key=(
                f"application-resume:{report['application_id']}:"
                f"{report['resume_sha256']}"
            ),
            message=message,
            document=Path(report["resume_path"]),
            media_root=media_root,
        )
        deliveries.append(
            {
                "application_id": report["application_id"],
                "status": delivery["status"],
                "message_id": delivery["message_id"],
            }
        )
    return deliveries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("deliver",))
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    deliveries = deliver_submitted_resumes(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
        media_root=args.media_root,
    )
    outcomes = deliver_reconciled_outcomes(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(
            {"deliveries": deliveries, "outcomes": outcomes},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)


if __name__ == "__main__":
    main()
