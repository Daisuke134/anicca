"""PROP-B3-annotate + B4-no-human-escalation (required:true) — bot2bot.

Sprint-2 shipped annotate-pr only. Sprint-3 (#27, colony spec "COLLECTIVE SELF-IMPROVEMENT — PR
auto-merge with NO human") adds auto_merge: the gate that gh-merges a PR iff tests pass + a
fresh-context adversary PASSed + chain-verified earnings delta is positive.
"""
from __future__ import annotations

import pytest


from lib.bot2bot import (  # FAIL until 2b
    post,
    poll,
    annotate_pr,
    auto_merge,
    parse_bot2bot_issue,
)


# ─── PROP-B3-annotate (required:true) ─────────────────────────────
def test_annotate_pr_does_not_merge(monkeypatch):
    """REQ-B3 in v2 ships ONLY annotate-pr; merge is sprint-3 commit."""
    merge_calls = []

    def fake_gh(*args, **kw):
        if "merge" in str(args):
            merge_calls.append(args)
        return "ok"
    monkeypatch.setattr("lib.bot2bot._gh_call", fake_gh)
    annotate_pr(slot="gig", pr_number=123, verdict={"overallVerdict": "PASS"})
    assert merge_calls == [], "bot2bot.annotate_pr must NOT call gh pr merge in sprint-2"


# ─── sprint-3: REQ-MERGE auto_merge (#27) ─────────────────────────
_GOOD_VERDICT = {"tests_pass": True, "adversary_verdict": "PASS", "earnings_delta_usd": 1.23}


def _capture_gh(monkeypatch):
    calls = []
    monkeypatch.setattr("lib.bot2bot._gh_call", lambda *a, **k: (calls.append(a) or "ok"))
    return calls


def test_auto_merge_merges_when_all_gates_pass(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    calls = _capture_gh(monkeypatch)
    result = auto_merge(slot="gig", pr_number=42, verdict=_GOOD_VERDICT)
    assert result["merged"] is True
    merge_calls = [c for c in calls if "merge" in c]
    assert len(merge_calls) == 1
    assert "42" in merge_calls[0]


def test_auto_merge_rejects_when_tests_fail(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    calls = _capture_gh(monkeypatch)
    verdict = {**_GOOD_VERDICT, "tests_pass": False}
    result = auto_merge(slot="gig", pr_number=42, verdict=verdict)
    assert result["merged"] is False
    assert not any("merge" in c for c in calls), "must never merge when tests fail"


def test_auto_merge_rejects_when_adversary_fail(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    calls = _capture_gh(monkeypatch)
    verdict = {**_GOOD_VERDICT, "adversary_verdict": "FAIL"}
    result = auto_merge(slot="gig", pr_number=42, verdict=verdict)
    assert result["merged"] is False
    assert not any("merge" in c for c in calls), "must never merge when the adversary FAILed"


def test_auto_merge_rejects_when_earnings_delta_non_positive(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    calls = _capture_gh(monkeypatch)
    verdict = {**_GOOD_VERDICT, "earnings_delta_usd": 0}
    result = auto_merge(slot="gig", pr_number=42, verdict=verdict)
    assert result["merged"] is False
    assert not any("merge" in c for c in calls), "must never merge a non-positive (no real improvement) delta"


def test_auto_merge_fails_closed_on_missing_verdict_keys(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    calls = _capture_gh(monkeypatch)
    result = auto_merge(slot="gig", pr_number=42, verdict={})
    assert result["merged"] is False, "missing verdict fields must fail-closed, never merge"
    assert not any("merge" in c for c in calls)


def test_auto_merge_logs_every_decision(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    _capture_gh(monkeypatch)
    auto_merge(slot="gig", pr_number=1, verdict=_GOOD_VERDICT)
    auto_merge(slot="gig", pr_number=2, verdict={**_GOOD_VERDICT, "tests_pass": False})
    log = tmp_path / "loops" / "gig" / "auto-merge-log.jsonl"
    assert log.exists()
    lines = log.read_text().strip().split("\n")
    assert len(lines) == 2, "both the merge and the rejection must be logged"


# ─── PROP-B1-post ─────────────────────────────────────────────────
def test_post_creates_issue_with_correct_label(monkeypatch):
    calls = []
    monkeypatch.setattr("lib.bot2bot._gh_call",
                        lambda *a, **k: (calls.append((a, k)) or "https://github.com/x/y/issues/1"))
    url = post(slot="gig", kind="review-requested", body_text="please review")
    assert url == "https://github.com/x/y/issues/1"
    # The first call should be gh issue create with --label bot2bot-review-requested
    flat_args = " ".join(str(a) for a in calls[0][0])
    assert "issue" in flat_args and "create" in flat_args
    assert "bot2bot-review-requested" in flat_args


# ─── PROP-B2-poll ─────────────────────────────────────────────────
def test_poll_returns_empty_list_when_no_issues(monkeypatch):
    monkeypatch.setattr("lib.bot2bot._gh_call", lambda *a, **k: "[]")
    result = poll(slot="gig")
    assert result == []


def test_poll_parses_each_issue():
    """parse_bot2bot_issue produces a TaskRow dict."""
    gh_json = {"url": "https://github.com/x/y/issues/1",
               "title": "[bot2bot][gig][review-requested] x",
               "body": "details", "createdAt": "2026-07-01T05:00:00Z"}
    task = parse_bot2bot_issue(gh_json)
    assert task["issue_url"] == gh_json["url"]
    assert task["kind"] == "review-requested"
    assert task["slot"] == "gig"


# ─── PROP-B4-no-human-escalation (required:true) ─────────────────
def test_post_never_uses_escalation_label_with_human_body():
    """REQ-J8: 'escalation' label is reserved for bot2bot internal review,
    never for 'Dais please look at this' messages."""
    HUMAN_PHRASES = ["dais", "owner please", "human", "manual review", "please intervene"]
    with pytest.raises((ValueError, AssertionError)):
        # Posting with escalation label + human-targeted body must raise
        post(slot="gig", kind="escalation", body_text="dais please intervene")
