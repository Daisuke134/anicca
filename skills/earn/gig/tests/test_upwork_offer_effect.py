from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from application_effect_fence import authorized_provider_intent  # noqa: E402
from connector_outbox import ConnectorBusy, ConnectorOutbox  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402
from upwork_offer_browser import validate_offer_preflight, validate_offer_readback  # noqa: E402
from upwork_offer_effect import SealedUpworkOfferEffect  # noqa: E402


AUTH = AuthorizationDecision(
    AuthorizationState.APPROVED_BROWSER, "matching_receipt",
    evidence_hash="a" * 64, receipt_hash="b" * 64,
)
CAPACITY = {"active_contract_ids": [], "concurrent_job_cap": 3}


class Selection:
    authorization = AUTH


class Transport:
    def for_action(self, action):
        return Selection() if action == "accept_offer" else None

    def effect_intent(self, selection, *, resource_id, payload_hash):
        return authorized_provider_intent(
            provider="upwork", account_key="owner", resource_id=resource_id,
            action="accept_offer", payload_hash=payload_hash,
            authorization=selection.authorization,
        )


def _decision(offer_id="offer-1"):
    return {
        "action": "accept", "reason_codes": [], "decision_sha256": "c" * 64,
        "offer": {
            "provider": "upwork", "offer_id": offer_id,
            "offer_url": f"https://www.upwork.com/ab/proposals/{offer_id}",
            "offer_source_sha256": "d" * 64, "title": "API integration",
            "scope": "Integrate one documented REST API endpoint.",
            "contract_type": "fixed_price", "rate_or_amount_usd": 75,
            "deadline": "2026-09-01", "payment_protection": "funded_milestone",
            "funded_milestone_usd": 75, "weekly_limit_hours": None,
            "account_state": "accept_enabled", "off_platform_required": False,
            "synchronous_or_physical_required": False,
        },
    }


def _snapshot(**changes):
    value = {
        "offer_url": "https://www.upwork.com/ab/proposals/offer-1",
        "body_text": "API integration Integrate one documented REST API endpoint. "
                     "$75.00 2026-09-01 Milestone funded",
        "accept_label": "Accept offer", "accept_enabled": True,
    }
    value.update(changes)
    return value


def _effect(tmp_path):
    store = ConnectorOutbox(tmp_path / "outbox.sqlite3", GIG_ROOT / "config/connectors/coconala.json")
    return SealedUpworkOfferEffect(store, Transport(), now_epoch=lambda: 100), store


def _row(store):
    with sqlite3.connect(store.database) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM provider_effect_intents").fetchone())


def test_exact_live_offer_terms_cross_preflight():
    result = validate_offer_preflight(_snapshot(), _decision())
    assert result["ready"] is True and result["offer_id"] == "offer-1"


@pytest.mark.parametrize("change", [
    {"offer_url": "https://www.upwork.com/ab/proposals/other"},
    {"body_text": "API integration $75.00 2026-09-01 Milestone funded"},
    {"body_text": "API integration Integrate one documented REST API endpoint. $75.00 2026-09-01"},
    {"accept_enabled": False},
])
def test_drift_or_unprotected_offer_never_crosses_preflight(change):
    with pytest.raises(ValueError, match="upwork_offer_preflight_mismatch"):
        validate_offer_preflight(_snapshot(**change), _decision())


def test_started_offer_is_durable_and_replay_never_clicks_twice(tmp_path):
    effect, store = _effect(tmp_path)
    preflight = validate_offer_preflight(_snapshot(), _decision())
    intent, started = effect.start(_decision(), preflight, capacity=CAPACITY)
    replay, replay_started = effect.start(_decision(), preflight, capacity=CAPACITY)
    assert started is True and replay_started is False
    assert replay.effect_key == intent.effect_key
    assert _row(store)["state"] == "reconcile_pending"
    assert _row(store)["action"] == "accept_offer"


def test_two_offers_cannot_reserve_the_last_capacity_slot(tmp_path):
    first, store = _effect(tmp_path)
    second = SealedUpworkOfferEffect(store, Transport(), now_epoch=lambda: 101)
    capacity = {"active_contract_ids": [], "concurrent_job_cap": 1}

    _, started = first.start(_decision("offer-1"), validate_offer_preflight(
        _snapshot(), _decision("offer-1")), capacity=capacity,
    )
    with pytest.raises(ConnectorBusy, match="provider capacity exhausted"):
        second.start(_decision("offer-2"), {
            **validate_offer_preflight(
                _snapshot(offer_url="https://www.upwork.com/ab/proposals/offer-2"),
                _decision("offer-2"),
            ),
            "offer_id": "offer-2",
        }, capacity=capacity)

    assert started is True
    with sqlite3.connect(store.database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM provider_effect_intents WHERE action='accept_offer'"
        ).fetchone()[0] == 1


def test_only_official_contract_id_verifies_acceptance(tmp_path):
    effect, store = _effect(tmp_path)
    intent, _ = effect.start(
        _decision(), validate_offer_preflight(_snapshot(), _decision()), capacity=CAPACITY,
    )
    receipt = validate_offer_readback({
        "offer_id": "offer-1", "readback_url": "https://www.upwork.com/ab/w/workroom/contract-1",
        "contract_id": "contract-1", "state": "accepted",
    }, _decision())
    effect.verify(intent, receipt)
    assert _row(store)["reconciliation_state"] == "verified"
    assert _row(store)["proposal_id"] == "contract-1"


def test_missing_contract_id_stays_unverified(tmp_path):
    effect, store = _effect(tmp_path)
    effect.start(
        _decision(), validate_offer_preflight(_snapshot(), _decision()), capacity=CAPACITY,
    )
    with pytest.raises(ValueError, match="upwork_offer_accept_unconfirmed"):
        validate_offer_readback({
            "offer_id": "offer-1", "readback_url": "https://www.upwork.com/ab/proposals/offer-1",
            "contract_id": None, "state": "unknown",
        }, _decision())
    assert _row(store)["reconciliation_state"] == "reconcile_unknown"
