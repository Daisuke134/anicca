"""One durable, owner-readable Telegram report per Alpaca wake."""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]


def _load_outbox():
    path = REPO / "skills/_shared/marketplace-core/scripts/telegram_outbox.py"
    spec = importlib.util.spec_from_file_location("lm_telegram_outbox", path)
    if spec is None or spec.loader is None:
        raise ValueError("telegram_outbox_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _telegram_client():
    import sys
    sys.path.insert(0, str(REPO))
    from skills._shared.telegram import TelegramClient

    environment = dict(os.environ)
    state_env = Path(os.environ.get(
        "LIFE_MANAGER_ENV_FILE", "~/.local/state/life-manager/.env")).expanduser()
    for key, value in _env_file(state_env).items():
        environment.setdefault(key, value)
    target = (environment.get("TELEGRAM_ALERT_CHAT_ID")
              or environment.get("LM_TELEGRAM_ALERT_CHAT_ID")
              or environment.get("TELEGRAM_CHAT_ID"))
    if not target:
        raise ValueError("telegram_target_missing")
    environment["TELEGRAM_CHAT_ID"] = target
    return TelegramClient.from_env(environ=environment, env_file=state_env), target


def render(observation: dict[str, Any], campaign: dict[str, Any],
           decision: dict[str, Any], effect: str) -> str:
    mode = decision.get("mode", "unknown")
    def money(value: Decimal) -> str:
        return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"

    equity = Decimal(str(observation["account"]["equity"]))
    cash = Decimal(str(observation["account"]["cash"]))
    change = equity - Decimal("100000")
    baseline_text = f"、開始時$100,000から {money(change)}" if mode == "paper" else ""
    realized = campaign.get("realized_pnl_usd")
    realized_text = f"確定損益 {money(Decimal(realized))}、" if realized is not None else ""
    effect_text = "注文なし" if effect == "none" else f"{mode}効果 {effect[:12]}"
    heading = "⏭️ 今回は投資しませんでした" if effect == "none" else "✅ 投資注文を実行しました"
    return "\n".join((
        "[Investment Loop][投資判断]",
        heading,
        "",
        f"モード: {mode}",
        f"判断: {decision['candidate_ref']}（{decision['gate']}）",
        f"理由: {decision.get('reason') or '理由は記録されていません'}",
        f"資産: {money(equity)}",
        f"現金: {money(cash)}{baseline_text}",
        f"損益: {realized_text}含み損益 {money(Decimal(campaign['unrealized_pnl_usd']))}",
        f"保有: {len(observation['positions'])}件",
        f"注文: {effect_text}",
        f"観測時刻: {decision['observed_at']}",
        "",
        "次に自動で行うこと",
        "5分後に市場と口座を再確認します。",
        "ユーザーの操作は必要ありません。",
    ))


def _deliver_message(state: Path, event_key: str, message: str,
                     observed_at: str) -> dict[str, Any]:
    outbox = _load_outbox()
    database = state / "telegram-outbox.sqlite3"
    inserted = outbox.enqueue(database, event_key, message, observed_at)
    if not inserted:
        item = next((row for row in outbox.list_items(database)
                     if row.event_key == event_key), None)
        if item and item.status == "delivered" and item.provider_message_id:
            return {"message_id": item.provider_message_id, "status": "delivered"}
        raise ValueError("telegram_prior_delivery_unconfirmed")
    claimed = outbox.claim_next(database)
    if claimed is None or claimed.event_key != event_key:
        raise ValueError("telegram_outbox_claim_failed")
    try:
        client, target = _telegram_client()
        response = client.send_text(message, chat_id=target)
    except Exception as error:
        outbox.mark_delivery_uncertain(database, event_key, type(error).__name__)
        raise ValueError("telegram_delivery_unconfirmed") from error
    ids = response.get("message_ids") if isinstance(response, dict) else None
    message_id = ids[0] if isinstance(ids, list) and len(ids) == 1 else None
    if isinstance(message_id, bool) or not isinstance(message_id, (str, int)):
        outbox.mark_delivery_uncertain(database, event_key, "message_id_missing")
        raise ValueError("telegram_message_id_missing")
    delivered_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    outbox.mark_delivered(database, event_key, str(message_id), delivered_at)
    receipt = {"event_key": event_key, "message_id": str(message_id),
               "status": "delivered", "delivered_at": delivered_at}
    path = state / "telegram-latest.json"
    path.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
    path.chmod(0o600)
    return receipt


def deliver(state: Path, observation: dict[str, Any], campaign: dict[str, Any],
            decision: dict[str, Any], effect: str) -> dict[str, Any]:
    observed_at = decision["observed_at"]
    return _deliver_message(
        state,
        f"alpaca-wake:{observed_at}",
        render(observation, campaign, decision, effect),
        observed_at,
    )


def render_failure(*, stage: str, effect_uncertain: bool, wake_id: str,
                   financial_text: str = "", mode: str = "unknown") -> str:
    effect_text = (
        f"{mode}注文を送信した可能性があるため、自動再試行せず次回wakeでbroker照合します。"
        if effect_uncertain else
        f"{mode}注文の送信前に停止したため、注文は実行していません。"
    )
    return "\n".join((
        "[Investment Loop][実行エラー]",
        "⚠️ 今回の投資判断を確定できませんでした",
        "",
        f"モード: {mode}",
        f"停止段階: {stage}",
        effect_text,
        financial_text,
        "原因の詳細は秘密情報を含む可能性があるため送信していません。",
        f"観測開始時刻: {wake_id}",
        "",
        "次に自動で行うこと",
        "5分後に安全な処理を再開します。",
        "ユーザーの操作は必要ありません。",
    ))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _latest_financial_text(state: Path, observation=None, campaign=None,
                           mode: str = "unknown") -> str:
    observation = observation or _read_json(state / "observation-latest.json")
    campaign = campaign or _read_json(state / "campaign.json")
    account = observation.get("account") if isinstance(observation.get("account"), dict) else {}
    campaign = campaign if isinstance(campaign, dict) else {}

    def decimal(value: Any):
        try:
            amount = Decimal(str(value))
            return amount if amount.is_finite() else None
        except (ValueError, TypeError, ArithmeticError):
            return None

    def money(amount) -> str:
        if amount is None:
            return "不明"
        return f"-${abs(amount):,.2f}" if amount < 0 else f"${amount:,.2f}"

    equity = decimal(account.get("equity"))
    cash = decimal(account.get("cash"))
    realized = decimal(campaign.get("realized_pnl_usd"))
    unrealized = decimal(campaign.get("unrealized_pnl_usd"))
    positions = observation.get("positions")
    position_count = f"{len(positions)}件" if isinstance(positions, list) else "不明"
    clock = observation.get("clock")
    observed_at = clock.get("observed_at", "不明") if isinstance(clock, dict) else "不明"
    delta = equity - Decimal("100000") if equity is not None else None
    baseline_text = f"、開始時$100,000から {money(delta)}" if mode == "paper" else ""
    return (
        f"利用可能な最新値（観測時刻 {observed_at}）：資産は {money(equity)}、"
        f"現金は {money(cash)}{baseline_text}。"
        f"確定損益 {money(realized)}、含み損益 {money(unrealized)}、"
        f"保有ポジション {position_count}。"
    )


def deliver_failure(state: Path, *, stage: str, effect_uncertain: bool,
                    wake_id: str, observation=None,
                    campaign=None, mode: str = "unknown") -> dict[str, Any]:
    return _deliver_message(
        state,
        f"alpaca-failure:{wake_id}",
        render_failure(
            stage=stage,
            effect_uncertain=effect_uncertain,
            wake_id=wake_id,
            mode=mode,
            financial_text=_latest_financial_text(state, observation, campaign, mode),
        ),
        wake_id,
    )
