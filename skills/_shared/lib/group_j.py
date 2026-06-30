"""group_j — self-recover dispatcher + Group J handlers (NO HUMAN, v7).

PROP-J8 anti-human-touch invariant + REQ-F1 dispatcher contract.

Spec: behavioral-spec.md REQ-F1 + REQ-J1..J9.
ZERO Telegram / Slack / Twilio / osascript / Touch ID. EVERY failure mode dispatches
to an auto-recovery handler; exhaustion routes to MOTHER queue (= another AI instance,
NOT a human).
"""
from __future__ import annotations

import ast
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from lib.escalate import dedup_key, is_duplicate, normalize_evidence


# ────────────────────────────────────────────────────────────────────────
# Result type — REQ-J8: must NOT carry any human-notification fields.
# A regression test asserts the field set has none of dais_notified /
# telegram_sent / tg_message_id / human_alerted / etc.
# ────────────────────────────────────────────────────────────────────────


@dataclass
class SelfRecoverResult:
    status: str  # "recovered" | "exhausted" | "deduplicated"
    handler: str | None = None
    details: dict = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────────
# PROP-J8 — anti-human-touch static analyzer.
# Greps source for any pattern in the blocklist. ANY non-empty result fails
# the adversary-daily review.
# ────────────────────────────────────────────────────────────────────────


_HUMAN_TOUCH_PATTERNS = [
    # (pattern_regex, label) — label is what we report.
    # Patterns are intentionally broad: they match the BLOCKED token regardless of
    # how the source spells it (e.g. `find-generic-password` whether called as
    # `security find-generic-password ...` or `["security", "find-generic-password"]`).
    (re.compile(r"api\.telegram\.org"), "telegram-api"),
    (re.compile(r"hooks\.slack\.com"), "slack-webhook"),
    (re.compile(r"\btwilio\b", re.IGNORECASE), "twilio"),
    (re.compile(r"\bosascript\b"), "osascript-dialog"),
    (re.compile(r"\bterminal-notifier\b"), "terminal-notifier"),
    (re.compile(r"\bfind-generic-password\b"), "security find-generic-password"),
    (re.compile(r"\badd-generic-password\b"), "security add-generic-password"),
    # gh issue with human-routing label — match the LABEL token wherever it appears,
    # not just after `--label`.
    (re.compile(r"\bneeds-login\b"), "needs-login"),
    (re.compile(r"\bneeds-human\b"), "needs-human"),
    (re.compile(r"\bneeds-attention\b"), "needs-attention"),
    # Match `escalation` as a gh-issue label argument. Covers BOTH:
    #   --label escalation        (string form, FIND-018)
    #   ["--label", "escalation"] (list-literal form, FIND-2-005)
    (re.compile(r"--label\s*[=]?\s*['\"]?escalation['\"]?"), "gh-issue-escalation"),
    (re.compile(r"['\"]--label['\"]\s*,\s*['\"]escalation['\"]"), "gh-issue-escalation-list-form"),
    (re.compile(r"\bplease-review\b"), "please-review"),
    (re.compile(r"discord\.com"), "discord"),
    (re.compile(r"fcm\.googleapis\.com"), "fcm"),
    (re.compile(r"api\.push\.apple\.com"), "apple-push"),
    (re.compile(r"pushover\.net"), "pushover"),
    (re.compile(r"ntfy\.sh"), "ntfy"),
    (re.compile(r"messagebird\.com"), "messagebird"),
    (re.compile(r"~/Library/Mobile Documents"), "icloud-bridge"),
    (re.compile(r"~/Documents/anicca-please-"), "human-attention-file"),
]


def anti_human_touch_violations(source: str) -> list[dict]:
    """Return list of {pattern, label, line} for each blocklist hit. Empty list = clean."""
    findings = []
    for pattern, label in _HUMAN_TOUCH_PATTERNS:
        for m in pattern.finditer(source):
            line_no = source[: m.start()].count("\n") + 1
            findings.append({
                "pattern": label,
                "match": m.group(0),
                "line": line_no,
            })
    return findings


# ────────────────────────────────────────────────────────────────────────
# Dispatcher — routes (slot, reason, evidence) to the right J handler.
# Implements REQ-F1 dedup + dispatch contract.
# ────────────────────────────────────────────────────────────────────────


