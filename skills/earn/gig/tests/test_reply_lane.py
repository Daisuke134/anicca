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


class UnknownSendBrowser(LaneBrowser):
    def read_after(self):
        return {"status": "read_failed"}


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


class SellerLastLaneBrowser:
    """Read-only browser fixture for the historical nothing-to-say closure."""

    def __init__(self, item):
        self.item = item
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read_before(self):
        self.events.append("read_before")
        return (
            {"conversation": [{"side": "seller", "body": "already answered"}]},
            {
                "talkroom_id": self.item["talkroom_id"],
                "url": self.item["talkroom_url"],
                "fingerprint": "seller-last",
                "seller_count": 1,
                "seller_messages": [],
                "last_sender": "seller",
            },
        )

    def fill(self, body):
        self.events.append("fill")
        raise AssertionError("nothing-to-say must not fill")

    def click(self):
        self.events.append("click")
        raise AssertionError("nothing-to-say must not click")

    def read_after(self):
        self.events.append("read_after")
        raise AssertionError("nothing-to-say must not read after")


class NothingToSayComposer:
    nothing_to_say_reason = staticmethod(lambda context: "seller_last")

    def __init__(self):
        self.calls = 0

    def __call__(self, context):
        self.calls += 1
        return "must not compose"


class LookupOutboxAdapter:
    """Inject only the exact-lifecycle lookup result/failure for lane tests."""

    def __init__(self, outbox, error=None):
        self._outbox = outbox
        self._error = error

    def action_lifecycle_for_event(self, event_key, thread_id):
        if self._error is not None:
            raise self._error
        return self._outbox.action_lifecycle_for_event(event_key, thread_id)

    def __getattr__(self, name):
        return getattr(self._outbox, name)


