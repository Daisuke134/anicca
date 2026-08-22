from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..ledger import Ledger
from .actions import ActionExecutor
from .candidate_memory import CandidateMemoryView
from .checkpoint import CheckpointStore, EvidenceStore
from .contracts import (
    ActionTargetV1,
    QueueRowReceiptV1,
    RowCheckpointV1,
    StepEvidenceV1,
    VisibleActionV1,
)
from .observation import ObservationBuilder
from .outcome_reporting import send_hourly_outcomes
from .queue import RowQueueSupervisor
from .resume_cursor import RowResumer
from .session import BrowserSession


_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
_WAKE_STEP_BUDGET = 50


def _path_env(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return Path(value)


def _redact(value: str) -> str:
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", value))


def _owner_endpoint() -> str:
    owner = json.loads(_path_env("JOB_SEARCH_BROWSER_OWNER_EVIDENCE").read_text())
    if owner.get("status") != "ready" or not owner.get("endpoint"):
        raise RuntimeError("browser owner is not ready")
    return str(owner["endpoint"])


def _wake_budget_path() -> Path:
    return _path_env("JOB_SEARCH_BROWSER_SCRATCH") / "wake-step-budget.json"


def _decision_path() -> Path:
    return _path_env("JOB_SEARCH_BROWSER_SCRATCH") / "last-decision.json"


def _decision_signature(observation_sha256: str, action_path: Path) -> str:
    return hashlib.sha256(
        observation_sha256.encode("ascii") + b"\0" + action_path.read_bytes()
    ).hexdigest()


def _reject_repeated_decision(observation_sha256: str, action_path: Path) -> str:
    signature = _decision_signature(observation_sha256, action_path)
    path = _decision_path()
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise RuntimeError("last decision record must be private")
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior.get("signature") == signature:
            raise RuntimeError("same action on unchanged observation is prohibited")
    return signature


def _record_decision(signature: str) -> None:
    path = _decision_path()
    path.write_text(json.dumps({"signature": signature}, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def _wake_budget(*, consume: bool = False) -> int:
    """Bound one owner wake without carrying exhaustion into the next wake."""

    path = _wake_budget_path()
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise RuntimeError("wake step budget must be private")
        remaining = int(json.loads(path.read_text(encoding="utf-8"))["remaining_steps"])
    else:
        remaining = _WAKE_STEP_BUDGET
    if consume:
        if remaining < 1:
            raise RuntimeError("wake step budget exhausted")
        remaining -= 1
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(
            json.dumps({"remaining_steps": remaining}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(path, 0o600)
    return remaining


def _row() -> dict[str, Any]:
    ledger = Ledger(_path_env("JOB_SEARCH_STATE_ROOT") / "ledger.sqlite3")
    try:
        rows = RowQueueSupervisor.collect(ledger)
    finally:
        ledger.close()
    if not rows:
        raise RuntimeError("no eligible active-provider row")
    return rows[0]


def _safe_observation(observation, checkpoint, remaining_steps: int) -> dict[str, Any]:
    return {
        "url": observation.url,
        "title": _redact(observation.title),
        "content_sha256": observation.content_sha256,
        "validation": [_redact(value) for value in observation.validation_text],
        "challenges": list(observation.visible_challenges),
        "remaining_steps": remaining_steps,
        "controls": [
            {
                "tag": control.tag,
                "role": control.role,
                "type": control.control_type,
                "label": _redact(control.label),
                "disabled": control.disabled,
                "stable_id": control.stable_id,
                "checked": control.checked,
                "options": [_redact(value) for value in control.options],
            }
            for control in observation.controls
            if control.label or control.stable_id
        ],
    }


async def _context():
    row = _row()
    state_root = _path_env("JOB_SEARCH_BROWSER_STATE_ROOT")
    session = BrowserSession()
    checkpoints = CheckpointStore(state_root)
    evidence = EvidenceStore(state_root)
    cursor = await RowResumer(session, checkpoints, evidence).restore(
        _owner_endpoint(), row["application_id"], row["canonical_url"]
    )
    builder = ObservationBuilder(
        session, _path_env("JOB_SEARCH_BROWSER_OWNER_EVIDENCE").parent
    )
    return row, session, checkpoints, evidence, cursor, builder


async def observe() -> dict[str, Any]:
    row, _session, _checkpoints, _evidence, cursor, builder = await _context()
    observation = await builder.build(cursor.handle)
    return {
        "status": "observed",
        "row": {
            "application_id": row["application_id"],
            "company": row["company"],
            "role": row["title"],
            "canonical_url": row["canonical_url"],
        },
        "needs_navigation": cursor.needs_navigation,
        "recovery_url": cursor.recovery_url if cursor.needs_navigation else None,
        "observation": _safe_observation(observation, cursor.checkpoint, _wake_budget()),
    }


def _private_action(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise RuntimeError("action file must exist with mode 0600")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("action file must contain an object")
    return value


def _action(value: dict[str, Any]) -> VisibleActionV1:
    target_value = value.get("target")
    target = None
    if isinstance(target_value, dict):
        target = ActionTargetV1(
            role=str(target_value.get("role") or ""),
            label=str(target_value.get("label") or ""),
            exact=bool(target_value.get("exact", True)),
            stable_id=str(target_value.get("stable_id") or ""),
        )
    text = value.get("text")
    concept = value.get("candidate_concept")
    if concept:
        memory = CandidateMemoryView.load(_path_env("JOB_SEARCH_CANDIDATE_MEMORY"))
        resolved = memory.get(str(concept))
        if not isinstance(resolved, (str, int, float)):
            raise ValueError("candidate concept is not a scalar browser value")
        text = str(resolved)
    file_path = Path(value["file_path"]) if value.get("file_path") else None
    kind = value.get("kind", value.get("action", value.get("type")))
    if not kind:
        raise ValueError("action file requires kind")
    return VisibleActionV1(
        kind=str(kind),
        target=target,
        text=str(text) if text is not None else None,
        url=str(value["url"]) if value.get("url") else None,
        file_path=file_path,
        delta_y=value.get("delta_y"),
        wait_ms=value.get("wait_ms"),
    )


async def act(action_path: Path) -> dict[str, Any]:
    row, session, checkpoints, evidence, cursor, builder = await _context()
    before = await builder.build(cursor.handle)
    action = _action(_private_action(action_path))
    decision_signature = _reject_repeated_decision(before.content_sha256, action_path)
    remaining = _wake_budget(consume=True)
    receipt = await ActionExecutor(session).execute(cursor.handle, action)
    after = await builder.build(cursor.handle)
    chain = evidence.read_chain(row["application_id"])
    evidence_receipt = evidence.append(
        StepEvidenceV1(
            1,
            row["application_id"],
            len(chain),
            chain[-1].evidence_sha256 if chain else None,
            before.content_sha256,
            receipt.receipt_sha256,
            after.content_sha256,
        )
    )
    prior_hashes = cursor.checkpoint.action_receipt_hashes if cursor.checkpoint else ()
    checkpoint_receipt = checkpoints.save(
        RowCheckpointV1(
            1,
            row["application_id"],
            "acting" if remaining else "checkpointed",
            cursor.handle.page_marker,
            cursor.handle.generation,
            after.content_sha256,
            (*prior_hashes, receipt.receipt_sha256),
            remaining,
            after.url,
        )
    )
    _record_decision(decision_signature)
    return {
        "status": "acted",
        "action": {
            key: value
            for key, value in asdict(receipt).items()
            if key not in {"before_url", "after_url"}
        },
        "evidence_sha256": evidence_receipt.evidence_sha256,
        "checkpoint_sha256": checkpoint_receipt.checkpoint_sha256,
        "observation": _safe_observation(
            after, checkpoints.load(row["application_id"]), remaining
        ),
    }


async def checkpoint(reason: str) -> dict[str, Any]:
    row, session, checkpoints, _evidence, cursor, builder = await _context()
    observation = await builder.build(cursor.handle)
    prior_hashes = cursor.checkpoint.action_receipt_hashes if cursor.checkpoint else ()
    receipt = checkpoints.save(
        RowCheckpointV1(
            1,
            row["application_id"],
            "checkpointed",
            cursor.handle.page_marker,
            cursor.handle.generation,
            observation.content_sha256,
            prior_hashes,
            0,
            observation.url,
        )
    )
    await session.close_owned(cursor.handle)
    return {
        "status": "checkpointed",
        "reason": reason,
        "row": {
            "application_id": row["application_id"],
            "company": row["company"],
            "role": row["title"],
        },
        "checkpoint_sha256": receipt.checkpoint_sha256,
        "observation_sha256": observation.content_sha256,
    }


def report(status: str) -> dict[str, Any]:
    row = _row()
    wake_id = _path_env("JOB_SEARCH_BROWSER_OWNER_EVIDENCE").parent.name
    result = send_hourly_outcomes(
        database=_path_env("JOB_SEARCH_STATE_ROOT") / "telegram-outbox.sqlite3",
        wake_id=wake_id,
        receipts=(
            QueueRowReceiptV1(
                row["application_id"], row["company"], row["title"], status
            ),
        ),
        evidence_classes={},
    )
    return {
        "status": result.get("status"),
        "message_id": result.get("message_id"),
        "application_id": row["application_id"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("observe")
    act_parser = subparsers.add_parser("act")
    act_parser.add_argument("--action-file", required=True, type=Path)
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument(
        "--reason", required=True, choices=("provider_unavailable", "visible_challenge")
    )
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument(
        "--status", required=True, choices=("checkpointed", "not_submitted")
    )
    args = parser.parse_args(argv)
    if args.command == "observe":
        operation = observe()
    elif args.command == "act":
        operation = act(args.action_file)
    elif args.command == "checkpoint":
        operation = checkpoint(args.reason)
    else:
        operation = None
    result = report(args.status) if operation is None else asyncio.run(operation)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
