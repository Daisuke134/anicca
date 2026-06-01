#!/usr/bin/env python3
"""
fetch_recording — pull the dual-channel recording of a wake call as mp3.

Usage:
  fetch_recording.py <call_sid> [out.mp3]   # specific call
  fetch_recording.py --latest [out.mp3]     # most recent recording on the account

Recordings are produced when a call is placed with Record=true (WAKE_RECORD=1).
Saves to a real folder (~/anicca-wake-recordings) per the no-temp rule.
"""
import base64
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ENV = (Path.home() / ".openclaw" / ".env").read_text()
OUT_DIR = Path.home() / "anicca-wake-recordings"


def env(n, d=""):
    m = re.search(rf"^{n}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else d)


def api(path):
    sid, tok = env("TWILIO_ACCOUNT_SID"), env("TWILIO_AUTH_TOKEN")
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}{path}")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    args = [a for a in sys.argv[1:]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args and args[0] == "--latest":
        data = json.loads(api("/Recordings.json?PageSize=1"))
        recs = data.get("recordings", [])
        if not recs:
            print("no recordings on account", file=sys.stderr); sys.exit(1)
        rec = recs[0]
        out = args[1] if len(args) > 1 else None
    elif args:
        call_sid = args[0]
        data = json.loads(api(f"/Calls/{call_sid}/Recordings.json"))
        recs = data.get("recordings", [])
        if not recs:
            print(f"no recording for call {call_sid} (was it answered + Record=true?)", file=sys.stderr); sys.exit(1)
        rec = recs[0]
        out = args[1] if len(args) > 1 else None
    else:
        print(__doc__); sys.exit(2)

    sid = rec["sid"]
    dur = rec.get("duration")
    mp3 = api(f"/Recordings/{sid}.mp3")
    if not out:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"wake_{ts}_{sid[:8]}.mp3")
    Path(out).write_bytes(mp3)
    print(f"saved {out} ({len(mp3)} bytes, {dur}s)")


if __name__ == "__main__":
    main()
