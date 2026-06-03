#!/usr/bin/env python3
"""register-cron.py — idempotently inserts cron.json into ~/.openclaw/cron/jobs.json.

Reads `../cron.json` (declarative spec next to this skill) and merges it into
the live openclaw jobs registry under the standard schema (matches the live
shape of e.g. anicca-fuel-broker, autonomy-check). If an entry with the same
`name` already exists, this is a no-op and the script exits 0 with a
"already-registered" message.

After mutation, the script writes the file atomically and kicks the gateway
(launchctl kickstart) so the new schedule loads.

Exit codes:
    0 — entry already present OR newly inserted
    2 — jobs.json missing / unparseable
    3 — cron.json missing / malformed
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
SKILL_DIR = Path(__file__).resolve().parent.parent
CRON_SPEC = SKILL_DIR / "cron.json"

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
    if not CRON_SPEC.exists():
        print(f"[register-cron] missing cron.json at {CRON_SPEC}", file=sys.stderr)
        sys.exit(3)
    try:
        return json.loads(CRON_SPEC.read_text())
    except json.JSONDecodeError as e:
        print(f"[register-cron] cron.json unparseable: {e}", file=sys.stderr)
        sys.exit(3)


def build_entry(spec: dict) -> dict:
    """Map cron.json spec → live jobs.json entry schema."""
    name = spec.get("name")
    if not name:
        print("[register-cron] cron.json missing 'name'", file=sys.stderr)
        sys.exit(3)
    schedule = spec.get("schedule") or {}
    payload = dict(spec.get("payload") or {})
    # default model = deepseek per HARD RULE on default cron model
    payload.setdefault("model", "deepseek/deepseek-v4-pro")

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
        ok = out.returncode == 0
        return ok, (out.stderr or out.stdout or "").strip()
    except FileNotFoundError:
        return False, "launchctl not found"
    except subprocess.TimeoutExpired:
        return False, "launchctl timed out"


def main() -> int:
    spec = load_spec()
    name = spec["name"]
    doc = load_jobs()
    jobs = doc.get("jobs", [])
    if not isinstance(jobs, list):
        print("[register-cron] jobs.json.jobs is not a list", file=sys.stderr)
        return 2

    # Idempotent: identify by `name` (humans rename ids; names are stable).
    existing = [j for j in jobs if isinstance(j, dict) and j.get("name") == name]
    if existing:
        ids = [j.get("id") for j in existing]
        print(json.dumps({
            "action": "already-registered",
            "name": name,
            "existing_ids": ids,
            "kickstart_skipped": True,
        }, ensure_ascii=False))
        return 0

    entry = build_entry(spec)

    # Backup, then write
    bak = JOBS_PATH.with_suffix(JOBS_PATH.suffix + f".bak.ubi.{int(time.time())}")
    shutil.copy2(JOBS_PATH, bak)
    doc["jobs"] = jobs + [entry]
    atomic_write(JOBS_PATH, doc)

    kick_ok, kick_msg = kickstart_gateway()
    print(json.dumps({
        "action": "inserted",
        "id": entry["id"],
        "name": name,
        "schedule": entry["schedule"],
        "backup": str(bak),
        "kickstart_ok": kick_ok,
        "kickstart_msg": kick_msg,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
