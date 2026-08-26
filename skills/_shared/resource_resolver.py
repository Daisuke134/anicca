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
SKILLS_ROOT = REPO / "skills"


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


def matches_service(service: str, *values: object) -> bool:
    haystack = " ".join(str(value).lower() for value in values if value is not None)
    wanted = service_tokens(service)
    if "x" in wanted or "twitter" in wanted:
        return bool(re.search(r"(?:x\.com|twitter|(?:^|[\s/_-])x(?:[\s/_-]|$))", haystack))
    return bool(tokens(haystack) & wanted)


def matches_registered_service(service: str, name: str, *values: object) -> bool:
    """Live slots must advertise the service, not merely mention a common word."""
    haystack = " ".join(str(value).lower() for value in values if value is not None)
    lowered = service.lower()
    if lowered in ("x.com", "twitter.com"):
        return matches_service(service, name, haystack)
    if "." in lowered:
        label = lowered.split(".", 1)[0]
        return lowered in haystack or label in tokens(name)
    return matches_service(service, name, haystack)


def frontmatter_scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", frontmatter)
    if not match:
        return ""
    value = match.group(1).strip().strip("'\"")
    if value not in ("|", ">", "|-", ">-"):
        return value
    lines = frontmatter[match.end():].splitlines()
    continuation = []
    for line in lines:
        if not line.startswith((" ", "\t")):
            break
        continuation.append(line.strip())
    return " ".join(continuation)


def installed_skill_refs(service: str, capability: str) -> list[dict[str, Any]]:
    """Discover installed knowledge/adapters without claiming runtime readiness.

    SKILL.md is the OSS capability catalogue.  The live slot registry is a smaller
    execution catalogue, so limiting discovery to it made otherwise reusable skills
    invisible to gig owners.  Parse only frontmatter and return a path for the owner to
    read; the owner still has to inspect the adapter and prove live readiness.
    """
    result = []
    for path in SKILLS_ROOT.glob("**/SKILL.md"):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not source.startswith("---\n"):
            continue
        end = source.find("\n---", 4)
        if end < 0:
            continue
        frontmatter = source[4:end]
        name = frontmatter_scalar(frontmatter, "name") or path.parent.name
        description = frontmatter_scalar(frontmatter, "description")
        if not matches_service(service, name, description, frontmatter):
            continue
        if capability and capability not in tokens(name, description, frontmatter):
            continue
        result.append({
            "skill": name,
            "skill_path": str(path.relative_to(REPO)),
            "description": description,
            "readiness": "inspect_adapter_and_verify_live_effect",
        })
    return sorted(result, key=lambda row: (row["skill"], row["skill_path"]))


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
            "secret_fields": sorted(key for key in ("password", "passcode", "token", "api_key") if row.get(key)),
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
    result = []
    for name, row in slots.items():
        if not isinstance(row, dict) or row.get("status") != "live":
            continue
        capabilities = row.get("capabilities", [])
        if capability and capabilities and capability not in capabilities:
            continue
        if not matches_registered_service(
                service, name, row.get("summary"), row.get("toolDescription")):
            continue
        result.append({key: value for key, value in {
            "slot": name, "dir": row.get("dir"), "entrypoint": row.get("entrypoint"),
            "summary": row.get("summary"), "risk": row.get("risk"),
            "capabilities": capabilities,
        }.items() if value not in (None, "")})
    known_paths = {row.get("dir") for row in result}
    for row in installed_skill_refs(service, capability):
        skill_dir = str(Path(row["skill_path"]).parent)
        if skill_dir not in known_paths:
            result.append(row)
    return result


def capability_manifest() -> dict[str, Any]:
    """Return the shared, non-secret capability plane every owner starts with."""
    slots = load_json(REGISTRY).get("slots", {}) if REGISTRY.is_file() else {}
    skills = []
    for name, row in slots.items():
        if not isinstance(row, dict) or row.get("status") != "live":
            continue
        skills.append({key: value for key, value in {
            "slot": name,
            "capabilities": row.get("capabilities", []),
        }.items() if value not in (None, "", [])})

    accounts = []
    rows = load_json(CREDENTIALS).get("credentials", []) if CREDENTIALS.is_file() else []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        accounts.append({key: value for key, value in {
            "ref": f"credentials:{index}",
            "service": row.get("service"),
            "username": row.get("username"),
            "url": row.get("url"),
            "account_status": row.get("account_status"),
        }.items() if value not in (None, "")})

    sessions = []
    if BROWSERS.is_file():
        for row in tomllib.loads(BROWSERS.read_text(encoding="utf-8")).get("identity", []):
            if not isinstance(row, dict):
                continue
            sessions.append({key: row.get(key) for key in (
                "id", "owner", "accounts", "handles", "ownership", "capabilities"
            ) if row.get(key) not in (None, [], "")})
    return {
        "version": 1,
        "skills": skills,
        "accounts": accounts,
        "browser_sessions": sessions,
        "policy": (
            "Shared discovery only: resolve the selected service/capability, then let its adapter read secrets by ref. "
            "Never copy secret values or another customer's mutable context into an owner prompt."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("resolve", "manifest"))
    parser.add_argument("--service")
    parser.add_argument("--capability", default="")
    args = parser.parse_args()
    if args.command == "manifest":
        print(json.dumps(capability_manifest(), ensure_ascii=False, sort_keys=True))
        return 0
    if not args.service:
        parser.error("resolve requires --service")
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
    value["effect_ready"] = bool(
        value["browser_sessions"]
        or any(row.get("slot") for row in value["skills"])
    )
    value["readiness_policy"] = (
        "Static capability match only. The selected owner must verify live readiness in official UI/API; "
        "if unavailable, resolve another authorized skill or channel instead of treating discovery as success."
    )
    value["available"] = value["discovered"]
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
