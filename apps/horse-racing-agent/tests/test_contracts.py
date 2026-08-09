import pytest

from horse_racing_agent.contracts import (
    RegistryDependencyBlocked,
    build_horse_racing_candidate,
)


def test_registry_v2_candidate_is_exact_and_deterministic():
    args = {
        "cfo_exact_seven_complete": True,
        "hra6_compliance_receipts_complete": False,
        "requested_live_purchase": True,
    }
    expected = {
        "registry": "v2",
        "business_id": "horse_racing",
        "candidate_ordinal": 8,
        "depends_on": "CFO-0c exact-seven",
        "live_purchase": "disabled",
    }
    assert build_horse_racing_candidate(**args) == expected
    assert build_horse_racing_candidate(**args) == build_horse_racing_candidate(**args)


def test_incomplete_cfo_dependency_blocks_before_candidate():
    with pytest.raises(RegistryDependencyBlocked, match="CFO-0c exact-seven"):
        build_horse_racing_candidate(
            cfo_exact_seven_complete=False,
            hra6_compliance_receipts_complete=False,
        )


def test_live_purchase_cannot_be_enabled_by_caller_input():
    for receipts_complete in (False, True):
        candidate = build_horse_racing_candidate(
            cfo_exact_seven_complete=True,
            hra6_compliance_receipts_complete=receipts_complete,
            requested_live_purchase=True,
        )
        assert candidate["live_purchase"] == "disabled"
