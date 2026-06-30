"""PROP-I1-proposal-loop (required:true, Tier 1 integration) — output-quality gate at apply time.

Spec: behavioral-spec.md REQ-I1.
NO submit until proposal passes a fresh-context adversary review across 5 dimensions:
brief_alignment / sample_relevance / price_realism / delivery_realism / red_flags.
≤3 round iter loop; cap reached → SKIP request (protects account rating).
"""
from __future__ import annotations

import json
import pytest

from lib.proposal_loop import (  # FAIL until 2b
    propose_with_verify,
    ProposalLoopResult,
)


# ────────────────────────────────────────────────────────────────────────
# Fixture: a stubbed adversary that returns a pre-canned verdict per round.
# Real impl spawns a fresh Opus subagent; tests inject fixture verdicts so
# the assertion is "did the dispatcher RESPECT the verdicts correctly?"
# ────────────────────────────────────────────────────────────────────────


def _verdict_pass():
    return {
        "overallVerdict": "PASS",
        "iteration": 1,
        "dimensions": [
            {"name": "brief_alignment", "verdict": "PASS"},
            {"name": "sample_relevance", "verdict": "PASS"},
            {"name": "price_realism", "verdict": "PASS"},
            {"name": "delivery_realism", "verdict": "PASS"},
            {"name": "red_flags", "verdict": "PASS"},
        ],
        "convergenceSignals": {"findingCount": 0},
    }


def _verdict_fail(dim, finding_id):
    return {
        "overallVerdict": "FAIL",
        "iteration": 1,
        "dimensions": [
            {"name": "brief_alignment", "verdict": "PASS"},
            {"name": "sample_relevance", "verdict": "PASS"},
            {"name": "price_realism", "verdict": "PASS"},
            {"name": "delivery_realism", "verdict": "PASS"},
            {"name": "red_flags", "verdict": "PASS"},
            # mutate one dimension to FAIL
            {"name": dim, "verdict": "FAIL"},
        ],
        "convergenceSignals": {"findingCount": 1, "evaluatedCriteria": [finding_id]},
    }


def _draft(price=10000, body="generic"):
    return {
        "title": "SEO診断",
        "body": body,
        "sample_deliverable": "/tmp/sample.docx",
        "price_jpy": price,
        "delivery_date": "2026-07-10",
    }


def _brief():
    return {
        "requestId": "5125589",
        "brief_text": "クライアントサイトのSEO診断と改善提案ができる方を募集します",
        "budget_range_jpy": [10000, 30000],
    }


# ── happy path round-1 ───────────────────────────────────────────────
def test_round_1_pass_submits_immediately(tmp_path):
    verdicts = iter([_verdict_pass()])
    submitted: list = []

    result = propose_with_verify(
        request=_brief(),
        draft=_draft(),
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        submit_fn=lambda d: submitted.append(d) or "applied_ok",
        max_rounds=3,
    )
    assert isinstance(result, ProposalLoopResult)
    assert result.submitted is True
    assert result.rounds_to_pass == 1
    assert len(submitted) == 1


# ── iterate-then-PASS round-2 ────────────────────────────────────────
def test_round_1_fail_round_2_pass(tmp_path):
    verdicts = iter([
        _verdict_fail("brief_alignment", "FIND-I1-001"),
        _verdict_pass(),
    ])
    submitted: list = []
    result = propose_with_verify(
        request=_brief(),
        draft=_draft(),
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        submit_fn=lambda d: submitted.append(d) or "applied_ok",
        max_rounds=3,
    )
    assert result.submitted is True
    assert result.rounds_to_pass == 2


# ── cap reached: round-3 still FAIL → SKIP, NO submit ────────────────
def test_round_3_fail_skips_submit_and_logs_lesson(tmp_path):
    verdicts = iter([
        _verdict_fail("brief_alignment", "FIND-I1-001"),
        _verdict_fail("price_realism", "FIND-I1-002"),
        _verdict_fail("delivery_realism", "FIND-I1-003"),
    ])
    submitted: list = []
    lessons = tmp_path / "lessons.jsonl"

    result = propose_with_verify(
        request=_brief(),
        draft=_draft(),
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        submit_fn=lambda d: submitted.append(d) or "applied_ok",
        max_rounds=3,
        lessons_path=lessons,
    )
    assert result.submitted is False
    assert result.stalled is True
    assert len(submitted) == 0  # protected: did not submit a bad proposal

    rows = [json.loads(l) for l in lessons.read_text().splitlines() if l.strip()]
    assert any(r["outcome"] == "proposal-stalled" for r in rows)


# ── round persistence to disk (for adversary re-review on round 2) ──
def test_each_round_draft_persisted_to_disk(tmp_path):
    verdicts = iter([_verdict_fail("red_flags", "FIND-X"), _verdict_pass()])
    propose_with_verify(
        request=_brief(),
        draft=_draft(),
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        submit_fn=lambda d: "applied_ok",
        max_rounds=3,
    )
    round_1_dir = tmp_path / "proposals" / "5125589" / "round-1"
    round_2_dir = tmp_path / "proposals" / "5125589" / "round-2"
    assert (round_1_dir / "draft.json").exists()
    assert (round_2_dir / "draft.json").exists()


# ── AI-tell phrase trips red_flags ───────────────────────────────────
def test_ai_tell_phrase_caught_by_red_flags_dimension(tmp_path):
    """If the adversary scoring function flagged 'delighted to help' as a
    red_flags FAIL, the dispatcher MUST respect that and iterate."""
    verdicts = iter([
        _verdict_fail("red_flags", "FIND-I1-ai-tell"),
        _verdict_pass(),
    ])
    body_with_ai_tell = "I would be delighted to help with your SEO needs..."
    result = propose_with_verify(
        request=_brief(),
        draft=_draft(body=body_with_ai_tell),
        loop_dir=tmp_path,
        adversary_stub=lambda **kw: next(verdicts),
        submit_fn=lambda d: "applied_ok",
        max_rounds=3,
    )
    assert result.submitted is True
    assert result.rounds_to_pass == 2
