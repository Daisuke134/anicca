#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

import market_product_contract

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "crowdworks_product_qualification.schema.json"


def _sha(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(product: dict, value: dict) -> dict:
    canonical = market_product_contract.canonical_contract(product)
    if product.get("contract_sha256") != canonical["contract_sha256"]:
        raise ValueError("product contract SHA mismatch")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda row: list(row.path))
    if errors:
        raise ValueError(errors[0].message)
    if (value["product_key"] != product["product_key"]
            or value["product_contract_sha256"] != canonical["contract_sha256"]
            or value["mapping"]["buyer_job"] != product["buyer_job"]
            or value["mapping"]["delivery_kind"] != product["delivery_kind"]
            or value["mapping"]["gross_price"] != product["base_price"]):
        raise ValueError("CrowdWorks mapping changes product truth")
    rates = sorted(row["rate_percent"] for row in value["fees"]["tiers"])
    if rates != [5, 10, 20] or sorted(value["fees"]["transfer_fee_jpy"]) != [100, 500]:
        raise ValueError("CrowdWorks fee schedule mismatch")
    serialized = json.dumps(value, ensure_ascii=False).lower()
    if "coconala" in serialized:
        raise ValueError("CrowdWorks qualification inherits Coconala evidence")
    return value


def persist(value: dict, output: Path) -> tuple[bool, str]:
    body = dict(value)
    body.pop("qualification_sha256", None)
    digest = _sha(body)
    encoded = (json.dumps({**body, "qualification_sha256": digest}, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if output.exists() and output.read_bytes() == encoded:
        return False, digest
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True, digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    product = json.loads(args.product.read_text(encoding="utf-8"))
    value = validate(product, json.loads(args.input.read_text(encoding="utf-8")))
    changed, digest = persist(value, args.output)
    print(json.dumps({"ok": True, "changed": changed, "qualification_sha256": digest}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
