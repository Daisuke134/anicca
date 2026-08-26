from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from ..state import canonical_url
from .checkpoint import _atomic_private
from .contracts import FinalReviewReceiptV1, SubmissionFenceLeaseV1


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SubmissionFence:
    """Persist one short-lived, one-shot authorization for the final click."""

    def __init__(self, ledger, root: Path) -> None:
        self._ledger = ledger
        self._root = root

    def _key(self, intent_id: str) -> str:
        return hashlib.sha256(intent_id.encode()).hexdigest()

    @contextmanager
    def _locked(self, intent_id: str) -> Iterator[Path]:
        directory = self._root / "submission-fences"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        key = self._key(intent_id)
        lock_path = directory / f"{key}.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield directory / f"{key}.json"

    def _intent(self, intent_id: str):
        row = self._ledger.connection.execute(
            """
            SELECT submit_intents.intent_id, submit_intents.fence,
                   submit_intents.application_id, submit_intents.resume_sha256,
                   submit_intents.status, applications.canonical_url
            FROM submit_intents
            JOIN applications ON applications.id = submit_intents.application_id
            WHERE submit_intents.intent_id = ?
            """,
            (intent_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("submission intent does not exist")
        return row

    def acquire(
        self,
        intent_id: str,
        fence: int,
        review: FinalReviewReceiptV1,
        ttl_seconds: int = 120,
    ) -> SubmissionFenceLeaseV1:
        if not 1 <= ttl_seconds <= 300:
            raise ValueError("submission fence TTL must be 1..300 seconds")
        with self._locked(intent_id) as path:
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("consumed_at") or datetime.fromisoformat(
                    existing["expires_at"]
                ) > _now():
                    raise RuntimeError("submission fence is already active or consumed")
            row = self._intent(intent_id)
            if str(row["status"]) != "submit_claimed" or int(row["fence"]) != fence:
                raise RuntimeError("submission intent is stale or terminal")
            if str(row["application_id"]) != review.application_id:
                raise RuntimeError("submission application identity mismatch")
            if canonical_url(str(row["canonical_url"])) != review.canonical_url:
                raise RuntimeError("submission URL identity mismatch")
            if str(row["resume_sha256"]) != review.resume_sha256:
                raise RuntimeError("submission resume identity mismatch")
            capability = secrets.token_hex(32)
            expires_at = (_now() + timedelta(seconds=ttl_seconds)).isoformat()
            state = {
                "intent_id": intent_id,
                "fence": fence,
                "review_receipt_sha256": review.receipt_sha256,
                "observation_sha256": review.observation_sha256,
                "expires_at": expires_at,
                "capability_sha256": hashlib.sha256(capability.encode()).hexdigest(),
                "consumed_at": None,
            }
            _atomic_private(path, (json.dumps(state, sort_keys=True) + "\n").encode())
            return SubmissionFenceLeaseV1(
                intent_id, fence, review.receipt_sha256,
                review.observation_sha256, expires_at, capability,
            )

    def consume(self, lease: SubmissionFenceLeaseV1, observation_sha256: str) -> str:
        with self._locked(lease.intent_id) as path:
            if not path.exists():
                raise RuntimeError("submission fence does not exist")
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("consumed_at"):
                raise RuntimeError("submission fence was already consumed")
            if datetime.fromisoformat(state["expires_at"]) <= _now():
                raise RuntimeError("submission fence expired")
            if state["fence"] != lease.fence or state["observation_sha256"] != observation_sha256:
                raise RuntimeError("submission fence is stale for this observation")
            capability_sha = hashlib.sha256(lease.capability.encode()).hexdigest()
            if not secrets.compare_digest(state["capability_sha256"], capability_sha):
                raise RuntimeError("submission fence capability mismatch")
            row = self._intent(lease.intent_id)
            if str(row["status"]) != "submit_claimed" or int(row["fence"]) != lease.fence:
                raise RuntimeError("submission intent became stale or terminal")
            state["consumed_at"] = _now().isoformat()
            _atomic_private(path, (json.dumps(state, sort_keys=True) + "\n").encode())
            return hashlib.sha256(
                json.dumps(state, sort_keys=True).encode()
            ).hexdigest()
