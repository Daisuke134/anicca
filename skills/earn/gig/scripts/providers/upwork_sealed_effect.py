#!/usr/bin/env python3
"""Bind one private sealed Upwork proposal to the shared durable provider fence."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from provider_authorization import AuthorizationState, load_receipts


class SealedEffectError(ValueError):
    """The proposal effect is not exact enough to mutate Upwork."""


class SealedUpworkProposalEffect:
    def __init__(self, store: Any, transport: Any, *, now_epoch=None) -> None:
        self.store = store
        self.transport = transport
        self.now_epoch = now_epoch or (lambda: int(time.time()))

    @staticmethod
    def _identity(payload: dict[str, Any]) -> tuple[str, str, int]:
        if not isinstance(payload, dict) or payload.get("provider") != "upwork":
            raise SealedEffectError("upwork_sealed_effect_invalid")
        job_id = payload.get("job_id")
        digest = payload.get("payload_sha256")
        terms = payload.get("terms")
        required = terms.get("required_connects") if isinstance(terms, dict) else None
        if (
            not isinstance(job_id, str) or not job_id.startswith("~")
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(required) is not int or required < 0
        ):
            raise SealedEffectError("upwork_sealed_effect_invalid")
        return job_id, digest, required

    def intent(self, payload: dict[str, Any]):
        job_id, digest, _ = self._identity(payload)
        selection = self.transport.for_action("propose")
        if selection is None:
            raise SealedEffectError("authorization_not_approved")
        return selection, self.transport.effect_intent(
            selection, resource_id=job_id, payload_hash=digest,
        )

    def start(self, payload: dict[str, Any], preflight: dict[str, Any]):
        selection, intent = self.intent(payload)
        job_id, _, required = self._identity(payload)
        if (
            not isinstance(preflight, dict) or preflight.get("ready") is not True
            or preflight.get("job_id") != job_id
            or preflight.get("required_connects") != required
            or type(preflight.get("available_connects")) is not int
            or preflight["available_connects"] < required
            or not re.fullmatch(r"[0-9a-f]{64}", str(preflight.get("evidence_sha256") or ""))
        ):
            raise SealedEffectError("upwork_preflight_effect_mismatch")
        row = self.store.provider_effect(intent)
        if row is None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            row = self.store.prepare_provider_effect(
                intent, authorization=selection.authorization, now=self.now_epoch(),
                connects_pre=preflight["available_connects"],
                connects_pre_hash=preflight["evidence_sha256"], payload_body=body,
            )
        else:
            self.store.prepare_provider_effect(
                intent, authorization=selection.authorization, now=self.now_epoch(),
            )
        if row["state"] != "prepared":
            return intent, False
        started = self.store.mark_provider_effect_started(
            intent, authorization=selection.authorization, now=self.now_epoch(),
        )
        return intent, started["started"] is True

    def verify(
        self, intent: Any, receipt: dict[str, Any], *, connects_post: int,
        connects_evidence_sha256: str,
    ) -> dict[str, Any]:
        if (
            not isinstance(receipt, dict) or receipt.get("state") != "submitted"
            or receipt.get("job_id") != intent.resource_id
            or not isinstance(receipt.get("proposal_id"), str) or not receipt["proposal_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("evidence_sha256") or ""))
            or type(connects_post) is not int or connects_post < 0
            or not re.fullmatch(r"[0-9a-f]{64}", connects_evidence_sha256)
        ):
            raise SealedEffectError("upwork_effect_readback_invalid")
        row = self.store.provider_effect(intent)
        try:
            required = json.loads(row["payload_body"])["terms"]["required_connects"]
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise SealedEffectError("upwork_effect_readback_invalid") from exc
        if type(required) is not int or connects_post != row["connects_pre"] - required:
            raise SealedEffectError("upwork_connects_effect_mismatch")
        combined = json.dumps({
            "proposal": receipt["evidence_sha256"],
            "connects": connects_evidence_sha256,
        }, sort_keys=True, separators=(",", ":"))
        readback_hash = hashlib.sha256(combined.encode()).hexdigest()
        return self.store.verify_provider_effect(
            intent, proposal_id=receipt["proposal_id"], connects_post=connects_post,
            readback_hash=readback_hash, now=self.now_epoch(),
        )


def active_upwork_browser_account(path: Path, now: datetime, action: str = "propose") -> str:
    """Return the one active private browser account for an exact action."""
    matches = {
        receipt.account for receipt in load_receipts(path.expanduser())
        if receipt.provider == "upwork" and receipt.action == action
        and receipt.transport == "cloak_browser"
        and receipt.state is AuthorizationState.APPROVED_BROWSER
        and receipt.issued_at <= now < receipt.expires_at
    }
    if len(matches) != 1:
        raise SealedEffectError(f"upwork_active_{action}_account_not_unique")
    return next(iter(matches))