_HANDLER_BY_REASON = {
    "needs-login": "j1_auto_login",
    "oauth-extract-failed": "j1_auto_login",
    "trust-anchor-unreadable": "j2_auto_rollback",
    "spawn-surface-sig-invalid": "j2_auto_rollback",
    "spawn-surface-drift": "j2_auto_rollback",
    "spawn-surface-flag-missing": "j2_auto_rollback",
    "hook-module-unrecognized": "j3_auto_research",
    "adversary-stalled": "j4_model_ladder",
    "backoff-cap": "j5_fresh_start",
    "token-kill-switch": "j6_strategy_reset",
    "token-source-degraded": "j9_measurement_recovery",
}


def dispatch_self_recover(
    *,
    slot: str,
    reason: str,
    evidence: str,
    mother_queue_path: Path | str,
    log_path: Path | str | None = None,
    now_ts: int | None = None,
) -> SelfRecoverResult:
    """REQ-F1 entry point. Routes to Group J handlers; exhaustion → MOTHER queue.
    NO Telegram / NO Slack / NO osascript / NO human-label gh issue.
    """
    if now_ts is None:
        now_ts = int(time.time())

    key = dedup_key(slot, reason, evidence)
    log_path = Path(log_path) if log_path else None

    # REQ-F1 step 2: 24h dedup
    if log_path is not None and log_path.exists():
        rows = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
        if is_duplicate(key, rows, now_ts):
            return SelfRecoverResult(status="deduplicated", handler=None)

    handler_name = _HANDLER_BY_REASON.get(reason)
    if handler_name is None:
        # Unknown reason — fall through to MOTHER queue (= another AI, NOT a human)
        _append_mother_queue(Path(mother_queue_path), slot, reason, evidence, now_ts)
        if log_path is not None:
            _append_log(log_path, slot, reason, evidence, key, "exhausted", now_ts)
        return SelfRecoverResult(status="exhausted", handler=None,
                                 details={"reason": "unknown-reason-routed-to-mother"})

    # Dispatch to the named handler. Handlers live as module-level functions; tests
    # monkeypatch them via "lib.group_j.j1_auto_login" etc.
    handler = globals().get(handler_name)
    if handler is None:
        _append_mother_queue(Path(mother_queue_path), slot, reason, evidence, now_ts)
        if log_path is not None:
            _append_log(log_path, slot, reason, evidence, key, "exhausted", now_ts)
        return SelfRecoverResult(status="exhausted", handler=handler_name,
                                 details={"reason": "handler-not-implemented"})

    result = handler(slot=slot, oauth_url=evidence) if handler_name == "j1_auto_login" \
        else handler(slot=slot, details=evidence)

    if log_path is not None:
        _append_log(log_path, slot, reason, evidence, key, result.status, now_ts)

    if result.status == "exhausted":
        _append_mother_queue(Path(mother_queue_path), slot, reason, evidence, now_ts)

    return result


# ────────────────────────────────────────────────────────────────────────
# Group J handler stubs.
# Production wires these to real recovery actions (camofox + Gmail OTP,
# git checkout + sig verify, firecrawl + auto-PR, model upgrade, etc.).
# Tests monkeypatch each function by name.
# ────────────────────────────────────────────────────────────────────────


def j1_auto_login(*, slot: str, oauth_url: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j1_auto_login",
                             details={"slot": slot, "url": oauth_url})


def j2_auto_rollback(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j2_auto_rollback",
                             details={"slot": slot, "details": details})


def j3_auto_research(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j3_auto_research",
                             details={"slot": slot, "details": details})


def j4_model_ladder(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j4_model_ladder",
                             details={"slot": slot, "details": details})


def j5_fresh_start(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j5_fresh_start",
                             details={"slot": slot, "details": details})


def j6_strategy_reset(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j6_strategy_reset",
                             details={"slot": slot, "details": details})


def j9_measurement_recovery(*, slot: str, details: str, **kw) -> SelfRecoverResult:
    return SelfRecoverResult(status="recovered", handler="j9_measurement_recovery",
                             details={"slot": slot, "details": details})


# ────────────────────────────────────────────────────────────────────────
# Persistence helpers
# ────────────────────────────────────────────────────────────────────────


def _append_log(log_path: Path, slot: str, reason: str, evidence: str,
                key: str, status: str, ts: int) -> None:
    row = {
        "ts": ts,
        "slot": slot,
        "reason": reason,
        "dedup_key": key,
        "normalized_evidence": normalize_evidence(evidence)[:200],
        "status": status,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_mother_queue(queue_path: Path, slot: str, reason: str,
                         evidence: str, ts: int) -> None:
    row = {
        "ts": ts,
        "slot": slot,
        "reason": reason,
        "evidence_truncated": evidence[:500],
        "status": "queued",
    }
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
