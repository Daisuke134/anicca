from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .ledger import Ledger
from .browser_agent.contracts import QueueRowReceiptV1
from .browser_agent.outcome_reporting import build_hourly_outcome_message
from .telegram import send_daily_report, send_document_once, send_once


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def deliver_wake_report(
    *,
    ledger_path: Path,
    outbox_path: Path,
    run_id: str,
    japan_day: str,
    runner_summary_path: Path,
    discovery_path: Path,
    output_path: Path,
    sender: Callable[..., dict[str, str | None]] = send_daily_report,
) -> dict[str, Any]:
    summary = _read_object(runner_summary_path)
    discovery = _read_object(discovery_path)
    result: dict[str, Any] = {}
    result_path = Path(str(summary.get("result_path") or ""))
    if result_path.parent == runner_summary_path.parent:
        result = _read_object(result_path)
    semantic = _read_object(runner_summary_path.parent / "semantic-validation.json")
    attempt: dict[str, Any] = {}
    attempts_path = Path(str(summary.get("attempts_path") or ""))
    if attempts_path.parent == runner_summary_path.parent and attempts_path.is_file():
        lines = attempts_path.read_text(encoding="utf-8").splitlines()
        if lines:
            try:
                value = json.loads(lines[-1])
                attempt = value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass

    queued = discovery.get("queued_application_ids")
    application_id = str(queued[0]) if isinstance(queued, list) and queued else ""
    company, role = "none", "none"
    ledger = Ledger(ledger_path)
    try:
        row = ledger.connection.execute(
            "SELECT company,title FROM applications WHERE id=?",
            (application_id,),
        ).fetchone()
        if row is not None:
            company, role = str(row["company"]), str(row["title"])
    finally:
        ledger.close()

    semantic_reason = semantic.get("reason") if semantic.get("status") == "failed" else None
    result_status = str(result.get("status") or "")
    outcome = (
        "failed"
        if semantic_reason or result_status == "transport_failed"
        else "success" if summary.get("status") == "success" else "failed"
    )
    reason = str(
        semantic_reason
        or (result_status if result_status == "transport_failed" else None)
        or attempt.get("error_class")
        or attempt.get("adapter_error")
        or summary.get("status")
        or discovery.get("status")
        or "unknown"
    )
    if outcome == "success":
        next_action = "continue_next_eligible_workday"
    elif reason == "transient_quota":
        next_action = "retry_with_available_provider_capacity"
    elif discovery.get("status") == "no_work":
        next_action = "discover_next_eligible_workday"
    else:
        next_action = "resume_same_row_next_wake"
    checked = len(discovery.get("shortlist") or discovery.get("discovered") or [])
    if outcome == "success" and company != "none":
        heading = "✅ 今回のWorkday処理を完了しました"
        result_text = f"会社: {company}\n求人: {role}"
    elif outcome == "success":
        heading = "🔎 新しい応募対象を確認しました"
        result_text = "今回は新しい応募の完了には至りませんでした。"
    else:
        heading = "⚠️ Workday処理を完了できませんでした"
        result_text = (
            f"会社: {company}\n求人: {role}"
            if company != "none"
            else "応募対象を確定する前に処理が止まりました。"
        )
    next_text = {
        "continue_next_eligible_workday": "次の新しい適合求人の確認を続けます。",
        "retry_with_available_provider_capacity": "利用可能なモデル容量で同じ安全な処理を再開します。",
        "discover_next_eligible_workday": "登録済みsourceと新しい公式Workday会社の探索を続けます。",
        "resume_same_row_next_wake": "同じ求人の保存済みcheckpointから安全に再開します。",
    }.get(next_action, "30分後に次の安全な処理を続けます。")
    message = (
        "Codex::: [Job Hunter][30分確認]\n"
        f"{heading}\n\n"
        "確認したこと\n"
        f"公式Workday候補を{checked}件、現在のLedgerと照合しました。\n\n"
        "結果\n"
        f"{result_text}\n\n"
        "理由\n"
        f"{reason}\n\n"
        "次に自動で行うこと\n"
        f"{next_text}\nユーザーの操作は必要ありません。"
    )
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    delivery = sender(
        database=outbox_path,
        japan_day=japan_day,
        message=message,
        material_digest=digest,
    )
    receipt: dict[str, Any] = {
        "status": delivery.get("status"),
        "message_id": delivery.get("message_id"),
        "event_key": delivery.get("event_key"),
        "application_id": application_id or None,
        "company": company,
        "role": role,
        "outcome": outcome,
        "reason": reason,
        "next_action": next_action,
    }
    _write_private_json(output_path, receipt)
    return receipt


