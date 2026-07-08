"""Phase 5 formal hardening — property-based (Hypothesis) tests for the PURE functions of
hl-realized-pnl (verification-architecture.md's "Purity boundary map" PURE rows: fills.py's
three functions + reconcile.py's plan_batch).

This file is a VERIFICATION HARNESS, not a production test file — it lives under
.vcsdd/features/hl-realized-pnl/verification/proof-harnesses/, not under
skills/earn/hl-trade/tests/. It imports the REAL, unmodified worktree modules by inserting the
worktree's lib/ directory onto sys.path (same technique as tests/conftest.py, pointed at an
absolute path since this file is outside that package).

Read-only, no network, no filesystem writes to anything but Hypothesis's own example database
(none configured here) — fixture/generated data only, mirrors the "Purity test rule" in
verification-architecture.md.

Run with the same interpreter used for the rest of Phase 5 (a scratch venv with
hyperliquid-python-sdk + hypothesis installed, since fills.py/reconcile.py themselves don't need
the SDK but the sibling test-collection environment does for hl.py-adjacent tests):

  <scratch-venv>/bin/python3 -m pytest \
      .vcsdd/features/hl-realized-pnl/verification/proof-harnesses/test_properties.py -v
"""
from __future__ import annotations

import os
import sys

_WORKTREE_LIB = "/Users/operator/anicca/.worktrees/hl-realized-pnl/skills/earn/hl-trade/lib"
if _WORKTREE_LIB not in sys.path:
    sys.path.insert(0, _WORKTREE_LIB)

from hypothesis import given, settings, strategies as st  # noqa: E402

from fills import compute_realized_pnl, is_unprocessable, select_close_fills  # noqa: E402
from reconcile import plan_batch  # noqa: E402


# ---------------------------------------------------------------------------------------------
# PROP-001 (REQ-B1): compute_realized_pnl — net_usdc == closed_pnl - fee, ALWAYS, for any float
# pair (not just the three fixture cases test_fills.py hand-picks).
# ---------------------------------------------------------------------------------------------

_finite_float = st.floats(
    min_value=-1_000_000, max_value=1_000_000, allow_nan=False, allow_infinity=False
)


@settings(max_examples=500)
@given(closed_pnl=_finite_float, fee=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False))
def test_prop001_net_usdc_always_equals_closed_pnl_minus_fee(closed_pnl, fee):
    r = compute_realized_pnl(closed_pnl, fee)
    assert abs(r["net_usdc"] - (closed_pnl - fee)) < 1e-6
    # earn/cost split invariant: exactly one of the two branches fires, never both partially.
    if closed_pnl > 0:
        assert r["earn_usdc"] == closed_pnl
        assert r["cost_usdc"] == fee
    else:
        assert r["earn_usdc"] == 0
        assert r["cost_usdc"] == fee + (-closed_pnl)
    # cost_usdc is never negative when fee >= 0 (the domain the live HL API always supplies).
    assert r["cost_usdc"] >= 0


# ---------------------------------------------------------------------------------------------
# PROP-002 / PROP-002b (REQ-B2/REQ-B8): select_close_fills — inclusive boundary, zero-pnl
# exclusion, ascending sort, for RANDOM fill sets (not just the hand-picked 3-fill fixtures).
# ---------------------------------------------------------------------------------------------

_fill_strategy = st.fixed_dictionaries({
    "time": st.integers(min_value=0, max_value=10_000),
    "tid": st.integers(min_value=1, max_value=10_000),
    "closedPnl": st.one_of(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False).map(str),
        st.just("0"), st.just("0.0"),
    ),
})


@settings(max_examples=300)
@given(fills=st.lists(_fill_strategy, min_size=0, max_size=25), since_time_ms=st.integers(min_value=0, max_value=10_000))
def test_prop002_select_close_fills_output_is_exactly_time_ge_since_and_nonzero_pnl(fills, since_time_ms):
    result = select_close_fills(fills, since_time_ms)

    # (a) every returned fill satisfies BOTH predicates the spec claims are the filter.
    for f in result:
        assert f["time"] >= since_time_ms
        assert float(f["closedPnl"]) != 0

    # (b) nothing eligible was silently dropped: recompute the expected set independently and
    #     compare as multisets of `tid` (order is checked separately in (c)).
    expected_tids = sorted(
        f["tid"] for f in fills if f["time"] >= since_time_ms and float(f["closedPnl"]) != 0
    )
    assert sorted(f["tid"] for f in result) == expected_tids

    # (c) ascending sort by time, regardless of input order (PROP-002's sort requirement).
    times = [f["time"] for f in result]
    assert times == sorted(times)


@settings(max_examples=200)
@given(t=st.integers(min_value=0, max_value=10_000), since_time_ms=st.integers(min_value=0, max_value=10_000))
def test_prop002b_boundary_is_inclusive_for_any_tied_timestamp(t, since_time_ms):
    """A single fill with time==since_time_ms and a nonzero closedPnl must be INCLUDED —
    generalizes the hand-picked tid=1/tid=2 fixture in test_fills.py to any tied value."""
    fills = [{"time": since_time_ms, "tid": 1, "closedPnl": "1.5"}]
    result = select_close_fills(fills, since_time_ms)
    assert len(result) == 1, "time == since_time_ms must be INCLUSIVE, not exclusive"


# ---------------------------------------------------------------------------------------------
# PROP-004/PROP-005 (REQ-B4): plan_batch — stop-index + no-gap invariants for RANDOM candidate
# lists (unprocessable fills, already-recorded tids, well-formed fills, in any order).
# ---------------------------------------------------------------------------------------------

_maybe_bad_candidate = st.fixed_dictionaries({
    "time": st.integers(min_value=0, max_value=10_000),
    "tid": st.integers(min_value=1, max_value=50),
    "closedPnl": st.one_of(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False).map(str), st.just("garbage")),
    "fee": st.one_of(st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False).map(str), st.just("garbage")),
})


@settings(max_examples=300)
@given(
    candidates=st.lists(_maybe_bad_candidate, min_size=0, max_size=15),
    already_recorded=st.sets(st.integers(min_value=1, max_value=50), max_size=10),
)
def test_prop004_005_plan_batch_stop_index_and_no_gap_invariants(candidates, already_recorded):
    plan = plan_batch(candidates, already_recorded)
    steps = plan["steps"]
    stop_index = plan["stop_index"]

    if stop_index is None:
        # nothing unprocessable (among not-already-recorded fills) was ever hit: every
        # candidate produced exactly one step, in the SAME order.
        assert len(steps) == len(candidates)
        for i, step in enumerate(steps):
            assert step["fill"] == candidates[i]
    else:
        # exactly `stop_index` steps were produced (one per index BEFORE the halting fill);
        # nothing at or after stop_index is represented in `steps` (REQ-B4.2's "no gap" rule —
        # the unprocessable fill itself, and everything after it, is truly untouched, not
        # silently skipped-and-continued).
        assert len(steps) == stop_index
        assert is_unprocessable(candidates[stop_index])
        assert candidates[stop_index].get("tid") not in already_recorded
        for i, step in enumerate(steps):
            assert step["fill"] == candidates[i]

    # every step's action correctly reflects tid membership in already_recorded_tids —
    # dedup (REQ-B4.1) is never confused with "record".
    for step in steps:
        tid = step["fill"].get("tid")
        if tid in already_recorded:
            assert step["action"] == "skip_duplicate"
        else:
            assert step["action"] == "record"
            assert not is_unprocessable(step["fill"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
