"""Recoverable RETIRE contract: gates, real seller control, and fail-closed behaviour.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_retire.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

SERVICE_ID = "4312985"
VERSION = "a" * 64
FAMILY = {SERVICE_ID: "ui_translation"}
SOURCE = {"service_id": SERVICE_ID, "service_version_sha256": VERSION}
ARCHIVE_CONTROL = {"tag": "A", "type": None, "label": "OK",
                   "href": f"/services/archive/{SERVICE_ID}", "id": None,
                   "cls": "button-solid modi_black js_change-open-status",
                   "context": "公開停止しますか？公開停止後も再公開できます。"}
INVENTORY_ROW = {"service_id": SERVICE_ID, "state": sd.PUBLIC_LISTING_STATE, "price_jpy": 4500,
                 "state_controls": [
                     {"tag": "A", "label": "編集する", "href": f"/mypage/services/{SERVICE_ID}",
                      "cls": "", "id": None, "context": None},
                     ARCHIVE_CONTROL]}
ALLOCATION = {
    "service_id": SERVICE_ID, "action": "RETIRE", "allocation_key": "b" * 64,
    "gates": {"minimum_sample_met": True, "weak_demand_evidence": True,
              "slot_capacity_pressure": True, "recoverable_retire_gates_met": True},
}


def seller_form(controls):
    return {"url": f"https://coconala.com/mypage/services/{SERVICE_ID}", "submit_controls": controls}


def render(**overrides):
    kwargs = {"source": SOURCE, "inventory_row": INVENTORY_ROW,
              "seller_snapshot": seller_form([
                  {"mode": "open", "label": "公開する", "disabled": False},
                  {"mode": "draft", "label": "下書き保存", "disabled": False},
              ]),
              "capability_families": FAMILY, "allocation": ALLOCATION}
    kwargs.update(overrides)
    return sd._render_listing_state_mutation(**kwargs)


def test_retire_contract_changes_only_the_listing_state_and_keeps_a_public_rollback():
    contract = render()
    assert contract["changed_field"] == "listing_state"
    assert contract["allowed_delta"] == [sd.LISTING_STATE_DELTA]
    assert contract["proposed_value"]["action"] == f"/services/archive/{SERVICE_ID}"
    assert contract["proposed_value"]["listing_state"] == "非公開"
    # Recoverable: rollback restores the public state, and the contract never asks for deletion.
    assert contract["rollback_value"] == {"listing_state": sd.PUBLIC_LISTING_STATE, "action": "none"}
    assert contract["official_readback"]["deletion"] is False
    assert contract["official_readback"]["recoverable"] is True
    assert len(contract["contract_sha256"]) == 64


def test_retire_fails_closed_when_the_seller_form_exposes_no_non_public_control():
    with pytest.raises(RuntimeError, match="storefront_retire_control_missing"):
        render(inventory_row={**INVENTORY_ROW, "state_controls": [
            {"tag": "A", "label": "編集する", "href": "/mypage/services/1", "cls": "", "context": None}]})
    with pytest.raises(RuntimeError, match="storefront_retire_controls_unobserved"):
        render(inventory_row={**INVENTORY_ROW, "state_controls": []})
    with pytest.raises(RuntimeError, match="storefront_retire_control_wording_unobserved"):
        render(inventory_row={**INVENTORY_ROW,
                              "state_controls": [{**ARCHIVE_CONTROL, "context": ""}]})


def test_retire_fails_closed_on_unmet_gates_or_a_listing_that_is_not_public():
    with pytest.raises(RuntimeError, match="storefront_retire_gates_unmet"):
        render(allocation={**ALLOCATION, "gates": {"recoverable_retire_gates_met": False}})
    with pytest.raises(RuntimeError, match="storefront_retire_listing_not_public"):
        render(inventory_row={**INVENTORY_ROW, "state": "下書き"})


def test_short_term_zero_sales_alone_never_reaches_the_retire_action():
    # Zero sales with an unknown/insufficient sample must not produce RETIRE or REPLACE.
    assert ALLOCATION["gates"]["minimum_sample_met"] is True
    with pytest.raises(RuntimeError, match="storefront_retire_allocation_invalid"):
        render(allocation={**ALLOCATION, "action": "IMPROVE"})


def test_replace_plan_requires_a_ready_candidate_and_keeps_a_republish_rollback():
    retire = render()
    create = {"draft_service_id": "4356229", "contract_sha256": "c" * 64,
              "expected_public_url": "https://coconala.com/services/4356229"}
    allocation = {**ALLOCATION, "action": "REPLACE"}
    plan = sd._render_replace_plan(retire, create, allocation)
    assert plan["sequence"] == ["retire", "create"]
    assert plan["retired_service_id"] == SERVICE_ID and plan["created_service_id"] == "4356229"
    # A failed creation must be able to put the old listing back.
    assert plan["rollback"] == {"republish_service_id": SERVICE_ID, "restore_to": sd.PUBLIC_LISTING_STATE,
                                "on": "create_failed_after_retire"}
    assert len(plan["plan_sha256"]) == 64

    # Never retire a slot before the replacement contract exists.
    with pytest.raises(RuntimeError, match="storefront_replace_without_ready_candidate"):
        sd._render_replace_plan(retire, None, allocation)
    with pytest.raises(RuntimeError, match="storefront_replace_identity_invalid"):
        sd._render_replace_plan(retire, {**create, "draft_service_id": SERVICE_ID}, allocation)
    with pytest.raises(RuntimeError, match="storefront_replace_allocation_invalid"):
        sd._render_replace_plan(retire, create, ALLOCATION)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
