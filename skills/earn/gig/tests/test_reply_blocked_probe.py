import importlib.util
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gig_blocked_probe_outbox_test", ROOT / "scripts/connector_outbox.py",
)
assert SPEC and SPEC.loader
outbox_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outbox_module)


def test_sending_unavailable_action_remains_officially_probeable_at_attempt_seven(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    outbox = outbox_module.ConnectorOutbox(
        database, ROOT / "config/connectors/coconala.json",
    )
    action = outbox.enqueue(
        event_key=outbox_module.coconala_inbox_event_key("90001", "a" * 64),
        thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=1000,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE connector_actions SET state='blocked',revive_attempts=7 WHERE action_id=?",
            (action["action_id"],),
        )
        connection.execute(
            """INSERT INTO connector_intents
               (action_id,revision,outgoing_hash,owner_id,fencing_token,state,created_at,
                rejection_code,outgoing_body)
               VALUES(?,1,?,'test-owner',1,'superseded',1000,
                      'submit_rejected_sending_unavailable','body')""",
            (action["action_id"], "b" * 64),
        )

    candidates = outbox.blocked_targeted_actions()

    assert [item["action_id"] for item in candidates] == [action["action_id"]]


def test_authoritative_absence_at_attempt_cap_closes_without_another_day_wait(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    outbox = outbox_module.ConnectorOutbox(
        database, ROOT / "config/connectors/coconala.json",
    )
    action = outbox.enqueue(
        event_key=outbox_module.coconala_inbox_event_key("90001", "a" * 64),
        thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=1000,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            """UPDATE connector_actions
               SET state='reconcile_pending',revive_attempts=8 WHERE action_id=?""",
            (action["action_id"],),
        )
        connection.execute(
            """INSERT INTO connector_intents
               (action_id,revision,outgoing_hash,owner_id,fencing_token,state,created_at,
                click_started_at,executor_quiesced_at,executor_quiesced_by,
                rejection_code,outgoing_body)
               VALUES(?,1,?,'test-owner',1,'reconcile_pending',1000,1000,1001,'owner',
                      'submit_rejected_sending_unavailable','body')""",
            (action["action_id"], "b" * 64),
        )

    stored = outbox.reconcile(
        int(action["action_id"]),
        thread_url="https://coconala.com/mypage/direct_message/90001",
        outgoing_hash="b" * 64,
        seller_sent_at=None,
        last_sender="buyer",
        observed_at=2000,
        authoritative_absent=True,
    )

    assert stored["dlq_at"] == 2000
    closures = outbox.closed_actions()
    assert closures[0]["reason"] == (
        "revive_attempts_exhausted:submit_rejected_sending_unavailable"
    )


def test_already_blocked_attempt_cap_is_terminal_before_backoff(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    outbox = outbox_module.ConnectorOutbox(
        database, ROOT / "config/connectors/coconala.json",
    )
    action = outbox.enqueue(
        event_key=outbox_module.coconala_inbox_event_key("90001", "a" * 64),
        thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=1000,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            """UPDATE connector_actions SET state='blocked',revive_attempts=8,
               updated_at=2000 WHERE action_id=?""",
            (action["action_id"],),
        )
        connection.execute(
            """INSERT INTO connector_intents
               (action_id,revision,outgoing_hash,owner_id,fencing_token,state,created_at,
                rejection_code,outgoing_body)
               VALUES(?,1,?,'test-owner',1,'superseded',1000,
                      'submit_rejected_sending_unavailable','body')""",
            (action["action_id"], "b" * 64),
        )

    plan = outbox.blocked_revive_plan(now=2001)

    assert plan[0]["decision"] == "dlq"
    assert plan[0]["reason"] == (
        "revive_attempts_exhausted:submit_rejected_sending_unavailable"
    )
