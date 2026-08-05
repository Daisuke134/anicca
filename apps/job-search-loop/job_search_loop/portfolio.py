from __future__ import annotations

import re


PORTFOLIO_LIMITS = {"dream": 2, "strong_fit": 5, "adjacent": 3}
DREAM_SCORE_MIN = 95
DREAM_COMPENSATION_MIN_JPY = 20_000_000
ADJACENT_ROLE_FAMILIES = frozenset(
    {
        "ai_product_management",
        "technical_program_management",
        "ai_business_development",
        "ai_partnerships",
        "technical_account_management",
        "ai_customer_success",
        "ai_sales_engineering",
    }
)


def _role_key(value: str) -> str:
    return re.sub(r"[\s-]+", "_", value.strip().casefold())


def classify_portfolio(
    *,
    score: int,
    compensation_min_jpy: int | None,
    role_family: str,
) -> str:
    if isinstance(score, bool) or not isinstance(score, int) or score < 75 or score > 100:
        raise ValueError("eligible score must be an integer from 75 to 100")
    if compensation_min_jpy is not None and (
        isinstance(compensation_min_jpy, bool)
        or not isinstance(compensation_min_jpy, int)
        or compensation_min_jpy < 0
    ):
        raise ValueError("compensation_min_jpy must be a non-negative integer or null")
    role_key = _role_key(role_family)
    if not role_key:
        raise ValueError("role_family is required")
    if score >= DREAM_SCORE_MIN or (
        compensation_min_jpy is not None
        and compensation_min_jpy >= DREAM_COMPENSATION_MIN_JPY
    ):
        return "dream"
    if role_key in ADJACENT_ROLE_FAMILIES:
        return "adjacent"
    return "strong_fit"
