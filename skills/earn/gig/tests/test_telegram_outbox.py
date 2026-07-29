import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "telegram_outbox.py"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_outbox", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load telegram_outbox")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TelegramOutboxTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "telegram.sqlite3"
        self.module = load_module()
        self.outbox = self.module.TelegramOutbox(self.database)

    def tearDown(self):
        self.temp.cleanup()

    def enqueue(self, key="reply:42:event-1", message="⚡ reply verified room=42"):
        return self.outbox.enqueue(
            event_key=key, kind="reply_verified", message=message, created_at=100,
        )

    def test_enqueue_is_idempotent_but_payload_mismatch_fails_closed(self):
        first = self.enqueue()
        second = self.enqueue()

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertEqual(self.outbox.counts(), {"pending": 1})
        with self.assertRaisesRegex(Exception, "event payload mismatch"):
            self.enqueue(message="changed")

    def test_successful_dispatch_calls_provider_once_and_persists_message_id(self):
        self.enqueue()
        calls = []

        first = self.module.dispatch_one(
            self.outbox,
            owner="telegram-worker",
            now=lambda: 101 + len(calls),
            transport=lambda message: calls.append(message) or "tg-9001",
        )
        second = self.module.dispatch_one(
            self.outbox,
            owner="telegram-worker-2",
            now=lambda: 110,
            transport=lambda message: calls.append(message) or "duplicate",
        )

        self.assertEqual(first["status"], "sent")
        self.assertEqual(first["message_id"], "tg-9001")
        self.assertEqual(second["status"], "queue_empty")
        self.assertEqual(calls, ["⚡ reply verified room=42"])

    def test_transport_failure_is_delivery_unknown_and_never_blind_retried(self):
        self.enqueue()
        calls = []

        first = self.module.dispatch_one(
            self.outbox,
            owner="telegram-worker",
            now=iter((101, 102, 103)).__next__,
            transport=lambda message: calls.append(message) or (_ for _ in ()).throw(RuntimeError("ack lost")),
        )
        second = self.module.dispatch_one(
            self.outbox,
            owner="telegram-worker-2",
            now=lambda: 200,
            transport=lambda message: calls.append(message) or "duplicate",
        )

        self.assertEqual(first["status"], "delivery_unknown")
        self.assertEqual(second["status"], "queue_empty")
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.outbox.counts(), {"delivery_unknown": 1})

    def test_expired_send_started_is_quarantined_unknown_not_retried(self):
        self.enqueue()
        action = self.outbox.claim(owner="crashed", now=101, lease_seconds=10)
        self.outbox.mark_send_started(
            action["report_id"], owner="crashed",
            fencing_token=action["fencing_token"], now=102,
        )

        recovered = self.outbox.recover_expired(now=112)
        calls = []
        result = self.module.dispatch_one(
            self.outbox,
            owner="new-worker",
            now=lambda: 113,
            transport=lambda message: calls.append(message) or "duplicate",
        )

        self.assertEqual(recovered, 1)
        self.assertEqual(result["status"], "queue_empty")
        self.assertEqual(calls, [])
        self.assertEqual(self.outbox.counts(), {"delivery_unknown": 1})

    def test_provider_receipt_reconciles_unknown_without_resending(self):
        message = "⚡ reply verified room=42"
        action = self.enqueue(message=message)
        claimed = self.outbox.claim(owner="worker", now=101, lease_seconds=10)
        self.outbox.mark_send_started(
            claimed["report_id"], owner="worker",
            fencing_token=claimed["fencing_token"], now=102,
        )
        self.outbox.mark_delivery_unknown(
            claimed["report_id"], owner="worker",
            fencing_token=claimed["fencing_token"],
            error_class="executor_lost_after_ack", now=103,
        )
        receipt_dir = Path(self.temp.name) / "receipts"
        receipt_dir.mkdir()
        event_digest = hashlib.sha256(action["event_key"].encode("utf-8")).hexdigest()
        message_digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        (receipt_dir / f"{event_digest}.json").write_text(json.dumps({
            "version": 1,
            "event_key": action["event_key"],
            "target": "8547730585",
            "message_sha256": message_digest,
            "message_id": "tg-9001",
            "provider_acked_at_epoch_ms": 102500,
        }))
        calls = []

        result = self.outbox.reconcile_receipts(
            receipt_dir=receipt_dir,
            target="8547730585",
            now=104,
        )
        dispatch = self.module.dispatch_one(
            self.outbox,
            owner="new-worker",
            now=lambda: 105,
            transport=lambda value: calls.append(value) or "duplicate",
        )

        self.assertEqual(result, {"reconciled": 1, "invalid": 0})
        self.assertEqual(dispatch["status"], "queue_empty")
        self.assertEqual(calls, [])
        self.assertEqual(self.outbox.counts(), {"sent": 1})

    def test_receipt_with_wrong_message_hash_stays_unknown(self):
        action = self.enqueue()
        claimed = self.outbox.claim(owner="worker", now=101, lease_seconds=10)
        self.outbox.mark_send_started(
            claimed["report_id"], owner="worker",
            fencing_token=claimed["fencing_token"], now=102,
        )
        self.outbox.mark_delivery_unknown(
            claimed["report_id"], owner="worker",
            fencing_token=claimed["fencing_token"],
            error_class="executor_lost_after_ack", now=103,
        )
        receipt_dir = Path(self.temp.name) / "receipts"
        receipt_dir.mkdir()
        event_digest = hashlib.sha256(action["event_key"].encode("utf-8")).hexdigest()
        (receipt_dir / f"{event_digest}.json").write_text(json.dumps({
            "version": 1,
            "event_key": action["event_key"],
            "target": "8547730585",
            "message_sha256": "0" * 64,
            "message_id": "tg-wrong",
            "provider_acked_at_epoch_ms": 102500,
        }))

        result = self.outbox.reconcile_receipts(
            receipt_dir=receipt_dir,
            target="8547730585",
            now=104,
        )

        self.assertEqual(result, {"reconciled": 0, "invalid": 1})
        self.assertEqual(self.outbox.counts(), {"delivery_unknown": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
