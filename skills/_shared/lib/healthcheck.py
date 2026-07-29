"""healthcheck — pure self-heal classifier + extractors.

Implements PROP-A-classify, PROP-A-oauth, PROP-A-hook-allowlist (all required:true).
Spec: __REPO_ROOT__/.vcsdd/features/earn-shared-skeleton/specs/behavioral-spec.md Group A.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    BACKOFF = "BACKOFF"
    TRUST_DIALOG = "TRUST_DIALOG"
    NOT_LOGGED_IN = "NOT_LOGGED_IN"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    HOOK_ERROR = "HOOK_ERROR"
    CRON_GONE = "CRON_GONE"
    TMUX_DEAD = "TMUX_DEAD"
    STALE = "STALE"
    STALE_FIRST_PASS = "STALE_FIRST_PASS"
    ALIVE_FRESH = "ALIVE_FRESH"


@dataclass(frozen=True)
class HealthcheckContext:
    slot: str
    pane_text: str
    has_session: bool
    last_pass_mtime: int | None
    last_start_mtime: int | None
    restart_log_entries: list[int]
    cron_has_slot_job: bool
    now_ts: int


_STALE_SECONDS = 90 * 60
_BACKOFF_WINDOW = 3600
_BACKOFF_CAP = 5
_API_RATE_LIMIT_RE = re.compile(r"API error · Retrying.*attempt (\d+)/10")


def classify(ctx: HealthcheckContext) -> Mode:
    """Walk the priority decision tree (spec: behavioral-spec.md table at REQ-A).

    Priority is more-specific (pane content / terminal states) before less-specific
    (timing / generic state). Returns EXACTLY ONE Mode per ctx (REQ-A9 mutex).
    """
    # 1. BACKOFF — terminal; even pane content can't override
    recent = [t for t in ctx.restart_log_entries if (ctx.now_ts - t) <= _BACKOFF_WINDOW]
    if len(recent) >= _BACKOFF_CAP:
        return Mode.BACKOFF

    # 2. TRUST_DIALOG (pane-content)
    if "Quick safety check" in ctx.pane_text and "trust" in ctx.pane_text:
        return Mode.TRUST_DIALOG

    # 3. NOT_LOGGED_IN (pane-content) — MUST outrank STALE (FIND-009 critical)
    if "Not logged in" in ctx.pane_text and "/login" in ctx.pane_text:
        return Mode.NOT_LOGGED_IN

    # 4. API_RATE_LIMIT (pane-content)
    m = _API_RATE_LIMIT_RE.search(ctx.pane_text)
    if m and int(m.group(1)) >= 5:
        return Mode.API_RATE_LIMIT

    # 5. HOOK_ERROR (pane-content)
    if (
        "PreToolUse:Bash hook error" in ctx.pane_text
        and "node:internal/modules/cjs/loader" in ctx.pane_text
    ):
        return Mode.HOOK_ERROR

    # 6. CRON_GONE (state)
    if ctx.has_session and not ctx.cron_has_slot_job:
        return Mode.CRON_GONE

    # 7. TMUX_DEAD (state)
    if not ctx.has_session:
        return Mode.TMUX_DEAD

    # 8. STALE (timing — last_pass exists and is old)
    if ctx.last_pass_mtime is not None and (ctx.now_ts - ctx.last_pass_mtime) >= _STALE_SECONDS:
        return Mode.STALE

    # 9. STALE_FIRST_PASS (timing — no last_pass, start is old; first-pass grace logic)
    if (
        ctx.last_pass_mtime is None
        and ctx.last_start_mtime is not None
        and (ctx.now_ts - ctx.last_start_mtime) >= _STALE_SECONDS
    ):
        return Mode.STALE_FIRST_PASS

    # 10. ALIVE_FRESH (default)
    return Mode.ALIVE_FRESH


# ── OAuth URL extraction (PROP-A-oauth, anti-phishing) ────────────────
# Spec REQ-A3 regex: anchored, host hard-coded, restricted charset.
# Search the pane line-by-line; only RETURN a URL that itself matches the
# anchored full-string regex (= no embedded-in-prefix smuggling).
_OAUTH_FULL_RE = re.compile(
    r"^https://claude\.com/cai/oauth/authorize\?[a-z0-9_=&%+\.\-]+$",
    re.IGNORECASE,
)
_OAUTH_CANDIDATE_RE = re.compile(
    r"(https://claude\.com/cai/oauth/authorize\?[a-z0-9_=&%+\.\-]+)",
    re.IGNORECASE,
)


def extract_oauth_url(pane_text: str) -> str | None:
    """Return an OAuth URL only if a line in pane_text contains one whose
    full-line content (after stripping surrounding whitespace) matches the
    anchored regex. Rejects subdomains, homographs, IP literals, javascript:,
    http://, path-traversal in query, extra path segments after authorize.
    """
    if not pane_text:
        return None
    for raw_line in pane_text.splitlines():
        line = raw_line.strip()
        # Exact full-line match preferred (= the canonical /login output format)
        if _OAUTH_FULL_RE.match(line):
            return line
        # Embedded-in-text rejected — anything BEFORE the https:// (other than
        # leading whitespace) is a smuggle vector (javascript:, data:, prefix tricks).
        # We only accept the URL if the whole line IS the URL.
    return None


# ── Hook module name extraction (PROP-A-hook-allowlist, anti-RCE) ─────
# Spec REQ-A5: strict npm regex AND allowlist required.
_HOOK_MODULE_RE = re.compile(r"Cannot find module '([^']*)'")
_NPM_NAME_RE = re.compile(r"^@?[a-z0-9][a-z0-9._\-/]*$")


def extract_hook_module_name(pane_text: str, allowlist: list[str]) -> dict:
    """Extract candidate module name from pane error + validate against npm
    name regex AND allowlist. Returns dict {name, valid, allowlisted}.
    """
    m = _HOOK_MODULE_RE.search(pane_text)
    if not m:
        return {"name": None, "valid": False, "allowlisted": False}
    candidate = m.group(1)
    # Reject anything containing null bytes / control chars / unusual punctuation up front.
    if "\x00" in candidate or any(ord(c) < 32 for c in candidate):
        return {"name": candidate, "valid": False, "allowlisted": False}
    valid = bool(_NPM_NAME_RE.match(candidate))
    # Even if regex matches, reject paths (../), URLs (http://), and CLI flag injections
    if valid and (candidate.startswith("-") or candidate.startswith(".") or "://" in candidate):
        valid = False
    allowlisted = valid and candidate in allowlist
    return {"name": candidate, "valid": valid, "allowlisted": allowlisted}
