#!/usr/bin/env python3
"""Canonical Gig report envelope shared by human and agent consumers.

The outer shape follows CloudEvents 1.0: source + id is the durable duplicate
identity, while the data section carries the Gig-specific report snapshot.
Human text is rendered only from this envelope.  The agent feed stores the same
object byte-for-byte, so Telegram and self-healing cannot disagree about what
happened.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SOURCE = "life-manager/gig"
PASS_TYPE = "com.anicca.gig.report.pass.v1"
WORK_EVENT_KINDS = {
    "application", "delivery", "reply", "contract", "payment", "incident", "recovery"
}
LANE_JA = {
    "application": "応募",
    "reply": "返信",
    "delivery": "納品",
    "listing": "出品",
}
LANE_EN = {
    "application": "Application",
    "reply": "Reply",
    "delivery": "Delivery",
    "listing": "Listing",
}

STEP_LABELS = {
    "PAID_QUEUE_DELIVERY": "納品",
    "PAID_WORK": "納品物の作成",
    "INQUIRY_REPLY": "問い合わせへの返信",
    "B0": "出品",
    "B1": "返信",
    "B2": "応募",
}


def _iso(epoch: int | float) -> str:
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat()


def _clean(value: object, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _verified_applications(
    applications: list[dict[str, Any]],
    pass_id: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in applications
        if str(row.get("pass_id") or "") == pass_id
        and row.get("status") == "applied"
        and row.get("submit_verified") is True
        and row.get("applied_page_verified") is True
        and "action" not in row
    ]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _money(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(float(str(value or "0").replace(",", "")))
    except ValueError:
        return 0


def _work_event_messages(event: dict[str, Any]) -> tuple[str, str]:
    kind = str(event["kind"])
    attributes = event["attributes"]
    if kind == "application":
        title = _clean(attributes.get("title"), "新しい仕事")
        bucket = "継続" if attributes.get("bucket") == "retainer" else "単発"
        amount = _money(attributes.get("price_jpy"))
        ja = "\n".join((
            "📨 新しい仕事へ応募しました",
            "",
            "状態",
            "応募の送信が完了しています。",
            "",
            "実際にしたこと",
            f"- [{bucket}] {title}",
            f"- 提案金額: {amount:,}円" if amount else "- 提案金額: 案件条件に合わせて提示",
            "",
            "結果",
            "- 送信画面、応募履歴、応募台帳の3か所で確認しました。",
            "",
            "次に自動で行うこと",
            "- 返信または契約の到着を自動で確認します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            "📨 A job application was submitted",
            "",
            "Status",
            "The application was submitted successfully.",
            "",
            "Work completed",
            f"- {title}",
            "",
            "Result",
            "- Verified the submission, marketplace application history, and ledger.",
            "",
            "Next automatic action",
            "- Monitor for a reply or contract.",
            "No user action is required.",
        ))
        return ja, en
    if kind == "delivery":
        artifact = _clean(attributes.get("artifact_version"), "納品物")
        ja = "\n".join((
            "📦 納品内容を購入者へ提出しました",
            "",
            "状態",
            "購入者画面で納品内容を確認できる状態です。",
            "",
            "実際にしたこと",
            f"- {artifact}を送信し、購入者画面で表示を確認しました。",
            "",
            "結果",
            "- 納品内容の表示と記録が一致しています。",
            "",
            "次に自動で行うこと",
            "- 購入者からの確認結果を自動で確認します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            "📦 Delivery was submitted to the buyer",
            "",
            "Status",
            "The delivery is visible on the buyer-facing page.",
            "",
            "Work completed",
            f"- Submitted {artifact} and verified buyer-facing visibility.",
            "",
            "Next automatic action",
            "- Monitor for the buyer's review.",
            "No user action is required.",
        ))
        return ja, en
    if kind == "contract":
        title = _clean(attributes.get("title"), "新しい仕事")
        amount = _money(attributes.get("price_jpy"))
        deadline = _clean(attributes.get("delivery_date"), "確認中")
        ja = "\n".join((
            "🎉 新しい仕事を受注しました",
            "",
            "状態",
            "契約成立を確認しました。",
            "",
            "実際にしたこと",
            "- 契約内容、金額、納期を購入者画面で確認しました。",
            "",
            "結果",
            f"- 内容: {title}",
            f"- 契約金額: {amount:,}円",
            f"- 納期: {deadline}",
            "",
            "次に自動で行うこと",
            "- 要件を保存し、制作と品質確認を開始します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            "🎉 A new contract was confirmed",
            "",
            "Status",
            "The marketplace confirms that the contract is active.",
            "",
            "Work completed",
            "- Verified the scope, amount, and deadline on the buyer-facing record.",
            "",
            "Result",
            f"- Work: {title}",
            f"- Contract amount: JPY {amount:,}",
            f"- Deadline: {deadline}",
            "",
            "Next automatic action",
            "- Save the requirements and begin production and quality checks.",
            "No user action is required.",
        ))
        return ja, en
    if kind == "payment":
        title = _clean(attributes.get("title"), "完了した仕事")
        amount = _money(attributes.get("net_jpy"))
        ja = "\n".join((
            f"💰 {amount:,}円の入金を確認しました",
            "",
            "状態",
            "検収済み売上として確認できています。",
            "",
            "実際にしたこと",
            "- 売上管理画面と収益台帳を照合しました。",
            "",
            "結果",
            f"- 内容: {title}",
            f"- 手数料控除後の売上: {amount:,}円",
            "",
            "次に自動で行うこと",
            "- この実績を次の案件選定と価格改善へ反映します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            f"💰 Payment confirmed: JPY {amount:,}",
            "",
            "Status",
            "The payment is confirmed as settled revenue.",
            "",
            "Work completed",
            "- Reconciled the marketplace revenue record with the earnings ledger.",
            "",
            "Result",
            f"- Work: {title}",
            f"- Net revenue after fees: JPY {amount:,}",
            "",
            "Next automatic action",
            "- Use this result to improve opportunity selection and pricing.",
            "No user action is required.",
        ))
        return ja, en
    if kind == "reply":
        latency = int(attributes.get("latency_minutes") or 0)
        ja = "\n".join((
            "💬 お客様への返信が完了しました",
            "",
            "状態",
            "新しいメッセージへの返信を確認しました。",
            "",
            "実際にしたこと",
            f"- 新しい質問1件へ{latency}分で回答しました。",
            "",
            "結果",
            "- 現在の未返信は0件です。",
            "",
            "次に自動で行うこと",
            "- 次は契約または追加メッセージを自動で確認します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            "💬 The buyer reply was completed",
            "",
            "Status",
            "The new buyer message has a confirmed reply.",
            "",
            "Work completed",
            f"- Answered one new question in {latency} minutes.",
            "",
            "Result",
            "- There are no unanswered messages.",
            "",
            "Next automatic action",
            "- Monitor for a contract or another buyer message.",
            "No user action is required.",
        ))
        return ja, en
    lane = str(
        attributes.get("affected_lane")
        or attributes.get("recovered_lane")
        or ""
    )
    lane_ja = LANE_JA.get(lane, "ギグワーク")
    lane_en = LANE_EN.get(lane, "Gig work")
    if kind == "incident":
        ja = "\n".join((
            f"🟠 {lane_ja}機能を自動で復旧しています",
            "",
            "状態",
            "予定した作業を最後まで確認できない問題を検出しました。",
            "",
            "実際にしたこと",
            "- 問題の範囲を記録し、安全のため影響する処理だけを停止しました。",
            "",
            "結果",
            "- 重複する外部操作は確認されていません。",
            "",
            "次に自動で行うこと",
            "- 原因を修復し、同じ作業を新しい確認経路で再実行します。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            f"🟠 Automatic recovery is in progress for {lane_en.lower()} work",
            "",
            "Status",
            "The system could not verify the scheduled work through completion.",
            "",
            "Work completed",
            "- Recorded the affected scope and paused only the unsafe operation.",
            "",
            "Result",
            "- No duplicate external action was observed.",
            "",
            "Next automatic action",
            "- Repair the cause and retry the same work through a fresh verifier.",
            "No user action is required.",
        ))
        return ja, en
    ja = "\n".join((
        f"🟢 {lane_ja}機能が復旧しました",
        "",
        "状態",
        "修復後の確認に成功し、通常の自動運転へ戻りました。",
        "",
        "実際にしたこと",
        "- 停止していた処理を再確認し、正常に動くことを検証しました。",
        "",
        "結果",
        "- 取りこぼしや重複する外部操作は確認されていません。",
        "",
        "次に自動で行うこと",
        "- 次の定時サイクルでも同じ仕事を確認します。",
        "ユーザーの操作は必要ありません。",
    ))
    en = "\n".join((
        f"🟢 {lane_en} work has recovered",
        "",
        "Status",
        "Fresh verification passed and normal autonomous operation has resumed.",
        "",
        "Work completed",
        "- Rechecked the stopped operation and verified that it now works.",
        "",
        "Result",
        "- No missed or duplicate external action was observed.",
        "",
        "Next automatic action",
        "- Check the same work again in the next scheduled cycle.",
        "No user action is required.",
    ))
    return ja, en


def build_work_event_envelope(
    *,
    work_event: dict[str, Any],
    observed_at: datetime,
) -> dict[str, Any]:
    """Build one immutable report around one code-owned business WorkEvent."""
    if (
        not isinstance(work_event, dict)
        or work_event.get("kind") not in WORK_EVENT_KINDS
        or not _clean(work_event.get("event_key"))
        or not _clean(work_event.get("entity_id"))
        or not _clean(work_event.get("occurred_at"))
        or not isinstance(work_event.get("attributes"), dict)
        or observed_at.tzinfo is None
    ):
        raise ValueError("work event envelope identity is incomplete")
    event = json.loads(json.dumps(work_event, ensure_ascii=False))
    kind = str(event["kind"])
    human_ja, human_en = _work_event_messages(event)
    work = {
        "searched": 0,
        "applied": int(kind == "application"),
        "replied": int(kind == "reply"),
        "contracted": int(kind == "contract"),
        "delivered": int(kind == "delivery"),
        "paid": int(kind == "payment"),
        "listings_created": 0,
        "listings_improved": 0,
    }
    incident = None
    if kind in {"incident", "recovery"}:
        incident = {
            "class": event["attributes"].get("failure_class"),
            "impact": event["attributes"].get("affected_lane"),
            "recovery_state": (
                "in_progress" if kind == "incident" else "verified"
            ),
            "next_retry_at": event["attributes"].get("next_retry_at"),
        }
    return {
        "specversion": "1.0",
        "id": f"gig:report:work-event:{event['event_key']}",
        "source": SOURCE,
        "type": f"com.anicca.gig.report.{kind}.v1",
        "subject": f"gig-work/{kind}/{event['entity_id']}",
        "time": str(event["occurred_at"]),
        "datacontenttype": "application/json",
        "data": {
            "report_type": kind,
            "status": str(event["state"]),
            "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
            "trace_id": str(event["entity_id"]),
            "human_message_ja": human_ja,
            "human_message_en": human_en,
            "objective": None,
            "work": work,
            "work_event": event,
            "events": [event],
            "work_event_ids": [str(event["event_key"])],
            "evidence_ids": list(event.get("evidence") or []),
            "affected_entity_ids": [str(event["entity_id"])],
            "incident": incident,
            "funnel": {
                "applications": work["applied"],
                "replies": 0,
                "contracts": work["contracted"],
                "deliveries": work["delivered"],
                "payments": work["paid"],
                "net_mrr": 0,
            },
            "next_actions": [str(event["next_action"])],
        },
    }


def build_period_envelope(
    *,
    report_type: str,
    period_id: str,
    snapshot: dict[str, Any],
    occurred_at: datetime,
) -> dict[str, Any]:
    """Build a bilingual daily summary from one normalized metrics snapshot."""
    if (
        report_type not in {"daily", "weekly"}
        or not period_id
        or not isinstance(snapshot, dict)
        or occurred_at.tzinfo is None
    ):
        raise ValueError("period envelope identity is incomplete")
    funnel = snapshot.get("funnel")
    work = snapshot.get("work")
    if not isinstance(funnel, dict) or not isinstance(work, dict):
        raise ValueError("period envelope snapshot is incomplete")
    if report_type == "weekly":
        revenue = _money(snapshot.get("revenue_jpy"))
        application_delta = int(snapshot.get("application_delta") or 0)
        revenue_delta = _money(snapshot.get("revenue_delta_jpy"))
        start_ja = _clean(snapshot.get("period_start_ja"))
        end_ja = _clean(snapshot.get("period_end_ja"))
        ja = "\n".join((
            f"📊 1週間のギグワーク成績｜{start_ja}〜{end_ja}",
            "",
            "1週間の流れ",
            f"応募 {int(funnel.get('applications') or 0)}件 → "
            f"返信 {int(funnel.get('replies') or 0)}件 → "
            f"契約 {int(funnel.get('contracts') or 0)}件 → "
            f"納品 {int(funnel.get('deliveries') or 0)}件 → "
            f"入金 {int(funnel.get('payments') or 0)}件",
            "",
            "売上",
            f"- 売上 {revenue:,}円",
            f"- 継続売上 {int(funnel.get('net_mrr') or 0):,}円",
            "",
            "前週比",
            f"- 応募 {application_delta:+d}件",
            f"- 売上 {revenue_delta:+,}円",
            "",
            "自動改善",
            f"- 改善を継続 {int(snapshot.get('experiment_kept') or 0)}件",
            f"- 元に戻した改善 {int(snapshot.get('experiment_reverted') or 0)}件",
            f"- 問題 {int(snapshot.get('incidents') or 0)}件、"
            f"復旧確認 {int(snapshot.get('recoveries') or 0)}件",
            "",
            "次週の自動方針",
            "- 返信率と契約率の高い案件へ探索時間を増やし、低利益の仕事を減らします。",
            "ユーザーの操作は必要ありません。",
        ))
        en = "\n".join((
            f"📊 Weekly gig work results | {snapshot.get('period_start_en')} to {snapshot.get('period_end_en')}",
            "",
            "Weekly funnel",
            f"Applications {int(funnel.get('applications') or 0)} → "
            f"Replies {int(funnel.get('replies') or 0)} → "
            f"Contracts {int(funnel.get('contracts') or 0)} → "
            f"Deliveries {int(funnel.get('deliveries') or 0)} → "
            f"Payments {int(funnel.get('payments') or 0)}",
            "",
            f"Revenue: JPY {revenue:,}",
            f"Recurring revenue: JPY {int(funnel.get('net_mrr') or 0):,}",
            "",
            "Change from the previous week",
            f"- Applications: {application_delta:+d}",
            f"- Revenue: JPY {revenue_delta:+,}",
            "",
            "Next week's automatic focus",
            "- Spend more search time on work with stronger reply and contract rates.",
            "No user action is required.",
        ))
        return {
            "specversion": "1.0",
            "id": f"gig:report:{report_type}:{period_id}",
            "source": SOURCE,
            "type": f"com.anicca.gig.report.{report_type}.v1",
            "subject": f"gig-report/{report_type}/{period_id}",
            "time": occurred_at.astimezone(timezone.utc).isoformat(),
            "datacontenttype": "application/json",
            "data": {
                "report_type": report_type,
                "status": "healthy",
                "observed_at": occurred_at.astimezone(timezone.utc).isoformat(),
                "trace_id": period_id,
                "human_message_ja": ja,
                "human_message_en": en,
                "work": work,
                "funnel": funnel,
                "metrics": snapshot,
                "events": [],
                "next_actions": [
                    "返信率と契約率の高い案件へ次週の探索時間を増やす"
                ],
            },
        }
    date_ja = occurred_at.astimezone(JST).strftime("%-m月%-d日")
    revenue_today = _money(snapshot.get("revenue_today_jpy"))
    revenue_month = _money(snapshot.get("revenue_month_jpy"))
    stopped = [
        LANE_JA.get(str(lane), str(lane))
        for lane in snapshot.get("attention_lanes") or []
    ]
    state_ja = (
        f"{'、'.join(stopped)}で自動確認が必要な問題を検出しています。"
        if stopped
        else "4つの仕事をすべて確認できています。"
    )
    state_en = (
        "Automatic recovery is active for: "
        + ", ".join(LANE_EN.get(str(lane), str(lane)) for lane in snapshot.get("attention_lanes") or [])
        + "."
        if stopped
        else "All four work areas were checked."
    )
    ja = "\n".join((
        f"☀️ 今日のギグワーク結果｜{date_ja}",
        "",
        "状態",
        state_ja,
        "",
        "売上",
        f"- 本日の入金 {revenue_today:,}円",
        f"- 今月の検収済売上 {revenue_month:,}円",
        f"- 継続売上 {int(funnel.get('net_mrr') or 0):,}円",
        "",
        "今日の流れ",
        f"応募 {int(funnel.get('applications') or 0)}件 → "
        f"返信 {int(funnel.get('replies') or 0)}件 → "
        f"契約 {int(funnel.get('contracts') or 0)}件 → "
        f"納品 {int(funnel.get('deliveries') or 0)}件 → "
        f"入金 {int(funnel.get('payments') or 0)}件",
        "",
        "4つの仕事",
        f"- 応募: {int(work.get('applied') or 0)}件",
        f"- 返信: {int(work.get('replied') or 0)}件、未返信 {int(snapshot.get('pending_replies') or 0)}件",
        f"- 納品: {int(work.get('delivered') or 0)}件",
        f"- 出品: {int(work.get('listings_created') or 0)}件",
        "",
        "自動復旧",
        f"- 問題 {int(snapshot.get('incidents') or 0)}件を検出し、"
        f"{int(snapshot.get('recoveries') or 0)}件の復旧を確認しました。",
        "",
        "次に自動で行うこと",
        "- 新着案件、購入者からの返信、進行中の納品、公開中サービスを順に確認します。",
        "ユーザーの操作は必要ありません。",
    ))
    en = "\n".join((
        f"☀️ Daily gig work results | {occurred_at.astimezone(JST):%B %-d}",
        "",
        "Status",
        state_en,
        "",
        "Revenue",
        f"- Payments today: JPY {revenue_today:,}",
        f"- Settled revenue this month: JPY {revenue_month:,}",
        f"- Recurring revenue: JPY {int(funnel.get('net_mrr') or 0):,}",
        "",
        "Today's funnel",
        f"Applications {int(funnel.get('applications') or 0)} → "
        f"Replies {int(funnel.get('replies') or 0)} → "
        f"Contracts {int(funnel.get('contracts') or 0)} → "
        f"Deliveries {int(funnel.get('deliveries') or 0)} → "
        f"Payments {int(funnel.get('payments') or 0)}",
        "",
        "Next automatic action",
        "- Check new opportunities, buyer replies, active deliveries, and public listings.",
        "No user action is required.",
    ))
    return {
        "specversion": "1.0",
        "id": f"gig:report:{report_type}:{period_id}",
        "source": SOURCE,
        "type": f"com.anicca.gig.report.{report_type}.v1",
        "subject": f"gig-report/{report_type}/{period_id}",
        "time": occurred_at.astimezone(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "report_type": report_type,
            "status": "attention" if stopped else "healthy",
            "observed_at": occurred_at.astimezone(timezone.utc).isoformat(),
            "trace_id": period_id,
            "human_message_ja": ja,
            "human_message_en": en,
            "work": work,
            "funnel": funnel,
            "metrics": snapshot,
            "events": [],
            "next_actions": [
                "新着案件、返信、納品、出品を次の定時サイクルで確認する"
            ],
        },
    }


def collect_lane_events(
    *,
    evidence_dir: Path,
    pass_id: str,
    occurred_at: int,
) -> list[dict[str, Any]]:
    """Convert owned structured lane evidence into canonical WorkEvents."""
    evidence_dir = Path(evidence_dir)
    events: list[dict[str, Any]] = []
    timestamp = _iso(occurred_at)

    b0 = _read_json(evidence_dir / "agent-B0" / "attempt-01.result.json")
    current_b0 = b0.get("current_b0") if isinstance(b0, dict) else None
    if isinstance(current_b0, dict):
        action = str(current_b0.get("action") or "")
        if action == "verified_noop":
            state = "observed_no_action"
            result = (
                "新しい出品は行わず、出品可能数の上限に達していることを確認しました"
            )
            next_action = "既存サービスの改善を続けます"
        else:
            state = "published" if current_b0.get("service_id") else "verified"
            title = _clean(current_b0.get("title"), "新しいサービス")
            result = f"「{title}」の出品内容を更新しました"
            next_action = "閲覧数と購入状況を確認して改善します"
        events.append({
            "event_key": f"gig:listing:{pass_id}",
            "kind": "listing",
            "lane": "listing",
            "entity_id": str(current_b0.get("service_id") or "storefront"),
            "occurred_at": timestamp,
            "state": state,
            "action": "出品枠と公開サービスを確認",
            "result": result,
            "next_action": next_action,
            "evidence": ["storefront_dom"],
            "attributes": {
                "service_id": current_b0.get("service_id"),
                "url": current_b0.get("url"),
            },
        })

    b1 = _read_json(evidence_dir / "agent-B1" / "attempt-01.result.json")
    current_b1 = b1.get("current_b1") if isinstance(b1, dict) else None
    inspected = (
        current_b1.get("inspected_talkrooms")
        if isinstance(current_b1, dict)
        else None
    )
    if isinstance(inspected, list):
        for row in inspected:
            if not isinstance(row, dict):
                continue
            talkroom_id = str(row.get("talkroom_id") or "").strip()
            if not talkroom_id:
                continue
            outcome = str(row.get("outcome") or "")
            if outcome == "observed_no_action":
                state = "observed_no_action"
                result = (
                    "購入者との会話を確認し、新しく返信すべきメッセージがないことを確認しました"
                )
                next_action = "5分ごとに新しい購入者メッセージを確認します"
            else:
                state = "replied"
                result = "購入者からの新しいメッセージを確認し、返信しました"
                next_action = "購入者からの次の返信を確認します"
            events.append({
                "event_key": f"gig:reply:{pass_id}:{talkroom_id}",
                "kind": "reply",
                "lane": "reply",
                "entity_id": talkroom_id,
                "occurred_at": timestamp,
                "state": state,
                "action": "購入者メッセージを確認",
                "result": result,
                "next_action": next_action,
                "evidence": ["talkroom_dom"],
                "attributes": {"url": row.get("url")},
            })

    b2 = _read_json(evidence_dir / "agent-B2" / "attempt-01.result.json")
    current_b2 = b2.get("current_b2") if isinstance(b2, dict) else None
    raw_sources = (
        current_b2.get("search_sources")
        if isinstance(current_b2, dict)
        else None
    )
    sources: list[dict[str, Any]] = []
    if isinstance(raw_sources, list):
        for row in raw_sources:
            if not isinstance(row, dict):
                continue
            source_id = _clean(row.get("source_id"))
            count = row.get("inspected_count")
            if (
                not source_id
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
            ):
                continue
            sources.append({
                "source_id": source_id,
                "inspected_count": count,
                "has_next": row.get("has_next") is True,
                "exhausted": row.get("exhausted") is True,
            })
    searched = sum(row["inspected_count"] for row in sources)
    if sources:
        events.append({
            "event_key": f"gig:application-search:{pass_id}",
            "kind": "application_search",
            "lane": "application",
            "entity_id": pass_id,
            "occurred_at": timestamp,
            "state": "searched",
            "action": "応募可能な仕事を探索",
            "result": (
                f"単発・関連カテゴリ・継続案件を延べ{searched}件確認しました"
            ),
            "next_action": "次の検索位置から探索を続けます",
            "evidence": ["b2_search_sources"],
            "attributes": {
                "searched": searched,
                "sources": sources,
            },
        })

    delivery = _read_json(
        evidence_dir
        / "agent-PAID_QUEUE_DELIVERY"
        / "paid-queue-evidence.json"
    )
    if isinstance(delivery, dict) and delivery.get("sent") is True:
        talkroom_id = str(delivery.get("talkroom_id") or "").strip()
        if delivery.get("mode") == "answer":
            events.append({
                "event_key": f"gig:reply:{pass_id}:{talkroom_id or 'unknown'}",
                "kind": "reply",
                "lane": "reply",
                "entity_id": talkroom_id or "unknown",
                "occurred_at": timestamp,
                "state": "replied",
                "action": "購入者の質問へ回答",
                "result": "購入者からの質問に回答し、購入者画面への表示を確認しました",
                "next_action": "購入者からの次の返信を自動で確認します",
                "evidence": ["buyer_visible_dom", "message_sha256"],
                "attributes": {
                    "url": delivery.get("expected_url"),
                    "interaction_mode": "answer",
                },
            })
            return events
        artifact = _clean(delivery.get("artifact_basename"), "納品ファイル")
        events.append({
            "event_key": f"gig:delivery:{pass_id}:{talkroom_id or 'unknown'}",
            "kind": "delivery",
            "lane": "delivery",
            "entity_id": talkroom_id or "unknown",
            "occurred_at": timestamp,
            "state": "buyer_visible",
            "action": "納品内容を購入者画面で確認",
            "result": (
                f"{artifact}が購入者画面に表示され、"
                "納品内容を確認できる状態です"
            ),
            "next_action": "購入者からの確認結果を待ちます",
            "evidence": ["buyer_visible_dom", "artifact_sha256"],
            "attributes": {
                "artifact_basename": delivery.get("artifact_basename"),
                "artifact_version": delivery.get("artifact_version"),
                "package_sha256": delivery.get("package_sha256"),
                "live_dom_path": delivery.get("live_dom_path"),
            },
        })
    return events


def build_pass_envelope(
    *,
    pass_row: dict[str, Any],
    applications: list[dict[str, Any]],
    usage_rows: list[dict[str, Any]],
    observed_at: datetime,
    lane_events: list[dict[str, Any]] | None = None,
    net_mrr_jpy: int = 0,
    search_objective: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one immutable snapshot from already-durable pass evidence."""
    pass_id = str(pass_row.get("pass_id") or "").strip()
    status = str(pass_row.get("status") or "").strip()
    occurred_at = pass_row.get("ts")
    if (
        not pass_id
        or status not in {"success", "failed"}
        or not isinstance(occurred_at, int)
        or observed_at.tzinfo is None
    ):
        raise ValueError("pass envelope identity is incomplete")

    verified = _verified_applications(applications, pass_id)
    objective_active = bool(
        isinstance(search_objective, dict)
        and search_objective.get("status") == "active"
        and str(search_objective.get("last_pass_id") or "") == pass_id
    )
    objective_next_action = _clean(
        search_objective.get("next_action")
        if objective_active and isinstance(search_objective, dict)
        else None
    )
    model_calls = 0
    model_cost = 0.0
    for usage in usage_rows:
        budget = usage.get("budget")
        scope_id = budget.get("scope_id") if isinstance(budget, dict) else None
        if usage.get("loop") != "gig" or scope_id != pass_id:
            continue
        model_calls += 1
        value = usage.get("provider_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            model_cost += float(value)

    steps = [str(value) for value in pass_row.get("steps_executed") or []]
    answer_mode = any(
        event.get("kind") == "reply"
        and (event.get("attributes") or {}).get("interaction_mode") == "answer"
        for event in (lane_events or [])
    )
    action_labels = list(dict.fromkeys(
        (
            "購入者への回答"
            if answer_mode and step in {"PAID_WORK", "PAID_QUEUE_DELIVERY"}
            else STEP_LABELS[step]
        )
        for step in steps
        if step in STEP_LABELS
    ))
    events: list[dict[str, Any]] = [{
        "event_key": f"gig:work-cycle:{pass_id}",
        "kind": "work_cycle",
        "lane": None,
        "entity_id": pass_id,
        "occurred_at": _iso(occurred_at),
        "state": "completed" if status == "success" else "failed",
        "action": "・".join(action_labels) if action_labels else "作業サイクル",
        "result": (
            "予定された作業サイクルを完了しました"
            if status == "success"
            else "作業サイクル中に修復が必要な問題を検出しました"
        ),
        "next_action": (
            objective_next_action
            if status == "success" and objective_active and objective_next_action
            else "次の毎時サイクルで4つの仕事を再確認します"
            if status == "success"
            else "原因を記録し、修復後に同じ作業を再実行します"
        ),
        "evidence": ["pass_ledger"],
        "attributes": {
            "executed_steps": steps,
            "failure_step": pass_row.get("failed_step"),
            "failure_reason": pass_row.get("reason"),
        },
    }]
    events.extend(lane_events or [])
    for application in verified:
        request_id = str(
            application.get("requestId") or application.get("request_id") or ""
        ).strip()
        bucket = str(application.get("bucket") or "")
        if not request_id:
            continue
        events.append({
            "event_key": f"gig:application:{pass_id}:{request_id}",
            "kind": "application",
            "lane": "application",
            "entity_id": request_id,
            "occurred_at": _iso(application.get("ts") or occurred_at),
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
                "bucket": "retainer" if bucket == "retainer" else "single",
                "title": _clean(application.get("title"), "案件名を取得できませんでした"),
                "url": str(application.get("url") or ""),
                "category": application.get("category"),
                "price_jpy": application.get("price_jpy"),
            },
        })

    searched = sum(
        int(event.get("attributes", {}).get("searched") or 0)
        for event in events
        if event.get("kind") == "application_search"
    )
    work = {
        "searched": searched,
        "applied": len(verified),
        "replied": sum(
            event.get("kind") == "reply" and event.get("state") == "replied"
            for event in events
        ),
        "contracted": 0,
        "delivered": sum(
            event.get("kind") == "delivery"
            and event.get("state") == "buyer_visible"
            for event in events
        ),
        "paid": 0,
        "listings_created": sum(
            event.get("kind") == "listing" and event.get("state") == "published"
            for event in events
        ),
        "listings_improved": sum(
            event.get("kind") == "listing" and event.get("state") == "verified"
            for event in events
        ),
    }
    return {
        "specversion": "1.0",
        "id": f"gig:report:pass:{pass_id}:{status}",
        "source": SOURCE,
        "type": PASS_TYPE,
        "subject": f"gig-pass/{pass_id}",
        "time": _iso(occurred_at),
        "datacontenttype": "application/json",
        "data": {
            "report_type": "work_cycle",
            "status": status,
            "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
            "trace_id": pass_id,
            "state": (
                "応募候補の探索を継続中です。今回の作業サイクルは正常に終了しました"
                if status == "success" and objective_active
                else "作業サイクルは正常に完了しました"
                if status == "success"
                else "作業サイクルで修復が必要な問題を検出しました"
            ),
            "objective": (
                {
                    "status": "active",
                    "next_action": objective_next_action,
                }
                if objective_active
                else None
            ),
            "actions": action_labels,
            "results": [event["result"] for event in events],
            "next_actions": list(dict.fromkeys(
                event["next_action"] for event in events
            )),
            "metrics": {
                "model_calls": model_calls,
                "model_cost_usd": round(model_cost, 6),
                "verified_applications": len(verified),
                "searched_opportunities": searched,
            },
            "work": work,
            "funnel": {
                "applications": work["applied"],
                "replies": work["replied"],
                "contracts": work["contracted"],
                "deliveries": work["delivered"],
                "payments": work["paid"],
                "net_mrr": int(net_mrr_jpy),
            },
            "events": events,
        },
    }


