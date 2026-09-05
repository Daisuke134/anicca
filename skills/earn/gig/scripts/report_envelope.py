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


def _incident_moment(occurred_at: object) -> str:
    """Render an event's ISO timestamp as a JST minute, or say we do not know.

    Minute precision is deliberate: it is enough to tell two incidents apart in
    a suppression window measured in hours, and coarse enough that a retry of
    the same incident inside the same minute still collapses into one message.
    """
    try:
        moment = datetime.fromisoformat(str(occurred_at))
    except (TypeError, ValueError):
        return "時刻不明"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(JST).strftime("%-m月%-d日 %H:%M")


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


def _load_local(name: str):
    import importlib.util

    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def application_outcome(evidence_dir: Path) -> dict[str, Any]:
    """The application breakdown for one pass, from the evidence B2 already wrote.

    Reads beside the existing agent-B2 read rather than collecting anything new. A pass
    whose B2 never ran leaves no parent-commit.json, and that absence is the signal that
    distinguishes an outage from an empty market.
    """
    summary_module = _load_local("application_outcome_summary")
    agent_dir = Path(evidence_dir) / "agent-B2"
    commit = _read_json(agent_dir / "parent-commit.json") or {}
    decisions = _read_json(agent_dir / "application-decisions.json") or {}
    results = commit.get("results") if isinstance(commit, dict) else None
    return summary_module.summarise(results, decisions)


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
        state = _clean(event.get("state"))
        if state in {"selected", "skipped"}:
            platform = _clean(attributes.get("platform_display_name")) or _clean(
                attributes.get("platform"), "Gig"
            ).capitalize()
            reasons = [
                _clean(reason) for reason in attributes.get("reason_codes", [])
                if _clean(reason)
            ]
            reason_lines = [f"- {reason}" for reason in reasons] or ["- Lunaの判断理由は記録されていません"]
            selected = state == "selected"
            ja = "\n".join((
                f"[{platform}][応募判断]",
                "✅ この案件への応募を準備します" if selected else "🚫 この案件には応募しませんでした",
                "",
                f"案件: {title}",
                f"依頼ID: {event['entity_id']}",
                "理由:",
                *reason_lines,
                "",
                "次に自動で行うこと",
                str(event["next_action"]),
                "ユーザーの操作は必要ありません。",
            ))
            en = "\n".join((
                f"[{platform}][Application decision]",
                "✅ Preparing an application" if selected else "🚫 Skipped this opportunity",
                "",
                f"Job: {title}",
                f"ID: {event['entity_id']}",
                "Reasons:",
                *reason_lines,
                "",
                "Next automatic action",
                str(event["next_action"]),
                "No user action is required.",
            ))
            return ja, en
        if state == "verified" and _clean(attributes.get("platform")) != "coconala":
            platform = _clean(attributes.get("platform_display_name")) or _clean(
                attributes.get("platform"), "Gig"
            ).capitalize()
            quote = attributes.get("quote") if isinstance(attributes.get("quote"), dict) else {}
            ja = "\n".join((
                f"[{platform}][応募完了]",
                "✅ 実際に応募しました",
                "",
                f"案件: {title}",
                f"依頼ID: {event['entity_id']}",
                f"Proposal ID: {_clean(attributes.get('proposal_id'), '確認済み')}",
                f"提案: {_clean(quote.get('currency'))} {_clean(quote.get('amount'))} / {_clean(quote.get('unit'))}",
                *([f"Connects: {attributes.get('connects_before')} → {attributes.get('connects_after')} (-{attributes.get('connects_spent')})"]
                  if attributes.get("connects_spent") is not None else []),
                "",
                "次に自動で行うこと",
                str(event["next_action"]),
                "ユーザーの操作は必要ありません。",
            ))
            return ja, ja
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
        # The detection moment is what makes one incident tellable from another.
        # Without it every failure in this lane renders the same bytes, and the
        # outbox — which suppresses a body it has already sent for 24 hours —
        # delivers only the first. Measured 2026-08-04: this body had gone out
        # 104 times for 納品 and 98 for 応募.
        #
        # The raw failure class goes in the English body only. The Japanese body
        # is under a no-jargon contract (test_business_event_reporting.py pins
        # "application_readback_failed" as forbidden there), and a timestamp is
        # already enough to keep two incidents apart.
        detected_at = _incident_moment(event.get("occurred_at"))
        failure_class = _clean(attributes.get("failure_class"), "不明")
        ja = "\n".join((
            f"🟠 {lane_ja}機能を自動で復旧しています",
            "",
            "状態",
            f"{detected_at} に、予定した作業を最後まで確認できない問題を検出しました。",
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
            f"At {detected_at}, the system could not verify the scheduled work through completion.",
            f"Detected fault: {failure_class}",
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
        "applied": int(kind == "application" and event.get("state") not in {"selected", "skipped"}),
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


def _e3_reaction_lines_ja(snapshot: dict[str, Any]) -> list[str]:
    """E3's buyer-reaction/score-vs-outcome breakdown, only when daily_gig_report.py
    ran today. Absent (older snapshot, or the E3 pass hasn't landed yet) renders
    nothing -- an optional section can't be allowed to make the daily report crash.
    """
    reactions = snapshot.get("buyer_replies_by_reaction")
    score_bands = snapshot.get("score_reality_by_band")
    completed = snapshot.get("revenue_completed_today")
    lines: list[str] = []
    if isinstance(reactions, dict) and reactions:
        breakdown = "、".join(
            f"{name}{int(count)}件" for name, count in sorted(reactions.items())
        )
        lines.append(f"- 買い手返信の内訳: {breakdown}")
    if isinstance(completed, (int, float)) and not isinstance(completed, bool):
        lines.append(f"- 取引完了: {int(completed)}件")
    if isinstance(score_bands, dict) and score_bands:
        band_text = "、".join(
            f"{band}点:" + "/".join(
                f"{reaction}{int(count)}" for reaction, count in sorted(counts.items())
            )
            for band, counts in sorted(score_bands.items())
        )
        lines.append(f"- 納品前スコアと反応: {band_text}")
    if not lines:
        return []
    return ["", "買い手の反応（本日）", *lines]


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
    # A19: a daily report without a four-layer health verdict must not render.
    # The old path judged the day by raw counts and printed success through a
    # six-day revenue outage; requiring the verdict here is the code-level ban.
    health = snapshot.get("health")
    layers = health.get("layers") if isinstance(health, dict) else None
    verdict = str(health.get("verdict")) if isinstance(health, dict) else ""
    if (
        not isinstance(layers, dict)
        or set(layers) != {"liveness", "coverage", "productivity", "economics"}
        or verdict not in {"GREEN", "WARN", "RED"}
    ):
        raise ValueError("daily report requires a four-layer health verdict")
    if verdict == "GREEN" and any(
        str(layer.get("verdict")) != "GREEN" for layer in layers.values()
    ):
        raise ValueError("daily verdict GREEN with a non-GREEN layer is forbidden")
    marks = {"GREEN": "✅", "WARN": "🟠", "RED": "🔴"}
    headline_ja = {
        "GREEN": f"☀️ 今日のギグワーク結果｜{date_ja}",
        "WARN": f"🟠 今日のギグワーク結果｜{date_ja}（注意が必要です）",
        "RED": f"🔴 今日のギグワーク結果｜{date_ja}（対応が必要な問題があります）",
    }[verdict]
    state_ja = {
        "GREEN": "4つの仕事をすべて確認できています。",
        "WARN": "一部に注意が必要ですが、自動で確認を続けています。",
        "RED": "問題が起きています。自動復旧を続けています。",
    }[verdict]
    state_en = {
        "GREEN": "All four work areas were checked.",
        "WARN": "Some areas need attention; automatic checks continue.",
        "RED": "Something is wrong; automatic recovery is running.",
    }[verdict]
    layer_labels_ja = {
        "liveness": "稼働",
        "coverage": "確認",
        "productivity": "実作業",
        "economics": "売上",
    }
    layer_lines_ja = [
        f"{marks.get(str(layers[name].get('verdict')), '🔴')} "
        f"{layer_labels_ja[name]}: {_clean(layers[name].get('reason_ja'), '判定不能')}"
        for name in ("liveness", "coverage", "productivity", "economics")
    ]
    pass_24h = health.get("pass_24h") or {}
    pass_total = int(pass_24h.get("total") or 0)
    pass_ok = int(pass_24h.get("succeeded") or 0)
    pass_line = (
        f"- 定時の巡回の成功率(24時間): {round(100 * pass_ok / pass_total)}%"
        f"（成功{pass_ok}/全{pass_total}回）"
        if pass_total
        else "- 定時の巡回の記録が24時間ありません"
    )
    last_success = health.get("last_success_pass_jst")
    last_success_line = (
        f"- 最後にすべて成功した巡回: {last_success}"
        if last_success
        else "- 最後にすべて成功した巡回: 記録なし"
    )
    settled_delta = int(health.get("settled_delta_jpy") or 0)
    settled_yesterday = int(health.get("settled_yesterday_jpy") or 0)
    zero_streak = int(health.get("zero_settlement_streak_days") or 0)
    revenue_lines = [
        f"- 本日の入金 {revenue_today:,}円",
        f"- 前日比 {settled_delta:+,}円（昨日 {settled_yesterday:,}円）",
        f"- 今月の検収済売上 {revenue_month:,}円",
        f"- 継続売上 {int(funnel.get('net_mrr') or 0):,}円",
    ]
    if zero_streak:
        revenue_lines.append(f"- 検収済みの入金が{zero_streak}日連続で増えていません")
    ja = "\n".join((
        headline_ja,
        "",
        "状態",
        state_ja,
        *layer_lines_ja,
        pass_line,
        last_success_line,
        "",
        "売上",
        *revenue_lines,
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
        *_e3_reaction_lines_ja(snapshot),
        "",
        "次に自動で行うこと",
        "- 新着案件、購入者からの返信、進行中の納品、公開中サービスを順に確認します。",
        "→ 応募管理を見る: https://coconala.com/mypage/job_matching/applied/offers",
        "→ 売上を見る: https://coconala.com/mypage/dashboard_provider",
        "ユーザーの操作は必要ありません。",
    ))
    headline_en = {
        "GREEN": f"☀️ Daily gig work results | {occurred_at.astimezone(JST):%B %-d}",
        "WARN": f"🟠 Daily gig work results | {occurred_at.astimezone(JST):%B %-d} (needs attention)",
        "RED": f"🔴 Daily gig work results | {occurred_at.astimezone(JST):%B %-d} (problems detected)",
    }[verdict]
    layer_labels_en = {
        "liveness": "Uptime",
        "coverage": "Checks",
        "productivity": "Output",
        "economics": "Revenue",
    }
    en = "\n".join((
        headline_en,
        "",
        "Status",
        state_en,
        *(
            f"{marks.get(str(layers[name].get('verdict')), '🔴')} "
            f"{layer_labels_en[name]}: {str(layers[name].get('verdict'))}"
            for name in ("liveness", "coverage", "productivity", "economics")
        ),
        "",
        "Revenue",
        f"- Payments today: JPY {revenue_today:,}",
        f"- Day-over-day: JPY {settled_delta:+,}",
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
            # The wire status is derived from the four-layer verdict alone;
            # there is no counts-based path back to "healthy" (A19).
            "status": {"GREEN": "healthy", "WARN": "attention", "RED": "critical"}[verdict],
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
    action_labels = [
        STEP_LABELS[step]
        for step in steps
        if step in STEP_LABELS
    ]
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
            "次の毎時サイクルで4つの仕事を再確認します"
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
    # P1b: the count alone could not tell an outage from an empty market -- a lane blocked
    # all hour and a lane that inspected 35 jobs and found every one closed both printed
    # "応募: 0件". pass_row carries the same evidence_dir telegram_report already hands to
    # collect_lane_events, so the breakdown costs no new collection. Absent on older rows
    # and fixture callers, where the report must still render.
    evidence_value = pass_row.get("evidence_dir")
    work = {
        "searched": searched,
        "application_outcome": (
            application_outcome(Path(str(evidence_value))) if evidence_value else {}
        ),
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
                "作業サイクルは正常に完了しました"
                if status == "success"
                else "作業サイクルで修復が必要な問題を検出しました"
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
    lines = [
        (
            f"✅ ギグワークの作業が完了しました（{stamp}）"
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
    # P1b: the count alone could not distinguish a lane that never ran from a lane that
    # inspected 35 jobs and found every one of them closed. The breakdown is shown on every
    # pass, including successful ones, because four applications can still hide 33 wasted
    # inspections -- which is what the numbers showed on 2026-08-06.
    outcome = (data.get("work") or {}).get("application_outcome") or {}
    if outcome:
        summary_module = _load_local("application_outcome_summary")
        lines.append(summary_module.render_line({**outcome, "applied": len(applications)}))
    else:
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


def append_work_event(path: Path, event: dict[str, Any]) -> dict[str, int]:
    """Append one provider-neutral WorkEvent once by event_key."""
    if (
        not isinstance(event, dict)
        or event.get("kind") not in WORK_EVENT_KINDS
        or not _clean(event.get("event_key"))
        or not _clean(event.get("entity_id"))
        or not _clean(event.get("occurred_at"))
        or not isinstance(event.get("attributes"), dict)
    ):
        raise ValueError("work event identity is incomplete")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event_key = str(event["event_key"])
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        for raw in handle:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("event_key") == event_key:
                return {"appended": 0, "duplicate": 1}
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(
            event, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {"appended": 1, "duplicate": 0}
