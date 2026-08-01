#!/usr/bin/env python3
"""Snapshot and validate the private Capafy portfolio registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TOP_FIELDS = {
    "schema_version",
    "kind",
    "observed_at",
    "inventory_source_digest",
    "company_projection_id",
    "inventory",
    "products",
}
PRODUCT_FIELDS = {
    "agent_id",
    "name",
    "description",
    "product_type",
    "observed_status",
    "updated_at",
    "public_url",
    "platform_sales",
    "recurring_mechanism",
    "purchase_model",
    "value_metric",
    "target_customer",
    "next_best_alternative",
    "renewal_reason",
    "evidence",
    "unit_economics",
    "decision",
    "decision_reason",
    "experiment",
    "unknowns",
}
STATUSES = {
    "online": "online",
    "approved": "online",
    "under_review": "under_review",
    "draft": "draft",
    "review_rejected": "rejected",
    "rejected": "rejected",
    "banned": "rejected",
}
RECURRING = {
    "repeated_workflow",
    "scheduled_refresh",
    "ongoing_monitoring",
    "collaboration",
    "metered_execution",
}
PURCHASE_MODELS = {"subscription", "usage", "one_time", "hybrid", "undecided"}
DECISIONS = {
    "unaudited",
    "promote",
    "repair",
    "reposition",
    "pause",
    "retire_candidate",
}
MONEY_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]{2}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def snapshot_digest(snapshot: dict) -> str:
    """Return the canonical content digest used to bind an audit to one snapshot."""
    return _digest(snapshot)


def _utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _from_ms(value: Any) -> str:
    return datetime.fromtimestamp(int(value) / 1000, timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def _https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def build_snapshot(
    agents: list[dict], company_projection: dict, observed_at: str
) -> dict:
    products = []
    for agent in agents:
        agent_id = str(agent.get("agentId") or "")
        status = STATUSES.get(str(agent.get("agentStatus") or ""))
        updated_at = int(agent.get("updatedAt") or 0)
        if not agent_id or status is None or updated_at <= 0:
            continue
        products.append(
            {
                "agent_id": agent_id,
                "name": str(agent.get("name") or ""),
                "description": str(agent.get("desc") or ""),
                "product_type": str(agent.get("agentType") or "unknown"),
                "observed_status": status,
                "updated_at": _from_ms(updated_at),
                "public_url": (
                    f"https://capafy.ai/agent/{agent_id}" if status == "online" else None
                ),
                "platform_sales": agent.get("sales"),
                "recurring_mechanism": None,
                "purchase_model": "undecided",
                "value_metric": None,
                "target_customer": None,
                "next_best_alternative": None,
                "renewal_reason": None,
                "evidence": [],
                "unit_economics": {
                    "gross_usd": None,
                    "cost_usd": None,
                    "contribution_usd": None,
                },
                "decision": "unaudited",
                "decision_reason": None,
                "experiment": None,
                "unknowns": [],
            }
        )
    inventory = {"online": 0, "under_review": 0, "draft": 0, "rejected": 0}
    for product in products:
        inventory[product["observed_status"]] += 1
    return {
        "schema_version": 1,
        "kind": "capafy_portfolio",
        "observed_at": observed_at,
        "inventory_source_digest": _digest(agents),
        "company_projection_id": company_projection.get("projection_id"),
        "inventory": inventory,
        "products": products,
    }


def validate_snapshot(snapshot: dict) -> list[str]:
    if not isinstance(snapshot, dict):
        return ["snapshot must be an object"]
    errors: list[str] = []
    unknown = sorted(set(snapshot) - TOP_FIELDS)
    if unknown:
        errors.append(f"unsupported top-level fields: {', '.join(unknown)}")
    if snapshot.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if snapshot.get("kind") != "capafy_portfolio":
        errors.append("kind must be capafy_portfolio")
    if not _utc(snapshot.get("observed_at")):
        errors.append("observed_at must be an RFC3339 UTC timestamp")
    if not DIGEST_RE.fullmatch(str(snapshot.get("inventory_source_digest") or "")):
        errors.append("inventory_source_digest is invalid")
    if not DIGEST_RE.fullmatch(str(snapshot.get("company_projection_id") or "")):
        errors.append("company_projection_id is invalid")
    products = snapshot.get("products")
    if not isinstance(products, list):
        return errors + ["products must be a list"]
    ids: set[str] = set()
    calculated = {"online": 0, "under_review": 0, "draft": 0, "rejected": 0}
    for index, product in enumerate(products):
        prefix = f"products[{index}]"
        if not isinstance(product, dict):
            errors.append(f"{prefix} must be an object")
            continue
        extra = sorted(set(product) - PRODUCT_FIELDS)
        missing = sorted(PRODUCT_FIELDS - set(product))
        if extra:
            errors.append(f"{prefix} unsupported fields: {', '.join(extra)}")
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
            continue
        agent_id = product.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            errors.append(f"{prefix}.agent_id is required")
        elif agent_id in ids:
            errors.append(f"duplicate agent_id: {agent_id}")
        else:
            ids.add(agent_id)
        status = product.get("observed_status")
        if status not in calculated:
            errors.append(f"{prefix}.observed_status is invalid")
        else:
            calculated[status] += 1
        if not _utc(product.get("updated_at")):
            errors.append(f"{prefix}.updated_at is invalid")
        public_url = product.get("public_url")
        if public_url is not None and not _https(public_url):
            errors.append(f"{prefix}.public_url must be HTTPS or null")
        sales = product.get("platform_sales")
        if sales is not None and (
            isinstance(sales, bool) or not isinstance(sales, (int, float)) or sales < 0
        ):
            errors.append(f"{prefix}.platform_sales must be non-negative or null")
        recurring = product.get("recurring_mechanism")
        if recurring is not None and recurring not in RECURRING:
            errors.append(f"{prefix}.recurring_mechanism is invalid")
        if product.get("purchase_model") not in PURCHASE_MODELS:
            errors.append(f"{prefix}.purchase_model is invalid")
        if product.get("decision") not in DECISIONS:
            errors.append(f"{prefix}.decision is invalid")
        economics = product.get("unit_economics")
        if not isinstance(economics, dict) or set(economics) != {
            "gross_usd",
            "cost_usd",
            "contribution_usd",
        }:
            errors.append(f"{prefix}.unit_economics has invalid fields")
        else:
            for field, value in economics.items():
                if value is not None and (
                    not isinstance(value, str) or not MONEY_RE.fullmatch(value)
                ):
                    errors.append(f"{prefix}.unit_economics.{field} is invalid")
        evidence = product.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence must be a list")
        else:
            for evidence_index, item in enumerate(evidence):
                ep = f"{prefix}.evidence[{evidence_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{ep} must be an object")
                    continue
                if not _https(item.get("url")):
                    errors.append(f"{ep}.evidence.url must be HTTPS")
                if not _utc(item.get("observed_at")):
                    errors.append(f"{ep}.evidence.observed_at is invalid")
                if item.get("confidence") not in {"high", "medium", "low"}:
                    errors.append(f"{ep}.evidence.confidence is invalid")
                if not isinstance(item.get("claim"), str) or not item["claim"].strip():
                    errors.append(f"{ep}.evidence.claim is required")
        unknowns = product.get("unknowns")
        if not isinstance(unknowns, list) or not all(
            isinstance(item, str) and item.strip() for item in unknowns
        ):
            errors.append(f"{prefix}.unknowns must contain only non-empty strings")
    if snapshot.get("inventory") != calculated:
        errors.append("inventory counts do not match product rows")
    return errors


def _atomic_write(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = _canonical(snapshot) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_inventory(args: argparse.Namespace) -> list[dict]:
    if args.inventory_json:
        payload = json.loads(args.inventory_json.read_text(encoding="utf-8"))
    else:
        completed = subprocess.run(
            [sys.executable, "packager.py", "publish-list"],
            cwd=args.inventory_command_dir,
            capture_output=True,
            text=True,
            timeout=90,
            check=True,
        )
        payload = json.loads(completed.stdout, strict=False)
    agents = ((payload.get("agents") or {}).get("list"))
    if not isinstance(agents, list) or not all(isinstance(item, dict) for item in agents):
        raise ValueError("inventory source does not contain agents.list")
    return agents


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--inventory-json", type=Path)
    snapshot.add_argument(
        "--inventory-command-dir",
        type=Path,
        default=Path.home()
        / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher",
    )
    snapshot.add_argument(
        "--projection",
        type=Path,
        default=Path(__file__).parents[1] / "site/company/state.json",
    )
    snapshot.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".openclaw/state/capafy-portfolio.json",
    )
    snapshot.add_argument("--observed-at")
    validate = commands.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            value = json.loads(args.input.read_text(encoding="utf-8"))
            errors = validate_snapshot(value)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 2
            print(json.dumps({"valid": True, "product_count": len(value["products"])}))
            return 0
        agents = _load_inventory(args)
        company = json.loads(args.projection.read_text(encoding="utf-8"))
        observed_at = args.observed_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        value = build_snapshot(agents, company, observed_at)
        errors = validate_snapshot(value)
        if errors:
            raise ValueError("; ".join(errors))
        if args.output.exists():
            existing = json.loads(args.output.read_text(encoding="utf-8"))
            if (
                not validate_snapshot(existing)
                and existing["inventory_source_digest"]
                == value["inventory_source_digest"]
                and existing["company_projection_id"] == value["company_projection_id"]
            ):
                value = existing
        _atomic_write(args.output, value)
        print(
            json.dumps(
                {
                    "valid": True,
                    "product_count": len(value["products"]),
                    "inventory_source_digest": value["inventory_source_digest"],
                    "company_projection_id": value["company_projection_id"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (json.JSONDecodeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
