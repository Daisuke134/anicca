import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from investment_status import build_investment_status


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
    message = build_investment_status(tmp_path)

    assert "状態をまだ確認できません" in message
    assert "ライブ注文は出しません" in message
    assert "最新状態をまだ読み取れません" in message


def test_running_bot_registers_invest_command():
    source = (SCRIPTS / "telegram_bot.py").read_text(encoding="utf-8")

    assert 'CommandHandler("invest", cmd_invest)' in source
    assert '"  /invest   show investment setup and loop status' in source
