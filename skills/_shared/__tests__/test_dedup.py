"""PROP-F2-dedup (required:true, Tier 1) — escalation dedup, anti-Telegram-spam.

Spec: REQ-F1 step 1 (dedup_key sha256 with normalize_evidence) + step 2 (24h-window scan).
Closes FIND-007 critical (was undefined evidence_hash in v1).
"""
import pytest

from lib.escalate import dedup_key, is_duplicate, normalize_evidence  # FAIL until 2b


# ── normalize strips rotating identifiers ────────────────────────────
def test_normalize_strips_unix_timestamps():
    a = normalize_evidence("error at ts:1782830000 in round-3")
    b = normalize_evidence("error at ts:1782999999 in round-3")
    assert a == b


def test_normalize_strips_round_numbers():
    a = normalize_evidence("round-3 failed")
    b = normalize_evidence("round-5 failed")
    assert a == b


def test_normalize_strips_bare_unix_timestamps_in_text():
    a = normalize_evidence("backoff at 1782830000")
    b = normalize_evidence("backoff at 1782831234")
    assert a == b


# ── same underlying failure → same dedup_key ─────────────────────────
def test_two_escalations_for_same_failure_collapse_to_same_key():
    """The EXACT FIND-007 critical: REQ-A8 backoff fires twice with rotating
    timestamps in evidence; dedup MUST collapse them, not spam Telegram."""
    a = dedup_key("gig", "backoff-cap", "last 5 audit verdicts at 1782830000 ts:1782830001 round-3")
    b = dedup_key("gig", "backoff-cap", "last 5 audit verdicts at 1782900000 ts:1782900001 round-5")
    assert a == b


def test_different_slot_yields_different_key():
    a = dedup_key("gig", "backoff-cap", "same evidence")
    b = dedup_key("clip", "backoff-cap", "same evidence")
    assert a != b


def test_different_reason_yields_different_key():
    a = dedup_key("gig", "backoff-cap", "same evidence")
    b = dedup_key("gig", "needs-login", "same evidence")
    assert a != b


# ── is_duplicate honors 24h window ───────────────────────────────────
def test_is_duplicate_within_24h_returns_true():
    now = 1782900000
    log = [{"dedup_key": "abc", "ts": now - 3600}]  # 1h ago
    assert is_duplicate("abc", log, now) is True


def test_is_duplicate_outside_24h_returns_false():
    now = 1782900000
    log = [{"dedup_key": "abc", "ts": now - 86400 - 1}]  # 24h+1s ago
    assert is_duplicate("abc", log, now) is False


def test_is_duplicate_no_match_returns_false():
    now = 1782900000
    log = [{"dedup_key": "xyz", "ts": now - 100}]
    assert is_duplicate("abc", log, now) is False


def test_is_duplicate_empty_log_returns_false():
    assert is_duplicate("abc", [], 1782900000) is False
