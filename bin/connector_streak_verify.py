#!/usr/bin/env python3
"""connector_streak_verify.py — deterministic, no-human-loop daily verifier for the connector-loop's
7-day streak goal (docs/superpowers spec 2026-07-11 "connector 7日streak"). Runs ONCE per JST calendar
day (idempotent by date, safe to re-invoke), independently of the connector-core agent's own
self-report (REQ: lessons.jsonl `pattern_detected: "self-report-unreliable"` -- a fresh-spawn agent
self-report of "done" was already found to be fabricated once; this script re-derives every fact from
the same primary sources the agent itself reads/writes, never trusts a summary).

Per-day pass conditions (ALL must hold for day_pass:true), each independently re-verified here:
  1. cron_ok       -- ~/.openclaw/state/.connector-core-last-pass (touched ONLY on a genuinely
                       completed STEP0-5 pass, never on mere startup -- see connector-healthcheck.sh)
                       has today's JST civil date.
  2. registration  -- EITHER a CONFIRMED applications.jsonl row was appended today (JST) and its
                       event_id independently re-reads as status=="confirmed" via
                       `gog calendar event primary <event_id>` (own read-back, not the agent's own
                       claim), OR today's signals.json has horizon_full:true (the connector's own
                       honest "nothing to register, calendar is full" signal -- also valid).
                       Anything else (no registration AND horizon not full) is an honest day_pass:false
                       -- never excused.
  3. telegram      -- a real `openclaw message send` call for today's digest returns a messageId
                       (delivered:true is proven by that id, never assumed from a zero exit code alone
                       since dry-run also exits 0).

Every day's row (pass or fail) is appended to <CONNECTOR_STREAK_STATE_DIR>/connector-streak.jsonl.
Once the trailing streak of consecutive JST calendar days with day_pass:true reaches 7, a completion
email is sent via `gog gmail send` to CONNECTOR_STREAK_COMPLETION_EMAIL exactly once (guarded by a
separate marker file, never re-sent on a later, longer streak).

Env (test-only overrides use the same convention as connector-signals.py/weekly_evaluator.py --
CONNECTOR_STATE_DIR, CONNECTOR_GOG_OVERRIDE, CONNECTOR_LAST_PASS_FILE already exist in this repo and
are reused verbatim; the CONNECTOR_STREAK_* ones below are new, scoped to this script only):
  CONNECTOR_STATE_DIR              connector-core's OWN state dir (applications.jsonl/signals.json).
                                    Default: skills/connector/state/
  CONNECTOR_GOG_OVERRIDE            gog binary override. Default: "gog"
  CONNECTOR_LAST_PASS_FILE          .connector-core-last-pass marker path override.
                                    Default: ~/.openclaw/state/.connector-core-last-pass
  CONNECTOR_STREAK_STATE_DIR        where connector-streak.jsonl + the completion marker live.
                                    Default: <repo_root>/state
  CONNECTOR_STREAK_NOW_OVERRIDE     ISO8601 UTC instant, test-only (pins "today").
  CONNECTOR_STREAK_OPENCLAW_OVERRIDE  openclaw binary override. Default: "openclaw"
  CONNECTOR_STREAK_TELEGRAM_TARGET  Telegram target for the daily digest. Default: "8547730585"
  CONNECTOR_STREAK_COMPLETION_EMAIL  address for the day-7 completion email. Default:
                                    "keiodaisuke@gmail.com"
  CONNECTOR_STREAK_CRON_JOB_ID      cron job id whose lastRunStatus is recorded (informational only,
                                    never gates day_pass). Default: connector's own
                                    "ad89027d-c869-4956-8967-542bfa8b31d9"

Usage: python3 connector_streak_verify.py
Prints the final JSON summary {date, day_pass, streak, completion_email_sent} to stdout.
Exit 0 always (a failed day_pass is a valid, honestly-recorded outcome, not a script error); exit 1
only on an unrecoverable internal error (e.g. cannot write the ledger at all).
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CONNECTOR_DIR = os.path.join(REPO_ROOT, "skills", "connector")
sys.path.insert(0, CONNECTOR_DIR)
from connector_lib import gog_override, read_jsonl as connector_read_jsonl, state_dir as connector_state_dir  # noqa: E402

JST = datetime.timezone(datetime.timedelta(hours=9))
DEFAULT_CRON_JOB_ID = "ad89027d-c869-4956-8967-542bfa8b31d9"


def now_utc():
    """Same override-env-var convention as connector-signals.py's own now_utc() -- test-only."""
    override = os.environ.get("CONNECTOR_STREAK_NOW_OVERRIDE")
    if override:
        try:
            dt = datetime.datetime.fromisoformat(override.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except Exception:
            pass
    return datetime.datetime.now(datetime.timezone.utc)


def parse_iso_utc(ts):
    dt = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def jst_date_of(dt_utc):
    return dt_utc.astimezone(JST).date()


def openclaw_override():
    return os.environ.get("CONNECTOR_STREAK_OPENCLAW_OVERRIDE") or "openclaw"


def streak_state_dir():
    return os.environ.get("CONNECTOR_STREAK_STATE_DIR") or os.path.join(REPO_ROOT, "state")


def ledger_path():
    return os.path.join(streak_state_dir(), "connector-streak.jsonl")


def completion_marker_path():
    return os.path.join(streak_state_dir(), "connector-streak-completion-sent.json")


def last_pass_file():
    return os.environ.get(
        "CONNECTOR_LAST_PASS_FILE",
        os.path.join(os.path.expanduser("~"), ".openclaw", "state", ".connector-core-last-pass"),
    )


def read_ledger():
    rows = []
    path = ledger_path()
    if os.path.isfile(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def append_ledger(row):
    d = streak_state_dir()
    os.makedirs(d, exist_ok=True)
    with open(ledger_path(), "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compute_cron_ok(today_jst):
    """REQ: today's JST civil date must match the last-genuinely-completed-pass marker's own JST
    civil date -- stricter than weekly_evaluator.py's compute_cadence_ok() (which only checks a loose
    26h staleness window, appropriate for a health check but not for a per-day streak ledger)."""
    path = last_pass_file()
    if not os.path.isfile(path):
        return False, None
    mtime = os.path.getmtime(path)
    dt_utc = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
    pass_date = jst_date_of(dt_utc)
    return pass_date == today_jst, str(pass_date)


def fetch_cron_last_run_status(job_id):
    """Best-effort informational context only -- NEVER gates day_pass (the marker-file check above is
    the authoritative signal; the gateway cron history reflects the daily restart-trigger, not the
    STEP0-5 pass itself)."""
    try:
        proc = subprocess.run(
            [openclaw_override(), "cron", "get", job_id],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        return data.get("state", {}).get("lastRunStatus")
    except Exception:
        return None


def verify_registration(today_jst):
    """Returns (registration_ok, registration_payload). registration_payload is either a list of
    {event_id, confirmed, evidence_reference} dicts (today's CONFIRMED registrations, independently
    re-verified against Google Calendar) or the string "none:horizon_full"/"none:no-registration-and-
    horizon-not-full"."""
    applications = connector_read_jsonl("applications.jsonl")
    today_regs = [
        a for a in applications
        if isinstance(a, dict) and a.get("status") == "CONFIRMED" and a.get("ts")
        and jst_date_of(parse_iso_utc(a["ts"])) == today_jst
    ]

    if today_regs:
        verified = []
        for reg in today_regs:
            event_id = reg.get("event_id")
            confirmed = False
            if event_id:
                try:
                    proc = subprocess.run(
                        [gog_override(), "calendar", "event", "primary", event_id,
                         "-j", "--results-only"],
                        capture_output=True, text=True, timeout=30,
                    )
                    if proc.returncode == 0:
                        ev = json.loads(proc.stdout)
                        confirmed = ev.get("status") == "confirmed" and ev.get("id") == event_id
                except Exception:
                    confirmed = False
            verified.append({
                "event_id": event_id,
                "confirmed": confirmed,
                "evidence_reference": reg.get("evidence_reference"),
            })
        return any(v["confirmed"] for v in verified), verified

    signals_path = os.path.join(connector_state_dir(), "signals.json")
    horizon_full = False
    if os.path.isfile(signals_path):
        try:
            with open(signals_path) as f:
                horizon_full = json.load(f).get("horizon_full") is True
        except Exception:
            horizon_full = False

    if horizon_full:
        return True, "none:horizon_full"
    return False, "none:no-registration-and-horizon-not-full"


def send_telegram_digest(today_jst, cron_ok, registration_ok, registration_payload, streak_before):
    target = os.environ.get("CONNECTOR_STREAK_TELEGRAM_TARGET", "8547730585")
    reg_summary = (
        registration_payload if isinstance(registration_payload, str)
        else json.dumps(registration_payload, ensure_ascii=False)
    )
    text = (
        f"[connector-streak] {today_jst} 検証結果 -- cron_ok={cron_ok} "
        f"registration_ok={registration_ok} registration={reg_summary} "
        f"連続成功中(この結果を含まない過去分)={streak_before}日"
    )
    try:
        proc = subprocess.run(
            [openclaw_override(), "message", "send", "--channel", "telegram",
             "--target", target, "-m", text, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return False, None
        data = json.loads(proc.stdout)
        message_id = data.get("messageId") or data.get("payload", {}).get("messageId")
        ok = bool(message_id) and data.get("payload", {}).get("ok") is not False
        return ok, message_id
    except Exception:
        return False, None


def compute_streak(rows):
    """Trailing count of consecutive JST calendar days with day_pass:true, walking backward from the
    newest row; a missing day (date gap) or a day_pass:false row stops the count (never bridges a
    gap)."""
    by_date = {}
    for row in rows:
        d = row.get("date")
        if d:
            by_date[d] = row
    if not by_date:
        return 0
    dates_sorted = sorted(by_date.keys())
    cursor = datetime.date.fromisoformat(dates_sorted[-1])
    streak = 0
    while True:
        row = by_date.get(str(cursor))
        if not row or row.get("day_pass") is not True:
            break
        streak += 1
        cursor = cursor - datetime.timedelta(days=1)
    return streak


def send_completion_email(streak, qualifying_rows):
    email = os.environ.get("CONNECTOR_STREAK_COMPLETION_EMAIL", "keiodaisuke@gmail.com")
    lines = [f"connector 7日streak達成 -- {len(qualifying_rows)}日連続 day_pass:true", ""]
    for row in qualifying_rows:
        reg = row.get("registration")
        reg_str = reg if isinstance(reg, str) else json.dumps(reg, ensure_ascii=False)
        lines.append(
            f"- {row.get('date')}: cron_ok={row.get('cron_ok')} registration={reg_str} "
            f"telegram_msg_id={row.get('telegram_msg_id')}"
        )
    body = "\n".join(lines)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(body)
        body_path = f.name
    try:
        proc = subprocess.run(
            [gog_override(), "gmail", "send",
             "--account", email, "--to", email,
             "--subject", "[Anicca] connector 7日streak達成 — goal完了",
             "--body-file", body_path],
            capture_output=True, text=True, timeout=60,
        )
        return proc.returncode == 0
    finally:
        try:
            os.unlink(body_path)
        except OSError:
            pass


def main():
    today_jst = jst_date_of(now_utc())
    today_str = str(today_jst)

    existing_rows = read_ledger()
    if any(r.get("date") == today_str for r in existing_rows):
        print(json.dumps({"date": today_str, "skipped": True, "reason": "already recorded"}))
        return 0

    streak_before = compute_streak(existing_rows)

    cron_ok, cron_last_pass_date = compute_cron_ok(today_jst)
    cron_job_id = os.environ.get("CONNECTOR_STREAK_CRON_JOB_ID", DEFAULT_CRON_JOB_ID)
    cron_last_run_status = fetch_cron_last_run_status(cron_job_id)

    registration_ok, registration_payload = verify_registration(today_jst)

    telegram_ok, telegram_msg_id = send_telegram_digest(
        today_jst, cron_ok, registration_ok, registration_payload, streak_before
    )

    day_pass = bool(cron_ok and registration_ok and telegram_ok)
    reason = None
    if not day_pass:
        if not cron_ok:
            reason = "cron_ok:false (no genuinely-completed connector pass marker for today, JST)"
        elif not registration_ok:
            reason = "registration_ok:false (no verified registration today and horizon not full)"
        elif not telegram_ok:
            reason = "telegram_ok:false (message send did not return a messageId)"

    row = {
        "date": today_str,
        "cron_ok": cron_ok,
        "cron_last_pass_date": cron_last_pass_date,
        "cron_last_run_status": cron_last_run_status,
        "registration": registration_payload,
        "telegram_msg_id": telegram_msg_id,
        "telegram_delivered": telegram_ok,
        "day_pass": day_pass,
        "reason": reason,
        "verified_at": now_utc().isoformat(),
    }
    append_ledger(row)

    streak = compute_streak(existing_rows + [row])

    completion_email_sent = False
    if streak >= 7 and not os.path.isfile(completion_marker_path()):
        all_rows = read_ledger()
        by_date = {r.get("date"): r for r in all_rows if r.get("date")}
        cursor = today_jst
        qualifying = []
        for _ in range(streak):
            r = by_date.get(str(cursor))
            if not r:
                break
            qualifying.append(r)
            cursor = cursor - datetime.timedelta(days=1)
        qualifying.reverse()
        if send_completion_email(streak, qualifying):
            completion_email_sent = True
            os.makedirs(streak_state_dir(), exist_ok=True)
            with open(completion_marker_path(), "w") as f:
                json.dump(
                    {"sent_at": now_utc().isoformat(), "streak_at_send": streak, "last_date": today_str},
                    f,
                )

    print(json.dumps({
        "date": today_str,
        "day_pass": day_pass,
        "reason": reason,
        "streak": streak,
        "telegram_msg_id": telegram_msg_id,
        "completion_email_sent": completion_email_sent,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
