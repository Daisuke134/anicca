import hashlib
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


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
LANE_SCRIPT = SCRIPTS / "reply_lane.py"
GIG_PASS = Path(__file__).resolve().parents[1] / "gig_pass.sh"


def load(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LaneBrowser:
    def __init__(self, controller, action, item):
        self.controller = controller
        self.action = action
        self.item = item
        self.body = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read_before(self):
        return (
            {"conversation": [{"side": "buyer", "body": f"question-{self.item['talkroom_id']}"}]},
            {
                "talkroom_id": self.item["talkroom_id"],
                "url": self.item["talkroom_url"],
                "fingerprint": f"before-{self.item['talkroom_id']}",
                "seller_count": 0,
            },
        )

    def fill(self, body):
        self.body = body

    def click(self):
        stored = self.controller.outbox.get_action(self.action["action_id"])
        if stored["state"] != "reconcile_pending":
            raise AssertionError("click was not fenced")

    def read_after(self):
        room = self.item["talkroom_id"]
        sent_epoch = 104 if room == "42" else 108
        return {
            "talkroom_id": room,
            "url": self.item["talkroom_url"],
            "fingerprint": f"after-{room}",
            "seller_count": 1,
            "seller_message_hashes": [hashlib.sha256(self.body.encode()).hexdigest()],
            "seller_sent_at": datetime.fromtimestamp(sent_epoch, timezone.utc).isoformat(),
            "last_sender": "seller",
        }


class ReconcileBrowser:
    def __init__(self, observation):
        self.observation = observation

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read_before(self):
        return ({"conversation": []}, self.observation)


class RequeuedBrowser(LaneBrowser):
    def read_after(self):
        return {
            "talkroom_id": self.item["talkroom_id"],
            "url": self.item["talkroom_url"],
            "fingerprint": "after-requeue",
            "seller_count": 1,
            "seller_message_hashes": [hashlib.sha256(self.body.encode()).hexdigest()],
            "seller_sent_at": datetime.fromtimestamp(229, timezone.utc).isoformat(),
            "last_sender": "seller",
        }


class ReplyLaneTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
        outbox_module = load("connector_outbox")
        outbox = outbox_module.ConnectorOutbox(self.database, self.manifest)
        self.items = []
        for room in ("42", "43"):
            event_key = outbox_module.coconala_message_event_key(room, f"message-{room}")
            url = f"https://coconala.com/mypage/direct_message/{room}"
            outbox.enqueue(
                event_key=event_key,
                thread_id=room,
                thread_url=url,
                observed_at=100,
            )
            self.items.append({
                "event_key": event_key,
                "covered_event_keys": [event_key],
                "talkroom_id": room,
                "talkroom_url": url,
                "origin_at": "1970-01-01T00:01:40+00:00",
            })
        action_module = load("reply_action")
        self.controller = action_module.ReplyActionController(self.database, self.manifest)
        self.lane = load("reply_lane")

    def tearDown(self):
        self.temp.cleanup()

    def prepare_delivery_unknown(self, item, body="ack lost"):
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="crashed-worker", now=101, lease_seconds=300,
            action_id=pending["action_id"],
        )
        intent = self.controller.prepare(
            action=action, queue_item=item, outgoing_body=body, now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "fingerprint": "before-unknown",
                "seller_count": 0,
            },
            after={"status": "read_failed"},
            observed_at=104,
        )
        return intent

    def test_two_threads_reach_replied_and_repeated_loop_sends_nothing(self):
        tick = iter(range(101, 200))
        composed = []

        def compose(context):
            composed.append(context)
            return f"reply-{len(composed)}"

        def browser_factory(action, item):
            return LaneBrowser(self.controller, action, item)

        first = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=browser_factory,
            owner_prefix="lane-test",
            clock=lambda: next(tick),
        )
        second = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=browser_factory,
            owner_prefix="lane-test-repeat",
            clock=lambda: next(tick),
        )

        self.assertEqual(first["replied"], 2)
        self.assertEqual(first["reconcile_pending"], 0)
        self.assertEqual(len(first["events"]), 2)
        self.assertEqual(
            {event["talkroom_id"] for event in first["events"]}, {"42", "43"},
        )
        self.assertTrue(all(event["status"] == "replied" for event in first["events"]))
        self.assertNotIn("reply-", json.dumps(first["events"]))
        self.assertEqual(second["replied"], 0)
        self.assertEqual(second["skipped"], 2)
        self.assertEqual(len(composed), 2)

    def test_poll_model_limit_composes_at_most_one_pending_thread(self):
        tick = iter(range(101, 200))
        composed = []

        first = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=lambda context: composed.append(context) or "bounded reply",
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bounded-poll",
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(first["model_calls"], 1)
        self.assertEqual(first["replied"], 1)
        self.assertEqual(first["deferred"], 1)
        self.assertEqual(len(composed), 1)

    def test_collector_unhealthy_queue_never_claims_or_composes(self):
        called = []

        with self.assertRaisesRegex(ValueError, "collector queue is unhealthy"):
            self.lane.process_queue(
                controller=self.controller,
                queue={"status": "collector_unhealthy", "items": []},
                compose=lambda context: called.append(context),
                browser_factory=lambda action, item: None,
                owner_prefix="lane-test",
                clock=lambda: 101,
            )

        self.assertEqual(called, [])

    def test_delivery_unknown_matching_live_hash_reconciles_without_model_or_click(self):
        item = self.items[0]
        intent = self.prepare_delivery_unknown(item)
        newer_item = dict(item, origin_at="1970-01-01T00:03:20+00:00")
        composed = []
        browser_calls = []
        observation = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [{
                "body_sha256": intent["outgoing_hash"],
                "sent_at": datetime.fromtimestamp(103, timezone.utc).isoformat(),
            }],
            "last_sender": "seller",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [newer_item]},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: (
                browser_calls.append(action) or ReconcileBrowser(observation)
            ),
            owner_prefix="reconciler",
            clock=lambda: 225,
        )

        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["reconciled"], 1)
        self.assertEqual(result["events"][0]["seller_sent_at"], observation["seller_messages"][0]["sent_at"])
        self.assertEqual(result["events"][0]["origin_at"], item["origin_at"])
        self.assertEqual(composed, [])
        self.assertEqual(len(browser_calls), 1)

    def test_queue_empty_still_reconciles_durable_delivery_unknown(self):
        item = self.items[0]
        intent = self.prepare_delivery_unknown(item)
        composed = []
        browser_calls = []
        observation = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [{
                "body_sha256": intent["outgoing_hash"],
                "sent_at": datetime.fromtimestamp(103, timezone.utc).isoformat(),
            }],
            "last_sender": "seller",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "queue_empty", "items": []},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: (
                browser_calls.append((action["thread_id"], queue_item["talkroom_id"]))
                or ReconcileBrowser(observation)
            ),
            owner_prefix="durable-reconciler",
            clock=lambda: 225,
        )

        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["reconciled"], 1)
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, [("42", "42")])

    def test_queue_empty_still_executes_one_durable_pending_action(self):
        composed = []
        browser_calls = []
        ticks = iter(range(101, 140))

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "queue_empty", "items": []},
            compose=lambda context: composed.append(context) or "durable reply",
            browser_factory=lambda action, item: (
                browser_calls.append((action["thread_id"], item["talkroom_id"]))
                or LaneBrowser(self.controller, action, item)
            ),
            owner_prefix="durable-pending",
            clock=lambda: next(ticks),
            max_model_calls=1,
        )

        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["deferred"], 1)
        self.assertEqual(len(composed), 1)
        self.assertEqual(browser_calls, [("42", "42")])

    def test_ready_empty_never_restores_durable_pending_action(self):
        composed = []
        browser_calls = []

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": []},
            compose=lambda context: composed.append(context) or "must not compose",
            browser_factory=lambda action, item: browser_calls.append((action, item)),
            owner_prefix="ready-empty",
            clock=lambda: 101,
            max_model_calls=1,
        )

        action = self.controller.pending_action_for_thread("42")
        self.assertEqual(result["replied"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, [])
        self.assertIsNotNone(action)
        self.assertEqual(action["state"], "pending")
        self.assertIsNone(action["owner"])

    def test_pending_actions_rejects_corrupt_event_identity(self):
        action = self.controller.pending_action_for_thread("42")
        action_id = action["action_id"]
        with sqlite3.connect(self.database) as connection:
            original = connection.execute(
                """SELECT event_key,action_id,platform,thread_id,observed_at
                     FROM connector_events
                    WHERE action_id=?
                    ORDER BY observed_at,event_key
                    LIMIT 1""",
                (action_id,),
            ).fetchone()
        self.assertIsNotNone(original)

        cases = (
            (
                "cross-thread event key",
                "UPDATE connector_events SET event_key=? WHERE action_id=?",
                ("coconala:message:v1:99:corrupt", action_id),
            ),
            (
                "unknown event grammar",
                "UPDATE connector_events SET event_key=? WHERE action_id=?",
                ("coconala:unknown:v1:42:corrupt", action_id),
            ),
            (
                "event platform mismatch",
                "UPDATE connector_events SET platform=? WHERE action_id=?",
                ("other", action_id),
            ),
            (
                "event thread mismatch",
                "UPDATE connector_events SET thread_id=? WHERE action_id=?",
                ("99", action_id),
            ),
            (
                "negative event timestamp",
                "UPDATE connector_events SET observed_at=? WHERE action_id=?",
                (-1, action_id),
            ),
            (
                "missing event",
                "DELETE FROM connector_events WHERE action_id=?",
                (action_id,),
            ),
        )

        try:
            for name, statement, parameters in cases:
                with self.subTest(name=name):
                    with sqlite3.connect(self.database) as connection:
                        connection.execute(
                            "DELETE FROM connector_events WHERE action_id=?", (action_id,)
                        )
                        connection.execute(
                            """INSERT INTO connector_events(
                                   event_key,action_id,platform,thread_id,observed_at
                               ) VALUES(?,?,?,?,?)""",
                            original,
                        )
                        connection.execute(statement, parameters)
                    with self.assertRaisesRegex(
                        RuntimeError, "durable pending action has invalid event identity"
                    ):
                        self.controller.pending_actions()
        finally:
            with sqlite3.connect(self.database) as connection:
                connection.execute(
                    "DELETE FROM connector_events WHERE action_id=?", (action_id,)
                )
                connection.execute(
                    """INSERT INTO connector_events(
                           event_key,action_id,platform,thread_id,observed_at
                       ) VALUES(?,?,?,?,?)""",
                    original,
                )

    def test_corrupt_durable_identity_fails_before_claim_model_or_browser(self):
        action = self.controller.pending_action_for_thread("42")
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE connector_events SET event_key=? WHERE action_id=?",
                ("coconala:message:v1:99:corrupt", action["action_id"]),
            )
        composed = []
        browser_calls = []

        with self.assertRaisesRegex(
            RuntimeError, "durable pending action has invalid event identity"
        ):
            self.lane.process_queue(
                controller=self.controller,
                queue={"status": "queue_empty", "items": []},
                compose=lambda context: composed.append(context) or "must not compose",
                browser_factory=lambda claimed, item: browser_calls.append((claimed, item)),
                owner_prefix="corrupt-durable",
                clock=lambda: 101,
                max_model_calls=1,
            )

        stored = self.controller.outbox.get_action(action["action_id"])
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, [])
        self.assertEqual(stored["state"], "pending")
        self.assertIsNone(stored["owner"])
        self.assertEqual(stored["lease_until"], 0)

    def test_authoritative_absence_after_window_requeues_and_sends_in_same_pass(self):
        item = self.items[0]
        self.prepare_delivery_unknown(item)
        composed = []
        browser_calls = []
        ticks = iter(range(225, 250))
        absent = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }

        def browser_factory(action, queue_item):
            browser_calls.append(action["state"])
            if action["state"] == "reconcile_pending":
                return ReconcileBrowser(absent)
            return RequeuedBrowser(self.controller, action, queue_item)

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context) or "safe resend",
            browser_factory=browser_factory,
            owner_prefix="reconciler",
            clock=lambda: next(ticks),
        )

        self.assertEqual(result["requeued"], 1)
        self.assertEqual(result["replied"], 1)
        self.assertEqual(len(composed), 1)
        self.assertEqual(browser_calls, ["reconcile_pending", "pending"])

    def test_authoritative_absence_inside_window_never_requeues_or_composes(self):
        item = self.items[0]
        self.prepare_delivery_unknown(item)
        composed = []
        absent = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: ReconcileBrowser(absent),
            owner_prefix="reconciler",
            clock=lambda: 200,
        )

        self.assertEqual(result["reconcile_pending"], 1)
        self.assertEqual(result["requeued"], 0)
        self.assertEqual(composed, [])

    def test_explicit_server_rejection_blocks_without_same_pass_resend(self):
        item = self.items[0]
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="rejected-worker", now=101, lease_seconds=300,
            action_id=pending["action_id"],
        )
        intent = self.controller.prepare(
            action=action, queue_item=item,
            outgoing_body="server rejected reply", now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "fingerprint": "before-rejected",
                "seller_count": 0,
            },
            after={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "seller_count": 0,
                "last_sender": "buyer",
                "send_network": [{
                    "method": "POST",
                    "path": f"/mypage/direct_message_ajax/{item['talkroom_id']}",
                    "outcome": "finished",
                    "status": 200,
                }],
                "browser_error_code": "submit_rejected_sending_unavailable",
            },
            observed_at=104,
        )
        composed = []
        browser_calls = []
        absent = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context) or "must not resend",
            browser_factory=lambda action, queue_item: (
                browser_calls.append(action["state"]) or ReconcileBrowser(absent)
            ),
            owner_prefix="rejected-reconciler",
            clock=lambda: 224,
        )

        self.assertEqual(result["blocked"], 1)
        self.assertEqual(result["requeued"], 0)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, ["reconcile_pending"])
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "blocked",
            "errors": ["submit_rejected_sending_unavailable"],
        }])

    def test_new_event_during_rejection_window_defers_fresh_revision_to_next_pass(self):
        item = self.items[0]
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="rejected-worker", now=101, lease_seconds=300,
            action_id=pending["action_id"],
        )
        intent = self.controller.prepare(
            action=action, queue_item=item,
            outgoing_body="rejected before a newer buyer event", now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        self.controller.finalize(
            intent=intent,
            before={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "fingerprint": "before-rejected-new-event",
                "seller_count": 0,
            },
            after={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "seller_count": 0,
                "last_sender": "buyer",
                "send_network": [{
                    "method": "POST",
                    "path": f"/mypage/direct_message_ajax/{item['talkroom_id']}",
                    "outcome": "finished",
                    "status": 200,
                }],
                "browser_error_code": "submit_rejected_sending_unavailable",
            },
            observed_at=104,
        )
        outbox_module = load("connector_outbox")
        self.controller.outbox.enqueue(
            event_key=outbox_module.coconala_message_event_key(
                item["talkroom_id"], "event-during-rejection-window"
            ),
            thread_id=item["talkroom_id"],
            thread_url=item["talkroom_url"],
            observed_at=105,
        )
        composed = []
        browser_calls = []
        absent = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [],
            "last_sender": "buyer",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context) or "must wait for next pass",
            browser_factory=lambda action, queue_item: (
                browser_calls.append(action["state"]) or ReconcileBrowser(absent)
            ),
            owner_prefix="rejected-new-event-reconciler",
            clock=lambda: 224,
        )

        self.assertEqual(result["requeued"], 1)
        self.assertEqual(result["blocked"], 0)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, ["reconcile_pending"])
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        self.assertEqual((pending["action_id"], pending["revision"]), (action["action_id"], 2))

    def test_queue_empty_cli_writes_owner_only_summary_without_model_or_browser(self):
        queue_path = self.root / "reply-queue.json"
        output = self.root / "reply-lane-result.json"
        empty_database = self.root / "empty-outbox.sqlite3"
        load("connector_outbox").ConnectorOutbox(empty_database, self.manifest)
        queue_path.write_text(json.dumps({
            "status": "queue_empty", "errors": [], "items": [],
        }), encoding="utf-8")

        completed = subprocess.run([
            sys.executable,
            str(LANE_SCRIPT),
            "--queue", str(queue_path),
            "--database", str(empty_database),
            "--manifest", str(self.manifest),
            "--runner", str(self.root / "must-not-run"),
            "--schema", str(self.root / "must-not-read"),
            "--cdp-helper", str(self.root / "must-not-open"),
            "--output", str(output),
        ], capture_output=True, text=True, check=False)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "completed")
        self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)

    def test_gig_pass_uses_fenced_lane_and_contains_no_legacy_direct_browser_prompt(self):
        source = GIG_PASS.read_text(encoding="utf-8")

        self.assertIn('scripts/reply_lane.py', source)
        self.assertIn('scripts/telegram_report.py', source)
        self.assertNotIn('verify_inquiry_live_dom.py', source)
        self.assertNotIn('Open each talkroom in this generic inquiry queue', source)
        self.assertNotIn('delivery_cadence.py" validate-inquiry', source)

    def test_cli_wires_hidden_browser_flag_to_cdp_reply_browser(self):
        source = LANE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('parser.add_argument("--hidden-browser", action="store_true")', source)
        self.assertIn("hidden=args.hidden_browser", source)

    def test_paid_queue_is_recollected_after_reply_before_project_or_delivery_selection(self):
        source = GIG_PASS.read_text(encoding="utf-8")

        reply = source.index("reply_inquiries || exit 1")
        revalidate = source.index("revalidate_paid_queue_after_reply || exit 1")
        project = source.index('PROJECT_SELECTION_JSON=$(TOP_JSON="$TOP_JSON"')
        paid_dispatch = source.index('case "$TOP_CLASS" in', project)
        self.assertLess(reply, revalidate)
        self.assertLess(revalidate, project)
        self.assertLess(project, paid_dispatch)
        self.assertIn('coconala_queue_snapshot.py" --output "$fresh_snapshot"', source)
        self.assertIn('delivery_queue.py" build --snapshot "$fresh_snapshot"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