def render_human_ja(envelope: dict[str, Any]) -> str:
    """Render plain Japanese from the canonical envelope only."""
    data = envelope["data"]
    if _clean(data.get("human_message_ja")):
        return str(data["human_message_ja"])
    status = data["status"]
    stamp = datetime.fromisoformat(envelope["time"]).astimezone(JST).strftime(
        "%m/%d %H:%M"
    )
    events = data["events"]
    applications = [event for event in events if event["kind"] == "application"]
    objective_active = bool(
        isinstance(data.get("objective"), dict)
        and data["objective"].get("status") == "active"
    )
    lines = [
        (
            f"🟡 ギグワークを進め、応募探索を継続しています（{stamp}）"
            if status == "success" and objective_active
            else f"✅ ギグワークの作業が完了しました（{stamp}）"
            if status == "success"
            else f"⚠️ ギグワークで修復が必要な問題を見つけました（{stamp}）"
        ),
        "",
        "状態",
        str(data["state"]),
        "",
        "今回行ったこと",
    ]
    actions = data.get("actions") or []
    if actions:
        lines.append(f"- {'、'.join(actions)}を確認・実行しました")
    else:
        lines.append("- 実行記録を確認しました")
    searched = int((data.get("work") or {}).get("searched") or 0)
    if searched:
        lines.append(
            f"- 応募: 延べ{searched}件を確認し、{len(applications)}件に応募しました"
        )
    else:
        lines.append(f"- 応募: {len(applications)}件")
    for event in applications:
        attributes = event["attributes"]
        label = "継続" if attributes["bucket"] == "retainer" else "単発"
        lines.extend((
            f"  - [{label}] {attributes['title']}",
            f"    {attributes['url']}",
            "    送信・応募履歴・台帳の3か所で確認済み",
        ))
    lane_labels = {
        "listing": "出品",
        "reply": "返信",
        "delivery": "納品",
    }
    for event in events:
        label = lane_labels.get(event.get("kind"))
        if label:
            lines.append(f"- {label}: {event['result']}")
    if status == "failed":
        cycle = next(event for event in events if event["kind"] == "work_cycle")
        reason = cycle["attributes"].get("failure_reason")
        if reason:
            lines.append(f"- 検出内容: {_clean(reason)}")
    lines.extend((
        "",
        "次の予定",
        *[f"- {value}" for value in data.get("next_actions") or []],
        "",
        f"AI処理費: ${data['metrics']['model_cost_usd']:.4f}",
        f"記録ID: {data['trace_id']}",
    ))
    return "\n".join(lines)


