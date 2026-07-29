"""PROP-C1-evidence (required:true, Tier 0) — TRAP-4 faithfulness drift.

Spec: REQ-C1 — `evidence_id` MUST be exactly one of URL / payout_id / file path.
Paraphrases are forbidden in evidence_id. Promoted to required:true in FIND-014.
"""
import pytest

from lib.lessons import validate_evidence_id  # FAIL until 2b


# ── accepted forms ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    "evidence_id,evidence_type",
    [
        ("https://coconala.com/requests/5123100", "url"),
        ("https://coconala.com/mypage/messages/abc-123-def", "url"),
        ("CN_PAYOUT_2026_07_01_98765", "payout_id"),
        ("STRIPE_po_3ABCDEF", "payout_id"),
        ("/home/life-manager/gig/screenshots/2026-07-01-evidence.png", "file"),
        ("/var/log/something.log", "file"),
    ],
)
def test_accepts_canonical_evidence_forms(evidence_id, evidence_type):
    assert validate_evidence_id(evidence_id, evidence_type) is True


# ── rejected forms (paraphrase = TRAP-4 attack) ──────────────────────
@pytest.mark.parametrize(
    "paraphrase,claimed_type",
    [
        ("the buyer accepted the proposal yesterday", "url"),
        ("payout came through", "payout_id"),
        ("see the screenshot I made", "file"),
        ("user replied with 'sounds good'", "url"),
        ("Coconala paid us", "payout_id"),
        # type mismatch attempts
        ("https://coconala.com/foo", "payout_id"),  # URL claimed as payout_id
        ("/tmp/foo.png", "url"),                      # file path claimed as URL
        ("CN_PAYOUT_1", "file"),                       # id claimed as file path
        # empty / whitespace
        ("", "url"),
        ("   ", "url"),
    ],
)
def test_rejects_paraphrases_and_type_mismatches(paraphrase, claimed_type):
    assert validate_evidence_id(paraphrase, claimed_type) is False


# ── unknown type tag ─────────────────────────────────────────────────
def test_unknown_type_tag_rejected():
    assert validate_evidence_id("https://example.com/x", "guess") is False
