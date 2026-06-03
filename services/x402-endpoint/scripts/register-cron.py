#!/usr/bin/env python3
"""register-cron.py — idempotently registers anicca-x402-uptime-check.

Mirrors the multi-spec pattern used by ubi-distribute-001 (spec 14 round-2).
Reads `../cron.json` and merges it into ~/.openclaw/cron/jobs.json under the
shared schema (agentId, schedule, sessionTarget, wakeMode, payload, delivery,
enabled, createdAtMs, state). Idempotent on `name`. Atomic write + kickstart.

Exit codes:
    0 — already registered OR newly inserted
    2 — jobs.json missing/unparseable
    3 — cron.json missing/malformed
    4 — atomic write failed
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
JOBS_PATH = Path(os.environ.get("OPENCLAW_JOBS_FILE",
                                 HOME / ".openclaw" / "cron" / "jobs.json"))
SCRIPT_DIR = Path(__file__).resolve().parent
SPEC_PATH = SCRIPT_DIR.parent / "cron.json"
GATEWAY_LABEL = "ai.openclaw.gateway"
SLACK_METRICS_CHANNEL = "channel:C091G3PKHL2"


def load_jobs() -> dict:
    if not JOBS_PATH.exists():
        print(f"[register-cron] missing jobs.json at {JOBS_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(JOBS_PATH.read_text())
    except json.JSONDecodeError as e:
        print(f"[register-cron] jobs.json unparseable: {e}", file=sys.stderr)
        sys.exit(2)


def load_spec() -> dict:
    if not SPEC_PATH.exists():
        print(f"[register-cron] cron.json missing at {SPEC_PATH}", file=sys.stderr)
        sys.exit(3)
    try:
        return json.loads(SPEC_PATH.read_text())
    except json.JSONDecodeError as e:
        print(f"[register-cron] cron.json unparseable: {e}", file=sys.stderr)
        sys.exit(3)


def build_entry(spec: dict) -> dict:
    name = spec.get("name")
    if not name:
        print("[register-cron] cron.json missing 'name'", file=sys.stderr)
        sys.exit(3)
    schedule = spec.get("schedule") or {}
    payload = dict(spec.get("payload") or {})
    created = int(time.time() * 1000)
    return {
        "id": f"{name}-{created}",
        "agentId": "anicca",
        "name": name,
        "schedule": {
            "kind": schedule.get("kind", "cron"),
            "expr": schedule.get("expr"),
            **({"tz": schedule["tz"]} if schedule.get("tz") else {}),
        },
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": payload,
        "delivery": {
            "mode": "announce",
            "channel": "slack",
            "to": SLACK_METRICS_CHANNEL,
            "bestEffort": True,
        },
        "enabled": True,
        "createdAtMs": created,
        "state": {},
    }


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, path)
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        print(f"[register-cron] atomic write failed: {e}", file=sys.stderr)
        sys.exit(4)


def kickstart_gateway() -> tuple[bool, str]:
    uid = os.getuid()
    try:
        out = subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{uid}/{GATEWAY_LABEL}"],
            capture_output=True, text=True, timeout=15,
        )
        return out.returncode == 0, (out.stderr or out.stdout or "").strip()
    except FileNotFoundError:
        return False, "launchctl not found"
    except subprocess.TimeoutExpired:
        return False, "launchctl timed out"


def main() -> int:
    spec = load_spec()
    doc = load_jobs()
    jobs = doc.get("jobs", [])
    if not isinstance(jobs, list):
        print("[register-cron] jobs.json.jobs is not a list", file=sys.stderr)
        return 2

    name = spec.get("name") or SPEC_PATH.stem
    existing = [j for j in jobs if isinstance(j, dict) and j.get("name") == name]
    if existing:
        print(json.dumps({
            "action": "already-registered",
            "name": name,
            "existing_ids": [j.get("id") for j in existing],
        }))
        return 0

    entry = build_entry(spec)
    backup = JOBS_PATH.with_suffix(JOBS_PATH.suffix + f".bak.x402.{int(time.time())}")
    shutil.copy2(JOBS_PATH, backup)
    doc["jobs"] = jobs + [entry]
    atomic_write(JOBS_PATH, doc)
    kick_ok, kick_msg = kickstart_gateway()
    print(json.dumps({
        "action": "inserted",
        "id": entry["id"],
        "name": name,
        "schedule": entry["schedule"],
        "backup": str(backup),
        "gateway_kicked": kick_ok,
        "gateway_msg": kick_msg,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
