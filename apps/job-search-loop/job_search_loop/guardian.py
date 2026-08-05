from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import sqlite3
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .release_activation import ActivationError, LANES, _link_commit, _validate_release
from .state import InvalidTransition, validate_transition


class GuardianError(RuntimeError):
    pass


EXPECTED_SCHEDULES = {
    "daily": {"StartInterval": 3600},
    "inbox": {"StartInterval": 300},
    "learning": {
        "StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": 15}
    },
}
MAX_EVIDENCE_AGE_SECONDS = {
    "daily": 7200,
    "inbox": 900,
    "learning": 8 * 24 * 3600,
}
REQUIRED_LEDGER_TRIGGERS = frozenset(
    {
        "applications_identity_no_update",
        "applications_owner_no_update",
        "applications_state_requires_event",
        "events_no_delete",
        "events_no_update",
        "external_application_imports_no_delete",
        "external_application_imports_no_update",
        "funnel_outcomes_no_delete",
        "funnel_outcomes_no_update",
        "gmail_application_matches_no_delete",
        "gmail_application_matches_no_update",
        "gmail_match_decisions_no_delete",
        "gmail_match_decisions_no_update",
        "submission_material_receipts_no_delete",
        "submission_material_receipts_no_update",
    }
)
MAX_SUBMISSION_CLAIM_AGE = timedelta(hours=2)


def _valid_event_projection(connection: sqlite3.Connection) -> bool:
    applications = connection.execute(
        "SELECT id, current_state FROM applications ORDER BY rowid"
    ).fetchall()
    for application in applications:
        events = connection.execute(
            "SELECT from_state, to_state, payload_json FROM events "
            "WHERE application_id=? ORDER BY rowid",
            (application["id"],),
        ).fetchall()
        if not events or events[0]["from_state"] is not None:
            return False
        previous = str(events[0]["to_state"])
        try:
            payload = json.loads(str(events[0]["payload_json"]))
        except (json.JSONDecodeError, TypeError):
            return False
        external_origin = previous == "submitted" and (
            payload.get("external_import") is True
            and all(
                payload.get(key)
                for key in ("applied_at", "source", "source_message_id", "evidence_sha256")
            )
        )
        if previous != "discovered" and not external_origin:
            return False
        for event in events[1:]:
            to_state = str(event["to_state"])
            if event["from_state"] != previous:
                return False
            try:
                payload = json.loads(str(event["payload_json"]))
            except (json.JSONDecodeError, TypeError):
                return False
            if previous == "submit_unknown" and to_state == "submitted":
                if not all(
                    payload.get(key)
                    for key in ("message_id", "thread_id", "evidence_sha256", "received_at")
                ):
                    return False
            else:
                try:
                    validate_transition(previous, to_state)
                except InvalidTransition:
                    return False
            previous = to_state
        if previous != str(application["current_state"]):
            return False
    return True


