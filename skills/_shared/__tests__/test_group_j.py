"""Group J self-recovery handlers (required:true PROP-J8 anti-human-touch; J1..J9 dispatch).

Spec: behavioral-spec.md Group J (REQ-J1..J9) + REQ-J8 invariant.
J8 is the SINGLE MOST IMPORTANT property here: NO Telegram, NO Slack, NO Twilio, NO
osascript dialog, NO `gh issue` with human-routing labels, NO Touch ID Keychain calls.
The static-analyzer that enforces J8 is the trust anchor of the whole NO-HUMAN doctrine.
"""
from __future__ import annotations

import pytest

from lib.group_j import (  # FAIL until 2b
    dispatch_self_recover,
    anti_human_touch_violations,
    SelfRecoverResult,
)


# ────────────────────────────────────────────────────────────────────────
# REQ-J8 anti-human-touch invariant — the most critical property.
# A static analyzer reads source code and flags any human-touching call.
# ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "src,expected_flag",
    [
        # Telegram POST
        ('requests.post("https://api.telegram.org/bot123/sendMessage", json={"text": "alert"})',
         "telegram"),
        # Slack webhook
        ('requests.post("https://hooks.slack.com/services/T/B/X", json={"text":"x"})',
         "slack"),
        # Twilio SMS
        ("twilio.messages.create(from_='+1', to='+1', body='alert')", "twilio"),
        # osascript dialog
        ('subprocess.run(["osascript", "-e", "display dialog \\"help\\""])', "osascript"),
        # terminal-notifier
        ('subprocess.run(["terminal-notifier", "-message", "help"])', "terminal-notifier"),
        # macOS keychain read (Touch ID gesture)
        ('subprocess.run(["security", "find-generic-password", "-s", "anicca-trust-anchor-pubkey", "-w"])',
         "security find-generic-password"),
        # gh issue with human-routing label
        ('subprocess.run(["gh", "issue", "create", "--label", "needs-login"])',
         "needs-login"),
        # Discord webhook
        ('requests.post("https://discord.com/api/webhooks/123/abc", json={"content":"x"})',
         "discord"),
        # FCM push
        ('requests.post("https://fcm.googleapis.com/fcm/send", json={"to":"x"})',
         "fcm"),
        # Apple Push (APN)
        ('requests.post("https://api.push.apple.com/3/device/X", json={"aps":{"alert":"x"}})',
         "apple"),
    ],
)
def test_static_analyzer_flags_human_touch(src, expected_flag):
    findings = anti_human_touch_violations(src)
    assert len(findings) >= 1, f"failed to flag: {src!r}"
    assert any(expected_flag in f["pattern"] for f in findings), \
        f"flag pattern {expected_flag} not in {findings}"


def test_clean_code_no_violations():
    """Normal earn-skill code must not be over-flagged."""
    src = (
        'import json, requests\n'
        'r = requests.get("https://coconala.com/api/v1/sales/5123100")\n'
        'data = json.loads(r.text)\n'
        'with open("earnings.jsonl", "a") as f:\n'
        '    f.write(json.dumps(data) + "\\n")\n'
    )
    findings = anti_human_touch_violations(src)
    assert findings == [], f"false-positive: {findings}"


# ────────────────────────────────────────────────────────────────────────
# Dispatcher tests — each REQ-J handler is invoked by reason
# ────────────────────────────────────────────────────────────────────────


def test_dispatch_unknown_reason_routes_to_mother_queue(tmp_path):
    """An unrecognized reason fall-through goes to MOTHER queue, NOT a human."""
    queue = tmp_path / "mother-recovery-queue.jsonl"
    result = dispatch_self_recover(
        slot="gig",
        reason="some-novel-failure-mode-we-never-saw-before",
        evidence="evidence text",
        mother_queue_path=queue,
    )
    assert result.status in ("exhausted",)
    assert queue.exists()
    assert queue.read_text().strip()  # row written


