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
    "paid_settled": {"bank_matched"},
    "bank_matched": {"revenue_recorded"},
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
    payout_id: str | None = None,
    bank_transaction_id: str | None = None,
    match_status: str | None = None,
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
    elif next_state == "bank_matched":
        identities = (payment_id, payout_id, bank_transaction_id)
        if not all(isinstance(value, str) and value.strip() for value in identities):
            raise WorkHarnessError("bank_matched requires payment, payout, and bank transaction IDs")
        if match_status != "matched":
            raise WorkHarnessError("bank_matched requires matched status")
        normalized_amount = _amount(amount_usd)
    else:
        if any(value is not None for value in (amount_usd, payment_id, settlement_status, payout_id, bank_transaction_id, match_status)):
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
    elif next_state == "bank_matched":
        event.update(
            {
                "payment_id": payment_id.strip(),
                "payout_id": payout_id.strip(),
                "bank_transaction_id": bank_transaction_id.strip(),
                "match_status": match_status,
                "amount_usd": normalized_amount,
            }
        )
    return next_state, event


def revenue_record(event: Mapping[str, Any]) -> dict[str, Any]:
    if event.get("state") != "bank_matched" or event.get("match_status") != "matched":
        raise WorkHarnessError("revenue requires matched bank evidence")
    identities = {
        key: event.get(key)
        for key in ("payment_id", "payout_id", "bank_transaction_id")
    }
    if not all(isinstance(value, str) and value.strip() for value in identities.values()):
        raise WorkHarnessError("revenue requires payment, payout, and bank transaction IDs")
    return {
        **{key: value.strip() for key, value in identities.items()},
        "amount_usd": _amount(event.get("amount_usd")),
    }
