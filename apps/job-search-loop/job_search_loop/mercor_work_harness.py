from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class WorkHarnessError(ValueError):
    pass


TRANSITIONS = {
    "submitted_pending_review": {"selected", "rejected"},
    "selected": {"contracted", "rejected", "needs_human"},
    "contracted": {"authorized_work", "needs_human"},
    "authorized_work": {"work_submitted", "needs_human"},
    "work_submitted": {"accepted", "needs_human"},
    "accepted": {"paid_settled"},
    "paid_settled": {"revenue_recorded"},
    "needs_human": {"selected", "contracted", "authorized_work"},
}
SETTLED_STATUSES = frozenset({"paid", "settled", "completed"})


def _amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise WorkHarnessError("amount_usd must be a decimal") from error
    if not amount.is_finite() or amount <= 0:
        raise WorkHarnessError("amount_usd must be positive")
    return amount


def advance_state(
    current_state: str,
    next_state: str,
    *,
    evidence_ref: str,
    payment_id: str | None = None,
    settlement_status: str | None = None,
    amount_usd: Any = None,
    reason: str | None = None,
    authorization_policy: str | None = None,
    acceptance_status: str | None = None,
) -> tuple[str, dict[str, Any]]:
    if next_state not in TRANSITIONS.get(current_state, set()):
        raise WorkHarnessError(f"invalid work transition: {current_state} -> {next_state}")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise WorkHarnessError("evidence_ref is required")
    if next_state == "needs_human" and (not isinstance(reason, str) or not reason.strip()):
        raise WorkHarnessError("needs_human requires a reason")
    if next_state == "authorized_work":
        if authorization_policy != "explicitly_allowed":
            raise WorkHarnessError("authorized_work requires explicit AI permission")
    elif authorization_policy is not None:
        raise WorkHarnessError("authorization_policy is allowed only for authorized_work")
    if next_state == "accepted":
        if acceptance_status != "accepted":
            raise WorkHarnessError("accepted requires explicit acceptance evidence")
    elif acceptance_status is not None:
        raise WorkHarnessError("acceptance_status is allowed only for accepted")
    if next_state == "paid_settled":
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise WorkHarnessError("paid_settled requires payment_id")
        if settlement_status not in SETTLED_STATUSES:
            raise WorkHarnessError("paid_settled requires settled payment status")
        normalized_amount = _amount(amount_usd)
    else:
        if amount_usd is not None or payment_id is not None or settlement_status is not None:
            raise WorkHarnessError("payment fields are allowed only for paid_settled")
        normalized_amount = None
    event: dict[str, Any] = {
        "from_state": current_state,
        "state": next_state,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_ref": evidence_ref.strip(),
    }
    if reason:
        event["reason"] = reason.strip()
    if next_state == "authorized_work":
        event["authorization_policy"] = authorization_policy
    if next_state == "accepted":
        event["acceptance_status"] = acceptance_status
    if next_state == "paid_settled":
        event.update(
            {
                "payment_id": payment_id.strip(),
                "settlement_status": settlement_status,
                "amount_usd": normalized_amount,
            }
        )
    return next_state, event


def revenue_record(event: Mapping[str, Any]) -> dict[str, Any]:
    if event.get("state") != "paid_settled":
        raise WorkHarnessError("only paid_settled events can enter revenue")
    if event.get("settlement_status") not in SETTLED_STATUSES:
        raise WorkHarnessError("revenue requires settled payment status")
    payment_id = event.get("payment_id")
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise WorkHarnessError("revenue requires payment_id")
    return {"payment_id": payment_id.strip(), "amount_usd": _amount(event.get("amount_usd"))}
