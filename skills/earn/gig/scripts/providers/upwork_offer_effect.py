#!/usr/bin/env python3
"""Bind one qualified Upwork Direct Offer to the shared durable effect fence."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from upwork_sealed_effect import SealedEffectError


class SealedUpworkOfferEffect:
    def __init__(self, store: Any, transport: Any, *, now_epoch=None) -> None:
        self.store = store
        self.transport = transport
        self.now_epoch = now_epoch or (lambda: int(time.time()))

    @staticmethod
    def _identity(decision: dict[str, Any]) -> tuple[str, str]:
        offer = decision.get("offer") if isinstance(decision, dict) else None
        digest = decision.get("decision_sha256") if isinstance(decision, dict) else None
        if (
            not isinstance(decision, dict) or decision.get("action") != "accept"
            or not isinstance(offer, dict) or offer.get("provider") != "upwork"
            or not isinstance(offer.get("offer_id"), str) or not offer["offer_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(digest or ""))
        ):
            raise SealedEffectError("upwork_offer_effect_invalid")
        return offer["offer_id"], digest

    def intent(self, decision: dict[str, Any]):
        offer_id, digest = self._identity(decision)
        selection = self.transport.for_action("accept_offer")
        if selection is None:
            raise SealedEffectError("authorization_not_approved")
        return selection, self.transport.effect_intent(selection, resource_id=offer_id, payload_hash=digest)

    def start(
        self, decision: dict[str, Any], preflight: dict[str, Any], *,
        capacity: dict[str, Any] | None = None,
    ):
        selection, intent = self.intent(decision)
        offer_id, _ = self._identity(decision)
        if (
            not isinstance(preflight, dict) or preflight.get("ready") is not True
            or preflight.get("offer_id") != offer_id
            or not re.fullmatch(r"[0-9a-f]{64}", str(preflight.get("evidence_sha256") or ""))
        ):
            raise SealedEffectError("upwork_offer_preflight_effect_mismatch")
        if (
            not isinstance(capacity, dict)
            or set(capacity) != {"active_contract_ids", "concurrent_job_cap"}
            or not isinstance(capacity["active_contract_ids"], list)
            or type(capacity["concurrent_job_cap"]) is not int
        ):
            raise SealedEffectError("upwork_offer_capacity_invalid")
        row = self.store.provider_effect(intent)
        if row is None:
            body = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            row = self.store.prepare_provider_effect(
                intent, authorization=selection.authorization, now=self.now_epoch(),
                connects_pre=0, connects_pre_hash=preflight["evidence_sha256"], payload_body=body,
                capacity_limit=capacity["concurrent_job_cap"],
                active_resource_ids=capacity["active_contract_ids"],
            )
        else:
            self.store.prepare_provider_effect(intent, authorization=selection.authorization, now=self.now_epoch())
        if row["state"] != "prepared":
            return intent, False
        started = self.store.mark_provider_effect_started(
            intent, authorization=selection.authorization, now=self.now_epoch(),
        )
        return intent, started["started"] is True

    def verify(self, intent: Any, receipt: dict[str, Any]) -> dict[str, Any]:
        if (
            not isinstance(receipt, dict) or receipt.get("state") != "accepted"
            or receipt.get("offer_id") != intent.resource_id
            or not isinstance(receipt.get("contract_id"), str) or not receipt["contract_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("evidence_sha256") or ""))
        ):
            raise SealedEffectError("upwork_offer_readback_invalid")
        readback_hash = hashlib.sha256(json.dumps({
            "contract_id": receipt["contract_id"], "evidence": receipt["evidence_sha256"],
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return self.store.verify_provider_effect(
            intent, proposal_id=receipt["contract_id"], connects_post=0,
            readback_hash=readback_hash, now=self.now_epoch(),
        )
