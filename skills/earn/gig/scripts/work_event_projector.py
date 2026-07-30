#!/usr/bin/env python3
"""Project durable Gig ground truth into idempotent canonical WorkEvents."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


JST = timezone(timedelta(hours=9))
SETTLED_STATES = {"検収", "支払", "検収完了", "completed", "paid"}
LANES = {
    "B0": "listing",
    "list": "listing",
    "listing": "listing",
    "B1": "reply",
    "reply": "reply",
    "B2": "application",
    "apply": "application",
    "application": "application",
    "PAID_WORK": "delivery",
    "PAID_QUEUE_DELIVERY": "delivery",
    "fulfill": "delivery",
    "delivery": "delivery",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _iso(value: Any, *, local_naive: bool = False) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromtimestamp(float(text), timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            moment = datetime.strptime(text, "%Y/%m/%d %H:%M")
        except ValueError:
            return None
        local_naive = True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=JST if local_naive else timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def _read_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for raw in lines:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _contract_events(snapshot: dict[str, Any] | None) -> Iterable[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return
    occurred_at = _iso(snapshot.get("captured_at"))
    orders = snapshot.get("orders")
    if occurred_at is None or not isinstance(orders, list):
        return
    for row in orders:
        if not isinstance(row, dict):
            continue
        contract_confirmed = (
            row.get("status") == "paid"
            or "取引中" in _clean(row.get("talkroom_state"))
        )
        if not contract_confirmed:
            continue
        talkroom_id = _clean(row.get("talkroom_id"))
        if not talkroom_id:
            continue
        title = _clean(row.get("title")) or "新しい仕事"
        yield {
            "event_key": f"gig:contract:coconala:{talkroom_id}",
            "kind": "contract",
            "entity_id": talkroom_id,
            "occurred_at": occurred_at,
            "state": "confirmed",
            "action": "新しい契約を確認",
            "result": f"「{title}」の契約成立を確認しました",
            "next_action": "要件を保存し、制作と品質確認を開始します",
            "evidence": ["marketplace_order"],
            "attributes": {
                "request_id": row.get("request_id"),
                "title": title,
                "price_jpy": row.get("price_jpy"),
                "delivery_date": row.get("delivery_date"),
                "recurring_active": row.get("recurring_active") is True,
                "billing_period": row.get("billing_period"),
                "monthly_net_jpy": row.get("monthly_net_jpy"),
                "platform": "coconala",
            },
        }


def _payment_events(rows: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for row in rows:
        if (
            row.get("status") not in SETTLED_STATES
            or not row.get("evidence")
            or not _clean(row.get("idem_key"))
        ):
            continue
        talkroom_id = _clean(row.get("talkroom_id") or row.get("requestId"))
        occurred_at = _iso(row.get("ts"), local_naive=True)
        if not talkroom_id or occurred_at is None:
            continue
        try:
            net_jpy = float(str(row.get("jpy") or "0").replace(",", ""))
        except ValueError:
            continue
        if net_jpy <= 0:
            continue
        title = _clean(row.get("title")) or "完了した仕事"
        yield {
            "event_key": f"gig:payment:{_clean(row['idem_key'])}",
            "kind": "payment",
            "entity_id": talkroom_id,
            "occurred_at": occurred_at,
            "state": "confirmed",
            "action": "検収済み売上を確認",
            "result": f"「{title}」の入金 {net_jpy:.0f}円を確認しました",
            "next_action": "この実績を案件選定と価格改善へ反映します",
            "evidence": ["marketplace_revenue"],
            "attributes": {
                "title": title,
                "net_jpy": int(net_jpy) if net_jpy.is_integer() else net_jpy,
                "net_of_fee": row.get("net_of_fee") is True,
                "payout_requested": row.get("payout_requested") is True,
                "platform": "coconala",
            },
        }


def _incident_events(rows: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for row in rows:
        pass_id = _clean(row.get("pass_id"))
        reason = _clean(row.get("reason"))
        occurred_at = _iso(row.get("ts"))
        if row.get("status") != "failed" or not pass_id or not reason or occurred_at is None:
            continue
        failed_step = _clean(row.get("failed_step"))
        affected_lane = LANES.get(failed_step)
        yield {
            "event_key": f"gig:incident:{pass_id}:{reason}",
            "kind": "incident",
            "entity_id": pass_id,
            "occurred_at": occurred_at,
            "state": "detected",
            "action": "作業停止の原因を記録",
            "result": "予定した作業を最後まで確認できない問題を検出しました",
            "next_action": "原因を自動修復し、同じ作業を安全に再実行します",
            "evidence": ["pass_failure"],
            "attributes": {
                "failure_class": reason,
                "failed_step": failed_step or None,
                "affected_lane": affected_lane,
                "duplicate_side_effect_observed": False,
            },
        }


def _recovery_events(rows: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for row in rows:
        occurred_at = _iso(row.get("ts"))
        if (
            occurred_at is not None
            and row.get("kind") == "self_heal_recovery"
            and row.get("state") == "verified"
            and isinstance(row.get("incident_id"), int)
            and isinstance(row.get("fencing_token"), int)
            and _clean(row.get("fingerprint"))
            and isinstance(row.get("verification"), dict)
            and row["verification"].get("fresh_fingerprint_present") is False
        ):
            incident_id = int(row["incident_id"])
            fencing_token = int(row["fencing_token"])
            fingerprint = _clean(row["fingerprint"])
            yield {
                "event_key": (
                    f"gig:recovery:incident:{incident_id}:{fencing_token}"
                ),
                "kind": "recovery",
                "entity_id": str(incident_id),
                "occurred_at": occurred_at,
                "state": "verified",
                "action": "自動運転の問題を修復して再確認",
                "result": "修復後の再確認に成功し、通常の自動運転へ戻りました",
                "next_action": "次の定時サイクルでも同じ状態を確認します",
                "evidence": ["fenced_repair", "fresh_slo_verification"],
                "attributes": {
                    "failure_fingerprint": fingerprint,
                    "repair_class": _clean(row.get("repair_class")),
                    "incident_id": incident_id,
                    "fencing_token": fencing_token,
                    "duplicate_side_effect_observed": False,
                },
            }
            continue
        changes = row.get("changed")
        if occurred_at is None or not isinstance(changes, list):
            continue
        lane_rows = row.get("lanes")
        previous_by_lane = {
            _clean(lane_row.get("lane")): _clean(
                lane_row.get("prev_alert_state")
            )
            for lane_row in lane_rows
            if isinstance(lane_rows, list) and isinstance(lane_row, dict)
        } if isinstance(lane_rows, list) else {}
        for change in changes:
            raw_lane = _clean(change.get("lane")) if isinstance(change, dict) else ""
            previous = (
                _clean(change.get("from"))
                if isinstance(change, dict)
                else ""
            ) or previous_by_lane.get(raw_lane, "")
            if (
                not isinstance(change, dict)
                or previous != "down"
                or change.get("to") != "ok"
            ):
                continue
            lane = LANES.get(raw_lane)
            if lane is None:
                continue
            yield {
                "event_key": f"gig:recovery:{lane}:{occurred_at}",
                "kind": "recovery",
                "entity_id": lane,
                "occurred_at": occurred_at,
                "state": "verified",
                "action": "停止していた仕事を再確認",
                "result": "修復後の確認に成功し、通常の自動運転へ戻りました",
                "next_action": "次の定時サイクルでも同じ仕事を確認します",
                "evidence": ["lane_health_transition"],
                "attributes": {
                    "recovered_lane": lane,
                    "from": "down",
                    "to": "ok",
                },
            }


def _application_events(
    rows: Iterable[dict[str, Any]],
    pass_id: str | None,
) -> Iterable[dict[str, Any]]:
    if not pass_id:
        return
    for row in rows:
        request_id = _clean(row.get("requestId") or row.get("request_id"))
        occurred_at = _iso(row.get("ts"))
        if (
            _clean(row.get("pass_id")) != pass_id
            or row.get("status") != "applied"
            or row.get("submit_verified") is not True
            or row.get("applied_page_verified") is not True
            or "action" in row
            or not request_id
            or occurred_at is None
        ):
            continue
        bucket = (
            "retainer" if _clean(row.get("bucket")) == "retainer" else "single"
        )
        title = _clean(row.get("title")) or "案件名を取得できませんでした"
        yield {
            "event_key": f"gig:application:{pass_id}:{request_id}",
            "kind": "application",
            "entity_id": request_id,
            "occurred_at": occurred_at,
            "state": "verified",
            "action": "継続案件へ応募" if bucket == "retainer" else "単発案件へ応募",
            "result": "応募を送信し、応募履歴と台帳への記録を確認しました",
            "next_action": "返信または契約の到着を自動で確認します",
            "evidence": [
                "submission",
                "marketplace_readback",
                "canonical_ledger",
            ],
            "attributes": {
                "bucket": bucket,
                "title": title,
                "url": _clean(row.get("url")),
                "category": row.get("category"),
                "price_jpy": row.get("price_jpy"),
                "platform": "coconala",
            },
        }


def _paid_interaction_events(
    rows: Iterable[dict[str, Any]],
    pass_id: str | None,
) -> Iterable[dict[str, Any]]:
    if not pass_id:
        return
    for row in rows:
        talkroom_id = _clean(row.get("talkroom_id") or row.get("requestId"))
        occurred_at = _iso(row.get("ts"))
        if (
            _clean(row.get("pass_id")) != pass_id
            or row.get("action") != "paid_progress"
            or row.get("buyer_visible") is not True
            or not talkroom_id
            or occurred_at is None
        ):
            continue
        interaction_mode = _clean(row.get("interaction_mode"))
        if interaction_mode == "answer":
            yield {
                "event_key": f"gig:reply:{pass_id}:{talkroom_id}",
                "kind": "reply",
                "entity_id": talkroom_id,
                "occurred_at": occurred_at,
                "state": "replied",
                "action": "購入者の質問へ回答",
                "result": "購入者からの質問に回答し、購入者画面への表示を確認しました",
                "next_action": "購入者からの次の返信を自動で確認します",
                "evidence": ["buyer_visible_dom", "canonical_paid_progress"],
                "attributes": {
                    "interaction_mode": "answer",
                    "url": _clean(row.get("url")),
                    "platform": "coconala",
                },
            }
            continue
        artifact_version = _clean(row.get("artifact_version")) or "納品物"
        yield {
            "event_key": f"gig:delivery:{pass_id}:{talkroom_id}",
            "kind": "delivery",
            "entity_id": talkroom_id,
            "occurred_at": occurred_at,
            "state": "buyer_visible",
            "action": "納品内容を購入者へ送信",
            "result": f"{artifact_version}を購入者画面で確認できる状態にしました",
            "next_action": "購入者からの確認結果を自動で確認します",
            "evidence": ["buyer_visible_dom", "canonical_paid_progress"],
            "attributes": {
                "artifact_version": artifact_version,
                "buyer_visible": True,
                "url": _clean(row.get("url")),
                "platform": "coconala",
            },
        }


def _append_unique(
    output_path: Path,
    events: Iterable[dict[str, Any]],
) -> dict[str, int]:
    candidates = list(events)
    if not candidates:
        return {"appended": 0, "duplicate": 0}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        existing: set[str] = set()
        for raw in handle:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and _clean(row.get("event_key")):
                existing.add(_clean(row["event_key"]))
        appended = 0
        duplicate = 0
        handle.seek(0, os.SEEK_END)
        for event in candidates:
            event_key = _clean(event.get("event_key"))
            if event_key in existing:
                duplicate += 1
                continue
            handle.write(
                json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            existing.add(event_key)
            appended += 1
        if appended:
            handle.flush()
            os.fsync(handle.fileno())
    return {"appended": appended, "duplicate": duplicate}


def project(
    *,
    snapshot_path: Path | None,
    earnings_path: Path,
    failures_path: Path,
    audit_path: Path,
    applications_path: Path,
    paid_progress_path: Path,
    pass_id: str | None,
    output_path: Path,
) -> dict[str, int]:
    events = [
        *_contract_events(_read_object(snapshot_path)),
        *_payment_events(_read_jsonl(earnings_path)),
        *_incident_events(_read_jsonl(failures_path)),
        *_recovery_events(_read_jsonl(audit_path)),
        *_application_events(_read_jsonl(applications_path), pass_id),
        *_paid_interaction_events(_read_jsonl(paid_progress_path), pass_id),
    ]
    return _append_unique(Path(output_path), events)


def _latest_snapshot(gig_dir: Path) -> Path | None:
    finished = [
        *_read_jsonl(gig_dir / "pass-report.jsonl"),
        *_read_jsonl(gig_dir / "pass-failures.jsonl"),
    ]
    rows = [
        row
        for row in finished
        if isinstance(row.get("ts"), (int, float))
        and _clean(row.get("evidence_dir"))
    ]
    if not rows:
        return None
    for row in sorted(rows, key=lambda value: float(value["ts"]), reverse=True):
        snapshot = (
            Path(str(row["evidence_dir"])) / "marketplace-snapshot.json"
        )
        if snapshot.is_file():
            return snapshot
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    home = Path.home()
    parser.add_argument("--gig-dir", type=Path, default=home / "gig")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--earnings", type=Path, default=home / "gig/earnings.jsonl"
    )
    parser.add_argument(
        "--failures", type=Path, default=home / "gig/pass-failures.jsonl"
    )
    parser.add_argument("--audit", type=Path, default=home / "gig/audit.jsonl")
    parser.add_argument(
        "--applications", type=Path, default=home / "gig/applied.jsonl"
    )
    parser.add_argument(
        "--paid-progress", type=Path, default=home / "gig/paid-progress.jsonl"
    )
    parser.add_argument("--pass-id")
    parser.add_argument(
        "--output", type=Path, default=home / "gig/work-events.jsonl"
    )
    args = parser.parse_args()
    result = project(
        snapshot_path=args.snapshot or _latest_snapshot(args.gig_dir),
        earnings_path=args.earnings,
        failures_path=args.failures,
        audit_path=args.audit,
        applications_path=args.applications,
        paid_progress_path=args.paid_progress,
        pass_id=_clean(args.pass_id) or None,
        output_path=args.output,
    )
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
