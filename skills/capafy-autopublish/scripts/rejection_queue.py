#!/usr/bin/env python3
"""Build a durable same-Agent repair queue from rejected Capafy versions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
AUTO = HERE.parent
PUBLISHER = AUTO / "vendor/capafy-publisher"
DEFAULT_QUEUE = Path.home() / ".local/state/mr-bot/state/capafy-rejection-repair-queue.json"
REASON_KEYS = {
    "rejectreason",
    "rejectionreason",
    "auditreason",
    "auditremark",
    "reviewreason",
    "reviewremark",
    "rejectmessage",
}
TERMINAL_STATES = {"resubmitted", "listed", "abandoned"}


def _reason(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(character for character in str(key).lower() if character.isalnum())
            if normalized in REASON_KEYS and isinstance(child, str) and child.strip():
                return child.strip()
        for child in value.values():
            found = _reason(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _reason(child)
            if found:
                return found
    return None


def _new_item(agent: dict, detail: dict, observed_at: str) -> dict:
    latest = detail.get("latest_version") if isinstance(detail, dict) else None
    latest = latest if isinstance(latest, dict) else {}
    agent_id = str(agent["agent_id"])
    version_id = str(latest.get("agentVersionId") or agent.get("latest_version_id") or "unknown-version")
    reason = _reason(latest)
    version_no = latest.get("versionNo")
    target_version = version_no + 1 if isinstance(version_no, int) and not isinstance(version_no, bool) else None
    return {
        "repair_id": f"{agent_id}:{version_id}",
        "agent_id": agent_id,
        "name": str(agent.get("name") or latest.get("title") or ""),
        "operation": "update_existing_agent",
        "source_version_id": version_id,
        "source_version_no": version_no,
        "source_version_name": latest.get("versionName") or agent.get("latest_version_name"),
        "target_version_no": target_version,
        "remote_status": agent.get("remote_status"),
        "numeric_status": latest.get("status"),
        "audit_status": latest.get("auditStatus"),
        "skills_confirmed": latest.get("isConfirmedSkills"),
        "config_confirmed": latest.get("isConfirmedConfigKeys"),
        "rejection_reason": reason or "platform_reason_unavailable",
        "reason_status": "observed" if reason else "unknown",
        "state": "queued" if reason else "needs_diagnosis",
        "first_observed_at": observed_at,
        "last_observed_at": observed_at,
    }


def build_queue(existing: dict, agents: list[dict], details: dict[str, dict], observed_at: str) -> dict:
    prior_items = existing.get("items") if isinstance(existing, dict) else None
    prior_items = prior_items if isinstance(prior_items, list) else []
    by_id = {
        item.get("repair_id"): dict(item)
        for item in prior_items
        if isinstance(item, dict) and isinstance(item.get("repair_id"), str)
    }
    order = [item["repair_id"] for item in prior_items if isinstance(item, dict) and item.get("repair_id") in by_id]
    for agent in sorted(agents, key=lambda row: str(row.get("agent_id") or "")):
        if agent.get("remote_status") != "review_rejected" or not agent.get("agent_id"):
            continue
        candidate = _new_item(agent, details.get(str(agent["agent_id"]), {}), observed_at)
        repair_id = candidate["repair_id"]
        if repair_id in by_id:
            prior = by_id[repair_id]
            prior["last_observed_at"] = observed_at
            if prior.get("reason_status") == "unknown" and candidate["reason_status"] == "observed":
                prior["rejection_reason"] = candidate["rejection_reason"]
                prior["reason_status"] = "observed"
                if prior.get("state") == "needs_diagnosis":
                    prior["state"] = "queued"
            by_id[repair_id] = prior
        else:
            by_id[repair_id] = candidate
            order.append(repair_id)
    items = [by_id[repair_id] for repair_id in order]
    return {
        "schema_version": 1,
        "updated_at": observed_at,
        "items": items,
        "counts": {
            "total": len(items),
            "active": sum(item.get("state") not in TERMINAL_STATES for item in items),
            "needs_diagnosis": sum(item.get("state") == "needs_diagnosis" for item in items),
            "ready": sum(item.get("state") == "queued" for item in items),
        },
    }


def _remote_detail(agent_id: str) -> dict:
    result = subprocess.run(
        [sys.executable, "packager.py", "publish-remote-status", "--agent-id", agent_id],
        cwd=PUBLISHER,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        return {"_error": f"remote_status_rc_{result.returncode}"}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_error": "remote_status_invalid_json"}
    return value if isinstance(value, dict) else {"_error": "remote_status_not_object"}


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--inventory-json", type=Path)
    parser.add_argument("--observed-at")
    args = parser.parse_args(argv)
    observed_at = args.observed_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    if args.inventory_json:
        inventory = json.loads(args.inventory_json.read_text())
    else:
        from inventory_status import normalize_agents, server_agents

        raw_agents = server_agents()
        if raw_agents is None:
            print(json.dumps({"ok": False, "reason": "inventory_unreadable"}))
            return 1
        inventory = normalize_agents(raw_agents)
    agents = inventory.get("agents") if isinstance(inventory, dict) else None
    if not isinstance(agents, list):
        print(json.dumps({"ok": False, "reason": "inventory_rows_missing"}))
        return 1
    rejected = [agent for agent in agents if isinstance(agent, dict) and agent.get("remote_status") == "review_rejected"]
    details = {str(agent["agent_id"]): _remote_detail(str(agent["agent_id"])) for agent in rejected}
    try:
        existing = json.loads(args.output.read_text()) if args.output.exists() else {}
    except (OSError, json.JSONDecodeError):
        print(json.dumps({"ok": False, "reason": "existing_queue_invalid"}))
        return 1
    queue = build_queue(existing, rejected, details, observed_at)
    _atomic_write(args.output, queue)
    print(json.dumps({"ok": True, "path": str(args.output), **queue["counts"]}, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
