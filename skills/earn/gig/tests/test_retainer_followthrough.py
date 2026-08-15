"""A4: carry already-submitted retainer applications to completion, no human loop.

Grounded on the real DOM captured 2026-07-30 from
https://coconala.com/mypage/job_matching/applied/outsource_applications and from
the 面談調整中 thread 01KYPJ0M0ACF4DBAFSJVFN9K24, which the reply lane has never
swept: its threads live under /mypage/job_matching/job_talkroom/<ULID>, a path the
connector outbox used to reject outright.
"""

import importlib.util
import json
import sqlite3
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


# --- real DOM, captured live 2026-07-30 (bodies trimmed, identities kept verbatim) ---

APPLICATIONS_DOM = {
    "url": "https://coconala.com/mypage/job_matching/applied/outsource_applications",
    "title": "応募・スカウト管理 | ココナラ",
    "container_present": True,
    "not_found_present": False,
    "error_present": False,
    "filters": {"all": 9, "unread": 1, "unanswered": 3},
    "cards": [
        {
            "application_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
            "thread_url": (
                "https://coconala.com/mypage/job_matching/job_talkroom/"
                "01KYPJ0M0ACF4DBAFSJVFN9K24"
            ),
            "title": "【長期・在宅】SNS投稿・更新サポートスタッフ募集｜未経験歓迎",
            "client": "買い手F",
            "last_message_at": "2026/07/30 00:32",
            "last_message_body": (
                "買い手E様 ご応募いただきありがとうございます。 一度面談の機会を頂きたく "
                "上記お時間帯にて面談を設定させていただきたいのですが ご調整可能でしょうか。"
            ),
            "applied_on": "2026/07/29",
            "offer_text": "提案額：1,500円/時間",
            "status": "面談調整中",
        },
        {
            "application_id": "01KYNAE4J11Q5SZNF7905GKHT1",
            "thread_url": (
                "https://coconala.com/mypage/job_matching/job_talkroom/"
                "01KYNAE4J11Q5SZNF7905GKHT1"
            ),
            "title": "LPとWeb広告のパフォーマンス分析・改善提案ができる方募集",
            "client": "合同会社グッドスタッフ",
            "last_message_at": "2026/07/29 16:51",
            "last_message_body": (
                "ご連絡いただきありがとうございます。 ぜひご相談をお願いできればと思っております。 "
                "つきましては、7月31日以降でご都合の良い日時をいくつかお知らせいただけますでしょうか。"
            ),
            "applied_on": "2026/07/29",
            "offer_text": "提案額：5,000円/時間",
            "status": "応募済み",
        },
        {
            # last message is our own application text -> nothing is waiting on us
            "application_id": "01KYSKA4XFNHVSKGEXQAZCV6SN",
            "thread_url": (
                "https://coconala.com/mypage/job_matching/job_talkroom/"
                "01KYSKA4XFNHVSKGEXQAZCV6SN"
            ),
            "title": "【完全在宅／未経験 OK】スキマ時間にコツコツ！商品情報のデータ入力・校正サポート",
            "client": "4110002026037",
            "last_message_at": "2026/07/30 22:27",
            "last_message_body": "募集内容を拝見し、商品画像・資料をもとにした商品情報の入力…",
            "applied_on": "2026/07/30",
            "offer_text": "提案額：4万円/月",
            "status": "応募済み",
            "last_message_side": "seller",
        },
        {
            # terminal: the client passed on us. Never queue, never message.
            "application_id": "01KYQ31TPSX55PZJP05VJHJYRZ",
            "thread_url": (
                "https://coconala.com/mypage/job_matching/job_talkroom/"
                "01KYQ31TPSX55PZJP05VJHJYRZ"
            ),
            "title": "オンライン秘書業務全般を担当する方を募集します",
            "client": "温故知新弐代目『かぶき者』 松本 マサヒデ",
            "last_message_at": "2026/07/29 23:09",
            "last_message_body": "",
            "applied_on": "2026/07/29",
            "offer_text": "提案額：1,200円/時間",
            "status": "お見送り",
        },
    ],
}

