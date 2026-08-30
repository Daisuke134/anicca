#!/usr/bin/env python3
"""Deterministic instant/hourly/daily Gig reports over durable Telegram outbox."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_verdict  # noqa: E402  -- A19 four-layer health verdict (no false-OK)
import listing_ledger  # noqa: E402  -- the single source of truth for listing counts
import paid_progress_ledger  # noqa: E402  -- buyer-visible progress on paid contracts
import report_envelope  # noqa: E402  -- canonical human/agent report snapshot
from gig_paths import RUNNER_DIR  # noqa: E402


JST = timezone(timedelta(hours=9))
DEFAULT_USAGE_LEDGER = (
    Path.home() / ".local/state/anicca/telemetry/agent-usage.jsonl"
)
# The auditor's own measurements are the liveness authority (§0.8 observation
# window); the daily verdict reads them instead of trusting the reporter itself.
DEFAULT_AUDITOR_LOG = Path.home() / ".openclaw/logs/gig-auditor.out.log"


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from telegram_outbox import TelegramOutbox, TelegramOutboxError, dispatch_one
    from owner_notify import send_email_if_configured
except ModuleNotFoundError:
    _outbox_module = _load_local("telegram_outbox")
    _notify_module = _load_local("owner_notify")
    TelegramOutbox = _outbox_module.TelegramOutbox
    TelegramOutboxError = _outbox_module.TelegramOutboxError
    dispatch_one = _outbox_module.dispatch_one
    send_email_if_configured = _notify_module.send_email_if_configured


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def composition_route(config_path: Path) -> str:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    candidates = config["task_classes"]["composition-agent"]["candidates"]
    labels: list[str] = []
    for candidate in candidates:
        provider = str(candidate.get("provider") or "")
        model = str(candidate.get("model") or "")
        effort = str(candidate.get("effort") or "")
        if model == "gpt-5.6-terra":
            name = "Terra"
        elif model == "gpt-5.6-luna":
            name = "Luna"
        elif provider in ("claude", "claude-direct"):
            name = f"Claude {model.title()}"
        else:
            name = model
        labels.append(f"{name} {effort}".strip())
    if not labels:
        raise ValueError("composition route is empty")
    return " → ".join(labels)


def reply_envelope(event: dict[str, Any]) -> dict[str, Any]:
    action_id = int(event["action_id"])
    revision = int(event["revision"])
    if action_id <= 0 or revision <= 0 or event.get("status") != "replied":
        raise ValueError("invalid verified reply event")
    thread_id = str(event.get("talkroom_id") or "")
    if not thread_id:
        raise ValueError("missing reply thread")
    origin = _timestamp(event["origin_at"])
    sent = _timestamp(event["seller_sent_at"])
    latency_minutes = max(0, math.ceil((sent - origin).total_seconds() / 60))
    work_event = {
        "event_key": f"gig:reply:{action_id}:{revision}",
        "kind": "reply",
        "entity_id": thread_id,
        "occurred_at": sent.isoformat(),
        "state": "confirmed",
        "action": "購入者の新しいメッセージへ返信",
        "result": f"新しい質問1件へ{latency_minutes}分で回答しました",
        "next_action": "契約または追加メッセージを自動で確認します",
        "evidence": ["connector_reply"],
        "attributes": {
            "latency_minutes": latency_minutes,
            "within_30_minute_sla": latency_minutes <= 30,
        },
    }
    return report_envelope.build_work_event_envelope(
        work_event=work_event,
        observed_at=sent,
    )


def reply_message(event: dict[str, Any], route: str) -> tuple[str, str]:
    del route
    envelope = reply_envelope(event)
    action_id = int(event["action_id"])
    revision = int(event["revision"])
    return (
        f"gig:telegram:reply:v2:{action_id}:{revision}",
        envelope["data"]["human_message_ja"],
    )


def publish_reply_events(
    *,
    events: list[dict[str, Any]],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now: Callable[[], int],
    agent_feed_path: Path | None = None,
) -> dict[str, int]:
    for event in events:
        if agent_feed_path is not None:
            report_envelope.append_agent_feed(
                agent_feed_path,
                reply_envelope(event),
            )
        event_key, message = reply_message(event, route)
        outbox.enqueue(
            event_key=event_key,
            kind="reply_verified",
            message=message,
            created_at=now(),
            # A verified reply is an event-keyed external work result.  Two
            # replies can render the same generic sentence but are still two
            # facts the human must be able to see.
            suppress_identical_body=False,
        )
    summary = {"sent": 0, "delivery_unknown": 0}
    pending = int(outbox.counts().get("pending", 0))
    for _ in range(pending):
        result = dispatch_one(
            outbox,
            owner=f"gig-telegram-{uuid.uuid4().hex}",
            now=now,
            transport=transport,
        )
        status = str(result["status"])
        if status == "queue_empty":
            break
        if status == "sent":
            summary["sent"] += 1
        elif status == "delivery_unknown":
            summary["delivery_unknown"] += 1
        else:
            raise RuntimeError(f"unexpected Telegram dispatch status: {status}")
    return summary


def _wake_count(state: dict[str, Any], key: str) -> str:
    value = state.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "未確認"
    return f"{value}件"


def _wake_positive(state: dict[str, Any], key: str) -> bool:
    value = state.get(key)
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _wake_health(state: dict[str, Any]) -> str:
    status = str(state.get("status") or "")
    if status == "operator_brake":
        return "paused"
    failed = state.get("failed")
    if status == "failed" or (
        isinstance(failed, int) and not isinstance(failed, bool) and failed > 0
    ):
        return "failed"
    required = (
        "observed", "actionable", "effect", "official_readback", "blocked",
        "historical_dlq", "newly_dlq", "failed", "pending", "skipped",
        "deferred",
        "officially_unrepliable_count", "stop_contact_count",
        "classification_failed_count",
        "semantic_judgement_failed_count", "semantic_migration_pending_count",
        "thread_changed_buyer_count", "thread_readback_count",
        "thread_revalidated_count",
    )
    if any(_wake_count(state, key) == "未確認" for key in required):
        return "degraded"
    if status in {
        "busy", "skipped_browser_restart", "restart_defer",
        "deferred", "reconcile_pending", "pending_verify",
    } or any(
        _wake_positive(state, key)
        for key in (
            "blocked", "dlq", "newly_dlq", "pending", "skipped", "deferred",
            "classification_failed_count", "semantic_judgement_failed_count",
            "semantic_migration_pending_count",
        )
    ):
        return "degraded"
    return "healthy"


def _wake_time(value: Any) -> str | None:
    if not value:
        return None
    try:
        moment = _timestamp(value).astimezone(JST)
    except (TypeError, ValueError):
        return None
    return f"{moment.year}年{moment.month}月{moment.day}日 {moment.hour:02d}:{moment.minute:02d}ごろ"


def reply_wake_message(state: dict[str, Any], route: str = "") -> tuple[str, str]:
    """Render one human health report for one five-minute reply detector wake."""
    del route
    run_id = str(state.get("run_id") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", run_id):
        raise ValueError("invalid reply wake identity")
    health = _wake_health(state)
    heading = {
        "healthy": "✅ 交渉ループは正常に動いています。",
        "degraded": "🟡 交渉ループは稼働しています。確認・整理中の項目があります。",
        "failed": "🔴 交渉ループの実処理で失敗しました。",
        "paused": "⏸️ 交渉ループはオペレーターの安全停止中です。",
    }[health]
    status = str(state.get("status") or "")
    lines = ["[ココナラ][交渉ループ]", heading, ""]
    if status == "operator_brake":
        lines.extend([
            "今回は受信箱を確認しておらず、返信・見積りの送信処理にも進んでいません。",
            "これは交渉処理の失敗ではありません。約3分後に安全停止状態を再確認します。",
        ])
        return f"gig:telegram:reply-wake:v1:{run_id}", "\n".join(lines)
    if status == "busy":
        lines.extend([
            "前回の確認処理が継続中のため、今回は重複起動せず見送りました。",
            "この確認では返信・見積りを送信していません。前回処理の完了後に再確認します。",
        ])
        return f"gig:telegram:reply-wake:v1:{run_id}", "\n".join(lines)
    if status in {"skipped_browser_restart", "restart_defer"}:
        lines.append("今回は安全確認のため処理を見送りました。")
    def raw_count(key: str, *, missing: int | None = None) -> int | None:
        value = state.get(key, missing)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    def display(value: int | None) -> str:
        return f"{value}件" if value is not None else "未確認"

    observed = raw_count("observed")
    actionable = raw_count("actionable")
    effect = raw_count("effect")
    official = raw_count("official_readback")
    estimate_required = raw_count("estimate_required", missing=0)
    estimate_effect = raw_count("estimate_effect", missing=0)
    estimate_readback = raw_count("estimate_readback", missing=0)
    normal_actionable = max(0, actionable - estimate_required) if actionable is not None and estimate_required is not None else None
    normal_effect = max(0, effect - estimate_effect) if effect is not None and estimate_effect is not None else None
    normal_official = max(0, official - estimate_readback) if official is not None and estimate_readback is not None else None
    lines.append(
        f"{display(observed)}の会話を確認しました。通常返信の処理対象は{display(normal_actionable)}、見積りの追跡対象は{display(estimate_required)}です。"
    )
    lines.append(
        "新着・変更されたbuyer-lastは"
        f"{_wake_count(state, 'thread_changed_buyer_count')}、今回strict判定した会話は"
        f"{_wake_count(state, 'thread_readback_count')}、旧記録を再確認した会話は"
        f"{_wake_count(state, 'thread_revalidated_count')}です。"
    )
    lines.append(
        f"通常返信の新規送信は{display(normal_effect)}、公式確認は{display(normal_official)}です。"
    )
    lines.append(
        "公式上メッセージを送れない会話は"
        f"{_wake_count(state, 'officially_unrepliable_count')}、相手が連絡終了を希望した会話は"
        f"{_wake_count(state, 'stop_contact_count')}です。これらには送信していません。"
    )
    if _wake_positive(state, "policy_ignored_count"):
        lines.append(
            "private no-contact policyにより"
            f"{_wake_count(state, 'policy_ignored_count')}を送信せず終了しました。"
        )
    lines.append(
        f"見積りの新規提出は{display(estimate_effect)}、公式提出確認は{display(estimate_readback)}です。"
        f"送信前に失敗し次回再試行する見積りは{_wake_count(state, 'estimate_failed')}、"
        f"送信後の公式確認待ちは{_wake_count(state, 'estimate_pending')}です。確認待ちには再送しません。"
    )
    lines.append(
        "現在の会話状態を判定できなかった会話は"
        f"{_wake_count(state, 'semantic_judgement_failed_count')}、旧判定記録を整理中の会話は"
        f"{_wake_count(state, 'semantic_migration_pending_count')}です。"
    )
    lines.append("")
    lines.append(
        "送信できない会話は"
        f"{_wake_count(state, 'blocked')}、以前から隔離している会話は"
        f"{_wake_count(state, 'historical_dlq')}、今回新たに隔離した会話は"
        f"{_wake_count(state, 'newly_dlq')}、"
        f"ループ全体の実処理失敗は{_wake_count(state, 'failed')}、公式確認待ちは{_wake_count(state, 'pending')}です。"
    )
    if _wake_positive(state, "skipped") or state.get("skipped") is None:
        lines.append(f"今回見送った会話は{_wake_count(state, 'skipped')}です。")
    lines.append(f"通常返信で次回へ持ち越した会話は{_wake_count(state, 'deferred')}です。")
    oldest = _wake_time(state.get("oldest_actionable"))
    if oldest:
        lines.append(f"最も古い未解決は{oldest}から残っています。")
    lines.append("")
    next_wake = _wake_time(state.get("next_wake"))
    if next_wake:
        lines.append(f"次は{next_wake}（約3分後）にもう一度確認します。")
    else:
        lines.append("約3分後にもう一度確認します。")
    return f"gig:telegram:reply-wake:v1:{run_id}", "\n".join(lines)


def publish_reply_wake(
    *,
    state: dict[str, Any],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Enqueue and dispatch exactly one durable report for one detector wake."""
    event_key, message = reply_wake_message(state, route)
    row = outbox.enqueue(
        event_key=event_key,
        kind="reply_wake",
        message=message,
        created_at=now_epoch,
        suppress_identical_body=False,
    )
    result = dispatch_one(
        outbox,
        owner=f"gig-telegram-{uuid.uuid4().hex}",
        now=lambda: now_epoch,
        transport=transport,
        report_id=int(row["report_id"]),
    )
    status = str(result["status"])
    if status == "sent":
        return {"sent": 1, "delivery_unknown": 0}
    if status == "delivery_unknown":
        return {"sent": 0, "delivery_unknown": 1}
    if status == "queue_empty":
        return {"sent": 0, "delivery_unknown": 0}
    raise RuntimeError(f"unexpected Telegram dispatch status: {status}")


