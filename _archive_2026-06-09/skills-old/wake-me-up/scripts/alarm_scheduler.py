#!/usr/bin/env python3
"""
alarm_scheduler — multi-tenant daily wake-up for aniccaai.com/alarm subscribers.

Runs every minute (launchd). Reads active subscribers from Supabase
`subscriber_profiles`, and for anyone whose wake_time == now (in their tz) and who
hasn't been fired today, launches the wake-me-up loop for their phone with the
generic (non-personal) persona. The Stripe webhook populates the table.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ENV = (Path.home() / ".openclaw" / ".env").read_text()
SKILL = Path.home() / ".openclaw" / "skills" / "wake-me-up"
STATE = SKILL / "state" / "alarm_fired.json"


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def subscribers():
    url = env("SUPABASE_URL")
    key = env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return []
    req = urllib.request.Request(
        f"{url}/rest/v1/subscriber_profiles?status=eq.active&select=phone,wake_time,tz,name",
        headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[scheduler] supabase read failed: {e}", file=sys.stderr)
        return []


def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    try:
        fired = json.loads(STATE.read_text())
    except Exception:
        fired = {}

    subs = subscribers()
    if not subs:
        return
    # bring the realtime bridge up once if anyone is due soon
    due = []
    for s in subs:
        tz = s.get("tz") or "Asia/Tokyo"
        now = datetime.now(ZoneInfo(tz)) if tz else datetime.now(timezone(timedelta(hours=9)))
        if now.strftime("%H:%M") == (s.get("wake_time") or "")[:5]:
            today = now.strftime("%Y-%m-%d")
            if fired.get(s["phone"]) != today:
                due.append((s, today))

    if not due:
        return
    subprocess.run(["bash", str(SKILL / "scripts" / "ensure-bridge.sh")], capture_output=True, timeout=120)

    for s, today in due:
        # launch the re-call-until-awake loop in the background, generic persona
        env_call = {**os.environ, "WAKE_MODE": "wakeup_generic"}
        subprocess.Popen(
            [sys.executable, str(SKILL / "scripts" / "wake_loop.py"), s["phone"], (s.get("name") or "there")],
            env=env_call, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fired[s["phone"]] = today
        print(f"[scheduler] fired wake for {s['phone'][:6]}... at {s.get('wake_time')}")

    STATE.write_text(json.dumps(fired, ensure_ascii=False))


if __name__ == "__main__":
    main()
