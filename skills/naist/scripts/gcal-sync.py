#!/usr/bin/env python3
"""gcal-sync.py — push schedule-<term>.json events to Google Calendar via gog CLI.

Per v1.8 SKILL.md: {{profile.education.institution}} class events + 健康診断 + announced events from
~/.openclaw/workspace/naist/<slug>/schedule-*.json are upserted into the user's
primary calendar at <slug>'s account using `gog calendar create`.

Idempotent: maintains a ledger at
~/.openclaw/workspace/naist/<slug>/gcal-events-ledger.json keyed by
(course_code, session_n, date) so re-runs don't duplicate events. Existing
events present in the ledger are skipped (or updated via `gog calendar update`
if the title/topic/instructor changed).

Auth: GOG_KEYRING_PASSWORD must be set (or in ~/.openclaw/.env). Account {{profile.lateness.stakeholders.channel}}
is read from <slug>/profile.json::naist.personal_gmail. NEVER use Google MCP /
agent-{{profile.lateness.stakeholders.channel}} / gcloud — only `gog`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

SLUG = os.environ.get("SLUG", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"
GOG = "/opt/homebrew/bin/gog"


def fail(msg: str, code: int = 1) -> None:
    print(f"gcal-sync[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def load_env_file(path: Path, env: dict[str, str]) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_account(slug: str) -> str:
    p = STATE_ROOT / slug / "profile.json"
    if p.exists():
        prof = json.loads(p.read_text())
        em = prof.get("personal_gmail")
        if em:
            return em
    fail("personal_gmail missing in profile.json")
    return ""  # unreachable


def get_slack_channel(slug: str) -> str:
    p = STATE_ROOT / slug / "slack_channel.txt"
    return p.read_text().strip() if p.exists() else "{{profile.channels.reportChannel}}"


def slack_post(text: str, channel: str) -> None:
    if DRY_RUN or not SLACK_TOKEN:
        print(f"[DRY] Slack: {text[:160]}")
        return
    import urllib.request
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception as e:
        print(f"slack_post error: {e}", file=sys.stderr)


def gog(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    r = subprocess.run([GOG, *args], capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def event_key(course_code: str, n: int, ev_date: str) -> str:
    return f"{course_code}#{n}@{ev_date}"


def make_summary(course: dict, sess: dict) -> str:
    return f"[{{profile.education.institution}}] {course['name']} #{sess['n']}: {sess['topic'][:40]}"


def make_description(course: dict, sess: dict) -> str:
    return (
        f"科目: {course['name']} ({course['code']})\n"
        f"第{sess['n']}回 / {sess['period']}限\n"
        f"教員: {sess['instructor']}\n"
        f"教室: {course['default_room']}\n"
        f"テーマ: {sess['topic']}"
    )


def upsert_class_event(course: dict, sess: dict, ledger: dict, account: str, env: dict[str, str]) -> tuple[bool, str]:
    key = event_key(course["code"], sess["n"], sess["date"])
    if key in ledger:
        return False, f"skip (ledger hit: {ledger[key]})"
    start_t, end_t = sess["time"].split("-")
    args = [
        "calendar", "create", "primary",
        "--account", account,
        "--summary", make_summary(course, sess),
        "--from", f"{sess['date']}T{start_t}:00+09:00",
        "--to", f"{sess['date']}T{end_t}:00+09:00",
        "--description", make_description(course, sess),
        "--location", course["default_room"],
        "-j",
    ]
    code, out, err = gog(args, env)
    if code != 0:
        return False, f"gog error: {err[:200]}"
    try:
        ev = json.loads(out)
        eid = ev.get("event", {}).get("id") or ev.get("id") or "?"
    except Exception:
        eid = "(unparsed)"
    ledger[key] = eid
    return True, f"created {eid}"


def upsert_other_event(ev: dict, ledger: dict, account: str, env: dict[str, str]) -> tuple[bool, str]:
    key = f"OTHER:{ev['title']}@{ev['date']}"
    if key in ledger:
        return False, f"skip (ledger hit: {ledger[key]})"
    args = [
        "calendar", "create", "primary",
        "--account", account,
        "--summary", f"[{{profile.education.institution}}] {ev['title']}",
        "--from", ev["date"],
        "--to", ev["date"],
        "--all-day",
        "-j",
    ]
    code, out, err = gog(args, env)
    if code != 0:
        return False, f"gog error: {err[:200]}"
    try:
        eid = json.loads(out).get("event", {}).get("id") or json.loads(out).get("id") or "?"
    except Exception:
        eid = "(unparsed)"
    ledger[key] = eid
    return True, f"created {eid}"


def main() -> int:
    if not SLUG:
        fail("SLUG env required")

    env = dict(os.environ)
    load_env_file(Path.home() / ".openclaw" / ".env", env)
    load_env_file(STATE_ROOT / SLUG / "secrets.env", env)
    if "GOG_KEYRING_PASSWORD" not in env:
        fail("GOG_KEYRING_PASSWORD not set (~/.openclaw/.env or per-slug secrets.env)")

    account = get_account(SLUG)
    channel = get_slack_channel(SLUG)

    slug_dir = WORKSPACE / SLUG
    slug_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = slug_dir / "gcal-events-ledger.json"
    ledger: dict = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}

    schedule_files = sorted(slug_dir.glob("schedule-*.json"))
    if not schedule_files:
        slack_post(f":warning: gcal-sync[{SLUG}]: no schedule-*.json files yet — run edu-portal-check first", channel)
        return 0

    created_count = 0
    skipped_count = 0
    error_count = 0
    errors: list[str] = []

    for sf in schedule_files:
        sched = json.loads(sf.read_text())
        for course in sched.get("courses", []):
            for sess in course.get("sessions", []):
                ok, msg = upsert_class_event(course, sess, ledger, account, env)
                if ok:
                    created_count += 1
                elif "skip" in msg:
                    skipped_count += 1
                else:
                    error_count += 1
                    errors.append(f"{course['code']}#{sess['n']}: {msg}")
                print(f"  [{course['code']} #{sess['n']} {sess['date']}] {msg}")
        for ev in sched.get("other_events", []):
            ok, msg = upsert_other_event(ev, ledger, account, env)
            if ok:
                created_count += 1
            elif "skip" in msg:
                skipped_count += 1
            else:
                error_count += 1
                errors.append(f"OTHER:{ev['title']}: {msg}")
            print(f"  [OTHER {ev['date']} {ev['title']}] {msg}")

    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2))

    msg_lines = [
        f":calendar: *gcal-sync ({SLUG})* — created={created_count} / skipped={skipped_count} / errors={error_count}",
        f"`{ledger_path}` ({len(ledger)} events tracked)",
    ]
    if errors:
        msg_lines.append(":warning: errors:\n" + "\n".join(errors[:5]))
    slack_post("\n".join(msg_lines), channel)

    print(f"\n=== gcal-sync[{SLUG}] done: created={created_count} skipped={skipped_count} errors={error_count} ===")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
