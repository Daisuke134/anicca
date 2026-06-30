"""health_check_v2 — generic auto-recovery dispatcher (sprint-2).

PROP-H3 (multi-match → highest-priority) + H6 (no human-touch).
Replaces sprint-1 Group J1/J2/J3/J5 handlers with a SINGLE classify+dispatch flow.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# REQ-H3 priority order (sprint-2 v6 fix per FIND-2-002: api_rate_limit + backoff
# INHERITED from sprint-1 REQ-A6 + REQ-A8 explicitly). Lower index = higher priority.
PRIORITY_ORDER = [
    "backoff",            # = sprint-1 REQ-A8 BACKOFF
    "trust_dialog",       # = sprint-1 REQ-A4
    "not_logged_in",      # = sprint-1 REQ-A3
    "api_rate_limit",     # = sprint-1 REQ-A6 (inherited; FIND-2-002 enumeration)
    "hook_missing",       # = sprint-1 REQ-A5
    "spawn_drift",        # = sprint-2 REQ-H3(f)
    "cron_missing",       # = sprint-1 REQ-A7
    "tmux_dead",          # = sprint-1 REQ-A1
    "tmux_server_corrupted",  # = sprint-2 REQ-H3(g)
    "stale",              # = sprint-1 REQ-A2
]


@dataclass(frozen=True)
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
    """PURE: maps an Issue to a recipe dict {action, params}. ZERO human-touch.
    All 10 issue kinds from PRIORITY_ORDER have a recipe (FIND-012 fix: all enumerated).
    """
    kind = issue.kind
    RECIPES = {
        "tmux_dead": {"action": "restart", "params": {}},
        "stale": {"action": "restart", "params": {}},
        "tmux_server_corrupted": {"action": "kill_server", "params": {}},
        "trust_dialog": {"action": "send_keys", "params": {"keys": "1", "enter": True}},
        "not_logged_in": {"action": "login", "params": {"flow": "camofox+gmail_otp"}},
        "api_rate_limit": {"action": "send_keys",
                          "params": {"keys": "/model haiku-4-5", "enter": True}},
        "hook_missing": {"action": "npm_install", "params": {"flow": "allowlist_check"}},
        "spawn_drift": {"action": "git_checkout", "params": {"target": "anicca-bot-signed"}},
        "cron_missing": {"action": "send_keys", "params": {"flow": "reinject_startup"}},
        "backoff": {"action": "escalate_via_bot2bot", "params": {"reason": "backoff-cap"}},
    }
    return RECIPES.get(kind, {"action": "noop", "params": {}})


def dispatch_highest_priority(snap: HealthSnapshot) -> dict | None:
    """Production-side entry (FIND-007 fix): collect issues, resolve multi-match
    by PRIORITY_ORDER, return the recipe for the highest-priority detected issue.
    Returns None when no issue detected (= healthy).
    """
    issues = classify_issue_from_snapshot(snap)
    if not issues:
        return None
    issues.sort(key=lambda i: PRIORITY_ORDER.index(i.kind)
                if i.kind in PRIORITY_ORDER else 999)
    return select_fix_recipe(issues[0])
