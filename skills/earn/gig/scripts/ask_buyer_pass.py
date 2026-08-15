#!/usr/bin/env python3
"""Plan the question a blocked paid order needs, and record that it was asked.

Same two-command split as followup_pass, for the same reason: a crash between planning and
recording loses a message rather than the memory of one, and here the memory is what stops
a paying buyer from being asked the identical question every hour.

Never fails the pass. Being unable to plan a question is not worse than the situation it
was trying to escape.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask_buyer  # noqa: E402
import ask_buyer_send_attempts  # noqa: E402
import paid_work_evidence  # noqa: E402


def _asked_keys(path: str) -> set[str]:
    """Blocked states already asked about. A corrupt line is skipped, never fatal."""
    keys: set[str] = set()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return keys
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("blocker_key"):
            keys.add(str(row["blocker_key"]))
    return keys


def _write_json(path: str, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)


def build(args: argparse.Namespace) -> int:
    # Never plan a question the send gate will throw away.
    #
    # This used to ask ask_buyer.blocked_state(), which says yes to a BLOCKED record about
    # feedback the buyer has already replaced. The gate that actually sends
    # (paid_work_fresh_blocked in gig_pass.sh) asks blocked_evidence_verdict() and moves
    # only on `fresh`. Two readers, two answers, one buyer: on 2026-08-07 12:41 order
    # 91000002 composed a question against digest 57b8719d while the buyer's open message
    # was 43981596, and the gate discarded it -- a model call spent, a pass failed, and the
    # buyer heard nothing. Same reader, same verdict, one decision.
    #
    # `fresh` and nothing else, deliberately. undeterminable must not open this path for the
    # same reason it must not open the send gate: a check that could not run has not seen a
    # blocker, and a paying buyer is not the place to guess.
    verdict, state = paid_work_evidence.blocked_evidence_verdict(args.project_root)
    if verdict != paid_work_evidence.BLOCK_FRESH or state is None:
        _write_json(args.output, {
            "status": "queue_empty", "errors": [], "items": [],
            "blocked_verdict": verdict,
        })
        return 0
    key = ask_buyer.blocker_key(state)
    if key in _asked_keys(args.ledger):
        # Already asked and still unanswered. Asking again changes nothing about what we
        # know and everything about what the buyer thinks of us.
        _write_json(args.output, {
            "status": "queue_empty", "errors": [], "items": [],
            "already_asked": key,
        })
        return 0
    talkroom_id = str(args.talkroom_id or "").strip()
    if not talkroom_id:
        _write_json(args.output, {"status": "queue_empty", "errors": ["missing_talkroom_id"], "items": []})
        return 0
    # ★ A send that keeps failing must stop being composed. ★
    #
    # Checked here rather than at the send call, and after the two cheap refusals above, so
    # that a bounded-out target costs no model call: `compose` runs a provider, and the
    # whole failure mode this bound exists for is paying for a question hourly that never
    # leaves the machine. ask-buyer.jsonl cannot answer this -- by design it is written only
    # after a verified send -- so the count comes from its own ledger.
    #
    # Absent flag means no bound, which is what every caller had before this existed.
    send_attempts = getattr(args, "send_attempts", None)
    if send_attempts:
        bound = ask_buyer_send_attempts.verdict(send_attempts, talkroom_id, key)
        if bound.get("exhausted"):
            _write_json(args.output, {
                "status": "queue_empty", "errors": [], "items": [],
                "send_attempts_exhausted": key,
                "consecutive_send_failures": bound.get("consecutive_failures"),
                "send_failure_class": bound.get("failure_class"),
                "send_attempt_limit": bound.get("limit"),
            })
            return 0
    # The outbox's existing message grammar, not a new one: the validator that enforces it
    # also binds the key to its thread, and that binding is what stops a queue from writing
    # into someone else's conversation. Measured -- the first shape tried was rejected with
    # ValueError("invalid event_key").
    event_key = f"coconala:message:v1:{talkroom_id}:ask-buyer-{key[:16]}"
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_json(args.output, {
        "status": "ready",
        "errors": [],
        "items": [{
            "platform": "coconala",
            "priority": "P0",
            "event_type": "ask_buyer",
            "event_key": event_key,
            "coordination_key": f"coconala:{talkroom_id}",
            "covered_event_keys": [event_key],
            "talkroom_id": talkroom_id,
            "talkroom_url": f"https://coconala.com/talkrooms/{talkroom_id}",
            # Both required by reply_queue.enqueue: it reads detected_at to stamp the
            # outbox row, and an item without it never becomes claimable.
            "origin_at": observed_at,
            "detected_at": observed_at,
            "blocker_key": key,
            "blocked_state": state,
            # Whether this buyer has already received something labelled 正式な納品.
            # It changes what the question has to open with, and it is read from the
            # project ledger here because the order may no longer be in any queue.
            "formal_delivery_observed": ask_buyer.formal_delivery_recorded(args.project_root),
            "next_action": "ask_buyer",
        }],
    })
    return 0


def _buyer_feedback_text(state: dict, project_root: str | None) -> str | None:
    """What the buyer actually wrote, from the file the blocked record names.

    Without it the question is composed from the blocker alone and reads like a form. The
    DM browser used to supply the thread; it is not on this path any more, but the builder
    rewrites the packet-bound requirements file with the current feedback every pass and
    the BLOCKED record names that file, so the buyer's own words are already on disk.
    """
    source = str((state or {}).get("requirements_path") or "").strip()
    if not source:
        return None
    path = Path(source).expanduser()
    if project_root:
        # The record is written by the model; the path it names is only trusted inside
        # the project it belongs to.
        try:
            path.resolve().relative_to(Path(project_root).expanduser().resolve())
        except (OSError, ValueError):
            return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return str(payload.get("feedback_text") or "").strip() or None


def compose(args: argparse.Namespace) -> int:
    """Write the question as a paid-talkroom answer payload.

    The question used to be sent by the DM lane (``reply_lane --ask-buyer``), which drives
    the message-detail browser. On a paid talkroom that browser lands on a different page
    and dies with collector_unhealthy:unexpected_title -- measured 2026-08-06, so the one
    branch that existed to break the deadlock could not deliver a single character.

    No new send path is built here. The composed question is written into the shape the
    paid-progress browser already accepts, and travels out on the lane that is already
    open to this buyer.
    """
    try:
        queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 1
    items = [item for item in (queue.get("items") or []) if isinstance(item, dict)]
    if not items:
        return 1
    import reply_composer  # noqa: PLC0415 -- optional dependency of this subcommand only

    composer = reply_composer.RunnerComposer(
        runner=Path(args.runner),
        schema=Path(args.schema),
        workdir=Path(args.workdir),
        prompt_builder=lambda context: ask_buyer.question_prompt(
            state=(context or {}).get("blocked_state"),
            conversation=(context or {}).get("conversation"),
            formal_delivery_observed=(context or {}).get("formal_delivery_observed") is True,
        ),
        task_label="gig-ask-buyer-compose",
    )
    state = items[0].get("blocked_state") or {}
    try:
        body = composer({
            "blocked_state": state,
            "conversation": _buyer_feedback_text(state, getattr(args, "project_root", None)),
            "formal_delivery_observed": items[0].get("formal_delivery_observed") is True,
        })
    except Exception:  # noqa: BLE001 -- a question that cannot be written must not fail the pass
        return 1
    # The two messages this buyer already received were polite and asked nothing. A third
    # of that shape is worse than silence, so it is refused rather than sent.
    if not ask_buyer.check_question(body).get("ok"):
        return 1
    _write_json(args.output, {"version": 1, "status": "answer", "message": str(body).strip()})
    return 0


def report(args: argparse.Namespace) -> int:
    """Tell Dais that a paying customer was asked a question, and why.

    The DM lane reported this through telegram_report's reply command, which reads the
    reply-outbox connector events. Those rows do not exist on this path, and reproducing
    them to keep the old call would be a lot of machinery for a worse report. Three facts
    are what he actually needs: which talkroom, what we asked, and what we were stuck on.
    Sent through the same openclaw transport, with the same receipt, as every other report.
    """
    try:
        queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
        answer = json.loads(Path(args.answer).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 1
    items = [item for item in (queue.get("items") or []) if isinstance(item, dict)]
    if not items or not isinstance(answer, dict):
        return 1
    item = items[0]
    state = item.get("blocked_state") or {}
    talkroom = str(item.get("talkroom_id") or "").strip()
    blocker = str(state.get("blocker") or "").strip()
    if not blocker:
        blocker = "、".join(ask_buyer.missing_items(state)) or "（自動診断なし）"
    message = "\n".join((
        "❓ 着手できない有償案件について、購入者へ質問を送りました",
        "",
        "状態",
        "お支払い済みのお客様に、制作を始めるために必要な情報をこちらから伺いました。",
        "",
        f"トークルーム: https://coconala.com/talkrooms/{talkroom}",
        "",
        "送った質問",
        str(answer.get("message") or "").strip(),
        "",
        "着手できなかった理由",
        f"- {blocker}",
        "",
        "次に自動で行うこと",
        "- お客様の返信を確認し、届き次第そのまま制作に入ります。",
        "ユーザーの操作は必要ありません。",
    ))
    import telegram_report  # noqa: PLC0415 -- only this subcommand needs the transport

    transport = telegram_report.OpenClawTelegramTransport(target=str(args.target))
    try:
        transport.send_report(
            message,
            event_key=f"coconala:ask-buyer:v1:{talkroom}:{ask_buyer.blocker_key(state)[:16]}",
        )
    except Exception:  # noqa: BLE001 -- an unreported send is still a completed send
        return 1
    return 0


def record(args: argparse.Namespace) -> int:
    result = {}
    try:
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    queue = {}
    try:
        queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    keys = {
        str(item.get("talkroom_id") or ""): str(item.get("blocker_key") or "")
        for item in (queue.get("items") or [])
        if isinstance(item, dict)
    }
    for event in (result.get("events") or []) if isinstance(result, dict) else []:
        if not isinstance(event, dict) or str(event.get("status") or "") != "replied":
            continue
        thread_id = str(event.get("talkroom_id") or "")
        key = keys.get(thread_id)
        if not key:
            continue
        row = json.dumps({"talkroom_id": thread_id, "blocker_key": key}, ensure_ascii=False)
        try:
            target = Path(args.ledger)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(row + "\n")
            os.chmod(target, 0o600)
        except OSError:
            continue
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("build")
    plan.add_argument("--project-root", required=True)
    plan.add_argument("--talkroom-id", required=True)
    plan.add_argument("--ledger", required=True)
    plan.add_argument("--output", required=True)
    # Optional: absent means "no bound", which is what every existing caller and test got
    # before the bound existed. Supplying it is what makes an endlessly failing send stop.
    plan.add_argument("--send-attempts", default=None)
    plan.set_defaults(handler=build)

    write = sub.add_parser("compose")
    write.add_argument("--queue", required=True)
    write.add_argument("--runner", required=True)
    write.add_argument("--schema", required=True)
    write.add_argument("--workdir", required=True)
    write.add_argument("--output", required=True)
    write.add_argument("--project-root")
    write.set_defaults(handler=compose)

    tell = sub.add_parser("report")
    tell.add_argument("--queue", required=True)
    tell.add_argument("--answer", required=True)
    tell.add_argument("--target", default="42")
    tell.set_defaults(handler=report)

    done = sub.add_parser("record")
    done.add_argument("--result", required=True)
    done.add_argument("--queue", required=True)
    done.add_argument("--ledger", required=True)
    done.set_defaults(handler=record)

    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
