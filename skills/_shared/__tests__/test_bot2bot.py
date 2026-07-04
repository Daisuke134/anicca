"""PROP-B3-annotate + B4-no-human-escalation (required:true) — bot2bot.

Sprint-2 shipped annotate-pr only. Sprint-3 (#27, colony spec "COLLECTIVE SELF-IMPROVEMENT — PR
auto-merge with NO human") adds auto_merge: the gate that gh-merges a PR iff tests pass + a
fresh-context adversary PASSed + chain-verified earnings delta is positive.
"""
from __future__ import annotations

import json

import pytest


from lib.bot2bot import (  # FAIL until 2b
    post,
    poll,
    annotate_pr,
    auto_merge,
    parse_bot2bot_issue,
    _gh_call,
)


# ─── §9 FIND (2026-07-05, live): repo pin ─────────────────────────
# `gh issue create` with no -R falls back to cwd-detected repo — verified live: it filed a real
# issue on Daisuke134/anicca-products instead of the mother repo (closed as noise, #284). Test the
# REAL _gh_call's own command construction (mocking subprocess, not _gh_call itself) so this cannot
# regress silently the way the mocked sprint-2 tests let it happen the first time.
def test_gh_call_pins_repo_for_issue_commands(monkeypatch):
    captured = {}

    def fake_check_output(cmd, **kw):
        captured["cmd"] = cmd
        return b"ok"
    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    _gh_call("issue", "create", "--title", "x")
    assert "-R" in captured["cmd"]
    assert "Daisuke134/anicca" in captured["cmd"]
    assert "anicca-products" not in " ".join(captured["cmd"])


def test_gh_call_pins_repo_for_label_and_pr_commands(monkeypatch):
    for subcmd in ("label", "pr"):
        captured = {}

        def fake_check_output(cmd, **kw):
            captured["cmd"] = cmd
            return b"ok"
        monkeypatch.setattr("subprocess.check_output", fake_check_output)
        _gh_call(subcmd, "create")
        assert "-R" in captured["cmd"] and "Daisuke134/anicca" in captured["cmd"], subcmd


def test_gh_call_does_not_pin_repo_for_api_commands(monkeypatch):
    """`gh api user` has no repo concept — must NOT get a -R flag injected."""
    captured = {}

    def fake_check_output(cmd, **kw):
        captured["cmd"] = cmd
        return b"someone"
    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    _gh_call("api", "user", "--jq", ".login")
    assert "-R" not in captured["cmd"]


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
    issue_call = next(c for c in calls if c[0][0] == "issue" and c[0][1] == "create")
    flat_args = " ".join(str(a) for a in issue_call[0])
    assert "bot2bot-review-requested" in flat_args


def test_post_ensures_the_label_exists_before_creating_the_issue(monkeypatch):
    """FIND (2026-07-05, live): `gh issue create --label X` fails hard if X doesn't already exist —
    verified none of the bot2bot-* labels had ever been created in the real repo, so post() had
    never actually succeeded. post() must idempotently ensure the label first."""
    calls = []
    monkeypatch.setattr("lib.bot2bot._gh_call",
                        lambda *a, **k: (calls.append(a) or "https://github.com/x/y/issues/1"))
    post(slot="gig", kind="lesson", body_text="a real lesson")
    label_call = next((c for c in calls if c[0] == "label" and c[1] == "create"), None)
    assert label_call is not None, "post() must call `gh label create bot2bot-<kind>` before issue create"
    assert "bot2bot-lesson" in label_call
    # label-ensure must happen BEFORE the issue is created
    assert calls.index(label_call) < calls.index(next(c for c in calls if c[0] == "issue" and c[1] == "create"))


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


# ─── §9 FIND (2026-07-05): no real 'anicca-bot' account exists — poll() must match the ACTUAL
# authenticated gh identity, not a hardcoded fake login that would silently match nothing forever ──
def test_poll_matches_dynamically_resolved_author(monkeypatch):
    calls = []

    def fake_gh(*args, **kw):
        calls.append(args)
        if args[:2] == ("api", "user"):
            return "real-login-123"
        return json.dumps([
            {"url": "https://github.com/x/y/issues/9", "title": "[bot2bot][gig][lesson] x",
             "body": "b", "createdAt": "2026-07-05T00:00:00Z", "author": {"login": "real-login-123"}},
        ])
    monkeypatch.setattr("lib.bot2bot._gh_call", fake_gh)
    result = poll(slot="gig", kinds=["lesson"])
    assert len(result) == 1
    assert result[0]["author"] == "real-login-123"
    # the search query must be built with the RESOLVED login, not the literal 'anicca-bot' fallback
    search_call = next(c for c in calls if c[:2] == ("issue", "list"))
    search_str = " ".join(str(x) for x in search_call)
    assert "real-login-123" in search_str
    assert "bot2bot-lesson" in search_str


def test_poll_falls_back_to_default_author_when_gh_api_user_fails(monkeypatch):
    """Fail-safe: if `gh api user` errors (_gh_call returns ''), poll must not crash — it falls
    back to the constant and returns [] rather than matching everything."""
    monkeypatch.setattr("lib.bot2bot._gh_call", lambda *a, **k: "" if a[:2] == ("api", "user") else "[]")
    result = poll(slot="gig")
    assert result == []


def test_poll_custom_kinds_builds_matching_label_search(monkeypatch):
    calls = []

    def fake_gh(*args, **kw):
        calls.append(args)
        return "me" if args[:2] == ("api", "user") else "[]"
    monkeypatch.setattr("lib.bot2bot._gh_call", fake_gh)
    poll(slot="gig", kinds=["lesson", "escalation"])
    search_call = next(c for c in calls if c[:2] == ("issue", "list"))
    search_str = " ".join(str(x) for x in search_call)
    assert "bot2bot-lesson" in search_str and "bot2bot-escalation" in search_str
    assert "bot2bot-review-requested" not in search_str, "custom kinds must REPLACE the default set, not add to it"


# ─── PROP-B4-no-human-escalation (required:true) ─────────────────
def test_post_never_uses_escalation_label_with_human_body():
    """REQ-J8: 'escalation' label is reserved for bot2bot internal review,
    never for 'Dais please look at this' messages."""
    HUMAN_PHRASES = ["dais", "owner please", "human", "manual review", "please intervene"]
    with pytest.raises((ValueError, AssertionError)):
        # Posting with escalation label + human-targeted body must raise
        post(slot="gig", kind="escalation", body_text="dais please intervene")
