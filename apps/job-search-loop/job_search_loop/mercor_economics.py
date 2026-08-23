from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


WEEKS_PER_MONTH = Decimal("52") / Decimal("12")


def _positive(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{field} must be numeric") from error
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{field} must be positive")
    return amount


def monthly_gross_projection(
    rate_min_usd: Any,
    rate_max_usd: Any,
    weekly_hours: int,
    accepted_application_count: int,
) -> dict[str, Any]:
    rate_min = _positive(rate_min_usd, "rate_min_usd")
    rate_max = _positive(rate_max_usd, "rate_max_usd")
    if rate_max < rate_min:
        raise ValueError("rate_max_usd must be >= rate_min_usd")
    if isinstance(weekly_hours, bool) or not isinstance(weekly_hours, int) or not 1 <= weekly_hours <= 80:
        raise ValueError("weekly_hours must be between 1 and 80")
    if isinstance(accepted_application_count, bool) or not isinstance(accepted_application_count, int) or accepted_application_count < 0:
        raise ValueError("accepted_application_count must be a non-negative integer")
    raw_monthly_hours = Decimal(weekly_hours) * WEEKS_PER_MONTH
    monthly_hours = raw_monthly_hours.quantize(Decimal("0.01"))
    capped_min = (raw_monthly_hours * rate_min).quantize(Decimal("0.01"))
    capped_max = (raw_monthly_hours * rate_max).quantize(Decimal("0.01"))
    naive_min = (raw_monthly_hours * rate_min * accepted_application_count).quantize(Decimal("0.01"))
    naive_max = (raw_monthly_hours * rate_max * accepted_application_count).quantize(Decimal("0.01"))
    return {
        "accepted_application_count": accepted_application_count,
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "gross_min_usd": capped_min,
        "gross_max_usd": capped_max,
        "capacity_capped": True,
        "naive_three_full_time_min_usd": naive_min,
        "naive_three_full_time_max_usd": naive_max,
        "revenue_status": "projection_only",
    }
