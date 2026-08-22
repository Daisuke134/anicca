from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from urllib.parse import urlsplit


class EarningsReadbackError(ValueError):
    """The live Mercor earnings read-back is not safe to count."""


SETTLED_STATUSES = frozenset({"paid", "settled", "completed"})


def _decimal(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise EarningsReadbackError(f"{field} must be a decimal amount") from error
    if not amount.is_finite() or amount < 0:
        raise EarningsReadbackError(f"{field} must be a finite non-negative amount")
    return amount.quantize(Decimal("0.01"))


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise EarningsReadbackError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise EarningsReadbackError(f"{field} must be an ISO date") from error


def _observed_at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise EarningsReadbackError("observed_at must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EarningsReadbackError("observed_at must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise EarningsReadbackError("observed_at must include a timezone")
    return parsed


def build_earnings_result(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Count only Mercor rows whose live status proves a settled payment."""
    if snapshot.get("provider") != "mercor":
        raise EarningsReadbackError("provider must be mercor")
    page_url = snapshot.get("page_url")
    parsed_url = urlsplit(page_url) if isinstance(page_url, str) else None
    if not parsed_url or parsed_url.scheme != "https" or parsed_url.netloc != "work.mercor.com":
        raise EarningsReadbackError("page_url must be the Mercor earnings page")
    if parsed_url.path.rstrip("/") != "/earnings":
        raise EarningsReadbackError("page_url must be the Mercor earnings page")
    observed_at = _observed_at(snapshot.get("observed_at"))
    history_status = snapshot.get("payment_history_status")
    if history_status not in {"empty", "has_rows"}:
        raise EarningsReadbackError("payment_history_status must be empty or has_rows")
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise EarningsReadbackError("rows must be an array")
    if history_status == "empty" and rows:
        raise EarningsReadbackError("empty payment history cannot contain rows")
    if history_status == "has_rows" and not rows:
        raise EarningsReadbackError("has_rows payment history must contain rows")

    settled_rows: list[dict[str, Any]] = []
    observed_day = observed_at.date()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise EarningsReadbackError(f"rows[{index}] must be an object")
        payment_id = row.get("payment_id")
        status = row.get("status")
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise EarningsReadbackError(f"rows[{index}].payment_id is required")
        if not isinstance(status, str) or not status.strip():
            raise EarningsReadbackError(f"rows[{index}].status is required")
        amount = _decimal(row.get("earned_usd"), f"rows[{index}].earned_usd")
        payout_date = _date(row.get("payout_date"), f"rows[{index}].payout_date")
        if status.casefold().strip() in SETTLED_STATUSES:
            if amount <= 0:
                raise EarningsReadbackError(f"rows[{index}] settled amount must be positive")
            normalized_row = {
                    "payment_id": payment_id.strip(),
                    "status": status.casefold().strip(),
                    "earned_usd": amount,
                    "payout_date": payout_date.isoformat(),
                }
            if row.get("work_id") is not None:
                if not isinstance(row.get("work_id"), str) or not row["work_id"].strip():
                    raise EarningsReadbackError(f"rows[{index}].work_id must be a non-empty string")
                normalized_row["work_id"] = row["work_id"].strip()
            settled_rows.append(normalized_row)

    settled_total = sum((row["earned_usd"] for row in settled_rows), Decimal("0.00"))
    window_start = observed_day - timedelta(days=29)
    monthly_total = sum(
        (
            row["earned_usd"]
            for row in settled_rows
            if window_start <= date.fromisoformat(row["payout_date"]) <= observed_day
        ),
        Decimal("0.00"),
    )
    return {
        "provider": "mercor",
        "page_url": page_url,
        "observed_at": observed_at.isoformat(),
        "status": "settled" if settled_rows else "not_observed",
        "settled_rows": settled_rows,
        "settled_total_usd": settled_total,
        "verified_monthly_run_rate_usd": monthly_total if settled_rows else None,
        "revenue_credited": bool(settled_rows),
    }
