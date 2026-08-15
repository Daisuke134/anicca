#!/usr/bin/env python3
"""A6 (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md section CC'): every pass,
say where the live site and the project ledger (state.json) disagree.

WHY: state.json for 91000001 said buyer_visible_artifact_observed=false and
current_artifact still pointed at a stale v1 docx while the site's own message log
already showed the Google-Docs delivery text sent to the buyer -- the ledger was
blind to reality and nothing detected it. state_reconciler.py mirrors some fields
(transaction_state, buyer_visible, buyer_agreement_observed) from the newest snapshot
but never touches buyer_visible_artifact_observed or talkroom_state, so those two can
drift indefinitely. This script does not fix drift (that is F3's job, later) -- it only
observes and records it, every pass, so a later self-repair step has something to read.

OBSERVATION ONLY: no write to state.json, no decision, no branching on the result.

Checks (grounded in real fields, verified against live evidence 2026-08-09):
  1. transaction_state   -- snapshot order["talkroom_state"] vs state["talkroom_state"]
                             (state["transaction_state"] is already kept fresh by
                             state_reconciler.py's MIRROR map; state["talkroom_state"]
                             is written once at project creation and never touched again)
  2. artifact_visible     -- a delivery-looking seller message on the site (an
                             attachment, or a link -- links are redacted to the literal
                             string "[redacted-url]" by coconala_queue_snapshot.py's PII
                             scrub, so that string is matched too) vs
                             state["buyer_visible_artifact_observed"]
  3. contract_kind        -- snapshot order["room_contract_kind"] (A5) vs the delivery
                             queue's own order["delivery_action"] for the same room:
                             "subscription" rooms must never carry a "formal"/"progress"
                             one-shot delivery action
  4. control_disabled     -- snapshot order["formal_delivery_control_disabled"] vs
                             state["last_delivery_attempt_reason"] ==
                             "formal_delivery_awaiting_buyer_confirmation"

Usage:
  site_ledger_reconcile.py --snapshot <marketplace-snapshot.json> \\
      --projects-root ~/gig/projects [--queue <delivery-queue.json>] \\
      --output <evidence-dir>/reconcile-report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery_identity  # noqa: E402

DELIVERY_LOOKING_MARKERS = ("[redacted-url]", "docs.google.com", "drive.google.com")
AWAITING_CONFIRMATION_REASON = "formal_delivery_awaiting_buyer_confirmation"
ONE_SHOT_DELIVERY_ACTIONS = {"formal", "progress"}


def _load_json(path: Path) -> tuple[Any, str | None]:
    """Return (value, error). error is None on success, else a short reason string."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"unreadable: {exc}"


def _site_artifact_visible(order: dict[str, Any]) -> bool:
    for message in order.get("seller_sent_messages") or []:
        if not isinstance(message, dict):
            continue
        if message.get("attachments"):
            return True
        text = str(message.get("text") or "")
        if any(marker in text for marker in DELIVERY_LOOKING_MARKERS):
            return True
    return False


def _project_id_for(order: dict[str, Any]) -> str | None:
    try:
        return delivery_identity.stable_identity(order)
    except ValueError:
        return None


def _queue_action_by_talkroom(queue_doc: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(queue_doc, dict):
        return result
    for item in queue_doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        talkroom_id = item.get("talkroom_id")
        action = item.get("delivery_action")
        if talkroom_id is not None and action is not None:
            result[str(talkroom_id)] = str(action)
    return result


def _check(name: str, site_value: Any, ledger_value: Any) -> dict[str, Any]:
    return {
        "name": name,
        "site_value": site_value,
        "ledger_value": ledger_value,
        "agree": site_value == ledger_value,
    }


def reconcile_project(order: dict[str, Any], state: dict[str, Any], queue_action: str | None) -> list[dict[str, Any]]:
    checks = [
        _check("transaction_state", order.get("talkroom_state"), state.get("talkroom_state")),
        _check(
            "artifact_visible",
            _site_artifact_visible(order),
            state.get("buyer_visible_artifact_observed") is True,
        ),
        _check(
            "control_disabled",
            order.get("formal_delivery_control_disabled") is True,
            state.get("last_delivery_attempt_reason") == AWAITING_CONFIRMATION_REASON,
        ),
    ]
    if queue_action is not None:
        room_contract_kind = order.get("room_contract_kind")
        subscription_with_one_shot_action = (
            room_contract_kind == "subscription" and queue_action in ONE_SHOT_DELIVERY_ACTIONS
        )
        checks.append(
            {
                "name": "contract_kind",
                "site_value": room_contract_kind,
                "ledger_value": queue_action,
                "agree": not subscription_with_one_shot_action,
            }
        )
    return checks


def scan(snapshot_path: Path, projects_root: Path, queue_path: Path | None = None) -> dict[str, Any]:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": str(snapshot_path),
        "projects_root": str(projects_root),
        "queue": str(queue_path) if queue_path else None,
        "rows": [],
        "projects_seen": 0,
        "projects_checked": 0,
        "skipped_no_state": 0,
        "unreadable_state": 0,
        "discrepancies": 0,
    }

    snapshot, snap_err = _load_json(snapshot_path)
    if snap_err is not None or not isinstance(snapshot, dict):
        summary["error"] = f"snapshot_{snap_err or 'malformed'}"
        return summary

    queue_action_by_talkroom: dict[str, str] = {}
    if queue_path is not None:
        queue_doc, queue_err = _load_json(queue_path)
        if queue_err is None:
            queue_action_by_talkroom = _queue_action_by_talkroom(queue_doc)
        else:
            summary["queue_error"] = queue_err

    for order in snapshot.get("orders") or []:
        if not isinstance(order, dict):
            continue
        summary["projects_seen"] += 1
        project_id = _project_id_for(order)
        talkroom_id = order.get("talkroom_id")
        row: dict[str, Any] = {"project_id": project_id, "talkroom_id": talkroom_id}

        if project_id is None:
            row["status"] = "skipped_no_identity"
            summary["skipped_no_state"] += 1
            summary["rows"].append(row)
            continue

        state_path = projects_root / project_id / "state.json"
        state, state_err = _load_json(state_path)
        if state_err == "missing":
            row["status"] = "skipped_no_state"
            summary["skipped_no_state"] += 1
            summary["rows"].append(row)
            continue
        if state_err is not None or not isinstance(state, dict):
            row["status"] = "unreadable_state"
            summary["unreadable_state"] += 1
            summary["rows"].append(row)
            continue

        queue_action = queue_action_by_talkroom.get(str(talkroom_id)) if talkroom_id is not None else None
        checks = reconcile_project(order, state, queue_action)
        row["status"] = "ok"
        row["checks"] = checks
        summary["projects_checked"] += 1
        summary["discrepancies"] += sum(1 for c in checks if not c["agree"])
        summary["rows"].append(row)

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=Path(os.environ.get("GIG_PROJECTS_ROOT", str(default_root / "projects"))),
    )
    parser.add_argument("--queue", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    report = scan(args.snapshot, args.projects_root, args.queue)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, args.output)

    summary_line = {
        k: v
        for k, v in report.items()
        if k != "rows"
    }
    print(json.dumps(summary_line, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
