"""Posting guardrails for X/TikTok agents (B2).

Keep logic deterministic and testable.
"""

from __future__ import annotations

from dataclasses import dataclass


MAX_CHARS_X = 260

RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}

BACKOFF_SECONDS = [60, 300, 1800]


@dataclass(frozen=True)
class ClassifiedError:
    category: str  # AUTH, PERMISSION, RATE_LIMIT, VALIDATION, PROVIDER_OUTAGE, UNKNOWN
    retryable: bool


def truncate_x_text(text: str, max_chars: int = MAX_CHARS_X) -> str:
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    # Conservative truncate with ellipsis.
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3] + "..."


def classify_http_status(status_code: int | None) -> ClassifiedError:
    if status_code is None:
        return ClassifiedError(category="UNKNOWN", retryable=True)

    if status_code in (401,):
        return ClassifiedError(category="AUTH", retryable=False)
    if status_code in (403,):
        return ClassifiedError(category="PERMISSION", retryable=False)
    if status_code in (400, 404, 422):
        return ClassifiedError(category="VALIDATION", retryable=False)
    if status_code == 429:
        return ClassifiedError(category="RATE_LIMIT", retryable=True)
    if 500 <= status_code <= 599:
        return ClassifiedError(category="PROVIDER_OUTAGE", retryable=True)

    return ClassifiedError(category="UNKNOWN", retryable=True)


def should_retry(status_code: int | None, attempt_index: int) -> bool:
    if attempt_index < 0:
        return False
    if attempt_index >= len(BACKOFF_SECONDS):
        return False

    classified = classify_http_status(status_code)
    return classified.retryable and (status_code in RETRYABLE_HTTP_STATUS or classified.category == "UNKNOWN")


def backoff_seconds(attempt_index: int) -> int:
    if attempt_index < 0:
        return 0
    if attempt_index >= len(BACKOFF_SECONDS):
        return BACKOFF_SECONDS[-1]
    return BACKOFF_SECONDS[attempt_index]
