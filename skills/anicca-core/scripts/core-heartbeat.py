#!/usr/bin/env python3
"""core-heartbeat.py — per-host liveness beacon for Anicca cores.

Ported from Sutando's src/core_heartbeat.py. Writes a small JSON file at
`<workspace>/state/cores/<hostname>.alive` every 30s while running. The file's
mtime is the cross-host "is this core still up?" signal.

Anicca runs two cores against the same workspace:
  - claude -p   (launchd hourly, host = mac-mini)  → status "claude"
  - OpenClaw    (gateway cron 6h, host = mac-mini)  → status "openclaw"
plus a possible MacBook core. Per-host + per-status files let the self-diagnose
health-check see who is alive without one file fighting N writers.

Usage:
  core-heartbeat.py                      # 30s loop, status "running"
  core-heartbeat.py --status claude      # tag which harness this core is
  core-heartbeat.py --once               # single beat then exit (tests/cron)
  core-heartbeat.py --interval 10
"""
from __future__ import annotations
import argparse
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path

_ws_env = os.environ.get("ANICCA_WORKSPACE", "").strip()
_home_env = os.environ.get("ANICCA_HOME", "").strip()
if _ws_env:
    WORKSPACE = Path(_ws_env).expanduser()
elif _home_env:
    WORKSPACE = Path(_home_env).expanduser() / "workspace"
else:
    WORKSPACE = Path.home() / ".openclaw" / "workspace"

CORES_DIR = WORKSPACE / "state" / "cores"
_STARTED_AT = time.time()
_SHUTDOWN = False


def _host() -> str:
    return socket.gethostname().split(".")[0]


def _alive_path(tag: str) -> Path:
    return CORES_DIR / f"{_host()}-{tag}.alive"


def write_beat(status: str) -> None:
    CORES_DIR.mkdir(parents=True, exist_ok=True)
    target = _alive_path(status)
    payload = {
        "host": _host(),
        "pid": os.getpid(),
        "started_at": _STARTED_AT,
        "last_beat_at": time.time(),
        "status": status,
        "schema_version": 1,
    }
    tmp = target.with_suffix(".alive.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(target)


def _on_signal(signum, frame) -> None:
    global _SHUTDOWN
    _SHUTDOWN = True


def run_forever(interval: float, status: str) -> int:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    while not _SHUTDOWN:
        try:
            write_beat(status)
        except Exception as e:
            print(f"core-heartbeat: write failed: {e}", file=sys.stderr, flush=True)
        slept, slice_s = 0.0, min(1.0, interval)
        while slept < interval and not _SHUTDOWN:
            time.sleep(slice_s)
            slept += slice_s
    try:
        _alive_path(status).unlink(missing_ok=True)
    except Exception:
        pass
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--interval", type=float, default=30.0)
    p.add_argument("--status", type=str, default="running")
    p.add_argument("--once", action="store_true")
    a = p.parse_args(argv)
    if a.once:
        write_beat(a.status)
        return 0
    return run_forever(a.interval, a.status)


if __name__ == "__main__":
    sys.exit(main())
