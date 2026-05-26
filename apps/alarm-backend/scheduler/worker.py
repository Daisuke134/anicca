#!/usr/bin/env python3
"""
alarm-backend scheduler worker (Railway, always-on).

Replaces the two Mac-mini launchd jobs:
  - alarm_scheduler.py  (every 60s)  — wake SaaS subscribers at their wake_time
  - saas_lateness.py    (every 900s) — never-be-late calls/renraku from calendar+location

The original skill scripts are reused UNMODIFIED. At boot we reproduce the
`~/.openclaw` filesystem layout they expect (.env, the bridge public_url.txt, a
PII-free placeholder profile, and the scripts at their canonical skill paths),
then drive their `main()` on a timer. Secrets come from Railway env vars, never
from the repo.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HOME = Path.home()
OPENCLAW = HOME / ".openclaw"
PKG = Path(__file__).resolve().parent

# Secrets the reused scripts read out of ~/.openclaw/.env (set as Railway env vars).
ENV_VARS = [
    "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
    "COMPOSIO_API_KEY", "GOOGLE_API_KEY",
    "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID",
    "GEMINI_API_KEY",
]

# bundled script -> canonical path under ~/.openclaw (so Path.home() resolution works)
SCRIPT_LAYOUT = {
    "alarm_scheduler.py": "skills/wake-me-up/scripts/alarm_scheduler.py",
    "wake_loop.py": "skills/wake-me-up/scripts/wake_loop.py",
    "ensure-bridge.sh": "skills/wake-me-up/scripts/ensure-bridge.sh",
    "saas_lateness.py": "skills/lateness-guard/scripts/saas_lateness.py",
    "lateness_check.py": "skills/lateness-guard/scripts/lateness_check.py",
    "gcal_departures.py": "skills/lateness-guard/scripts/gcal_departures.py",
    "anicca_profile.py": "skills/_shared/anicca_profile.py",
}

WAKE_SCHEDULER = OPENCLAW / "skills" / "wake-me-up" / "scripts" / "alarm_scheduler.py"
SAAS_LATENESS = OPENCLAW / "skills" / "lateness-guard" / "scripts" / "saas_lateness.py"

WAKE_EVERY = int(os.environ.get("WAKE_SCHED_EVERY_SEC", "60"))
LATE_EVERY = int(os.environ.get("LATE_SCHED_EVERY_SEC", "900"))


def bootstrap():
    """Recreate the ~/.openclaw layout the reused skill scripts expect."""
    OPENCLAW.mkdir(parents=True, exist_ok=True)

    # 1) .env — the scripts read secrets by regex out of this file.
    lines = [f"{k}={os.environ[k]}" for k in ENV_VARS if os.environ.get(k)]
    (OPENCLAW / ".env").write_text("\n".join(lines) + "\n")

    # 2) bridge public URL — replaces the Mac-mini cloudflared tunnel file.
    bridge = (os.environ.get("BRIDGE_PUBLIC_URL") or "").rstrip("/")
    if not bridge:
        raise RuntimeError("BRIDGE_PUBLIC_URL is required (the Railway bridge service URL)")
    st = OPENCLAW / "workspace" / "imokenet" / "state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "public_url.txt").write_text(bridge + "\n")

    # 3) PII-free placeholder profile so module-level prof.home_latlon() never crashes.
    #    SaaS logic uses per-subscriber data from Supabase, not this file.
    idn = OPENCLAW / "identity"
    idn.mkdir(parents=True, exist_ok=True)
    (idn / "profile.json").write_text(json.dumps({
        "identity": {"legalName": "", "stageName": "", "preferredName": "there", "homeAddress": ""},
        "contact": {"phone": "", "personalEmail": "", "workEmail": ""},
        "location": {"homeLat": 35.68, "homeLon": 139.76},
        "alarm": {"wakeTime": "07:00"},
        "timezone": "Asia/Tokyo",
        "lateness": {"defaultSenderType": "legal", "stakeholders": []},
    }))

    # 4) place the reused scripts at their canonical skill paths.
    for src, rel in SCRIPT_LAYOUT.items():
        dst = OPENCLAW / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PKG / src, dst)
    os.chmod(OPENCLAW / "skills" / "wake-me-up" / "scripts" / "ensure-bridge.sh", 0o755)

    # 5) state dirs the scripts write into (saas_lateness does not mkdir its own).
    (OPENCLAW / "skills" / "lateness-guard" / "state").mkdir(parents=True, exist_ok=True)
    (OPENCLAW / "skills" / "wake-me-up" / "state").mkdir(parents=True, exist_ok=True)


def run(script: Path, label: str, timeout: int):
    """Run a scheduler script once as a child; never let a crash kill the loop."""
    try:
        r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out:
            print(f"[{label}] {out[-800:]}", flush=True)
        if err:
            print(f"[{label}] stderr: {err[-800:]}", file=sys.stderr, flush=True)
        if r.returncode != 0:
            print(f"[{label}] exit={r.returncode}", file=sys.stderr, flush=True)
    except subprocess.TimeoutExpired:
        print(f"[{label}] timeout after {timeout}s", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[{label}] crashed: {e}\n{traceback.format_exc()}", file=sys.stderr, flush=True)


def main():
    bootstrap()
    print(f"[worker] booted. bridge={os.environ.get('BRIDGE_PUBLIC_URL')} "
          f"wake_every={WAKE_EVERY}s late_every={LATE_EVERY}s", flush=True)
    last_late = 0.0
    while True:
        # wake scheduler returns fast (spawns the re-call loop in the background)
        run(WAKE_SCHEDULER, "wake-sched", timeout=120)
        now = time.time()
        if now - last_late >= LATE_EVERY:
            run(SAAS_LATENESS, "saas-late", timeout=600)
            last_late = now
        time.sleep(WAKE_EVERY)


if __name__ == "__main__":
    main()
