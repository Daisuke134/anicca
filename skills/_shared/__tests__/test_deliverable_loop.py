"""PROP-I2-deliverable-loop (required:true, Tier 1 integration) — output-quality at delivery.

Spec: behavioral-spec.md REQ-I2.
NO 納品 until artifact passes a fresh-context adversary review across 5 dimensions:
brief_completeness / factual_correctness / usefulness / presentation_quality / safety_surface.
Cap reached → DO NOT 納品, send polite scope-clarification message to buyer.
"""
from __future__ import annotations

import json
import pytest

from lib.deliverable_loop import (  # FAIL until 2b
    deliver_with_verify,
    DeliverableLoopResult,
)


def _verdict_pass():
    return {
        "overallVerdict": "PASS",
        "iteration": 1,
        "dimensions": [
            {"name": d, "verdict": "PASS"}
            for d in [
                "brief_completeness", "factual_correctness", "usefulness",
                "presentation_quality", "safety_surface",
            ]
        ],
        "convergenceSignals": {"findingCount": 0},
    }


def _verdict_fail(dim):
    return {
        "overallVerdict": "FAIL",
        "iteration": 1,
        "dimensions": [
            {"name": "brief_completeness", "verdict": "PASS"},
            {"name": "factual_correctness", "verdict": "PASS"},
            {"name": "usefulness", "verdict": "PASS"},
            {"name": "presentation_quality", "verdict": "PASS"},
            {"name": "safety_surface", "verdict": "PASS"},
            {"name": dim, "verdict": "FAIL"},
        ],
        "convergenceSignals": {"findingCount": 1},
    }


def _ctx(tmp_path):
    artifact = tmp_path / "deliverable.pptx"
    artifact.write_bytes(b"<binary pptx fake>")
    brief = tmp_path / "brief.md"
    brief.write_text("Build a 20-page SEO audit pptx covering …")
    msgs = tmp_path / "messages.jsonl"
    msgs.write_text(json.dumps({"role": "buyer", "text": "looking forward"}) + "\n")
    return artifact, brief, msgs


# ── happy path ───────────────────────────────────────────────────────
def test_happy_path_round_1_pass_delivers(tmp_path):
    artifact, brief, msgs = _ctx(tmp_path)
    verdicts = iter([_verdict_pass()])
    delivered: list = []

    result = deliver_with_verify(
        request_id="5123100",
        artifact_path=artifact,
        brief_path=brief,
        buyer_messages_path=msgs,
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        deliver_fn=lambda p: delivered.append(p) or "delivered_ok",
        max_rounds=3,
    )
    assert isinstance(result, DeliverableLoopResult)
    assert result.delivered is True
    assert result.rounds_to_pass == 1
    assert len(delivered) == 1


# ── iterate then pass ────────────────────────────────────────────────
def test_round_1_factual_fail_round_2_pass(tmp_path):
    artifact, brief, msgs = _ctx(tmp_path)
    verdicts = iter([_verdict_fail("factual_correctness"), _verdict_pass()])
    result = deliver_with_verify(
        request_id="5123100",
        artifact_path=artifact,
        brief_path=brief,
        buyer_messages_path=msgs,
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        deliver_fn=lambda p: "delivered_ok",
        max_rounds=3,
    )
    assert result.delivered is True
    assert result.rounds_to_pass == 2


# ── cap reached: DO NOT 納品 + send buyer scope-clarification ────────
def test_cap_reached_sends_buyer_clarification_msg_NOT_delivers(tmp_path):
    artifact, brief, msgs = _ctx(tmp_path)
    verdicts = iter([
        _verdict_fail("usefulness"),
        _verdict_fail("usefulness"),
        _verdict_fail("usefulness"),
    ])
    delivered: list = []
    buyer_msgs_sent: list = []
    lessons = tmp_path / "lessons.jsonl"

    result = deliver_with_verify(
        request_id="5123100",
        artifact_path=artifact,
        brief_path=brief,
        buyer_messages_path=msgs,
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        deliver_fn=lambda p: delivered.append(p) or "delivered_ok",
        send_buyer_msg_fn=lambda txt: buyer_msgs_sent.append(txt),
        max_rounds=3,
        lessons_path=lessons,
    )
    assert result.delivered is False
    assert result.stalled is True
    assert len(delivered) == 0  # protected: did NOT 納品 a bad artifact
    assert len(buyer_msgs_sent) == 1  # sent a scope-clarification msg
    # The msg is polite + buyer-facing — NOT a Telegram ping to a human (Dais)
    assert "scope" in buyer_msgs_sent[0].lower() or "clarif" in buyer_msgs_sent[0].lower()

    rows = [json.loads(l) for l in lessons.read_text().splitlines() if l.strip()]
    assert any(r["outcome"] == "deliverable-stalled" for r in rows)


# ── hallucinated-stat trips factual_correctness ─────────────────────
def test_hallucinated_stat_caught_by_factual_dimension(tmp_path):
    """If the adversary's factual_correctness fixture FAILed on round 1
    (= hallucinated stat detected), the dispatcher must iterate, NOT 納品."""
    artifact, brief, msgs = _ctx(tmp_path)
    verdicts = iter([_verdict_fail("factual_correctness"), _verdict_pass()])
    delivered: list = []
    result = deliver_with_verify(
        request_id="5123100",
        artifact_path=artifact,
        brief_path=brief,
        buyer_messages_path=msgs,
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        deliver_fn=lambda p: delivered.append(p) or "delivered_ok",
        max_rounds=3,
    )
    assert result.delivered is True
    assert result.rounds_to_pass == 2
    assert len(delivered) == 1
