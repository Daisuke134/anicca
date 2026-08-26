#!/usr/bin/env python3
"""Exactly-once fence for one funded Upwork milestone submission."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DIGEST = re.compile(r"[0-9a-f]{64}")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UpworkMilestoneDelivery:
    def __init__(
        self, store: Any, transport: Any,
        read_contract: Callable[..., dict[str, Any]],
        submit: Callable[..., dict[str, Any]],
        read_submission: Callable[..., dict[str, Any] | None],
        *, now: Callable[[], datetime] | None = None,
    ) -> None:
        self.store, self.transport = store, transport
        self.read_contract, self.submit, self.read_submission = read_contract, submit, read_submission
        self.now = now or (lambda: datetime.now(timezone.utc))

    def _selection(self):
        selection = self.transport.for_action("deliver_milestone")
        if selection is None:
            raise ValueError("authorization_not_approved")
        return selection

    def _contract(
        self, selection: Any, contract_id: str, milestone_id: str, contract_sha256: str,
    ) -> dict[str, Any]:
        row = self.read_contract(selection, contract_id, milestone_id)
        try:
            observed = datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("upwork_delivery_contract_readback_invalid") from exc
        age = (self.now().astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
        if (
            not isinstance(row, dict) or row.get("contract_id") != contract_id
            or row.get("milestone_id") != milestone_id
            or row.get("contract_sha256") != contract_sha256
            or row.get("milestone_state") != "active" or row.get("funded") is not True
            or not isinstance(row.get("workroom_url"), str)
            or not row["workroom_url"].startswith("https://www.upwork.com/")
            or not DIGEST.fullmatch(str(row.get("evidence_sha256") or ""))
            or age < -30 or age > 300
        ):
            raise ValueError("upwork_delivery_contract_readback_invalid")
        return row

    @staticmethod
    def _payload(
        workspace: Path, contract_id: str, milestone_id: str,
        execution: dict[str, Any], verification: dict[str, Any], message: str,
    ) -> dict[str, Any]:
        rows = execution.get("artifacts") if isinstance(execution, dict) else None
        hashes = verification.get("artifact_sha256") if isinstance(verification, dict) else None
        evidence = verification.get("evidence") if isinstance(verification, dict) else None
        if (
            not isinstance(contract_id, str) or not contract_id.strip()
            or not isinstance(milestone_id, str) or not milestone_id.strip()
            or execution.get("state") != "completed"
            or not DIGEST.fullmatch(str(execution.get("execution_id") or ""))
            or not DIGEST.fullmatch(str(execution.get("contract_sha256") or ""))
            or verification.get("status") != "PASS"
            or verification.get("delivery_intent_permitted") is not True
            or not isinstance(evidence, list)
            or not {"artifact_hash_verified", "independent_context_verified"}.issubset(evidence)
            or not isinstance(rows, list) or not rows
            or not isinstance(hashes, list) or hashes != [row.get("sha256") for row in rows]
            or not isinstance(message, str) or not message.strip() or len(message) > 5000
        ):
            raise ValueError("upwork_delivery_verification_invalid")
        artifacts = []
        for row in rows:
            raw = row.get("path") if isinstance(row, dict) else None
            if (
                not isinstance(raw, str) or Path(raw).is_absolute() or ".." in Path(raw).parts
                or not DIGEST.fullmatch(str(row.get("sha256") or ""))
                or type(row.get("bytes")) is not int or row["bytes"] < 1
            ):
                raise ValueError("upwork_delivery_artifact_invalid")
            path = workspace / raw
            try:
                path.resolve(strict=True).relative_to(workspace.resolve(strict=True))
            except (OSError, ValueError) as exc:
                raise ValueError("upwork_delivery_artifact_invalid") from exc
            if path.is_symlink() or not path.is_file() or path.stat().st_size != row["bytes"] or _sha_file(path) != row["sha256"]:
                raise ValueError("upwork_delivery_artifact_invalid")
            artifacts.append({"path": raw, "sha256": row["sha256"], "bytes": row["bytes"]})
        return {
            "version": 1, "provider": "upwork", "contract_id": contract_id,
            "milestone_id": milestone_id, "contract_sha256": execution["contract_sha256"],
            "execution_id": execution.get("execution_id"), "artifact_sha256": hashes,
            "artifacts": artifacts, "message": message.strip(),
            "verification_sha256": _sha(verification),
        }

    def plan(
        self, *, workspace: str | Path, contract_id: str, milestone_id: str,
        execution_receipt: dict[str, Any], verification: dict[str, Any], message: str,
    ):
        root = Path(workspace).expanduser()
        payload = self._payload(root, contract_id, milestone_id, execution_receipt, verification, message)
        selection = self._selection()
        contract = self._contract(selection, contract_id, milestone_id, payload["contract_sha256"])
        digest = _sha(payload)
        intent = self.transport.effect_intent(
            selection, resource_id=f"{contract_id}:{milestone_id}", payload_hash=digest,
        )
        self.store.prepare_provider_effect(
            intent, authorization=selection.authorization, now=int(self.now().timestamp()),
            connects_pre=0, connects_pre_hash=contract["evidence_sha256"],
            payload_body=_canonical(payload),
        )
        return intent

    def _verified_receipt(self, intent: Any, row: dict[str, Any]) -> dict[str, Any]:
        payload = json.loads(row["payload_body"])
        return {
            "state": "submitted", "submission_id": row["proposal_id"],
            "contract_id": payload["contract_id"], "milestone_id": payload["milestone_id"],
            "artifact_sha256": payload["artifact_sha256"], "readback_sha256": row["readback_hash"],
        }

    def reconcile(self, intent: Any) -> dict[str, Any] | None:
        row = self.store.provider_effect(intent)
        if row is None:
            raise ValueError("upwork_delivery_intent_missing")
        if row.get("reconciliation_state") == "verified":
            return self._verified_receipt(intent, row)
        selection = self._selection()
        receipt = self.read_submission(selection, intent)
        if receipt is None:
            return None
        payload = json.loads(row["payload_body"])
        if (
            not isinstance(receipt, dict) or receipt.get("state") != "submitted"
            or not isinstance(receipt.get("submission_id"), str) or not receipt["submission_id"]
            or receipt.get("contract_id") != payload["contract_id"]
            or receipt.get("milestone_id") != payload["milestone_id"]
            or receipt.get("artifact_sha256") != payload["artifact_sha256"]
            or not DIGEST.fullmatch(str(receipt.get("evidence_sha256") or ""))
        ):
            raise ValueError("upwork_delivery_readback_invalid")
        readback_hash = _sha({"submission_id": receipt["submission_id"], "evidence": receipt["evidence_sha256"]})
        stored = self.store.verify_provider_effect(
            intent, proposal_id=receipt["submission_id"], connects_post=0,
            readback_hash=readback_hash, now=int(self.now().timestamp()),
        )
        return self._verified_receipt(intent, stored)

    def execute(self, intent: Any) -> dict[str, Any]:
        row = self.store.provider_effect(intent)
        if row is None:
            raise ValueError("upwork_delivery_intent_missing")
        if row.get("reconciliation_state") == "verified":
            return self._verified_receipt(intent, row)
        if row.get("state") == "reconcile_pending":
            receipt = self.reconcile(intent)
            if receipt is None:
                raise ValueError("upwork_delivery_reconcile_unknown")
            return receipt
        selection = self._selection()
        payload = json.loads(row["payload_body"])
        self._contract(selection, payload["contract_id"], payload["milestone_id"], payload["contract_sha256"])
        started = self.store.mark_provider_effect_started(
            intent, authorization=selection.authorization, now=int(self.now().timestamp()),
        )
        if started.get("started") is not True:
            receipt = self.reconcile(intent)
            if receipt is None:
                raise ValueError("upwork_delivery_reconcile_unknown")
            return receipt
        try:
            receipt = self.submit(selection, intent, payload)
        except TimeoutError:
            receipt = None
        if receipt is not None:
            # The official readback callback, not the mutation ACK, is authoritative.
            receipt = self.read_submission(selection, intent)
        else:
            receipt = self.read_submission(selection, intent)
        if receipt is None:
            raise ValueError("upwork_delivery_reconcile_unknown")
        return self.reconcile(intent)
