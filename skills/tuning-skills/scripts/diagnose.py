#!/usr/bin/env python3
"""
diagnose.py — Find failing crons, write tickets.

Reads:
  ~/.openclaw/cron/jobs.json
  ~/.openclaw/tasks/runs.sqlite

Writes:
  ~/.openclaw/workspace/tuning-skills/tickets/<ts>-<skill>.json
    one per cron with consecutiveErrors >= threshold

DOES NOT modify jobs.json or any skill. Read-only diagnostic.

Env:
  TUNING_DRY_RUN          "true" → log only, no ticket files (default: false)
  TUNING_DLQ_THRESHOLD    int (default: 1)
  TUNING_RUNS_DB          path to runs.sqlite (default: ~/.openclaw/tasks/runs.sqlite)
  TUNING_JOBS_JSON        path to jobs.json
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

JOBS_JSON = Path(os.environ.get("TUNING_JOBS_JSON", str(Path.home() / ".openclaw" / "cron" / "jobs.json")))
RUNS_DB = Path(os.environ.get("TUNING_RUNS_DB", str(Path.home() / ".openclaw" / "tasks" / "runs.sqlite")))
TICKETS_DIR = Path.home() / ".openclaw" / "workspace" / "tuning-skills" / "tickets"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "tuning-skills"
DRY_RUN = os.environ.get("TUNING_DRY_RUN", "false").lower() == "true"
THRESHOLD = int(os.environ.get("TUNING_DLQ_THRESHOLD", "1"))


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"diagnose_{datetime.now():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def load_jobs() -> list[dict]:
    if not JOBS_JSON.exists():
        log(f"WARN: jobs.json not found at {JOBS_JSON}")
        return []
    return json.loads(JOBS_JSON.read_text()).get("jobs", [])


def recent_error_for(job_id: str, job_name: str, conn: sqlite3.Connection) -> str | None:
    """Best-effort: pull a recent error blob from runs.sqlite.

    OpenClaw task_runs schema keys runs by `label` (= cron job name) and `source_id`,
    not `job_id`. Try both. Fall back to terminal_summary if error column is empty.
    """
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
    except Exception:
        return None
    if "task_runs" not in tables:
        return None

    for col, val in (("label", job_name), ("source_id", job_id), ("source_id", job_name)):
        try:
            cur = conn.execute(
                f"SELECT error, terminal_summary FROM task_runs WHERE {col} = ? "
                f"ORDER BY started_at DESC LIMIT 1",
                (val,),
            )
            row = cur.fetchone()
            if row:
                if row[0]:
                    return str(row[0])[:1000]
                if row[1]:
                    return str(row[1])[:1000]
        except Exception:
            continue
    return None


def main() -> int:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    log(f"=== diagnose start (DRY_RUN={DRY_RUN}, threshold={THRESHOLD}) ===")

    jobs = load_jobs()
    log(f"loaded {len(jobs)} jobs from {JOBS_JSON}")

    conn: sqlite3.Connection | None = None
    if RUNS_DB.exists():
        try:
            conn = sqlite3.connect(f"file:{RUNS_DB}?mode=ro", uri=True)
        except Exception as e:
            log(f"WARN: could not open {RUNS_DB}: {e}")

    failing: list[dict] = []
    for j in jobs:
        ce = (j.get("state") or {}).get("consecutiveErrors") or 0
        if ce < THRESHOLD:
            continue
        last_err = None
        if conn:
            last_err = recent_error_for(j["id"], j["name"], conn)
        ticket = {
            "ticket_id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{j['name']}",
            "job_id": j["id"],
            "job_name": j["name"],
            "schedule": j.get("schedule"),
            "consecutive_errors": ce,
            "last_status": (j.get("state") or {}).get("lastStatus"),
            "last_run_at_ms": (j.get("state") or {}).get("lastRunAtMs"),
            "last_delivery_status": (j.get("state") or {}).get("lastDeliveryStatus"),
            "extracted_error": last_err,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "0.2.0",
            "shadow_mode": True,
        }
        failing.append(ticket)

    log(f"found {len(failing)} jobs with consecutiveErrors >= {THRESHOLD}")

    if DRY_RUN:
        for t in failing[:5]:
            log(f"[DRY_RUN] would write ticket: {t['ticket_id']}")
        return 0

    for t in failing:
        out = TICKETS_DIR / f"{t['ticket_id']}.json"
        out.write_text(json.dumps(t, indent=2, ensure_ascii=False))
    log(f"wrote {len(failing)} tickets to {TICKETS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
