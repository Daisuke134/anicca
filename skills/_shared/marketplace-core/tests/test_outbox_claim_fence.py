"""A reclaimed message must not be resolvable by the worker that lost it.

reclaim_stale exists because an abandoned 'sending' claim stops the queue entirely and silently —
measured 2026-09-05, three of them blocked every later CrowdWorks report. But returning the row to
pending hands it to a second worker while the first may only be slow, not dead. Without a fence the
slow worker can still resolve the row and overwrite the live worker's record with the result of a
send nobody is tracking.

The Coconala outbox has fenced this since it was written (state + owner + fencing token + lease).
The shared outbox did not, which is the reason nothing should have been migrated onto it yet.

Run: python3 -m pytest skills/_shared/marketplace-core/tests/test_outbox_claim_fence.py
"""

import importlib.util
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


outbox = _load("fence_test_outbox", SCRIPTS / "telegram_outbox.py")


def _reclaimed(database: Path):
    """Drive the real race: claim, abandon, reclaim, re-claim. Returns (stale, live)."""
    outbox.enqueue(database, event_key="k", message="one report",
                   created_at="2026-09-06T11:59:00+00:00")
    stale = outbox.claim_next(database)
    # Backdate the claim so reclaim_stale sees the abandonment it is written for, rather than
    # weakening the window and testing something the production window would never do.
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE telegram_outbox SET claimed_at = ? WHERE event_key = 'k'",
            ("2026-09-06T00:00:00+00:00",),
        )
    stale = replace(stale, claimed_at="2026-09-06T00:00:00+00:00")
    assert outbox.reclaim_stale(database, older_than_seconds=900) == 1
    live = outbox.claim_next(database)
    assert live is not None and live.claimed_at != stale.claimed_at
    return stale, live


def test_stale_worker_cannot_mark_delivered(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    stale, live = _reclaimed(database)

    with pytest.raises(outbox.StaleClaim):
        outbox.mark_delivered(database, "k", "stale-id", "2026-09-06T12:00:00+00:00",
                              claimed_at=stale.claimed_at)

    # The live worker still owns the row and can resolve it.
    outbox.mark_delivered(database, "k", "live-id", "2026-09-06T12:00:01+00:00",
                          claimed_at=live.claimed_at)
    item = outbox.list_items(database)[0]
    assert (item.status, item.provider_message_id) == ("delivered", "live-id")


def test_stale_worker_cannot_return_the_row_to_pending(tmp_path):
    """The dangerous one: a stale pre-send failure would re-queue a message already in flight."""
    database = tmp_path / "outbox.sqlite3"
    stale, _live = _reclaimed(database)

    with pytest.raises(outbox.StaleClaim):
        outbox.mark_pre_send_failed(database, "k", "process_not_started",
                                    claimed_at=stale.claimed_at)
    assert outbox.list_items(database)[0].status == "sending"


def test_stale_worker_cannot_quarantine_the_row(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    stale, _live = _reclaimed(database)

    with pytest.raises(outbox.StaleClaim):
        outbox.mark_delivery_uncertain(database, "k", "receipt_missing",
                                       claimed_at=stale.claimed_at)
    assert outbox.list_items(database)[0].status == "sending"


def test_callers_that_pass_no_claim_are_unchanged(tmp_path):
    """The fence is opt-in so migrating lanes one at a time cannot break the ones not yet moved."""
    database = tmp_path / "outbox.sqlite3"
    outbox.enqueue(database, event_key="k", message="one report",
                   created_at="2026-09-06T11:59:00+00:00")
    outbox.claim_next(database)
    outbox.mark_delivered(database, "k", "id-1", "2026-09-06T12:00:00+00:00")
    assert outbox.list_items(database)[0].status == "delivered"
