#!/usr/bin/env python3
"""Maintain the ask-once private Life Manager profile without echoing values."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


REPO = Path(__file__).resolve().parents[1]
SCHEMA = REPO / "integrations" / "profile.schema.json"
MANIFESTS = REPO / "integrations"
PROFILE = Path(os.environ.get("LIFE_MANAGER_PROFILE") or Path.home() / ".config/life-manager/profile.json")


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _write_private(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def load(create: bool = False) -> dict[str, Any]:
    if not PROFILE.exists():
        if not create:
            return {"version": 1, "fields": {}}
        value = {"version": 1, "fields": {}}
        _write_private(PROFILE, value)
        return value
    value = json.loads(PROFILE.read_text(encoding="utf-8"))
    _validator().validate(value)
    return value


def put(field_id: str, field: dict[str, Any]) -> dict[str, Any]:
    value = load(create=True)
    value["fields"][field_id] = field
    _validator().validate(value)
    _write_private(PROFILE, value)
    return {"status": "stored", "field_id": field_id, "privacy": field["privacy"]}


def summary(value: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    rows = []
    for field_id, field in sorted(value["fields"].items()):
        expires = field.get("expires_at")
        fresh = True
        if expires:
            fresh = datetime.fromisoformat(expires.replace("Z", "+00:00")) > now
        rows.append({
            "field_id": field_id, "privacy": field["privacy"], "source": field["source"],
            "scopes": field["scopes"], "fresh": fresh,
            "consent": field["consent"]["granted"], "has_value": field.get("value") is not None,
            "has_secret_ref": field.get("secret_ref") is not None,
            "has_evidence": field.get("evidence_sha256") is not None,
        })
    return {"status": "ready" if PROFILE.exists() else "uninitialized", "fields": rows}


def _fresh(field: dict[str, Any]) -> bool:
    expires = field.get("expires_at")
    return not expires or datetime.fromisoformat(expires.replace("Z", "+00:00")) > datetime.now(timezone.utc)


def missing(integration_id: str, value: dict[str, Any]) -> dict[str, Any]:
    manifest_path = MANIFESTS / f"{integration_id}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    absent = []
    for requirement in manifest["profile_fields"]:
        if not requirement["required"]:
            continue
        field = value["fields"].get(requirement["field_id"])
        if (not isinstance(field, dict) or field.get("privacy") != requirement["privacy"]
                or field.get("purpose") != requirement["purpose"] or not _fresh(field)
                or field.get("consent", {}).get("granted") is not True
                or integration_id not in field.get("scopes", []) and "*" not in field.get("scopes", [])):
            absent.append(requirement["field_id"])
    return {"integration_id": integration_id, "missing": absent,
            "status": "ready" if not absent else "needs_profile"}


def export_profile(output: Path) -> dict[str, Any]:
    value = load()
    _validator().validate(value)
    _write_private(output.expanduser().absolute(), value)
    return {"status": "exported", "fields": len(value["fields"]), "output": "private:profile-export"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "put", "status", "missing", "export"))
    parser.add_argument("--field-id")
    parser.add_argument("--integration")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "export":
        if args.output is None:
            parser.error("export requires --output")
        output = export_profile(args.output)
    elif args.command == "init":
        value = load(create=True)
        output = summary(value)
    elif args.command == "put":
        if not args.field_id:
            parser.error("put requires --field-id")
        field = json.load(os.fdopen(os.dup(0), "r", encoding="utf-8"))
        output = put(args.field_id, field)
    elif args.command == "missing":
        if not args.integration:
            parser.error("missing requires --integration")
        output = missing(args.integration, load())
    else:
        output = summary(load())
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if output.get("status") not in {"uninitialized", "needs_profile"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
