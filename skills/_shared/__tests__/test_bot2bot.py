"""PROP-B3-annotate + B4-no-human-escalation (required:true) — bot2bot.

Sprint-2 ships annotate-pr only; auto-merge SCOPE-DEFERRED to sprint-3.
"""
from __future__ import annotations

import pytest


from lib.bot2bot import (  # FAIL until 2b
    post,
    poll,
    annotate_pr,
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


def test_auto_merge_function_does_not_exist():
    """Static-analysis-level: lib.bot2bot has NO auto_merge function."""
    import lib.bot2bot
    assert not hasattr(lib.bot2bot, "auto_merge"), \
        "auto_merge is SCOPE-DEFERRED to sprint-3 per FIND-003 critical"


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
