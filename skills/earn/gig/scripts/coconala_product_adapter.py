#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import market_product_contract


def _sha(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def render(product: dict, binding: dict) -> dict:
    canonical = market_product_contract.canonical_contract(product)
    if product.get("contract_sha256") != canonical["contract_sha256"]:
        raise ValueError("product contract SHA mismatch")
    service_id = str(binding.get("service_id") or "")
    offer = binding.get("offer")
    family = str(binding.get("generated_from_family") or "")
    evidence = product.get("capability_evidence") or []
    if (binding.get("version") != 1 or binding.get("platform") != "coconala"
            or not service_id.isdigit()
            or binding.get("public_url") != f"https://coconala.com/services/{service_id}"
            or not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("service_version_sha256") or ""))
            or not isinstance(offer, dict)
            or offer.get("base_price_jpy") != product["base_price"]["amount"]
            or product["base_price"]["currency"] != "JPY"
            or f"owned:capability-family:{family}" not in evidence):
        raise ValueError("Coconala binding does not match product contract")
    fields = {
        key: offer.get(key) for key in (
            "outcome", "inclusions", "deliverables", "required_inputs", "base_price_jpy", "options"
        )
    }
    if (not isinstance(fields["outcome"], str) or not fields["outcome"].strip()
            or any(not isinstance(fields[key], list) or not fields[key]
                   for key in ("inclusions", "deliverables", "required_inputs"))
            or not isinstance(fields["options"], list)):
        raise ValueError("Coconala accepted offer fields are incomplete")
    result = {
        "version": 1, "adapter": "coconala", "product_key": product["product_key"],
        "product_contract_sha256": canonical["contract_sha256"],
        "binding": {key: binding[key] for key in ("service_id", "service_version_sha256", "public_url")},
        "fields": fields,
    }
    return {**result, "adapter_sha256": _sha(result)}


def persist(value: dict, output: Path) -> bool:
    encoded = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if output.exists() and output.read_bytes() == encoded:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = render(json.loads(args.product.read_text()), json.loads(args.binding.read_text()))
    changed = persist(value, args.output)
    print(json.dumps({"ok": True, "changed": changed, "adapter_sha256": value["adapter_sha256"]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
