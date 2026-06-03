#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# register.py — child posts itself to anicca-001's peer-api so the lineage
# dashboard + heartbeat can see it.
#
# Reads state/<instance>/{wallet,inbox,constitution}.json, builds a registration
# payload, POSTs to PEER_API_BASE_URL/register. Idempotent on the server side
# (= upsert by instance_id).

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def _read_json(p: Path, key: str) -> dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"missing {key} file at {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{key} JSON parse failed: {exc}") from exc


def build_payload(state_dir: Path, instance_id: str) -> dict[str, Any]:
    wallet = _read_json(state_dir / "wallet.json", "wallet")
    inbox = _read_json(state_dir / "inbox.json", "inbox")
    constitution = _read_json(state_dir / "constitution.json", "constitution")
    return {
        "instance_id": instance_id,
        "wallet": {
            "owner_eoa": wallet.get("owner_eoa"),
            "smart_account": wallet.get("smart_account"),
            "network": wallet.get("network"),
            "broadcast": wallet.get("broadcast", False),
        },
        "inbox": {
            "email": inbox.get("inbox_email"),
            "inbox_id": inbox.get("inbox_id"),
            "custom_address_succeeded": inbox.get("custom_address_succeeded"),
        },
        "constitution": {
            "sha256": constitution.get("sha256"),
            "captured_at": constitution.get("captured_at"),
        },
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PROVISIONED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-id", default=os.environ.get("ANICCA_INSTANCE_ID", "anicca-002"))
    parser.add_argument("--state-dir", required=True)
    parser.add_argument(
        "--peer-api",
        default=os.environ.get("PEER_API_BASE_URL", "http://localhost:18789"),
    )
    args = parser.parse_args()

    state_dir = Path(args.state_dir).expanduser().resolve()
    payload = build_payload(state_dir, args.instance_id)

    body = json.dumps(payload).encode("utf-8")
    url = args.peer_api.rstrip("/") + "/register"
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=8) as resp:
            status = resp.status
            response = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        sys.stderr.write(f"peer-api returned {exc.code}: {exc.reason}\n")
        return 0  # non-fatal per spawn.sh contract
    except URLError as exc:
        sys.stderr.write(f"peer-api unreachable at {url}: {exc.reason}\n")
        # Persist payload locally so anicca-001 can ingest later
        local = state_dir / "register-pending.json"
        local.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.stderr.write(f"persisted pending registration to {local}\n")
        return 0

    out = state_dir / "register.json"
    out.write_text(
        json.dumps({"http_status": status, "url": url, "response": response}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
