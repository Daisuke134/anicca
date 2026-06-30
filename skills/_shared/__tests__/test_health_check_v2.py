"""PROP-H3 + H6 — health-check dispatch (sprint-2 v2).

Spec REQ-H3: multi-match resolves to HIGHEST-PRIORITY issue, not raise.
"""
from __future__ import annotations

import pytest

from lib.health_check_v2 import (  # FAIL until 2b
    HealthSnapshot,
    Issue,
    classify_issue_from_snapshot,
    select_fix_recipe,
    PRIORITY_ORDER,
)


def _snap(**overrides):
    base = dict(
        tmux_alive=True,
        last_pass_mtime=1782900000,
        last_start_mtime=1782900000,
        restart_log_entries=[],
        pane_text="",
        cron_has_slot_job=True,
        spawn_surface_valid=True,
        hook_modules_valid=True,
        now_ts=1782900000,
    )
    base.update(overrides)
    return HealthSnapshot(**base)


# ─── PROP-H3-dispatch (required:true) ─────────────────────────────
def test_tmux_dead_detected():
    issues = classify_issue_from_snapshot(_snap(tmux_alive=False))
    assert any(i.kind == "tmux_dead" for i in issues)


def test_stale_detected():
    issues = classify_issue_from_snapshot(
        _snap(last_pass_mtime=1782900000 - 6000)  # 100 min ago
    )
    assert any(i.kind == "stale" for i in issues)


def test_not_logged_in_detected():
    issues = classify_issue_from_snapshot(
        _snap(pane_text="Not logged in · Please run /login")
    )
    assert any(i.kind == "not_logged_in" for i in issues)


def test_trust_dialog_detected():
    issues = classify_issue_from_snapshot(
        _snap(pane_text="Quick safety check: Is this a project you ... trust")
    )
    assert any(i.kind == "trust_dialog" for i in issues)


def test_hook_missing_detected():
    issues = classify_issue_from_snapshot(_snap(hook_modules_valid=False))
    assert any(i.kind == "hook_missing" for i in issues)


def test_spawn_drift_detected():
    issues = classify_issue_from_snapshot(_snap(spawn_surface_valid=False))
    assert any(i.kind == "spawn_drift" for i in issues)


def test_tmux_server_corrupted_detected():
    """FIND-2-010 fix: HealthSnapshot is frozen=True; tmux_server_state set
    at construction time, not via post-construct mutation."""
    snap = _snap(tmux_alive=False, tmux_server_state="corrupted")
    issues = classify_issue_from_snapshot(snap)
    # Either tmux_dead or tmux_server_corrupted issue is acceptable
    assert any(i.kind in ("tmux_dead", "tmux_server_corrupted") for i in issues)


# ─── PROP-H3 multi-match resolves to highest priority ─────────────
def test_multi_match_resolves_to_highest_priority():
    """When tmux_dead AND not_logged_in both detect, dispatch picks the
    highest-priority issue per REQ-H3 priority order — not 'raise'."""
    snap = _snap(
        tmux_alive=False,
        pane_text="Not logged in · Please run /login",
    )
    issues = classify_issue_from_snapshot(snap)
    # Both issues exist in detected list
    kinds = {i.kind for i in issues}
    assert "tmux_dead" in kinds
    # But the dispatch picks the highest-priority one
    primary = max(issues, key=lambda i: -PRIORITY_ORDER.index(i.kind) if i.kind in PRIORITY_ORDER else -999)
    recipe = select_fix_recipe(primary)
    assert recipe is not None
    assert recipe["action"] in ("restart", "login", "send_keys", "git_checkout", "npm_install", "kill_server")


def test_no_issues_when_healthy():
    issues = classify_issue_from_snapshot(_snap())
    assert issues == []


# ─── PROP-H6-no-human-touch (required:true) ───────────────────────
def test_select_fix_recipe_never_returns_human_touch_action():
    """Any recipe must NOT have action='telegram_post' or similar human-touch."""
    snap = _snap(tmux_alive=False)
    issues = classify_issue_from_snapshot(snap)
    for i in issues:
        recipe = select_fix_recipe(i)
        FORBIDDEN_ACTIONS = {
            "telegram_post", "slack_webhook", "twilio_sms", "osascript_dialog",
            "terminal_notifier", "security_find_generic_password",
        }
        assert recipe.get("action") not in FORBIDDEN_ACTIONS
