from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS, PROVIDERS = GIG_ROOT / "scripts", GIG_ROOT / "scripts/providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from application_effect_fence import authorized_provider_intent  # noqa: E402
from connector_outbox import ConnectorOutbox  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402
from upwork_message_browser import validate_preflight, validate_readback  # noqa: E402
from upwork_message_effect import SealedUpworkMessageEffect  # noqa: E402


AUTH = AuthorizationDecision(AuthorizationState.APPROVED_BROWSER, "matching_receipt", evidence_hash="a" * 64, receipt_hash="b" * 64)


class Selection:
    authorization = AUTH


class Transport:
    def for_action(self, action):
        return Selection() if action == "message" else None

    def effect_intent(self, selection, *, resource_id, payload_hash):
        return authorized_provider_intent(provider="upwork", account_key="owner", resource_id=resource_id, action="message", payload_hash=payload_hash, authorization=selection.authorization)


def _decision():
    return {
        "decision": "clarify", "reason_codes": ["scope_missing"], "intent_sha256": "c" * 64,
        "source": {"room_id": "room-1", "room_url": "https://www.upwork.com/ab/messages/rooms/room-1", "event_id": "d" * 64, "head_sha256": "e" * 64, "revision": 1},
        "message": {"body": "Could you confirm the exact endpoint and expected response fields?", "scope": None, "price_usd": None, "expected_cost_usd": None, "margin_bps": None, "deadline": None},
    }


def _snapshot(**changes):
    value = {"room_url": "https://www.upwork.com/ab/messages/rooms/room-1", "room_id": "room-1", "room_head_sha256": "e" * 64, "message_body": _decision()["message"]["body"], "send_enabled": True, "send_label": "Send", "before_message_ids": ["story-1"], "validation_errors": []}
    value.update(changes)
    return value


def _effect(tmp_path):
    store = ConnectorOutbox(tmp_path / "outbox.sqlite3", GIG_ROOT / "config/connectors/coconala.json")
    return SealedUpworkMessageEffect(store, Transport(), now_epoch=lambda: 100), store


def _row(store):
    with sqlite3.connect(store.database) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM provider_effect_intents").fetchone())


def test_exact_current_head_and_filled_body_cross_preflight():
    assert validate_preflight(_snapshot(), _decision())["ready"] is True


@pytest.mark.parametrize("change", [
    {"room_url": "https://www.upwork.com/ab/messages/rooms/other"},
    {"room_head_sha256": "f" * 64}, {"message_body": "changed"},
    {"send_enabled": False}, {"validation_errors": ["blocked"]},
])
def test_stale_room_or_changed_message_never_crosses_fence(change):
    with pytest.raises(ValueError, match="upwork_message_preflight_mismatch"):
        validate_preflight(_snapshot(**change), _decision())


def test_durable_start_and_replay_allow_one_send_only(tmp_path):
    effect, store = _effect(tmp_path)
    preflight = validate_preflight(_snapshot(), _decision())
    intent, started = effect.start(_decision(), preflight)
    replay, second = effect.start(_decision(), preflight)
    assert started is True and second is False and replay.effect_key == intent.effect_key
    assert _row(store)["action"] == "message" and _row(store)["reconciliation_state"] == "reconcile_unknown"


def test_only_new_official_story_id_and_exact_body_verify(tmp_path):
    effect, store = _effect(tmp_path)
    intent, _ = effect.start(_decision(), validate_preflight(_snapshot(), _decision()))
    receipt = validate_readback({"room_id": "room-1", "readback_url": "https://www.upwork.com/ab/messages/rooms/room-1", "message_id": "story-2", "state": "sent", "body_sha256": None}, _decision())
    effect.verify(intent, receipt)
    assert _row(store)["reconciliation_state"] == "verified"
    assert _row(store)["proposal_id"] == "story-2"


def test_missing_story_id_stays_unknown(tmp_path):
    effect, store = _effect(tmp_path)
    effect.start(_decision(), validate_preflight(_snapshot(), _decision()))
    with pytest.raises(ValueError, match="upwork_message_send_unconfirmed"):
        validate_readback({"room_id": "room-1", "readback_url": "https://www.upwork.com/ab/messages/rooms/room-1", "message_id": None, "state": "unknown", "body_sha256": None}, _decision())
    assert _row(store)["reconciliation_state"] == "reconcile_unknown"