def ledger_health(
    ledger_path: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Guardian ledger time must include timezone")
    path = Path(ledger_path).expanduser().resolve()
    reasons: list[str] = []
    missing_triggers: list[str] = []
    application_count = event_count = active_claim_count = stale_claim_count = 0
    integrity = "unavailable"
    foreign_key_violation_count = 0
    if not path.is_file():
        reasons.append("ledger_missing")
    else:
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            reasons.append("ledger_permissions_invalid")
        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro", uri=True, timeout=10
            )
            connection.row_factory = sqlite3.Row
            try:
                integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
                integrity = ";".join(str(row[0]) for row in integrity_rows)
                if [str(row[0]) for row in integrity_rows] != ["ok"]:
                    reasons.append("sqlite_integrity_failed")
                foreign_key_violation_count = len(
                    connection.execute("PRAGMA foreign_key_check").fetchall()
                )
                if foreign_key_violation_count:
                    reasons.append("foreign_key_violation")
                present = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='trigger'"
                    )
                }
                missing_triggers = sorted(REQUIRED_LEDGER_TRIGGERS - present)
                if missing_triggers:
                    reasons.append("required_trigger_missing")
                application_count = int(
                    connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
                )
                event_count = int(
                    connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                )
                if not _valid_event_projection(connection):
                    reasons.append("event_projection_mismatch")
                claims = connection.execute(
                    "SELECT created_at FROM submit_intents WHERE status='submit_claimed'"
                ).fetchall()
                active_claim_count = len(claims)
                for claim in claims:
                    try:
                        created = datetime.fromisoformat(str(claim["created_at"]))
                        if created.tzinfo is None or current - created > MAX_SUBMISSION_CLAIM_AGE:
                            stale_claim_count += 1
                    except ValueError:
                        stale_claim_count += 1
                if stale_claim_count:
                    reasons.append("stale_submission_claim")
            finally:
                connection.close()
        except sqlite3.Error:
            reasons.append("ledger_unreadable")
    return {
        "version": 1,
        "status": "healthy" if not reasons else "unhealthy",
        "reasons": sorted(set(reasons)),
        "integrity": integrity,
        "foreign_key_violation_count": foreign_key_violation_count,
        "missing_triggers": missing_triggers,
        "application_count": application_count,
        "event_count": event_count,
        "active_submission_claim_count": active_claim_count,
        "stale_submission_claim_count": stale_claim_count,
    }


def _launchctl(label: str) -> str | None:
    completed = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        check=False, capture_output=True, text=True, timeout=10,
    )
    return completed.stdout if completed.returncode == 0 else None


