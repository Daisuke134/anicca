from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

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


class RowQueueSupervisor:
    """Run every unique queued row; one row failure never ends the wake."""

    @staticmethod
    def collect(ledger: Any) -> tuple[dict[str, Any], ...]:
        ordered: Iterable[dict[str, Any]] = (
            *ledger.pending_materials_ready_applications(),
            *ledger.retryable_applications(),
        )
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for row in ordered:
            identity = canonical_url(str(row["canonical_url"]))
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
