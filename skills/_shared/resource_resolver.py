#!/usr/bin/env python3
"""Resolve reusable Life Manager skills, accounts, sessions, and credential refs.

The output is deliberately non-secret. Adapters consume credential material directly
from the local credential SSOT; models receive only references and public identity.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("LIFE_MANAGER_REPO") or HERE.parents[1]).resolve()
REGISTRY = Path(os.environ.get("LIFE_MANAGER_SKILL_REGISTRY") or REPO / "skills/registry.json")
CREDENTIALS = Path(os.environ.get("ANICCA_CREDENTIALS_FILE") or Path.home() / ".local/share/anicca/credentials.json")
BROWSERS = Path(os.environ.get("AI_BROWSER_REGISTRY") or Path.home() / ".config/ai/registry/browsers.toml")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def tokens(*values: object) -> set[str]:
    ignored = {"com", "www", "net", "org", "io", "app"}
    return {part for value in values for part in re.findall(r"[a-z0-9]+", str(value).lower())
            if part not in ignored}


def service_tokens(service: str) -> set[str]:
    result = tokens(service)
    if "x" in result or "twitter" in result:
        result.update(("x", "twitter"))
    return result


def credential_refs(service: str) -> list[dict[str, Any]]:
    rows = load_json(CREDENTIALS).get("credentials", []) if CREDENTIALS.is_file() else []
    wanted = service_tokens(service)
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not (tokens(row.get("service")) & wanted):
            continue
        result.append({
            "ref": f"credentials:{index}",
            "service": row.get("service"),
            "username": row.get("username"),
            "url": row.get("url"),
            "account_status": row.get("account_status"),
            "secret_fields": sorted(key for key in ("password", "token", "api_key") if row.get(key)),
        })
    return result


def browser_refs(service: str, capability: str) -> list[dict[str, Any]]:
    if not BROWSERS.is_file():
        return []
    rows = tomllib.loads(BROWSERS.read_text(encoding="utf-8")).get("identity", [])
    wanted = service_tokens(service)
    result = []
    for row in rows:
        if not isinstance(row, dict) or not any(tokens(value) & wanted for value in row.get("accounts", [])):
            continue
        capabilities = row.get("capabilities", [])
        if capability and capabilities and capability not in capabilities:
            continue
        result.append({key: row.get(key) for key in (
            "id", "owner", "accounts", "handles", "ownership", "capabilities", "notes"
        ) if row.get(key) not in (None, [], "")})
    return result


def skill_refs(service: str, capability: str) -> list[dict[str, Any]]:
    slots = load_json(REGISTRY).get("slots", {}) if REGISTRY.is_file() else {}
    wanted = service_tokens(service) | tokens(capability)
    result = []
    for name, row in slots.items():
        if not isinstance(row, dict) or row.get("status") != "live":
            continue
        capabilities = row.get("capabilities", [])
        if capability and capabilities and capability not in capabilities:
            continue
        if not (tokens(name, row.get("summary"), row.get("toolDescription")) & wanted):
            continue
        result.append({key: value for key, value in {
            "slot": name, "dir": row.get("dir"), "entrypoint": row.get("entrypoint"),
            "summary": row.get("summary"), "risk": row.get("risk"),
            "capabilities": capabilities,
        }.items() if value not in (None, "")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("resolve",))
    parser.add_argument("--service", required=True)
    parser.add_argument("--capability", default="")
    args = parser.parse_args()
    value = {
        "version": 1,
        "service": args.service,
        "capability": args.capability,
        "skills": skill_refs(args.service, args.capability),
        "accounts": credential_refs(args.service),
        "browser_sessions": browser_refs(args.service, args.capability),
        "credential_policy": "Adapters read secret fields by ref; never print or place them in prompts.",
    }
    value["discovered"] = bool(value["skills"] or value["accounts"] or value["browser_sessions"])
    value["effect_ready"] = bool(value["skills"] or value["browser_sessions"])
    value["readiness_policy"] = (
        "Static capability match only. The selected owner must verify live readiness in official UI/API; "
        "if unavailable, resolve another authorized skill or channel instead of treating discovery as success."
    )
    value["available"] = value["discovered"]
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
