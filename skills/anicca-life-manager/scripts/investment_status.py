"""Build the local /invest reply from the investment loop's existing receipts."""
from __future__ import annotations

import json
from pathlib import Path

ALPACA_SIGNUP_URL = "https://app.alpaca.markets/signup"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def build_investment_reply(state_root: Path) -> dict:
    root = state_root / "alpaca-investment"
    account_path = root / "account-status.json"
    account = _read_json(account_path)
    observation = _read_json(root / "observation-latest.json")
    allocation = _read_json(root / "allocation-latest.json")

    if not account_path.exists():
        return {
            "text": "\n".join([
                "Investment Loop",
                "",
                "Alpacaで口座開設と本人確認を完了してください。",
                "Life Managerと同じメールアドレスを使うと接続が簡単です。",
                "完了後はLife Managerが審査状態を確認し、自動運転まで進めます。",
            ]),
            "reply_markup": {"inline_keyboard": [[
                {"text": "Alpacaで口座開設する", "url": ALPACA_SIGNUP_URL},
                {"text": "今はしない", "callback_data": "invest:later"},
            ]]},
        }

    application_status = str(account.get("application_status") or "unknown").lower()
    paper_account = observation.get("account") if isinstance(observation.get("account"), dict) else {}
    equity = paper_account.get("equity")
    cash = paper_account.get("cash")
    reason = allocation.get("reason")
    decision = "取引なし" if allocation.get("approved") is False else "取引候補あり"

    lines = ["Investment Loop", ""]
    if application_status == "in_review":
        lines.append("ライブ口座: 審査中です。今は操作不要です。承認を確認したら、次に必要な操作だけ知らせます。")
    elif application_status == "approved":
        lines.append("ライブ口座: 承認済みです。入金とリスク上限を確認するまでライブ注文は出しません。")
    elif application_status in {"rejected", "action_required"}:
        lines.append("ライブ口座: 追加対応が必要です。Alpacaの画面で表示される本人対応だけ行ってください。")
    else:
        lines.append("ライブ口座: 状態をまだ確認できません。ライブ注文は出しません。")

    if equity is not None and cash is not None:
        lines.append(f"paper loop: 稼働中。資産 ${equity}、現金 ${cash}、今回の判断は{decision}です。")
        if reason:
            lines.append(f"理由: {reason}")
    else:
        lines.append("paper loop: 最新状態をまだ読み取れません。次の5分周期で再確認します。")
    return {"text": "\n".join(lines)}


def build_investment_status(state_root: Path) -> str:
    """Compatibility helper for callers that only need message text."""
    return build_investment_reply(state_root)["text"]
