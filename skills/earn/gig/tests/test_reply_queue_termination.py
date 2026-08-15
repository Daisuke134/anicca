"""E6b: every reply queue entry must be able to STOP.

Two live incidents, both a five-minute retry loop with no terminal state:

  thread 93000007  412 consecutive `ValueError: reply composition requires
                   buyer-last conversation` -- the correct finding that we
                   already spoke last, delivered as an exception
  thread 93000002  102+ consecutive `RuntimeError: missing_message_input` -- a
                   genuine fault that repetition will not fix

The first must close cleanly WITHOUT claiming a reply and WITHOUT muting the
next buyer message. The second must dead-letter on CONSECUTIVE identical
failure, durably enough that a fresh process every 300s can still count.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MANIFEST = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
THREAD = "93000007"
THREAD_URL = f"https://coconala.com/mypage/direct_message/{THREAD}"


def load(name):
    spec = importlib.util.spec_from_file_location(f"termination_{name}", SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SellerLastBrowser:
    """The DOM shape thread_state() produces for a thread we answered last."""

    def __init__(self, last_side="seller"):
        self.last_side = last_side
        self.events: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read_before(self):
        self.events.append("read_before")
        return (
            {"conversation": [
                {"side": "buyer", "body": "納期はいつになりますか"},
                {"side": self.last_side, "body": "明日中にお送りします"},
            ]},
            {
                "talkroom_id": THREAD,
                "url": THREAD_URL,
                "fingerprint": "before",
                "seller_count": 1,
                "seller_message_hashes": [],
                "seller_messages": [],
                "last_sender": self.last_side,
            },
        )

    def fill(self, body):
        self.events.append("fill")

    def click(self):
        self.events.append("click")

    def read_after(self):
        self.events.append("read_after")
        raise AssertionError("must not reach read_after")


class Composer:
    """A composer that answers the buyer-last question without a model call."""

    nothing_to_say_reason = staticmethod(load("reply_composer").nothing_to_say_reason)

    def __init__(self):
        self.calls = 0

    def __call__(self, context):
        self.calls += 1
        return "承知しました。本日中に着手します。"


class NothingToSayClosureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.outbox_module = load("connector_outbox")
        self.outbox = self.outbox_module.ConnectorOutbox(self.database, MANIFEST)
        self.action = self.outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key(THREAD, "message-1"),
            thread_id=THREAD,
            thread_url=THREAD_URL,
            observed_at=100,
        )
        self.controller = load("reply_action").ReplyActionController(self.database, MANIFEST)
        self.executor = load("reply_executor")
        self.queue_item = {
            "event_key": f"coconala:message:v1:{THREAD}:message-1",
            "talkroom_id": THREAD,
            "talkroom_url": THREAD_URL,
            "origin_at": "1970-01-01T00:01:40+00:00",
        }

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, browser, *ticks):
        clock = iter(ticks).__next__
        return self.executor.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=clock,
            compose=Composer(),
            browser=browser,
            # E6a: see run_once below. Empty rather than None -- these fixtures are
            # pre-purchase enquiry threads, and None means "could not tell", which
            # refuse_fenced_talkroom rejects before nothing_to_say can be reached.
            paid_talkroom_ids=frozenset(),
        )

    def test_seller_last_closes_the_entry_instead_of_raising(self):
        browser = SellerLastBrowser()

        result = self.execute(browser, 101, 102, 103, 104)

        self.assertEqual(result["status"], "nothing_to_say")
        self.assertEqual(result["reason"], "seller_last")
        self.assertEqual(browser.events, ["read_before"], "must not fill or click")
        stored = self.outbox.get_action(int(self.action["action_id"]))
        self.assertIsNotNone(stored["dlq_at"], "the entry must leave the queue")
        self.assertIsNone(self.outbox.pending_action_for_thread(THREAD))
        self.assertEqual(self.outbox.pending_actions(), [])

    def test_nothing_to_say_never_claims_the_buyer_was_replied_to(self):
        self.execute(SellerLastBrowser(), 101, 102, 103, 104)

        stored = self.outbox.get_action(int(self.action["action_id"]))
        self.assertNotEqual(stored["state"], "replied")
        self.assertIsNone(stored["verified_outgoing_hash"])
        self.assertIsNone(stored["seller_sent_at"])
        closed = self.outbox.closed_actions(closure="nothing_to_say")
        self.assertEqual([entry["action_id"] for entry in closed],
                         [int(self.action["action_id"])])
        self.assertEqual(closed[0]["reason"], "nothing_to_say:seller_last")
        self.assertEqual(self.outbox.dlq_actions(), [],
                         "a clean closure is not a fault needing repair")

    def test_a_new_buyer_message_makes_the_room_actionable_again(self):
        self.execute(SellerLastBrowser(), 101, 102, 103, 104)
        closed_id = int(self.action["action_id"])

        reopened = self.outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key(THREAD, "message-2"),
            thread_id=THREAD,
            thread_url=THREAD_URL,
            observed_at=500,
        )

        self.assertNotEqual(int(reopened["action_id"]), closed_id)
        self.assertEqual(reopened["state"], "pending")
        self.assertIsNone(reopened["dlq_at"])
        self.assertEqual(
            [action["action_id"] for action in self.outbox.pending_actions()],
            [int(reopened["action_id"])],
        )
        self.assertIsNotNone(self.outbox.pending_action_for_thread(THREAD))

    def test_a_buyer_last_thread_is_still_answered(self):
        """The guard must close nothing that a buyer is waiting on."""
        browser = SellerLastBrowser(last_side="buyer")

        result = self.execute(browser, 101, 102, 103, 104, 105)

        self.assertNotEqual(result["status"], "nothing_to_say")
        self.assertEqual(browser.events[:3], ["read_before", "fill", "click"])
        self.assertIsNone(self.outbox.get_action(int(self.action["action_id"]))["dlq_at"])
        self.assertEqual(self.outbox.closed_actions(), [])

    def test_closure_refuses_to_run_once_an_intent_exists(self):
        action = self.outbox.claim(owner="worker-1", now=101, lease_seconds=600)
        self.outbox.prepare_intent(
            int(action["action_id"]),
            owner="worker-1",
            fencing_token=int(action["fencing_token"]),
            outgoing_body="already prepared",
            now=102,
            origin_at=100,
        )

        with self.assertRaises(self.outbox_module.InvalidTransition):
            self.outbox.close_nothing_to_say(
                int(action["action_id"]),
                owner="worker-1",
                fencing_token=int(action["fencing_token"]),
                reason="seller_last",
                now=103,
            )


class ConsecutiveFailureDeadLetterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.outbox_module = load("connector_outbox")
        self.action_module = load("reply_action")
        self.outbox = self.outbox_module.ConnectorOutbox(self.database, MANIFEST)
        self.action = self.outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key("93000002", "message-1"),
            thread_id="93000002",
            thread_url="https://coconala.com/mypage/direct_message/93000002",
            observed_at=100,
        )
        self.limit = self.action_module.DLQ_AFTER_CONSECUTIVE_FAILURES

    def tearDown(self):
        self.temp.cleanup()

    def fail_once(self, outbox, now, error_class="RuntimeError:missing_message_input"):
        return outbox.record_thread_failure(
            thread_id="93000002",
            error_class=error_class,
            now=now,
            dead_letter_after=self.limit,
        )

    def test_n_minus_one_consecutive_failures_keep_the_entry(self):
        for index in range(self.limit - 1):
            result = self.fail_once(self.outbox, 200 + index)
            self.assertEqual(result["consecutive"], index + 1)
            self.assertFalse(result["dead_lettered"])

        self.assertIsNone(self.outbox.get_action(int(self.action["action_id"]))["dlq_at"])
        self.assertIsNotNone(self.outbox.pending_action_for_thread("93000002"))

    def test_the_nth_consecutive_failure_dead_letters(self):
        for index in range(self.limit):
            result = self.fail_once(self.outbox, 200 + index)

        self.assertTrue(result["dead_lettered"])
        self.assertEqual(
            result["reason"],
            "consecutive_failures:RuntimeError:missing_message_input",
        )
        self.assertIsNotNone(self.outbox.get_action(int(self.action["action_id"]))["dlq_at"])
        self.assertIsNone(self.outbox.pending_action_for_thread("93000002"))
        self.assertEqual([entry["action_id"] for entry in self.outbox.dlq_actions()],
                         [int(self.action["action_id"])])

    def test_a_pass_that_did_not_raise_resets_the_run(self):
        for index in range(self.limit - 1):
            self.fail_once(self.outbox, 200 + index)

        self.outbox.clear_thread_failure_streak("93000002")

        self.assertIsNone(self.outbox.thread_failure_streak("93000002"))
        result = self.fail_once(self.outbox, 300)
        self.assertEqual(result["consecutive"], 1)
        self.assertFalse(result["dead_lettered"])
        self.assertIsNone(self.outbox.get_action(int(self.action["action_id"]))["dlq_at"])

    def test_a_different_error_class_restarts_the_run(self):
        for index in range(self.limit - 1):
            self.fail_once(self.outbox, 200 + index)

        result = self.fail_once(self.outbox, 300, error_class="ValueError:other")

        self.assertEqual(result["consecutive"], 1)
        self.assertFalse(result["dead_lettered"])

    def test_the_streak_survives_the_process(self):
        """The detector is a fresh process every 300s; memory is not a counter."""
        for index in range(self.limit - 1):
            self.fail_once(self.outbox, 200 + index)

        reopened = self.outbox_module.ConnectorOutbox(self.database, MANIFEST)

        self.assertEqual(
            int(reopened.thread_failure_streak("93000002")["consecutive"]),
            self.limit - 1,
        )
        result = self.fail_once(reopened, 400)
        self.assertEqual(result["consecutive"], self.limit)
        self.assertTrue(result["dead_lettered"])

    def test_a_dead_letter_is_recoverable_without_hand_editing_sqlite(self):
        for index in range(self.limit):
            self.fail_once(self.outbox, 200 + index)
        action_id = int(self.action["action_id"])

        restored = self.outbox.requeue_closed_action(action_id, now=500)

        self.assertEqual(restored["state"], "pending")
        self.assertIsNone(restored["dlq_at"])
        self.assertIsNotNone(self.outbox.pending_action_for_thread("93000002"))
        self.assertEqual(self.outbox.dlq_actions(), [])
        self.assertIsNone(self.outbox.thread_failure_streak("93000002"))

    def test_requeue_refuses_to_collide_with_a_live_action(self):
        for index in range(self.limit):
            self.fail_once(self.outbox, 200 + index)
        successor = self.outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key("93000002", "message-2"),
            thread_id="93000002",
            thread_url="https://coconala.com/mypage/direct_message/93000002",
            observed_at=500,
        )
        self.assertNotEqual(int(successor["action_id"]), int(self.action["action_id"]))

        with self.assertRaises(self.outbox_module.InvalidTransition):
            self.outbox.requeue_closed_action(int(self.action["action_id"]), now=600)

    def test_failure_class_separates_kinds_but_ignores_live_numbers(self):
        failure_class = self.action_module.failure_class

        budget_a = failure_class(RuntimeError(
            'reply composer failed with rc=75: token_budget_exceeded",'
            '"daily_consumed_tokens":1047806}'
        ))
        budget_b = failure_class(RuntimeError(
            'reply composer failed with rc=75: token_budget_exceeded",'
            '"daily_consumed_tokens":1048001}'
        ))
        missing = failure_class(RuntimeError("missing_message_input"))

        self.assertEqual(budget_a, budget_b, "run-varying counts must not fork a streak")
        self.assertNotEqual(budget_a, missing, "two RuntimeErrors are not one fault")
        self.assertTrue(len(budget_a) <= 200)


class FillFailsBrowser(SellerLastBrowser):
    """A real executor failure used to exercise the bounded failure streak."""

    def __init__(self):
        super().__init__(last_side="buyer")

    def fill(self, body):
        self.events.append("fill")
        raise RuntimeError("reply_executor_failed")


class LaneTerminatesRepeatedFailureTest(unittest.TestCase):
    """The bulkhead used to swallow the failure and leave the entry claimable."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.outbox_module = load("connector_outbox")
        self.action_module = load("reply_action")
        self.lane = load("reply_lane")
        self.outbox = self.outbox_module.ConnectorOutbox(self.database, MANIFEST)
        self.action = self.outbox.enqueue(
            event_key=self.outbox_module.coconala_message_event_key(THREAD, "message-1"),
            thread_id=THREAD,
            thread_url=THREAD_URL,
            observed_at=100,
        )
        self.controller = self.action_module.ReplyActionController(self.database, MANIFEST)
        self.queue = {"status": "ready", "items": [{
            "event_key": f"coconala:message:v1:{THREAD}:message-1",
            "covered_event_keys": [f"coconala:message:v1:{THREAD}:message-1"],
            "talkroom_id": THREAD,
            "talkroom_url": THREAD_URL,
            "origin_at": "1970-01-01T00:01:40+00:00",
        }]}
        self.limit = self.action_module.DLQ_AFTER_CONSECUTIVE_FAILURES

    def tearDown(self):
        self.temp.cleanup()

    def run_once(self, now, browser):
        return self.lane.process_queue(
            controller=self.controller,
            queue=self.queue,
            compose=Composer(),
            browser_factory=lambda action, item: browser,
            owner_prefix="lane-test",
            clock=lambda: now,
            # E6a: TODO 3c made this keyword-only argument required. Empty, not None:
            # these fixtures are pre-purchase enquiry threads, and None would make
            # refuse_fenced_talkroom reject every one of them before the behaviour
            # under test -- the retry bound -- could run at all.
            paid_talkroom_ids=frozenset(),
            max_model_calls=None,
        )

    def test_the_lane_stops_retrying_after_the_bound_and_says_so(self):
        for index in range(self.limit):
            summary = self.run_once(200 + index * 300, FillFailsBrowser())
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["errors"][0]["consecutive"], index + 1)

        self.assertEqual(summary["dlq"], 1)
        self.assertEqual(len(summary["dlq_events"]), 1)
        self.assertEqual(summary["dlq_events"][0]["talkroom_id"], THREAD)
        self.assertEqual(summary["dlq_events"][0]["consecutive"], self.limit)
        self.assertIsNotNone(self.outbox.get_action(int(self.action["action_id"]))["dlq_at"])

        after = self.run_once(200 + self.limit * 300, FillFailsBrowser())
        self.assertEqual(after["failed"], 0, "a closed entry is not retried")
        self.assertEqual(after["dlq"], 1)
        self.assertEqual(after["skipped"], 0)
        self.assertEqual(after["errors"][0]["status"], "dlq")
        self.assertEqual(after["dlq_events"], [])

    def test_bookkeeping_failure_cannot_escalate_into_a_lane_crash(self):
        """The counter guards the bulkhead; it must not become a way through it."""
        class Unavailable:
            def __init__(self, inner):
                self.inner = inner

            def __getattr__(self, name):
                return getattr(self.inner, name)

            def note_failure(self, **kwargs):
                raise RuntimeError("database is locked")

        self.controller = Unavailable(self.controller)

        summary = self.run_once(200, FillFailsBrowser())

        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["dlq"], 0)
        self.assertIn(
            "failure_bookkeeping_unavailable: RuntimeError",
            summary["errors"][0]["errors"],
        )

    def test_a_pass_that_did_not_raise_clears_the_lane_streak(self):
        for index in range(self.limit - 1):
            self.run_once(200 + index * 300, FillFailsBrowser())
        self.assertEqual(
            int(self.outbox.thread_failure_streak(THREAD)["consecutive"]), self.limit - 1
        )

        summary = self.run_once(200 + self.limit * 300, SellerLastBrowser())

        self.assertEqual(summary["nothing_to_say"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertIsNone(self.outbox.thread_failure_streak(THREAD))


class DeadLetterIsAnnouncedTest(unittest.TestCase):
    """A dead letter is the one outcome that looks like silence from every angle."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = load("telegram_report")
        self.outbox = load("telegram_outbox").TelegramOutbox(self.root / "telegram.sqlite3")
        self.sent: list[str] = []
        self.entry = {
            "action_id": 70,
            "talkroom_id": "93000002",
            "reason": "consecutive_failures:RuntimeError:missing_message_input",
            "error_class": "RuntimeError:missing_message_input",
            "consecutive": 5,
        }

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, message):
        self.sent.append(message)
        return f"stub-{len(self.sent)}"

    def publish(self):
        return self.report.publish_reply_dlq_alerts(
            events=[self.entry],
            outbox=self.outbox,
            route="Test",
            transport=self.transport,
            now_epoch=1000,
        )

    def test_one_alert_per_entry_no_matter_how_often_it_is_republished(self):
        self.assertEqual(self.publish(), {"sent": 1, "delivery_unknown": 0})
        self.assertEqual(self.publish(), {"sent": 0, "delivery_unknown": 0})

        self.assertEqual(len(self.sent), 1)
        self.assertIn("93000002", self.sent[0])
        self.assertIn("5", self.sent[0])

    def test_the_alert_names_the_recovery_and_admits_no_reply_was_sent(self):
        self.publish()

        self.assertIn("requeue_closed_action(action_id=70)", self.sent[0])
        self.assertIn("返信していません", self.sent[0])

    def test_an_empty_dead_letter_list_says_nothing(self):
        result = self.report.publish_reply_dlq_alerts(
            events=[], outbox=self.outbox, route="Test",
            transport=self.transport, now_epoch=1000,
        )

        self.assertEqual(result, {"sent": 0, "delivery_unknown": 0})
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
