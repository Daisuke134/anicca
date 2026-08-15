"""A4 execution: the lane fires, and firing it twice does not act twice.

test_retainer_followthrough.py proved the ledgers in isolation. This file drives the
executor that sits on top of them, because the failure that matters is not "the
ledger allowed a second write", it is "the pass ran again five minutes later and the
client got a second message". Every test here therefore runs the executor TWICE over
the same queue item and asserts the second run is inert.
"""

import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
JST = timezone(timedelta(hours=9))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OFFER_TEXT = (
    "買い手F様から三者面談の候補日時が届きました。面談日時を選択してください。\n"
    "◾️面談時間：\n30分\n\n◾️面談可能な時間帯：\n"
    "2026年08月03日 18:00 ~ 20:00\n\n面談日時を選択する"
)

INTERVIEW_ITEM = {
    "talkroom_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
    "talkroom_url": (
        "https://coconala.com/mypage/job_matching/job_talkroom/01KYPJ0M0ACF4DBAFSJVFN9K24"
    ),
    "application_status": "面談調整中",
    "title": "【長期・在宅】SNS投稿サポート",
    "event_key": "coconala:01KYPJ0M0ACF4DBAFSJVFN9K24:fallback:0:abc",
    "origin_at": "2026-07-29T15:32:00+00:00",
}

REPLY_ITEM = {
    "talkroom_id": "01KYNAE4J11Q5SZNF7905GKHT1",
    "talkroom_url": (
        "https://coconala.com/mypage/job_matching/job_talkroom/01KYNAE4J11Q5SZNF7905GKHT1"
    ),
    "application_status": "応募済み",
    "title": "LPとWeb広告のパフォーマンス分析",
    "event_key": "coconala:01KYNAE4J11Q5SZNF7905GKHT1:fallback:0:def",
    "origin_at": "2026-07-29T07:51:00+00:00",
}


class FakeBrowser:
    """A thread whose rendered state changes only when the platform would change it."""

    def __init__(self, world):
        self.world = world

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read_state(self):
        return self.world.state()

    def read_fresh(self):
        return self.world.state()

    def open_interview_modal(self):
        self.world.log.append("open_modal")
        return {"ok": True, "slots": self.world.slots}

    def select_slot(self, *, year, month, day_of_month, slot_label_text):
        self.world.log.append(
            f"select:{year}-{month:02d}-{day_of_month:02d}:{slot_label_text}"
        )
        return {"ok": True, "selected": slot_label_text}

    def advance_to_confirmation(self):
        self.world.log.append("advance")
        return {"ok": True, "dialog_text": self.world.confirmation_text}

    def confirm_interview(self, *, expected_date, expected_slot):
        # The real driver refuses to press when the summary names another slot; the
        # fake models that platform, so the executor's own contract stays honest.
        if expected_date not in self.world.confirmation_text:
            raise RuntimeError("confirmation_shows_another_slot")
        if expected_slot not in self.world.confirmation_text:
            raise RuntimeError("confirmation_shows_another_slot")
        self.world.log.append(f"confirm:{expected_date} {expected_slot}")
        self.world.confirmed = True
        return {"ok": True, "dialog_open": False}

    def dialog_state(self):
        return {"ok": True, "open": False, "text": "", "buttons": []}

    def click_dialog_button(self, label):
        self.world.log.append(f"dialog:{label}")
        return {"ok": True, "dialog_open": False, "dialog_text": ""}

    def close_interview_modal(self):
        return None

    def send_reply(self, body):
        self.world.log.append("send_reply")
        self.world.messages.append(
            {"side": "seller", "author": "自分", "sent_at": "2026-07-31 12:00", "body": body}
        )


