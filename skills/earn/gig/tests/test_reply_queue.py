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

    def blocked_outbox(self, root):
        """Build a real outbox whose single thread is stuck in ``blocked`` (C1b)."""
        outbox_script = Path(__file__).resolve().parents[1] / "scripts" / "connector_outbox.py"
        spec = importlib.util.spec_from_file_location("connector_outbox", outbox_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        database = root / "connector.sqlite3"
        manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
        outbox = module.ConnectorOutbox(database, manifest)
        action = outbox.enqueue(
            event_key="coconala:message:v1:4201:msg-7",
            thread_id="4201",
            thread_url="https://coconala.com/mypage/direct_message/4201",
            observed_at=900,
        )
        claim = outbox.claim(owner="blocked-worker", now=901, lease_seconds=60)
        intent = outbox.prepare_intent(
            action["action_id"], owner="blocked-worker",
            fencing_token=claim["fencing_token"],
            outgoing_body="reply the buyer never received", now=902,
        )
        outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="blocked-worker",
            fencing_token=claim["fencing_token"], now=903,
        )
        outbox.record_delivery_unknown(
            action["action_id"], owner="blocked-worker",
            fencing_token=claim["fencing_token"], now=904,
            rejection_code="submit_rejected_sending_unavailable",
        )
        blocked = outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None,
            last_sender="buyer", observed_at=1030, authoritative_absent=True,
        )
        self.assertEqual(blocked["state"], "blocked")
        return database, manifest, blocked

    def test_enqueue_cli_revives_a_blocked_thread_without_any_new_event(self):
        """C1b: an hourly pass must resurrect a silent blocked thread by itself."""
        queue = {"status": "queue_empty", "errors": [], "items": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            queue_path = root / "reply-queue.json"
            queue_path.write_text(json.dumps(queue), encoding="utf-8")

            completed = subprocess.run([
                sys.executable,
                str(SCRIPT),
                "enqueue",
                "--queue", str(queue_path),
                "--database", str(database),
                "--manifest", str(manifest),
                "--now", str(int(blocked["updated_at"]) + 1800),
            ], capture_output=True, text=True, check=False)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["revived"], 1)
            self.assertEqual(payload["dead_lettered"], 0)
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT state,revision FROM connector_actions WHERE action_id=?",
                        (blocked["action_id"],),
                    ).fetchone(),
                    ("pending", 2),
                )
            self.assertTrue((root / "connector-outbox-revives.jsonl").exists())

    def test_enqueue_ingests_a_new_thread_and_revives_a_blocked_one_in_one_pass(self):
        """Both lanes of the same step: a live queue item AND a due blocked thread."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            due = int(blocked["updated_at"]) + 1800
            queue = {
                "status": "ready",
                "errors": [],
                "items": [{
                    "event_key": "coconala:message:v1:4300:msg-9",
                    "covered_event_keys": ["coconala:message:v1:4300:msg-9"],
                    "talkroom_id": "4300",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4300",
                    "detected_at": datetime.fromtimestamp(due - 60, timezone.utc).isoformat(),
                }],
            }

            result = reply_queue.enqueue_queue(
                queue, database=database, manifest=manifest, now=due
            )

            self.assertEqual(len(result["actions"]), 1)
            self.assertEqual(result["actions"][0]["thread_id"], "4300")
            self.assertEqual([entry["action_id"] for entry in result["revived"]],
                             [blocked["action_id"]])
            self.assertEqual(result["dead_lettered"], [])
            with sqlite3.connect(database) as connection:
                states = dict(connection.execute(
                    "SELECT thread_id,state FROM connector_actions"
                ).fetchall())
            self.assertEqual(states, {"4201": "pending", "4300": "pending"})

    def test_current_semantic_receipt_reauthorizes_only_pre_intent_dlq(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reply_queue = load_module()
            database = root / "connector.sqlite3"
            manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
            outbox = reply_queue.ConnectorOutbox(database, manifest)
            action = outbox.enqueue(
                event_key="coconala:message:v1:4201:msg-7", thread_id="4201",
                thread_url="https://coconala.com/mypage/direct_message/4201", observed_at=900,
            )
            outbox.record_thread_failure(
                thread_id="4201", error_class="old_projection_failure",
                now=901, dead_letter_after=1,
            )
            queue = {
                "status": "ready", "errors": [], "semantic_ssot": True,
                "items": [{
                    "event_key": "coconala:message:v1:4201:msg-7",
                    "covered_event_keys": ["coconala:message:v1:4201:msg-7"],
                    "talkroom_id": "4201",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
                    "detected_at": "1970-01-01T00:15:02+00:00",
                    "semantic_reply_body": "現在のsemantic判定で承認済みです。",
                    "semantic_context_sha256": "a" * 64,
                }],
            }

            result = reply_queue.enqueue_queue(
                queue, database=database, manifest=manifest, now=902,
            )

            self.assertEqual(result["semantic_reauthorized"], [action["action_id"]])
            self.assertEqual(result["actions"][0]["state"], "pending")
            self.assertIsNone(result["actions"][0]["dlq_at"])

    def test_semantic_receipt_never_reauthorizes_a_prior_click_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            outbox = reply_queue.ConnectorOutbox(database, manifest)
            outbox.record_thread_failure(
                thread_id="4201", error_class="old_post_click_failure",
                now=1040, dead_letter_after=1,
            )
            queue = {
                "status": "ready", "errors": [], "semantic_ssot": True,
                "items": [{
                    "event_key": "coconala:message:v1:4201:msg-7",
                    "covered_event_keys": ["coconala:message:v1:4201:msg-7"],
                    "talkroom_id": "4201",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
                    "detected_at": "1970-01-01T00:17:21+00:00",
                    "semantic_reply_body": "再送してはいけません。",
                    "semantic_context_sha256": "b" * 64,
                }],
            }

            result = reply_queue.enqueue_queue(
                queue, database=database, manifest=manifest, now=1041,
            )

            self.assertEqual(result["semantic_reauthorized"], [])
            self.assertIsNotNone(result["actions"][0]["dlq_at"])

    def test_a_revive_in_either_order_never_breaks_event_ingest(self):
        """A revive must not be able to invalidate an in-flight snapshot event.

        Round 2 shipped the ordering (enqueue first) as the guard. That was too
        weak: the 5-minute detector and the hourly pass hold different locks, so a
        revive can land BETWEEN another process's snapshot capture and its enqueue
        - an ordering inside one call cannot help there. The revive no longer
        advances ``updated_at`` at all, so both orders are now safe. Enqueue-first
        is kept as the shipped order, but it is defence in depth, not the fix.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            due = int(blocked["updated_at"]) + 1800
            queue = {
                "status": "ready",
                "errors": [],
                "items": [{
                    "event_key": "coconala:message:v1:4201:msg-later",
                    "covered_event_keys": ["coconala:message:v1:4201:msg-later"],
                    "talkroom_id": "4201",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
                    "detected_at": datetime.fromtimestamp(due - 60, timezone.utc).isoformat(),
                }],
            }

            # Reversed order (revive first, as a concurrent detector would do),
            # then ingest an event captured BEFORE that revive.
            outbox = reply_queue.ConnectorOutbox(database, manifest)
            outbox.revive_blocked_actions(now=due)
            reversed_order = reply_queue.enqueue_queue(
                queue, database=database, manifest=manifest, now=due
            )
            self.assertEqual(len(reversed_order["actions"]), 1)
            self.assertIsNone(reversed_order["revive_error"])

            # Shipped order (enqueue first) on the same inputs: also fine.
            fresh_root = root / "shipped-order"
            fresh_root.mkdir()
            fresh_db, fresh_manifest, fresh_blocked = self.blocked_outbox(fresh_root)
            shipped = reply_queue.enqueue_queue(
                queue, database=fresh_db, manifest=fresh_manifest,
                now=int(fresh_blocked["updated_at"]) + 1800,
            )
            self.assertEqual(shipped["actions"][0]["state"], "pending")
            self.assertIsNone(shipped["revive_error"])

    def test_a_raising_revive_still_yields_a_successful_enqueue(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            queue = {
                "status": "ready",
                "errors": [],
                "items": [{
                    "event_key": "coconala:message:v1:4400:msg-1",
                    "covered_event_keys": ["coconala:message:v1:4400:msg-1"],
                    "talkroom_id": "4400",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4400",
                    "detected_at": "2026-07-22T00:04:00+00:00",
                }],
            }
            original = reply_queue.ConnectorOutbox.revive_blocked_actions

            def exploding(self, *, now):
                raise RuntimeError("revive blew up")

            reply_queue.ConnectorOutbox.revive_blocked_actions = exploding
            try:
                result = reply_queue.enqueue_queue(
                    queue, database=database, manifest=manifest, now=99999999
                )
            finally:
                reply_queue.ConnectorOutbox.revive_blocked_actions = original

            # Event ingest is the job of this step and it completed.
            self.assertEqual(len(result["actions"]), 1)
            self.assertEqual(result["status"], "enqueued")
            self.assertEqual(result["revived"], [])
            self.assertEqual(result["revive_status"], "failed")
            self.assertIn("revive blew up", result["revive_error"])
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM connector_events"
                    ).fetchone()[0],
                    2,
                )

    def test_a_corrupt_manifest_on_an_empty_queue_does_not_kill_the_lane(self):
        # The revive is now the FIRST manifest read on a queue_empty pass; before
        # C1b nothing read it when the loop body never ran.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, _ = self.blocked_outbox(root)
            reply_queue = load_module()
            corrupt = root / "corrupt-manifest.json"
            corrupt.write_text("{ this is not json", encoding="utf-8")

            result = reply_queue.enqueue_queue(
                {"status": "queue_empty", "errors": [], "items": []},
                database=database, manifest=corrupt, now=99999999,
            )

            self.assertEqual(result["status"], "queue_empty")
            self.assertEqual(result["revive_status"], "failed")
            self.assertIn("ConnectorDisabled", result["revive_error"])

    def test_a_disabled_connector_is_never_logged_as_a_confident_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            disabled = root / "disabled-manifest.json"
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["enabled"] = False
            disabled.write_text(json.dumps(payload), encoding="utf-8")

            result = reply_queue.enqueue_queue(
                {"status": "queue_empty", "errors": [], "items": []},
                database=database, manifest=disabled,
                now=int(blocked["updated_at"]) + 1800,
            )

            self.assertEqual(result["revive_status"], "connector_disabled")
            self.assertIsNone(result["revive_error"])
            self.assertEqual(result["revived"], [])

    def test_enqueue_of_a_new_event_on_the_blocked_thread_revives_it_event_driven(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            reply_queue = load_module()
            due = int(blocked["updated_at"]) + 1800
            queue = {
                "status": "ready",
                "errors": [],
                "items": [{
                    "event_key": "coconala:message:v1:4201:msg-buyer-wrote-again",
                    "covered_event_keys": ["coconala:message:v1:4201:msg-buyer-wrote-again"],
                    "talkroom_id": "4201",
                    "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
                    "detected_at": datetime.fromtimestamp(due, timezone.utc).isoformat(),
                }],
            }

            result = reply_queue.enqueue_queue(
                queue, database=database, manifest=manifest, now=due
            )

            self.assertEqual(result["actions"][0]["state"], "pending")
            self.assertEqual(result["revived"], [])
            self.assertEqual(result["dead_lettered"], [])

    def test_enqueue_cli_leaves_a_blocked_thread_alone_before_the_backoff(self):
        queue = {"status": "queue_empty", "errors": [], "items": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database, manifest, blocked = self.blocked_outbox(root)
            queue_path = root / "reply-queue.json"
            queue_path.write_text(json.dumps(queue), encoding="utf-8")

            completed = subprocess.run([
                sys.executable,
                str(SCRIPT),
                "enqueue",
                "--queue", str(queue_path),
                "--database", str(database),
                "--manifest", str(manifest),
                "--now", str(int(blocked["updated_at"]) + 1799),
            ], capture_output=True, text=True, check=False)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["revived"], 0)
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT state FROM connector_actions WHERE action_id=?",
                        (blocked["action_id"],),
                    ).fetchone()[0],
                    "blocked",
                )

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
