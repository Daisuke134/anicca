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
