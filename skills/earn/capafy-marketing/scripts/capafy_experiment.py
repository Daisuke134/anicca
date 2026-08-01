#!/usr/bin/env python3
"""Validate and activate one bounded Capafy packaging experiment."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import capafy_portfolio as portfolio
from capafy_event_store import append_event


FIELDS = {
    "schema_version", "kind", "portfolio_source_digest", "experiment_id", "agent_id",
    "owner", "purchase_model", "price_usd", "billing_interval", "metered_unit",
    "bounded_deliverable", "value_metric", "renewal_reason", "projected_units",
    "platform_fee_rate", "model_cost_per_unit_usd", "projected_gross_usd",
    "projected_platform_fee_usd", "projected_cost_usd", "projected_contribution_usd",
    "observed_gross_usd", "observed_cost_usd", "observed_contribution_usd",
    "success_metric", "stop_condition", "activated_at", "evidence",
}
MONEY = re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$")
RATE = re.compile(r"^(?:0|1)\.[0-9]{4}$")
MODELS = {"subscription", "usage", "one_time", "hybrid"}


def _money(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not MONEY.fullmatch(value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_proposal(snapshot: dict, value: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != FIELDS:
        return ["proposal has unsupported or missing fields"]
    if value.get("schema_version") != 1 or value.get("kind") != "capafy_packaging_experiment":
        errors.append("proposal identity is invalid")
    if value.get("portfolio_source_digest") != portfolio.snapshot_digest(snapshot):
        errors.append("portfolio source digest does not match")
    if not _text(value.get("experiment_id")):
        errors.append("experiment_id is required")
    if value.get("owner") not in {"builder", "marketer"}:
        errors.append("owner is invalid")
    model = value.get("purchase_model")
    if model not in MODELS:
        errors.append("purchase_model is invalid")
    products = {product["agent_id"]: product for product in snapshot.get("products", [])}
    selected = products.get(value.get("agent_id"))
    eligible = [
        product for product in products.values()
        if product.get("observed_status") == "online"
        and product.get("decision") == "promote"
        and bool(product.get("evidence"))
    ]
    if selected not in eligible:
        errors.append("agent_id is not evidence-eligible")
    elif len(selected.get("evidence", [])) < max(len(p.get("evidence", [])) for p in eligible):
        errors.append("agent_id is not in the highest-evidence eligible tier")
    for field in ("value_metric", "success_metric", "stop_condition"):
        if not _text(value.get(field)):
            errors.append(f"{field} is required")
    if model in {"subscription", "hybrid"}:
        if value.get("billing_interval") not in {"day", "week", "month"}:
            errors.append("billing_interval is required for recurring packaging")
        if not _text(value.get("renewal_reason")):
            errors.append("renewal_reason is required for recurring packaging")
    elif value.get("billing_interval") is not None or value.get("renewal_reason") is not None:
        errors.append("billing_interval and renewal_reason must be null for this model")
    if model in {"usage", "hybrid"}:
        if not _text(value.get("metered_unit")):
            errors.append("metered_unit is required for usage packaging")
    elif value.get("metered_unit") is not None:
        errors.append("metered_unit must be null for this model")
    if model in {"one_time", "hybrid"}:
        if not _text(value.get("bounded_deliverable")):
            errors.append("bounded_deliverable is required for one-time packaging")
    elif value.get("bounded_deliverable") is not None:
        errors.append("bounded_deliverable must be null for this model")
    price = _money(value.get("price_usd"))
    cost_per_unit = _money(value.get("model_cost_per_unit_usd"))
    units = value.get("projected_units")
    rate_text = value.get("platform_fee_rate")
    rate = Decimal(rate_text) if isinstance(rate_text, str) and RATE.fullmatch(rate_text) else None
    if price is None or price <= 0:
        errors.append("price_usd must be a positive two-decimal string")
    if cost_per_unit is None:
        errors.append("model_cost_per_unit_usd must be a non-negative two-decimal string")
    elif model in {"subscription", "usage", "hybrid"} and cost_per_unit == 0:
        errors.append("actual compute cost must be known and positive for cloud execution")
    if isinstance(units, bool) or not isinstance(units, int) or units <= 0:
        errors.append("projected_units must be a positive integer")
    if rate is None or rate < 0 or rate > 1:
        errors.append("platform_fee_rate must be 0.0000 through 1.0000")
    for field in (
        "projected_gross_usd", "projected_platform_fee_usd", "projected_cost_usd",
        "projected_contribution_usd",
    ):
        if _money(value.get(field)) is None:
            errors.append(f"{field} must be a non-negative two-decimal string")
    for field in ("observed_gross_usd", "observed_cost_usd", "observed_contribution_usd"):
        if value.get(field) is not None and _money(value[field]) is None:
            errors.append(f"{field} must be a two-decimal string or null")
    if price is not None and cost_per_unit is not None and isinstance(units, int) and units > 0 and rate is not None:
        gross = _quantize(price * units)
        fee = _quantize(gross * rate)
        cost = _quantize(cost_per_unit * units)
        expected = {
            "projected_gross_usd": gross,
            "projected_platform_fee_usd": fee,
            "projected_cost_usd": cost,
            "projected_contribution_usd": _quantize(gross - fee - cost),
        }
        for field, expected_value in expected.items():
            actual = _money(value.get(field))
            if actual != expected_value:
                errors.append(f"{field} does not match exact unit economics")
    if not portfolio._utc(value.get("activated_at")):
        errors.append("activated_at is invalid")
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or len(evidence) < 2:
        errors.append("evidence must cite both fee and product positioning")
    else:
        for index, proof in enumerate(evidence):
            if not isinstance(proof, dict) or not portfolio._https(proof.get("url")):
                errors.append(f"evidence[{index}].url must be HTTPS")
            if not isinstance(proof, dict) or not portfolio._utc(proof.get("observed_at")):
                errors.append(f"evidence[{index}].observed_at is invalid")
            if not isinstance(proof, dict) or not _text(proof.get("claim")):
                errors.append(f"evidence[{index}].claim is required")
            if not isinstance(proof, dict) or proof.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"evidence[{index}].confidence is invalid")
    return errors


def activate(snapshot: dict, proposal: dict) -> dict:
    active = [
        p for p in snapshot.get("products", [])
        if isinstance(p.get("experiment"), dict)
        and p["experiment"].get("status") in {"proposed", "active"}
    ]
    if active:
        raise ValueError("existing experiment must be measured before replacement")
    errors = validate_proposal(snapshot, proposal)
    if errors:
        raise ValueError("; ".join(errors))
    result = copy.deepcopy(snapshot)
    for product in result["products"]:
        if product["agent_id"] != proposal["agent_id"]:
            continue
        product["purchase_model"] = proposal["purchase_model"]
        product["value_metric"] = proposal["value_metric"]
        product["renewal_reason"] = proposal["renewal_reason"]
        product["experiment"] = {
            key: copy.deepcopy(value)
            for key, value in proposal.items()
            if key not in {"schema_version", "kind", "portfolio_source_digest", "agent_id"}
        }
        product["experiment"]["status"] = "active"
    validation = portfolio.validate_snapshot(result)
    if validation:
        raise ValueError("activated portfolio is invalid: " + "; ".join(validation))
    return result


def repair_invalid_activation(snapshot: dict, proposal: dict) -> dict:
    """Remove only the matching invalid active proposal and restore unknown fields."""
    if not validate_proposal(snapshot, proposal):
        raise ValueError("proposal is valid; repair is not permitted")
    result = copy.deepcopy(snapshot)
    repaired = False
    for product in result.get("products", []):
        active = product.get("experiment")
        if (
            product.get("agent_id") == proposal.get("agent_id")
            and isinstance(active, dict)
            and active.get("experiment_id") == proposal.get("experiment_id")
            and active.get("status") == "active"
        ):
            product["experiment"] = None
            product["purchase_model"] = "undecided"
            product["value_metric"] = None
            product["renewal_reason"] = None
            repaired = True
    if not repaired:
        raise ValueError("matching invalid active experiment was not found")
    validation = portfolio.validate_snapshot(result)
    if validation:
        raise ValueError("repaired portfolio is invalid: " + "; ".join(validation))
    return result


def activation_event(proposal: dict, recorded_at: str) -> dict:
    event_id = f"capafy:experiment.activated:{proposal['experiment_id']}"
    zero_money = {
        "currency": "USD", "gross_delta": "0.00", "pending_delta": "0.00",
        "realized_delta": "0.00", "mrr_delta": "0.00", "cost_delta": "0.00",
        "contribution_delta": "0.00",
    }
    urls = list(dict.fromkeys(proof["url"] for proof in proposal["evidence"]))
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": "experiment.activated",
        "occurred_at": proposal["activated_at"],
        "recorded_at": recorded_at,
        "loop": "capafy",
        "entity": {"type": "experiment", "id": proposal["experiment_id"]},
        "correlation_id": proposal["agent_id"],
        "summary": f"Activated one bounded {proposal['purchase_model']} packaging experiment for seller-owned product {proposal['agent_id']}",
        "status": {"before": None, "after": "active"},
        "money": zero_money,
        "metrics": {},
        "public_evidence": {
            "urls": urls,
            "labels": [
                f"price hypothesis ${proposal['price_usd']}",
                f"projected contribution ${proposal['projected_contribution_usd']}; not realized revenue",
                f"stop condition: {proposal['stop_condition']}",
            ],
        },
        "technical_evidence_ref": event_id,
        "source": {
            "producer": "capafy_experiment.py",
            "source_id": proposal["experiment_id"],
            "source_digest": portfolio._digest(proposal),
        },
        "next": {"owner": proposal["owner"], "retry_at": None},
    }


def _atomic_write(path: Path, value: dict) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode() + b"\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path); os.chmod(path, 0o600)
    finally:
        if temporary.exists(): temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--repair-invalid", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.portfolio.read_text())
        proposal = json.loads(args.proposal.read_text())
        if bool(args.ledger) != bool(args.evidence_dir):
            raise ValueError("--ledger and --evidence-dir must be supplied together")
        matching_active = any(
            isinstance(product.get("experiment"), dict)
            and product["experiment"].get("experiment_id") == proposal.get("experiment_id")
            and product["experiment"].get("status") == "active"
            for product in snapshot.get("products", [])
        )
        if matching_active and not args.repair_invalid:
            result = snapshot
        else:
            result = (
                repair_invalid_activation(snapshot, proposal)
                if args.repair_invalid
                else activate(snapshot, proposal)
            )
            _atomic_write(args.portfolio, result)
        if args.ledger and not args.repair_invalid:
            recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            append_event(args.ledger, activation_event(proposal, recorded_at), proposal, args.evidence_dir)
        print(json.dumps({"valid": True, "repaired": args.repair_invalid, "experiment_id": proposal["experiment_id"], "agent_id": proposal["agent_id"]}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
