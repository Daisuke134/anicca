#!/usr/bin/env python3
"""
wake-me-up: realtime phone wake-up loop.

Places a realtime (Twilio <-> Gemini Live) wake-up call, watches the call
outcome, and keeps re-calling at a fixed gap until the person is provably
awake (answered + held a real conversation) or the attempt cap is reached.
Reports the run to Slack.

Entity-agnostic: pass the phone number + name; reads secrets from ~/.openclaw/.env.
The realtime bridge (imokenet) must be reachable; its public URL is read from
imokenet/state/public_url.txt (kept fresh by the launchd-managed run-bridge.sh).
"""
import base64
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

ENV = (Path.home() / ".openclaw" / ".env").read_text()
URL_FILE = Path.home() / ".openclaw" / "workspace" / "imokenet" / "state" / "public_url.txt"

# Tunables (env-overridable)
AWAKE_MIN_SEC = int(os.environ.get("WAKE_AWAKE_MIN_SEC", "20"))   # answered+>=this => awake
RETRY_GAP_SEC = int(os.environ.get("WAKE_RETRY_GAP_SEC", "60"))   # gap between re-calls
MAX_ATTEMPTS = int(os.environ.get("WAKE_MAX_ATTEMPTS", "12"))     # hard cap
POLL_TIMEOUT_SEC = int(os.environ.get("WAKE_POLL_TIMEOUT_SEC", "120"))


def env(name):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    if not m:
        raise RuntimeError(f"missing {name} in ~/.openclaw/.env")
    return m.group(1).strip().strip('"').strip("'")


def public_base_url():
    url = URL_FILE.read_text().strip()
    if not url:
        raise RuntimeError("public_url.txt is empty; is the imokenet bridge running?")
    return url.rstrip("/")


def bridge_healthy(base):
    try:
        with urllib.request.urlopen(f"{base}/healthz", timeout=8) as r:
            return json.loads(r.read().decode()).get("ok") is True
    except Exception:
        return False


def twilio(method, path, data=None):
    sid = env("TWILIO_ACCOUNT_SID")
    token = env("TWILIO_AUTH_TOKEN")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}{path}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    if body:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def place_call(to_num, name, base):
    q = {"name": name}
    _mode = os.environ.get("WAKE_MODE", "")  # 'wakeup_generic' for SaaS subscribers
    if _mode:
        q["mode"] = _mode
    twiml_url = f"{base}/twiml?{urllib.parse.urlencode(q)}"
    call = {
        "To": to_num, "From": env("TWILIO_PHONE_NUMBER"),
        "Url": twiml_url, "Method": "GET",
    }
    # WAKE_RECORD=1 -> dual-channel recording (for promo material / self-improvement logs)
    if os.environ.get("WAKE_RECORD") == "1":
        call["Record"] = "true"
        call["RecordingChannels"] = "dual"
    res = twilio("POST", "/Calls.json", call)
    return res.get("sid")


def wait_for_outcome(call_sid):
    """Poll until the call reaches a terminal state. Returns (status, duration_sec)."""
    terminal = {"completed", "no-answer", "busy", "failed", "canceled"}
    deadline = time.time() + POLL_TIMEOUT_SEC
    last = ("unknown", 0)
    while time.time() < deadline:
        d = twilio("GET", f"/Calls/{call_sid}.json")
        status = d.get("status")
        dur = int(d.get("duration") or 0)
        last = (status, dur)
        if status in terminal:
            return last
        time.sleep(3)
    return last


def slack(text):
    try:
        token = env("SLACK_BOT_TOKEN")
        channel = env("SLACK_CHANNEL_ID")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {token}"}, method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        if not resp.get("ok"):
            print(f"[wake] slack api error: {resp.get('error')}", file=sys.stderr)
    except Exception as e:
        print(f"[wake] slack failed: {e}", file=sys.stderr)


def is_awake(status, dur, min_sec=AWAKE_MIN_SEC):
    """Pure decision: a call that was answered and lasted long enough = a real
    conversation happened = awake."""
    return status == "completed" and dur >= min_sec


def wake_run(to_num, name, base, sleep_fn=time.sleep):
    """Re-call until awake or attempt cap. Returns (awake, log). Pure-ish:
    delegates to module-level place_call / wait_for_outcome (monkeypatchable)."""
    log = []
    awake = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        sid = place_call(to_num, name, base)
        status, dur = wait_for_outcome(sid)
        log.append(f"#{attempt} {status} {dur}s")
        print(f"[wake] attempt {attempt}: sid={sid} status={status} dur={dur}s", flush=True)
        if is_awake(status, dur):
            awake = True
            break
        if attempt < MAX_ATTEMPTS:
            sleep_fn(RETRY_GAP_SEC)
    return awake, log


def main():
    to_num = sys.argv[1] if len(sys.argv) > 1 else prof.phone()
    name = sys.argv[2] if len(sys.argv) > 2 else prof.name()

    base = public_base_url()
    if not bridge_healthy(base):
        slack(f"☎️ wake-me-up: bridge UNHEALTHY at {base} — aborting wake for {name}. Fix imokenet launchd.")
        print("bridge unhealthy", file=sys.stderr)
        sys.exit(1)

    awake, log = wake_run(to_num, name, base)
    summary = " | ".join(log)
    if awake:
        slack(f"☀️ {name} is up. wake-me-up succeeded after {len(log)} call(s): {summary}")
    else:
        slack(f"😴 {name} NOT confirmed awake after {len(log)} calls (cap {MAX_ATTEMPTS}): {summary}")
    print(json.dumps({"awake": awake, "attempts": len(log), "log": log}))
    sys.exit(0 if awake else 2)


if __name__ == "__main__":
    main()
