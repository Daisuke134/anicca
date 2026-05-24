#!/usr/bin/env python3
"""Apply jobs.json migration: -5 old {{profile.education.institution}} + 4 new {{profile.education.institution}} + 5 new auto-research crons.

Idempotent: if a target cron already exists by id, it's overwritten in place.
Removes the 5 old {{profile.education.institution}} crons by name. Backups jobs.json before mutating.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

JJ = Path(os.environ.get("JOBS_JSON", os.path.expanduser("~/.openclaw/cron/jobs.json")))

OLD_{{profile.education.institution}}_NAMES = {
    "naist-mail-digest",
    "naist-papers-daily",
    "naist-funds-weekly",
    "naist-events-weekly",
    "naist-deadline-reminder",
}

CHANNEL = "channel:{{profile.channels.reportChannel}}"


def naist_cron(name: str, expr: str, mode: str) -> dict:
    return {
        "id": name,
        "agentId": "anicca",
        "name": name,
        "schedule": {"kind": "cron", "expr": expr, "tz": "Asia/Tokyo"},
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": (
                "Execute the unified naist skill (v2). "
                "Read ~/.openclaw/skills/naist/SKILL.md and follow it. "
                f"Run: MODE={mode} bash ~/.openclaw/skills/naist/scripts/run.sh\n"
                "If ~/.openclaw/state/naist/<slug>/slack_channel.txt exists for an onboarded user, post per-user. "
                "Otherwise post a single status line; cron announce relays it to #metrics. "
                "Do NOT auto-send any homework reply: homework drafts must be Slack-confirmed (👍) before send-as.py is invoked. "
                "Do NOT call the message tool. Do NOT modify openclaw.json."
            ),
            "timeoutSeconds": 600,
            "env": {},
        },
        "delivery": {"mode": "announce", "channel": "slack", "to": CHANNEL, "bestEffort": True},
        "enabled": True,
        "state": {},
    }


def auto_research_cron(name: str, expr: str, mode: str) -> dict:
    return {
        "id": name,
        "agentId": "anicca",
        "name": name,
        "schedule": {"kind": "cron", "expr": expr, "tz": "Asia/Tokyo"},
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {
            "kind": "agentTurn",
            "message": (
                "Execute the auto-research orchestrator. "
                "Read ~/.openclaw/skills/auto-research/SKILL.md and follow it. "
                f"Run: MODE={mode} bash ~/.openclaw/skills/auto-research/scripts/run.sh\n"
                "Round-robin one project from projects.yaml. Honor human_flags Slack ack gate. "
                "Verify every citation against OpenAlex before drafting commits. "
                "Do NOT call the message tool. Do NOT modify openclaw.json."
            ),
            "timeoutSeconds": 1800,
            "env": {},
        },
        "delivery": {"mode": "announce", "channel": "slack", "to": CHANNEL, "bestEffort": True},
        "enabled": True,
        "state": {},
    }


NEW_{{profile.education.institution}} = [
    naist_cron("naist-pull",            "*/15 * * * *", "pull"),
    naist_cron("naist-morning-rollup",  "0 9 * * *",    "morning-rollup"),
    naist_cron("naist-friday-rollup",   "0 18 * * 5",   "friday-rollup"),
    naist_cron("naist-deadline-ical",   "0 7 * * *",    "deadline-ical"),
]

NEW_AR = [
    auto_research_cron("auto-research-literature",  "0 1 * * *", "literature"),
    auto_research_cron("auto-research-hypothesise", "0 2 * * *", "hypothesise"),
    auto_research_cron("auto-research-experiment",  "0 3 * * *", "experiment"),
    auto_research_cron("auto-research-write",       "0 4 * * *", "write"),
    auto_research_cron("auto-research-grant",       "0 5 * * 1", "grant"),
]


def main() -> int:
    if not JJ.exists():
        print(f"jobs.json missing at {JJ}", file=sys.stderr); return 66

    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    bak = JJ.with_suffix(JJ.suffix + f".bak.{ts}-pre-naist-v2-and-auto-research-apply")
    shutil.copy2(JJ, bak)

    data = json.loads(JJ.read_text())
    jobs = data.get("jobs", [])
    before = len(jobs)

    # remove old {{profile.education.institution}}
    removed = [j for j in jobs if j.get("name") in OLD_{{profile.education.institution}}_NAMES]
    jobs = [j for j in jobs if j.get("name") not in OLD_{{profile.education.institution}}_NAMES]
    new_ids = {c["id"] for c in NEW_{{profile.education.institution}} + NEW_AR}
    # idempotent: drop any prior copy of new ids before appending
    jobs = [j for j in jobs if j.get("id") not in new_ids]
    jobs.extend(NEW_{{profile.education.institution}})
    jobs.extend(NEW_AR)

    after = len(jobs)
    data["jobs"] = jobs

    # validate JSON round-trip
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(rendered)  # raises if invalid

    tmp = JJ.with_suffix(JJ.suffix + ".tmp.apply")
    tmp.write_text(rendered)
    tmp.replace(JJ)

    print(f"backup: {bak}")
    print(f"removed {len(removed)} old {{profile.education.institution}} crons: {[j['name'] for j in removed]}")
    print(f"added 4 new {{profile.education.institution}} + 5 new auto-research = {len(NEW_{{profile.education.institution}})+len(NEW_AR)} crons")
    print(f"jobs count: {before} → {after}  (delta {after - before:+d})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
