#!/usr/bin/env python3
"""Validate integration onboarding manifests and render the shared readiness graph."""

from __future__ import annotations

import argparse
import json
import plistlib
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "integrations"
SCHEMA = ROOT / "onboarding.schema.json"


def load_manifests() -> list[dict[str, Any]]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifests = []
    for path in sorted(ROOT.glob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
        if errors:
            location = ".".join(str(part) for part in errors[0].path) or "$"
            raise ValueError(f"invalid_integration_manifest:{path.name}:{location}:{errors[0].message}")
        manifests.append(value)
    if not manifests:
        raise ValueError("integration_manifests_empty")
    validate_cross_manifest(manifests)
    return manifests


def validate_cross_manifest(manifests: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    owners: dict[str, str] = {}
    profile_fields: dict[str, tuple[str, str]] = {}
    receipts: set[str] = set()
    for manifest in manifests:
        integration_id = manifest["integration_id"]
        if integration_id in ids:
            raise ValueError(f"duplicate_integration_id:{integration_id}")
        ids.add(integration_id)
        ceremony_states = {row["completion_state"] for row in manifest["ceremonies"]}
        if not ceremony_states <= set(manifest["gate_states"]):
            raise ValueError(f"undeclared_ceremony_state:{integration_id}")
        for owner in manifest["activation"]["owners"]:
            if owner in owners:
                raise ValueError(f"duplicate_integration_owner:{owner}:{owners[owner]}:{integration_id}")
            owners[owner] = integration_id
        for field in manifest["profile_fields"]:
            identity = (field["purpose"], field["privacy"])
            prior = profile_fields.setdefault(field["field_id"], identity)
            if prior != identity:
                raise ValueError(f"conflicting_profile_field:{field['field_id']}")
        local_receipts: set[str] = set()
        for receipt in manifest["receipts"]:
            receipt_id = receipt["receipt_id"]
            if receipt_id in local_receipts:
                raise ValueError(f"duplicate_integration_receipt:{integration_id}:{receipt_id}")
            local_receipts.add(receipt_id)
            identity = f"{integration_id}:{receipt_id}"
            if identity in receipts:
                raise ValueError(f"duplicate_integration_receipt:{identity}")
            receipts.add(identity)


def graph(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    discovered = discover_owner_labels()
    declared = {owner for manifest in manifests for owner in manifest["activation"]["owners"]}
    return {
        "version": 1,
        "manifest_coverage": {
            "discovered_owners": len(discovered),
            "declared_owners": len(discovered & declared),
            "unmanaged_owners": len(discovered - declared),
        },
        "integrations": [{
            "integration_id": manifest["integration_id"],
            "display_name": manifest["display_name"],
            "organ": manifest["organ"],
            "outcome": manifest["outcome"],
            "owner_time_minutes": manifest["owner_time_minutes"],
            "platforms": manifest["platforms"],
            "prerequisites": manifest["prerequisites"],
            "profile_fields": manifest["profile_fields"],
            "ceremonies": manifest["ceremonies"],
            "gate_states": manifest["gate_states"],
            "connect": manifest["connect"],
            "preflight": manifest["preflight"],
            "readiness": manifest["readiness"],
            "outcome_status": manifest["outcome_status"],
            "activation": manifest["activation"],
            "receipt_ids": [row["receipt_id"] for row in manifest["receipts"]],
            "state": "unknown",
        } for manifest in manifests],
    }


def discover_owner_labels() -> set[str]:
    labels: set[str] = set()
    for path in REPO.rglob("launchd-jobs.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for row in value.get("jobs", []):
            if isinstance(row, dict) and isinstance(row.get("label"), str):
                labels.add(row["label"])
    for path in list(REPO.rglob("*.plist")) + list(REPO.rglob("*.plist.template")):
        if ".git" in path.parts or "legacy-launchd-archive" in path.parts:
            continue
        try:
            value = plistlib.loads(path.read_bytes())
            label = value.get("Label") if isinstance(value, dict) else None
        except Exception:
            text = path.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"<key>Label</key>\s*<string>([^<]+)</string>", text)
            label = match.group(1) if match else None
        if isinstance(label, str) and re.fullmatch(r"[A-Za-z0-9._-]+", label):
            labels.add(label)
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "graph"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifests = load_manifests()
    value = ({"status": "valid", "integrations": len(manifests)}
             if args.command == "validate" else graph(manifests))
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
