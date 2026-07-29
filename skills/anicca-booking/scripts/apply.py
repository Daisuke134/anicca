#!/usr/bin/env python3
"""
apply — log approved candidates and insert PROPOSED gcal entries.

The REAL apply step (form-fill + submit + verify) is NOT done here.
SKILL.md tells Anicca to use camofox via natural-language reasoning, because
each event site has a different form structure — hard-coded scripts cannot
handle that. apply.py is the deterministic ledger; the agent does the rest.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
STATE_HOME = Path(os.environ.get(
    "LIFE_MANAGER_STATE_HOME",
    Path.home() / ".local/state/life-manager",
)).expanduser()
sys.path.insert(0, str(REPO_ROOT / "skills/_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
ENV_PATH = STATE_HOME / ".env"
ENV = ENV_PATH.read_text() if ENV_PATH.is_file() else ""
HISTORY = STATE_HOME / "state/anicca-booking/booking-history.jsonl"
HISTORY.parent.mkdir(parents=True, exist_ok=True)


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def slack(text):
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": env("SLACK_CHANNEL_ID"), "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {env('SLACK_BOT_TOKEN')}"},
            method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"[apply] slack failed: {e}", file=sys.stderr)


def log_history(record):
    record["ts"] = datetime.now(JST).isoformat()
    with HISTORY.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def insert_gcal(cand, status):
    """gcal-policy.sh create (HARD RULE #19, named-arg API)."""
    policy = REPO_ROOT / "skills/_shared/lib/gcal-policy.sh"
    if not policy.exists():
        return False, "gcal-policy.sh missing"
    title = f"[{status}] {cand['domain']}: {cand['title'][:80]}"
    slot = cand["slot"]
    desc = f"booked by anicca-booking\nurl: {cand.get('url','')}\nstatus: {status}"
    duration_min = max(60, min(slot.get("duration_min", 60), 120))
    from datetime import datetime as _dt, timedelta as _td
    start_dt = _dt.fromisoformat(slot["startIso"])
    end_iso = (start_dt + _td(minutes=duration_min)).isoformat(timespec="seconds")
    out = subprocess.run(
        ["bash", str(policy), "create",
         "--summary", title, "--from", slot["startIso"], "--to", end_iso,
         "--location", cand.get("location", ""), "--description", desc,
         "--skip-travel",
         "--check-conflict"],  # GATE 3 enforce at insert-time (race-safe)
        capture_output=True, text=True,
    )
    return out.returncode == 0, (out.stderr or out.stdout)[:300]


def main():
    if sys.stdin.isatty():
        print("[apply] expects JSON candidates on stdin", file=sys.stderr)
        sys.exit(2)
    candidates = json.loads(sys.stdin.read() or "[]")
    approved = [c for c in candidates if c.get("status") == "approved"]
    stats = {"scanned": len(candidates), "approved": len(approved),
             "applied": 0, "blocked": len(candidates) - len(approved),
             "slack_review": 0}
    # dedupe by url to avoid pushing the same event into multiple slots
    seen_urls = set()
    for cand in approved:
        u = cand.get("url", "")
        if u in seen_urls:
            continue
        seen_urls.add(u)
        log_history({"event": "candidate_approved", **cand})
        # PROPOSED gcal — the agent (SKILL.md) will upgrade to CONFIRMED after camofox apply
        ok, info = insert_gcal(cand, "PROPOSED")
        if ok:
            stats["applied"] += 1
            log_history({"event": "gcal_proposed", **cand})
        else:
            log_history({"event": "gcal_propose_failed", "reason": info, **cand})
        slack(f":calendar: *anicca-booking PROPOSED candidate*\n"
              f"domain: `{cand['domain']}` · slot {cand['slot']['startIso']} ({cand['slot']['duration_min']}min)\n"
              f"title: {cand['title'][:120]}\n"
              f"url: {u}\n"
              f"_agent now uses camofox to apply per SKILL.md and upgrade to CONFIRMED._")
        stats["slack_review"] += 1
        if stats["slack_review"] >= 5:
            break
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