class InterviewWorld:
    def __init__(self):
        self.confirmed = False
        self.slots = ["18:00~18:30", "18:30~19:00", "19:00~19:30", "19:30~20:00"]
        self.confirmation_text = "面談日時の確認 2026年08月03日 18:00~18:30"
        self.log = []
        self.messages = []

    def state(self):
        retainer = load("retainer_thread")
        return {
            "application_id": INTERVIEW_ITEM["talkroom_id"],
            "messages": [
                {"side": "system", "author": "システムメッセージ",
                 "sent_at": "2026-07-30 00:26", "body": OFFER_TEXT},
                {"side": "client", "author": "買い手F",
                 "sent_at": "2026-07-30 00:32", "body": "一度面談の機会を頂きたく"},
            ] + self.messages,
            "last_side": "seller" if self.messages else "client",
            "interview_offer": retainer.parse_interview_offer(OFFER_TEXT),
            "interview_confirmed": self.confirmed,
            "interview_select_button_present": not self.confirmed,
            "composer_present": True,
        }


class ReplyWorld:
    def __init__(self):
        self.log = []
        self.messages = []

    def state(self):
        return {
            "application_id": REPLY_ITEM["talkroom_id"],
            "messages": [
                # our application first, the client's request AFTER it: that ordering
                # is the whole reason this row is work at all.
                {"side": "seller", "author": "自分",
                 "sent_at": "2026-07-29 09:12", "body": "募集内容を拝見しました。"},
                {"side": "client", "author": "合同会社グッドスタッフ",
                 "sent_at": "2026-07-29 16:51",
                 "body": "ご都合の良い日時をいくつかお知らせいただけますでしょうか。"},
            ] + self.messages,
            "last_side": "seller" if self.messages else "client",
            "interview_offer": None,
            "interview_confirmed": False,
            "interview_select_button_present": False,
            "composer_present": True,
        }


class ExecutorHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.booking = load("retainer_booking").BookingLedger(root / "bookings.sqlite3")
        self.messages = load("retainer_message").MessageLedger(root / "messages.sqlite3")
        self.executor_module = load("retainer_executor")
        self.now = 1_000_000
        self.reports = []
        self.calendar_created = []
        self.calendar_present = {}

    def _executor(self, world, *, compose=None):
        def factory(_thread_id):
            return FakeBrowser(world)

        def report(event_key, message):
            self.reports.append((event_key, message))
            return f"msg-{len(self.reports)}"

        def readback(key):
            return self.calendar_present.get(key)

        def create(*, account, slot, summary, description, booking_key):
            self.calendar_created.append(booking_key)
            self.calendar_present[booking_key] = f"evt-{len(self.calendar_created)}"
            return self.calendar_present[booking_key]

        return self.executor_module.RetainerExecutor(
            booking_ledger=self.booking,
            message_ledger=self.messages,
            browser_factory=factory,
            calendar_account="operator@example.com",
            clock=lambda: self.now,
            report=report,
            compose=compose,
            calendar_readback=readback,
            calendar_create=create,
        )


