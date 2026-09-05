import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from investment_status import ALPACA_SIGNUP_URL, build_investment_reply, build_investment_status


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_in_review_reuses_existing_paper_receipts(tmp_path):
    root = tmp_path / "alpaca-investment"
    _write(root / "account-status.json", {"application_status": "in_review"})
    _write(root / "observation-latest.json", {"account": {"equity": "99996.76", "cash": "99996.76"}})
    _write(root / "allocation-latest.json", {"approved": False, "reason": "No fresh edge."})

    message = build_investment_status(tmp_path)

    assert message.startswith("Investment Loop\n")
    assert "審査中" in message
    assert "今は操作不要" in message
    assert "資産 $99996.76" in message
    assert "取引なし" in message
    assert "No fresh edge." in message
    assert "Alpaca Loop" not in message
    assert "Codex" not in message


def test_unknown_status_fails_closed_without_inventing_balance(tmp_path):
    root = tmp_path / "alpaca-investment"
    root.mkdir()
    (root / "account-status.json").write_text("not-json", encoding="utf-8")

    reply = build_investment_reply(tmp_path)
    message = reply["text"]

    assert "状態をまだ確認できません" in message
    assert "ライブ注文は出しません" in message
    assert "最新状態をまだ読み取れません" in message
    assert "reply_markup" not in reply


def test_missing_account_status_offers_exact_official_signup_link(tmp_path):
    reply = build_investment_reply(tmp_path)

    assert reply["text"].startswith("Investment Loop\n")
    assert "口座開設と本人確認" in reply["text"]
    assert "Life Managerと同じメールアドレス" in reply["text"]
    buttons = reply["reply_markup"]["inline_keyboard"][0]
    assert buttons == [
        {"text": "Alpacaで口座開設する", "url": ALPACA_SIGNUP_URL},
        {"text": "今はしない", "callback_data": "invest:later"},
    ]


def test_known_account_status_never_reopens_signup(tmp_path):
    _write(tmp_path / "alpaca-investment" / "account-status.json", {"application_status": "in_review"})

    reply = build_investment_reply(tmp_path)

    assert "審査中" in reply["text"]
    assert "reply_markup" not in reply


def test_running_bot_registers_invest_command():
    source = (SCRIPTS / "telegram_bot.py").read_text(encoding="utf-8")

    assert 'CommandHandler("invest", cmd_invest)' in source
    assert '"  /invest   show investment setup and loop status' in source
    assert "build_investment_reply" in source
