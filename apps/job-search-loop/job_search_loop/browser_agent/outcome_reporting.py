from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ..telegram import send_once
from .contracts import QueueRowReceiptV1


def _line(value: str) -> str:
    return " ".join(value.split())[:240]


def build_hourly_outcome_message(
    receipts: Sequence[QueueRowReceiptV1],
    evidence_classes: Mapping[str, str],
) -> str:
    messages = []
    for receipt in receipts:
        if receipt.status == "submitted":
            evidence_class = evidence_classes.get(receipt.application_id, "")
            if evidence_class not in {"exact_completion_ui", "authoritative_receipt_email"}:
                raise ValueError("submitted Telegram row lacks authoritative evidence")
            heading = "📨 新しい仕事へ応募しました"
            state = "応募の送信が完了し、応募先の受領証拠を確認しました。"
            evidence = f"確認: {evidence_class}"
            next_action = "返信または選考連絡の到着を自動で確認します。"
        elif receipt.status == "checkpointed":
            heading = "⏸ 応募を一時停止しました"
            state = "安全に再開できるcheckpointを保存しました。"
            evidence = "確認: 外部送信前または再試行禁止状態を記録済み"
            next_action = "同じ求人を安全に再開しながら、求人確認を続けます。"
        elif receipt.status == "submit_unknown":
            heading = "⚠️ 応募結果を確認中です"
            state = "送信結果が確定していないため、重複応募せず確認しています。"
            evidence = "確認: authoritative receipt待ち"
            next_action = "Gmailと応募先画面を自動で照合します。"
        elif receipt.status == "post_submit_verification":
            heading = "🔎 応募メールを確認中です"
            state = "応募フォームの送信後、正式な受領メールを待っています。"
            evidence = "確認: provider receipt待ち"
            next_action = "Gmailを自動確認し、届き次第submittedへ更新します。"
        elif receipt.status == "ineligible":
            heading = "🚫 この求人には応募しませんでした"
            state = "応募条件を満たさないため送信していません。"
            evidence = "確認: 応募送信なし"
            next_action = "次の求人の確認を続けます。"
        else:
            heading = "ℹ️ 応募処理を完了しました"
            state = "応募は送信されていません。"
            evidence = "確認: 応募送信なし"
            next_action = "次の求人の確認を続けます。"
        messages.append(
            "Codex::: [Job Hunter][応募結果]\n"
            f"{heading}\n\n"
            f"会社: {_line(receipt.company)}\n"
            f"求人: {_line(receipt.role)}\n\n"
            "状態\n"
            f"{state}\n\n"
            f"{evidence}\n\n"
            "次に自動で行うこと\n"
            f"{next_action}\n"
            "ユーザーの操作は必要ありません。"
        )
    return "\n\n---\n\n".join(messages)


def send_hourly_outcomes(
    *,
    database: Path,
    wake_id: str,
    receipts: Sequence[QueueRowReceiptV1],
    evidence_classes: Mapping[str, str],
    sender: Callable[..., dict[str, str | None]] = send_once,
) -> dict[str, str | None]:
    message = build_hourly_outcome_message(receipts, evidence_classes)
    digest = hashlib.sha256(message.encode()).hexdigest()[:16]
    result = sender(
        database=database,
        event_key=f"job-search-hourly:{_line(wake_id)}:{digest}",
        message=message,
    )
    if result.get("status") != "sent" or not result.get("message_id"):
        raise RuntimeError("hourly Telegram outcome has no acknowledged message ID")
    return result
