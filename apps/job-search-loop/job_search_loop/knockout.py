from __future__ import annotations

import re
from typing import Any, Iterable


JPY_FLOOR = 8_000_000
JPY_AMOUNT_RE = re.compile(
    r"(?:\bJPY\b|¥)\s*([0-9][0-9,]*(?:\.[0-9]+)?)|"
    r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:\bJPY\b|円)",
    re.IGNORECASE,
)
RELEVANT_TITLE_RE = re.compile(
    r"\b(?:AI|GenAI|LLM|machine learning|deployment|forward deployed|"
    r"solutions?|field engineer|product|technical program|partnerships?|"
    r"account (?:director|executive)|architect)\b|生成AI|機械学習",
    re.IGNORECASE,
)
JAPAN_RE = re.compile(r"\b(?:japan|tokyo)\b|日本|東京", re.IGNORECASE)


def _source_span(url: str, field: str, value: Any, limit: int = 500) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    compact = " ".join(value.split())[:limit]
    return f"{url}#{field}={compact}"


def _jpy_amounts(text: Any) -> list[int]:
    if not isinstance(text, str):
        return []
    values = []
    for match in JPY_AMOUNT_RE.finditer(text):
        raw = match.group(1) or match.group(2)
        try:
            values.append(int(float(raw.replace(",", ""))))
        except ValueError:
            continue
    return values


def assess_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    url = str(candidate.get("official_url") or candidate.get("url") or "").strip()
    title = str(candidate.get("title") or "").strip()
    location = str(candidate.get("location") or "").strip()
    description = candidate.get("description")
    reasons: list[str] = []
    amounts = _jpy_amounts(description)
    if amounts and max(amounts) < JPY_FLOOR:
        status = "rejected"
        reasons.append("compensation_max_below_jpy_8000000")
    elif RELEVANT_TITLE_RE.search(title):
        status = "pass"
        reasons.append("title_relevance_explicit")
    else:
        status = "needs_verification"
        reasons.append("title_relevance_needs_verification")
    spans = [
        span
        for span in (
            _source_span(url, "title", title),
            _source_span(url, "location", location),
            _source_span(url, "description", description),
        )
        if span is not None
    ]
    return {
        "gate_status": status,
        "gate_reasons": reasons,
        "source_spans": spans,
    }


def _score(candidate: dict[str, Any]) -> tuple[int, str]:
    score = 0
    if candidate.get("gate_status") == "pass":
        score += 100
    location = str(candidate.get("location") or "")
    if JAPAN_RE.search(location):
        score += 50
    if candidate.get("ai_requirement_evidence"):
        score += 10
    bucket = str(candidate.get("bucket") or "")
    score += {"dream": 6, "strong_fit": 4, "adjacent": 2}.get(bucket, 0)
    return score, str(candidate.get("official_url") or "")


def shortlist_candidates(
    candidates: Iterable[dict[str, Any]], *, limit: int = 12
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("shortlist limit must be positive")
    assessed = [
        row
        if row.get("gate_status") in {"pass", "needs_verification", "rejected"}
        else {**row, **assess_candidate(row)}
        for row in candidates
    ]
    eligible = [row for row in assessed if row.get("gate_status") != "rejected"]
    eligible.sort(key=_score, reverse=True)
    return eligible[:limit]
