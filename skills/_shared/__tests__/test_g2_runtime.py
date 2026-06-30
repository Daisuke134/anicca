"""PROP-G2-runtime (required:true, Tier 1 integration) — INV-13 active half, 3-check pattern.

Spec: REQ-G2 step (b) — endpoint allowlist + hash-fidelity + field-equality.
Closes FIND-015 + ROUND-2-001 critical + ROUND-3-003 (off-by-0.005 epsilon).
"""
import hashlib
import pytest

from lib.events import verify_earn_event  # FAIL until 2b


# Fixture allowlist
ALLOWLIST = {
    "coconala": {
        "endpoints": [
            {
                "endpoint": "/api/v1/sales/{receipt_id}",
                "method": "GET",
                "response_format": "json",
                "receipt_id_path": "$.sale.id",
                "amount_path": "$.sale.amount",
                "payer_path": "$.sale.buyer.id",
                "unit": "jpy_int",
                "comparison": "exact",
            }
        ]
    },
    "whop": {
        "endpoints": [
            {
                "endpoint": "/api/v2/payouts/{receipt_id}",
                "method": "GET",
                "response_format": "json",
                "receipt_id_path": "$.payout.id",
                "amount_path": "$.payout.amount_usdc",
                "payer_path": "$.payout.from",
                "unit": "usdc_float_6dp",
                "comparison": "epsilon:0.01",
            }
        ]
    },
}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ── (i) ROUND-2-001 attack: plausible-endpoint + forged receipt ──────
def test_benign_endpoint_with_forged_receipt_rejected_at_allowlist():
    """The exact ROUND-2-001 attack: skill emits a forged receipt paired with
    the real hash of `GET /v1/me`. Must reject at step 1 (allowlist)."""
    benign_body = '{"user": {"id": "user-123", "email": "anicca@example.com"}}'
    event = {
        "event": "earn",
        "slot": "gig",
        "receipt_id": "FAKE-RECEIPT-123",
        "amount_jpy": 100000,
        "payer": "fake-buyer",
        "platform": "coconala",
        "platform_api_call": {
            "endpoint": "/v1/me",  # NOT in allowlist for coconala
            "response_sha256": _hash(benign_body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: benign_body)
    assert result.ok is False
    assert result.failed_check == "endpoint-not-allowlisted"


# ── (ii) allowlisted endpoint + real hash + forged receipt_id ────────
def test_allowlisted_endpoint_with_forged_receipt_id_rejected_at_field_equality():
    """The skill picks an allowlisted endpoint AND emits a real response_sha256
    from a past real settlement, but with a forged receipt_id in the event row.
    Must reject at step 3 (field-equality)."""
    real_body = '{"sale": {"id": "REAL-12345", "amount": 50000, "buyer": {"id": "buyer-A"}}}'
    event = {
        "event": "earn",
        "slot": "gig",
        "receipt_id": "FAKE-99999",  # ≠ REAL-12345 in body
        "amount_jpy": 50000,
        "payer": "buyer-A",
        "platform": "coconala",
        "platform_api_call": {
            "endpoint": "/api/v1/sales/REAL-12345",
            "response_sha256": _hash(real_body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: real_body)
    assert result.ok is False
    assert result.failed_check.startswith("field-mismatch:receipt_id")


# ── (iii) happy path Coconala JPY (exact) ────────────────────────────
def test_happy_path_coconala_jpy_exact_accepts():
    body = '{"sale": {"id": "CN-2026-12345", "amount": 40000, "buyer": {"id": "yamamoto"}}}'
    event = {
        "event": "earn",
        "slot": "gig",
        "receipt_id": "CN-2026-12345",
        "amount_jpy": 40000,
        "payer": "yamamoto",
        "platform": "coconala",
        "platform_api_call": {
            "endpoint": "/api/v1/sales/CN-2026-12345",
            "response_sha256": _hash(body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: body)
    assert result.ok is True


# ── (iv) happy path Whop USDC float (epsilon:0.01) ───────────────────
def test_happy_path_whop_usdc_within_epsilon_accepts():
    body = '{"payout": {"id": "WH-99", "amount_usdc": 12.504, "from": "whop"}}'
    event = {
        "event": "earn",
        "slot": "clip",
        "receipt_id": "WH-99",
        "amount_usdc": 12.50,  # within 0.01 of 12.504
        "payer": "whop",
        "platform": "whop",
        "platform_api_call": {
            "endpoint": "/api/v2/payouts/WH-99",
            "response_sha256": _hash(body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: body)
    assert result.ok is True


# ── (v) ROUND-3-003 off-by-0.005 attack: outside epsilon → reject ────
def test_whop_usdc_off_by_more_than_epsilon_rejected():
    """If event claims 1.000 USDC but response shows 1.05 → diff=0.05 > 0.01 → reject.
    Verifies the epsilon is enforced both directions."""
    body = '{"payout": {"id": "WH-100", "amount_usdc": 1.05, "from": "whop"}}'
    event = {
        "event": "earn",
        "slot": "clip",
        "receipt_id": "WH-100",
        "amount_usdc": 1.00,
        "payer": "whop",
        "platform": "whop",
        "platform_api_call": {
            "endpoint": "/api/v2/payouts/WH-100",
            "response_sha256": _hash(body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: body)
    assert result.ok is False
    assert result.failed_check.startswith("field-mismatch:amount")


# ── hash mismatch (step 2) ──────────────────────────────────────────
def test_hash_mismatch_rejected_at_step_2():
    real_body = '{"sale": {"id": "CN-1", "amount": 10000, "buyer": {"id": "x"}}}'
    event = {
        "event": "earn",
        "slot": "gig",
        "receipt_id": "CN-1",
        "amount_jpy": 10000,
        "payer": "x",
        "platform": "coconala",
        "platform_api_call": {
            "endpoint": "/api/v1/sales/CN-1",
            "response_sha256": "0" * 64,  # wrong hash
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: real_body)
    assert result.ok is False
    assert result.failed_check == "response-hash-mismatch"


# ── payer field-equality ────────────────────────────────────────────
def test_forged_payer_rejected_at_field_equality():
    body = '{"sale": {"id": "CN-2", "amount": 5000, "buyer": {"id": "REAL-BUYER"}}}'
    event = {
        "event": "earn",
        "slot": "gig",
        "receipt_id": "CN-2",
        "amount_jpy": 5000,
        "payer": "FAKE-BUYER",  # ≠ REAL-BUYER
        "platform": "coconala",
        "platform_api_call": {
            "endpoint": "/api/v1/sales/CN-2",
            "response_sha256": _hash(body),
        },
    }
    result = verify_earn_event(event, ALLOWLIST, refetch_fn=lambda *a, **k: body)
    assert result.ok is False
    assert result.failed_check.startswith("field-mismatch:payer")
