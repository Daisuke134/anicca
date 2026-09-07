"""A failure reported as a type name is not diagnosable.

This lane spent six days emitting `storefront_offer:TimeoutError` and
`storefront_offer:TargetClosedError` with nothing to act on, while the sibling Coconala lane
was having the same class of browser failure fixed by name. The receipt now carries what
actually went wrong alongside the operator-facing code, which stays unchanged so nothing
downstream that switches on `error` has to move.
"""
from __future__ import annotations

import re
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "scripts" / "storefront_offer.py").read_text(
    encoding="utf-8")
# Two handlers share that opening line; the one under test is the run-level handler that
# reports to stderr, not the earlier per-step one.
HANDLER = SOURCE[SOURCE.index('print(f"storefront_offer:{type(error).__name__}') - 400:][:1200]


def test_the_stderr_line_carries_the_message_not_only_the_type():
    assert 'str(error)[:400]' in HANDLER


def test_the_result_carries_the_failure_for_a_reader_of_the_receipt():
    assert '"failure"' in HANDLER


def test_the_operator_facing_error_code_is_unchanged():
    # Anything switching on `error` must keep working.
    assert '"account_lock_busy"' in HANDLER
    assert '"offer_unavailable"' in HANDLER


def test_the_lock_busy_branch_still_decides_on_the_type():
    assert '"LockBusy" in type(error).__name__' in HANDLER


def test_the_message_is_bounded():
    # An unbounded exception string can carry a page dump into a log line.
    assert re.search(r"str\(error\)\[:\d+\]", HANDLER)
