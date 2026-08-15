#!/usr/bin/env python3
"""The last check before a stranger is contacted again."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import followup_gate  # noqa: E402

CLEAN = "その後いかがでしょうか。ご購入後、当日中に初稿をご提出します。"
REFUSED = [{"sender": "buyer", "text": "他の方探して下さい。"}]


def test_a_clean_draft_on_an_open_thread_is_sent():
    assert followup_gate.decide(conversation=[], body=CLEAN, silent_days=9.0)["ok"] is True


def test_a_refusal_outranks_a_perfect_draft():
    decision = followup_gate.decide(conversation=REFUSED, body=CLEAN, silent_days=9.0)
    assert decision["ok"] is False
    assert decision["reason"] == "stopped:other_seller"
    assert "他の方探して下さい" in decision["evidence"]


def test_the_live_thread_can_overrule_an_over_stated_silence():
    # The shortlist may have measured from buyer_sent_at, which sits before our reply.
    decision = followup_gate.decide(conversation=[], body=CLEAN, silent_days=0.5)
    assert decision["reason"] == "too_soon"


def test_a_free_deliverable_promise_is_refused():
    # The sentence that lost kiki_1115: a deliverable, before any purchase.
    decision = followup_gate.decide(
        conversation=[], body="本日中に構成案をお送りします。", silent_days=9.0)
    assert decision["ok"] is False
    assert decision["violations"] == ["unpaid_delivery_promise"]


def test_external_contact_is_refused():
    decision = followup_gate.decide(
        conversation=[], body="詳細は https://example.com をご覧ください。", silent_days=9.0)
    assert decision["reason"] == "draft_violation"
    assert "external_link" in decision["violations"]


def test_an_empty_draft_is_refused():
    assert followup_gate.decide(conversation=[], body="", silent_days=9.0)["ok"] is False


def test_missing_silence_does_not_block_a_clean_draft():
    # None means unknown, and the shortlist already applied the floor.
    assert followup_gate.decide(conversation=[], body=CLEAN, silent_days=None)["ok"] is True


def test_the_two_gates_share_one_floor():
    import followup_candidates

    assert followup_gate.MIN_SILENT_DAYS == followup_candidates.MIN_SILENT_DAYS
