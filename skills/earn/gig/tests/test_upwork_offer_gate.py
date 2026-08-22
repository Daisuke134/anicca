from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


PROVIDERS = Path(__file__).resolve().parents[1] / "scripts/providers"
if str(PROVIDERS) not in sys.path:
    sys.path.insert(0, str(PROVIDERS))
MODULE = PROVIDERS / "upwork_offer_gate.py"
spec = importlib.util.spec_from_file_location("upwork_offer_gate_test", MODULE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


def _packet(tmp_path):
    value = {
        "version": 1, "provider": "upwork", "kind": "direct_offer_detected",
        "resource_id": "offer-1", "resource_url": "https://www.upwork.com/ab/proposals/offer-1",
        "detail_evidence_sha256": "a" * 64, "observed_at": "now",
        "rendered_text": "Accept offer. Decline. Fixed-price $75. Milestone funded $75.",
    }
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path = tmp_path / f"{hashlib.sha256(body.encode()).hexdigest()}.json"
    path.write_text(body)
    path.chmod(0o600)
    return path, value


def _accept(packet, contract_type="fixed_price"):
    fixed = contract_type == "fixed_price"
    return {
        "action": "accept", "reason_codes": [], "offer": {
            "provider": "upwork", "offer_id": packet["resource_id"],
            "offer_url": packet["resource_url"],
            "offer_source_sha256": packet["detail_evidence_sha256"],
            "title": "Documented API integration", "scope": "Integrate one documented REST API endpoint.",
            "contract_type": contract_type, "rate_or_amount_usd": 75,
            "deadline": "2026-09-01",
            "payment_protection": "funded_milestone" if fixed else "verified_hourly_billing",
            "funded_milestone_usd": 75 if fixed else None,
            "weekly_limit_hours": None if fixed else 10,
            "account_state": "accept_enabled", "off_platform_required": False,
            "synchronous_or_physical_required": False,
        },
    }


def test_exact_funded_fixed_offer_is_accept_ready(tmp_path):
    path, packet = _packet(tmp_path)
    result = gate.validate_decision(_accept(packet), gate.load_offer_packet(path))
    assert result["action"] == "accept"
    assert len(result["decision_sha256"]) == 64


def test_exact_verified_hourly_offer_is_accept_ready(tmp_path):
    path, packet = _packet(tmp_path)
    result = gate.validate_decision(_accept(packet, "hourly"), gate.load_offer_packet(path))
    assert result["offer"]["weekly_limit_hours"] == 10


@pytest.mark.parametrize("field,value", [
    ("offer_id", "other"), ("offer_source_sha256", "b" * 64),
    ("account_state", "disabled"), ("off_platform_required", True),
    ("synchronous_or_physical_required", True), ("funded_milestone_usd", None),
    ("deadline", None), ("funded_milestone_usd", 74),
])
def test_unsafe_or_unbound_accept_is_rejected(tmp_path, field, value):
    path, packet = _packet(tmp_path)
    decision = _accept(packet)
    decision["offer"][field] = value
    with pytest.raises(ValueError, match="offer_acceptance_mismatch"):
        gate.validate_decision(decision, gate.load_offer_packet(path))


def test_non_accept_needs_reason_and_cannot_carry_executable_offer(tmp_path):
    path, packet = _packet(tmp_path)
    loaded = gate.load_offer_packet(path)
    assert gate.validate_decision({
        "action": "request_changes", "reason_codes": ["funding_missing"], "offer": None,
    }, loaded)["action"] == "request_changes"
    with pytest.raises(ValueError, match="offer_decision_invalid"):
        gate.validate_decision({
            "action": "decline", "reason_codes": [], "offer": None,
        }, loaded)
    with pytest.raises(ValueError, match="offer_decision_invalid"):
        gate.validate_decision({
            "action": "request_changes", "reason_codes": ["funding_missing"],
            "offer": _accept(packet)["offer"],
        }, loaded)
