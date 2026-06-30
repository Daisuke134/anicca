"""PROP-B4-killswitch (required:true, Tier 1) — INV-11 token kill-switch.

Spec: REQ-B4 — kill_switch_tripped(cum_cost_jpy, cum_earned_jpy, age_seconds, m=5, grace=7d).
Closes FIND-001 critical dimensional bug (raw tokens vs JPY).
"""
import pytest

from lib.roi import kill_switch_tripped  # FAIL until 2b


GRACE_S = 7 * 86400
HALF_S = 3 * 86400
POST_S = 8 * 86400


# ── FIND-001: brand-new slot is never killed on first pass ────────────
def test_brand_new_slot_with_zero_earned_NOT_killed_during_grace():
    """The exact failure mode FIND-001 critical was about: every new slot would
    trip kill-switch on first pass (jpy_earned=0) under the v1 spec."""
    assert kill_switch_tripped(cum_cost_jpy=1000.0, cum_earned_jpy=0, age_seconds=HALF_S) is False


def test_zero_earned_age_at_boundary_grace_minus_1s_NOT_killed():
    assert kill_switch_tripped(cum_cost_jpy=1000.0, cum_earned_jpy=0, age_seconds=GRACE_S - 1) is False


def test_zero_earned_just_past_grace_IS_killed():
    """After 7 days of zero earn and any cost > 0, slot is archived."""
    assert kill_switch_tripped(cum_cost_jpy=1.0, cum_earned_jpy=0, age_seconds=GRACE_S + 1) is True


# ── normal-operation trip condition ──────────────────────────────────
def test_cost_below_5x_earned_NOT_killed_past_grace():
    # cost=400, earned=100 → ratio=4 < 5 → still profitable-enough
    assert kill_switch_tripped(cum_cost_jpy=400.0, cum_earned_jpy=100, age_seconds=POST_S) is False


def test_cost_above_5x_earned_IS_killed_past_grace():
    # cost=501, earned=100 → ratio=5.01 > 5
    assert kill_switch_tripped(cum_cost_jpy=501.0, cum_earned_jpy=100, age_seconds=POST_S) is True


def test_cost_exactly_5x_earned_NOT_killed():
    """Boundary: strict > 5*earned, not >=."""
    assert kill_switch_tripped(cum_cost_jpy=500.0, cum_earned_jpy=100, age_seconds=POST_S) is False


# ── inside grace = never killed regardless of ratio ──────────────────
def test_during_grace_never_killed_even_huge_loss():
    assert (
        kill_switch_tripped(cum_cost_jpy=1_000_000.0, cum_earned_jpy=1, age_seconds=HALF_S)
        is False
    )


# ── multiplier param honored ─────────────────────────────────────────
def test_multiplier_param_is_honored():
    # m=10 → not killed at ratio=6
    assert (
        kill_switch_tripped(cum_cost_jpy=600.0, cum_earned_jpy=100, age_seconds=POST_S, multiplier=10)
        is False
    )


# ── ROUND-2-001 type-coherence guard ─────────────────────────────────
def test_inputs_are_both_in_jpy_units():
    """Both args are JPY amounts. Test asserts the function exists with the
    expected param names (= dimensional intent encoded in API)."""
    # signature inspection — ensures the function name maps inputs as JPY
    import inspect
    sig = inspect.signature(kill_switch_tripped)
    # spec REQ-B4 expects: cum_cost_jpy, cum_earned_jpy
    assert "cum_cost_jpy" in sig.parameters
    assert "cum_earned_jpy" in sig.parameters
