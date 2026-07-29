import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
ACTION_SCRIPT = SCRIPTS / "reply_action.py"
OUTBOX_SCRIPT = SCRIPTS / "connector_outbox.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplyActionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
        self.outbox_module = load(OUTBOX_SCRIPT, "reply_action_outbox_fixture")
        outbox = self.outbox_module.ConnectorOutbox(self.database, self.manifest)
        outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key("42", "message-1"),
            thread_id="42",
            thread_url="https://coconala.com/mypage/direct_message/42",
            observed_at=100,
        )
        self.action_module = load(ACTION_SCRIPT, "reply_action_under_test")
        self.controller = self.action_module.ReplyActionController(self.database, self.manifest)
        self.queue_item = {
            "event_key": "coconala:message:v1:42:message-1",
            "talkroom_id": "42",
            "talkroom_url": "https://coconala.com/mypage/direct_message/42",
            "origin_at": "1970-01-01T00:01:40+00:00",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_claim_prepare_authorize_and_matching_ground_truth_replies_once(self):
        action = self.controller.claim(owner="worker-1", now=101, lease_seconds=60)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="  bounded reply  ",
            now=102,
        )
        digest = hashlib.sha256(b"bounded reply").hexdigest()
        self.assertEqual(intent["outgoing_hash"], digest)
        self.assertNotIn("bounded reply", json.dumps(intent))
        self.controller.authorize_click(intent=intent, now=103)
        result = self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "fingerprint": "before",
                "seller_count": 1,
            },
            after={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "fingerprint": "after",
                "seller_count": 2,
                "seller_message_hashes": [digest],
                "seller_sent_at": "1970-01-01T00:01:44+00:00",
                "last_sender": "seller",
            },
            observed_at=105,
        )

        self.assertEqual(result["status"], "replied")
        self.assertEqual(self.controller.outbox.get_action(action["action_id"])["state"], "replied")
        with sqlite3.connect(self.database) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn("bounded reply", dump)

    def test_proven_pre_click_failure_requeues_without_send(self):
        action = self.controller.claim(owner="worker-1", now=101, lease_seconds=60)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="safe retry body",
            now=102,
        )

        recovered = self.controller.pre_click_failure(intent=intent, now=103)

        self.assertEqual(recovered["state"], "pending")
        self.assertIsNone(recovered["owner"])
        self.assertEqual(recovered["revision"], 2)

    def test_post_click_read_failure_is_reconcile_pending_not_blind_retry(self):
        action = self.controller.claim(owner="worker-1", now=101, lease_seconds=60)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="sent but ack missing",
            now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)

        result = self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "fingerprint": "before",
                "seller_count": 1,
            },
            after={"status": "read_failed"},
            observed_at=104,
        )

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertIsNone(stored["owner"])
        self.assertIsNone(self.controller.claim(owner="worker-2", now=105, lease_seconds=60))

    def test_explicit_server_rejection_blocks_after_authoritative_absence(self):
        action = self.controller.claim(owner="worker-1", now=101, lease_seconds=60)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="server rejected body",
            now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        result = self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "fingerprint": "before",
                "seller_count": 0,
            },
            after={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "seller_count": 0,
                "last_sender": "buyer",
                "send_network": [{
                    "method": "POST",
                    "path": "/mypage/direct_message_ajax/42",
                    "outcome": "finished",
                    "status": 200,
                }],
                "browser_error_code": "submit_rejected_sending_unavailable",
            },
            observed_at=104,
        )
        self.assertEqual(result["status"], "reconcile_pending")

        reconciliation = self.controller.reconciliation_action_for_thread("42")
        blocked = self.controller.reconcile_observation(
            action=reconciliation,
            observation={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "seller_messages": [],
                "last_sender": "buyer",
            },
            observed_at=224,
        )
        self.assertEqual(blocked, {
            "status": "blocked",
            "errors": ["submit_rejected_sending_unavailable"],
        })
        self.assertEqual(
            self.controller.outbox.get_action(action["action_id"])["state"],
            "blocked",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