def test_dispatch_needs_login_invokes_j1_handler(tmp_path, monkeypatch):
    """needs-login reason dispatches to J1 auto-login (camofox + Gmail OTP)."""
    j1_called: list = []
    monkeypatch.setattr(
        "lib.group_j.j1_auto_login",
        lambda slot, oauth_url, **kw: (j1_called.append((slot, oauth_url)) or
                                       SelfRecoverResult(status="recovered")),
    )
    result = dispatch_self_recover(
        slot="gig",
        reason="needs-login",
        evidence="https://claude.com/cai/oauth/authorize?code=true&...",
        mother_queue_path=tmp_path / "queue.jsonl",
    )
    assert result.status == "recovered"
    assert len(j1_called) == 1


def test_dispatch_spawn_surface_drift_invokes_j2_handler(tmp_path, monkeypatch):
    j2_called: list = []
    monkeypatch.setattr(
        "lib.group_j.j2_auto_rollback",
        lambda slot, details, **kw: (j2_called.append(details) or
                                     SelfRecoverResult(status="recovered")),
    )
    result = dispatch_self_recover(
        slot="gig",
        reason="spawn-surface-drift",
        evidence="adversary-daily-prompt.tmpl:observed-sha:pinned-sha",
        mother_queue_path=tmp_path / "queue.jsonl",
    )
    assert result.status == "recovered"
    assert len(j2_called) == 1


def test_dispatch_backoff_cap_invokes_j5_handler(tmp_path, monkeypatch):
    j5_called: list = []
    monkeypatch.setattr(
        "lib.group_j.j5_fresh_start",
        lambda slot, details, **kw: (j5_called.append(slot) or
                                     SelfRecoverResult(status="recovered")),
    )
    result = dispatch_self_recover(
        slot="gig",
        reason="backoff-cap",
        evidence="5 restarts in 60min",
        mother_queue_path=tmp_path / "queue.jsonl",
    )
    assert result.status == "recovered"
    assert "gig" in j5_called


# ────────────────────────────────────────────────────────────────────────
# Dedup — same failure twice within 24h must collapse
# ────────────────────────────────────────────────────────────────────────


def test_two_calls_same_failure_collapse_via_self_recover_log(tmp_path, monkeypatch):
    """REQ-F1 step 2 + REQ-F2: same (slot, reason, normalized_evidence) within
    24h does NOT re-fire the handler."""
    j1_calls: list = []
    monkeypatch.setattr(
        "lib.group_j.j1_auto_login",
        lambda slot, oauth_url, **kw: (j1_calls.append((slot, oauth_url)) or
                                       SelfRecoverResult(status="recovered")),
    )
    log = tmp_path / "self-recover-log.jsonl"
    dispatch_self_recover(
        slot="gig",
        reason="needs-login",
        evidence="https://claude.com/cai/oauth/authorize?code=A ts:1782800000 round-3",
        mother_queue_path=tmp_path / "queue.jsonl",
        log_path=log,
    )
    dispatch_self_recover(
        slot="gig",
        reason="needs-login",
        evidence="https://claude.com/cai/oauth/authorize?code=B ts:1782900000 round-5",
        mother_queue_path=tmp_path / "queue.jsonl",
        log_path=log,
    )
    # Two calls, same normalized evidence (timestamps + round-N stripped) →
    # dedup collapses to ONE handler invocation.
    assert len(j1_calls) == 1


# ────────────────────────────────────────────────────────────────────────
# REQ-J8 negative meta-test: the SelfRecoverResult interface itself does NOT
# carry any human-notification fields. If a future change adds fields like
# `dais_notified` or `tg_message_id`, that's a regression.
# ────────────────────────────────────────────────────────────────────────


def test_SelfRecoverResult_has_no_human_fields():
    r = SelfRecoverResult(status="recovered")
    forbidden_fields = {
        "dais_notified", "telegram_sent", "tg_message_id",
        "human_alerted", "escalated_to_human", "slack_message_id",
    }
    actual_fields = set(r.__dataclass_fields__.keys()) if hasattr(r, "__dataclass_fields__") else set(vars(r).keys())
    assert not (forbidden_fields & actual_fields), \
        f"regression: result carries human-touch fields: {forbidden_fields & actual_fields}"