def deliver_reconciled_outcomes(
    *,
    ledger_path: Path,
    outbox_path: Path,
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> list[dict[str, str | None]]:
    ledger = Ledger(ledger_path)
    try:
        rows = ledger.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              submission_confirmations.message_id
            FROM submission_confirmations
            JOIN submit_intents
              ON submit_intents.intent_id = submission_confirmations.intent_id
            JOIN applications
              ON applications.id = submit_intents.application_id
            WHERE applications.current_state = 'submitted'
            ORDER BY submission_confirmations.received_at,
                     submission_confirmations.message_id
            """
        ).fetchall()
    finally:
        ledger.close()

    deliveries = []
    for row in rows:
        application_id = str(row["application_id"])
        message_id = str(row["message_id"])
        message = build_hourly_outcome_message(
            (
                QueueRowReceiptV1(
                    application_id,
                    str(row["company"]),
                    str(row["title"]),
                    "submitted",
                ),
            ),
            {application_id: "authoritative_receipt_email"},
        )
        delivery = sender(
            database=outbox_path,
            event_key=f"application-submitted:{application_id}:{message_id}",
            message=message,
        )
        deliveries.append(
            {
                "application_id": application_id,
                "receipt_message_id": message_id,
                "status": delivery["status"],
                "message_id": delivery["message_id"],
            }
        )
    return deliveries


def deliver_fit_decision(
    *,
    decision: dict[str, Any],
    outbox_path: Path,
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> dict[str, str | None]:
    status = str(decision.get("decision") or "")
    company = str(decision.get("company") or "")
    title = str(decision.get("title") or "")
    reason = str(decision.get("reason") or "判断理由は記録されていません。")
    compensation = str(decision.get("compensation") or "給与情報は未確認です。")
    if status == "qualified":
        heading = "✅ この求人へ応募します"
        next_action = "応募フォームを自動で進め、結果を改めて報告します。"
    elif status == "hold":
        heading = "⏸ この求人への応募を保留しました"
        next_action = "確認可能な不足情報を調べながら、次の求人の確認を続けます。"
    else:
        heading = "🚫 この求人には応募しませんでした"
        next_action = "次の求人の確認を続けます。ユーザーの操作は必要ありません。"
    message = (
        "Codex::: [Job Hunter][応募判断]\n"
        f"{heading}\n\n"
        f"会社: {company}\n"
        f"求人: {title}\n"
        f"理由: {reason}\n"
        f"給与: {compensation}\n\n"
        "次に自動で行うこと\n"
        f"{next_action}"
    )
    return sender(
        database=outbox_path,
        event_key=(
            f"workday-fit:{decision.get('application_id')}:"
            f"{decision.get('evidence_sha256')}"
        ),
        message=message,
    )


def deliver_application_progress(
    *,
    ledger_path: Path,
    outbox_path: Path,
    application_id: str,
    run_id: str,
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> dict[str, str | None]:
    ledger = Ledger(ledger_path)
    try:
        row = ledger.connection.execute(
            "SELECT company,title,current_state FROM applications WHERE id=?",
            (application_id,),
        ).fetchone()
        fit = ledger.connection.execute(
            "SELECT decision,evidence_sha256 FROM workday_fit_decisions WHERE application_id=?",
            (application_id,),
        ).fetchone()
    finally:
        ledger.close()
    if row is None or fit is None or str(fit["decision"]) != "qualified":
        raise ValueError("application progress requires a qualified Workday row")

    fit_key = f"workday-fit:{application_id}:{fit['evidence_sha256']}"
    from .outbox import Outbox

    outbox = Outbox(outbox_path)
    try:
        fit_row = outbox.connection.execute(
            "SELECT payload,telegram_message_id FROM outbox WHERE event_key=? AND status='sent'",
            (fit_key,),
        ).fetchone()
    finally:
        outbox.close()
    detail_lines = []
    if fit_row is not None:
        for line in str(fit_row[0]).splitlines():
            if line.startswith("理由:") or line.startswith("給与:"):
                detail_lines.append(line)
    if not detail_lines:
        detail_lines.append("理由: 完全な公式JDと履歴書・希望条件をモデルが比較し、面接可能性ありと判断しました。")

    message = (
        "Codex::: [Job Hunter][応募処理]\n"
        "📨 Workday応募を開始または再開しました\n\n"
        f"会社: {row['company']}\n"
        f"求人: {row['title']}\n"
        + "\n".join(detail_lines)
        + "\n\n状態\n"
        f"現在の台帳状態 `{row['current_state']}` から、専用ブラウザで応募フォームを進めています。\n\n"
        "次に自動で行うこと\n"
        "公式完了画面とGmail receiptを確認し、結果を別メッセージで報告します。ユーザーの操作は必要ありません。"
    )
    return sender(
        database=outbox_path,
        event_key=f"workday-application-progress:{application_id}:{run_id}",
        message=message,
    )


def deliver_submitted_resumes(
    *,
    ledger_path: Path,
    outbox_path: Path,
    media_root: Path,
    sender: Callable[..., dict[str, str | None]] = send_document_once,
) -> list[dict[str, str | None]]:
    ledger = Ledger(ledger_path)
    try:
        reports = ledger.submitted_resume_reports()
    finally:
        ledger.close()

    deliveries = []
    for report in reports:
        message = (
            "📎 Resume used for submitted application\n"
            f"{report['company']} — {report['title']}\n"
            f"{report['canonical_url']}"
        )
        delivery = sender(
            database=outbox_path,
            event_key=(
                f"application-resume:{report['application_id']}:"
                f"{report['resume_sha256']}"
            ),
            message=message,
            document=Path(report["resume_path"]),
            media_root=media_root,
        )
        deliveries.append(
            {
                "application_id": report["application_id"],
                "status": delivery["status"],
                "message_id": delivery["message_id"],
            }
        )
    return deliveries


def deliver_terminal_report(
    *,
    outbox_path: Path,
    run_id: str,
    outcome: str,
    reason: str,
    output_path: Path,
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> dict[str, Any]:
    message = (
        "Codex::: [Job Hunter][Inbox]\n"
        f"run={run_id}\n"
        f"outcome={outcome}\n"
        f"reason={reason}"
    )
    try:
        delivery = sender(
            database=outbox_path,
            event_key=f"job-search-inbox:{run_id}",
            message=message,
        )
        receipt: dict[str, Any] = {
            "delivery": "ack" if delivery.get("message_id") else "delivery_unknown",
            "event_key": f"job-search-inbox:{run_id}",
            "message_id": delivery.get("message_id"),
            "outcome": outcome,
            "reason": reason,
        }
    except Exception as error:
        receipt = {
            "delivery": "delivery_unknown",
            "event_key": f"job-search-inbox:{run_id}",
            "outcome": outcome,
            "reason": reason,
            "delivery_error": type(error).__name__,
        }
    _write_private_json(output_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("deliver", "wake", "progress", "terminal"))
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--media-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--day")
    parser.add_argument("--runner-summary", type=Path)
    parser.add_argument("--discovery", type=Path)
    parser.add_argument("--application-id")
    parser.add_argument("--outcome")
    parser.add_argument("--reason")
    args = parser.parse_args()

    if args.command == "terminal":
        if not all((args.run_id, args.outcome, args.reason)):
            parser.error("terminal requires --run-id, --outcome and --reason")
        receipt = deliver_terminal_report(
            outbox_path=args.outbox,
            run_id=args.run_id,
            outcome=args.outcome,
            reason=args.reason,
            output_path=args.output,
        )
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "progress":
        if not args.application_id or not args.run_id:
            parser.error("progress requires --application-id and --run-id")
        receipt = deliver_application_progress(
            ledger_path=args.ledger,
            outbox_path=args.outbox,
            application_id=args.application_id,
            run_id=args.run_id,
        )
        _write_private_json(args.output, receipt)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0 if receipt.get("message_id") else 1

    if args.command == "wake":
        if not all((args.run_id, args.day, args.runner_summary, args.discovery)):
            parser.error("wake requires --run-id, --day, --runner-summary and --discovery")
        receipt = deliver_wake_report(
            ledger_path=args.ledger,
            outbox_path=args.outbox,
            run_id=args.run_id,
            japan_day=args.day,
            runner_summary_path=args.runner_summary,
            discovery_path=args.discovery,
            output_path=args.output,
        )
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0 if receipt.get("message_id") else 1

    if args.media_root is None:
        parser.error("deliver requires --media-root")

    deliveries = deliver_submitted_resumes(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
        media_root=args.media_root,
    )
    outcomes = deliver_reconciled_outcomes(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(
            {"deliveries": deliveries, "outcomes": outcomes},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0
    os.chmod(args.output, 0o600)


if __name__ == "__main__":
    raise SystemExit(main())