def report_kinds_for_command(command: str) -> tuple[str, ...] | None:
    """Keep a lane wake from redriving or draining another lane's reports."""
    if command in {"reply", "reply-wake", "reply-dlq"}:
        return ("reply_verified", "reply_wake", "reply_dlq")
    return None


def ready_report_ids_for_kinds(
    outbox: TelegramOutbox, kinds: tuple[str, ...], *, now: int, limit: int = 3,
) -> list[int]:
    """Return a bounded cross-kind queue without selecting any foreign kind."""
    return sorted(
        report_id
        for kind in kinds
        for report_id in outbox.ready_report_ids(kind=kind, now=now, limit=limit)
    )[:limit]


def reply_dlq_message(entry: dict[str, Any], route: str) -> tuple[str, str]:
    """One alert per dead-lettered reply entry: what left, why, and how to undo it."""
    action_id = int(entry["action_id"])
    thread_id = str(entry.get("talkroom_id") or "")
    if action_id <= 0 or not thread_id:
        raise ValueError("invalid reply dead-letter event")
    consecutive = int(entry.get("consecutive") or 0)
    error_class = str(entry.get("error_class") or "unknown")[:200]
    return (
        f"gig:telegram:reply-dlq:v1:{action_id}",
        (
            f"[{route}] 返信キューを打ち切りました: トークルーム {thread_id}"
            f"（{error_class} が {consecutive} 回連続）。"
            f"このメッセージには返信していません。原因を直したら"
            f" requeue_closed_action(action_id={action_id}) で戻せます。"
        ),
    )


