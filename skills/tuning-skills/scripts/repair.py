#!/usr/bin/env python3
"""
repair.py — Apply known-fix patches to jobs.json based on tickets.

Reads:
  ~/.openclaw/workspace/tuning-skills/tickets/*.json
  ~/.openclaw/skills/tuning-skills/known_fixes.json
  ~/.openclaw/cron/jobs.json

Writes:
  ~/.openclaw/workspace/tuning-skills/repairs/<ts>-<skill>.diff   (unified diff text)

Modes:
  --dry-run (default)  Generate diffs but do NOT modify jobs.json
  --apply              Write a backup, modify jobs.json, mark ticket processed
  --undo <ticket_id>   Revert a previously-applied repair using its diff

For the first 30 nights of v0.2.0 SHADOW operation, only --dry-run is invoked
by the cron. --apply requires explicit human invocation.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

JOBS_JSON = Path(os.environ.get("TUNING_JOBS_JSON", str(Path.home() / ".openclaw" / "cron" / "jobs.json")))
TICKETS_DIR = Path.home() / ".openclaw" / "workspace" / "tuning-skills" / "tickets"
REPAIRS_DIR = Path.home() / ".openclaw" / "workspace" / "tuning-skills" / "repairs"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "tuning-skills"
KNOWN_FIXES = Path.home() / ".openclaw" / "skills" / "tuning-skills" / "known_fixes.json"


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"repair_{datetime.now():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def load_known_fixes() -> list[dict]:
    if not KNOWN_FIXES.exists():
        log(f"ERROR: known_fixes.json missing at {KNOWN_FIXES}")
        return []
    return json.loads(KNOWN_FIXES.read_text()).get("patterns", [])


def match_pattern(error_text: str, patterns: list[dict]) -> dict | None:
    if not error_text:
        return None
    for p in patterns:
        for rx in p.get("match_any", []):
            if re.search(rx, error_text, re.IGNORECASE):
                return p
    return None


def apply_fix(job: dict, fix: dict) -> dict:
    """Return a copy of `job` with `fix` applied (immutable)."""
    new = json.loads(json.dumps(job))  # deep copy
    kind = fix.get("kind")
    path = fix.get("path", "")
    if kind == "set_field":
        parts = path.split(".")
        cur = new
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = fix["value"]
    elif kind == "replace_field":
        parts = path.split(".")
        cur = new
        for p in parts[:-1]:
            cur = cur.get(p) if isinstance(cur, dict) else None
            if cur is None:
                return new
        if isinstance(cur, dict) and parts[-1] in cur and isinstance(cur[parts[-1]], str):
            cur[parts[-1]] = cur[parts[-1]].replace(fix["from_substr"], fix["to"])
    return new


def gen_diff(orig: dict, new: dict, name: str) -> str:
    a = json.dumps(orig, indent=2, ensure_ascii=False, sort_keys=True).splitlines(keepends=True)
    b = json.dumps(new, indent=2, ensure_ascii=False, sort_keys=True).splitlines(keepends=True)
    return "".join(difflib.unified_diff(a, b, fromfile=f"a/{name}", tofile=f"b/{name}"))


def cmd_run(apply_mode: bool) -> int:
    REPAIRS_DIR.mkdir(parents=True, exist_ok=True)
    patterns = load_known_fixes()
    if not patterns:
        return 1

    if not JOBS_JSON.exists():
        log(f"ERROR: jobs.json not found at {JOBS_JSON}")
        return 1
    jobs_doc = json.loads(JOBS_JSON.read_text())
    jobs = jobs_doc.get("jobs", [])
    by_id = {j["id"]: j for j in jobs}

    tickets = sorted(TICKETS_DIR.glob("*.json"))
    log(f"=== repair {'--apply' if apply_mode else '--dry-run'} (tickets={len(tickets)}) ===")

    if apply_mode:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = JOBS_JSON.with_suffix(f".json.bak.{ts}-pre-repair")
        shutil.copyfile(JOBS_JSON, backup)
        log(f"backup: {backup}")

    diffs_written = 0
    applied = 0
    skipped_unsafe = 0
    no_match = 0

    for tkt_path in tickets:
        ticket = json.loads(tkt_path.read_text())
        if ticket.get("processed"):
            continue
        job = by_id.get(ticket.get("job_id"))
        if not job:
            log(f"WARN: ticket {tkt_path.name} references unknown job_id")
            continue

        err = ticket.get("extracted_error") or ""
        pat = match_pattern(err, patterns)
        if not pat:
            no_match += 1
            continue

        if not pat.get("auto_apply_safe", False):
            skipped_unsafe += 1
            log(f"  ticket {tkt_path.name} → matched {pat['id']} but auto_apply_safe=false (manual_review)")
            continue

        fix = pat["fix"]
        new_job = apply_fix(job, fix)
        diff_txt = gen_diff(job, new_job, job["name"])
        diff_file = REPAIRS_DIR / f"{ticket['ticket_id']}.diff"
        diff_file.write_text(
            f"# pattern: {pat['id']}\n# auto_apply_safe: {pat.get('auto_apply_safe')}\n"
            f"# mode: {'apply' if apply_mode else 'dry-run'}\n\n{diff_txt}"
        )
        diffs_written += 1
        log(f"  ticket {tkt_path.name} → {pat['id']} → diff: {diff_file.name}")

        if apply_mode:
            jobs[jobs.index(job)] = new_job
            applied += 1
            ticket["processed"] = True
            ticket["applied_at"] = datetime.now(timezone.utc).isoformat()
            ticket["pattern_id"] = pat["id"]
            tkt_path.write_text(json.dumps(ticket, indent=2, ensure_ascii=False))

    if apply_mode and applied > 0:
        jobs_doc["jobs"] = jobs
        JOBS_JSON.write_text(json.dumps(jobs_doc, indent=2, ensure_ascii=False))
        log(f"jobs.json updated: {applied} jobs patched")

    log(f"summary: diffs={diffs_written} applied={applied} unsafe_skipped={skipped_unsafe} no_match={no_match}")
    return 0


def cmd_undo(ticket_id: str) -> int:
    diff = REPAIRS_DIR / f"{ticket_id}.diff"
    if not diff.exists():
        log(f"ERROR: diff not found: {diff}")
        return 1
    log(f"--undo {ticket_id} → restore from latest backup")
    backups = sorted(JOBS_JSON.parent.glob("jobs.json.bak.*-pre-repair"))
    if not backups:
        log("ERROR: no pre-repair backups found")
        return 1
    latest = backups[-1]
    shutil.copyfile(latest, JOBS_JSON)
    log(f"restored {JOBS_JSON} from {latest.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", type=str, default=None)
    args = ap.parse_args()

    if args.undo:
        return cmd_undo(args.undo)
    return cmd_run(apply_mode=args.apply)


if __name__ == "__main__":
    sys.exit(main())
