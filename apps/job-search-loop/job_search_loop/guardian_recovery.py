from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .outbox import Outbox
from .telegram import send_once


MAX_ACTIONS_PER_PASS = 3
STALE_PRE_SEND_AGE = timedelta(hours=2)


def _stored_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def bounded_recovery(
    *,
    outbox_database: Path,
    private_paths: list[Path],
    now: datetime | None = None,
    alert: Any,
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Guardian recovery time must include timezone")
    actions = 0
    repaired_permissions = 0
    recovered_claims = 0
    remaining_permission_faults = 0
    for raw_path in private_paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file() or stat.S_IMODE(path.stat().st_mode) == 0o600:
            continue
        if actions < MAX_ACTIONS_PER_PASS:
            os.chmod(path, 0o600)
            actions += 1
            if stat.S_IMODE(path.stat().st_mode) == 0o600:
                repaired_permissions += 1
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            remaining_permission_faults += 1

    database = Path(outbox_database).expanduser().resolve()
    uncertain_count = 0
    stale_remaining = 0
    database_fault = not database.is_file()
    if database.is_file():
        connection = sqlite3.connect(database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(outbox)")
            }
            required = {"status", "fence", "claimed_at", "send_started_at"}
            if not required.issubset(columns):
                database_fault = True
            else:
                uncertain_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM outbox WHERE status='send_started'"
                    ).fetchone()[0]
                )
                connection.execute("BEGIN IMMEDIATE")
                try:
                    claims = connection.execute(
                        "SELECT event_key,fence,claimed_at FROM outbox "
                        "WHERE status='claimed' AND send_started_at IS NULL ORDER BY rowid"
                    ).fetchall()
                    for row in claims:
                        claimed_at = _stored_time(row["claimed_at"])
                        stale = claimed_at is not None and current - claimed_at > STALE_PRE_SEND_AGE
                        if not stale:
                            continue
                        if actions >= MAX_ACTIONS_PER_PASS:
                            stale_remaining += 1
                            continue
                        changed = connection.execute(
                            "UPDATE outbox SET status='pending',fence=NULL,claimed_at=NULL "
                            "WHERE event_key=? AND fence=? AND status='claimed' "
                            "AND send_started_at IS NULL",
                            (row["event_key"], row["fence"]),
                        ).rowcount
                        if changed == 1:
                            actions += 1
                            recovered_claims += 1
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
        except sqlite3.Error:
            database_fault = True
        finally:
            connection.close()

    remaining_fault_count = (
        remaining_permission_faults + stale_remaining + uncertain_count
        + int(database_fault)
    )
    alert_sent = False
    if remaining_fault_count:
        try:
            alert(
                {
                    "kind": "guardian_recovery_incomplete",
                    "remaining_fault_count": remaining_fault_count,
                    "uncertain_side_effect_count": uncertain_count,
                }
            )
            alert_sent = True
        except Exception:
            alert_sent = False
    return {
        "version": 1,
        "status": "recovered" if remaining_fault_count == 0 else "manual_required",
        "action_count": actions,
        "repaired_permission_count": repaired_permissions,
        "recovered_pre_send_claim_count": recovered_claims,
        "uncertain_side_effect_count": uncertain_count,
        "remaining_fault_count": remaining_fault_count,
        "alert_sent": alert_sent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--private-path", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", default="8547730585")
    parser.add_argument("--openclaw", default="/opt/homebrew/bin/openclaw")
    args = parser.parse_args(argv)
    delivery: dict[str, Any] = {}
    outbox = Outbox(args.outbox)
    outbox.close()

    def alert(value: dict[str, Any]) -> None:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
        message = (
            "Job Hunter Guardianの限定復旧後も手動確認が必要です。"
            f" 残存fault {value['remaining_fault_count']}件、"
            f"副作用不明 {value['uncertain_side_effect_count']}件。"
            " 自動再送・自動応募はしていません。"
        )
        delivery.update(
            send_once(
                database=args.outbox,
                event_key=f"guardian-recovery:{digest}",
                message=message,
                target=args.target,
                executable=args.openclaw,
            )
        )

    report = bounded_recovery(
        outbox_database=args.outbox,
        private_paths=args.private_path,
        alert=alert,
    )
    if delivery.get("message_id") is not None:
        report["alert_message_id_recorded"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