# The system message that carries the offer, verbatim from the live thread.
INTERVIEW_OFFER_TEXT = (
    "買い手F様から三者面談の候補日時が届きました。面談日時を選択してください。\n"
    "◾️面談時間：\n30分\n\n◾️面談可能な時間帯：\n"
    "2026年07月31日 18:00 ~ 20:00\n"
    "2026年08月03日 18:00 ~ 20:00\n"
    "2026年08月04日 18:00 ~ 20:00\n\n面談日時を選択する"
)

# The confirmation the platform posted at 2026-07-31 00:48, verbatim, once the
# booking really landed. Note that the OFFER message above kept its
# 「面談日時を選択する」 button after this arrived.
INTERVIEW_CONFIRMED_TEXT = (
    "買い手F様との三者面談の日時が確定しました。予定時間になったら、「面談に参加する」を"
    "押してください。(開始予定時間の5分前から参加できます。)\n"
    "面談日時：2026年08月03日 18:00〜18:30\n面談に参加する"
)

THREAD_DOM = {
    "url": (
        "https://coconala.com/mypage/job_matching/job_talkroom/"
        "01KYPJ0M0ACF4DBAFSJVFN9K24/talkroom"
    ),
    "application_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
    "container_present": True,
    "not_found_present": False,
    "error_present": False,
    "banner_text": (
        "三者面談の候補日時が届きました。メッセージを確認して、都合の良い日時を選択してください。"
    ),
    "interview_select_button_present": True,
    "composer_present": True,
    "messages": [
        {"author": "システムメッセージ", "sent_at": "2026-07-29 18:06", "body": "◎取引の流れについて"},
        {"author": "自分", "sent_at": "2026-07-29 18:06", "body": "募集内容を拝見しました。"},
        {"author": "システムメッセージ", "sent_at": "2026-07-30 00:26", "body": INTERVIEW_OFFER_TEXT},
        {"author": "買い手F", "sent_at": "2026-07-30 00:32", "body": "一度面談の機会を頂きたく"},
    ],
}


