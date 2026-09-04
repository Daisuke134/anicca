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
    def money(value: Decimal) -> str:
        return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"

    equity = Decimal(str(observation["account"]["equity"]))
    cash = Decimal(str(observation["account"]["cash"]))
    change = equity - Decimal("100000")
    realized = campaign.get("realized_pnl_usd")
    realized_text = f"確定損益 {money(Decimal(realized))}、" if realized is not None else ""
    effect_text = "注文なし" if effect == "none" else f"paper効果 {effect[:12]}"
    return (
        "Codex::: Alpaca paper投資loopの1回分です。"
        f"判断は {decision['candidate_ref']}（{decision['gate']}）。"
        f"資産は {money(equity)}、現金は {money(cash)}、開始時$100,000から {money(change)}。"
        f"{realized_text}含み損益 {money(Decimal(campaign['unrealized_pnl_usd']))}、"
        f"保有ポジション {len(observation['positions'])}件、{effect_text}。"
        f"観測時刻 {decision['observed_at']}。"
    )


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


def render_failure(*, stage: str, effect_uncertain: bool, wake_id: str) -> str:
    effect_text = (
        "paper注文を送信した可能性があるため、自動再試行せず次回wakeでbroker照合します。"
        if effect_uncertain else
        "paper注文の送信前に停止したため、注文は実行していません。"
    )
    return (
        "Codex::: Alpaca paper投資loopの1回分です。"
        f"処理段階 {stage} で安全に完了できなかったため、今回の判断結果を確定できませんでした。"
        f"{effect_text}原因の詳細は秘密情報を含む可能性があるため送信していません。"
        f"観測開始時刻 {wake_id}。"
    )


def deliver_failure(state: Path, *, stage: str, effect_uncertain: bool,
                    wake_id: str) -> dict[str, Any]:
    return _deliver_message(
        state,
        f"alpaca-failure:{wake_id}",
        render_failure(stage=stage, effect_uncertain=effect_uncertain, wake_id=wake_id),
        wake_id,
    )
