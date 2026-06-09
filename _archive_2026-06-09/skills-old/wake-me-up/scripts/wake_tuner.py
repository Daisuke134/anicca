#!/usr/bin/env python3
"""
wake_tuner — the self-improvement loop (B6).

Reads the history of wake outcomes (wake_outcomes.jsonl, written by wake_loop)
and learns how hard Anicca should push to actually get this person up. Writes
wake_tuning.json, which wake_loop reads on the NEXT call:

  - intensity: 'normal' | 'high'   (high = extra-relentless persona)
  - suggested_start_offset_min     (advisory: how many min earlier to start)
  - avg_attempts (last 7 days), note

Heuristic (sleep-inertia: more attempts/failures => push harder & earlier):
  avg attempts >= 3   OR any miss in last 3 days  -> intensity high, start 10m earlier
  avg attempts <= 1.3 and no misses               -> intensity normal, no offset
Runs after each wake (run.sh) or on its own cron.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"
OUTCOMES = STATE / "wake_outcomes.jsonl"
TUNING = STATE / "wake_tuning.json"
ENV = (Path.home() / ".openclaw" / ".env").read_text()


def env(n, d=""):
    m = re.search(rf"^{n}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else d)


def slack(text):
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": env("SLACK_CHANNEL_ID"), "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {env('SLACK_BOT_TOKEN')}"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def recent(days=7):
    if not OUTCOMES.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for line in OUTCOMES.read_text().splitlines():
        try:
            r = json.loads(line)
            if datetime.fromisoformat(r["ts"]) >= cutoff:
                out.append(r)
        except Exception:
            continue
    return out


def main():
    hist = recent(7)
    if not hist:
        print("[tuner] no history yet — keeping defaults")
        TUNING.write_text(json.dumps({"intensity": "normal", "suggested_start_offset_min": 0,
                                      "avg_attempts": None, "note": "no data"}, ensure_ascii=False))
        return
    attempts = [r.get("attempts", 1) for r in hist]
    avg = round(sum(attempts) / len(attempts), 2)
    misses = sum(1 for r in hist[-3:] if not r.get("awake"))
    if avg >= 3 or misses > 0:
        tuning = {"intensity": "high", "suggested_start_offset_min": 10}
        note = f"押しが足りない (平均{avg}回/直近ミス{misses}) → intensity=high, 10分早く"
    elif avg <= 1.3:
        tuning = {"intensity": "normal", "suggested_start_offset_min": 0}
        note = f"順調 (平均{avg}回) → intensity=normal"
    else:
        tuning = {"intensity": "normal", "suggested_start_offset_min": 5}
        note = f"やや手こずる (平均{avg}回) → 5分早めを推奨"
    tuning.update({"avg_attempts": avg, "note": note, "updated": datetime.now().isoformat(timespec="seconds")})
    TUNING.write_text(json.dumps(tuning, ensure_ascii=False, indent=2))
    print(f"[tuner] {note}")
    slack(f"🧠 wake自己改善: {note} (直近{len(hist)}回分から学習)")


if __name__ == "__main__":
    main()
