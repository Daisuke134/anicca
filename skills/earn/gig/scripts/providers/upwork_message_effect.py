#!/usr/bin/env python3
"""Bind one sealed Upwork message intent to the shared provider-effect ledger."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from upwork_sealed_effect import SealedEffectError


class SealedUpworkMessageEffect:
    def __init__(self, store: Any, transport: Any, *, now_epoch=None) -> None:
        self.store, self.transport = store, transport
        self.now_epoch = now_epoch or (lambda: int(time.time()))

    def intent(self, decision: dict[str, Any]):
        source, digest = decision.get("source"), decision.get("intent_sha256")
        if (
            not isinstance(source, dict) or decision.get("decision") == "no_reply"
            or not isinstance(decision.get("message"), dict)
            or not isinstance(source.get("room_id"), str) or not source["room_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(digest or ""))
        ):
            raise SealedEffectError("upwork_message_effect_invalid")
        selection = self.transport.for_action("message")
        if selection is None:
            raise SealedEffectError("authorization_not_approved")
        return selection, self.transport.effect_intent(selection, resource_id=source["room_id"], payload_hash=digest)

    def start(self, decision: dict[str, Any], preflight: dict[str, Any]):
        selection, intent = self.intent(decision)
        source = decision["source"]
        if (
            not isinstance(preflight, dict) or preflight.get("ready") is not True
            or preflight.get("room_id") != source["room_id"]
            or preflight.get("head_sha256") != source["head_sha256"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(preflight.get("evidence_sha256") or ""))
        ):
            raise SealedEffectError("upwork_message_preflight_effect_mismatch")
        row = self.store.provider_effect(intent)
        if row is None:
            row = self.store.prepare_provider_effect(
                intent, authorization=selection.authorization, now=self.now_epoch(), connects_pre=0,
                connects_pre_hash=preflight["evidence_sha256"], payload_body=json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            )
        else:
            self.store.prepare_provider_effect(intent, authorization=selection.authorization, now=self.now_epoch())
        if row["state"] != "prepared":
            return intent, False
        started = self.store.mark_provider_effect_started(intent, authorization=selection.authorization, now=self.now_epoch())
        return intent, started["started"] is True

    def verify(self, intent: Any, receipt: dict[str, Any]) -> dict[str, Any]:
        if (
            not isinstance(receipt, dict) or receipt.get("state") != "sent"
            or receipt.get("room_id") != intent.resource_id
            or not isinstance(receipt.get("message_id"), str) or not receipt["message_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("body_sha256") or ""))
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("evidence_sha256") or ""))
        ):
            raise SealedEffectError("upwork_message_readback_invalid")
        readback_hash = hashlib.sha256(json.dumps({"message": receipt["message_id"], "body": receipt["body_sha256"], "evidence": receipt["evidence_sha256"]}, sort_keys=True).encode()).hexdigest()
        return self.store.verify_provider_effect(intent, proposal_id=receipt["message_id"], connects_post=0, readback_hash=readback_hash, now=self.now_epoch())
