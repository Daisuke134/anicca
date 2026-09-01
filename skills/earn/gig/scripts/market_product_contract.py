#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "market_product_contract.schema.json"
MARKETPLACE_KEYS = {"platform", "service_id", "public_url", "category_id", "form_field"}


def _schema() -> dict:
    value = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


def validate_contract(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("market product contract must be an object")
    forbidden = MARKETPLACE_KEYS.intersection(value)
    if forbidden:
        raise ValueError(f"marketplace-specific keys are forbidden: {sorted(forbidden)}")
    candidate = {key: item for key, item in value.items() if key != "contract_sha256"}
    errors = sorted(Draft202012Validator(_schema()).iter_errors(candidate), key=lambda row: list(row.path))
    if errors:
        raise ValueError(errors[0].message)
    return candidate


def canonical_contract(value: dict) -> dict:
    candidate = validate_contract(value)
    encoded = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    result = {**candidate, "contract_sha256": hashlib.sha256(encoded).hexdigest()}
    errors = list(Draft202012Validator(_schema()).iter_errors(result))
    if errors:
        raise ValueError(errors[0].message)
    return result


def persist(value: dict, output: Path) -> bool:
    encoded = (json.dumps(canonical_contract(value), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
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
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.input.read_text(encoding="utf-8"))
    changed = persist(value, args.output)
    print(json.dumps({"ok": True, "changed": changed, "output": str(args.output)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
