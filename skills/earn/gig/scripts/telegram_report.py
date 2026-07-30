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
import listing_ledger  # noqa: E402  -- the single source of truth for listing counts
import paid_progress_ledger  # noqa: E402  -- buyer-visible progress on paid contracts
import report_envelope  # noqa: E402  -- canonical human/agent report snapshot
from gig_paths import RUNNER_DIR  # noqa: E402


JST = timezone(timedelta(hours=9))
DEFAULT_USAGE_LEDGER = (
    Path.home() / ".local/state/life-manager/telemetry/agent-usage.jsonl"
)


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from telegram_outbox import TelegramOutbox, TelegramOutboxError, dispatch_one
except ModuleNotFoundError:
    _outbox_module = _load_local("telegram_outbox")
    TelegramOutbox = _outbox_module.TelegramOutbox
    TelegramOutboxError = _outbox_module.TelegramOutboxError
    dispatch_one = _outbox_module.dispatch_one


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


def publish_barren_alerts(
    *,
    alerts: list[dict[str, Any]],
    outbox: TelegramOutbox,
    route: str,
    transport: Callable[[str], str],
    now_epoch: int,
) -> dict[str, int]:
    """Alert once per barren streak that a live lane has stopped producing.

    The event key is anchored to the streak's START, not to the pass or to the
    streak length, so the hook can run on every pass (its only call site) while a
    lane stays silent without ever re-sending. A lane that recovers and then goes
    barren again opens a new anchor and is therefore allowed to alert again --
    the 4.5-day silence this exists to catch must never be dedupe'd away.
    """
    summary = {"sent": 0, "delivery_unknown": 0}
    if not alerts:
        return summary
    for alert in alerts:
        lane = str(alert["lane"])
        anchor = int(float(alert["streak_started_at"]))
        label = str(alert.get("label", lane))
        # The message must stay byte-identical for the whole streak: the outbox
        # rejects a re-enqueue of the same key with a different payload, and the
        # streak COUNT keeps growing while the lane stays silent. So the text is
        # anchored to when the silence began, not to how long it has run.
        outbox.enqueue(
            event_key=f"gig:telegram:lane-barren:v1:{lane}:{anchor}",
            kind="lane_barren",
            message=(
                f"[{route}] 沈黙警告: {label}({lane}) が3回以上連続で実作業ゼロ。"
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
) -> str:
    stats = _connector_stats(connector_database)
    telegram_unknown = telegram_outbox.counts().get("delivery_unknown", 0)
    stamp = now.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")
    return "\n".join((
        f"⏱ gig毎時SLA {stamp}",
        f"verified={stats['replied']} / pending={stats['pending']} / reconcile={stats['reconcile_pending']}",
        f"P1 breach={stats['breach']} / Telegram未確定={telegram_unknown}",
        f"route={route}",
    ))


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
    try:
        search_objective_value = json.loads(
            (Path(gig_dir) / "b2-search-objective.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        search_objective_value = None
    search_objective = (
        search_objective_value
        if isinstance(search_objective_value, dict)
        else None
    )
    return report_envelope.build_pass_envelope(
        pass_row=row,
        applications=_jsonl(Path(gig_dir) / "applied.jsonl"),
        usage_rows=_jsonl(Path(usage_ledger)),
        observed_at=observed_at,
        lane_events=lane_events,
        net_mrr_jpy=_verified_net_mrr(Path(gig_dir) / "work-events.jsonl"),
        search_objective=search_objective,
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
        if event_key in seen:
            continue
        envelope = report_envelope.build_work_event_envelope(
            work_event=event,
            observed_at=observed_at,
        )
        report_envelope.append_agent_feed(Path(agent_feed_path), envelope)
        outbox.enqueue(
            event_key=f"gig:telegram:work-event:v1:{event_key}",
            kind=str(event["kind"]),
            message=report_envelope.render_human_ja(envelope),
            created_at=observed_epoch,
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
    enqueued = 0
    for event in events:
        event_key = str(event["event_key"])
        if event_key in seen:
            continue
        envelope = report_envelope.build_work_event_envelope(
            work_event=event,
            observed_at=observed_at,
        )
        report_envelope.append_agent_feed(Path(agent_feed_path), envelope)
        outbox.enqueue(
            event_key=f"gig:telegram:instant-work-event:v1:{event_key}",
            kind=str(event["kind"]),
            message=report_envelope.render_human_ja(envelope),
            created_at=observed_epoch,
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
    return {**dispatched, "enqueued": enqueued}


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
) -> tuple[list[str], list[str]]:
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
    return lines, sorted(missing)


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
    lane_lines, missing = _four_lane_attribution(
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


def daily_envelope(
    *,
    gig_dir: Path,
    connector_database: Path,
    telegram_outbox: TelegramOutbox,
    now: datetime,
    lane_database: Path | None = None,
    evidence_root: Path | None = None,
    usage_ledger: Path = DEFAULT_USAGE_LEDGER,
) -> dict[str, Any]:
    """Build the daily human/agent report from one normalized snapshot."""
    day_start, day_end = listing_ledger.jst_day_bounds_for(now)
    metrics = _weekly_metrics(
        gig_dir=Path(gig_dir),
        usage_ledger=Path(usage_ledger),
        start=day_start,
        end=day_end,
    )
    _, missing = _four_lane_attribution(
        lane_database=lane_database or (Path(gig_dir) / "lane-actions.sqlite3"),
        evidence_root=evidence_root or (Path(gig_dir) / "evidence"),
        usage_ledger=Path(usage_ledger),
        earnings_path=Path(gig_dir) / "earnings.jsonl",
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
    }
    return report_envelope.build_period_envelope(
        report_type="daily",
        period_id=local.strftime("%Y%m%d"),
        snapshot=snapshot,
        occurred_at=now,
    )


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
        "model_cost_usd": current["model_cost"],
    }
    return report_envelope.build_period_envelope(
        report_type="weekly",
        period_id=start_day.replace("-", ""),
        snapshot=snapshot,
        occurred_at=now,
    )


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
        completed = self.run(
            [
                str(self.executable), "message", "send",
                "--channel", "telegram", "--target", self.target,
                "--message", message, "--json",
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Telegram transport failed rc={completed.returncode}")
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
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
            "target": self.target,
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
) -> dict[str, int]:
    outbox.enqueue(event_key=event_key, kind=kind, message=message, created_at=now_epoch)
    tick = iter(range(now_epoch + 1, now_epoch + 1000)).__next__
    return publish_reply_events(events=[], outbox=outbox, route="", transport=transport, now=tick)


def main() -> int:
    home = Path.home()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "reply", "pass", "hourly", "daily", "weekly", "flush",
            "lane-barren", "application-recovery", "work-events",
            "instant-work-events",
        ),
    )
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
    args = parser.parse_args()
    if not args.target:
        parser.error("--target or GIG_REPORT_CHAT is required")
    outbox = TelegramOutbox(args.telegram_database)
    now_epoch = int(time.time())
    outbox.recover_expired(now=now_epoch)
    outbox.reconcile_receipts(
        receipt_dir=args.gig_dir / "telegram-delivery-receipts",
        target=args.target,
        now=now_epoch,
    )
    route = composition_route(args.runner_config)
    transport = OpenClawTelegramTransport(
        target=args.target,
        executable=args.openclaw,
        receipt_dir=args.gig_dir / "telegram-delivery-receipts",
    )
    if args.command == "instant-work-events":
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
        result = _dispatch_message(
            outbox=outbox, event_key=key, kind="daily", message=message,
            transport=transport, now_epoch=now_epoch,
        )
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
            event_key=f"gig:telegram:weekly:v2:{envelope['data']['trace_id']}",
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
