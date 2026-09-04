import importlib.util
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gig_reconcile_pending_dlq_test", ROOT / "scripts/connector_outbox.py",
)
assert SPEC and SPEC.loader
outbox_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outbox_module)


def test_reconcile_pending_action_dead_letters_after_five_consecutive_read_failures(tmp_path):
    """Measured 2026-09-04 on thread 10085794 (action 605): a CollectorUnhealthy
    raised by browser.read_before() happens BEFORE reconcile_observation runs, so
    reconcile_attempts never advances. With 'reconcile_pending' excluded from the
    dead-letter-eligible states, and an older already-replied action on the same
    thread (smaller action_id, dlq_at still NULL) outranking it in the action
    lookup, the consecutive-failure streak climbed past 30 with no way to stop --
    every poll_seconds, forever. Both must be fixed: which action is inspected,
    and whether reconcile_pending is eligible.
    """
    database = tmp_path / "outbox.sqlite3"
    manifest = ROOT / "config/connectors/coconala.json"
    outbox = outbox_module.ConnectorOutbox(database, manifest)

    old_replied = outbox.enqueue(
        event_key=outbox_module.coconala_inbox_event_key("10085794", "a" * 64),
        thread_id="10085794",
        thread_url="https://coconala.com/mypage/direct_message/10085794",
        observed_at=1000,
    )
    with sqlite3.connect(database) as connection:
        # An old, already-answered action on the same thread: terminal state,
        # dlq_at never set (replied actions do not get quarantined), smallest
        # action_id -- exactly what outranked the live action before the fix.
        connection.execute(
            "UPDATE connector_actions SET state='replied' WHERE action_id=?",
            (old_replied["action_id"],),
        )

    stuck = outbox.enqueue(
        event_key=outbox_module.coconala_inbox_event_key("10085794", "b" * 64),
        thread_id="10085794",
        thread_url="https://coconala.com/mypage/direct_message/10085794",
        observed_at=2000,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE connector_actions SET state='reconcile_pending' WHERE action_id=?",
            (stuck["action_id"],),
        )

    result = None
    for attempt in range(5):
        result = outbox.record_thread_failure(
            thread_id="10085794",
            error_class="CollectorUnhealthy:collector_unhealthy:dm_attachment_message_identity_changed",
            now=3000 + attempt,
            dead_letter_after=5,
        )

    assert result["consecutive"] == 5
    assert result["action_id"] == stuck["action_id"]
    assert result["dead_lettered"] is True
    assert result["not_dead_lettered_because"] is None

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT state, dlq_at FROM connector_actions WHERE action_id=?",
            (stuck["action_id"],),
        ).fetchone()
    # dead-lettering never invents a delivery outcome: state is untouched.
    assert row["state"] == "reconcile_pending"
    assert row["dlq_at"] == 3004
