from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from .contracts import (
    CheckpointReceiptV1,
    EvidenceReceiptV1,
    RowCheckpointV1,
    StepEvidenceV1,
)


def _row_key(row_run_id: str) -> str:
    if not row_run_id:
        raise ValueError("row_run_id is required")
    return hashlib.sha256(row_run_id.encode()).hexdigest()


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _atomic_private(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class CheckpointStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, row_run_id: str) -> Path:
        return self._root / "checkpoints" / f"{_row_key(row_run_id)}.json"

    def load(self, row_run_id: str) -> RowCheckpointV1 | None:
        path = self._path(row_run_id)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("row_run_id") != row_run_id or value.get("schema_version") != 1:
            raise RuntimeError("checkpoint identity or schema mismatch")
        value["action_receipt_hashes"] = tuple(value["action_receipt_hashes"])
        return RowCheckpointV1(**value)

    def save(self, checkpoint: RowCheckpointV1) -> CheckpointReceiptV1:
        if checkpoint.schema_version != 1 or checkpoint.remaining_steps < 0:
            raise ValueError("invalid checkpoint")
        if not _sha256(checkpoint.observation_sha256) or not all(
            _sha256(value) for value in checkpoint.action_receipt_hashes
        ):
            raise ValueError("checkpoint evidence fields must be SHA-256 references")
        if checkpoint.current_url:
            parsed = urlparse(checkpoint.current_url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError("checkpoint current_url must be absolute HTTPS")
        payload = _canonical(asdict(checkpoint))
        path = self._path(checkpoint.row_run_id)
        _atomic_private(path, payload)
        return CheckpointReceiptV1(path, hashlib.sha256(payload).hexdigest())


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _directory(self, row_run_id: str) -> Path:
        return self._root / "steps" / _row_key(row_run_id)

    def read_chain(self, row_run_id: str) -> tuple[EvidenceReceiptV1, ...]:
        directory = self._directory(row_run_id)
        receipts: list[EvidenceReceiptV1] = []
        predecessor = None
        for path in sorted(directory.glob("*.json")) if directory.exists() else ():
            payload = path.read_bytes()
            value = json.loads(payload)
            digest = hashlib.sha256(payload).hexdigest()
            if value.get("row_run_id") != row_run_id:
                raise RuntimeError("evidence identity mismatch")
            if value.get("sequence") != len(receipts) or value.get("predecessor_sha256") != predecessor:
                raise RuntimeError("broken evidence predecessor chain")
            receipts.append(EvidenceReceiptV1(len(receipts), digest, path))
            predecessor = digest
        return tuple(receipts)

    def append(self, step: StepEvidenceV1) -> EvidenceReceiptV1:
        if step.schema_version != 1 or step.sequence < 0:
            raise ValueError("invalid step evidence")
        hashes = (
            step.before_observation_sha256,
            step.action_receipt_sha256,
            step.after_observation_sha256,
        )
        if not all(_sha256(value) for value in hashes):
            raise ValueError("step evidence fields must be SHA-256 references")
        chain = self.read_chain(step.row_run_id)
        expected_predecessor = chain[-1].evidence_sha256 if chain else None
        if step.sequence != len(chain) or step.predecessor_sha256 != expected_predecessor:
            raise RuntimeError("step sequence or predecessor mismatch")
        payload = _canonical(asdict(step))
        directory = self._directory(step.row_run_id)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        path = directory / f"{step.sequence:08d}.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return EvidenceReceiptV1(step.sequence, hashlib.sha256(payload).hexdigest(), path)