def schedule_health(
    *,
    plist_root: Path,
    launcher_root: Path,
    evidence_root: Path,
    intentionally_disabled: set[str],
    launchctl_reader: Any = _launchctl,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Guardian schedule time must include timezone")
    lanes: dict[str, Any] = {}
    for lane, expected_schedule in EXPECTED_SCHEDULES.items():
        reasons: list[str] = []
        label = f"ai.anicca.job-search-{lane}"
        plist_path = Path(plist_root) / f"{label}.plist"
        try:
            value = plistlib.loads(plist_path.read_bytes())
        except (OSError, plistlib.InvalidFileException):
            value = {}
            reasons.append("plist_invalid")
        expected_program = str((Path(launcher_root) / lane).resolve())
        if value.get("Label") != label:
            reasons.append("label_mismatch")
        arguments = value.get("ProgramArguments")
        if (
            not isinstance(arguments, list) or len(arguments) != 1
            or str(Path(str(arguments[0])).resolve()) != expected_program
        ):
            reasons.append("program_mismatch")
        if value.get("RunAtLoad") is not True:
            reasons.append("run_at_load_mismatch")
        for key, expected in expected_schedule.items():
            if value.get(key) != expected:
                reasons.append("interval_mismatch")
        output = launchctl_reader(label)
        loaded = output is not None
        lane_state = "loaded" if loaded else "unloaded"
        runs = None
        last_exit = None
        if lane in intentionally_disabled:
            lane_state = "intentionally_disabled"
            if loaded:
                reasons.append("intentionally_disabled_but_loaded")
        elif not loaded:
            reasons.append("not_loaded")
        else:
            runs_match = re.search(r"(?m)^\s*runs = (\d+)", output)
            exit_match = re.search(r"(?m)^\s*last exit code = (\d+)", output)
            runs = int(runs_match.group(1)) if runs_match else 0
            last_exit = int(exit_match.group(1)) if exit_match else None
            if runs == 0:
                reasons.append("never_run")
            if last_exit not in {None, 0}:
                reasons.append("last_exit_nonzero")
            candidates = list(Path(evidence_root).glob(f"{lane}-*"))
            if not candidates:
                reasons.append("evidence_missing")
            else:
                latest = max(candidate.stat().st_mtime for candidate in candidates)
                age = current.timestamp() - latest
                if age < 0 or age > MAX_EVIDENCE_AGE_SECONDS[lane]:
                    reasons.append("evidence_stale")
        lanes[lane] = {
            "state": lane_state,
            "interval_seconds": value.get("StartInterval"),
            "calendar_interval": value.get("StartCalendarInterval"),
            "runs": runs,
            "last_exit_code": last_exit,
            "reasons": sorted(set(reasons)),
        }
    return {
        "version": 1,
        "status": "healthy" if all(not row["reasons"] for row in lanes.values()) else "unhealthy",
        "lanes": lanes,
    }


def release_health(data_root: Path, launcher_root: Path | None = None) -> dict[str, Any]:
    data_root = Path(data_root).resolve()
    receipt_path = data_root / "active-release.json"
    if receipt_path.stat().st_mode & 0o777 != 0o600:
        raise GuardianError("active release receipt permissions are invalid")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GuardianError("active release receipt is invalid") from error
    if not isinstance(receipt, dict) or set(receipt) != {
        "version", "active_commit", "manifest_sha256", "route_config_sha256"
    } or receipt.get("version") != 1:
        raise GuardianError("active release receipt contract is invalid")
    try:
        linked_commit = _link_commit(data_root, "current")
        candidate = _validate_release(data_root, str(receipt["active_commit"]))
    except (ActivationError, OSError) as error:
        raise GuardianError(str(error)) from error
    if linked_commit != receipt["active_commit"]:
        raise GuardianError("active release pointer differs from receipt")
    checks = {
        "manifest_sha256": candidate / "RELEASE.json",
        "route_config_sha256": candidate / "runtime/agent-runner/config.json",
    }
    for field, path in checks.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt[field]:
            raise GuardianError(f"active release {field} mismatch")
    launcher_root = Path(launcher_root or (
        Path.home() / ".local/libexec/anicca/job-search"
    )).resolve()
    stable_count = 0
    for lane in LANES:
        launcher = launcher_root / lane
        if (
            not launcher.is_file() or not os.access(launcher, os.X_OK)
            or stat.S_IMODE(launcher.stat().st_mode) & 0o222
        ):
            raise GuardianError(f"stable launcher is unhealthy: {lane}")
        stable_count += 1
    return {
        "version": 1,
        "status": "healthy",
        "active_commit": linked_commit,
        "runner_count": len(LANES),
        "stable_launcher_count": stable_count,
        "manifest_sha256": receipt["manifest_sha256"],
        "route_config_sha256": receipt["route_config_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    release = subparsers.add_parser("release")
    release.add_argument("--data-root", type=Path, required=True)
    release.add_argument("--launcher-root", type=Path, required=True)
    release.add_argument("--output", type=Path, required=True)
    schedule = subparsers.add_parser("schedule")
    schedule.add_argument("--plist-root", type=Path, required=True)
    schedule.add_argument("--launcher-root", type=Path, required=True)
    schedule.add_argument("--evidence-root", type=Path, required=True)
    schedule.add_argument("--intentionally-disabled", nargs="*", default=[])
    schedule.add_argument("--output", type=Path, required=True)
    ledger = subparsers.add_parser("ledger")
    ledger.add_argument("--ledger", type=Path, required=True)
    ledger.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "release":
        report = release_health(args.data_root, args.launcher_root)
        public = {
            "status": report["status"], "active_commit": report["active_commit"],
            "runner_count": report["runner_count"],
            "stable_launcher_count": report["stable_launcher_count"],
        }
    elif args.command == "schedule":
        report = schedule_health(
            plist_root=args.plist_root, launcher_root=args.launcher_root,
            evidence_root=args.evidence_root,
            intentionally_disabled=set(args.intentionally_disabled),
        )
        public = {
            "status": report["status"],
            "lanes": {key: value["state"] for key, value in report["lanes"].items()},
        }
    else:
        report = ledger_health(args.ledger)
        public = {
            "status": report["status"],
            "application_count": report["application_count"],
            "event_count": report["event_count"],
            "active_submission_claim_count": report["active_submission_claim_count"],
            "stale_submission_claim_count": report["stale_submission_claim_count"],
            "reasons": report["reasons"],
        }
    args.output.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(public, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
