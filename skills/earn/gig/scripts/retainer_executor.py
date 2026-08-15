#!/usr/bin/env python3
"""Carry one retainer thread from "plan says act" to a side effect we read back.

The ordering is the same one every other irreversible thing in this loop uses --
durable intent, then execute, then AUTHORITATIVE readback, then ledger, then report
-- and the readback is deliberately a fresh render of the page rather than our own
return value.  A click that "returned ok" is not evidence; a thread that shows the
interview booked, or shows our message as the newest one, is.

Two shapes of work exist and they are not interchangeable:

  schedule_interview  the platform sent a structured offer, so there is a modal to
                      drive and a calendar entry to write. Costs no model call:
                      choosing the slot is arithmetic over Dais's real calendar.

  reply               the client asked in prose for candidate times, so there is no
                      modal at all. Costs the lane's one model call.

Telegram is told afterwards, as a report. It is never asked what to do, and it is
never told before the platform agrees -- `reportable()` on both ledgers is what
enforces that ordering rather than the order of statements in this file.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


JST = timezone(timedelta(hours=9))

_BROWSER_MODULE = None


def browser_module():
    global _BROWSER_MODULE
    if _BROWSER_MODULE is None:
        _BROWSER_MODULE = _load_local("coconala_retainer_browser")
    return _BROWSER_MODULE


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slot_address(slot: dict[str, str]) -> tuple[int, int, int, str]:
    """Translate a chosen slot into the handles the modal actually exposes.

    Year and month are carried because the calendar page, not just the day number,
    identifies a day: the July page also renders June's tail and August's head. The
    radio group's `name` is a React Aria generated id that changes on every render,
    so the option is matched by its rendered VALUE (18:00~18:30) and never by name.
    """
    browser = _load_local("coconala_retainer_browser")
    start = datetime.fromisoformat(str(slot["start"])).astimezone(JST)
    end = datetime.fromisoformat(str(slot["end"])).astimezone(JST)
    return (
        start.year, start.month, start.day,
        browser.slot_label(f"{start:%H:%M}", f"{end:%H:%M}"),
    )


WORKING_DAY_START_MINUTES = 10 * 60
WORKING_DAY_END_MINUTES = 19 * 60
DEFAULT_MEETING_MINUTES = 30


def free_slots(
    *, events: list[dict[str, Any]], now: datetime, limit: int = 3
) -> list[dict[str, str]]:
    """Real free half-hours in Dais's working day, one per day, from his calendar."""
    scheduler = _load_local("interview_scheduler")
    today = now.astimezone(JST).date()
    synthetic_offer = {
        "duration_minutes": DEFAULT_MEETING_MINUTES,
        "windows": [{
            "start": datetime.combine(
                today, datetime.min.time(), tzinfo=JST,
            ).replace(hour=WORKING_DAY_START_MINUTES // 60).isoformat(),
            "end": datetime.combine(
                today, datetime.min.time(), tzinfo=JST,
            ).replace(hour=WORKING_DAY_END_MINUTES // 60).isoformat(),
        }],
    }
    return scheduler.counter_proposals(
        offer=synthetic_offer,
        busy=scheduler.busy_intervals(events),
        now=now,
        limit=limit,
    )


def interview_summary(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    return f"ココナラ 三者面談: {title}"[:180] if title else "ココナラ 三者面談"


def counter_proposal_text(decision: dict[str, Any]) -> str:
    scheduler = _load_local("interview_scheduler")
    return scheduler.counter_proposal_message(list(decision.get("proposals") or []))


def create_calendar_event(
    *,
    account: str,
    slot: dict[str, str],
    summary: str,
    description: str,
    booking_key: str,
    runner: Callable[..., Any] = subprocess.run,
) -> str:
    """Write the interview to the real calendar and return the event id it got."""
    scheduler = _load_local("interview_scheduler")
    completed = runner(
        scheduler.calendar_create_argv(
            account=account, slot=slot, summary=summary,
            description=description, booking_key=booking_key,
        ),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"calendar create failed rc={completed.returncode}")
    payload = json.loads(completed.stdout or "{}")
    event = payload if isinstance(payload, dict) else {}
    if isinstance(event.get("event"), dict):
        event = event["event"]
    event_id = str(event.get("id") or "")
    if not event_id:
        raise RuntimeError("calendar create returned no event id")
    return event_id


class RetainerExecutor:
    """Drive one queue item to a verified side effect. Never two."""

    def __init__(
        self,
        *,
        booking_ledger: Any,
        message_ledger: Any,
        browser_factory: Callable[[str], Any],
        calendar_account: str,
        clock: Callable[[], int],
        report: Callable[[str, str], str],
        compose: Callable[[dict[str, Any]], str] | None = None,
        calendar_readback: Callable[..., str | None] | None = None,
        calendar_create: Callable[..., str] | None = None,
        max_model_calls: int = 1,
    ):
        lane = _load_local("retainer_lane")
        self.lane = lane
        self.booking_ledger = booking_ledger
        self.message_ledger = message_ledger
        self.browser_factory = browser_factory
        self.calendar_account = calendar_account
        self.clock = clock
        self.report = report
        self.compose = compose
        self.calendar_readback = calendar_readback or (
            lambda key: lane.calendar_event_for_booking(
                account=self.calendar_account, key=key
            )
        )
        self.calendar_create = calendar_create or create_calendar_event
        self.max_model_calls = int(max_model_calls)
        self.model_calls = 0

    # -- planning ---------------------------------------------------------------
    def plan(self, *, item: dict[str, Any], events: list[dict[str, Any]],
             now: datetime) -> dict[str, Any]:
        """Read the live thread and decide, with no side effect of any kind."""
        with self.browser_factory(str(item["talkroom_id"])) as browser:
            state = browser.read_state()
        plan = self.lane.plan_thread(
            item=item, thread_state=state, events=events, now=now,
        )
        if str(plan.get("action") or "") == "reply":
            # A client asking "when are you free?" must be answered from the real
            # calendar, not from a language model's imagination. The lane already
            # read availability to plan interviews; the same reading is handed to the
            # composer as verified research so the times it offers are times Dais
            # actually has -- otherwise the reply books a conflict by hand.
            plan["free_slots"] = free_slots(events=events, now=now)
        plan["thread_state"] = {
            "last_side": state.get("last_side"),
            "interview_confirmed": state.get("interview_confirmed"),
            "interview_select_button_present": state.get(
                "interview_select_button_present"
            ),
            "composer_present": state.get("composer_present"),
            "message_count": len(state.get("messages", [])),
        }
        return plan

    # -- execution --------------------------------------------------------------
    def execute(self, *, item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        action = str(plan.get("action") or "")
        if action == "already_confirmed":
            return self._close_confirmed(item=item, plan=plan)
        if action == "none":
            return {
                "status": "skipped",
                "action": action,
                "thread_id": str(item["talkroom_id"]),
                "reason": str(plan.get("reason") or action),
            }
        if action == "schedule_interview":
            return self._schedule(item=item, plan=plan)
        if action == "reply":
            return self._reply(item=item, plan=plan)
        raise RuntimeError(f"unsupported retainer plan action: {action}")

    def _close_confirmed(
        self, *, item: dict[str, Any], plan: dict[str, Any]
    ) -> dict[str, Any]:
        """The platform shows this interview as agreed. Finish the paperwork, once."""
        thread_id = str(item["talkroom_id"])
        booking_module = _load_local("retainer_booking")
        digest = str(plan.get("offer_hash") or "")
        result: dict[str, Any] = {
            "status": "skipped",
            "action": "already_confirmed",
            "thread_id": thread_id,
            "reason": "already_confirmed",
        }
        if len(digest) != 64:
            return result
        key = booking_module.booking_key(thread_id, digest)
        row = self.booking_ledger.get(key)
        if row is None:
            return result
        confirmed = plan.get("confirmed_interview") or {}
        if row["state"] != "confirmed":
            self.booking_ledger.adopt_existing_confirmation(
                key,
                observation={
                    "thread_id": thread_id,
                    "interview_confirmed": True,
                    "confirmed_start": str(confirmed.get("start") or ""),
                },
                now=self.clock(),
            )
            result["adopted"] = True
        decision = json.loads(self.booking_ledger.get(key)["decision_json"])
        result["booking_key"] = key
        result["confirmed_interview"] = confirmed
        result["calendar_event_id"] = self._ensure_calendar_entry(
            key=key, item=item, decision=decision,
        )
        if self.booking_ledger.reportable(key):
            result["telegram_message_id"] = self.report(
                f"gig:telegram:retainer-booking:v1:{key}",
                self.lane.telegram_text(item=item, booked=self.booking_ledger.get(key)),
            )
            self.booking_ledger.mark_reported(key, now=self.clock())
        result["status"] = "confirmed"
        return result

    # -- interview --------------------------------------------------------------
    def _schedule(self, *, item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        thread_id = str(item["talkroom_id"])
        decision = dict(plan["decision"])
        if decision["decision"] != "accept":
            # Counter-proposing is a MESSAGE to the client, and its readback signal --
            # what the thread looks like after 「都合が合う日時がないため…」 is submitted
            # -- was never captured live. Firing a path whose success I cannot read
            # back is how a client gets told the same thing twice. Left unfired, and
            # deliberately: the queue keeps the row, so it is visible, not lost.
            return {
                "status": "not_executed",
                "action": "schedule_interview",
                "thread_id": thread_id,
                "decision": decision["decision"],
                "reason": "counter_proposal_readback_never_observed",
                "proposals": list(decision.get("proposals") or []),
            }
        booking = self.booking_ledger.open_intent(
            thread_id=thread_id,
            offer_hash=str(plan["offer_hash"]),
            decision=decision,
            now=self.clock(),
        )
        key = str(booking["booking_key"])
        result: dict[str, Any] = {
            "status": "in_progress",
            "action": "schedule_interview",
            "thread_id": thread_id,
            "booking_key": key,
            "decision": decision["decision"],
        }
        if booking["state"] == "intent":
            self.booking_ledger.mark_confirm_started(key, now=self.clock())
            with self.browser_factory(thread_id) as browser:
                self._drive_modal(browser=browser, decision=decision)
                observation = browser.read_fresh()
        elif booking["state"] == "confirm_started":
            # A previous attempt's outcome is unknown. Never click again: ask the
            # platform what happened first. This is the branch that stops a crash
            # from becoming a double booking.
            with self.browser_factory(thread_id) as browser:
                observation = browser.read_fresh()
            result["recovered"] = True
        else:
            observation = None

        if observation is not None:
            reconciled = self.booking_ledger.reconcile(
                key,
                observation={
                    "thread_id": thread_id,
                    "interview_confirmed": bool(observation.get("interview_confirmed")),
                    # The platform's stated time, not ours. If they disagree, the one
                    # the client will show up for is the platform's.
                    "confirmed_start": str(
                        (observation.get("confirmed_interview") or {}).get("start")
                        or (decision.get("slot") or {}).get("start")
                        or ""
                    ),
                },
                now=self.clock(),
            )
            result["readback"] = {
                "interview_confirmed": bool(observation.get("interview_confirmed")),
                "confirmed_interview": observation.get("confirmed_interview"),
                "interview_select_button_present": observation.get(
                    "interview_select_button_present"
                ),
                "last_side": observation.get("last_side"),
                "banner_text": str(observation.get("banner_text") or "")[:120],
            }
            if (
                reconciled["state"] == "confirmed"
                and str((observation.get("confirmed_interview") or {}).get("start") or "")
                != str((decision.get("slot") or {}).get("start") or "")
            ):
                # Never silently. The booking stands (it is the client's reality) but
                # the report has to say it is not the slot we chose.
                result["slot_mismatch"] = True
            if reconciled["state"] != "confirmed":
                result["status"] = "reconcile_pending"
                return result
        elif self.booking_ledger.get(key)["state"] != "confirmed":
            result["status"] = "reconcile_pending"
            return result

        if decision["decision"] == "accept":
            result["calendar_event_id"] = self._ensure_calendar_entry(
                key=key, item=item, decision=decision,
            )
        if self.booking_ledger.reportable(key):
            text = self.lane.telegram_text(
                item=item, booked=self.booking_ledger.get(key),
            )
            result["telegram_message_id"] = self.report(
                f"gig:telegram:retainer-booking:v1:{key}", text,
            )
            self.booking_ledger.mark_reported(key, now=self.clock())
        result["status"] = "confirmed"
        return result

    def _drive_modal(self, *, browser: Any, decision: dict[str, Any]) -> None:
        opened = browser.open_interview_modal()
        year, month, day, label = slot_address(dict(decision["slot"]))
        if label not in list(opened.get("slots") or []):
            # The modal renders the client's own grid. A slot we chose that the modal
            # does not show means the offer moved under us: stop, do not improvise.
            browser.close_interview_modal()
            raise RuntimeError(f"chosen slot {label} is not offered by the modal")
        browser.select_slot(
            year=year, month=month, day_of_month=day, slot_label_text=label,
        )
        browser.advance_to_confirmation()
        # The platform now shows what it believes it is about to book. Confirming is
        # allowed only when that summary is OUR slot -- see confirm_interview_expression.
        browser.confirm_interview(
            expected_date=browser_module().confirmation_date_text(
                year=year, month=month, day=day,
            ),
            expected_slot=label,
        )

    def _ensure_calendar_entry(
        self, *, key: str, item: dict[str, Any], decision: dict[str, Any]
    ) -> str:
        if not self.booking_ledger.needs_calendar_entry(key):
            row = self.booking_ledger.get(key)
            return str(row["calendar_event_id"] or "")
        # The calendar records what the PLATFORM confirmed. Writing our own decision
        # would put Dais in a meeting at a time the client is not expecting him.
        slot = dict(decision["slot"])
        confirmed_start = str(self.booking_ledger.get(key)["confirmed_start"] or "")
        if confirmed_start:
            duration = (
                datetime.fromisoformat(str(slot["end"]))
                - datetime.fromisoformat(str(slot["start"]))
            )
            start = datetime.fromisoformat(confirmed_start)
            slot = {"start": start.isoformat(), "end": (start + duration).isoformat()}
        # Readback BEFORE write: the private property carries the booking key, so a
        # crashed pass that already created the event finds it instead of a twin.
        existing = self.calendar_readback(key)
        event_id = existing or self.calendar_create(
            account=self.calendar_account,
            slot=slot,
            summary=interview_summary(item),
            description=self.lane.calendar_description(item=item, thread_state={}),
            booking_key=key,
        )
        self.booking_ledger.record_calendar_entry(
            key, event_id=str(event_id), now=self.clock(),
        )
        return str(event_id)

    # -- free-text reply --------------------------------------------------------
    def _reply(self, *, item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        thread_id = str(item["talkroom_id"])
        row = self.message_ledger.open_intent(
            thread_id=thread_id,
            event_key=str(item["event_key"]),
            inbound_sent_at=str(item["origin_at"]),
            now=self.clock(),
        )
        key = str(row["message_key"])
        result: dict[str, Any] = {
            "status": "in_progress",
            "action": "reply",
            "thread_id": thread_id,
            "message_key": key,
        }
        browser_module = _load_local("coconala_retainer_browser")

        if row["state"] == "sent":
            result["status"] = "already_sent"
            return result

        if row["state"] == "send_started":
            # Unknown outcome from a previous attempt. Read first, never resend blind.
            with self.browser_factory(thread_id) as browser:
                observation = browser_module.answer_observation(
                    browser.read_fresh(),
                    thread_id=thread_id,
                    inbound_sent_at=str(item["origin_at"]),
                )
            reconciled = self.message_ledger.reconcile(
                key, observation=observation, now=self.clock(),
            )
            result["recovered"] = True
            result["readback"] = observation
            if reconciled["state"] != "sent":
                result["status"] = "reconcile_pending"
                return result
        else:
            if self.compose is None:
                raise RuntimeError("a composer is required to answer a retainer thread")
            if self.model_calls >= self.max_model_calls:
                result["status"] = "deferred"
                return result
            with self.browser_factory(thread_id) as browser:
                state = browser.read_state()
                already = browser_module.answer_observation(
                    state, thread_id=thread_id, inbound_sent_at=str(item["origin_at"]),
                )
                if already["answered"]:
                    # Somebody -- an earlier pass, or Dais -- already answered this.
                    self.message_ledger.adopt_existing_answer(
                        key, observation=already, now=self.clock(),
                    )
                    result["status"] = "already_answered"
                    result["readback"] = already
                    return result
                context: dict[str, Any] = {
                    "conversation": [
                        {
                            "side": "buyer" if message["side"] == "client" else "seller",
                            "body": str(message.get("body") or ""),
                        }
                        for message in state.get("messages", [])
                        if message["side"] in {"client", "seller"}
                    ]
                }
                slots = list(plan.get("free_slots") or [])
                if slots:
                    context["verified_research"] = {
                        "source": "owner_google_calendar_read_this_pass",
                        "available_slots_jst": [
                            f"{slot['start']} - {slot['end']}" for slot in slots
                        ],
                        "instruction": (
                            "候補日時を提示する場合は available_slots_jst のみを使うこと。"
                        ),
                    }
                self.model_calls += 1
                body = str(self.compose(context)).replace("\r\n", "\n").replace("\r", "\n")
                self.message_ledger.mark_send_started(
                    key,
                    attempt_hash=_load_local("retainer_message").body_hash(body),
                    now=self.clock(),
                )
                browser.send_reply(body)
                body = ""
                observation = browser_module.answer_observation(
                    browser.read_fresh(),
                    thread_id=thread_id,
                    inbound_sent_at=str(item["origin_at"]),
                )
            reconciled = self.message_ledger.reconcile(
                key, observation=observation, now=self.clock(),
            )
            result["readback"] = observation
            if reconciled["state"] != "sent":
                result["status"] = "reconcile_pending"
                return result

        if self.message_ledger.reportable(key):
            result["telegram_message_id"] = self.report(
                f"gig:telegram:retainer-reply:v1:{key}",
                (
                    "継続案件スレッドに返信しました（事後報告）\n"
                    f"案件: {item.get('title') or thread_id}\n"
                    f"スレッド: {item['talkroom_url']}\n"
                    f"送信時刻: {result.get('readback', {}).get('seller_sent_at') or '?'}"
                ),
            )
            self.message_ledger.mark_reported(key, now=self.clock())
        result["status"] = "sent"
        return result


def telegram_reporter(
    *, outbox: Any, transport: Callable[[str], str], clock: Callable[[], int]
) -> Callable[[str, str], str]:
    """Enqueue-then-drain, and then verify OUR row -- not whatever got dispatched.

    `dispatch_one` claims the oldest pending report, which may belong to another
    lane. Returning that row's message_id would be reporting someone else's receipt
    as ours, so the drain runs until the queue is empty and the answer is read back
    out of the outbox by event key.
    """
    import sqlite3

    outbox_module = _load_local("telegram_outbox")

    def report(event_key: str, message: str) -> str:
        outbox.enqueue(
            event_key=event_key,
            kind="retainer_followthrough",
            message=message,
            created_at=clock(),
        )
        for _ in range(int(outbox.counts().get("pending", 0)) + 1):
            result = outbox_module.dispatch_one(
                outbox,
                owner=f"gig-retainer-{uuid.uuid4().hex}",
                now=clock,
                transport=transport,
            )
            if str(result.get("status")) == "queue_empty":
                break
        connection = sqlite3.connect(outbox.database, timeout=30)
        try:
            row = connection.execute(
                "SELECT state,message_id FROM telegram_reports WHERE event_key=?",
                (event_key,),
            ).fetchone()
        finally:
            connection.close()
        if not row or row[0] != "sent" or not row[1]:
            raise RuntimeError(
                f"telegram report did not reach sent state: {row[0] if row else 'missing'}"
            )
        return str(row[1])

    return report
