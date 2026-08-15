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

    def _delivery_unknown(self, body, *, owner="crashed-worker"):
        action = self.controller.claim(owner=owner, now=101, lease_seconds=300)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body=body,
            now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "fingerprint": "before",
                "seller_count": 0,
            },
            after={"status": "read_failed"},
            observed_at=104,
        )
        return action, intent

    def test_reconcile_duplicate_matches_close_terminal_already_delivered(self):
        # A21: >1 identical outgoing messages in the thread means we already
        # double-posted. The closure is terminal (already_delivered), never a
        # swallowed duplicate_detected counter, and never a resend.
        action, intent = self._delivery_unknown("identical progress message")
        reconciliation = self.controller.reconciliation_action_for_thread("42")

        result = self.controller.reconcile_observation(
            action=reconciliation,
            observation={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "seller_messages": [
                    {
                        "body_sha256": intent["outgoing_hash"],
                        "sent_at": "1970-01-01T00:01:44+00:00",
                    },
                    {
                        "body_sha256": intent["outgoing_hash"],
                        "sent_at": "1970-01-01T00:01:50+00:00",
                    },
                ],
                "last_sender": "seller",
            },
            observed_at=224,
        )

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(result["status"], "already_delivered")
        self.assertEqual(result["errors"], ["duplicate_outgoing_message"])
        self.assertEqual(stored["state"], "replied")
        self.assertIsNone(self.controller.reconciliation_action_for_thread("42"))
        closures = (self.root / "connector-outbox-closures.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        records = [json.loads(line) for line in closures]
        self.assertEqual(
            [record["closure"] for record in records], ["already_delivered"]
        )
        self.assertEqual(records[0]["thread_id"], "42")

    def test_reconcile_single_stale_match_closes_already_delivered(self):
        # The 588-reconcile_pending trap: the hash IS in the thread but the DOM
        # sent_at falls outside the strict click window, so the old code returned
        # unchanged forever. Content presence == delivered (idempotency key).
        action, intent = self._delivery_unknown("stale but delivered")
        reconciliation = self.controller.reconciliation_action_for_thread("42")

        result = self.controller.reconcile_observation(
            action=reconciliation,
            observation={
                "talkroom_id": "42",
                "url": self.queue_item["talkroom_url"],
                "seller_messages": [{
                    "body_sha256": intent["outgoing_hash"],
                    "sent_at": "1970-01-01T00:00:50+00:00",
                }],
                "last_sender": "seller",
            },
            observed_at=224,
        )

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(result["status"], "already_delivered")
        self.assertEqual(stored["state"], "replied")
        self.assertIsNone(self.controller.reconciliation_action_for_thread("42"))

    def test_failure_injection_unproven_quiescence_dead_letters_after_bounded_attempts(self):
        # A21 (c): executor crashed after click without quiescence proof. The old
        # code raised ExecutorStillActive forever (blind loop). New contract:
        # bounded unresolved passes, then the message moves to the DLQ and the
        # lane moves on. No blind retry: the action is never requeued.
        action = self.controller.claim(owner="crashed-worker", now=101, lease_seconds=300)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="delivery forever unknown",
            now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        absent = {
            "talkroom_id": "42",
            "url": self.queue_item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }
        limit = self.action_module.DLQ_AFTER_UNRESOLVED_ATTEMPTS

        statuses = []
        for index in range(limit):
            reconciliation = self.controller.reconciliation_action_for_thread("42")
            self.assertIsNotNone(reconciliation)
            outcome = self.controller.reconcile_observation(
                action=reconciliation,
                observation=absent,
                observed_at=300 + index,
            )
            statuses.append(outcome["status"])
            self.assertEqual(outcome["errors"], ["executor_quiescence_unproven"])

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(statuses[:-1], ["reconcile_pending"] * (limit - 1))
        self.assertEqual(statuses[-1], "dlq")
        self.assertIsNone(self.controller.reconciliation_action_for_thread("42"))
        self.assertEqual(self.controller.reconciliation_actions(), [])
        self.assertIsNone(self.controller.pending_action_for_thread("42"))
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertIsNone(stored["owner"])
        dlq = self.controller.outbox.dlq_actions()
        self.assertEqual(len(dlq), 1)
        self.assertEqual(dlq[0]["thread_id"], "42")
        self.assertEqual(dlq[0]["reason"], "executor_quiescence_unproven")
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            slot = connection.execute(
                "SELECT action_id,owner FROM connector_slots WHERE platform='coconala'"
            ).fetchone()
        self.assertIsNone(slot["action_id"])
        closures = (self.root / "connector-outbox-closures.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        records = [json.loads(line) for line in closures]
        self.assertEqual(records[-1]["closure"], "dlq")
        self.assertEqual(records[-1]["thread_id"], "42")

    def test_runaway_supersede_loop_is_reported_as_dlq_to_the_lane(self):
        # C1b anti-burn: once the action has spent its revision budget the
        # reconciliation must surface as a terminal dlq closure, not as another
        # "requeued" round that the lane will pay for again next pass.
        absent = {
            "talkroom_id": "42",
            "url": self.queue_item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }
        budget = self.outbox_module.MAX_REVISIONS_PER_ACTION
        clock = 200
        statuses = []
        for index in range(budget):
            action = self.controller.claim(
                owner=f"burn-{index}", now=clock, lease_seconds=300
            )
            intent = self.controller.prepare(
                action=action, queue_item=self.queue_item,
                outgoing_body=f"burned body {index}", now=clock + 1,
            )
            self.controller.authorize_click(intent=intent, now=clock + 2)
            self.controller.finalize(
                intent=intent,
                before={
                    "talkroom_id": "42",
                    "url": self.queue_item["talkroom_url"],
                    "fingerprint": "before",
                    "seller_count": 0,
                },
                after={"status": "read_failed"},
                observed_at=clock + 3,
            )
            reconciliation = self.controller.reconciliation_action_for_thread("42")
            self.assertIsNotNone(reconciliation)
            statuses.append(self.controller.reconcile_observation(
                action=reconciliation, observation=absent, observed_at=clock + 200,
            )["status"])
            clock += 400

        self.assertEqual(statuses[:-1], ["requeued"] * (budget - 1))
        self.assertEqual(statuses[-1], "dlq")
        self.assertEqual(
            self.controller.outbox.get_action(1)["revision"], budget
        )
        self.assertIsNone(self.controller.reconciliation_action_for_thread("42"))
        self.assertIsNone(self.controller.pending_action_for_thread("42"))
        dlq = self.controller.outbox.dlq_actions()
        self.assertEqual(len(dlq), 1)
        self.assertEqual(dlq[0]["reason"], "revision_budget_exhausted")

    def test_failure_injection_minute_truncated_sent_at_still_reaches_replied(self):
        # Live incident 2026-08-01 08:01 thread 93000006: Coconala renders
        # sent_at with minute resolution, so a message sent at :10 seconds shows
        # :00 and lands BEFORE click_started_at. The three-point read-back had
        # already proven delivery, yet the old finalize raised
        # "verified reply did not reach replied state" and crashed the lane.
        action = self.controller.claim(owner="worker-1", now=101, lease_seconds=60)
        intent = self.controller.prepare(
            action=action,
            queue_item=self.queue_item,
            outgoing_body="delivered in the same minute",
            now=102,
        )
        digest = intent["outgoing_hash"]
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
                # minute-truncated: epoch 100 < click_started_at 103
                "seller_sent_at": "1970-01-01T00:01:40+00:00",
                "last_sender": "seller",
            },
            observed_at=105,
        )

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(result["status"], "replied")
        self.assertTrue(result["verified"])
        self.assertEqual(stored["state"], "replied")
        self.assertIsNone(stored["owner"])
        self.assertEqual(stored["verified_outgoing_hash"], digest)

    def test_consistency_window_open_is_not_counted_toward_dlq(self):
        self._delivery_unknown("still inside the window")
        absent = {
            "talkroom_id": "42",
            "url": self.queue_item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }
        limit = self.action_module.DLQ_AFTER_UNRESOLVED_ATTEMPTS

        for index in range(limit + 2):
            reconciliation = self.controller.reconciliation_action_for_thread("42")
            self.assertIsNotNone(reconciliation)
            outcome = self.controller.reconcile_observation(
                action=reconciliation,
                observation=absent,
                observed_at=110 + index,
            )
            self.assertEqual(outcome, {
                "status": "reconcile_pending",
                "errors": ["consistency_window_open"],
            })

        self.assertIsNotNone(self.controller.reconciliation_action_for_thread("42"))
        self.assertEqual(self.controller.outbox.dlq_actions(), [])

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
