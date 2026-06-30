"""escalate — dedup + normalize for the only human gate.

PROP-F2-dedup (required:true, Tier 1) — REQ-F1 step 1 (dedup_key sha256 with
normalize_evidence) + step 2 (24h-window scan).
Closes FIND-007 critical (was undefined evidence_hash in v1).
"""
from __future__ import annotations

import hashlib
import re


# Spec REQ-F1: normalize strips substrings that rotate but mean the same failure.
_TS_BARE_RE = re.compile(r"\b\d{10}\b")           # bare unix timestamp (10-digit)
_TS_TAGGED_RE = re.compile(r"\bts:\d+\b")         # tagged unix timestamp
_ROUND_RE = re.compile(r"\bround-\d+\b")          # round-N rotation


_DEDUP_WINDOW_SECONDS = 86400


def normalize_evidence(evidence: str) -> str:
    """Strip rotating identifiers so the same underlying failure collapses to
    the same dedup key (REQ-F1 step 1).
    """
    s = evidence
    s = _TS_TAGGED_RE.sub("", s)
    s = _TS_BARE_RE.sub("", s)
    s = _ROUND_RE.sub("", s)
    return s


def dedup_key(slot: str, reason: str, evidence: str) -> str:
    """sha256(slot || \\x00 || reason || \\x00 || normalize_evidence(evidence))."""
    normalized = normalize_evidence(evidence)
    h = hashlib.sha256()
    h.update(slot.encode("utf-8"))
    h.update(b"\x00")
    h.update(reason.encode("utf-8"))
    h.update(b"\x00")
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def is_duplicate(key: str, log_rows: list[dict], now_ts: int) -> bool:
    """Return True iff any row in log_rows has dedup_key == key AND
    ts > (now_ts − 24h). REQ-F1 step 2 / REQ-F2.
    """
    lo = now_ts - _DEDUP_WINDOW_SECONDS
    for row in log_rows:
        if row.get("dedup_key") == key and int(row.get("ts", 0)) > lo:
            return True
    return False
