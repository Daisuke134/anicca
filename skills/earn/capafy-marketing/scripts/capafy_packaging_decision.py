#!/usr/bin/env python3
"""Validate and apply one evidence-bound Capafy packaging decision."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import capafy_portfolio as portfolio


FIELDS = {
    "schema_version", "kind", "portfolio_source_digest", "remote_source_digest",
    "decided_at", "agent_id", "provider_name", "provider_model",
    "purchase_model", "price_usd", "billing_interval", "included_units", "metered_unit",
    "bounded_deliverable", "value_metric", "renewal_reason", "platform_fee_rate",
    "input_tokens_per_unit", "output_tokens_per_unit", "input_price_per_million_usd",
    "output_price_per_million_usd", "compute_assumption", "gross_usd",
    "platform_fee_usd", "cost_usd", "contribution_usd", "resolved_unknowns", "evidence",
}
EVIDENCE_FIELDS = {"url", "observed_at", "claim", "confidence", "supports"}
SUPPORTS = {
    "purchase_model", "price_usd", "included_units", "value_metric", "renewal_reason",
    "platform_fee_rate", "model_pricing", "bounded_deliverable",
}
MONEY = re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$")
RATE = re.compile(r"^(?:0|1)\.[0-9]{4}$")
MODELS = {"subscription", "usage", "one_time", "hybrid"}
GOOGLE_PROVIDER = "publisher_google_official"
GOOGLE_MODEL = "gemini-3.5-flash-lite"


def _money(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not MONEY.fullmatch(value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def remote_fact(remote: dict) -> dict:
    latest = remote.get("latest_version") if isinstance(remote, dict) else None
    if not isinstance(latest, dict):
        return {}
    credentials = latest.get("requiredCredentials")
    if isinstance(credentials, str):
        try:
            credentials = json.loads(credentials)
        except json.JSONDecodeError:
            credentials = {}
    if not isinstance(credentials, dict):
        credentials = {}
    url_proxies = credentials.get("url_proxy")
    if not isinstance(url_proxies, list):
        url_proxies = []
    generic_credentials = credentials.get("generic")
    if not isinstance(generic_credentials, list):
        generic_credentials = []
    billings = latest.get("billings")
    if not isinstance(billings, list):
        billings = []
    providers = []
    for item in url_proxies:
        if not isinstance(item, dict):
            continue
        providers.append({
            key: item.get(key)
            for key in ("provider_name", "vendor_name", "model", "api_format")
        })
    providers.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return {
        "agent_id": str(latest.get("agentId") or ""),
        "product_type": latest.get("agentType"),
        "status": latest.get("status"),
        "billings": [
            {
                "billing_mode": item.get("billingMode"),
                "cycle_type": item.get("cycleType"),
                "cycle_price": item.get("cyclePrice"),
                "one_time_fee": item.get("oneTimeFee"),
                "included_units": item.get("cycleMaxMessageCount"),
                "currency": item.get("currency"),
            }
            for item in billings
            if isinstance(item, dict)
        ],
        "providers": providers,
        "generic_credential_count": len([
            item for item in generic_credentials if isinstance(item, dict)
        ]),
    }


def remote_source_digest(remote: dict) -> str:
    payload = json.dumps(
        remote_fact(remote), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _configured_billing_matches(fact: dict, value: dict) -> bool:
    price = _money(value.get("price_usd"))
    units = value.get("included_units")
    if price is None or not _positive_int(units):
        return False
    for billing in fact.get("billings", []):
        if value.get("purchase_model") == "subscription":
            remote_price = billing.get("cycle_price")
            try:
                same_price = Decimal(str(remote_price)) == price
            except InvalidOperation:
                same_price = False
            if (
                billing.get("billing_mode") == "subscription"
                and billing.get("cycle_type") == value.get("billing_interval")
                and billing.get("included_units") == units
                and same_price
            ):
                return True
        elif value.get("purchase_model") == "one_time":
            remote_price = billing.get("one_time_fee")
            try:
                same_price = Decimal(str(remote_price)) == price
            except InvalidOperation:
                same_price = False
            if billing.get("billing_mode") == "one_time" and units == 1 and same_price:
                return True
    return False


def validate_decision(snapshot: dict, value: dict, remote: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != FIELDS:
        return ["decision has unsupported or missing fields"]
    if value.get("schema_version") != 1 or value.get("kind") != "capafy_packaging_decision":
        errors.append("decision identity is invalid")
    if value.get("portfolio_source_digest") != portfolio.snapshot_digest(snapshot):
        errors.append("portfolio source digest does not match")
    fact = remote_fact(remote)
    if value.get("remote_source_digest") != remote_source_digest(remote):
        errors.append("remote source digest does not match")
    if fact.get("agent_id") != value.get("agent_id"):
        errors.append("remote agent_id does not match")
    if fact.get("product_type") != "run_online" or fact.get("status") != 4:
        errors.append("remote product is not an online hosted Agent")
    providers = fact.get("providers", [])
    if len(providers) != 1:
        errors.append("remote product must expose exactly one hosted provider")
        provider = {}
    else:
        provider = providers[0]
    if provider.get("provider_name") != value.get("provider_name"):
        errors.append("declared provider name does not match remote provider")
    if provider.get("model") != value.get("provider_model"):
        errors.append("declared provider model does not match remote provider model")
    if provider.get("vendor_name") == "OpenRouter" or provider.get("provider_name") != GOOGLE_PROVIDER:
        errors.append("OpenRouter or unsupported hosted provider must be migrated before packaging")
    if provider.get("model") != GOOGLE_MODEL or provider.get("api_format") != "google-generative-ai":
        errors.append("remote provider model is unsupported for Google pricing")
    if fact.get("generic_credential_count") != 0:
        errors.append("remote product has ambiguous generic credentials")
    if not _configured_billing_matches(fact, value):
        errors.append("decision does not match any configured billing package")
    if not portfolio._utc(value.get("decided_at")):
        errors.append("decided_at is invalid")

    products = {item["agent_id"]: item for item in snapshot.get("products", [])}
    selected = products.get(value.get("agent_id"))
    if not isinstance(selected, dict) or selected.get("observed_status") != "online" or selected.get("decision") != "promote":
        errors.append("agent_id is not an online promoted evidence-eligible product")
    elif not selected.get("evidence"):
        errors.append("agent_id is not an online promoted evidence-eligible product")
    elif selected.get("purchase_model") != "undecided":
        errors.append("selected product purchase_model must still be undecided")
    elif isinstance(selected.get("experiment"), dict) and selected["experiment"].get("status") in {"proposed", "active"}:
        errors.append("selected product has an unresolved experiment")

    model = value.get("purchase_model")
    if model not in MODELS:
        errors.append("purchase_model is invalid")
    for field in ("metered_unit", "value_metric", "compute_assumption"):
        if not _text(value.get(field)):
            errors.append(f"{field} is required")
    if model in {"subscription", "hybrid"}:
        if value.get("billing_interval") not in {"day", "week", "month"}:
            errors.append("billing_interval is required for recurring packaging")
        if not _text(value.get("renewal_reason")):
            errors.append("renewal_reason is required for recurring packaging")
    elif value.get("billing_interval") is not None or value.get("renewal_reason") is not None:
        errors.append("billing_interval and renewal_reason must be null for non-recurring packaging")
    if model in {"one_time", "hybrid"}:
        if not _text(value.get("bounded_deliverable")):
            errors.append("bounded_deliverable is required for one-time packaging")
    elif value.get("bounded_deliverable") is not None:
        errors.append("bounded_deliverable must be null for this purchase model")

    price = _money(value.get("price_usd"))
    input_rate = _money(value.get("input_price_per_million_usd"))
    output_rate = _money(value.get("output_price_per_million_usd"))
    rate_text = value.get("platform_fee_rate")
    fee_rate = Decimal(rate_text) if isinstance(rate_text, str) and RATE.fullmatch(rate_text) else None
    if price is None or price <= 0:
        errors.append("price_usd must be a positive two-decimal string")
    if input_rate is None or output_rate is None:
        errors.append("model prices must be non-negative two-decimal strings")
    elif input_rate != Decimal("0.30") or output_rate != Decimal("2.50"):
        errors.append("model prices do not match the supported Google provider")
    if fee_rate is None:
        errors.append("platform_fee_rate must be 0.0000 through 1.0000")
    elif fee_rate != Decimal("0.2000"):
        errors.append("platform_fee_rate must match the official 0.2000 fee")
    units = value.get("included_units")
    input_tokens = value.get("input_tokens_per_unit")
    output_tokens = value.get("output_tokens_per_unit")
    if not _positive_int(units):
        errors.append("included_units must be a positive integer")
    if not _nonnegative_int(input_tokens) or not _nonnegative_int(output_tokens):
        errors.append("token assumptions must be non-negative integers")
    elif input_tokens + output_tokens == 0 and model != "one_time":
        errors.append("hosted packaging requires a positive compute assumption")

    for field in ("gross_usd", "platform_fee_usd", "cost_usd", "contribution_usd"):
        if _money(value.get(field)) is None:
            errors.append(f"{field} must be a non-negative two-decimal string")
    if (
        price is not None and input_rate is not None and output_rate is not None
        and fee_rate is not None and _positive_int(units)
        and _nonnegative_int(input_tokens) and _nonnegative_int(output_tokens)
    ):
        gross = price
        fee = _quantize(gross * fee_rate)
        raw_unit_cost = (
            Decimal(input_tokens) * input_rate + Decimal(output_tokens) * output_rate
        ) / Decimal(1_000_000)
        cost = _quantize(raw_unit_cost * Decimal(units))
        expected = {
            "gross_usd": gross,
            "platform_fee_usd": fee,
            "cost_usd": cost,
            "contribution_usd": _quantize(gross - fee - cost),
        }
        for field, expected_value in expected.items():
            if _money(value.get(field)) != expected_value:
                errors.append(f"{field} does not match exact package economics")

    resolved = value.get("resolved_unknowns")
    if not isinstance(resolved, list) or not resolved or any(not _text(item) for item in resolved):
        errors.append("resolved_unknowns must be a non-empty list")
    elif selected is not None and not set(resolved).issubset(set(selected.get("unknowns", []))):
        errors.append("resolved_unknowns must be an exact subset of the selected product unknowns")

    supported: set[str] = set()
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
    else:
        for index, item in enumerate(evidence):
            prefix = f"evidence[{index}]"
            if not isinstance(item, dict) or set(item) != EVIDENCE_FIELDS:
                errors.append(f"{prefix} has unsupported or missing fields")
                continue
            if not portfolio._https(item.get("url")):
                errors.append(f"{prefix}.url must be HTTPS")
            if not portfolio._utc(item.get("observed_at")):
                errors.append(f"{prefix}.observed_at is invalid")
            if not _text(item.get("claim")):
                errors.append(f"{prefix}.claim is required")
            if item.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"{prefix}.confidence is invalid")
            supports = item.get("supports")
            if not isinstance(supports, list) or not supports or any(field not in SUPPORTS for field in supports):
                errors.append(f"{prefix}.supports is invalid")
            else:
                supported.update(supports)
    required_support = {
        "purchase_model", "price_usd", "included_units", "value_metric",
        "platform_fee_rate", "model_pricing",
    }
    if model in {"subscription", "hybrid"}:
        required_support.add("renewal_reason")
    if model in {"one_time", "hybrid"}:
        required_support.add("bounded_deliverable")
    for field in sorted(required_support - supported):
        errors.append(f"{field} lacks field-specific evidence")
    return errors


def apply_decision(snapshot: dict, value: dict, remote: dict) -> dict:
    errors = validate_decision(snapshot, value, remote)
    if errors:
        raise ValueError("; ".join(errors))
    result = copy.deepcopy(snapshot)
    result["observed_at"] = value["decided_at"]
    for item in result["products"]:
        if item["agent_id"] != value["agent_id"]:
            continue
        item["purchase_model"] = value["purchase_model"]
        item["value_metric"] = value["value_metric"]
        item["renewal_reason"] = value["renewal_reason"]
        item["unit_economics"] = {
            "gross_usd": value["gross_usd"],
            "cost_usd": value["cost_usd"],
            "contribution_usd": value["contribution_usd"],
        }
        item["unknowns"] = [
            unknown for unknown in item["unknowns"] if unknown not in set(value["resolved_unknowns"])
        ]
        item["evidence"].extend(copy.deepcopy(value["evidence"]))
    validation = portfolio.validate_snapshot(result)
    if validation:
        raise ValueError("applied portfolio is invalid: " + "; ".join(validation))
    return result


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--remote-json", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
        value = json.loads(args.decision.read_text(encoding="utf-8"))
        remote = json.loads(args.remote_json.read_text(encoding="utf-8"))
        result = apply_decision(snapshot, value, remote)
        _atomic_write(args.output or args.portfolio, result)
        print(json.dumps({"valid": True, "agent_id": value["agent_id"]}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