class RetainerQueueTest(unittest.TestCase):
    """DoD 3: the retainer tab has to reach the built queue at all."""

    def test_retainer_tab_threads_reach_the_queue_with_the_right_next_action(self):
        retainer = load("retainer_thread")
        queue = retainer.build_queue(
            {
                "captured_at": "2026-07-30T13:00:00+00:00",
                "retainer_applications": APPLICATIONS_DOM["cards"],
            },
            now=datetime(2026, 7, 30, 13, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(queue["status"], "ready", queue)
        self.assertEqual(queue["errors"], [])
        by_thread = {item["talkroom_id"]: item for item in queue["items"]}

        # the rotting 三者面談 thread the loop has never looked at
        self.assertIn("01KYPJ0M0ACF4DBAFSJVFN9K24", by_thread)
        scheduling = by_thread["01KYPJ0M0ACF4DBAFSJVFN9K24"]
        self.assertEqual(scheduling["next_action"], "schedule_interview")
        self.assertEqual(
            scheduling["talkroom_url"],
            "https://coconala.com/mypage/job_matching/job_talkroom/01KYPJ0M0ACF4DBAFSJVFN9K24",
        )
        self.assertEqual(scheduling["platform"], "coconala")
        self.assertEqual(scheduling["lane"], "retainer")

        # the client asked us for candidate times in free text -> a reply, not a click
        self.assertEqual(by_thread["01KYNAE4J11Q5SZNF7905GKHT1"]["next_action"], "reply")

        # our own last word, and a rejected application, are not work
        self.assertNotIn("01KYSKA4XFNHVSKGEXQAZCV6SN", by_thread)
        self.assertNotIn("01KYQ31TPSX55PZJP05VJHJYRZ", by_thread)

    def test_queue_items_carry_a_durable_event_identity_bound_to_the_thread(self):
        retainer = load("retainer_thread")
        outbox = load("connector_outbox")
        queue = retainer.build_queue(
            {
                "captured_at": "2026-07-30T13:00:00+00:00",
                "retainer_applications": APPLICATIONS_DOM["cards"],
            },
            now=datetime(2026, 7, 30, 13, 5, tzinfo=timezone.utc),
        )
        for item in queue["items"]:
            self.assertEqual(item["covered_event_keys"], [item["event_key"]])
            outbox.validate_coconala_event_key(item["event_key"], item["talkroom_id"])

    def test_job_talkroom_urls_are_accepted_by_the_durable_outbox(self):
        """They were rejected before: only /talkrooms and /mypage/direct_message existed."""
        outbox = load("connector_outbox")
        thread_id = "01KYPJ0M0ACF4DBAFSJVFN9K24"
        url = f"https://coconala.com/mypage/job_matching/job_talkroom/{thread_id}"
        self.assertEqual(outbox.ConnectorOutbox._canonical_thread_url(url, thread_id), url)
        with self.assertRaises(ValueError):
            outbox.ConnectorOutbox._canonical_thread_url(url + "/talkroom", thread_id)


class InterviewOfferParseTest(unittest.TestCase):
    def test_offer_windows_and_duration_come_off_the_real_system_message(self):
        retainer = load("retainer_thread")
        offer = retainer.parse_interview_offer(INTERVIEW_OFFER_TEXT)
        self.assertIsNotNone(offer)
        self.assertEqual(offer["duration_minutes"], 30)
        self.assertEqual(
            offer["windows"],
            [
                {"start": "2026-07-31T18:00:00+09:00", "end": "2026-07-31T20:00:00+09:00"},
                {"start": "2026-08-03T18:00:00+09:00", "end": "2026-08-03T20:00:00+09:00"},
                {"start": "2026-08-04T18:00:00+09:00", "end": "2026-08-04T20:00:00+09:00"},
            ],
        )

    def test_prose_without_an_offer_is_not_an_offer(self):
        retainer = load("retainer_thread")
        self.assertIsNone(
            retainer.parse_interview_offer(
                "つきましては、7月31日以降でご都合の良い日時をいくつかお知らせいただけますでしょうか。"
            )
        )

    def test_offered_windows_split_into_the_platforms_own_30_minute_slots(self):
        """The modal offers 18:00~18:30 / 18:30~19:00 / 19:00~19:30 / 19:30~20:00."""
        scheduler = load("interview_scheduler")
        retainer = load("retainer_thread")
        offer = retainer.parse_interview_offer(INTERVIEW_OFFER_TEXT)
        slots = scheduler.candidate_slots(offer)
        first_day = [s for s in slots if s["start"].startswith("2026-07-31")]
        self.assertEqual(
            [(s["start"][11:16], s["end"][11:16]) for s in first_day],
            [("18:00", "18:30"), ("18:30", "19:00"), ("19:00", "19:30"), ("19:30", "20:00")],
        )
        self.assertEqual(len(slots), 12)


class ThreadIsAuthoritativeTest(unittest.TestCase):
    """The applied tab shows a last message but never who wrote it.

    Live on 2026-07-30 the tab held 9 applications and said 未読1 / 未返信3, yet
    8 rows look identical from the list because most carry our own application
    text. Acting on the list alone would message six clients who are waiting on
    nobody, so the thread read decides, exactly as the direct-message lane does.
    """

    def test_queue_items_are_marked_as_needing_thread_confirmation(self):
        retainer = load("retainer_thread")
        queue = retainer.build_queue(
            {"captured_at": "2026-07-30T13:00:00+00:00",
             "retainer_applications": APPLICATIONS_DOM["cards"]},
            now=datetime(2026, 7, 30, 13, 5, tzinfo=timezone.utc),
        )
        for item in queue["items"]:
            self.assertTrue(item["requires_thread_confirmation"], item)

    def test_our_own_last_word_is_not_work_once_the_thread_is_read(self):
        lane = load("retainer_lane")
        retainer = load("retainer_thread")
        item = {"talkroom_id": "01KYR084FQ7KACP80TZ8XGD4GF",
                "talkroom_url": retainer.thread_url("01KYR084FQ7KACP80TZ8XGD4GF")}
        plan = lane.plan_thread(
            item=item,
            thread_state={"last_side": "seller", "interview_offer": None},
            events=[], now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(plan["action"], "none")
        self.assertEqual(plan["reason"], "seller_has_the_last_word")

    def test_a_client_waiting_on_us_is_work(self):
        lane = load("retainer_lane")
        retainer = load("retainer_thread")
        plan = lane.plan_thread(
            item={"talkroom_id": "01KYNAE4J11Q5SZNF7905GKHT1",
                  "talkroom_url": retainer.thread_url("01KYNAE4J11Q5SZNF7905GKHT1")},
            thread_state={"last_side": "client", "interview_offer": None},
            events=[], now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(plan["action"], "reply")

    def test_a_confirmed_interview_is_never_rebooked(self):
        lane = load("retainer_lane")
        retainer = load("retainer_thread")
        offer = retainer.parse_interview_offer(INTERVIEW_OFFER_TEXT)
        plan = lane.plan_thread(
            item={"talkroom_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
                  "talkroom_url": retainer.thread_url("01KYPJ0M0ACF4DBAFSJVFN9K24")},
            thread_state={"last_side": "client", "interview_offer": offer,
                          "interview_confirmed": True},
            events=[], now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(plan["action"], "already_confirmed")

    def test_the_flow_explainer_is_not_mistaken_for_a_booked_interview(self):
        """Every retainer thread says 「面談日時と参加用URLが届きます」 in its
        取引の流れ boilerplate. A text match reads that as already-booked and the
        loop then never books anything. Measured live on 01KYPJ0M0ACF4DBAFSJVFN9K24.
        """
        retainer = load("retainer_thread")
        dom = dict(THREAD_DOM)
        dom["messages"] = list(THREAD_DOM["messages"]) + [{
            "author": "システムメッセージ", "sent_at": "2026-07-29 18:06",
            "body": "・日時が確定したら、面談日時と参加用URLが届きます。",
        }]
        dom["interview_select_button_present"] = True
        self.assertFalse(retainer.thread_state(dom)["interview_confirmed"])

    def test_the_platforms_own_announcement_is_what_proves_the_booking(self):
        """Corrected against the live thread on 2026-07-31 -- see the DOM below.

        The previous rule here was "an offer exists and 面談日時を選択する is gone".
        It was wrong: after the interview really was booked, the OFFER message still
        rendered its 面談日時を選択する button, so the lane read a booked interview as
        unbooked and would have booked it a second time. The signal that is actually
        true is the platform's own confirmation message, which carries the time.
        """
        retainer = load("retainer_thread")
        dom = dict(THREAD_DOM)
        dom["messages"] = list(THREAD_DOM["messages"]) + [{
            "author": "システムメッセージ", "sent_at": "2026-07-31 00:48",
            "body": INTERVIEW_CONFIRMED_TEXT,
        }]
        dom["interview_select_button_present"] = True   # verbatim from the live page
        state = retainer.thread_state(dom)
        self.assertTrue(state["interview_confirmed"])
        self.assertEqual(
            state["confirmed_interview"],
            {"start": "2026-08-03T18:00:00+09:00", "end": "2026-08-03T18:30:00+09:00"},
        )

    def test_a_vanished_select_button_alone_does_not_prove_a_booking(self):
        retainer = load("retainer_thread")
        dom = dict(THREAD_DOM)
        dom["interview_select_button_present"] = False
        self.assertFalse(retainer.thread_state(dom)["interview_confirmed"])

    def test_a_confirmation_without_a_time_is_not_a_confirmation(self):
        retainer = load("retainer_thread")
        self.assertIsNone(retainer.parse_interview_confirmation(
            "買い手F様との三者面談の日時が確定しました。"
        ))
        self.assertIsNone(retainer.parse_interview_confirmation(
            "・日時が確定したら、面談日時と参加用URLが届きます。"
        ))

    def test_a_thread_that_was_never_offered_an_interview_is_not_confirmed(self):
        retainer = load("retainer_thread")
        self.assertFalse(
            retainer.thread_state({
                "application_id": "01KYNAE4J11Q5SZNF7905GKHT1",
                "interview_select_button_present": True,
                "messages": [{"author": "合同会社グッドスタッフ",
                              "sent_at": "2026-07-29 16:51", "body": "ご連絡ありがとうございます"}],
            })["interview_confirmed"]
        )

    def test_thread_dom_attribution_matches_the_live_thread(self):
        retainer = load("retainer_thread")
        state = retainer.thread_state(THREAD_DOM)
        self.assertEqual(
            [row["side"] for row in state["messages"]],
            ["system", "seller", "system", "client"],
        )
        self.assertEqual(state["last_side"], "client")
        self.assertIsNotNone(state["interview_offer"])
        self.assertEqual(state["interview_offer"]["duration_minutes"], 30)


class SchedulingDecisionTest(unittest.TestCase):
    """DoD 4: the decision is made here, from Dais's calendar, never handed to Dais."""

    def _offer(self):
        return load("retainer_thread").parse_interview_offer(INTERVIEW_OFFER_TEXT)

    def test_a_conflict_pushes_the_choice_to_the_next_free_slot(self):
        scheduler = load("interview_scheduler")
        busy = [
            # blocks 18:00-19:00 on the first offered day only
            {"start": {"dateTime": "2026-07-31T18:00:00+09:00"},
             "end": {"dateTime": "2026-07-31T19:00:00+09:00"},
             "summary": "existing", "status": "confirmed"},
        ]
        decision = scheduler.choose_slot(
            offer=self._offer(),
            events=busy,
            now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["decision"], "accept")
        self.assertEqual(decision["slot"]["start"], "2026-07-31T19:00:00+09:00")
        self.assertEqual(decision["slot"]["end"], "2026-07-31T19:30:00+09:00")

    def test_free_time_takes_the_earliest_offered_slot(self):
        scheduler = load("interview_scheduler")
        decision = scheduler.choose_slot(
            offer=self._offer(),
            events=[],
            now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["decision"], "accept")
        self.assertEqual(decision["slot"]["start"], "2026-07-31T18:00:00+09:00")

    def test_transparent_and_cancelled_events_do_not_block(self):
        scheduler = load("interview_scheduler")
        decision = scheduler.choose_slot(
            offer=self._offer(),
            events=[
                {"start": {"dateTime": "2026-07-31T18:00:00+09:00"},
                 "end": {"dateTime": "2026-07-31T20:00:00+09:00"},
                 "transparency": "transparent", "status": "confirmed"},
                {"start": {"dateTime": "2026-07-31T18:00:00+09:00"},
                 "end": {"dateTime": "2026-07-31T20:00:00+09:00"},
                 "status": "cancelled"},
            ],
            now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["decision"], "accept")
        self.assertEqual(decision["slot"]["start"], "2026-07-31T18:00:00+09:00")

    def test_a_fully_booked_offer_counter_proposes_instead_of_asking_a_human(self):
        scheduler = load("interview_scheduler")
        busy = [
            {"start": {"dateTime": f"2026-{m:02d}-{d:02d}T00:00:00+09:00"},
             "end": {"dateTime": f"2026-{m:02d}-{d:02d}T23:59:00+09:00"},
             "status": "confirmed"}
            for m, d in ((7, 31), (8, 3), (8, 4))
        ]
        decision = scheduler.choose_slot(
            offer=self._offer(),
            events=busy,
            now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["decision"], "counter_propose")
        self.assertTrue(decision["proposals"], decision)
        # proposals must be real free time, inside the band the client asked for
        for proposal in decision["proposals"]:
            self.assertRegex(proposal["start"], r"T(1[89]|20):")
            for blocked in busy:
                self.assertFalse(proposal["start"].startswith(blocked["start"]["dateTime"][:10]))

    def test_no_decision_path_ever_escalates_to_a_human(self):
        """Dais rejected 'send him the slots and let him pick'. There is no such branch."""
        scheduler = load("interview_scheduler")
        allowed = {"accept", "counter_propose"}
        for events in ([], [{"start": {"dateTime": "2026-07-31T00:00:00+09:00"},
                             "end": {"dateTime": "2026-08-05T00:00:00+09:00"},
                             "status": "confirmed"}]):
            decision = scheduler.choose_slot(
                offer=self._offer(), events=events,
                now=datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc),
            )
            self.assertIn(decision["decision"], allowed)
        self.assertNotIn("ask_human", scheduler.DECISIONS)
        source = (SCRIPTS / "interview_scheduler.py").read_text(encoding="utf-8")
        self.assertNotIn("ask_dais", source)

    def test_slots_that_already_started_are_never_chosen(self):
        scheduler = load("interview_scheduler")
        decision = scheduler.choose_slot(
            offer=self._offer(),
            events=[],
            # 2026-07-31 18:40 JST: the first two slots are in the past
            now=datetime(2026, 7, 31, 9, 40, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["decision"], "accept")
        self.assertEqual(decision["slot"]["start"], "2026-07-31T19:00:00+09:00")

    def test_calendar_read_and_write_use_the_real_gog_flag_surface(self):
        scheduler = load("interview_scheduler")
        read = scheduler.calendar_events_argv(
            account="operator@example.com",
            start=datetime(2026, 7, 30, tzinfo=JST),
            end=datetime(2026, 8, 6, tzinfo=JST),
        )
        self.assertNotIn("--max-results", read)  # does not exist in gog 0.17.0
        self.assertIn("--max", read)
        self.assertIn("--all-pages", read)
        self.assertIn("--json", read)
        self.assertEqual(read[:3], ["gog", "calendar", "events"])

        create = scheduler.calendar_create_argv(
            account="operator@example.com",
            slot={"start": "2026-07-31T18:00:00+09:00", "end": "2026-07-31T18:30:00+09:00"},
            summary="三者面談",
            description="d",
            booking_key="bk-1",
        )
        self.assertIn("--private-prop", create)
        self.assertIn("gig_booking_key=bk-1", create)
        self.assertIn("--from", create)
        self.assertIn("2026-07-31T18:00:00+09:00", create)

        readback = scheduler.calendar_readback_argv(
            account="operator@example.com", booking_key="bk-1"
        )
        self.assertIn("--private-prop-filter", readback)
        self.assertIn("gig_booking_key=bk-1", readback)


class AtMostOnceBookingTest(unittest.TestCase):
    """DoD 5: confirming a slot is irreversible; a crash must not double-book."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "bookings.sqlite3"
        self.addCleanup(self.tmp.cleanup)

    def _decision(self):
        return {
            "decision": "accept",
            "slot": {"start": "2026-07-31T18:00:00+09:00", "end": "2026-07-31T18:30:00+09:00"},
        }

    def test_crash_between_intent_and_confirmation_converges_to_one_booking(self):
        booking = load("retainer_booking")
        ledger = booking.BookingLedger(self.db)
        offer_hash = "a" * 64

        intent = ledger.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24",
            offer_hash=offer_hash,
            decision=self._decision(),
            now=1000,
        )
        ledger.mark_confirm_started(intent["booking_key"], now=1001)
        # ---- process dies here; the click may or may not have landed ----

        recovered = booking.BookingLedger(self.db)
        replay = recovered.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24",
            offer_hash=offer_hash,
            decision=self._decision(),
            now=1100,
        )
        self.assertEqual(replay["booking_key"], intent["booking_key"])
        self.assertEqual(replay["state"], "confirm_started")
        # an in-flight confirmation is never clicked blind
        self.assertFalse(recovered.may_confirm(replay["booking_key"]))

        # authoritative readback says the platform did take it
        resolved = recovered.reconcile(
            replay["booking_key"],
            observation={
                "interview_confirmed": True,
                "confirmed_start": "2026-07-31T18:00:00+09:00",
                "thread_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
            },
            now=1200,
        )
        self.assertEqual(resolved["state"], "confirmed")

        # and every later pass is a no-op
        again = booking.BookingLedger(self.db).open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24",
            offer_hash=offer_hash,
            decision=self._decision(),
            now=1300,
        )
        self.assertEqual(again["state"], "confirmed")
        self.assertFalse(booking.BookingLedger(self.db).may_confirm(again["booking_key"]))

        with sqlite3.connect(self.db) as connection:
            rows = connection.execute(
                "SELECT COUNT(*) FROM retainer_bookings WHERE state='confirmed'"
            ).fetchone()[0]
        self.assertEqual(rows, 1)

    def test_a_confirmation_that_did_not_land_is_retried_with_the_same_slot(self):
        booking = load("retainer_booking")
        ledger = booking.BookingLedger(self.db)
        intent = ledger.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24", offer_hash="b" * 64,
            decision=self._decision(), now=1000,
        )
        ledger.mark_confirm_started(intent["booking_key"], now=1001)
        resolved = ledger.reconcile(
            intent["booking_key"],
            observation={"interview_confirmed": False, "thread_id": "01KYPJ0M0ACF4DBAFSJVFN9K24"},
            now=1002,
        )
        self.assertEqual(resolved["state"], "intent")
        self.assertTrue(ledger.may_confirm(intent["booking_key"]))
        self.assertEqual(json.loads(resolved["decision_json"])["slot"], self._decision()["slot"])

    def test_the_intent_is_immutable_for_one_offer(self):
        booking = load("retainer_booking")
        ledger = booking.BookingLedger(self.db)
        ledger.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24", offer_hash="c" * 64,
            decision=self._decision(), now=1000,
        )
        with self.assertRaises(booking.ImmutableBooking):
            ledger.open_intent(
                thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24", offer_hash="c" * 64,
                decision={"decision": "accept",
                          "slot": {"start": "2026-08-03T18:00:00+09:00",
                                   "end": "2026-08-03T18:30:00+09:00"}},
                now=1001,
            )

    def test_calendar_write_is_skipped_when_the_readback_already_shows_the_event(self):
        booking = load("retainer_booking")
        ledger = booking.BookingLedger(self.db)
        intent = ledger.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24", offer_hash="d" * 64,
            decision=self._decision(), now=1000,
        )
        ledger.mark_confirm_started(intent["booking_key"], now=1001)
        ledger.reconcile(
            intent["booking_key"],
            observation={"interview_confirmed": True,
                         "confirmed_start": "2026-07-31T18:00:00+09:00",
                         "thread_id": "01KYPJ0M0ACF4DBAFSJVFN9K24"},
            now=1002,
        )
        self.assertTrue(ledger.needs_calendar_entry(intent["booking_key"]))
        ledger.record_calendar_entry(
            intent["booking_key"], event_id="evt-1", now=1003,
        )
        self.assertFalse(ledger.needs_calendar_entry(intent["booking_key"]))
        # replaying the same readback must not create a second event
        ledger.record_calendar_entry(intent["booking_key"], event_id="evt-1", now=1004)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM retainer_bookings WHERE calendar_event_id IS NOT NULL"
                ).fetchone()[0],
                1,
            )
        with self.assertRaises(booking.ImmutableBooking):
            ledger.record_calendar_entry(intent["booking_key"], event_id="evt-2", now=1005)

    def test_telegram_is_reported_after_the_fact_not_before(self):
        booking = load("retainer_booking")
        ledger = booking.BookingLedger(self.db)
        intent = ledger.open_intent(
            thread_id="01KYPJ0M0ACF4DBAFSJVFN9K24", offer_hash="e" * 64,
            decision=self._decision(), now=1000,
        )
        self.assertFalse(ledger.reportable(intent["booking_key"]))
        ledger.mark_confirm_started(intent["booking_key"], now=1001)
        self.assertFalse(ledger.reportable(intent["booking_key"]))
        ledger.reconcile(
            intent["booking_key"],
            observation={"interview_confirmed": True,
                         "confirmed_start": "2026-07-31T18:00:00+09:00",
                         "thread_id": "01KYPJ0M0ACF4DBAFSJVFN9K24"},
            now=1002,
        )
        ledger.record_calendar_entry(intent["booking_key"], event_id="evt-1", now=1003)
        self.assertTrue(ledger.reportable(intent["booking_key"]))


class A3StillHoldsTest(unittest.TestCase):
    """DoD 6: finishing old applications must not reopen the ban on new ones."""

    def test_a_retainer_application_submit_is_still_refused(self):
        eligibility = load("application_eligibility")
        # A5 made `market` keyword-only with no default so a caller cannot bid
        # without having read the client's stats. The retainer path is the one
        # place that legitimately has none: it refuses before it ever loads a
        # brief, so it passes None explicitly, exactly as cdp_nav_snapshot does.
        verdict = eligibility.evaluate_application(
            "完全非同期のチャット業務です",
            "テキストで支援します",
            bucket="retainer",
            market=None,
        )
        self.assertFalse(verdict["allowed"])
        self.assertIn(
            eligibility.RETAINER_APPLICATIONS_DISABLED, verdict["reason_codes"]
        )

    def test_this_lane_never_opens_or_submits_a_retainer_application(self):
        for name in ("retainer_thread", "interview_scheduler",
                     "retainer_booking", "retainer_lane"):
            source = (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
            self.assertNotIn("submit-retainer-application", source, name)
            self.assertNotIn("open-retainer-application", source, name)
            self.assertNotIn("/job_matching/outsources", source, name)


class RetainerLaneBudgetTest(unittest.TestCase):
    """The reply lane spends 1 model call per pass on purpose; a third queue would starve."""

    def test_the_retainer_lane_carries_its_own_budget(self):
        lane = load("retainer_lane")
        self.assertEqual(lane.DEFAULT_MAX_MODEL_CALLS, 1)
        self.assertEqual(lane.MODEL_CALL_LIMIT_ENV, "GIG_RETAINER_LANE_MODEL_CALL_LIMIT")

    def test_scheduling_a_confirmed_offer_costs_no_model_call(self):
        """Picking a slot is arithmetic over a calendar, not a composition."""
        lane = load("retainer_lane")
        self.assertFalse(lane.needs_model_call({"next_action": "schedule_interview"}))
        self.assertTrue(lane.needs_model_call({"next_action": "reply"}))


class RetainerBrowserContractTest(unittest.TestCase):
    """Selectors are grounded on the live DOM, not guessed."""

    def test_selectors_match_what_the_live_page_actually_renders(self):
        browser = load("coconala_retainer_browser")
        self.assertEqual(browser.SELECT_INTERVIEW_BUTTON_TEXT, "面談日時を選択する")
        self.assertEqual(browser.CONFIRM_STEP_BUTTON_TEXT, "確認に進む")
        self.assertEqual(browser.CANCEL_BUTTON_TEXT, "キャンセル")
        self.assertEqual(
            browser.NO_SUITABLE_SLOT_CHECKBOX_TEXT,
            "都合が合う日時がないため、別の候補の提示をお願いする",
        )
        self.assertEqual(browser.COMPOSER_SELECTOR, "#jobtalkroom-message-input")
        self.assertEqual(browser.SEND_BUTTON_TEXT, "送信する")

    def test_thread_urls_are_derived_not_guessed(self):
        browser = load("coconala_retainer_browser")
        self.assertEqual(
            browser.thread_message_url("01KYPJ0M0ACF4DBAFSJVFN9K24"),
            "https://coconala.com/mypage/job_matching/job_talkroom/"
            "01KYPJ0M0ACF4DBAFSJVFN9K24/talkroom",
        )
        with self.assertRaises(ValueError):
            browser.thread_message_url("4201")  # numeric ids are single-shot, not retainer


if __name__ == "__main__":
    unittest.main()
