"""health_check_v2 — generic auto-recovery dispatcher (sprint-2).

PROP-H3 (multi-match → highest-priority) + H6 (no human-touch).
Replaces sprint-1 Group J1/J2/J3/J5 handlers with a SINGLE classify+dispatch flow.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Priority order: lower index = higher priority
# (REQ-H3 says: BACKOFF > TRUST_DIALOG > NOT_LOGGED_IN > API_RATE_LIMIT > HOOK > CRON > TMUX > STALE)
PRIORITY_ORDER = [
    "backoff",
    "trust_dialog",
    "not_logged_in",
    "api_rate_limit",
    "hook_missing",
    "spawn_drift",
    "cron_missing",
    "tmux_dead",
    "tmux_server_corrupted",
    "stale",
]


@dataclass
class HealthSnapshot:
    tmux_alive: bool
    last_pass_mtime: int
    last_start_mtime: int
    restart_log_entries: list[int]
    pane_text: str
    cron_has_slot_job: bool
    spawn_surface_valid: bool
    hook_modules_valid: bool
    now_ts: int
    tmux_server_state: str = "ok"


@dataclass
class Issue:
    kind: str
    details: dict[str, Any] = field(default_factory=dict)


_STALE_SECONDS = 90 * 60
_API_RATE_RE = re.compile(r"API error · Retrying.*attempt (\d+)/10")


def classify_issue_from_snapshot(snap: HealthSnapshot) -> list[Issue]:
    """PURE: returns a list of detected issues. Multi-match returns ALL detected;
    select_fix_recipe picks the highest-priority via PRIORITY_ORDER.
    """
    issues: list[Issue] = []

    # Backoff
    recent_restarts = [t for t in snap.restart_log_entries if (snap.now_ts - t) <= 3600]
    if len(recent_restarts) >= 5:
        issues.append(Issue(kind="backoff"))

    # Pane content modes
    if "Quick safety check" in snap.pane_text and "trust" in snap.pane_text:
        issues.append(Issue(kind="trust_dialog"))
    if "Not logged in" in snap.pane_text and "/login" in snap.pane_text:
        issues.append(Issue(kind="not_logged_in"))
    m = _API_RATE_RE.search(snap.pane_text)
    if m and int(m.group(1)) >= 5:
        issues.append(Issue(kind="api_rate_limit"))

    # State modes
    if not snap.hook_modules_valid:
        issues.append(Issue(kind="hook_missing"))
    if not snap.spawn_surface_valid:
        issues.append(Issue(kind="spawn_drift"))
    if not snap.cron_has_slot_job:
        issues.append(Issue(kind="cron_missing"))
    if not snap.tmux_alive:
        if snap.tmux_server_state == "corrupted":
            issues.append(Issue(kind="tmux_server_corrupted"))
        else:
            issues.append(Issue(kind="tmux_dead"))
    if snap.last_pass_mtime and (snap.now_ts - snap.last_pass_mtime) >= _STALE_SECONDS:
        issues.append(Issue(kind="stale"))

    return issues


def select_fix_recipe(issue: Issue) -> dict:
    """PURE: maps an Issue to a recipe dict {action, params}. ZERO human-touch."""
    kind = issue.kind
    if kind in ("tmux_dead", "stale"):
        return {"action": "restart", "params": {}}
    if kind == "tmux_server_corrupted":
        return {"action": "kill_server", "params": {}}
    if kind == "trust_dialog":
        return {"action": "send_keys", "params": {"keys": "1", "enter": True}}
    if kind == "not_logged_in":
        return {"action": "login", "params": {"flow": "camofox+gmail_otp"}}
    if kind == "api_rate_limit":
        return {"action": "send_keys", "params": {"keys": "/model haiku-4-5", "enter": True}}
    if kind == "hook_missing":
        return {"action": "npm_install", "params": {"flow": "allowlist_check"}}
    if kind == "spawn_drift":
        return {"action": "git_checkout", "params": {"target": "anicca-bot-signed"}}
    if kind == "cron_missing":
        return {"action": "send_keys", "params": {"flow": "reinject_startup"}}
    if kind == "backoff":
        return {"action": "escalate_via_bot2bot", "params": {"reason": "backoff-cap"}}
    return {"action": "noop", "params": {}}