def publish_reply_dlq_alerts(
    *,
    events: list[dict[str, Any]],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Say out loud that a buyer thread was abandoned by the machine.

    A dead letter is the one outcome that looks like silence from every angle:
    the queue gets shorter, the error count drops, and nobody replied. The event
    key is the action id, so the durable outbox emits it exactly once per entry
    no matter how many times a later run re-reads the same file.
    """
    summary = {"sent": 0, "delivery_unknown": 0}
    if not events:
        return summary
    for entry in events:
        event_key, message = reply_dlq_message(entry, route)
        outbox.enqueue(
            event_key=event_key,
            kind="reply_dlq",
            message=message,
            created_at=now_epoch,
        )
    return _drain_pending(outbox=outbox, transport=transport, now_epoch=now_epoch)


BARREN_ESCALATION_BASE = 3
BARREN_ESCALATION_FACTOR = 4


def barren_escalation_rung(streak: int) -> int:
    """The highest rung of the escalation ladder this streak has climbed.

    3, 12, 48, 192 ... Each rung is a fourfold worsening, so a lane that stays
    broken speaks a handful of times over days rather than once per pass or
    once per lifetime.
    """
    rung = BARREN_ESCALATION_BASE
    while rung * BARREN_ESCALATION_FACTOR <= streak:
        rung *= BARREN_ESCALATION_FACTOR
    return rung


def publish_barren_alerts(
    *,
    alerts: list[dict[str, Any]],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Alert on a barren streak, and again each time the streak multiplies.

    The event key is anchored to the streak's START, not to the pass, so the
    hook can run on every pass (its only call site) without re-sending while
    nothing changes. A lane that recovers and then goes barren again opens a new
    anchor and is therefore allowed to alert again.

    The anchor alone was not enough. On 2026-08-05 the apply lane sat at a barren
    streak of 104 -- three days, 104 passes, zero recorded applications -- and the
    only message Dais ever received was the one sent at streak 3. A silence
    warning that itself falls silent as the problem grows is the failure it was
    written to prevent, so the key also carries the escalation rung.
    """
    summary = {"sent": 0, "delivery_unknown": 0}
    if not alerts:
        return summary
    for alert in alerts:
        lane = str(alert["lane"])
        anchor = int(float(alert["streak_started_at"]))
        label = str(alert.get("label", lane))
        rung = barren_escalation_rung(int(alert.get("streak", 0) or 0))
        # The message must stay byte-identical for one rung: the outbox rejects a
        # re-enqueue of the same key with a different payload, and the streak
        # COUNT keeps growing between rungs. So the text carries the rung, not the
        # live count.
        outbox.enqueue(
            event_key=f"gig:telegram:lane-barren:v1:{lane}:{anchor}:{rung}",
            kind="lane_barren",
            message=(
                f"[{route}] 沈黙警告: {label}({lane}) が {rung} 回以上連続で実作業ゼロ。"
                f"lane は生きているが台帳に成果が出ていない。"
                f"起点 {datetime.fromtimestamp(anchor, timezone.utc).isoformat()}"
            ),
            created_at=now_epoch,
        )
    pending = int(outbox.counts().get("pending", 0))
    for _ in range(pending):
        result = dispatch_one(
            outbox,
            owner=f"gig-telegram-{uuid.uuid4().hex}",
            now=lambda: now_epoch,
            transport=transport,
        )
        status = str(result["status"])
        if status == "queue_empty":
            break
        if status == "sent":
            summary["sent"] += 1
        elif status == "delivery_unknown":
            summary["delivery_unknown"] += 1
        else:
            raise RuntimeError(f"unexpected Telegram dispatch status: {status}")
    return summary


def blocked_repairs(database: Path) -> list[dict[str, Any]]:
    """Incidents the healer has given up on, newest first."""
    if not database.exists():
        return []
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT incident_id, fingerprint, repair_class, attempt_count, blocked_at
                 FROM repair_queue WHERE state='blocked'
                ORDER BY incident_id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def publish_blocked_repair_alerts(
    *,
    blocked: list[dict[str, Any]],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Tell Dais when self-healing has given up on a fault.

    'blocked' is terminal: the queue's unique index stops any newer incident with
    the same fingerprint from opening, so a blocked incident freezes both the
    repair and the detection. On 2026-08-05 application:barren_streak had been
    blocked since 2026-08-03 and nothing anywhere said so. The event key is the
    incident, so one message per giving-up, never a repeat per audit.
    """
    summary = {"sent": 0, "delivery_unknown": 0}
    if not blocked:
        return summary
    for incident in blocked:
        incident_id = int(incident["incident_id"])
        fingerprint = str(incident["fingerprint"])
        repair_class = str(incident.get("repair_class") or "unknown")
        attempts = int(incident.get("attempt_count") or 0)
        outbox.enqueue(
            event_key=f"gig:telegram:repair-blocked:v1:{incident_id}",
            kind="repair_blocked",
            message=(
                f"[{route}] 自己修復が諦めました: {fingerprint}"
                f"（修復 {repair_class} を {attempts} 回試行して失敗）。"
                f"この不具合は今後 自動では検知も修復もされません。"
            ),
            created_at=now_epoch,
        )
    return _drain_pending(outbox=outbox, transport=transport, now_epoch=now_epoch)


def _drain_pending(
    *,
    outbox: TelegramOutbox,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Send whatever is queued. Same loop the reply/barren publishers run inline."""
    summary = {"sent": 0, "delivery_unknown": 0}
    pending = int(outbox.counts().get("pending", 0))
    for _ in range(pending):
        result = dispatch_one(
            outbox,
            owner=f"gig-telegram-{uuid.uuid4().hex}",
            now=lambda: now_epoch,
            transport=transport,
        )
        status = str(result["status"])
        if status == "queue_empty":
            break
        if status == "sent":
            summary["sent"] += 1
        elif status == "delivery_unknown":
            summary["delivery_unknown"] += 1
        else:
            raise RuntimeError(f"unexpected Telegram dispatch status: {status}")
    return summary


PASS_OUTAGE_COMMANDS = ("pass-blocked", "pass-recovered", "pass-silence")


def publish_pass_outage(
    *,
    command: str,
    gig_dir: Path,
    outbox: TelegramOutbox,
    transport: Callable[[str], str],
    now_epoch: int,
    reason: str = "",
    detail: str = "",
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Announce that the pass stopped, and later that it came back -- once each.

    The gate that refuses a pass and the auditor that notices nobody finished one
    write into the same single outage record, so a known cause is never buried
    under the symptom it produces. Publishing is enqueue-then-clear: the durable
    outbox owns delivery from the moment the row lands.
    """
    pass_outage = _load_local("pass_outage")
    state_path = Path(gig_dir) / pass_outage.DEFAULT_STATE_FILENAME
    action = "none"
    record = None

    if command == "pass-blocked":
        started_at = now_epoch
        if reason == "stop_flag" and detail:
            # The sentinel stamped the flag when it stopped us, which is a truer
            # outage start than the hourly wake that first noticed.
            try:
                started_at = int(Path(detail).stat().st_mtime)
            except OSError:
                started_at = now_epoch
        record = pass_outage.open_outage(
            state_path=state_path,
            reason=reason,
            started_at=started_at,
            now=now_epoch,
            detail=detail,
        )
        action = "opened" if record is not None else "none"
    elif command == "pass-recovered":
        record = pass_outage.close_outage(
            state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=now_epoch
        )
        action = "recovered" if record is not None else "none"
    elif command == "pass-silence":
        # Everything after state_path exists to tell "nothing ran" apart from
        # "everything ran and died", and to let the ladder act on the second
        # before anyone is told about it.
        evaluation = pass_outage.evaluate_pass_silence(
            heartbeat_path=Path(gig_dir) / pass_outage.DEFAULT_HEARTBEAT_FILENAME,
            state_path=state_path,
            now=now_epoch,
            environ=environ,
            failures_path=Path(gig_dir) / pass_outage.DEFAULT_FAILURES_FILENAME,
            evidence_root=Path(gig_dir) / pass_outage.DEFAULT_EVIDENCE_DIRNAME,
            isolation_path=Path(gig_dir) / "state" / "step-isolation.json",
            repair_database=Path(gig_dir) / "gig-control.sqlite3",
            source_root=Path(__file__).resolve().parents[2],
        )
        action = str(evaluation["action"])
        record = evaluation["record"] if action in ("opened", "recovered") else None
    else:  # pragma: no cover - argparse constrains the command set
        raise ValueError(f"not a pass outage command: {command}")

    if record is not None:
        builder = (
            pass_outage.outage_report if action == "opened" else pass_outage.recovery_report
        )
        event_key, kind, message = builder(record)
        try:
            outbox.enqueue(
                event_key=event_key, kind=kind, message=message, created_at=now_epoch
            )
        except TelegramOutboxError:
            # A same-key row already exists: the event is durable, which is all
            # this call had to guarantee. Never re-raise into the caller's exit.
            pass
        if action == "recovered":
            pass_outage.clear_state(state_path)

    summary: dict[str, Any] = dict(
        _drain_pending(outbox=outbox, transport=transport, now_epoch=now_epoch)
    )
    summary["action"] = action
    if command == "pass-silence":
        # The log line is the only place a rung climbed in silence is visible.
        summary["state"] = evaluation["health"]["state"]
        summary["ladder"] = evaluation["ladder"]["action"]
        summary["consecutive"] = evaluation["health"]["consecutive"]
    return summary


def _connector_stats(database: Path) -> dict[str, int]:
    counts = {"replied": 0, "pending": 0, "reconcile_pending": 0, "breach": 0}
    if not Path(database).exists():
        return counts
    try:
        with sqlite3.connect(database) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='connector_actions'"
            ).fetchone()
            if exists is None:
                return counts
            for state, count in connection.execute(
                "SELECT state,COUNT(*) FROM connector_actions GROUP BY state"
            ):
                if state in counts:
                    counts[str(state)] = int(count)
            counts["breach"] = int(connection.execute(
                """SELECT COUNT(*) FROM connector_actions
                   WHERE state='replied' AND seller_sent_at IS NOT NULL
                     AND seller_sent_at-created_at>1800"""
            ).fetchone()[0])
    except sqlite3.Error:
        return counts
    return counts


def _verified_net_mrr(work_events_path: Path) -> int:
    """Sum only explicit, active monthly net revenue from marketplace contracts."""
    latest_by_contract: dict[str, dict[str, Any]] = {}
    for row in _jsonl(Path(work_events_path)):
        contract_id = str(row.get("entity_id") or "").strip()
        attributes = row.get("attributes")
        if (
            row.get("kind") != "contract"
            or not contract_id
            or not isinstance(attributes, dict)
            or "marketplace_order" not in (row.get("evidence") or [])
        ):
            continue
        previous = latest_by_contract.get(contract_id)
        if previous is None or str(row.get("occurred_at") or "") >= str(
            previous.get("occurred_at") or ""
        ):
            latest_by_contract[contract_id] = row
    total = 0
    for row in latest_by_contract.values():
        attributes = row["attributes"]
        if (
            row.get("state") != "confirmed"
            or attributes.get("recurring_active") is not True
            or attributes.get("billing_period") != "monthly"
        ):
            continue
        value = attributes.get("monthly_net_jpy")
        if isinstance(value, bool):
            continue
        try:
            amount = int(float(str(value or "0").replace(",", "")))
        except ValueError:
            continue
        if amount > 0:
            total += amount
    return total


def hourly_message(
    *,
    connector_database: Path,
    telegram_outbox: TelegramOutbox,
    route: str,
    now: datetime,
    gig_dir: Path | None = None,
) -> str:
    stats = _connector_stats(connector_database)
    telegram_unknown = telegram_outbox.counts().get("delivery_unknown", 0)
    stamp = now.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")
    lines = [
        f"⏱ gig毎時SLA {stamp}",
        f"verified={stats['replied']} / pending={stats['pending']} / reconcile={stats['reconcile_pending']}",
        f"P1 breach={stats['breach']} / Telegram未確定={telegram_unknown}",
        f"route={route}",
    ]
    if gig_dir is not None:
        try:
            projector = _load_local("kpi_funnel_projector")
            snapshot = projector.project_state(Path(gig_dir), as_of=now.isoformat())
            def metric(value: dict[str, Any], *, money: bool = False) -> str:
                if value.get("status") != "known":
                    return "不明"
                amount = int(value["value"])
                return f"¥{amount:,}" if money else str(amount)
            lines.extend(("", "💰 売上KPI（公式証拠ベース）"))
            for label, period_name in (("直近1時間", "hour"), ("今日", "day"), ("7日", "seven_day")):
                period = snapshot["periods"][period_name]
                store = period["lanes"]["storefront"]
                apply = period["lanes"]["apply"]
                lines.append(
                    f"{label}: 出品 {metric(store['stages']['settled'])}件/{metric(store['net_jpy'], money=True)}"
                    f"｜応募 {metric(apply['stages']['settled'])}件/{metric(apply['net_jpy'], money=True)}"
                    f"｜全体 {metric(period['all']['settled_count'])}件/{metric(period['all']['net_jpy'], money=True)}"
                )
            ledger = _jsonl(Path(gig_dir) / "kpi-readback-audit.jsonl")
            if ledger:
                latest = ledger[-1]
                audit_status = str(latest.get("status") or "unknown")
                reason = str(
                    ((latest.get("checks") or {}).get("official_readback") or {}).get("reason")
                    or "公式/local一致"
                )
                icon = "✅" if audit_status == "match" else "⚠️"
                lines.append(f"{icon} 公式照合: {audit_status}（{reason}）")
            else:
                lines.append("⚠️ 公式照合: receiptなし")
            lines.append("不明は0ではありません。証拠が揃うまで売上を推定しません。")
        except Exception as error:
            lines.extend(("", f"🚨 KPI生成エラー: {type(error).__name__}"))
    return "\n".join(lines)


def _latest_pass_row(gig_dir: Path) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    success_rows = _jsonl(Path(gig_dir) / "pass-report.jsonl")
    failure_rows = _jsonl(Path(gig_dir) / "pass-failures.jsonl")
    if success_rows:
        candidates.append(success_rows[-1])
    if failure_rows:
        candidates.append(failure_rows[-1])
    rows = [
        row for row in candidates
        if isinstance(row.get("ts"), int) and isinstance(row.get("pass_id"), str)
    ]
    return max(rows, key=lambda value: value["ts"]) if rows else None


def pass_envelope(
    *,
    gig_dir: Path,
    usage_ledger: Path,
    observed_at: datetime | None = None,
) -> dict[str, Any] | None:
    """Build the canonical snapshot for the most recently finished pass."""
    row = _latest_pass_row(gig_dir)
    if row is None:
        return None
    # Rebuilding the same pass must be byte-stable.  The durable pass timestamp
    # is therefore also the default observation time; the outbox keeps its own
    # actual enqueue/send timestamps.
    if observed_at is None:
        observed_at = datetime.fromtimestamp(row["ts"], timezone.utc)
    evidence_value = row.get("evidence_dir")
    lane_events = (
        report_envelope.collect_lane_events(
            evidence_dir=Path(evidence_value),
            pass_id=str(row["pass_id"]),
            occurred_at=row["ts"],
        )
        if isinstance(evidence_value, str) and evidence_value
        else []
    )
    return report_envelope.build_pass_envelope(
        pass_row=row,
        applications=_jsonl(Path(gig_dir) / "applied.jsonl"),
        usage_rows=_jsonl(Path(usage_ledger)),
        observed_at=observed_at,
        lane_events=lane_events,
        net_mrr_jpy=_verified_net_mrr(Path(gig_dir) / "work-events.jsonl"),
    )


def pass_message(
    *,
    gig_dir: Path,
    usage_ledger: Path,
    route: str,
    envelope: dict[str, Any] | None = None,
) -> tuple[str, str] | None:
    """Render Telegram from the same envelope written to the agent feed."""
    del route  # routing is operational metadata, not user-facing work status
    snapshot = envelope or pass_envelope(
        gig_dir=gig_dir,
        usage_ledger=usage_ledger,
    )
    if snapshot is None:
        return None
    pass_id = snapshot["data"]["trace_id"]
    status = snapshot["data"]["status"]
    key = f"gig:telegram:pass:v3:{pass_id}:{status}"
    return key, report_envelope.render_human_ja(snapshot)


def application_recovery_message(
    evidence: dict[str, Any],
    *,
    route: str,
) -> tuple[str, str]:
    """Report a code-owned canonical reconciliation omitted by an earlier pass."""
    recovery_id = str(evidence.get("recovery_id") or "").strip()
    applications = evidence.get("applications")
    if (
        evidence.get("source") != "canonical_orphan_reconciliation"
        or not recovery_id
        or not isinstance(applications, list)
        or not applications
        or not all(isinstance(row, dict) for row in applications)
    ):
        raise ValueError("application_recovery_evidence_invalid")
    lines = [
        "🩹 gig応募自己回復",
        f"recovery={recovery_id}",
        f"応募 verified={len(applications)}件",
    ]
    for application in applications:
        request_id = str(application.get("request_id") or "").strip()
        bucket = str(application.get("bucket") or "")
        title = re.sub(
            r"\s+", " ", str(application.get("title") or "")
        ).strip()
        url = str(application.get("url") or "")
        if (
            not request_id
            or bucket not in {"single", "retainer"}
            or not title
            or not url
        ):
            raise ValueError("application_recovery_row_invalid")
        label = "継続" if bucket == "retainer" else "単発"
        lines.append(f"- [{label}] {title} / request={request_id}")
        lines.append(f"  {url}")
        lines.append("  応募履歴✅ 台帳✅ 過去報告補正✅")
    lines.append(f"route={route}")
    return (
        f"gig:telegram:application-recovery:v1:{recovery_id}",
        "\n".join(lines),
    )


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


VOLUME_TARGET = 100

def write_application_volume_controller(
    *, gig_dir: Path, now: datetime | None = None, output_path: Path | None = None,
) -> dict[str, Any]:
    """Write one atomic, bounded daily volume decision from existing ledgers."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local, stamp = now.astimezone(JST), now.timestamp()
    start = datetime(local.year, local.month, local.day, tzinfo=JST).timestamp(); end = start + 86400
    applied = {str(row.get("requestId") or row.get("request_id")) for row in _jsonl(Path(gig_dir) / "applied.jsonl")
               if row.get("status") == "applied" and row.get("submit_verified") is True and row.get("applied_page_verified") is True
               and row.get("requestId", row.get("request_id")) and (time := listing_ledger.parse_ts(row.get("ts"))) is not None and start <= time <= stamp < end}
    wakes = {str(row.get("pass_id") or time) for row in _jsonl(Path(gig_dir) / "pass-report.jsonl")
             if (time := listing_ledger.parse_ts(row.get("ts"))) is not None and start <= time <= stamp < end}
    shortfalls = [row for row in _jsonl(Path(gig_dir) / "b2-shortfall.jsonl")
                  if (time := listing_ledger.parse_ts(row.get("recorded_at"))) is not None and start <= time <= stamp < end]
    source = stage = "unknown"
    if shortfalls:
        latest = max(shortfalls, key=lambda row: listing_ledger.parse_ts(row.get("recorded_at")) or 0)
        errors = [str(error) for error in (latest.get("blocking_errors") or []) + (latest.get("shortfall_errors") or [])]
        exhausted = latest.get("outcome") == "shortfall" and not latest.get("eligible_work_available") \
            and not any(error.startswith("under_target_search_not_exhausted") for error in errors)
        source = str(latest.get("source_status") or ("exhausted" if exhausted else "open"))
        if source == "exhausted" and not exhausted: source = "open"
        stage = str(latest.get("largest_loss_stage") or "")
        if not stage:
            eligible, reported = int(latest.get("eligible_work_available") or 0), int(latest.get("applications_reported") or 0)
            stage = ("attempted_to_verified" if any(any(token in error for token in ("readback", "ledger", "submit")) for error in errors)
                     else "discovered_to_eligible" if eligible == 0
                     else "eligible_to_attempted" if reported < eligible else "daily_target_gap")
    verified, observed = len(applied), len(wakes); deficit = max(0, VOLUME_TARGET - verified)
    remaining = max(0, math.ceil((end - stamp) / 1800)); target = max(1, min(8, math.ceil(deficit / max(1, remaining))))
    cap = max(3, min(6, target + 1))
    state = {
        "version": 1,
        "jst_day": local.date().isoformat(), "daily_target": VOLUME_TARGET,
        "verified_applications": verified, "remaining_applications": deficit,
        "observed_wakes": observed, "verified_average_per_observed_wake": round(verified / observed, 4) if observed else 0.0,
        "remaining_scheduled_wakes": remaining, "target_this_wake": target, "turn_cap": cap,
        "source_status": source, "largest_loss_stage": stage,
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, separators=(",", ":")); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    return state


def _volume_controller_for_report(gig_dir: Path, now: datetime) -> dict[str, Any]:
    path = Path(gig_dir) / "application-volume-controller.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) and value.get("jst_day") == now.astimezone(JST).date().isoformat() else {}


def _volume_controller_line(state: dict[str, Any]) -> str:
    if not state:
        return "応募量コントローラ: unavailable"
    verified, target = int(state.get("verified_applications") or 0), int(state.get("daily_target") or VOLUME_TARGET)
    return ("応募量コントローラ: "
            f"verified={verified}/{target} deficit={max(0, target - verified)} wake average={float(state.get('verified_average_per_observed_wake') or 0):g} "
            f"turn cap={int(state.get('turn_cap') or 0)} source status={state.get('source_status') or 'unknown'} "
            f"largest loss={state.get('largest_loss_stage') or 'unknown'}")


def _write_work_event_report_state(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "version": 1,
                    "seen_event_keys": sorted(seen),
                },
                handle,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _read_work_event_report_state(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("work_event_report_state_unreadable") from error
    keys = value.get("seen_event_keys") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("version") != 1
        or not isinstance(keys, list)
        or not all(isinstance(key, str) and key for key in keys)
    ):
        raise ValueError("work_event_report_state_invalid")
    return set(keys)


def publish_work_event_reports(
    *,
    events_path: Path,
    state_path: Path,
    agent_feed_path: Path,
    outbox: TelegramOutbox,
    transport: Callable[[str], str],
    now: Callable[[], int],
) -> dict[str, int]:
    """Publish only newly projected business events; baseline old history once."""
    supported = {"contract", "payment", "incident", "recovery"}
    events = [
        row
        for row in _jsonl(Path(events_path))
        if row.get("kind") in supported
        and isinstance(row.get("event_key"), str)
        and row.get("event_key")
    ]
    seen = _read_work_event_report_state(Path(state_path))
    if seen is None:
        baseline = {str(event["event_key"]) for event in events}
        _write_work_event_report_state(Path(state_path), baseline)
        return {
            "sent": 0,
            "delivery_unknown": 0,
            "bootstrapped": len(baseline),
            "enqueued": 0,
        }

    observed_epoch = now()
    observed_at = datetime.fromtimestamp(observed_epoch, timezone.utc)
    enqueued = 0
    for event in events:
        event_key = str(event["event_key"])
        outbox_event_key = f"gig:telegram:work-event:v1:{event_key}"
        # This stream is history-baselined on first observation.  A seen key
        # therefore intentionally remains quiet even when its old row was
        # never materialized; live instant events use the repair-aware path
        # below.
        if event_key in seen:
            continue
        envelope = report_envelope.build_work_event_envelope(
            work_event=event,
            observed_at=observed_at,
        )
        report_envelope.append_agent_feed(Path(agent_feed_path), envelope)
        outbox.enqueue(
            event_key=outbox_event_key,
            kind=str(event["kind"]),
            message=report_envelope.render_human_ja(envelope),
            created_at=observed_epoch,
            # Incidents and recoveries are operational alerts and keep the
            # volume-control window.  Confirmed business results are
            # irreversible event facts, so their event key wins over body
            # coalescing.
            suppress_identical_body=str(event["kind"]) in {"incident", "recovery"},
        )
        seen.add(event_key)
        enqueued += 1
    _write_work_event_report_state(Path(state_path), seen)
    dispatched = publish_reply_events(
        events=[],
        outbox=outbox,
        route="",
        transport=transport,
        now=now,
    )
    return {
        **dispatched,
        "bootstrapped": 0,
        "enqueued": enqueued,
    }


def publish_instant_work_event_reports(
    *,
    events_path: Path,
    state_path: Path,
    agent_feed_path: Path,
    outbox: TelegramOutbox,
    transport: Callable[[str], str],
    now: Callable[[], int],
) -> dict[str, int]:
    """Publish new application/delivery facts immediately, without migration baselining."""
    supported = {"application", "delivery"}
    events = [
        row
        for row in _jsonl(Path(events_path))
        if row.get("kind") in supported
        and isinstance(row.get("event_key"), str)
        and row.get("event_key")
    ]
    seen = _read_work_event_report_state(Path(state_path)) or set()
    observed_epoch = now()
    observed_at = datetime.fromtimestamp(observed_epoch, timezone.utc)
    historical_skipped = 0
    enqueued = 0
    instant_report_ids: list[int] = []
    for event in events:
        try:
            occurred_epoch = _timestamp(event.get("occurred_at")).timestamp()
        except (TypeError, ValueError, OverflowError):
            historical_skipped += 1
            continue
        if occurred_epoch < observed_epoch - 24 * 60 * 60:
            historical_skipped += 1
            continue
        event_key = str(event["event_key"])
        outbox_event_key = f"gig:telegram:instant-work-event:v1:{event_key}"
        envelope = report_envelope.build_work_event_envelope(
            work_event=event,
            observed_at=observed_at,
        )
        message = report_envelope.render_human_ja(envelope)
        if event_key in seen and outbox.has_event(outbox_event_key):
            queued = outbox.enqueue(
                event_key=outbox_event_key,
                kind=str(event["kind"]),
                message=message,
                created_at=observed_epoch,
                suppress_identical_body=False,
            )
            if queued.get("state") == "pending":
                instant_report_ids.append(int(queued["report_id"]))
            continue
        if event_key not in seen:
            report_envelope.append_agent_feed(Path(agent_feed_path), envelope)
        queued = outbox.enqueue(
            event_key=outbox_event_key,
            kind=str(event["kind"]),
            message=message,
            created_at=observed_epoch,
            # Application and delivery are irreversible business results.  A
            # repeated body is not a duplicate event, so preserve both rows.
            suppress_identical_body=False,
        )
        instant_report_ids.append(int(queued["report_id"]))
        seen.add(event_key)
        enqueued += 1
    _write_work_event_report_state(Path(state_path), seen)
    dispatched = {"sent": 0, "delivery_unknown": 0}
    for report_id in instant_report_ids:
        result = dispatch_one(
            outbox,
            owner=f"gig-telegram-{uuid.uuid4().hex}",
            now=now,
            transport=transport,
            report_id=report_id,
        )
        status = str(result["status"])
        if status == "sent":
            dispatched["sent"] += 1
        elif status == "delivery_unknown":
            dispatched["delivery_unknown"] += 1
            break
        elif status != "queue_empty":
            raise RuntimeError(f"unexpected Telegram dispatch status: {status}")
    return {
        **dispatched,
        "enqueued": enqueued,
        "historical_skipped": historical_skipped,
    }


LANE_REPORT_NAMES = {
    "listing": "Shuppin",
    "application": "Oubo",
    "reply": "Reply",
    "delivery": "Nouhin",
}
TASK_LABEL_LANES = {
    "gig-B0": "listing",
    "gig-B2": "application",
    "gig-B1": "reply",
    "gig-PAID_WORK": "delivery",
}
PASS_EVENT = re.compile(r"^(listing|application|reply|delivery):pass-(.+)$")


def _four_lane_attribution(
    *,
    lane_database: Path,
    evidence_root: Path,
    usage_ledger: Path,
    earnings_path: Path,
    now: datetime,
) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    lanes = {
        lane: {
            "checked": 0,
            "eligible": 0,
            "actions": 0,
            "verified": 0,
            "noops": set(),
            "duplicate": 0,
            "model_calls": 0,
            "cost": 0.0,
            "revenue": 0,
            "pass_ids": set(),
            # X3: a lane that never ran must be visible as such. Folding not_run into
            # "verified" is what made 47 skipped passes read as 47 healthy checks.
            "not_run": 0,
            "last_action_at": 0,
        }
        for lane in LANE_REPORT_NAMES
    }
    missing: set[str] = set()
    start_epoch = int((now.astimezone(timezone.utc) - timedelta(hours=24)).timestamp())
    end_epoch = int(now.astimezone(timezone.utc).timestamp())
    if not Path(lane_database).exists():
        missing.update(lanes)
    else:
        try:
            with sqlite3.connect(lane_database) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(
                    """SELECT lane,event_key,action_kind,state,side_effect_count,
                              blind_retry_count,observed_at
                       FROM lane_actions
                       WHERE observed_at>=? AND observed_at<?
                       ORDER BY action_id""",
                    (start_epoch, end_epoch),
                ).fetchall()
        except sqlite3.Error:
            rows = []
            missing.update(lanes)
        for row in rows:
            lane = str(row["lane"])
            match = PASS_EVENT.fullmatch(str(row["event_key"]))
            if lane not in lanes or match is None or match.group(1) != lane:
                continue
            values = lanes[lane]
            values["checked"] += 1
            values["pass_ids"].add(match.group(2))
            if row["action_kind"] == "not_run":
                # X1 writes this when poll mode never invoked the lane. Counting it as a
                # verification is what turned a silent outage into "verified=47".
                values["not_run"] += 1
            elif row["action_kind"] == "verified_noop":
                values["noops"].add("verified_noop")
            else:
                values["eligible"] += 1
                side_effects = int(row["side_effect_count"] or 0)
                values["actions"] += side_effects
                if side_effects > 0:
                    # Real work, not merely a run: this is the clock the report shows.
                    values["last_action_at"] = max(
                        values["last_action_at"], int(row["observed_at"] or 0)
                    )
            if row["action_kind"] != "not_run" and row["state"] in ("verified", "verified_noop"):
                values["verified"] += 1
            values["duplicate"] += int(row["blind_retry_count"] or 0)
            values["duplicate"] += max(0, int(row["side_effect_count"] or 0) - 1)
    for lane, values in lanes.items():
        if values["checked"] == 0:
            missing.add(lane)

    usage_rows = _jsonl(Path(usage_ledger))
    usage_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in usage_rows:
        budget = row.get("budget")
        pass_id = budget.get("scope_id") if isinstance(budget, dict) else None
        task_label = row.get("task_label")
        if row.get("loop") == "gig" and isinstance(pass_id, str) and isinstance(task_label, str):
            usage_index.setdefault((pass_id, task_label), []).append(row)

    all_pass_ids = sorted({
        pass_id
        for values in lanes.values()
        for pass_id in values["pass_ids"]
    })
    for pass_id in all_pass_ids:
        poll_path = Path(evidence_root) / f"gig-pass-{pass_id}" / "poll-control.json"
        try:
            poll = json.loads(poll_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            for lane, values in lanes.items():
                if pass_id in values["pass_ids"]:
                    missing.add(lane)
            continue
        labels = poll.get("model_call_labels")
        if (
            poll.get("version") != 1
            or poll.get("pass_id") != pass_id
            or not isinstance(labels, list)
            or poll.get("model_calls") != len(labels)
        ):
            for lane, values in lanes.items():
                if pass_id in values["pass_ids"]:
                    missing.add(lane)
            continue
        for raw_label in labels:
            task_label = str(raw_label)
            if not task_label.startswith("gig-"):
                task_label = f"gig-{task_label}"
            lane = TASK_LABEL_LANES.get(task_label)
            if lane is None or pass_id not in lanes[lane]["pass_ids"]:
                missing.add(lane or "agent-runner")
                continue
            matched_usage = usage_index.get((pass_id, task_label), [])
            if not matched_usage:
                missing.add(lane)
                continue
            lanes[lane]["model_calls"] += 1
            for usage in matched_usage:
                cost = usage.get("provider_cost_usd")
                if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                    lanes[lane]["cost"] += float(cost)
                else:
                    missing.add(lane)

    if not Path(earnings_path).exists():
        missing.add("delivery")
    else:
        settled_states = {"検収", "支払", "検収完了", "completed", "paid"}
        for row in _jsonl(Path(earnings_path)):
            pass_id = row.get("pass_id")
            task_label = row.get("task_label")
            if (
                row.get("status") in settled_states
                and isinstance(pass_id, str)
                and task_label == "gig-PAID_WORK"
                and pass_id in lanes["delivery"]["pass_ids"]
                and isinstance(row.get("evidence"), str)
                and row["evidence"]
            ):
                try:
                    lanes["delivery"]["revenue"] += int(
                        str(row.get("jpy", 0)).replace(",", "")
                    )
                except ValueError:
                    missing.add("delivery")

    # How long each lane may be silent before it is called out. Reply and applications
    # are the revenue path and should move several times a day; storefront and profile
    # are daily craft work.
    silence_budget_h = {"reply": 8, "application": 8, "delivery": 8, "listing": 36}

    lines: list[str] = []
    for lane, report_name in LANE_REPORT_NAMES.items():
        values = lanes[lane]
        noop = ",".join(sorted(values["noops"])) or "-"
        last_action = values.get("last_action_at") or 0
        if last_action:
            silent_h = (end_epoch - last_action) / 3600.0
            silence = f"{silent_h:.1f}h"
        else:
            silent_h = float("inf")
            silence = "記録なし"
        budget = silence_budget_h.get(lane, 24)
        mark = "🔴" if silent_h > budget else "✅"
        lines.append(
            f"{mark} {report_name}: 実行={values['actions']} 未実行pass={values['not_run']} "
            f"最終実行={silence} (許容{budget}h) "
            f"checked={values['checked']} verified={values['verified']} noop={noop} "
            f"model_calls={values['model_calls']} cost=${values['cost']:.2f} "
            f"revenue=¥{values['revenue']}"
        )
    stalled = [
        LANE_REPORT_NAMES[lane]
        for lane in LANE_REPORT_NAMES
        if ((end_epoch - (lanes[lane].get("last_action_at") or 0)) / 3600.0
            > silence_budget_h.get(lane, 24))
    ]
    if stalled:
        lines.insert(0, f"⚠️ 停止中のlane: {', '.join(stalled)}")
    return lines, sorted(missing), lanes


def daily_message(
    *,
    gig_dir: Path,
    connector_database: Path,
    telegram_outbox: TelegramOutbox,
    route: str,
    now: datetime,
    lane_database: Path | None = None,
    evidence_root: Path | None = None,
    usage_ledger: Path = DEFAULT_USAGE_LEDGER,
) -> str:
    lane_lines, missing, _lanes = _four_lane_attribution(
        lane_database=lane_database or (Path(gig_dir) / "lane-actions.sqlite3"),
        evidence_root=evidence_root or (Path(gig_dir) / "evidence"),
        usage_ledger=usage_ledger,
        earnings_path=Path(gig_dir) / "earnings.jsonl",
        now=now,
    )
    applied_rows = _jsonl(Path(gig_dir) / "applied.jsonl")
    applications = [row for row in applied_rows if row.get("status") == "applied"]
    # 返信・納品 counts buyer-visible work, so it must include progress replies sent on
    # already-won paid contracts. Those used to be appended to applied.jsonl, which made
    # them visible here for free -- at the cost of the apply funnel and the category
    # bandit counting a paid-contract update as a 募集 application reply. X22 moved the
    # write to its own ledger; this line is what keeps the daily number whole. An action
    # that happened and stops being counted is indistinguishable from one never taken.
    replies = [
        row for row in applied_rows
        if row.get("status") in ("replied", "評価依頼", "delivered")
    ] + _jsonl(Path(gig_dir) / paid_progress_ledger.LEDGER_FILENAME)
    # Listings are NOT counted here. This line used to count publish *rows*, so one
    # listing republished four times was reported as four, and the report said 7 while
    # the funnel said 4 for the same day. Both now read listing_ledger's taxonomy.
    listing_events = listing_ledger.load_events(
        Path(gig_dir) / listing_ledger.LEDGER_FILENAME
    )
    listings_total = listing_ledger.count(listing_events)
    listing_day_start, listing_day_end = listing_ledger.jst_day_bounds_for(now)
    listings_today = listing_ledger.count(
        listing_events, since=listing_day_start, until=listing_day_end
    )
    settled_states = {"検収", "支払", "検収完了", "completed", "paid"}
    earnings = [
        row for row in _jsonl(Path(gig_dir) / "earnings.jsonl")
        if row.get("status") in settled_states and row.get("evidence")
    ]
    jpy = 0.0
    for row in earnings:
        try:
            jpy += float(str(row.get("jpy", 0)).replace(",", "") or 0)
        except ValueError:
            continue
    # "応募累計:109" was byte-identical for four days while applications were dead. A
    # total can only be read as progress against the total you remember, so carry the
    # day's delta beside it and let a zero speak for itself.
    #
    # The window is the JST natural day this report is headed with -- not a rolling 24h
    # off wall-clock UTC. The header already said "2026-07-27" while every delta beside
    # it measured 09:07-to-09:07, so the report contradicted its own date.
    day_start = listing_day_start

    def _fmt_delta(fresh: int) -> str:
        return f"+{fresh}" if fresh else "±0"

    def _delta(rows: list[dict]) -> str:
        fresh = 0
        for row in rows:
            moment = listing_ledger.parse_ts(row.get("ts"))
            if moment is not None and day_start <= moment < listing_day_end:
                fresh += 1
        return _fmt_delta(fresh)

    stats = _connector_stats(connector_database)
    telegram_unknown = telegram_outbox.counts().get("delivery_unknown", 0)
    today = now.astimezone(JST).date().isoformat()
    lane_status = (
        "状態: HEALTHY | lane evidence=4/4"
        if not missing
        else f"状態: FAIL | missing evidence={','.join(missing)}"
    )
    listing_caveats = []
    if listings_total.unidentified_publish_events:
        listing_caveats.append(
            f"出品ID不明の公開記録={listings_total.unidentified_publish_events}件"
            "(重複排除できないため未計上)"
        )
    if listings_total.created_listings:
        listing_caveats.append(f"下書きのみ={listings_total.created_listings}")
    listing_note = f" ※{' / '.join(listing_caveats)}" if listing_caveats else ""
    daily_ops = _weekly_metrics(
        gig_dir=Path(gig_dir),
        usage_ledger=Path(usage_ledger),
        start=listing_day_start,
        end=listing_day_end,
    )

    return "\n".join((
        f"🧰 gig日報 (Coconala/mtdc) {today}",
        lane_status,
        *lane_lines,
        f"応募累計:{len(applications)}({_delta(applications)}) / "
        f"返信・納品:{len(replies)}({_delta(replies)}) / "
        f"出品公開:{listings_total.published_listings}"
        f"({_fmt_delta(listings_today.published_listings)})"
        f" ※括弧内=当日JST{listing_note}",
        f"売上(検収済):{len(earnings)}件 ¥{jpy:.0f}",
        f"日次funnel: 応募 {daily_ops['applications']} → 返信 {daily_ops['replies']} → "
        f"契約 {daily_ops['contracts']} → 納品 {daily_ops['deliveries']} → "
        f"入金 {daily_ops['paid']}",
        f"日次運用: model cost ${daily_ops['model_cost']:.2f} / "
        f"incident {daily_ops['incidents']} / "
        f"self-heal recovery evidence {daily_ops['recoveries']}",
        f"即応: verified={stats['replied']} / pending={stats['pending']} / reconcile={stats['reconcile_pending']}",
        f"SLA breach={stats['breach']} / Telegram未確定={telegram_unknown}",
        f"返信route={route}",
        "✅ 実¥あり" if jpy > 0 else "(実¥まだ0=受注待ち・正直報告)",
    ))


def _completed_week_bounds(now: datetime) -> tuple[float, float, str, str]:
    local = now.astimezone(JST)
    current_monday = local.date() - timedelta(days=local.weekday())
    end = datetime(
        current_monday.year, current_monday.month, current_monday.day, tzinfo=JST
    )
    start = end - timedelta(days=7)
    return (
        start.timestamp(),
        end.timestamp(),
        start.date().isoformat(),
        (end.date() - timedelta(days=1)).isoformat(),
    )


def weekly_event_key(now: datetime) -> str:
    _, _, week_start, _ = _completed_week_bounds(now)
    return f"gig:telegram:weekly:v1:{week_start.replace('-', '')}"


def _in_window(row: dict[str, Any], start: float, end: float, *fields: str) -> bool:
    for field in fields:
        moment = listing_ledger.parse_ts(row.get(field))
        if moment is None:
            try:
                local = datetime.strptime(
                    str(row.get(field) or ""), "%Y/%m/%d %H:%M"
                ).replace(tzinfo=JST)
                moment = local.timestamp()
            except ValueError:
                pass
        if moment is not None:
            return start <= moment < end
    return False


def _weekly_metrics(
    *, gig_dir: Path, usage_ledger: Path, start: float, end: float,
) -> dict[str, Any]:
    applied_rows = _jsonl(Path(gig_dir) / "applied.jsonl")
    request_id = lambda row: str(row.get("requestId") or "").strip()
    applications = {
        request_id(row) for row in applied_rows
        if row.get("status") == "applied"
        and request_id(row)
        and _in_window(row, start, end, "ts", "applied_at")
    }
    replies = {
        request_id(row) for row in applied_rows
        if row.get("status") in ("replied", "followed_up")
        and request_id(row)
        and _in_window(row, start, end, "ts", "applied_at")
    }
    contracts = {
        request_id(row) for row in applied_rows
        if row.get("status") in ("評価依頼", "delivered", "delivered_pending")
        and request_id(row)
        and _in_window(row, start, end, "ts", "applied_at")
    }

    settled_states = {"検収", "支払", "検収完了", "completed", "paid"}
    paid_rows = [
        row for row in _jsonl(Path(gig_dir) / "earnings.jsonl")
        if row.get("status") in settled_states
        and row.get("evidence")
        and _in_window(row, start, end, "ts", "finished_at")
    ]
    revenue = 0.0
    for row in paid_rows:
        try:
            revenue += float(str(row.get("jpy", 0)).replace(",", "") or 0)
        except ValueError:
            continue

    listing_events = listing_ledger.load_events(
        Path(gig_dir) / listing_ledger.LEDGER_FILENAME
    )
    listings = listing_ledger.count(listing_events, since=start, until=end)

    deliveries = 0
    for transaction in (Path(gig_dir) / "evidence").glob("**/paid-queue-evidence.json"):
        try:
            row = json.loads(transaction.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if (
            row.get("sent") is True
            and row.get("formal_delivery_checkbox") is True
            and _in_window(row, start, end, "captured_at")
        ):
            deliveries += 1

    model_calls = 0
    model_cost = 0.0
    for row in _jsonl(Path(usage_ledger)):
        if row.get("loop") != "gig" or not _in_window(
            row, start, end, "timestamp", "ts", "finished_at", "started_at"
        ):
            continue
        model_calls += 1
        value = row.get("provider_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            model_cost += float(value)

    incidents = [
        row for row in _jsonl(Path(gig_dir) / "pass-failures.jsonl")
        if _in_window(row, start, end, "ts")
    ]
    recoveries = 0
    for row in _jsonl(Path(gig_dir) / "audit.jsonl"):
        if not _in_window(row, start, end, "ts"):
            continue
        # "FIRING" means the loop is firing normally and "FRESH" means an open
        # thread is fresh; neither is a failure/recovery pair. Only the lane state
        # machine's explicit down -> ok transition is durable recovery evidence.
        recoveries += sum(
            isinstance(change, dict)
            and change.get("from") == "down"
            and change.get("to") == "ok"
            for change in (row.get("changed") or [])
        )

    try:
        strategy = json.loads((Path(gig_dir) / "strategy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        strategy = {}
    experiments = [
        row for row in (strategy.get("experiments") or [])
        if isinstance(row, dict) and _in_window(row, start, end, "ts")
    ]

    return {
        "applications": len(applications),
        "replies": len(replies),
        "contracts": len(contracts),
        "deliveries": deliveries,
        "paid": len(paid_rows),
        "revenue": revenue,
        "listings": listings.published_listings,
        "model_calls": model_calls,
        "model_cost": model_cost,
        "incidents": len(incidents),
        "recoveries": recoveries,
        "experiment_kept": sum(row.get("status") == "kept" for row in experiments),
        "experiment_reverted": sum(row.get("status") == "reverted" for row in experiments),
    }


def _weekly_outcome_progress(*, gig_dir: Path, now: datetime) -> dict[str, Any]:
    start, end = now.timestamp() - 40 * 86400, now.timestamp()
    applied: dict[str, dict[str, Any]] = {}
    for row in _jsonl(Path(gig_dir) / "applied.jsonl"):
        request_id = str(row.get("requestId") or "").strip()
        if row.get("status") != "applied" or not request_id:
            continue
        applied.setdefault(request_id, row)
    cohort = [(request_id, row) for request_id, row in applied.items()
              if _in_window(row, start, end, "ts", "applied_at")]
    latest = {
        str(row.get("request_id") or "").strip(): str(row.get("status") or "")
        for row in _jsonl(Path(gig_dir) / "applied-outcomes.jsonl") if row.get("request_id")
    }
    statuses = ("we_won", "someone_contracted", "closed_unfilled", "expired", "open")
    bands = ("<¥5k", "¥5k–<10k", "¥10k–<50k", "¥50k–<100k", "¥100k–<300k", "¥300k+", "不明")
    def amount(row: dict[str, Any], fields: tuple[str, ...]) -> float | None:
        for field in fields:
            value = row.get(field)
            if value is None or isinstance(value, bool): continue
            try:
                parsed = float(str(value).replace(",", "").strip())
            except (TypeError, ValueError):
                continue
            if math.isfinite(parsed) and parsed >= 0:
                return parsed
        return None
    def band(price: float | None) -> str:
        if price is None: return "不明"
        for ceiling, label in ((5_000, "<¥5k"), (10_000, "¥5k–<10k"), (50_000, "¥10k–<50k"), (100_000, "¥50k–<100k"), (300_000, "¥100k–<300k")):
            if price < ceiling:
                return label
        return "¥300k+"
    blank = lambda: {"applications": 0, "tracked": 0, "we_won": 0, "someone_contracted": 0}
    price_bands = {label: blank() for label in bands}
    client = blank()
    counts = {status: 0 for status in statuses}
    for request_id, row in cohort:
        status = latest.get(request_id, "")
        tracked = status in statuses
        if tracked: counts[status] += 1
        bucket = price_bands[band(amount(row, ("bid_jpy", "price_jpy", "price_proposed")))]
        bucket["applications"] += 1
        bucket["tracked"] += int(tracked)
        if status in ("we_won", "someone_contracted"):
            bucket[status] += 1
        if any((value := amount(row, (field,))) is not None and value >= 50_000 for field in ("budget_lo_jpy", "budget_hi_jpy")):
            client["applications"] += 1
            client["tracked"] += int(tracked)
            if status in ("we_won", "someone_contracted"): client[status] += 1
    applications = len(cohort)
    pct = lambda numerator, denominator: round(100 * numerator / denominator, 2) if denominator else None
    win_rate = pct(counts["we_won"], applications)
    return {
        "applications": applications, "tracked": sum(counts.values()), "coverage_pct": pct(sum(counts.values()), applications),
        "we_won": counts["we_won"], "someone_contracted": counts["someone_contracted"],
        "closed_unfilled": counts["closed_unfilled"], "expired": counts["expired"], "open": counts["open"],
        "application_win_rate_pct": win_rate,
        "application_win_rate_target_pct": 5.0,
        "application_win_rate_gap_pct_points": round(win_rate - 5.0, 2) if win_rate is not None else None,
        "competitive_win_rate_pct": pct(counts["we_won"], counts["we_won"] + counts["someone_contracted"]),
        "price_bands": price_bands,
        "client_budget_50k_plus": client,
    }


def _weekly_outcome_message_ja(outcome: dict[str, Any]) -> str:
    pct = lambda value: "不明" if value is None else f"{float(value):.2f}".rstrip("0").rstrip(".") + "%"
    counts = lambda value: f"{value['applications']}/{value['tracked']}/{value['we_won']}/{value['someone_contracted']}"
    bands = "、".join(f"{label} {counts(value)}" for label, value in outcome["price_bands"].items() if value["applications"])
    gap = outcome["application_win_rate_gap_pct_points"]
    return "\n".join((
        "直近40日の応募成果（応募/追跡/自受注/他者契約）",
        f"- 目標5% / 自受注率 {pct(outcome['application_win_rate_pct'])}（差{'不明' if gap is None else f'{gap:+.2f}pp'}） / "
        f"追跡{outcome['tracked']}件（{pct(outcome['coverage_pct'])}） / 競争勝率 {pct(outcome['competitive_win_rate_pct'])}",
        f"- 自受注{outcome['we_won']}件 / 他者契約{outcome['someone_contracted']}件 / "
        f"未契約終了{outcome['closed_unfilled']}件 / 消滅{outcome['expired']}件 / 追跡中(open){outcome['open']}件",
        f"- 提案価格帯: {bands}",
        f"- client提示¥50k+: {counts(outcome['client_budget_50k_plus'])}",
    ))


def _e3_daily_report(gig_dir: Path, now: datetime) -> dict[str, Any] | None:
    """Read daily_gig_report.py's (E3) own JST-day rollup instead of recomputing it --
    two independent counters of the same day would drift, and E3 already runs on every
    pass so its file is never more than one pass stale by the time this reads it.
    """
    jst_date = now.astimezone(JST).date().isoformat()
    path = Path(gig_dir) / "daily-report" / f"{jst_date}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def daily_envelope(
    *,
    gig_dir: Path,
    connector_database: Path,
    telegram_outbox: TelegramOutbox,
    now: datetime,
    lane_database: Path | None = None,
    evidence_root: Path | None = None,
    usage_ledger: Path = DEFAULT_USAGE_LEDGER,
    auditor_log: Path = DEFAULT_AUDITOR_LOG,
) -> dict[str, Any]:
    """Build the daily human/agent report from one normalized snapshot."""
    day_start, day_end = listing_ledger.jst_day_bounds_for(now)
    metrics = _weekly_metrics(
        gig_dir=Path(gig_dir),
        usage_ledger=Path(usage_ledger),
        start=day_start,
        end=day_end,
    )
    volume_controller = _volume_controller_for_report(Path(gig_dir), now)
    _, missing, lanes = _four_lane_attribution(
        lane_database=lane_database or (Path(gig_dir) / "lane-actions.sqlite3"),
        evidence_root=evidence_root or (Path(gig_dir) / "evidence"),
        usage_ledger=Path(usage_ledger),
        earnings_path=Path(gig_dir) / "earnings.jsonl",
        now=now,
    )
    # A19: the four layers are judged from the ledgers, never from pass status.
    health = daily_verdict.evaluate(
        gig_dir=Path(gig_dir),
        auditor_log=Path(auditor_log),
        lane_evidence_missing=sorted(missing),
        lane_not_run_total=sum(int(values["not_run"]) for values in lanes.values()),
        now=now,
    )
    local = now.astimezone(JST)
    month_start = datetime(local.year, local.month, 1, tzinfo=JST).timestamp()
    month_revenue = 0.0
    for row in _jsonl(Path(gig_dir) / "earnings.jsonl"):
        if (
            row.get("status") in {"検収", "支払", "検収完了", "completed", "paid"}
            and row.get("evidence")
            and _in_window(row, month_start, day_end, "ts", "finished_at")
        ):
            try:
                month_revenue += float(str(row.get("jpy") or "0").replace(",", ""))
            except ValueError:
                continue
    connector = _connector_stats(connector_database)
    period_work_events = [
        row
        for row in _jsonl(Path(gig_dir) / "work-events.jsonl")
        if _in_window(row, day_start, day_end, "occurred_at")
    ]
    incident_count = sum(
        row.get("kind") == "incident" for row in period_work_events
    )
    recovery_count = sum(
        row.get("kind") == "recovery" for row in period_work_events
    )
    if not period_work_events:
        incident_count = metrics["incidents"]
        recovery_count = metrics["recoveries"]
    snapshot = {
        "period_start": datetime.fromtimestamp(day_start, timezone.utc).isoformat(),
        "period_end": datetime.fromtimestamp(day_end, timezone.utc).isoformat(),
        "revenue_today_jpy": metrics["revenue"],
        "revenue_month_jpy": month_revenue,
        "work": {
            "searched": 0,
            "applied": metrics["applications"],
            "replied": metrics["replies"],
            "contracted": metrics["contracts"],
            "delivered": metrics["deliveries"],
            "paid": metrics["paid"],
            "listings_created": metrics["listings"],
            "listings_improved": 0,
        },
        "funnel": {
            "applications": metrics["applications"],
            "replies": metrics["replies"],
            "contracts": metrics["contracts"],
            "deliveries": metrics["deliveries"],
            "payments": metrics["paid"],
            "net_mrr": _verified_net_mrr(
                Path(gig_dir) / "work-events.jsonl"
            ),
        },
        "attention_lanes": sorted(missing),
        "pending_replies": connector["pending"] + connector["reconcile_pending"],
        "incidents": incident_count,
        "recoveries": recovery_count,
        "telegram_delivery_unknown": int(
            telegram_outbox.counts().get("delivery_unknown", 0)
        ),
        "model_calls": metrics["model_calls"],
        "model_cost_usd": metrics["model_cost"],
        "health": health,
        "volume_controller": volume_controller,
    }
    e3 = _e3_daily_report(Path(gig_dir), now)
    if e3 is not None:
        snapshot["buyer_replies_by_reaction"] = e3.get("buyer_replies_by_reaction") or {}
        snapshot["revenue_completed_today"] = int(e3.get("revenue_completed") or 0)
        snapshot["score_reality_by_band"] = e3.get("score_reality_by_band") or {}
    envelope = report_envelope.build_period_envelope(
        report_type="daily",
        period_id=local.strftime("%Y%m%d"),
        snapshot=snapshot,
        occurred_at=now,
    )
    envelope["data"]["human_message_ja"] += "\n\n" + _volume_controller_line(volume_controller)
    return envelope


def weekly_envelope(
    *,
    gig_dir: Path,
    telegram_outbox: TelegramOutbox,
    now: datetime,
    usage_ledger: Path = DEFAULT_USAGE_LEDGER,
) -> dict[str, Any]:
    """Build the weekly human/agent report from one normalized comparison."""
    start, end, start_day, end_day = _completed_week_bounds(now)
    current = _weekly_metrics(
        gig_dir=Path(gig_dir),
        usage_ledger=Path(usage_ledger),
        start=start,
        end=end,
    )
    outcome_progress = _weekly_outcome_progress(gig_dir=Path(gig_dir), now=now)
    previous = _weekly_metrics(
        gig_dir=Path(gig_dir),
        usage_ledger=Path(usage_ledger),
        start=start - 7 * 86400,
        end=start,
    )
    period_events = [
        row
        for row in _jsonl(Path(gig_dir) / "work-events.jsonl")
        if _in_window(row, start, end, "occurred_at")
    ]
    incidents = sum(row.get("kind") == "incident" for row in period_events)
    recoveries = sum(row.get("kind") == "recovery" for row in period_events)
    if not period_events:
        incidents = current["incidents"]
        recoveries = current["recoveries"]
    start_date = datetime.fromtimestamp(start, JST)
    end_date = datetime.fromtimestamp(end - 1, JST)
    snapshot = {
        "period_start_ja": f"{start_date.month}月{start_date.day}日",
        "period_end_ja": f"{end_date.month}月{end_date.day}日",
        "period_start_en": start_date.strftime("%B %-d"),
        "period_end_en": end_date.strftime("%B %-d"),
        "revenue_jpy": current["revenue"],
        "revenue_delta_jpy": current["revenue"] - previous["revenue"],
        "application_delta": current["applications"] - previous["applications"],
        "work": {
            "searched": 0,
            "applied": current["applications"],
            "replied": current["replies"],
            "contracted": current["contracts"],
            "delivered": current["deliveries"],
            "paid": current["paid"],
            "listings_created": current["listings"],
            "listings_improved": 0,
        },
        "funnel": {
            "applications": current["applications"],
            "replies": current["replies"],
            "contracts": current["contracts"],
            "deliveries": current["deliveries"],
            "payments": current["paid"],
            "net_mrr": _verified_net_mrr(
                Path(gig_dir) / "work-events.jsonl"
            ),
        },
        "incidents": incidents,
        "recoveries": recoveries,
        "experiment_kept": current["experiment_kept"],
        "experiment_reverted": current["experiment_reverted"],
        "telegram_delivery_unknown": int(
            telegram_outbox.counts().get("delivery_unknown", 0)
        ),
        "model_calls": current["model_calls"],
        "model_cost_usd": current["model_cost"], "outcome_progress": outcome_progress,
    }
    envelope = report_envelope.build_period_envelope(
        report_type="weekly",
        period_id=start_day.replace("-", ""),
        snapshot=snapshot,
        occurred_at=now,
    )
    envelope["data"]["outcome_progress"] = outcome_progress
    envelope["data"]["human_message_ja"] += "\n\n" + _weekly_outcome_message_ja(outcome_progress)
    return envelope


def weekly_message(
    *,
    gig_dir: Path,
    usage_ledger: Path = DEFAULT_USAGE_LEDGER,
    now: datetime,
    telegram_outbox: TelegramOutbox | None = None,
) -> str:
    start, end, start_day, end_day = _completed_week_bounds(now)
    current = _weekly_metrics(
        gig_dir=Path(gig_dir), usage_ledger=Path(usage_ledger), start=start, end=end,
    )
    previous = _weekly_metrics(
        gig_dir=Path(gig_dir), usage_ledger=Path(usage_ledger),
        start=start - 7 * 86400, end=start,
    )
    application_delta = current["applications"] - previous["applications"]
    revenue_delta = current["revenue"] - previous["revenue"]
    revenue_delta_text = (
        f"+¥{revenue_delta:.0f}" if revenue_delta >= 0 else f"-¥{abs(revenue_delta):.0f}"
    )
    unknown = (
        int(telegram_outbox.counts().get("delivery_unknown", 0))
        if telegram_outbox is not None else 0
    )
    return "\n".join((
        f"📈 gig週報 {start_day}..{end_day}",
        f"応募 {current['applications']} → 返信 {current['replies']} → "
        f"契約 {current['contracts']} → 納品 {current['deliveries']} → 入金 {current['paid']}",
        f"売上 ¥{current['revenue']:.0f} / 出品 {current['listings']} / "
        f"model cost ${current['model_cost']:.2f} ({current['model_calls']} calls)",
        f"前週比 応募 {application_delta:+d} / 売上 {revenue_delta_text}",
        f"incident {current['incidents']} / "
        f"self-heal recovery evidence {current['recoveries']}",
        f"experiment kept {current['experiment_kept']} / "
        f"reverted {current['experiment_reverted']}",
        f"Telegram未確定 {unknown}",
    ))


class OpenClawTelegramTransport:
    def __init__(
        self,
        *,
        target: str,
        executable: Path = Path("/opt/homebrew/bin/openclaw"),
        run: Callable[..., Any] = subprocess.run,
        receipt_dir: Path | None = None,
        now_ms: Callable[[], int] | None = None,
    ):
        self.target = str(target)
        self.executable = Path(executable)
        self.run = run
        self.receipt_dir = Path(
            receipt_dir or Path.home() / "gig/telegram-delivery-receipts"
        )
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))

    def __call__(self, message: str) -> str:
        return self.send_report(message, event_key=f"legacy:{hashlib.sha256(message.encode()).hexdigest()}")

    def send_report(self, message: str, *, event_key: str) -> str:
        message_id = send_email_if_configured(message, event_key=event_key, run=self.run)
        if message_id is None:
            command = [
                str(self.executable), "message", "send",
                "--channel", "telegram", "--target", self.target,
                "--message", message, "--json",
            ]
            try:
                completed = self.run(
                    command, stdin=subprocess.DEVNULL, capture_output=True,
                    text=True, timeout=60, check=False,
                )
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"Telegram transport failed rc={completed.returncode}"
                    )
                provider_output = completed.stdout
            except subprocess.TimeoutExpired as error:
                provider_output = error.stdout
                if not provider_output:
                    raise
            if isinstance(provider_output, bytes):
                provider_output = provider_output.decode("utf-8", errors="strict")
            try:
                result = json.loads(provider_output)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError("Telegram transport returned invalid JSON") from error
            payload = result.get("payload") if isinstance(result, dict) else None
            if isinstance(payload, dict) and payload.get("ok") is False:
                raise RuntimeError("Telegram provider rejected message")
            message_id = result.get("messageId") if isinstance(result, dict) else None
            if not message_id and isinstance(payload, dict):
                message_id = payload.get("messageId")
            if not message_id:
                raise RuntimeError("Telegram ACK has no message ID")
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        event_digest = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
        receipt = {
            "version": 1,
            "event_key": event_key,
            "target": os.environ.get("GIG_NOTIFY_EMAIL", "").strip() or self.target,
            "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
            "message_id": str(message_id),
            "provider_acked_at_epoch_ms": int(self.now_ms()),
        }
        fd, temporary = tempfile.mkstemp(
            prefix=f".{event_digest}.",
            suffix=".tmp",
            dir=self.receipt_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.receipt_dir / f"{event_digest}.json")
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        return str(message_id)


def _dispatch_message(
    *, outbox: TelegramOutbox, event_key: str, kind: str, message: str,
    transport: Callable[[str], str], now_epoch: int,
    suppress_identical_body: bool = True,
) -> dict[str, int]:
    outbox.enqueue(
        event_key=event_key, kind=kind, message=message, created_at=now_epoch,
        suppress_identical_body=suppress_identical_body,
    )
    tick = iter(range(now_epoch + 1, now_epoch + 1000)).__next__
    return publish_reply_events(events=[], outbox=outbox, route="", transport=transport, now=tick)


HERMES_AUDIT_LANES = ("paid", "reply", "apply", "storefront")
HERMES_AUDIT_METRICS = ("expected_due", "enqueued", "done", "executed", "deferred")


def hermes_audit_message(state: dict[str, Any]) -> tuple[str, str] | None:
    """Render only the fixed, terminal Hermes audit facts for Telegram."""
    if state.get("phase") == "active" and state.get("verdict") == "PENDING":
        return None
    if state.get("phase") != "terminal" or state.get("verdict") not in {"GREEN", "RED"}:
        raise ValueError("invalid Hermes audit state")
    audit_id = str(state.get("audit_id") or "").strip()
    if not audit_id:
        raise ValueError("invalid Hermes audit identity")
    since, until = state.get("since"), state.get("until")
    if (
        isinstance(since, bool) or isinstance(until, bool) or not isinstance(since, int)
        or not isinstance(until, int) or not 0 <= since < until
        or audit_id != f"{since}-{until}"
    ):
        raise ValueError("invalid Hermes audit identity")
    result = state.get("result") if isinstance(state.get("result"), dict) else {}
    if (
        result.get("version") != 1 or result.get("window_complete") is not True
        or result.get("verdict") != state.get("verdict")
        or result.get("since") != since or result.get("until") != until
    ):
        raise ValueError("invalid terminal Hermes audit result")
    number = lambda value: max(0, int(value)) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
    lanes = result.get("lanes") if isinstance(result.get("lanes"), dict) else {}
    def metric(lane: str, name: str) -> int:
        row = lanes.get(lane)
        return number(row.get(name)) if isinstance(row, dict) else 0
    lines = [
        "🧭 Hermes 24時間監査",
        f"監査ID: {audit_id}",
        f"監査期間: {number(state.get('since'))} – {number(state.get('until'))}",
        f"判定: {state['verdict']}",
    ]
    lines += [
        f"{lane}: " + " ".join(f"{name}={metric(lane, name)}" for name in HERMES_AUDIT_METRICS)
        for lane in HERMES_AUDIT_LANES
    ]
    if state["verdict"] == "RED":
        invariants = result.get("invariants") if isinstance(result.get("invariants"), dict) else {}
        failed_counts = {
            invariant: sum(metric(lane, field) for lane in HERMES_AUDIT_LANES)
            for invariant, field in (
                ("no_missing_due", "missing_slots"),
                ("no_bad_receipts", "nonzero_or_invalid_receipts"),
                ("no_blocked_tasks", "blocked"),
                ("no_stale_active", "stale_active"),
            )
        }
        applications = result.get("applications") if isinstance(result.get("applications"), dict) else {}
        telegram = result.get("telegram") if isinstance(result.get("telegram"), dict) else {}
        storefront = result.get("storefront") if isinstance(result.get("storefront"), dict) else {}
        failed_counts.update({
            "no_duplicate_applications": len(applications.get("duplicate_request_ids", [])),
            "all_applications_reported": len(telegram.get("unreported_application_ids", [])),
            "no_excess_storefront_effects": max(0, number(storefront.get("effect_count")) - metric("storefront", "executed")),
            "all_lanes_nonstarved": sum(metric(lane, "executed") == 0 for lane in HERMES_AUDIT_LANES),
        })
        failed = [
            f"{name}={failed_counts[name]}"
            for name in failed_counts
            if invariants.get(name) is False
        ]
        if failed:
            lines.append("失敗した不変条件: " + ", ".join(failed))
    return f"gig:telegram:hermes-audit:v1:{audit_id}", "\n".join(lines)


def publish_hermes_audit(
    *, state: dict[str, Any], outbox: TelegramOutbox,
    transport: Callable[[str], str], now_epoch: int,
) -> dict[str, int]:
    pair = hermes_audit_message(state)
    return ({"sent": 0, "delivery_unknown": 0} if pair is None else
            _dispatch_message(outbox=outbox, event_key=pair[0], kind="hermes_audit",
                              message=pair[1], transport=transport, now_epoch=now_epoch,
                              suppress_identical_body=False))


def main() -> int:
    home = Path.home()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "reply", "reply-dlq", "reply-wake", "pass", "hourly", "daily",
            "weekly", "flush", "lane-barren", "application-recovery",
            "work-events", "instant-work-events", "repair-blocked",
            "hermes-audit", "volume-controller", *PASS_OUTAGE_COMMANDS,
        ),
    )
    parser.add_argument(
        "--repair-database", type=Path, default=home / "gig/gig-control.sqlite3"
    )
    # pass_outage owns the canonical reason set and rejects anything outside it.
    parser.add_argument("--reason", default="")
    parser.add_argument("--detail", default="")
    parser.add_argument("--openclaw", type=Path, default=Path("/opt/homebrew/bin/openclaw"))
    parser.add_argument("--events", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--connector-database", type=Path, default=home / "gig/connector-outbox.sqlite3")
    parser.add_argument("--telegram-database", type=Path, default=home / "gig/telegram-outbox.sqlite3")
    parser.add_argument("--gig-dir", type=Path, default=home / "gig")
    parser.add_argument(
        "--runner-config", type=Path,
        default=RUNNER_DIR / "config.json",
    )
    parser.add_argument("--target", default=os.environ.get("GIG_REPORT_CHAT", ""))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit-state", type=Path)
    parser.add_argument("--now", default="")
    args = parser.parse_args()
    if args.command == "volume-controller":
        moment = datetime.now(timezone.utc)
        if args.now:
            moment = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        state = write_application_volume_controller(
            gig_dir=args.gig_dir,
            output_path=args.output or args.gig_dir / "application-volume-controller.json",
            now=moment,
        )
        print(json.dumps(state, ensure_ascii=False, separators=(",", ":")))
        return 0
    outbox = TelegramOutbox(args.telegram_database)
    now_epoch = int(time.time())
    outbox.recover_expired(now=now_epoch)
    outbox.reconcile_receipts(
        receipt_dir=args.gig_dir / "telegram-delivery-receipts",
        target=args.target,
        now=now_epoch,
    )
    redrive_kinds = report_kinds_for_command(args.command)
    outbox.redrive_unresolved(now=now_epoch, kinds=redrive_kinds)
    # The outage alarm must not depend on anything the outage may have broken --
    # least of all the model-routing config, which it never mentions to Dais.
    route = (
        ""
        if args.command in PASS_OUTAGE_COMMANDS
        or args.command in {"hermes-audit", "reply-wake"}
        else composition_route(args.runner_config)
    )
    transport = OpenClawTelegramTransport(
        target=args.target,
        executable=args.openclaw,
        receipt_dir=args.gig_dir / "telegram-delivery-receipts",
    )
    # Drain a few of the rows redrive_unresolved() just reopened, so a redriven
    # health report goes out on this same wake instead of waiting for the next
    # one. This is a drain, not a scheduler -- 3 is a bound, not a target -- and
    # it must never take down this lane's own report, which is why it is fenced
    # off in its own try/except.
    try:
        redrive_tick = iter(range(now_epoch, now_epoch + 10000)).__next__
        selected_ids: list[int] | None = None
        if redrive_kinds is not None:
            selected_ids = ready_report_ids_for_kinds(
                outbox, redrive_kinds, now=now_epoch, limit=3,
            )
        for index in range(3):
            if selected_ids is not None and index >= len(selected_ids):
                break
            drained = dispatch_one(
                outbox,
                owner=f"gig-telegram-{uuid.uuid4().hex}",
                now=redrive_tick,
                transport=transport,
                report_id=None if selected_ids is None else selected_ids[index],
            )
            if drained["status"] == "queue_empty":
                break
    except Exception:
        pass
    if args.command in PASS_OUTAGE_COMMANDS:
        result = publish_pass_outage(
            command=args.command,
            gig_dir=args.gig_dir,
            outbox=outbox,
            transport=transport,
            now_epoch=now_epoch,
            reason=args.reason,
            detail=args.detail,
        )
    elif args.command == "hermes-audit":
        if args.audit_state is None:
            raise SystemExit("--audit-state is required for hermes-audit")
        state = json.loads(args.audit_state.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise SystemExit("invalid Hermes audit state")
        result = publish_hermes_audit(
            state=state, outbox=outbox, transport=transport, now_epoch=now_epoch,
        )
    elif args.command == "instant-work-events":
        result = publish_instant_work_event_reports(
            events_path=args.gig_dir / "work-events.jsonl",
            state_path=args.gig_dir / "instant-work-event-report-state.json",
            agent_feed_path=args.gig_dir / "report-envelopes.jsonl",
            outbox=outbox,
            transport=transport,
            now=iter(range(now_epoch, now_epoch + 10000)).__next__,
        )
    elif args.command == "work-events":
        result = publish_work_event_reports(
            events_path=args.gig_dir / "work-events.jsonl",
            state_path=args.gig_dir / "work-event-report-state.json",
            agent_feed_path=args.gig_dir / "report-envelopes.jsonl",
            outbox=outbox,
            transport=transport,
            now=iter(range(now_epoch, now_epoch + 10000)).__next__,
        )
    elif args.command == "application-recovery":
        if args.evidence is None:
            raise SystemExit("--evidence is required for application-recovery")
        key, message = application_recovery_message(
            json.loads(args.evidence.read_text(encoding="utf-8")),
            route=route,
        )
        result = _dispatch_message(
            outbox=outbox,
            event_key=key,
            kind="application_recovery",
            message=message,
            transport=transport,
            now_epoch=now_epoch,
        )
    elif args.command == "lane-barren":
        # The silence alarm reads lane_health's measured streaks -- never a model's
        # self-report -- and rides the same per-pass choke point as the pass report.
        lane_health = _load_local("lane_health")
        result = publish_barren_alerts(
            alerts=lane_health.barren_alerts(),
            outbox=outbox, route=route, transport=transport, now_epoch=now_epoch,
        )
    elif args.command == "repair-blocked":
        # Read the repair queue itself, not the healer's return value: a controller
        # that crashed after blocking still left the incident terminal.
        result = publish_blocked_repair_alerts(
            blocked=blocked_repairs(args.repair_database),
            outbox=outbox, route=route, transport=transport, now_epoch=now_epoch,
        )
    elif args.command == "reply":
        if args.events is None:
            raise SystemExit("--events is required for reply")
        value = json.loads(args.events.read_text(encoding="utf-8"))
        events = value.get("events") if isinstance(value, dict) else None
        if not isinstance(events, list):
            raise SystemExit("events file has no events array")
        tick = iter(range(now_epoch, now_epoch + 10000)).__next__
        result = publish_reply_events(
            events=events,
            outbox=outbox,
            route=route,
            transport=transport,
            now=tick,
            agent_feed_path=args.gig_dir / "report-envelopes.jsonl",
        )
    elif args.command == "reply-wake":
        if args.events is None:
            raise SystemExit("--events is required for reply-wake")
        state = json.loads(args.events.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise SystemExit("wake file is not an object")
        result = publish_reply_wake(
            state=state,
            outbox=outbox,
            route=route,
            transport=transport,
            now_epoch=now_epoch,
        )
    elif args.command == "reply-dlq":
        if args.events is None:
            raise SystemExit("--events is required for reply-dlq")
        value = json.loads(args.events.read_text(encoding="utf-8"))
        entries = value.get("dlq_events") if isinstance(value, dict) else None
        if not isinstance(entries, list):
            raise SystemExit("events file has no dlq_events array")
        result = publish_reply_dlq_alerts(
            events=entries,
            outbox=outbox, route=route, transport=transport, now_epoch=now_epoch,
        )
    elif args.command == "pass":
        envelope = pass_envelope(
            gig_dir=args.gig_dir,
            usage_ledger=DEFAULT_USAGE_LEDGER,
        )
        pair = pass_message(
            gig_dir=args.gig_dir,
            usage_ledger=DEFAULT_USAGE_LEDGER,
            route=route,
            envelope=envelope,
        )
        if pair is None:
            print(json.dumps({"sent": 0, "delivery_unknown": 0}, separators=(",", ":")))
            return 0
        key, message = pair
        report_envelope.append_agent_feed(
            args.gig_dir / "report-envelopes.jsonl",
            envelope,
        )
        try:
            result = _dispatch_message(
                outbox=outbox, event_key=key, kind="pass", message=message,
                transport=transport, now_epoch=now_epoch,
            )
        except TelegramOutboxError:
            # Same pass already reported with an earlier snapshot of the
            # usage ledger; never send a second message for one pass.
            print(json.dumps({"sent": 0, "delivery_unknown": 0}, separators=(",", ":")))
            return 0
    elif args.command == "hourly":
        moment = datetime.now(timezone.utc)
        message = hourly_message(
            connector_database=args.connector_database,
            telegram_outbox=outbox,
            route=route,
            now=moment,
            gig_dir=args.gig_dir,
        )
        key = f"gig:telegram:hourly:v1:{moment.astimezone(JST):%Y%m%d%H}"
        result = _dispatch_message(
            outbox=outbox, event_key=key, kind="hourly", message=message,
            transport=transport, now_epoch=now_epoch,
        )
    elif args.command == "daily":
        moment = datetime.now(timezone.utc)
        envelope = daily_envelope(
            gig_dir=args.gig_dir,
            connector_database=args.connector_database,
            telegram_outbox=outbox,
            now=moment,
        )
        report_envelope.append_agent_feed(
            args.gig_dir / "report-envelopes.jsonl",
            envelope,
        )
        message = envelope["data"]["human_message_ja"]
        key = f"gig:telegram:daily:v2:{moment.astimezone(JST):%Y%m%d}"
        try:
            result = _dispatch_message(
                outbox=outbox, event_key=key, kind="daily", message=message,
                transport=transport, now_epoch=now_epoch,
            )
        except TelegramOutboxError:
            # Today's report already went out (e.g. a post-repair verification
            # fire before the scheduled wake). At-most-once per day: never send
            # a second daily message, and never crash the scheduled wake.
            print(json.dumps({"sent": 0, "delivery_unknown": 0}, separators=(",", ":")))
            return 0
    elif args.command == "weekly":
        moment = datetime.now(timezone.utc)
        envelope = weekly_envelope(
            gig_dir=args.gig_dir,
            telegram_outbox=outbox,
            now=moment,
        )
        report_envelope.append_agent_feed(
            args.gig_dir / "report-envelopes.jsonl",
            envelope,
        )
        message = envelope["data"]["human_message_ja"]
        result = _dispatch_message(
            outbox=outbox,
            event_key=f"gig:telegram:weekly:v3:{envelope['data']['trace_id']}",
            kind="weekly",
            message=message, transport=transport, now_epoch=now_epoch,
        )
    else:
        tick = iter(range(now_epoch, now_epoch + 10000)).__next__
        result = publish_reply_events(
            events=[], outbox=outbox, route=route, transport=transport, now=tick,
        )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 2 if result["delivery_unknown"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