class LookupControllerAdapter:
    """Force the lane into the no-pending-action lookup branch without SQL edits."""

    def __init__(self, controller, outbox):
        self._controller = controller
        self.outbox = outbox
        self.note_failure_calls = 0
        self.clear_failure_calls = 0

    def pending_action_for_thread(self, thread_id):
        return None

    def note_failure(self, **kwargs):
        self.note_failure_calls += 1
        return self._controller.note_failure(**kwargs)

    def clear_failure_streak(self, thread_id):
        self.clear_failure_calls += 1
        return self._controller.clear_failure_streak(thread_id)

    def __getattr__(self, name):
        return getattr(self._controller, name)


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
        self.dlq_limit = action_module.DLQ_AFTER_CONSECUTIVE_FAILURES
        self.lane = load("reply_lane")

    def tearDown(self):
        self.temp.cleanup()

    def test_semantic_composer_adapter_preserves_zero_model_call_contract(self):
        composer = self.lane.SemanticReceiptComposer()
        wrapped = self.lane._as_awaiting_buyer(composer)

        self.assertIs(wrapped.uses_model, False)
        self.assertEqual(
            wrapped({"semantic_reply_body": "semantic SSOT本文"}),
            "semantic SSOT本文",
        )

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

    def lookup_failure_fixture(self, *, event_key, queued_thread_id, outbox):
        target_url = f"https://coconala.com/mypage/direct_message/{queued_thread_id}"
        target = self.controller.outbox.enqueue(
            event_key=load("connector_outbox").coconala_message_event_key(
                queued_thread_id, "unrelated-pending"
            ),
            thread_id=queued_thread_id,
            thread_url=target_url,
            observed_at=150,
        )
        item = {
            "event_key": event_key,
            "covered_event_keys": [event_key],
            "talkroom_id": queued_thread_id,
            "talkroom_url": target_url,
            "origin_at": "1970-01-01T00:02:30+00:00",
        }
        adapter = LookupControllerAdapter(self.controller, outbox)
        return target, item, adapter

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
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
        )
        second = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=browser_factory,
            owner_prefix="lane-test-repeat",
            paid_talkroom_ids=frozenset(),
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
        self.assertEqual(second["already_delivered"], 2)
        self.assertEqual(second["skipped"], 0)
        self.assertEqual(second["model_calls"], 0)
        self.assertEqual(len(composed), 2)

    def test_exact_event_for_blocked_action_is_reported_without_retry(self):
        item = self.items[0]
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="blocked-worker", now=101, lease_seconds=300,
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
                "fingerprint": "before-blocked-exact",
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
        self.controller.reconcile_observation(
            action=self.controller.reconciliation_action_for_thread(item["talkroom_id"]),
            observation={
                "talkroom_id": item["talkroom_id"],
                "url": item["talkroom_url"],
                "seller_messages": [],
                "last_sender": "buyer",
            },
            observed_at=224,
        )
        composed = []
        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: self.fail("browser must not run"),
            owner_prefix="exact-blocked",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 225,
        )

        self.assertEqual(result["blocked"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "blocked",
            "errors": ["submit_rejected_sending_unavailable"],
        }])

    def test_exact_event_for_dlq_action_is_reported_without_retry(self):
        item = self.items[0]
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="dlq-worker", now=101, lease_seconds=300,
            action_id=pending["action_id"],
        )
        intent = self.controller.prepare(
            action=action, queue_item=item,
            outgoing_body="delivery forever unknown", now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        self.controller.outbox.move_to_dlq(
            action["action_id"], reason="executor_quiescence_unproven", now=104,
        )
        composed = []
        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: self.fail("browser must not run"),
            owner_prefix="exact-dlq",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 105,
        )

        self.assertEqual(result["dlq"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "dlq",
            "errors": ["executor_quiescence_unproven"],
        }])
        # This action was already in the DLQ before this pass. Historical
        # classification must not be emitted as a new dead-letter transition,
        # otherwise the detector sends a duplicate Telegram incident.
        self.assertEqual(result["dlq_events"], [])

    def test_unknown_exact_event_is_an_explicit_failure_without_retry(self):
        item = self.items[0]
        action = self.controller.pending_action_for_thread(item["talkroom_id"])
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE connector_actions SET state='replied' WHERE action_id=?",
                (action["action_id"],),
            )
        unknown_event = "coconala:message:v1:42:missing-exact-event"
        unknown_item = dict(
            item,
            event_key=unknown_event,
            covered_event_keys=[unknown_event],
        )
        composed = []
        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [unknown_item]},
            compose=lambda context: composed.append(context),
            browser_factory=lambda action, queue_item: self.fail("browser must not run"),
            owner_prefix="exact-unknown",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 105,
        )

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "failed",
            "errors": ["exact_event_not_found"],
        }])

    def test_invalid_exact_event_is_an_explicit_failure_without_retry(self):
        item = self.items[0]
        action = self.controller.pending_action_for_thread(item["talkroom_id"])
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE connector_actions SET state='replied' WHERE action_id=?",
                (action["action_id"],),
            )
        invalid_item = dict(
            item,
            event_key="not-a-coconala-event",
            covered_event_keys=["not-a-coconala-event"],
        )
        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [invalid_item]},
            compose=lambda context: self.fail("invalid exact event must not compose"),
            browser_factory=lambda action, queue_item: self.fail(
                "invalid exact event must not open browser"
            ),
            owner_prefix="exact-invalid",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 105,
        )

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "failed",
            "errors": ["exact_event_invalid"],
        }])

    def test_identity_mismatch_lookup_never_counts_or_dead_letters_target_action(self):
        outbox_module = load("connector_outbox")
        event_key = outbox_module.coconala_initial_contact_event_key("order-a")
        self.controller.outbox.enqueue(
            event_key=event_key,
            thread_id="thread-a",
            thread_url="https://coconala.com/mypage/direct_message/thread-a",
            observed_at=140,
        )
        target, item, adapter = self.lookup_failure_fixture(
            event_key=event_key,
            queued_thread_id="thread-b",
            outbox=LookupOutboxAdapter(self.controller.outbox),
        )
        browser_calls = []
        composer_calls = []

        def compose(context):
            composer_calls.append(context)
            self.fail("invalid exact event must not compose")

        def browser_factory(action, queue_item):
            browser_calls.append((action, queue_item))
            self.fail("invalid exact event must not open browser")

        for _ in range(self.dlq_limit + 1):
            result = self.lane.process_queue(
                controller=adapter,
                queue={"status": "ready", "items": [item]},
                compose=compose,
                browser_factory=browser_factory,
                owner_prefix="identity-mismatch",
                paid_talkroom_ids=frozenset(),
                clock=lambda: 200,
            )
            self.assertEqual(result["failed"], 1)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["dlq_events"], [])
            self.assertEqual(
                result["errors"][0]["errors"],
                ["exact_event_identity_mismatch"],
            )

        stored = self.controller.outbox.get_action(target["action_id"])
        self.assertEqual(stored["state"], "pending")
        self.assertIsNone(stored["dlq_at"])
        self.assertEqual(stored["revision"], 1)
        self.assertIsNone(self.controller.outbox.thread_failure_streak("thread-b"))
        self.assertEqual(adapter.note_failure_calls, 0)
        self.assertEqual(adapter.clear_failure_calls, 0)
        self.assertEqual(browser_calls, [])
        self.assertEqual(composer_calls, [])

    def test_lookup_infrastructure_error_never_counts_or_dead_letters_target_action(self):
        outbox_module = load("connector_outbox")
        event_key = outbox_module.coconala_message_event_key(
            "thread-b", "lookup-failure"
        )
        target, item, adapter = self.lookup_failure_fixture(
            event_key=event_key,
            queued_thread_id="thread-b",
            outbox=LookupOutboxAdapter(
                self.controller.outbox,
                error=sqlite3.OperationalError("database is locked"),
            ),
        )
        browser_calls = []
        composer_calls = []

        for _ in range(self.dlq_limit + 1):
            result = self.lane.process_queue(
                controller=adapter,
                queue={"status": "ready", "items": [item]},
                compose=lambda context: composer_calls.append(context),
                browser_factory=lambda action, queue_item: browser_calls.append(
                    (action, queue_item)
                ),
                owner_prefix="lookup-infrastructure",
                paid_talkroom_ids=frozenset(),
                clock=lambda: 200,
            )
            self.assertEqual(result["failed"], 1)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["dlq_events"], [])
            self.assertEqual(
                result["errors"][0]["errors"],
                ["exact_lifecycle_lookup_failed:OperationalError"],
            )

        stored = self.controller.outbox.get_action(target["action_id"])
        self.assertEqual(stored["state"], "pending")
        self.assertIsNone(stored["dlq_at"])
        self.assertEqual(stored["revision"], 1)
        self.assertIsNone(self.controller.outbox.thread_failure_streak("thread-b"))
        self.assertEqual(adapter.note_failure_calls, 0)
        self.assertEqual(adapter.clear_failure_calls, 0)
        self.assertEqual(browser_calls, [])
        self.assertEqual(composer_calls, [])

    def test_historical_nothing_to_say_is_no_browser_and_refunds_model_call(self):
        item = self.items[0]
        composer = NothingToSayComposer()
        browser = SellerLastLaneBrowser(item)
        first = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=composer,
            browser_factory=lambda action, queue_item: browser,
            owner_prefix="nothing-to-say-first",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 200,
        )

        self.assertEqual(first["nothing_to_say"], 1)
        self.assertEqual(first["model_calls"], 0)
        self.assertEqual(first["skipped"], 0)
        self.assertEqual(composer.calls, 0)
        self.assertEqual(browser.events, ["read_before"])

        second_browser_calls = []
        second = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: self.fail("historical closure must not compose"),
            browser_factory=lambda action, queue_item: second_browser_calls.append(
                (action, queue_item)
            ),
            owner_prefix="nothing-to-say-history",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 201,
        )

        self.assertEqual(second["nothing_to_say"], 1)
        self.assertEqual(second["model_calls"], 0)
        self.assertEqual(second["skipped"], 0)
        self.assertEqual(second_browser_calls, [])

    def test_poll_model_limit_composes_at_most_one_pending_thread(self):
        tick = iter(range(101, 200))
        composed = []

        first = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=lambda context: composed.append(context) or "bounded reply",
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bounded-poll",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(first["model_calls"], 1)
        self.assertEqual(first["replied"], 1)
        self.assertEqual(first["deferred"], 1)
        self.assertEqual(len(composed), 1)

    def test_a_thread_awaiting_the_buyer_does_not_eat_the_send_budget(self):
        # 2026-08-06: eight buyers waited, the oldest since 08-01, and every pass produced
        # failed=1 deferred=7. The lane sends at most one message per pass, and it spent that
        # one slot on a thread whose last message was already ours -- reply_composer refuses
        # those before any model call or browser action -- so the seven buyers who were
        # actually owed a reply were deferred, every pass, for days.
        #
        # A thread with nothing to say costs nothing to send. It must not consume the budget
        # that exists to limit how many strangers hear from us in one waking.
        tick = iter(range(101, 200))
        composed = []

        def compose(context):
            composed.append(context)
            if len(composed) == 1:
                raise self.lane.AwaitingBuyer("reply composition requires buyer-last conversation")
            return "bounded reply"

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bounded-awaiting",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["awaiting_buyer"], 1)
        self.assertEqual(result["deferred"], 0)
        # Waiting on the buyer is not a failure; reporting it as one is what made every pass
        # look broken while it was behaving correctly on that thread.
        self.assertEqual(result["failed"], 0)

    def test_the_composers_real_precondition_is_recognised_as_awaiting_buyer(self):
        # reply_composer raises a plain ValueError with this exact text. Production has to
        # get the same slot-refund the typed exception gets, or the fix only works in tests.
        tick = iter(range(101, 200))
        composed = []

        def compose(context):
            composed.append(context)
            if len(composed) == 1:
                raise ValueError("reply composition requires buyer-last conversation")
            return "bounded reply"

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bounded-bridge",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(result["awaiting_buyer"], 1)
        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["failed"], 0)

    def test_an_unrelated_value_error_is_still_a_failure(self):
        tick = iter(range(101, 200))

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items[:1]},
            compose=lambda context: (_ for _ in ()).throw(ValueError("schema broke")),
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bounded-unrelated",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["awaiting_buyer"], 0)

    def test_a_thread_with_no_reply_box_does_not_eat_the_send_budget(self):
        # Measured 2026-08-06 03:00 on thread 93000002. The page loaded, we were logged in --
        #
        #   title="メッセージ詳細 | マイページ | ココナラ"
        #   forms=["/users_blocks/add/91000128", "/users_blocks/remove/91000128"]
        #   candidates=[]        (no textarea, no text input, no contenteditable)
        #
        # -- and the only thing the page offers is blocking the other person. There is no
        # reply box because the conversation is closed. Retrying it cost the pass's single
        # send every time, so the buyers who could be answered never were.
        tick = iter(range(101, 200))
        composed = []

        def factory(action, item):
            if not composed:
                composed.append(item)
                raise RuntimeError(
                    'missing_message_input (location="https://coconala.com/mypage/'
                    'direct_message/93000002"; title="メッセージ詳細 | マイページ | ココナラ"; '
                    'forms=["/users_blocks/add/91000128"])'
                )
            return LaneBrowser(self.controller, action, item)

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=lambda context: "bounded reply",
            browser_factory=factory,
            owner_prefix="bounded-nobox",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(tick),
            max_model_calls=1,
        )

        self.assertEqual(result["unrepliable"], 1)
        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["deferred"], 0)

    def test_collector_unhealthy_queue_never_claims_or_composes(self):
        called = []

        with self.assertRaisesRegex(ValueError, "collector queue is unhealthy"):
            self.lane.process_queue(
                controller=self.controller,
                queue={"status": "collector_unhealthy", "items": []},
                compose=lambda context: called.append(context),
                browser_factory=lambda action, item: None,
                owner_prefix="lane-test",
                paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
                paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
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
            paid_talkroom_ids=frozenset(),
            clock=lambda: 224,
        )

        self.assertEqual(result["requeued"], 1)
        self.assertEqual(result["blocked"], 0)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(composed, [])
        self.assertEqual(browser_calls, ["reconcile_pending"])
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        self.assertEqual((pending["action_id"], pending["revision"]), (action["action_id"], 2))

    def test_failure_injection_duplicate_matches_close_terminal_without_resend(self):
        # A21: the lane must not swallow duplicate_detected into reconcile_pending.
        # Two identical outgoing messages -> terminal already_delivered closure,
        # zero composes, zero resends.
        item = self.items[0]
        intent = self.prepare_delivery_unknown(item, body="identical progress message")
        composed = []
        observation = {
            "talkroom_id": item["talkroom_id"],
            "url": item["talkroom_url"],
            "seller_messages": [
                {
                    "body_sha256": intent["outgoing_hash"],
                    "sent_at": datetime.fromtimestamp(103, timezone.utc).isoformat(),
                },
                {
                    "body_sha256": intent["outgoing_hash"],
                    "sent_at": datetime.fromtimestamp(150, timezone.utc).isoformat(),
                },
            ],
            "last_sender": "seller",
        }

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context) or "must not resend",
            browser_factory=lambda action, queue_item: ReconcileBrowser(observation),
            owner_prefix="duplicate-reconciler",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 225,
        )

        stored = self.controller.outbox.get_action(1)
        self.assertEqual(result["already_delivered"], 1)
        self.assertEqual(result["reconcile_pending"], 0)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(composed, [])
        self.assertEqual(stored["state"], "replied")

    def test_post_send_ground_truth_unavailable_is_pending_verify_not_swallowed(self):
        # A21: "sent but unreadable" is its own closure (pending_verify), not a
        # blob inside reconcile_pending. The next detector cycle reconciles it.
        item = self.items[0]
        composed = []
        ticks = iter(range(101, 140))

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": [item]},
            compose=lambda context: composed.append(context) or "possibly sent",
            browser_factory=lambda action, queue_item: UnknownSendBrowser(
                self.controller, action, queue_item
            ),
            owner_prefix="unknown-send",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(ticks),
        )

        stored = self.controller.outbox.get_action(1)
        self.assertEqual(result["pending_verify"], 1)
        self.assertEqual(result["reconcile_pending"], 0)
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertEqual(len(composed), 1)
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "pending_verify",
            "errors": ["post_send_ground_truth_unavailable"],
        }])

    def test_dead_letter_closure_is_surfaced_and_lane_moves_on(self):
        item = self.items[0]
        pending = self.controller.pending_action_for_thread(item["talkroom_id"])
        action = self.controller.claim(
            owner="crashed-worker", now=101, lease_seconds=300,
            action_id=pending["action_id"],
        )
        intent = self.controller.prepare(
            action=action, queue_item=item,
            outgoing_body="delivery forever unknown", now=102,
        )
        self.controller.authorize_click(intent=intent, now=103)
        action_module = load("reply_action")
        for _ in range(action_module.DLQ_AFTER_UNRESOLVED_ATTEMPTS - 1):
            self.controller.outbox.note_reconcile_unresolved(
                action["action_id"], now=200,
            )
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
            compose=lambda context: composed.append(context) or "must not resend",
            browser_factory=lambda claimed, queue_item: ReconcileBrowser(absent),
            owner_prefix="dlq-reconciler",
            paid_talkroom_ids=frozenset(),
            clock=lambda: 500,
        )

        self.assertEqual(result["dlq"], 1)
        self.assertEqual(result["reconcile_pending"], 0)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(composed, [])
        self.assertEqual(result["errors"], [{
            "talkroom_id": item["talkroom_id"],
            "status": "dlq",
            "errors": ["executor_quiescence_unproven"],
        }])
        self.assertEqual(len(self.controller.outbox.dlq_actions()), 1)

    def test_failure_injection_one_message_crash_does_not_kill_the_lane(self):
        # Live incident gig-pass-1785538800 (2026-08-01 08:01): one message's
        # verification raised RuntimeError and the WHOLE lane died in 11s,
        # leaving the remaining breached threads unanswered. Bulkhead: a
        # per-message failure becomes a per-message `failed` closure and the
        # lane continues to the next thread.
        composed = []
        ticks = iter(range(101, 200))

        def compose(context):
            composed.append(context)
            if len(composed) == 1:
                raise RuntimeError("model unavailable")
            return "second thread still gets its reply"

        result = self.lane.process_queue(
            controller=self.controller,
            queue={"status": "ready", "items": self.items},
            compose=compose,
            browser_factory=lambda action, item: LaneBrowser(self.controller, action, item),
            owner_prefix="bulkhead",
            paid_talkroom_ids=frozenset(),
            clock=lambda: next(ticks),
        )

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["replied"], 1)
        self.assertEqual(len(composed), 2)
        self.assertEqual({event["talkroom_id"] for event in result["events"]}, {"43"})
        self.assertEqual(result["errors"][0]["talkroom_id"], "42")
        self.assertEqual(result["errors"][0]["status"], "failed")
        self.assertIn("RuntimeError", result["errors"][0]["errors"][0])
        # the crashed thread is requeued (pre-click failure), not lost
        pending = self.controller.pending_action_for_thread("42")
        self.assertIsNotNone(pending)
        self.assertEqual(pending["state"], "pending")

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

    def test_cli_zero_model_limit_uses_existing_unlimited_queue_mode(self):
        source = LANE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("max_model_calls=args.max_model_calls or None", source)

    def test_paid_queue_is_recollected_after_reply_before_project_or_delivery_selection(self):
        source = GIG_PASS.read_text(encoding="utf-8")

        reply = source.index('reply_inquiries || isolate_lane "INQUIRY_REPLY"')
        revalidate = source.index("revalidate_paid_queue_after_reply || {", reply)
        project = source.index('PROJECT_SELECTION_JSON=$(TOP_JSON="$TOP_JSON"')
        paid_dispatch = source.index('case "$TOP_CLASS" in', project)
        self.assertLess(reply, revalidate)
        self.assertLess(revalidate, project)
        self.assertLess(project, paid_dispatch)
        self.assertIn('coconala_queue_snapshot.py" --output "$fresh_snapshot"', source)
        self.assertIn('delivery_queue.py" build --snapshot "$fresh_snapshot"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class NearDuplicateLaneTest(unittest.TestCase):
    """A suppressed duplicate must not read as a lane failure."""

    def setUp(self):
        self.lane = load("reply_lane")

    def test_the_lane_accepts_the_suppressed_status(self):
        # reply_lane raises on an unknown status (:268). Introducing
        # near_duplicate_suppressed without teaching the lane would turn every suppression
        # into a "failed" thread -- the same false alarm P1b exists to remove -- and would
        # also spend the pass's send budget on a thread that sent nothing.
        self.assertIn("near_duplicate_suppressed", LANE_SCRIPT.read_text(encoding="utf-8"))

    def test_a_suppressed_thread_does_not_consume_the_send_budget(self):
        # The refund must live in the branch itself, next to awaiting_buyer and
        # unrepliable, which already give the slot back for the same reason: nothing was
        # sent, so nobody should have paid for it.
        source = LANE_SCRIPT.read_text(encoding="utf-8")
        branch = source[source.index('elif status == "near_duplicate_suppressed"'):]
        branch = branch[:branch.index("        else:")]
        self.assertIn('summary["near_duplicate"] += 1', branch)
        self.assertIn('summary["model_calls"] = max(0, summary["model_calls"] - 1)', branch)
