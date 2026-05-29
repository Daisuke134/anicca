#!/usr/bin/env python3
"""Mail triage second-pass — HARD RULE #6 compliant.

NO external LLM call. Rule-based classification for known patterns.
Heartbeat owns LLM judgment for unknown/complex cases.
"""
from __future__ import annotations
import json, re, sys

SAFE_FALLBACK = "notify"

SBIVC_KYC_RE = re.compile(
    r"(SBI\s*VC|sbivc\.co\.jp|出庫予約|トラベルルール|受取人情報|追加確認.*SBI|SBI.*追加確認)",
    re.IGNORECASE,
)
BOOKING_RE = re.compile(
    r"(湘南美容|SHBC|shonan.*biyou|ヒゲ脱毛|脱毛.*予約|予約.*脱毛)",
    re.IGNORECASE,
)
UBER_LICENSE_RE = re.compile(
    r"(uber.*license.*invalid|license.*format.*invalid|ERROR-\d+X-license|format-invalid)",
    re.IGNORECASE,
)


def llm_triage(thread: dict) -> tuple[str, str]:
    subject = thread.get("subject") or ""
    body = thread.get("body") or ""

    # SBI VC KYC question → reply with profile data
    if SBIVC_KYC_RE.search(subject) or SBIVC_KYC_RE.search(body[:1000]):
        return ("email", "SBI VC KYC query: profile reply required")

    # Booking request (湘南美容 etc) → invoke skill + reply
    if BOOKING_RE.search(subject):
        return ("email", "booking request detected: shonan-bishu-book skill")

    # Uber license format error → Round 3 codex escalation
    if UBER_LICENSE_RE.search(subject) or UBER_LICENSE_RE.search(body[:1000]):
        return ("email", "Uber license format-invalid: codex Round 3 escalation")

    return SAFE_FALLBACK, "HARD RULE #6: no external LLM call — heartbeat owns judgment"


if __name__ == "__main__":
    thread = json.load(sys.stdin)
    triage, reason = llm_triage(thread)
    print(json.dumps({"triage": triage, "reason": reason}, ensure_ascii=False))
