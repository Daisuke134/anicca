from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from ..ats import detect_provider
from ..state import canonical_url
from .contracts import QueueRowReceiptV1


RowProcessor = Callable[[dict[str, Any]], Awaitable[str]]
_STATUSES = frozenset(
    {
        "checkpointed",
        "ineligible",
        "post_submit_verification",
        "not_submitted",
        "submit_unknown",
        "submitted",
    }
)
_NEVER_REAPPLY = frozenset(
    {
        canonical_url(
            "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site/"
            "job/Japan---Tokyo/Forward-Deployed-Engineer--Multiple-Levels-_JR355047"
        )
    }
)


class RowQueueSupervisor:
    """Run every unique queued row; one row failure never ends the wake."""

    @staticmethod
    def collect(
        ledger: Any, active_provider: str | None = None
    ) -> tuple[dict[str, Any], ...]:
        provider = active_provider or os.environ.get(
            "JOB_SEARCH_ACTIVE_APPLICATION_PROVIDER"
        )
        ordered: Iterable[dict[str, Any]] = (
            *ledger.pending_materials_ready_applications(),
            *ledger.retryable_applications(),
        )
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for row in ordered:
            identity = canonical_url(str(row["canonical_url"]))
            if provider and detect_provider(identity) != provider:
                continue
            if identity in _NEVER_REAPPLY:
                continue
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(row)
        return tuple(rows)

    async def run(
        self, rows: Iterable[dict[str, Any]], processor: RowProcessor
    ) -> tuple[QueueRowReceiptV1, ...]:
        receipts: list[QueueRowReceiptV1] = []
        for row in rows:
            try:
                status = await processor(row)
                if status not in _STATUSES:
                    raise ValueError("row processor returned an invalid status")
                error_type = None
            except Exception as error:  # row isolation is the purpose of this boundary
                status = "checkpointed"
                error_type = type(error).__name__
            receipts.append(
                QueueRowReceiptV1(
                    application_id=str(row["application_id"]),
                    company=str(row["company"]),
                    role=str(row["title"]),
                    status=status,
                    error_type=error_type,
                )
            )
        return tuple(receipts)
