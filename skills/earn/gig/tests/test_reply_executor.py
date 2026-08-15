import hashlib
import importlib.util
import inspect
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBrowser:
    def __init__(self, controller, action_id, *, fail_click=False):
        self.controller = controller
        self.action_id = action_id
        self.fail_click = fail_click
        self.events = []
        self.body = ""
        self.url = "https://coconala.com/mypage/direct_message/42"

    def read_before(self):
        self.events.append("read_before")
        return (
            {"latest_buyer_message": "private buyer question"},
            {"talkroom_id": "42", "url": self.url, "fingerprint": "before", "seller_count": 1},
        )

    def fill(self, body):
        self.events.append("fill")
        self.body = body

    def click(self):
        self.events.append("click")
        state = self.controller.outbox.get_action(self.action_id)["state"]
        if state != "reconcile_pending":
            raise AssertionError("browser click occurred before click authorization CAS")
        if self.fail_click:
            raise RuntimeError("ambiguous click failure")

    def read_after(self):
        self.events.append("read_after")
        digest = hashlib.sha256(self.body.encode()).hexdigest()
        return {
            "talkroom_id": "42",
            "url": self.url,
            "fingerprint": "after",
            "seller_count": 2,
            "seller_message_hashes": [digest],
            "seller_sent_at": "1970-01-01T00:01:45+00:00",
            "last_sender": "seller",
        }

    def failure_evidence(self, error):
        return {
            "status": "read_failed",
            "send_network": [],
            "browser_error_code": "click_transport_failed",
        }


class BuyerFollowUpWithoutOutgoingBrowser(FakeBrowser):
    old_hash = "a" * 64
    old_sent_at = "1970-01-01T00:01:39+00:00"

    def read_before(self):
        self.events.append("read_before")
        return (
            {"latest_buyer_message": "private buyer question"},
            {
                "talkroom_id": "42",
                "url": self.url,
                "fingerprint": "before",
                "seller_count": 1,
                "seller_message_hashes": [self.old_hash],
                "seller_messages": [{
                    "body_sha256": self.old_hash,
                    "sent_at": self.old_sent_at,
                }],
            },
        )

    def read_after(self):
        self.events.append("read_after")
        return {
            "talkroom_id": "42",
            "url": self.url,
            "fingerprint": "after-buyer-follow-up",
            "seller_count": 1,
            "seller_message_hashes": [self.old_hash],
            "seller_messages": [{
                "body_sha256": self.old_hash,
                "sent_at": self.old_sent_at,
            }],
            "seller_sent_at": self.old_sent_at,
            "latest_buyer_sent_at": "1970-01-01T00:01:44+00:00",
            "last_sender": "buyer",
        }


class DomNormalizingBrowser(FakeBrowser):
    def fill(self, body):
        super().fill(body.replace("\r\n", "\n").replace("\r", "\n"))


class AlreadyDeliveredBeforeBrowser(FakeBrowser):
    """Thread already shows the exact outgoing body (an earlier pass delivered it)."""

    def __init__(self, controller, action_id, body):
        super().__init__(controller, action_id)
        digest = hashlib.sha256(body.encode()).hexdigest()
        self.before_messages = [{
            "body_sha256": digest,
            "sent_at": "1970-01-01T00:01:35+00:00",
        }]

    def read_before(self):
        self.events.append("read_before")
        return (
            {"latest_buyer_message": "private buyer question"},
            {
                "talkroom_id": "42",
                "url": self.url,
                "fingerprint": "before",
                "seller_count": 1,
                "seller_message_hashes": [
                    message["body_sha256"] for message in self.before_messages
                ],
                "seller_messages": list(self.before_messages),
                "last_sender": "seller",
            },
        )


class ReplyExecutorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
        outbox_module = load("connector_outbox")
        outbox = outbox_module.ConnectorOutbox(self.database, self.manifest)
        self.action = outbox.enqueue(
            event_key=outbox_module.coconala_message_event_key("42", "message-1"),
            thread_id="42",
            thread_url="https://coconala.com/mypage/direct_message/42",
            observed_at=100,
        )
        action_module = load("reply_action")
        self.controller = action_module.ReplyActionController(self.database, self.manifest)
        self.executor_module = load("reply_executor")
        self.queue_item = {
            "event_key": "coconala:message:v1:42:message-1",
            "talkroom_id": "42",
            "talkroom_url": "https://coconala.com/mypage/direct_message/42",
            "origin_at": "1970-01-01T00:01:40+00:00",
        }

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def clock(*values):
        ticks = iter(values)
        return lambda: next(ticks)

    def test_an_internal_token_is_refused_before_the_body_reaches_the_form(self):
        # Order 91000002 read 「パッケージSHA-256: f0ce9706...」 on 2026-08-06 because nothing
        # inspected the body at the last point where refusing is still free. A model that
        # echoes an internal token must lose its reply, not the buyer's trust -- and it must
        # lose it BEFORE fill, so no click is ever authorized.
        browser = FakeBrowser(self.controller, self.action["action_id"])

        with self.assertRaisesRegex(ValueError, "buyer_style_violation"):
            self.executor_module.execute_reply(
                controller=self.controller,
                queue_item=self.queue_item,
                owner="worker-1",
                clock=self.clock(101, 102, 103, 106),
                compose=lambda context: (
                    "ご確認ください。パッケージSHA-256: " + "a" * 64
                ),
                browser=browser,
                paid_talkroom_ids=frozenset(),
            )

        self.assertEqual(browser.events, ["read_before"])
        self.assertNotIn("fill", browser.events)
        self.assertNotIn("click", browser.events)

    def test_an_ordinary_japanese_reply_is_not_blocked_by_the_style_gate(self):
        # The gate sits in front of every reply, so a false positive costs a real buyer.
        browser = FakeBrowser(self.controller, self.action["action_id"])

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: (
                "お問い合わせありがとうございます。ご希望の内容で対応可能です。"
                "ご購入後、当日中に初稿をお送りします。"
            ),
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        self.assertEqual(result["status"], "replied")
        self.assertEqual(browser.events, ["read_before", "fill", "click", "read_after"])

    def test_model_only_composes_and_click_occurs_after_intent_cas(self):
        browser = FakeBrowser(self.controller, self.action["action_id"])
        contexts = []

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: contexts.append(context) or "specific helpful reply",
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        self.assertEqual(result["status"], "replied")
        self.assertEqual(browser.events, ["read_before", "fill", "click", "read_after"])
        self.assertEqual(contexts, [{"latest_buyer_message": "private buyer question"}])
        self.assertEqual(self.controller.outbox.get_action(self.action["action_id"])["state"], "replied")

    def test_composer_newlines_are_dom_compatible_before_intent_and_fill(self):
        browser = DomNormalizingBrowser(self.controller, self.action["action_id"])
        composed = "start\rone\r\ntwo\nend"
        canonical = "start\none\ntwo\nend"

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: composed,
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        self.assertEqual(result["status"], "replied")
        self.assertEqual(browser.body, canonical)
        self.assertEqual(
            stored["verified_outgoing_hash"],
            hashlib.sha256(canonical.encode()).hexdigest(),
        )
        self.assertEqual(
            self.executor_module.dom_compatible_outgoing_body("\r\n\rvalue\r"),
            "\n\nvalue\n",
        )

    def test_default_lease_outlives_coconala_native_submit_timeout(self):
        browser_module = load("coconala_reply_browser")
        composer_module = load("reply_composer")
        lease_default = inspect.signature(
            self.executor_module.execute_reply
        ).parameters["lease_seconds"].default
        composer_timeout = inspect.signature(
            composer_module.RunnerComposer.__init__
        ).parameters["timeout_seconds"].default

        self.assertGreater(
            lease_default,
            browser_module.NATIVE_SUBMIT_TIMEOUT_SECONDS,
        )
        self.assertGreater(lease_default, composer_timeout)

    def test_click_renews_short_initial_lease_through_stalled_post_finalize(self):
        browser = FakeBrowser(
            self.controller,
            self.action["action_id"],
            fail_click=True,
        )

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 524),
            compose=lambda context: "possibly sent reply",
            browser=browser,
            paid_talkroom_ids=frozenset(),
            lease_seconds=5,
        )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            slot = connection.execute(
                "SELECT action_id,owner,lease_until FROM connector_slots WHERE platform='coconala'"
            ).fetchone()
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertIsNone(stored["owner"])
        self.assertIsNone(slot["action_id"])
        self.assertIsNone(slot["owner"])
        self.assertEqual(slot["lease_until"], 0)

    def test_expired_pre_click_owner_is_requeued_and_slot_released_without_click(self):
        browser = FakeBrowser(self.controller, self.action["action_id"])

        with self.assertRaisesRegex(Exception, "stale"):
            self.executor_module.execute_reply(
                controller=self.controller,
                queue_item=self.queue_item,
                owner="worker-1",
                clock=self.clock(101, 1300, 1302, 1303),
                compose=lambda context: "specific helpful reply",
                browser=browser,
                paid_talkroom_ids=frozenset(),
                lease_seconds=1200,
            )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            slot = connection.execute(
                "SELECT action_id,owner,lease_until FROM connector_slots WHERE platform='coconala'"
            ).fetchone()
        self.assertEqual(stored["state"], "pending")
        self.assertIsNone(stored["owner"])
        self.assertIsNone(slot["action_id"])
        self.assertIsNone(slot["owner"])
        self.assertEqual(slot["lease_until"], 0)
        self.assertEqual(browser.events, ["read_before", "fill"])

    def test_composer_failure_is_proven_pre_click_and_requeued(self):
        browser = FakeBrowser(self.controller, self.action["action_id"])

        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            self.executor_module.execute_reply(
                controller=self.controller,
                queue_item=self.queue_item,
                owner="worker-1",
                clock=self.clock(101, 102),
                compose=lambda context: (_ for _ in ()).throw(RuntimeError("model unavailable")),
                browser=browser,
                paid_talkroom_ids=frozenset(),
            )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        self.assertEqual(stored["state"], "pending")
        self.assertEqual(browser.events, ["read_before"])

    def test_click_exception_is_ambiguous_and_never_requeued_blindly(self):
        browser = FakeBrowser(self.controller, self.action["action_id"], fail_click=True)

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 104),
            compose=lambda context: "possibly sent reply",
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(result["errors"], [
            "post_send_ground_truth_unavailable",
            "send_request_not_observed",
            "click_transport_failed",
        ])
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertIsNone(stored["owner"])
        self.assertEqual(browser.events, ["read_before", "fill", "click"])

    def test_failure_injection_same_hash_in_thread_is_refused_before_send(self):
        # A21 (a): the exact body hash is already visible in the talkroom, so the
        # send is refused BEFORE fill/click and the action closes already_delivered.
        body = "identical progress message"
        browser = AlreadyDeliveredBeforeBrowser(
            self.controller, self.action["action_id"], body
        )

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102),
            compose=lambda context: body,
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            slot = connection.execute(
                "SELECT action_id,owner,lease_until FROM connector_slots WHERE platform='coconala'"
            ).fetchone()
        self.assertEqual(result["status"], "already_delivered")
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(browser.events, ["read_before"])
        self.assertEqual(stored["state"], "replied")
        self.assertEqual(
            stored["verified_outgoing_hash"],
            hashlib.sha256(body.encode()).hexdigest(),
        )
        self.assertIsNone(stored["owner"])
        self.assertIsNone(slot["action_id"])
        closures = (self.database.parent / "connector-outbox-closures.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(closures), 1)
        record = json.loads(closures[0])
        self.assertEqual(record["closure"], "already_delivered")
        self.assertEqual(record["thread_id"], "42")

    def test_failure_injection_previously_replied_hash_blocks_resend_via_outbox_history(self):
        # A21 (a)+2: even when the live DOM read misses the old message, the outbox
        # history (a replied action with the same verified hash on this thread)
        # refuses the resend.
        body = "identical progress message"
        first_browser = FakeBrowser(self.controller, self.action["action_id"])
        first = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: body,
            browser=first_browser,
            paid_talkroom_ids=frozenset(),
        )
        self.assertEqual(first["status"], "replied")

        outbox_module = load("connector_outbox")
        second_action = self.controller.outbox.enqueue(
            event_key=outbox_module.coconala_message_event_key("42", "message-2"),
            thread_id="42",
            thread_url="https://coconala.com/mypage/direct_message/42",
            observed_at=200,
        )
        second_browser = FakeBrowser(self.controller, second_action["action_id"])
        second_item = dict(
            self.queue_item,
            event_key="coconala:message:v1:42:message-2",
            origin_at="1970-01-01T00:03:25+00:00",
        )

        second = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=second_item,
            owner="worker-2",
            clock=self.clock(206, 207),
            compose=lambda context: body,
            browser=second_browser,
            paid_talkroom_ids=frozenset(),
        )

        stored = self.controller.outbox.get_action(second_action["action_id"])
        self.assertEqual(second["status"], "already_delivered")
        self.assertEqual(second_browser.events, ["read_before"])
        self.assertEqual(stored["state"], "replied")
        self.assertIsNone(stored["owner"])

    def test_unknown_send_with_buyer_follow_up_reaches_reconcile_pending_and_releases_owner(self):
        browser = BuyerFollowUpWithoutOutgoingBrowser(
            self.controller,
            self.action["action_id"],
        )

        result = self.executor_module.execute_reply(
            controller=self.controller,
            queue_item=self.queue_item,
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: "specific helpful reply",
            browser=browser,
            paid_talkroom_ids=frozenset(),
        )

        stored = self.controller.outbox.get_action(self.action["action_id"])
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["verified"])
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(result["errors"], ["reply_ground_truth_not_confirmed"])
        self.assertEqual(stored["state"], "reconcile_pending")
        self.assertIsNone(stored["owner"])
        self.assertEqual(browser.events, ["read_before", "fill", "click", "read_after"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
