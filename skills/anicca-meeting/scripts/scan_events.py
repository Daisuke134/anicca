#!/usr/bin/env python3
"""
scan_events — calendar → autonomous bot trigger.

Run every few minutes via cron. Scans the operator's Google Calendar for
upcoming events tagged for autonomous Anicca attendance. For each tagged event
that's about to start, generates a deck via deck_generator.py and POSTs to
pipecat-meeting /api/launch so a Recall bot joins the meeting on schedule.

Event tagging (anywhere in event SUMMARY or DESCRIPTION):
  [BOT-LT]        → 5-min lightning talk, English (default lang)
  [BOT-LT-JA]     → 5-min LT, Japanese
  [BOT-SALES-30]  → 30-min sales demo, English
  [BOT-COMEDY-JA] → 3-min flip comedy, Japanese
  [BOT-COMEDY-EN] → 3-min flip comedy, English
  [BOT-DECK=<id>] → use a specific pre-baked deck (skips generation)

Required event fields:
  - hangoutLink (= conferenceData → google_meet)
    Zoom / Teams URLs in event.location are also accepted.
  - dateTime start (all-day events are skipped — bot can't time those)

Idempotency:
  state/launched-events.jsonl records {event_id, launched_at_ms, bot_id}
  per launched event. Re-running the cron never re-launches the same event.
  Trigger window is "start_time - 90s .. start_time + 300s" so the bot has a
  few minutes of waiting room slack.

Usage:
  scan_events.py                      # production: scan + launch
  scan_events.py --dry-run            # print plan, no API calls
  scan_events.py --window-min 90      # look 90min ahead (default 30)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
SKILL_DIR = Path(__file__).resolve().parent.parent
DECKS_DIR = SKILL_DIR / "decks"
STATE_DIR = SKILL_DIR / "state"
STATE_FILE = STATE_DIR / "launched-events.jsonl"

PIPECAT_URL_FILE = Path.home() / ".openclaw" / "state" / "anicca_meeting_url.txt"

# Tag → deck-generator args
# default_deck_id is used ONLY when its language matches the tag language;
# otherwise the script falls through to deck_generator.py so the deck is
# actually in the right language. Hardcoded English defaults for JA tags
# was a bug (caught E2E 2026-05-29: [BOT-LT-JA] ran the English deck).
TAG_TABLE = [
    # (regex, type, lang, duration, default_deck_id_if_no_gen)
    (r"\[BOT-LT-JA\]",     "lt",     "ja", 5,  None),  # generate JA fresh
    (r"\[BOT-LT(?!-)\]",   "lt",     "en", 5,  "default-anicca-lt-5min"),
    (r"\[BOT-SALES-30\]",  "sales",  "en", 30, "sales-demo-30min"),
    (r"\[BOT-SALES\]",     "sales",  "en", 30, "sales-demo-30min"),
    (r"\[BOT-COMEDY-JA\]", "comedy", "ja", 3,  "comedy-3min"),  # JA bundled exists
    (r"\[BOT-COMEDY-EN\]", "comedy", "en", 3,  None),
    (r"\[BOT-COMEDY\]",    "comedy", "ja", 3,  "comedy-3min"),
]
DECK_ID_RE = re.compile(r"\[BOT-DECK=([^\]]+)\]")


def env(key: str, default: str = "") -> str:
    """Read from .env directly to match the rest of openclaw skills."""
    envp = Path.home() / ".openclaw" / ".env"
    try:
        for line in envp.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return os.environ.get(key, default)


def gcal_account() -> str:
    return env("GOG_ACCOUNT") or "keiodaisuke@gmail.com"


def fetch_events(window_min: int) -> list[dict]:
    now = datetime.now(JST)
    to = (now + timedelta(minutes=window_min)).strftime("%Y-%m-%d")
    cmd = ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
           "--account", gcal_account(), "--from", "today", "--to", to,
           "--all-pages", "--max", "250"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          env={**os.environ,
                               "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
                               "GOG_ACCOUNT": gcal_account()})
    if out.returncode != 0:
        print(f"[scan] gog failed: {out.stderr[:200]}", file=sys.stderr)
        return []
    try:
        d = json.loads(out.stdout)
    except json.JSONDecodeError as e:
        print(f"[scan] parse failed: {e}", file=sys.stderr)
        return []
    return d if isinstance(d, list) else d.get("events", d.get("items", []))


def already_launched(event_id: str) -> bool:
    if not STATE_FILE.exists():
        return False
    for line in STATE_FILE.read_text().splitlines():
        try:
            r = json.loads(line)
            if r.get("event_id") == event_id:
                return True
        except Exception:
            continue
    return False


def record_launch(event_id: str, summary: str, bot_id: str | None, deck_id: str) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    with STATE_FILE.open("a") as f:
        f.write(json.dumps({
            "event_id": event_id,
            "summary": summary,
            "bot_id": bot_id,
            "deck_id": deck_id,
            "launched_at_ms": int(time.time() * 1000),
        }, ensure_ascii=False) + "\n")


def classify(event: dict) -> dict | None:
    """Return {type, lang, duration, deck_id_hint} if the event is tagged for
    bot attendance. None otherwise."""
    text = " ".join([event.get("summary", ""), event.get("description", "")])
    # Specific deck override wins
    m = DECK_ID_RE.search(text)
    if m:
        return {"type": "manual", "lang": None, "duration": None,
                "deck_id": m.group(1).strip()}
    for pattern, typ, lang, dur, default_deck_id in TAG_TABLE:
        if re.search(pattern, text):
            return {"type": typ, "lang": lang, "duration": dur,
                    "deck_id": default_deck_id}
    return None


def meeting_url(event: dict) -> str | None:
    # Native hangouts/Meet
    if event.get("hangoutLink"):
        return event["hangoutLink"]
    conf = event.get("conferenceData", {}) or {}
    for ep in (conf.get("entryPoints") or []):
        if ep.get("entryPointType") == "video":
            return ep.get("uri")
    # Zoom / Teams in location
    loc = event.get("location", "") or ""
    for proto in ("https://zoom.us/", "https://us02web.zoom.us/", "https://teams.microsoft.com/",
                  "https://meet.google.com/"):
        if proto in loc:
            m = re.search(r"(https?://[^\s\]]+)", loc)
            if m:
                return m.group(1)
    return None


def generate_deck_for_event(event: dict, plan: dict) -> Path | None:
    """If plan has a default deck_id and that file exists, use it as-is.
    Otherwise call deck_generator.py to produce a fresh one."""
    if plan["deck_id"]:
        bundled = DECKS_DIR / f"{plan['deck_id']}.json"
        if bundled.exists():
            return bundled

    # Generate
    DECKS_DIR.mkdir(exist_ok=True)
    out = DECKS_DIR / f"event-{event.get('id', 'unknown')}.json"
    cmd = [
        sys.executable, str(SKILL_DIR / "scripts" / "deck_generator.py"),
        "--title", event.get("summary", "untitled")[:140],
        "--type", plan["type"],
        "--duration", str(plan["duration"] or 5),
        "--lang", plan["lang"] or "en",
        "--description", (event.get("description") or "")[:1500],
        "--out", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "DEEPSEEK_API_KEY": env("DEEPSEEK_API_KEY")})
    if r.returncode != 0:
        print(f"[scan] deck gen failed for '{event.get('summary')}': {r.stderr[:200]}", file=sys.stderr)
        return None
    return out


def pipecat_meeting_url() -> str:
    explicit = os.environ.get("ANICCA_MEETING_API_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    try:
        return PIPECAT_URL_FILE.read_text().strip().rstrip("/")
    except FileNotFoundError:
        return "http://127.0.0.1:7861"


def launch_bot(meet_url: str, deck_path: Path, bot_name: str = "Anicca") -> str | None:
    """POST to /api/launch via localhost (server stash-passes deck path)."""
    body = json.dumps({
        "meeting_url": meet_url,
        "bot_name": bot_name,
        "deck": str(deck_path),
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:7861/api/launch",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        return d.get("id") or d.get("bot_id")
    except Exception as e:
        print(f"[scan] /api/launch failed: {e}", file=sys.stderr)
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--window-min", type=int, default=30,
                   help="how many minutes ahead to scan (default 30)")
    p.add_argument("--lead-sec", type=int, default=90,
                   help="launch bot this many seconds BEFORE start_time")
    p.add_argument("--slack-sec", type=int, default=300,
                   help="if event already started up to this many seconds ago, still launch")
    args = p.parse_args()

    now = datetime.now(JST)
    events = fetch_events(args.window_min)
    print(f"[scan] {now.isoformat()}  events in next {args.window_min}min: {len(events)}", file=sys.stderr)

    launched = 0
    for e in events:
        s = e.get("start", {})
        dt_str = s.get("dateTime")
        if not dt_str:
            continue  # all-day events skipped
        start = datetime.fromisoformat(dt_str).astimezone(JST)
        sec_to_start = (start - now).total_seconds()
        # Outside launch window (too early or too late)
        if sec_to_start > args.lead_sec:
            continue
        if sec_to_start < -args.slack_sec:
            continue

        plan = classify(e)
        if not plan:
            continue

        event_id = e.get("id") or e.get("iCalUID") or ""
        if not event_id:
            continue
        if already_launched(event_id):
            continue

        url = meeting_url(e)
        if not url:
            print(f"[scan] tagged but no meet url: {e.get('summary')}", file=sys.stderr)
            continue

        print(f"[scan] WILL LAUNCH  {e.get('summary','?')[:60]}  in {int(sec_to_start)}s  → {url}",
              file=sys.stderr)
        if args.dry_run:
            launched += 1
            continue

        deck_path = generate_deck_for_event(e, plan)
        if not deck_path:
            continue
        bot_id = launch_bot(url, deck_path)
        if bot_id:
            record_launch(event_id, e.get("summary", "?"), bot_id, plan.get("deck_id") or deck_path.stem)
            print(f"[scan] LAUNCHED  event={event_id[:12]}  bot={bot_id[:12]}  deck={deck_path.name}",
                  file=sys.stderr)
            launched += 1

    print(json.dumps({"scanned": len(events), "launched": launched, "dry_run": args.dry_run},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
