#!/usr/bin/env python3
"""Validate and apply one complete evidence-backed Capafy portfolio audit."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import capafy_portfolio as portfolio


AUDIT_TOP_FIELDS = {
    "schema_version", "kind", "portfolio_source_digest", "audited_at", "products"
}
AUDIT_PRODUCT_FIELDS = {
    "agent_id", "recurring_mechanism", "purchase_model", "value_metric",
    "target_customer", "next_best_alternative", "renewal_reason", "decision",
    "decision_reason", "unknowns", "evidence",
}
AUTHORED_FIELDS = {
    "recurring_mechanism", "purchase_model", "value_metric", "target_customer",
    "next_best_alternative", "renewal_reason", "decision",
}
OBSERVED_PRODUCT_FIELDS = {
    "agent_id", "name", "description", "product_type", "observed_status",
    "updated_at", "public_url", "platform_sales", "unit_economics", "experiment",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _validate_evidence(prefix: str, evidence: Any) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    supported: set[str] = set()
    if not isinstance(evidence, list) or not evidence:
        return [f"{prefix}.evidence must be a non-empty list"], supported
    for index, item in enumerate(evidence):
        ep = f"{prefix}.evidence[{index}]"
        if not isinstance(item, dict) or set(item) != {
            "url", "observed_at", "claim", "confidence", "supports"
        }:
            errors.append(f"{ep} has invalid fields")
            continue
        if not portfolio._https(item.get("url")):
            errors.append(f"{ep}.url must be HTTPS")
        if not portfolio._utc(item.get("observed_at")):
            errors.append(f"{ep}.observed_at is invalid")
        if item.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"{ep}.confidence is invalid")
        if not isinstance(item.get("claim"), str) or not item["claim"].strip():
            errors.append(f"{ep}.claim is required")
        supports = item.get("supports")
        if not isinstance(supports, list) or not supports or any(
            field not in AUTHORED_FIELDS for field in supports
        ):
            errors.append(f"{ep}.supports is invalid")
        else:
            supported.update(supports)
    return errors, supported


def validate_audit(snapshot: dict, audit: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(audit, dict):
        return ["audit must be an object"]
    if set(audit) != AUDIT_TOP_FIELDS:
        errors.append("audit has unsupported or missing top-level fields")
    if audit.get("schema_version") != 1 or audit.get("kind") != "capafy_portfolio_audit":
        errors.append("audit identity is invalid")
    if audit.get("portfolio_source_digest") != portfolio.snapshot_digest(snapshot):
        errors.append("portfolio source digest does not match")
    if not portfolio._utc(audit.get("audited_at")):
        errors.append("audited_at is invalid")
    products = audit.get("products")
    expected_ids = [product["agent_id"] for product in snapshot.get("products", [])]
    if not isinstance(products, list):
        return errors + ["products must be a list"]
    received_ids = [item.get("agent_id") for item in products if isinstance(item, dict)]
    if len(received_ids) != len(set(received_ids)):
        errors.append("audit contains duplicate agent_id")
    if sorted(received_ids) != sorted(expected_ids):
        errors.append("audit must contain exactly one result for every portfolio product")
    for index, item in enumerate(products):
        prefix = f"products[{index}]"
        if not isinstance(item, dict) or set(item) != AUDIT_PRODUCT_FIELDS:
            errors.append(f"{prefix} has unsupported or missing fields")
            continue
        if item.get("recurring_mechanism") is not None and item["recurring_mechanism"] not in portfolio.RECURRING:
            errors.append(f"{prefix}.recurring_mechanism is invalid")
        if item.get("purchase_model") not in portfolio.PURCHASE_MODELS:
            errors.append(f"{prefix}.purchase_model is invalid")
        if item.get("decision") not in portfolio.DECISIONS - {"unaudited"}:
            errors.append(f"{prefix}.decision is invalid")
        unknowns = item.get("unknowns")
        if not isinstance(unknowns, list) or not unknowns or any(
            not isinstance(value, str) or not value.strip() for value in unknowns
        ):
            errors.append(f"{prefix}.unknowns must explicitly name unresolved facts")
        evidence_errors, supported = _validate_evidence(prefix, item.get("evidence"))
        errors.extend(evidence_errors)
        for field in AUTHORED_FIELDS:
            value = item.get(field)
            is_asserted = (
                value is not None
                and not (field == "purchase_model" and value == "undecided")
            )
            if is_asserted and field not in supported:
                errors.append(f"{prefix}.{field} lacks field-specific evidence")
        if not isinstance(item.get("decision_reason"), str) or not item["decision_reason"].strip():
            errors.append(f"{prefix}.decision_reason is required")
    return errors


def apply_audit(snapshot: dict, audit: dict) -> dict:
    errors = validate_audit(snapshot, audit)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = {item["agent_id"]: item for item in audit["products"]}
    result = copy.deepcopy(snapshot)
    result["observed_at"] = audit["audited_at"]
    for product in result["products"]:
        item = by_id[product["agent_id"]]
        for field in AUDIT_PRODUCT_FIELDS - {"agent_id"}:
            product[field] = copy.deepcopy(item[field])
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
            stream.write(_canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
        value = json.loads(args.audit.read_text(encoding="utf-8"))
        result = apply_audit(snapshot, value)
        destination = args.output or args.portfolio
        _atomic_write(destination, result)
        print(json.dumps({"valid": True, "product_count": len(result["products"])}))
        return 0
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
