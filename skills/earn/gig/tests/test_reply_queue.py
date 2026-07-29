import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reply_queue.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reply_queue", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reply_queue")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplyQueueTest(unittest.TestCase):
    def test_buyer_last_uncontracted_message_becomes_p1_with_deadlines(self):
        reply_queue = load_module()
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/mypage/direct_message/4201?token=secret",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-22T00:00:00+00:00",
                "message_id": "msg-7",
                "buyer": "must-not-leak",
                "raw_message": "must-not-leak",
            }],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["items"], [{
            "platform": "coconala",
            "priority": "P1",
            "event_type": "buyer_message",
            "event_key": "coconala:message:v1:4201:msg-7",
            "coordination_key": "coconala:4201",
            "covered_event_keys": ["coconala:message:v1:4201:msg-7"],
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "detected_at": "2026-07-22T00:04:00+00:00",
            "reply_due_at": "2026-07-22T00:14:00+00:00",
            "warning_at": "2026-07-22T00:15:00+00:00",
            "breach_at": "2026-07-22T00:30:00+00:00",
            "sla_status": "on_time",
            "next_action": "reply",
        }])
        self.assertNotIn("must-not-leak", str(result))

    def test_paid_order_talkroom_is_excluded_from_speedy_lane(self):
        reply_queue = load_module()
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [{"talkroom_id": "4201", "status": "open"}],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/talkrooms/4201",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-22T00:00:00+00:00",
                "message_id": "msg-paid",
            }],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(result, {"status": "queue_empty", "errors": [], "items": []})

    def test_explicit_contracted_conversation_is_excluded_without_order_join(self):
        reply_queue = load_module()
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/talkrooms/4201",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-22T00:00:00+00:00",
                "message_id": "msg-paid",
                "contracted": True,
            }],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(result, {"status": "queue_empty", "errors": [], "items": []})

    def test_actionable_row_without_stable_identity_is_unhealthy_not_silently_dropped(self):
        reply_queue = load_module()
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/talkrooms/4201",
                "last_message_side": "buyer",
                "reply_required": True,
            }],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(result["status"], "collector_unhealthy")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["errors"], ["inquiry:4201:missing_buyer_sent_at"])

    def test_message_without_platform_id_uses_fixed_ordinal_and_sha256_identity(self):
        reply_queue = load_module()
        digest = "a" * 64
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/talkrooms/4201",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-22T00:00:00+00:00",
                "stable_ordinal": 3,
                "message_sha256": digest,
            }],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            result["items"][0]["event_key"],
            f"coconala:fallback:v1:4201:1784678400:3:sha256_v1:{digest}",
        )

    def test_same_thread_events_coalesce_and_threads_sort_oldest_first(self):
        reply_queue = load_module()

        def inquiry(room_id, message_id, sent_at):
            return {
                "talkroom_id": room_id,
                "talkroom_url": f"https://coconala.com/talkrooms/{room_id}",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": sent_at,
                "message_id": message_id,
            }

        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [
                inquiry("4201", "msg-2", "2026-07-22T00:02:00+00:00"),
                inquiry("4202", "msg-old", "2026-07-21T23:59:00+00:00"),
                inquiry("4201", "msg-1", "2026-07-22T00:00:00+00:00"),
                inquiry("4201", "msg-1", "2026-07-22T00:00:00+00:00"),
            ],
        }

        result = reply_queue.build_queue(
            snapshot,
            now=datetime(2026, 7, 22, 0, 4, tzinfo=timezone.utc),
        )

        self.assertEqual([item["talkroom_id"] for item in result["items"]], ["4202", "4201"])
        room = result["items"][1]
        self.assertEqual(room["event_key"], "coconala:message:v1:4201:msg-1")
        self.assertEqual(room["covered_event_keys"], [
            "coconala:message:v1:4201:msg-1",
            "coconala:message:v1:4201:msg-2",
        ])

    def test_build_cli_writes_owner_only_queue_for_gig_pass_integration(self):
        snapshot = {
            "captured_at": "2026-07-22T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/talkrooms/4201",
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-22T00:00:00+00:00",
                "message_id": "msg-7",
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot_path = root / "snapshot.json"
            output_path = root / "reply-queue.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

            completed = subprocess.run([
                sys.executable,
                str(SCRIPT),
                "build",
                "--snapshot", str(snapshot_path),
                "--now", "2026-07-22T00:04:00+00:00",
                "--output", str(output_path),
            ], capture_output=True, text=True, check=False)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["status"], "ready")
            self.assertEqual(os.stat(output_path).st_mode & 0o777, 0o600)

    def test_enqueue_cli_persists_typed_events_once_across_repeated_loops(self):
        queue = {
            "status": "ready",
            "errors": [],
            "items": [{
                "event_key": "coconala:message:v1:4201:msg-7",
                "covered_event_keys": ["coconala:message:v1:4201:msg-7"],
                "talkroom_id": "4201",
                "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
                "detected_at": "2026-07-22T00:04:00+00:00",
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queue_path = root / "reply-queue.json"
            database = root / "connector.sqlite3"
            manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
            queue_path.write_text(json.dumps(queue), encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT),
                "enqueue",
                "--queue", str(queue_path),
                "--database", str(database),
                "--manifest", str(manifest),
            ]

            first = subprocess.run(command, capture_output=True, text=True, check=False)
            second = subprocess.run(command, capture_output=True, text=True, check=False)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM connector_actions").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM connector_events").fetchone()[0], 1)
