from __future__ import annotations

import json

from ..state import canonical_url as normalize_url
from ..state import provider_recovery_url
from ..state import same_application_surface
from .checkpoint import CheckpointStore, EvidenceStore
from .contracts import ResumeCursorV1, SessionHandleV1
from .session import BrowserSession


class RowResumer:
    """Restore one pre-submit cursor without replaying prior browser actions."""

    def __init__(
        self,
        session: BrowserSession,
        checkpoints: CheckpointStore,
        evidence: EvidenceStore,
    ) -> None:
        self._session = session
        self._checkpoints = checkpoints
        self._evidence = evidence

    async def restore(
        self, endpoint: str, row_run_id: str, canonical_url: str
    ) -> ResumeCursorV1:
        checkpoint = self._checkpoints.load(row_run_id)
        if checkpoint is None:
            handle = await self._session.attach(endpoint, row_run_id)
            needs_navigation = not same_application_surface(
                self._session.page(handle).url, canonical_url
            )
            return ResumeCursorV1(
                handle, None, None, needs_navigation, canonical_url
            )

        chain = self._evidence.read_chain(row_run_id)
        if len(chain) != len(checkpoint.action_receipt_hashes):
            raise RuntimeError("checkpoint and evidence action counts differ")
        for receipt, expected_action_hash in zip(
            chain, checkpoint.action_receipt_hashes, strict=True
        ):
            step = json.loads(receipt.path.read_text(encoding="utf-8"))
            if step.get("action_receipt_sha256") != expected_action_hash:
                raise RuntimeError("checkpoint and evidence action hashes differ")

        prior = SessionHandleV1(
            1,
            endpoint,
            row_run_id,
            checkpoint.page_marker,
            checkpoint.session_generation,
        )
        handle, recovered = await self._session.resume(prior)
        page_matches = same_application_surface(
            self._session.page(handle).url, canonical_url
        )
        recovery_url = checkpoint.current_url or canonical_url
        if not page_matches:
            recovery_url = provider_recovery_url(canonical_url)
        elif normalize_url(recovery_url) == normalize_url(canonical_url):
            recovery_url = provider_recovery_url(canonical_url)
        return ResumeCursorV1(
            handle,
            checkpoint,
            chain[-1].evidence_sha256 if chain else None,
            not recovered or not page_matches,
            recovery_url,
        )
