#!/usr/bin/env python3
"""Bind one official Upwork revision request and route it without overwriting work."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import project_ledger


DIGEST = re.compile(r"[0-9a-f]{64}")
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,127}")


class RevisionError(ValueError):
    pass


def _body(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha(value: Any) -> str:
    return hashlib.sha256(_body(value)).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exclusive(path: Path, value: Any) -> None:
    body = _body(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != body:
            raise RevisionError("revision_identity_collision")
        return
    with os.fdopen(fd, "wb") as handle:
        handle.write(body); handle.flush(); os.fsync(handle.fileno())


def _validate_artifacts(root: Path, execution: dict[str, Any]) -> None:
    rows = execution.get("artifacts") if isinstance(execution, dict) else None
    if (
        not DIGEST.fullmatch(str(execution.get("execution_id") or ""))
        or not DIGEST.fullmatch(str(execution.get("contract_sha256") or ""))
        or not isinstance(rows, list) or not rows
    ):
        raise RevisionError("prior_execution_invalid")
    for row in rows:
        raw = row.get("path") if isinstance(row, dict) else None
        if (
            not isinstance(raw, str) or Path(raw).is_absolute() or ".." in Path(raw).parts
            or not DIGEST.fullmatch(str(row.get("sha256") or ""))
            or type(row.get("bytes")) is not int or row["bytes"] < 1
        ):
            raise RevisionError("prior_execution_invalid")
        path = root / raw
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise RevisionError("original_artifact_changed") from exc
        if (
            path.is_symlink() or not path.is_file() or path.stat().st_size != row["bytes"]
            or _sha_file(path) != row["sha256"]
        ):
            raise RevisionError("original_artifact_changed")


def _validate(
    contract: Any, request: Any, decision: Any, execution: Any,
    elapsed_seconds: int, model_cost: int, tool_cost: int,
) -> None:
    if (
        not isinstance(contract, dict)
        or set(contract) != {"contract_id", "milestone_id", "scope", "deadline", "contract_sha256"}
        or not isinstance(request, dict)
        or set(request) != {"provider", "message_id", "room_id", "contract_id", "milestone_id",
                            "request_text", "requested_deadline", "observed_at", "evidence_sha256"}
        or not isinstance(decision, dict)
        or set(decision) != {"in_scope", "scope_clause", "reason_codes", "evidence_sha256"}
    ):
        raise RevisionError("revision_input_invalid")
    try:
        date.fromisoformat(contract["deadline"])
        datetime.fromisoformat(request["observed_at"].replace("Z", "+00:00"))
        if request["requested_deadline"] is not None:
            date.fromisoformat(request["requested_deadline"])
    except (TypeError, ValueError) as exc:
        raise RevisionError("revision_input_invalid") from exc
    keys = [contract["contract_id"], contract["milestone_id"], request["message_id"], request["room_id"]]
    if (
        request["provider"] != "upwork" or any(not KEY.fullmatch(str(item)) for item in keys)
        or request["contract_id"] != contract["contract_id"]
        or request["milestone_id"] != contract["milestone_id"]
        or not isinstance(contract["scope"], str) or not contract["scope"].strip()
        or not isinstance(request["request_text"], str) or not request["request_text"].strip()
        or not DIGEST.fullmatch(str(contract["contract_sha256"] or ""))
        or not DIGEST.fullmatch(str(request["evidence_sha256"] or ""))
        or not DIGEST.fullmatch(str(decision["evidence_sha256"] or ""))
        or type(decision["in_scope"]) is not bool
        or not isinstance(decision["scope_clause"], str) or not decision["scope_clause"].strip()
        or not isinstance(decision["reason_codes"], list) or not decision["reason_codes"]
        or any(not isinstance(code, str) or not code for code in decision["reason_codes"])
        or execution.get("contract_sha256") != contract["contract_sha256"]
        or any(type(value) is not int or value < 0 for value in (elapsed_seconds, model_cost, tool_cost))
    ):
        raise RevisionError("revision_input_invalid")
    if decision["in_scope"] and decision["scope_clause"] != contract["scope"]:
        raise RevisionError("revision_scope_evidence_invalid")


def _commit_route(root: Path, receipt: dict[str, Any]) -> None:
    economics = receipt["economics"]
    project_ledger.append_fact(
        root, "upwork_revision_routed", economics,
        provenance=[{"source": "upwork_message", "sha256": receipt["source"]["evidence_sha256"]}],
    )
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    next_action = receipt["next_actions"][0]
    if state.get("active_revision_id") != receipt["revision_id"] or state.get("next_action") != next_action:
        project_ledger.append(root, {
            "active_revision_id": receipt["revision_id"], "next_action": next_action,
            "revision_route": receipt["route"],
        }, "upwork_revision_routed")


def process_revision(
    *, workspace: str | Path, contract: dict[str, Any], request: dict[str, Any],
    decision: dict[str, Any], prior_execution: dict[str, Any], elapsed_seconds: int,
    model_cost_usd_minor: int, tool_cost_usd_minor: int,
) -> dict[str, Any]:
    """Persist one decision; replay is read-only and in-scope work returns to Tasks 17-19."""
    _validate(contract, request, decision, prior_execution, elapsed_seconds,
              model_cost_usd_minor, tool_cost_usd_minor)
    root = Path(workspace).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise RevisionError("workspace_invalid")
    _validate_artifacts(root, prior_execution)
    source = {
        "provider": "upwork", "message_id": request["message_id"], "room_id": request["room_id"],
        "contract_id": request["contract_id"], "milestone_id": request["milestone_id"],
        "evidence_sha256": request["evidence_sha256"],
    }
    identity = _sha(source)
    input_sha256 = _sha({
        "contract": contract, "request": request, "decision": decision,
        "prior_execution": prior_execution,
    })
    lock = root / ".revision.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        receipt_path = root / "revision-receipts" / f"{identity}.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected = receipt.pop("receipt_sha256", None)
            if _sha(receipt) != expected:
                raise RevisionError("revision_receipt_invalid")
            if receipt.get("input_sha256") != input_sha256:
                raise RevisionError("revision_identity_collision")
            receipt = {**receipt, "receipt_sha256": expected}
            _commit_route(root, receipt)
            return receipt

        deadline_changed = request["requested_deadline"] not in (None, contract["deadline"])
        in_scope = decision["in_scope"] and not deadline_changed
        revision_id = _sha({
            "source": source, "request_text": request["request_text"],
            "decision_sha256": _sha(decision), "prior_execution_id": prior_execution["execution_id"],
        })
        packet = {
            "version": 1, "revision_id": revision_id, "source": source,
            "request_text": request["request_text"], "observed_at": request["observed_at"],
            "scope_clause": decision["scope_clause"], "reason_codes": decision["reason_codes"],
            "prior_execution_id": prior_execution["execution_id"],
            "prior_artifacts": prior_execution["artifacts"],
            "decision_evidence_sha256": decision["evidence_sha256"],
        }
        revision_path = None
        if in_scope:
            revision_path = root / "requirements" / "client-revisions" / f"{revision_id}.json"
            _exclusive(revision_path, packet)
        route = "fulfillment" if in_scope else "negotiation"
        receipt = {
            "version": 1, "revision_id": revision_id, "route": route,
            "next_actions": (["execute_workflow", "verify_deliverables", "deliver_milestone"]
                             if in_scope else ["negotiate_scope_change"]),
            "revision_request": str(revision_path) if revision_path else None,
            "source": source, "prior_execution_id": prior_execution["execution_id"],
            "input_sha256": input_sha256,
            "economics": {
                "event_id": identity, "revision_id": revision_id, "route": route,
                "elapsed_seconds": elapsed_seconds, "model_cost_usd_minor": model_cost_usd_minor,
                "tool_cost_usd_minor": tool_cost_usd_minor,
            },
        }
        receipt["receipt_sha256"] = _sha(receipt)
        _exclusive(receipt_path, receipt)
        _commit_route(root, receipt)
        return receipt
