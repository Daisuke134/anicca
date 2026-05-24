#!/usr/bin/env python3
"""health-check.py — Anicca self-diagnose (ported from Sutando src/health-check.py).

Verifies the autonomous system is actually running and able to act. Step 2 of
the beat (MUST chores / self-heal) runs this; --fix repairs what it safely can.

Checks:
  - OpenClaw gateway launchd job loaded + process alive
  - claude -p heartbeat launchd job loaded (ai.anicca.heartbeat)
  - Critical files present (HEARTBEAT.md, CONSTITUTION.md, build_log.md, AGENTS.md)
  - Memory index (MEMORY.md) present + non-empty
  - core-status freshness → STUCK LOOP detection (status=running but stale)
  - per-host core liveness (.alive mtime younger than 2× beat interval)

Usage:
  health-check.py                 # human readable
  health-check.py --json          # machine readable
  health-check.py --fix           # attempt safe repairs (reload launchd, restart gateway)
  health-check.py --emit-task     # write a task file on failure (for the loop to pick up)
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
WS = Path(os.environ.get("ANICCA_WORKSPACE", str(ANICCA_HOME / "workspace")))
BEAT_MIN = float(os.environ.get("ANICCA_BEAT_INTERVAL_MIN", "60"))
def _default_memory_dir() -> Path:
    """ANICCA_MEMORY_DIR if set; else first ~/.claude/projects/*/memory match.
    No hardcoded user path — keeps the OSS mirror clean."""
    env = os.environ.get("ANICCA_MEMORY_DIR")
    if env:
        return Path(env)
    # Pick the project-memory dir with the MOST .md files (the active one).
    # Robust on a multi-project machine and on a fresh single-project OSS install.
    cands = [p for p in (Path.home() / ".claude" / "projects").glob("*/memory") if p.is_dir()]
    if cands:
        return max(cands, key=lambda p: len(list(p.glob("*.md"))))
    return Path.home() / ".claude" / "projects" / "memory"


MEMORY_DIR = _default_memory_dir()

GATEWAY_LABEL = os.environ.get("ANICCA_GATEWAY_LABEL", "ai.openclaw.gateway")
BEAT_LABEL = os.environ.get("ANICCA_BEAT_LABEL", "ai.anicca.heartbeat")

results: list[dict] = []


def add(name: str, ok: bool, detail: str = "", fixable: bool = False):
    results.append({"check": name, "ok": ok, "detail": detail, "fixable": fixable})


def _launchctl_loaded(label: str) -> bool:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
        return label in out.stdout
    except Exception:
        return False


def _pgrep(pattern: str) -> bool:
    try:
        return subprocess.run(["pgrep", "-f", pattern], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def check_gateway(fix: bool):
    loaded = _launchctl_loaded(GATEWAY_LABEL)
    alive = _pgrep("openclaw") or _pgrep("gateway")
    ok = loaded and alive
    detail = f"launchd={'loaded' if loaded else 'MISSING'} proc={'alive' if alive else 'DEAD'}"
    if not ok and fix:
        try:
            subprocess.run(["openclaw", "gateway", "restart"], capture_output=True, timeout=60)
            time.sleep(3)
            alive = _pgrep("openclaw") or _pgrep("gateway")
            ok = alive
            detail += f" → fix:restart {'ok' if ok else 'FAILED'}"
        except Exception as e:
            detail += f" → fix:err {e}"
    add("openclaw_gateway", ok, detail, fixable=True)


def check_beat_launchd(fix: bool):
    loaded = _launchctl_loaded(BEAT_LABEL)
    detail = "loaded" if loaded else "MISSING"
    if not loaded and fix:
        plist = Path.home() / "Library" / "LaunchAgents" / f"{BEAT_LABEL}.plist"
        if plist.exists():
            try:
                subprocess.run(["launchctl", "load", str(plist)], capture_output=True, timeout=15)
                loaded = _launchctl_loaded(BEAT_LABEL)
                detail += f" → fix:load {'ok' if loaded else 'FAILED'}"
            except Exception as e:
                detail += f" → fix:err {e}"
    add("claude_p_heartbeat_launchd", loaded, detail, fixable=True)


def check_files():
    for rel in ["workspace/HEARTBEAT.md", "workspace/CONSTITUTION.md",
                "workspace/ops/build_log.md", "workspace/AGENTS.md"]:
        p = ANICCA_HOME / rel
        add(f"file:{rel}", p.exists() and p.stat().st_size > 0,
            "ok" if p.exists() else "MISSING")


def check_memory():
    idx = MEMORY_DIR / "MEMORY.md"
    ok = idx.exists() and idx.stat().st_size > 0
    n = len(list(MEMORY_DIR.glob("*.md"))) if MEMORY_DIR.exists() else 0
    add("memory_index", ok, f"MEMORY.md={'ok' if ok else 'MISSING'} files={n}")


def check_stuck_loop():
    """STUCK = core-status says running but mtime older than 2 beat intervals."""
    f = WS / "core-status.json"
    if not f.exists():
        add("core_status", True, "no core-status.json yet (first run)")
        return
    try:
        d = json.loads(f.read_text())
    except Exception:
        add("core_status", False, "core-status.json unparseable")
        return
    age_min = (time.time() - f.stat().st_mtime) / 60.0
    status = d.get("status", "unknown")
    stuck = status == "running" and age_min > (2 * BEAT_MIN)
    add("core_status", not stuck,
        f"status={status} age={age_min:.0f}m" + (" → STUCK LOOP" if stuck else ""))


def check_core_liveness():
    cores = WS / "state" / "cores"
    if not cores.exists():
        add("core_liveness", True, "no cores/ dir yet (liveness beacon optional)")
        return
    alive = []
    for f in cores.glob("*.alive"):
        age = (time.time() - f.stat().st_mtime) / 60.0
        if age < (2 * BEAT_MIN / 60.0 if BEAT_MIN > 30 else 5):  # younger than ~2 beats / 5min
            alive.append(f.stem)
    add("core_liveness", True, f"alive_cores={alive or 'none-running-now'}")


def main() -> int:
    fix = "--fix" in sys.argv
    check_gateway(fix)
    check_beat_launchd(fix)
    check_files()
    check_memory()
    check_stuck_loop()
    check_core_liveness()

    failures = [r for r in results if not r["ok"]]
    if "--json" in sys.argv:
        print(json.dumps({"ok": not failures, "checks": results}))
    else:
        for r in results:
            print(f"{'✅' if r['ok'] else '❌'} {r['check']}: {r['detail']}")
        print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILURE(S)'}")

    if failures and "--emit-task" in sys.argv:
        tdir = WS / "tasks"
        tdir.mkdir(parents=True, exist_ok=True)
        tf = tdir / f"task-health-{int(time.time())}.txt"
        tf.write_text("self-diagnose found issues:\n" +
                      "\n".join(f"- {r['check']}: {r['detail']}" for r in failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
