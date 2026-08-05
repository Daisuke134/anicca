from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping


BOJ_RELEASE_PATTERN = re.compile(
    r"^https://www\.boj\.or\.jp/en/statistics/market/forex/fxdaily/"
    r"fxlist/fx(?P<date>\d{6})\.pdf$"
)
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
VALUE_KINDS = frozenset({"annual_base", "annual_total_compensation"})


class CompensationError(ValueError):
    pass


def _decimal(value: Any, *, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CompensationError(f"{name} must be numeric") from error
    if not parsed.is_finite() or parsed <= 0:
        raise CompensationError(f"{name} must be positive and finite")
    return parsed


def classify_six_figure_usd(
    *,
    value: Any,
    currency: Any,
    value_kind: str,
    rate_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    amount = _decimal(value, name="compensation value")
    source_currency = str(currency or "").upper()
    if source_currency not in {"JPY", "USD"}:
        raise CompensationError("currency must be JPY or USD")
    if value_kind not in VALUE_KINDS:
        raise CompensationError("value kind must be verified annual base or total compensation")
    if not isinstance(rate_evidence, Mapping):
        raise CompensationError("rate evidence is required")
    if rate_evidence.get("provider") != "Bank of Japan":
        raise CompensationError("rate provider must be Bank of Japan")
    release_url = str(rate_evidence.get("release_url") or "")
    match = BOJ_RELEASE_PATTERN.fullmatch(release_url)
    if match is None:
        raise CompensationError("rate release must be an official BOJ daily PDF")
    observation_date = str(rate_evidence.get("observation_date") or "")
    try:
        observed_day = date.fromisoformat(observation_date)
    except ValueError as error:
        raise CompensationError("rate observation date must be ISO-8601") from error
    if observed_day.strftime("%y%m%d") != match.group("date"):
        raise CompensationError("BOJ release URL date does not match observation date")
    if rate_evidence.get("observation_time_jst") != "17:00":
        raise CompensationError("BOJ rate must be observed at 17:00 JST")
    bid = _decimal(rate_evidence.get("usd_jpy_bid"), name="USD/JPY bid")
    offer = _decimal(rate_evidence.get("usd_jpy_offer"), name="USD/JPY offer")
    if offer < bid:
        raise CompensationError("USD/JPY offer must not be below bid")
    mid = ((bid + offer) / Decimal("2")).quantize(Decimal("0.01"))
    release_sha256 = str(rate_evidence.get("release_sha256") or "")
    if SHA256_PATTERN.fullmatch(release_sha256) is None:
        raise CompensationError("BOJ release SHA-256 is required")
    converted = amount if source_currency == "USD" else amount / mid
    converted = converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    receipt: dict[str, Any] = {
        "version": 1,
        "value": format(amount, "f"),
        "value_kind": value_kind,
        "period": "annual",
        "source_currency": source_currency,
        "target_currency": "USD",
        "converted_usd": format(converted, ".2f"),
        "six_figure_usd": converted >= Decimal("100000.00"),
        "rate_provider": "Bank of Japan",
        "rate_release_url": release_url,
        "rate_release_sha256": release_sha256,
        "rate_observed_at": f"{observation_date}T17:00:00+09:00",
        "usd_jpy_bid": format(bid, "f"),
        "usd_jpy_offer": format(offer, "f"),
        "usd_jpy_mid": format(mid, ".2f"),
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return receipt