class InterviewExecutionTest(ExecutorHarness):
    def _plan(self, executor, world):
        return executor.plan(
            item=INTERVIEW_ITEM,
            events=[],
            now=datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc),
        )

    def test_an_accepted_slot_is_booked_calendared_and_reported_exactly_once(self):
        world = InterviewWorld()
        executor = self._executor(world)
        plan = self._plan(executor, world)
        self.assertEqual(plan["action"], "schedule_interview")
        self.assertEqual(plan["decision"]["decision"], "accept")
        self.assertEqual(plan["decision"]["slot"]["start"], "2026-08-03T18:00:00+09:00")

        first = executor.execute(item=INTERVIEW_ITEM, plan=plan)
        self.assertEqual(first["status"], "confirmed")
        self.assertTrue(first["calendar_event_id"])
        self.assertEqual(first["telegram_message_id"], "msg-1")
        self.assertEqual(world.log, ["open_modal", "select:2026-08-03:18:00~18:30", "advance",
             "confirm:2026年08月03日 18:00~18:30"])

        # ---- the pass runs again five minutes later ----
        self.now += 300
        second_executor = self._executor(world)
        second_plan = self._plan(second_executor, world)
        self.assertEqual(second_plan["action"], "already_confirmed")
        second = second_executor.execute(item=INTERVIEW_ITEM, plan=second_plan)
        # Terminal, not "skipped": the tail is idempotent and re-entering it must
        # neither create a second calendar entry nor send a second report.
        self.assertEqual(second["status"], "confirmed")
        self.assertNotIn("telegram_message_id", second)
        self.assertEqual(
            world.log, ["open_modal", "select:2026-08-03:18:00~18:30", "advance",
             "confirm:2026年08月03日 18:00~18:30"],
            "the modal was driven a second time",
        )
        self.assertEqual(len(self.calendar_created), 1)
        self.assertEqual(len(self.reports), 1)

    def test_a_crash_after_the_click_never_clicks_again(self):
        world = InterviewWorld()
        executor = self._executor(world)
        plan = self._plan(executor, world)
        booking = self.booking.open_intent(
            thread_id=INTERVIEW_ITEM["talkroom_id"],
            offer_hash=plan["offer_hash"],
            decision=plan["decision"],
            now=self.now,
        )
        self.booking.mark_confirm_started(booking["booking_key"], now=self.now)
        # the click DID land, the process died before it could be recorded
        world.confirmed = True

        recovered = executor.execute(item=INTERVIEW_ITEM, plan=plan)
        self.assertEqual(recovered["status"], "confirmed")
        self.assertTrue(recovered.get("recovered"))
        self.assertEqual(world.log, [], "a recovering pass clicked 確認に進む blind")

    def test_a_click_that_did_not_land_is_not_reported_as_booked(self):
        world = InterviewWorld()
        executor = self._executor(world)
        plan = self._plan(executor, world)
        booking = self.booking.open_intent(
            thread_id=INTERVIEW_ITEM["talkroom_id"],
            offer_hash=plan["offer_hash"],
            decision=plan["decision"],
            now=self.now,
        )
        self.booking.mark_confirm_started(booking["booking_key"], now=self.now)

        result = executor.execute(item=INTERVIEW_ITEM, plan=plan)
        self.assertEqual(result["status"], "reconcile_pending")
        self.assertEqual(self.reports, [])
        self.assertEqual(self.calendar_created, [])
        self.assertTrue(self.booking.may_confirm(booking["booking_key"]))

    def test_a_booking_that_landed_while_the_ledger_says_intent_is_adopted(self):
        """The exact live shape on 2026-07-31: booked on the platform, `intent` here.

        The readback had misread the confirmation, so the row rolled back. Without
        adoption that row is either stranded (never calendared, never reported) or
        -- much worse -- treated as still owed and confirmed a second time.
        """
        world = InterviewWorld()
        executor = self._executor(world)
        plan = self._plan(executor, world)
        self.booking.open_intent(
            thread_id=INTERVIEW_ITEM["talkroom_id"],
            offer_hash=plan["offer_hash"],
            decision=plan["decision"],
            now=self.now,
        )
        world.confirmed = True   # the platform now says it is agreed

        self.now += 300
        second = self._executor(world)
        confirmed_plan = self._plan(second, world)
        self.assertEqual(confirmed_plan["action"], "already_confirmed")
        self.assertEqual(confirmed_plan["offer_hash"], plan["offer_hash"])
        result = second.execute(item=INTERVIEW_ITEM, plan=confirmed_plan)
        self.assertEqual(result["status"], "confirmed")
        self.assertTrue(result["adopted"])
        self.assertEqual(len(self.calendar_created), 1)
        self.assertEqual(len(self.reports), 1)
        self.assertEqual(world.log, [], "an already-booked interview was driven again")

        # and a third pass is inert
        self.now += 300
        third = self._executor(world)
        third_result = third.execute(item=INTERVIEW_ITEM, plan=self._plan(third, world))
        self.assertEqual(third_result["status"], "confirmed")
        self.assertEqual(len(self.calendar_created), 1)
        self.assertEqual(len(self.reports), 1)

    def test_a_counter_proposal_is_not_fired_by_this_lane(self):
        """Its readback signal was never observed live, so it is not fired blind."""
        world = InterviewWorld()
        executor = self._executor(world)
        busy = [{
            "status": "confirmed",
            "start": {"dateTime": "2026-08-03T09:00:00+00:00"},
            "end": {"dateTime": "2026-08-03T11:00:00+00:00"},
        }]
        plan = executor.plan(
            item=INTERVIEW_ITEM,
            events=busy,
            now=datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(plan["decision"]["decision"], "counter_propose")
        result = executor.execute(item=INTERVIEW_ITEM, plan=plan)
        self.assertEqual(result["status"], "not_executed")
        self.assertEqual(world.log, [])
        self.assertEqual(self.reports, [])


class CalendarAddressTest(unittest.TestCase):
    """Measured live 2026-07-31, and it would have booked the wrong day.

    The modal opens on 2026年7月 and its grid renders June's tail and August's head,
    so the page contains "3" (July 3) while the offered 2026-08-03 is not on it at
    all -- and "1" appears twice. A bare day number is not an address.
    """

    def test_a_slot_carries_its_month_not_just_its_day(self):
        executor = load("retainer_executor")
        self.assertEqual(
            executor.slot_address({
                "start": "2026-08-03T18:00:00+09:00",
                "end": "2026-08-03T18:30:00+09:00",
            }),
            (2026, 8, 3, "18:00~18:30"),
        )

    def test_the_expression_walks_to_the_target_month_before_picking_a_day(self):
        browser = load("coconala_retainer_browser")
        expression = browser.select_slot_expression(
            year=2026, month=8, day_of_month=3, slot_label_text="18:00~18:30",
        )
        self.assertIn("2026年8月", expression)
        self.assertIn("次へ", expression)
        self.assertIn("month_unreachable", expression)
        # every day the platform did not offer is aria-disabled; only enabled ones count
        self.assertIn("aria-disabled", expression)
        self.assertIn("day_ambiguous", expression)

    def test_the_pressable_is_the_inner_react_aria_element_not_the_table_cell(self):
        """Measured live: clicking the <td> was a silent no-op that kept 7/31."""
        browser = load("coconala_retainer_browser")
        expression = browser.select_slot_expression(
            year=2026, month=8, day_of_month=3, slot_label_text="18:00~18:30",
        )
        self.assertIn("[role=button][data-react-aria-pressable]", expression)
        self.assertIn("pointerdown", expression)
        self.assertIn("pointerup", expression)
        for marker in ("dataset.disabled", "dataset.unavailable", "dataset.outsideMonth"):
            self.assertIn(marker, expression)

    def test_confirmation_is_refused_unless_the_dialog_names_our_slot(self):
        browser = load("coconala_retainer_browser")
        expression = browser.confirm_interview_expression(
            expected_date="2026年08月03日", expected_slot="18:00~18:30",
        )
        self.assertIn("2026年08月03日", expression)
        self.assertIn("18:00~18:30", expression)
        self.assertIn("confirmation_shows_another_slot", expression)
        self.assertIn("面談日時の確認", expression)
        self.assertIn("日程を確定する", expression)
        # the mismatch branch must come BEFORE any click
        self.assertLess(
            expression.index("confirmation_shows_another_slot"),
            expression.index("日程を確定する"),
        )

    def test_the_confirmation_date_is_spelled_the_way_the_platform_spells_it(self):
        browser = load("coconala_retainer_browser")
        self.assertEqual(
            browser.confirmation_date_text(year=2026, month=8, day=3), "2026年08月03日",
        )

    def test_an_impossible_calendar_target_is_refused_before_the_browser_sees_it(self):
        browser = load("coconala_retainer_browser")
        for bad in (
            {"year": 2026, "month": 13, "day_of_month": 3},
            {"year": 2026, "month": 8, "day_of_month": 0},
            {"year": 1999, "month": 8, "day_of_month": 3},
        ):
            with self.assertRaises(ValueError):
                browser.select_slot_expression(slot_label_text="18:00~18:30", **bad)


class ReplyExecutionTest(ExecutorHarness):
    def _plan(self, executor):
        return executor.plan(
            item=REPLY_ITEM,
            events=[],
            now=datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc),
        )

    def test_one_reply_per_inbound_message_even_across_passes(self):
        world = ReplyWorld()
        composed = []

        def compose(context):
            composed.append(context)
            self.assertEqual(context["conversation"][-1]["side"], "buyer")
            return "候補日時をお送りします。8月3日18:00〜などいかがでしょうか。"

        executor = self._executor(world, compose=compose)
        plan = self._plan(executor)
        self.assertEqual(plan["action"], "reply")
        first = executor.execute(item=REPLY_ITEM, plan=plan)
        self.assertEqual(first["status"], "sent")
        self.assertEqual(first["telegram_message_id"], "msg-1")
        self.assertEqual(world.log, ["send_reply"])
        self.assertEqual(len(composed), 1)

        self.now += 300
        second_executor = self._executor(world, compose=compose)
        second_plan = self._plan(second_executor)
        # The thread itself now says we hold the last word.
        self.assertEqual(second_plan["action"], "none")
        second = second_executor.execute(item=REPLY_ITEM, plan=second_plan)
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(world.log, ["send_reply"], "a second message was sent")
        self.assertEqual(len(self.reports), 1)
        self.assertEqual(len(composed), 1, "a second model call was spent")

    def test_a_send_of_unknown_outcome_is_read_back_not_resent(self):
        world = ReplyWorld()
        message_module = load("retainer_message")
        row = self.messages.open_intent(
            thread_id=REPLY_ITEM["talkroom_id"],
            event_key=REPLY_ITEM["event_key"],
            inbound_sent_at=REPLY_ITEM["origin_at"],
            now=self.now,
        )
        self.messages.mark_send_started(
            row["message_key"], attempt_hash=message_module.body_hash("x"), now=self.now,
        )
        # it actually landed; this process just never learned that
        world.messages.append({
            "side": "seller", "author": "自分",
            "sent_at": "2026-07-30 09:00", "body": "候補日時をお送りします。",
        })

        def compose(_context):
            raise AssertionError("a recovering pass must not compose a new message")

        executor = self._executor(world, compose=compose)
        result = executor.execute(item=REPLY_ITEM, plan={"action": "reply"})
        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["recovered"])
        self.assertEqual(world.log, [])
        self.assertEqual(len(self.reports), 1)

    def test_an_answer_that_already_exists_is_adopted_without_a_model_call(self):
        world = ReplyWorld()
        world.messages.append({
            "side": "seller", "author": "自分",
            "sent_at": "2026-07-30 09:00", "body": "先に手で返信済み",
        })

        def compose(_context):
            raise AssertionError("an already-answered thread must not be composed for")

        executor = self._executor(world, compose=compose)
        result = executor.execute(item=REPLY_ITEM, plan={"action": "reply"})
        self.assertEqual(result["status"], "already_answered")
        self.assertEqual(world.log, [])
        self.assertEqual(executor.model_calls, 0)

    def test_the_lane_budget_defers_rather_than_spending_a_second_call(self):
        world = ReplyWorld()
        executor = self._executor(world, compose=lambda _c: "ok")
        executor.model_calls = 1
        result = executor.execute(item=REPLY_ITEM, plan={"action": "reply"})
        self.assertEqual(result["status"], "deferred")
        self.assertEqual(world.log, [])


if __name__ == "__main__":
    unittest.main()
