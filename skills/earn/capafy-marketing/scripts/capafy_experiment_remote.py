#!/usr/bin/env python3
"""Verify one Capafy experiment against remote publisher truth and record it."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from capafy_event_store import append_event
from capafy_experiment import configuration_event


def validate_remote(proposal: dict, payload: dict) -> list[str]:
    errors: list[str] = []
    latest = payload.get("latest_version") if isinstance(payload, dict) else None
    if payload.get("ok") is not True or not isinstance(latest, dict):
        return ["remote status response is unavailable"]
    if str(latest.get("agentId")) != str(proposal.get("agent_id")):
        errors.append("remote agentId does not match proposal")
    if proposal.get("purchase_model") == "one_time":
        if latest.get("agentType") != "download":
            errors.append("remote agentType must be download")
        billings = latest.get("billings")
        download = next(
            (item for item in billings or [] if item.get("billingMode") == "download"),
            None,
        )
        try:
            remote_fee = Decimal(str((download or {}).get("oneTimeFee"))).quantize(Decimal("0.01"))
            expected = Decimal(proposal["price_usd"])
        except (InvalidOperation, TypeError, KeyError):
            remote_fee = None; expected = None
        if remote_fee is None or remote_fee != expected:
            errors.append("remote one-time fee does not match proposal")
    if latest.get("isConfirmedSkills") != 1:
        errors.append("remote skill selection is not confirmed")
    if latest.get("status") not in {1, 4}:
        errors.append("remote status must be under review or online")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--remote-json", type=Path)
    parser.add_argument("--publisher-dir", type=Path, default=Path.home() / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        proposal = json.loads(args.proposal.read_text())
        if args.remote_json:
            payload = json.loads(args.remote_json.read_text())
        else:
            completed = subprocess.run(
                [sys.executable, "packager.py", "publish-remote-status", "--agent-id", proposal["agent_id"]],
                cwd=args.publisher_dir, capture_output=True, text=True, timeout=90, check=True,
            )
            payload = json.loads(completed.stdout, strict=False)
        errors = validate_remote(proposal, payload)
        if errors:
            raise ValueError("; ".join(errors))
        recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        event = configuration_event(proposal, recorded_at)
        result = append_event(args.ledger, event, {"proposal": proposal, "remote_status": payload}, args.evidence_dir)
        print(json.dumps({"verified": True, "event_id": result.event_id, "appended": result.appended, "listing_url": f"https://capafy.ai/agent/{proposal['agent_id']}"}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
