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
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .browser_owner import probe_cdp
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
GMAIL_CHECKPOINT_ID = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def _browser_listeners(port: int) -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpn"],
        check=False, capture_output=True, text=True, timeout=10,
    )
    if completed.returncode not in {0, 1}:
        return []
    listeners: list[dict[str, Any]] = []
    pid: int | None = None
    for line in completed.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            address = line[1:].rsplit(":", 1)[0]
            listeners.append({"pid": pid, "address": address})
    return listeners


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def browser_owner_health(
    *,
    receipt_path: Path,
    endpoint: str,
    now: datetime | None = None,
    cdp_probe: Any = probe_cdp,
    listener_reader: Any = _browser_listeners,
    pid_alive: Any = _pid_alive,
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Guardian browser time must include timezone")
    reasons: list[str] = []
    owner_state = "unverified"
    holder_pid: int | None = None
    path = Path(receipt_path).expanduser().resolve()
    receipt: dict[str, Any] | None = None
    if not path.is_file():
        reasons.append("browser_owner_receipt_missing")
    else:
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            reasons.append("browser_owner_receipt_permissions_invalid")
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
            receipt = candidate if isinstance(candidate, dict) else None
        except (OSError, json.JSONDecodeError):
            receipt = None
        required = {
            "version", "status", "owner", "endpoint", "lease_id", "fence",
            "holder_pid", "acquired_at", "expires_at",
        }
        valid = (
            receipt is not None
            and required.issubset(receipt)
            and receipt.get("version") == 2
            and receipt.get("status") == "ready"
            and receipt.get("owner") == "ai.anicca.job-search-daily"
            and receipt.get("endpoint") == endpoint
            and isinstance(receipt.get("lease_id"), str)
            and bool(receipt.get("lease_id"))
            and isinstance(receipt.get("fence"), int)
            and not isinstance(receipt.get("fence"), bool)
            and receipt.get("fence", 0) > 0
            and isinstance(receipt.get("holder_pid"), int)
            and not isinstance(receipt.get("holder_pid"), bool)
            and receipt.get("holder_pid", 0) > 0
        )
        if not valid:
            reasons.append("browser_owner_receipt_invalid")
        else:
            holder_pid = int(receipt["holder_pid"])
            try:
                acquired = datetime.fromisoformat(str(receipt["acquired_at"]))
                expires = datetime.fromisoformat(str(receipt["expires_at"]))
                if acquired.tzinfo is None or expires.tzinfo is None or not acquired <= current < expires:
                    reasons.append("browser_owner_lease_expired")
                else:
                    owner_state = "leased"
            except ValueError:
                reasons.append("browser_owner_receipt_invalid")
            if not pid_alive(holder_pid):
                reasons.append("browser_owner_pid_dead")
    parsed = urlsplit(endpoint)
    port = parsed.port or 80
    listeners = listener_reader(port)
    if len(listeners) != 1:
        reasons.append("browser_listener_not_unique")
    if any(row.get("address") not in {"127.0.0.1", "[::1]", "::1"} for row in listeners):
        reasons.append("browser_listener_not_loopback")
    if holder_pid is not None and len(listeners) == 1 and listeners[0].get("pid") != holder_pid:
        reasons.append("browser_listener_holder_mismatch")
    try:
        cdp_ready = cdp_probe(endpoint).get("status") == "ready"
    except Exception:
        cdp_ready = False
    if not cdp_ready:
        reasons.append("browser_cdp_unavailable")
    return {
        "version": 1,
        "status": "healthy" if not reasons else "unhealthy",
        "reasons": sorted(set(reasons)),
        "owner_state": owner_state,
        "listener_count": len(listeners),
        "listener_loopback_only": bool(listeners) and not any(
            row.get("address") not in {"127.0.0.1", "[::1]", "::1"}
            for row in listeners
        ),
        "cdp": "ready" if cdp_ready else "unavailable",
    }


def telegram_outbox_health(database: Path) -> dict[str, Any]:
    path = Path(database).expanduser().resolve()
    reasons: list[str] = []
    counts: dict[str, int] = {}
    uncertain_count = 0
    integrity = "unavailable"
    if not path.is_file():
        reasons.append("telegram_outbox_missing")
    else:
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            reasons.append("telegram_outbox_permissions_invalid")
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
            connection.row_factory = sqlite3.Row
            try:
                values = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
                integrity = ";".join(values)
                if values != ["ok"]:
                    reasons.append("telegram_outbox_integrity_failed")
                columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(outbox)")}
                timestamp_columns = {"created_at", "claimed_at", "send_started_at", "completed_at"}
                if not timestamp_columns.issubset(columns):
                    reasons.append("telegram_outbox_timestamps_missing")
                rows = connection.execute(
                    "SELECT status,fence,telegram_message_id,payload,event_key FROM outbox"
                ).fetchall()
                allowed = {"pending", "claimed", "send_started", "sent"}
                message_ids: list[str] = []
                for row in rows:
                    status_value = str(row["status"])
                    counts[status_value] = counts.get(status_value, 0) + 1
                    fence = row["fence"]
                    message_id = row["telegram_message_id"]
                    if status_value not in allowed or not row["event_key"] or not row["payload"]:
                        reasons.append("telegram_outbox_row_invalid")
                    elif status_value == "pending" and (fence is not None or message_id is not None):
                        reasons.append("telegram_outbox_row_invalid")
                    elif status_value in {"claimed", "send_started"} and (not fence or message_id is not None):
                        reasons.append("telegram_outbox_row_invalid")
                    elif status_value == "sent" and (not fence or not message_id):
                        reasons.append("telegram_outbox_row_invalid")
                    if status_value == "send_started":
                        uncertain_count += 1
                    if status_value == "sent" and message_id:
                        message_ids.append(str(message_id))
                if len(message_ids) != len(set(message_ids)):
                    reasons.append("telegram_message_id_duplicate")
                if uncertain_count:
                    reasons.append("telegram_side_effect_uncertain")
            finally:
                connection.close()
        except sqlite3.Error:
            reasons.append("telegram_outbox_unreadable")
    return {
        "version": 1,
        "status": "healthy" if not reasons else "unhealthy",
        "reasons": sorted(set(reasons)),
        "integrity": integrity,
        "counts": dict(sorted(counts.items())),
        "uncertain_count": uncertain_count,
    }


def _gmail_checkpoint_health(path: Path) -> tuple[list[str], int]:
    reasons: list[str] = []
    message_count = 0
    if not path.is_file():
        return ["gmail_checkpoint_missing"], 0
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        reasons.append("gmail_checkpoint_permissions_invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        message_ids = value.get("message_ids") if isinstance(value, dict) else None
        legacy_ids = value.get("legacy_thread_ids", []) if isinstance(value, dict) else None
        valid = (
            isinstance(value, dict)
            and value.get("version") == 2
            and isinstance(message_ids, list)
            and isinstance(legacy_ids, list)
            and len(message_ids) == len(set(message_ids))
            and len(legacy_ids) == len(set(legacy_ids))
            and all(
                isinstance(item, str) and GMAIL_CHECKPOINT_ID.fullmatch(item)
                for item in [*message_ids, *legacy_ids]
            )
        )
        if not valid:
            reasons.append("gmail_checkpoint_invalid")
        else:
            message_count = len(message_ids)
    except (OSError, json.JSONDecodeError):
        reasons.append("gmail_checkpoint_invalid")
    return reasons, message_count


def gmail_health(
    *,
    account: str,
    checkpoint_path: Path,
    executable: Path = Path("/opt/homebrew/bin/gog"),
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    reasons, checkpoint_message_count = _gmail_checkpoint_health(
        Path(checkpoint_path).expanduser().resolve()
    )
    executable_path = Path(executable).expanduser().resolve()
    auth_ok = False
    read_ok = False
    probe_thread_count = 0
    if not account.strip():
        reasons.append("gmail_account_missing")
    if not executable_path.is_file() or not os.access(executable_path, os.X_OK):
        reasons.append("gog_executable_invalid")
    if not reasons or not any(
        reason in {"gmail_account_missing", "gog_executable_invalid"}
        for reason in reasons
    ):
        auth_argv = [
            str(executable_path), "auth", "doctor", "--account", account,
            "--json", "--gmail-no-send", "--no-input", "--check",
        ]
        try:
            completed = runner(
                auth_argv, check=False, capture_output=True, text=True, timeout=60
            )
            auth_value = json.loads(completed.stdout) if completed.returncode == 0 else None
            auth_ok = isinstance(auth_value, dict)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            auth_ok = False
        if not auth_ok:
            reasons.append("gmail_auth_check_failed")
        else:
            search_argv = [
                str(executable_path), "gmail", "search", "--account", account,
                "--json", "--wrap-untrusted", "--gmail-no-send", "--no-input",
                "--max", "1", "newer_than:1d",
            ]
            try:
                completed = runner(
                    search_argv, check=False, capture_output=True, text=True, timeout=60
                )
                value = json.loads(completed.stdout) if completed.returncode == 0 else None
                threads = value.get("threads") if isinstance(value, dict) else None
                read_ok = isinstance(threads, list)
                if read_ok:
                    probe_thread_count = len(threads)
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                read_ok = False
            if not read_ok:
                reasons.append("gmail_read_invalid")
    return {
        "version": 1,
        "status": "healthy" if not reasons else "unhealthy",
        "reasons": sorted(set(reasons)),
        "auth_check": "passed" if auth_ok else "failed",
        "gmail_read": "passed" if read_ok else "not_passed",
        "checkpoint_message_count": checkpoint_message_count,
        "probe_thread_count": probe_thread_count,
    }


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
    gmail = subparsers.add_parser("gmail")
    gmail.add_argument("--account", required=True)
    gmail.add_argument("--checkpoint", type=Path, required=True)
    gmail.add_argument("--gog", type=Path, default=Path("/opt/homebrew/bin/gog"))
    gmail.add_argument("--output", type=Path, required=True)
    browser = subparsers.add_parser("browser")
    browser.add_argument("--receipt", type=Path, required=True)
    browser.add_argument("--endpoint", default="http://127.0.0.1:9222")
    browser.add_argument("--output", type=Path, required=True)
    outbox = subparsers.add_parser("outbox")
    outbox.add_argument("--database", type=Path, required=True)
    outbox.add_argument("--output", type=Path, required=True)
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
    elif args.command == "ledger":
        report = ledger_health(args.ledger)
        public = {
            "status": report["status"],
            "application_count": report["application_count"],
            "event_count": report["event_count"],
            "active_submission_claim_count": report["active_submission_claim_count"],
            "stale_submission_claim_count": report["stale_submission_claim_count"],
            "reasons": report["reasons"],
        }
    elif args.command == "gmail":
        report = gmail_health(
            account=args.account,
            checkpoint_path=args.checkpoint,
            executable=args.gog,
        )
        public = report
    elif args.command == "browser":
        report = browser_owner_health(
            receipt_path=args.receipt,
            endpoint=args.endpoint,
        )
        public = report
    else:
        report = telegram_outbox_health(args.database)
        public = report
    args.output.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(public, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
