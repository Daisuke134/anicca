#!/usr/bin/env python3
"""Deterministically bind an independent deliverable review to one contract and artifact set."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class DeliverableVerificationError(ValueError):
    pass


DIGEST = re.compile(r"[0-9a-f]{64}")
PRIVATE_DATA = re.compile(
    rb"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    rb"(?:api[_ -]?key|password|secret|token)\s*[:=]\s*[^\s,;]{4,}|"
    rb"\b(?:\+?\d[\d .()-]{8,}\d)\b)"
)


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, reason: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise DeliverableVerificationError(reason)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeliverableVerificationError(reason) from exc
    if not isinstance(value, dict):
        raise DeliverableVerificationError(reason)
    return value


def _result(status: str, clause: str, hashes: list[str], evidence: list[str]) -> dict[str, Any]:
    return {
        "version": 1,
        "status": status,
        "contract_clause": clause,
        "artifact_sha256": hashes,
        "evidence": evidence,
        "delivery_intent_permitted": status == "PASS",
        "next_action": "deliver" if status == "PASS" else ("execute_workflow" if status == "REVISE" else "repair_verification_input"),
    }


def verify_deliverables(*, workspace: str | Path, execution_receipt: Any,
                        reviewer_context_id: str, review: Any) -> dict[str, Any]:
    """Return PASS, REVISE, or BLOCKED without causing a marketplace effect."""
    root = Path(workspace).expanduser()
    if root.is_symlink() or not root.is_dir() or not isinstance(execution_receipt, dict):
        return _result("BLOCKED", "", [], ["execution_receipt_invalid"])
    revision = execution_receipt.get("revision_sha256")
    execution_id = execution_receipt.get("execution_id")
    hashes = [row.get("sha256", "") for row in execution_receipt.get("artifacts", []) if isinstance(row, dict)]
    requirement = root / "requirements" / "revisions" / f"{revision}.json"
    try:
        contract = _read_json(requirement, "contract_missing")
    except DeliverableVerificationError as exc:
        return _result("BLOCKED", "", hashes, [str(exc)])
    clause = str(contract.get("scope") or "").strip()
    if not clause:
        return _result("BLOCKED", clause, hashes, ["contract_criterion_missing"])
    if not isinstance(reviewer_context_id, str) or not reviewer_context_id.strip():
        return _result("BLOCKED", clause, hashes, ["reviewer_context_missing"])
    if reviewer_context_id == execution_id:
        return _result("BLOCKED", clause, hashes, ["self_approval_rejected"])

    artifacts = execution_receipt.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return _result("BLOCKED", clause, hashes, ["artifact_missing"])
    for row in artifacts:
        if not isinstance(row, dict) or not DIGEST.fullmatch(str(row.get("sha256") or "")):
            return _result("BLOCKED", clause, hashes, ["artifact_hash_invalid"])
        raw = row.get("path")
        if not isinstance(raw, str) or Path(raw).is_absolute() or ".." in Path(raw).parts:
            return _result("BLOCKED", clause, hashes, ["artifact_path_invalid"])
        path = root / raw
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except (OSError, ValueError):
            return _result("BLOCKED", clause, hashes, ["artifact_path_invalid"])
        if path.is_symlink() or not path.is_file() or _sha_file(path) != row["sha256"] or path.stat().st_size != row.get("bytes"):
            return _result("BLOCKED", clause, hashes, ["artifact_hash_mismatch"])
        if PRIVATE_DATA.search(path.read_bytes()):
            return _result("BLOCKED", clause, hashes, ["private_data_leak"])

    stored_path = root / "artifacts" / "execution-receipts" / f"{execution_id}.json"
    try:
        stored = _read_json(stored_path, "execution_receipt_missing")
    except DeliverableVerificationError as exc:
        return _result("BLOCKED", clause, hashes, [str(exc)])
    if _sha_value(stored) != _sha_value(execution_receipt):
        return _result("BLOCKED", clause, hashes, ["execution_receipt_mismatch"])
    contract_sha = _sha_value(contract)
    if execution_receipt.get("contract_sha256") != contract_sha:
        return _result("BLOCKED", clause, hashes, ["contract_hash_mismatch"])

    if not isinstance(review, dict):
        return _result("BLOCKED", clause, hashes, ["review_invalid"])
    criteria = review.get("criteria")
    matching = [row for row in criteria if isinstance(row, dict) and row.get("clause") == clause] if isinstance(criteria, list) else []
    if len(matching) != 1:
        return _result("REVISE", clause, hashes, ["contract_criterion_missing"])
    criterion = matching[0]
    if criterion.get("status") != "PASS" or not str(criterion.get("evidence") or "").strip():
        return _result("REVISE", clause, hashes, ["contract_criterion_failed"])
    claims = review.get("factual_claims")
    if not isinstance(claims, list):
        return _result("BLOCKED", clause, hashes, ["review_claims_invalid"])
    for claim in claims:
        if (not isinstance(claim, dict) or not str(claim.get("claim") or "").strip()
                or not isinstance(claim.get("evidence"), list) or not claim["evidence"]):
            return _result("REVISE", clause, hashes, ["unsupported_factual_claim"])
    if review.get("verdict") != "PASS" or not str(review.get("reason") or "").strip():
        return _result("REVISE", clause, hashes, ["review_not_pass"])
    return _result("PASS", clause, hashes, ["contract_clause_pass", "artifact_hash_verified", "independent_context_verified"])