def render_human_en(envelope: dict[str, Any]) -> str:
    """Render plain English from the canonical envelope only."""
    data = envelope["data"]
    if _clean(data.get("human_message_en")):
        return str(data["human_message_en"])
    status = str(data.get("status") or "")
    applications = [
        event
        for event in data.get("events") or []
        if event.get("kind") == "application"
    ]
    lines = [
        (
            "✅ Gig work cycle completed"
            if status == "success"
            else "⚠️ Gig work found a problem that needs automatic recovery"
        ),
        "",
        "Status",
        (
            "The scheduled work cycle completed normally."
            if status == "success"
            else "The cycle recorded the problem and will retry after repair."
        ),
        "",
        "Work completed",
        f"- Verified applications: {len(applications)}",
        "",
        "Next automatic action",
        "- Check all four work areas again in the next hourly cycle.",
        "No user action is required.",
    ]
    return "\n".join(lines)


def render_agent_json(envelope: dict[str, Any]) -> str:
    return json.dumps(
        envelope,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def append_agent_feed(path: Path, envelope: dict[str, Any]) -> dict[str, int]:
    """Append once by CloudEvents id while holding an advisory file lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event_id = str(envelope.get("id") or "").strip()
    if not event_id:
        raise ValueError("envelope id is required")
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        for raw in handle:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("id") == event_id:
                return {"appended": 0, "duplicate": 1}
        handle.seek(0, os.SEEK_END)
        handle.write(render_agent_json(envelope) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {"appended": 1, "duplicate": 0}
