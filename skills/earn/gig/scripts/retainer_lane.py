#!/usr/bin/env python3
"""Follow-through lane for retainer applications that were already submitted.

A3 banned NEW retainer applications.  This lane touches only threads that already
exist, and it exists because nothing else was touching them: the applied-retainer
tab showed 未読1 / 未返信3 with an unanswered 三者面談 offer while the reply lane
swept a different set of pages entirely.

Why its own budget instead of a third source on the reply queue
---------------------------------------------------------------
reply_lane.process_queue spends at most GIG_REPLY_LANE_MODEL_CALL_LIMIT model calls
per pass, default 1, and gig_pass.sh documents that the 1 is deliberate: "Every call
here is an autonomous message to a real buyer, so raising the pass-wide lane budget
must not quietly quadruple the number of messages a stranger receives per waking."
Folding retainer threads into that same list would not respect that rule, it would
break the other one: with a shared budget of 1, one direct-message inquiry starves
every retainer thread for the whole pass, forever, because the inquiry queue is
rebuilt first every time.  So the retainer lane gets its own budget of 1.  The
invariant the comment actually protects -- one autonomous message per counterparty
per waking -- is preserved exactly, because these are different counterparties on a
different surface.

Scheduling costs no model call at all: choosing a slot is arithmetic over a
calendar, and the counter-proposal text is generated from the free slots we found.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAX_MODEL_CALLS = 1
MODEL_CALL_LIMIT_ENV = "GIG_RETAINER_LANE_MODEL_CALL_LIMIT"
DEFAULT_CALENDAR_ACCOUNT = os.environ.get("GIG_CALENDAR_ACCOUNT", "operator@example.com")
CALENDAR_LOOKAHEAD_DAYS = 21


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def needs_model_call(item: dict[str, Any]) -> bool:
    """Only composing a free-text reply needs a model."""
    return str(item.get("next_action") or "") == "reply"


def max_model_calls(environ: dict[str, str] | None = None) -> int:
    raw = (environ if environ is not None else os.environ).get(MODEL_CALL_LIMIT_ENV)
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return DEFAULT_MAX_MODEL_CALLS
    return value if value >= 1 else DEFAULT_MAX_MODEL_CALLS


def read_calendar(
    *, account: str, start: datetime, end: datetime, runner: Any = subprocess.run
) -> list[dict[str, Any]]:
    """Read real availability. An unreadable calendar is not an empty calendar."""
    scheduler = _load_local("interview_scheduler")
    completed = runner(
        scheduler.calendar_events_argv(account=account, start=start, end=end),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"calendar read failed rc={completed.returncode}")
    payload = json.loads(completed.stdout or "{}")
    events = payload.get("events") if isinstance(payload, dict) else payload
    if not isinstance(events, list):
        raise RuntimeError("calendar read returned no event list")
    return events


def calendar_event_for_booking(
    *, account: str, key: str, runner: Any = subprocess.run
) -> str | None:
    """Authoritative check for an already-written interview, by booking key."""
    scheduler = _load_local("interview_scheduler")
    completed = runner(
        scheduler.calendar_readback_argv(account=account, booking_key=key),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"calendar readback failed rc={completed.returncode}")
    payload = json.loads(completed.stdout or "{}")
    events = payload.get("events") if isinstance(payload, dict) else payload
    if not isinstance(events, list) or not events:
        return None
    return str(events[0].get("id") or "") or None


def plan_thread(
    *,
    item: dict[str, Any],
    thread_state: dict[str, Any],
    events: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    """Decide what this thread needs, without performing any side effect."""
    scheduler = _load_local("interview_scheduler")
    booking = _load_local("retainer_booking")
    offer = thread_state.get("interview_offer")
    if thread_state.get("interview_confirmed") is True:
        # Carries the offer identity so a ledger row that never learned the booking
        # landed can still be closed, calendared and reported -- see
        # BookingLedger.adopt_existing_confirmation.
        return {
            "action": "already_confirmed",
            "thread_id": item["talkroom_id"],
            "offer_hash": booking.offer_hash(offer) if offer is not None else None,
            "confirmed_interview": thread_state.get("confirmed_interview"),
        }
    if offer is None:
        # The applied tab shows the last message body but not its author, so most
        # of its rows are our own application text sitting under 応募済み. Only the
        # live thread can say whether anyone is actually waiting on us.
        if thread_state.get("last_side") != "client":
            return {
                "action": "none",
                "thread_id": item["talkroom_id"],
                "reason": "seller_has_the_last_word",
            }
        return {"action": "reply", "thread_id": item["talkroom_id"]}
    decision = scheduler.choose_slot(offer=offer, events=events, now=now)
    return {
        "action": "schedule_interview",
        "thread_id": item["talkroom_id"],
        "offer": offer,
        "offer_hash": booking.offer_hash(offer),
        "decision": decision,
    }


def calendar_description(*, item: dict[str, Any], thread_state: dict[str, Any]) -> str:
    return (
        "Coconala 三者面談 (retainer application follow-through).\n"
        f"thread: {item['talkroom_url']}\n"
        f"status: {item.get('application_status') or 'unknown'}\n"
        "Booked autonomously by the gig loop from live calendar availability."
    )


def telegram_text(*, item: dict[str, Any], booked: dict[str, Any]) -> str:
    """After the fact. Dais is told what happened, never asked what to do."""
    slot = json.loads(booked["decision_json"]).get("slot") or {}
    # What the platform confirmed is what the client will show up for; our decision
    # is only the fallback for a row that predates a readback.
    start = str(booked.get("confirmed_start") or "") or slot.get("start", "?")
    return (
        "面談を確定しました（事後報告）\n"
        f"案件: {item.get('title') or item['talkroom_id']}\n"
        f"日時: {start} 〜 {slot.get('end', '?')}\n"
        f"スレッド: {item['talkroom_url']}\n"
        "カレンダーにも登録済みです。"
    )


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def build(snapshot_path: Path, output: Path, now: datetime | None = None) -> dict[str, Any]:
    retainer = _load_local("retainer_thread")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    queue = retainer.build_queue(snapshot, now=now)
    _atomic_json(output, queue)
    return queue


def run(args: Any) -> dict[str, Any]:
    """Plan every queued thread, then carry the ones that say act to a readback.

    Planning happens for ALL items first and is printed before anything irreversible
    starts, because the operator's question is never "what happened" but "what is
    about to happen to a real client".
    """
    executor_module = _load_local("retainer_executor")
    browser_module = _load_local("coconala_retainer_browser")
    booking_module = _load_local("retainer_booking")
    message_module = _load_local("retainer_message")

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    now = datetime.now(timezone.utc)
    events = read_calendar(
        account=args.calendar_account,
        start=now,
        end=now + timedelta(days=CALENDAR_LOOKAHEAD_DAYS),
    )

    def browser_factory(application_id: str) -> Any:
        return browser_module.CoconalaCdpRetainerBrowser(
            args.cdp_helper, application_id, hidden=bool(args.hidden_browser),
        )

    executor = executor_module.RetainerExecutor(
        booking_ledger=booking_module.BookingLedger(args.booking_database),
        message_ledger=message_module.MessageLedger(args.message_database),
        browser_factory=browser_factory,
        calendar_account=args.calendar_account,
        clock=lambda: int(time.time()),
        report=_reporter(args),
        compose=_composer(args),
        max_model_calls=max(1, int(args.max_model_calls)),
    )

    plans = [executor.plan(item=item, events=events, now=now) for item in items]
    summary: dict[str, Any] = {
        "status": "completed",
        "plans": plans,
        "results": [],
        "model_calls": 0,
        "errors": [],
    }
    if getattr(args, "plan_only", False):
        summary["status"] = "planned"
        return summary
    for item, plan in zip(items, plans):
        try:
            summary["results"].append(executor.execute(item=item, plan=plan))
        except Exception as error:  # one thread's failure is not the lane's
            summary["errors"].append({
                "thread_id": str(item.get("talkroom_id") or ""),
                "type": type(error).__name__,
                "message": str(error)[:300],
            })
    summary["model_calls"] = executor.model_calls
    if summary["errors"]:
        summary["status"] = "partial"
    return summary


def _composer(args: Any) -> Any:
    if not getattr(args, "runner", None) or not getattr(args, "schema", None):
        return None
    composer_module = _load_local("reply_composer")
    return composer_module.RunnerComposer(
        runner=args.runner, schema=args.schema, workdir=args.workdir,
    )


def _reporter(args: Any) -> Any:
    executor_module = _load_local("retainer_executor")
    outbox_module = _load_local("telegram_outbox")
    report_module = _load_local("telegram_report")
    transport = report_module.OpenClawTelegramTransport(
        target=str(args.telegram_target),
        receipt_dir=Path(args.telegram_database).parent / "telegram-delivery-receipts",
    )
    return executor_module.telegram_reporter(
        outbox=outbox_module.TelegramOutbox(args.telegram_database),
        transport=transport,
        clock=lambda: int(time.time()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--snapshot", required=True, type=Path)
    build_parser.add_argument("--output", required=True, type=Path)
    build_parser.add_argument("--now")
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--queue", required=True, type=Path)
    plan_parser.add_argument("--thread-state", required=True, type=Path)
    plan_parser.add_argument("--output", required=True, type=Path)
    plan_parser.add_argument("--calendar-account", default=DEFAULT_CALENDAR_ACCOUNT)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--queue", required=True, type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.add_argument("--booking-database", required=True, type=Path)
    run_parser.add_argument("--message-database", required=True, type=Path)
    run_parser.add_argument("--telegram-database", required=True, type=Path)
    run_parser.add_argument("--cdp-helper", required=True, type=Path)
    run_parser.add_argument("--runner", type=Path)
    run_parser.add_argument("--schema", type=Path)
    run_parser.add_argument("--runner-config", type=Path)
    run_parser.add_argument("--workdir", type=Path, default=Path.home())
    run_parser.add_argument("--telegram-target", default="42")
    run_parser.add_argument("--calendar-account", default=DEFAULT_CALENDAR_ACCOUNT)
    run_parser.add_argument("--max-model-calls", type=int, default=DEFAULT_MAX_MODEL_CALLS)
    run_parser.add_argument("--hidden-browser", action="store_true")
    run_parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    if args.command == "build":
        now = (
            datetime.fromisoformat(str(args.now).replace("Z", "+00:00"))
            if args.now
            else None
        )
        queue = build(args.snapshot, args.output, now=now)
        print(json.dumps({
            "status": queue["status"],
            "items": len(queue["items"]),
            "errors": queue["errors"],
            "output": str(args.output),
        }, ensure_ascii=False, separators=(",", ":")))
        return 2 if queue["status"] == "collector_unhealthy" else 0

    if args.command == "run":
        try:
            summary = run(args)
        except Exception as error:
            failure = {
                "status": "failed",
                "plans": [],
                "results": [],
                "model_calls": 0,
                "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            }
            _atomic_json(args.output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1
        _atomic_json(args.output, summary)
        print(json.dumps({
            "status": summary["status"],
            "plans": [
                {key: plan.get(key) for key in ("action", "thread_id", "reason")}
                for plan in summary["plans"]
            ],
            "results": [
                {key: result.get(key) for key in ("status", "action", "thread_id")}
                for result in summary["results"]
            ],
            "model_calls": summary["model_calls"],
            "errors": summary["errors"],
        }, ensure_ascii=False, separators=(",", ":")))
        return 0 if summary["status"] in {"completed", "planned"} else 2

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    states = json.loads(args.thread_state.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    events = read_calendar(
        account=args.calendar_account,
        start=now,
        end=now + timedelta(days=CALENDAR_LOOKAHEAD_DAYS),
    )
    plans = [
        plan_thread(
            item=item,
            thread_state=states.get(str(item["talkroom_id"]), {}),
            events=events,
            now=now,
        )
        for item in queue.get("items", [])
    ]
    result = {"status": "planned", "plans": plans}
    _atomic_json(args.output, result)
    print(json.dumps({"status": "planned", "plans": len(plans)},
                     ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
