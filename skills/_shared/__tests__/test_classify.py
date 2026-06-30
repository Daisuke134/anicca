"""PROP-A-classify (required:true, Tier 1) — healthcheck mutual exclusion + priority order.

Spec: behavioral-spec.md REQ-A1..A9 + priority table (10 modes).
classify(HealthcheckContext) → Mode enum. Pure. Deterministic. Mutually exclusive.
"""
import pytest

from lib.healthcheck import HealthcheckContext, Mode, classify  # FAIL until 2b


def _ctx(**overrides):
    base = dict(
        slot="gig",
        pane_text="",
        has_session=True,
        last_pass_mtime=1782800000,
        last_start_mtime=1782800000,
        restart_log_entries=[],
        cron_has_slot_job=True,
        now_ts=1782830000,
    )
    base.update(overrides)
    return HealthcheckContext(**base)


# ── happy / generic modes ──────────────────────────────────────────────
def test_alive_fresh_when_nothing_wrong():
    assert classify(_ctx()) == Mode.ALIVE_FRESH


def test_tmux_dead_when_no_session():
    assert classify(_ctx(has_session=False)) == Mode.TMUX_DEAD


def test_stale_when_last_pass_older_than_90min():
    assert classify(_ctx(now_ts=1782800000 + 91 * 60)) == Mode.STALE


def test_stale_first_pass_when_no_last_pass_but_start_old():
    assert (
        classify(_ctx(last_pass_mtime=None, now_ts=1782800000 + 91 * 60))
        == Mode.STALE_FIRST_PASS
    )


def test_cron_gone_when_session_alive_but_no_cron():
    assert classify(_ctx(cron_has_slot_job=False)) == Mode.CRON_GONE


# ── pane-content modes ────────────────────────────────────────────────
def test_trust_dialog_detected():
    assert (
        classify(_ctx(pane_text="Quick safety check: Is this a project you ... trust"))
        == Mode.TRUST_DIALOG
    )


def test_not_logged_in_detected():
    assert (
        classify(_ctx(pane_text="Not logged in · Please run /login"))
        == Mode.NOT_LOGGED_IN
    )


def test_hook_error_detected():
    assert (
        classify(
            _ctx(pane_text="PreToolUse:Bash hook error  node:internal/modules/cjs/loader:1458")
        )
        == Mode.HOOK_ERROR
    )


def test_api_rate_limit_detected_at_attempt_5():
    assert (
        classify(_ctx(pane_text="✻ API error · Retrying in 1s · attempt 5/10"))
        == Mode.API_RATE_LIMIT
    )


def test_api_rate_limit_NOT_detected_at_attempt_4():
    # boundary: N must be >= 5, not >= 4
    text = "✻ API error · Retrying in 1s · attempt 4/10"
    assert classify(_ctx(pane_text=text)) != Mode.API_RATE_LIMIT


# ── backoff is terminal (FIND-009 fix) ────────────────────────────────
def test_backoff_outranks_everything_when_5_restarts_in_1h():
    now = 1782830000
    log = [now - 100, now - 200, now - 300, now - 400, now - 500]
    # also has trust dialog AND not-logged-in AND stale — backoff still wins
    ctx = _ctx(
        pane_text="Not logged in · Please run /login\nQuick safety check: Is this a project you ... trust",
        last_pass_mtime=1782800000,
        now_ts=now,
        restart_log_entries=log,
    )
    assert classify(ctx) == Mode.BACKOFF


# ── PRIORITY: NOT_LOGGED_IN outranks STALE (FIND-009 critical) ────────
def test_not_logged_in_outranks_stale():
    """Critical: every logged-out slot WILL go stale; if STALE outranked,
    healthcheck would thrash-restart instead of surfacing the OAuth URL."""
    now = 1782830000
    ctx = _ctx(
        pane_text="Not logged in · Please run /login",
        last_pass_mtime=now - 120 * 60,  # 120 min ago (stale)
        now_ts=now,
    )
    assert classify(ctx) == Mode.NOT_LOGGED_IN


def test_trust_dialog_outranks_stale():
    now = 1782830000
    ctx = _ctx(
        pane_text="Quick safety check: Is this a project you ... trust",
        last_pass_mtime=now - 120 * 60,
        now_ts=now,
    )
    assert classify(ctx) == Mode.TRUST_DIALOG


# ── REQ-A9 mutual exclusion: classify returns EXACTLY one mode ────────
@pytest.mark.parametrize(
    "ctx_kwargs",
    [
        {"has_session": False},
        {"pane_text": "Not logged in · Please run /login"},
        {"pane_text": "Quick safety check: trust"},
        {"pane_text": "node:internal/modules/cjs/loader:1458"},
        {"pane_text": "API error · Retrying in 1s · attempt 7/10"},
        {"cron_has_slot_job": False},
        {"last_pass_mtime": 1782700000},  # very old
    ],
)
def test_classify_returns_a_member_of_mode_enum(ctx_kwargs):
    result = classify(_ctx(**ctx_kwargs))
    assert isinstance(result, Mode), f"got {type(result).__name__}, expected Mode"
