"""Two listings selling the same thing under nearly the same name are one too many.

`_near_duplicate_listings` used to declare a duplicate by a 0.9 title-similarity ratio -- the
five tests this file used to carry directly against that ratio. That gate measured at most 0.857
across the eight real listings it was supposed to catch and never fired in production, so
whether two listings are substitutes is now a model judgement, not a string measure (see
storefront_duplicate_judgement.schema.json). The mocked-model coverage this replaces --
including the "same family, different offer" and "reworded pair" cases this file used to check --
now lives in `test_storefront_duplicate_judgement.py`, which also carries the regression check
that the old 0.9 ratio could never have caught the real case. The one test kept here, an
unreadable title is never compared, still holds unchanged: it is a structural filter applied
before the model is ever called, not part of what the model decides.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402

FAMILIES = {
    "4357844": "excel_automation",
    "4357869": "excel_automation",
    "91000005": "excel_automation",
    "91000004": "presentation_design",
}


def test_a_listing_whose_title_could_not_be_read_is_not_compared(tmp_path):
    rows = [{"service_id": "4357844", "title_stem": None},
            {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"}]
    # Only one row survives the title_stem filter, so the function returns before it would ever
    # need to call the model -- no mock required to prove this.
    assert storefront_direct._near_duplicate_listings(
        rows, FAMILIES, state_dir=tmp_path, evidence_dir=tmp_path / "evidence",
    ) == []


def test_a_withdrawn_listing_is_never_deleted_as_litter(tmp_path):
    """4356229 is a draft because the platform withdrew it, not because a publication failed."""
    import json as _json

    ledger = tmp_path / "new-listing-drafts.jsonl"
    ledger.write_text(_json.dumps({
        "draft_service_id": "4356229", "status": "published", "public_effect": 1,
    }) + "\n", encoding="utf-8")
    drafts = ["4356229", "4356299", "4357788"]

    assert storefront_direct._deletable_drafts(ledger, drafts) == ["4356299", "4357788"]
    assert storefront_direct._deletable_drafts(tmp_path / "absent.jsonl", drafts) == sorted(drafts)


def test_latest_unpublished_candidate_per_family_is_not_deleted_as_litter(tmp_path):
    import json as _json

    ledger = tmp_path / "new-listing-drafts.jsonl"
    ledger.write_text("\n".join(_json.dumps(row) for row in [
        {"draft_service_id": "4371756", "status": "draft_created",
         "capability_family": "ai-automation-builder", "public_effect": 0},
        {"draft_service_id": "4371796", "status": "draft_created",
         "capability_family": "ai-automation-builder", "public_effect": 0},
    ]) + "\n", encoding="utf-8")

    assert storefront_direct._deletable_drafts(
        ledger, ["4371756", "4371796"],
    ) == ["4371756"]


def test_an_active_draft_stuck_on_an_unhealable_subscription_pair_loses_its_protection(tmp_path):
    """Draft 4385273 (mobile_app_dev) kept resubmitting a can_subscribe/discount_ratio pair
    Coconala's own edit form can never actually clear. The active-family guard that normally
    protects a mid-flight draft must step aside for this specific, precisely diagnosed case so
    the loop can delete it and rebuild from a blank draft, instead of resubmitting forever."""
    import hashlib
    import json as _json

    poisoned_unsigned = {
        "draft_service_id": "4385273",
        "capability_evidence": {"family": "mobile_app_dev", "recurring_support_included": False},
        "demand_evidence_path": "/evidence/mobile.json",
        "subscription": {"enabled": True, "discount_ratio": "5"},
        # A real recovered contract always carries the target category's own discovered facet
        # groups (see storefront_facet_proposal); this is what a post-facets-fix seal looks like.
        "category_specific": {"facets": {}},
    }
    digest = hashlib.sha256(_json.dumps(
        poisoned_unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    poisoned_contract = {**poisoned_unsigned, "contract_sha256": digest}
    evidence = tmp_path / "evidence" / "wake-1"
    evidence.mkdir(parents=True)
    (evidence / "generated-create-contract.json").write_text(
        _json.dumps(poisoned_contract) + "\n", encoding="utf-8",
    )
    (tmp_path / "wakes.jsonl").write_text(_json.dumps({
        "pass_id": "wake-1", "status": "completed",
        "new_listing_draft": {
            "status": "prepared", "readback": 1, "public_effect": 0,
            "draft_service_id": "4385273", "contract_sha256": digest,
            "capability_family": "mobile_app_dev",
            "demand_evidence_path": "/evidence/mobile.json",
        },
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "new-listing-drafts.jsonl"
    ledger.write_text(_json.dumps({
        "draft_service_id": "4385273", "status": "prepared", "public_effect": 0,
        "capability_family": "mobile_app_dev", "demand_evidence_path": "/evidence/mobile.json",
        "contract_sha256": digest,
    }) + "\n", encoding="utf-8")

    assert storefront_direct._deletable_drafts(ledger, ["4385273"]) == ["4385273"]
    # A healthy active draft -- one whose recorded contract already matches what healing would
    # produce -- keeps its protection; only the provably stuck one loses it.
    healthy_unsigned = {**poisoned_unsigned, "draft_service_id": "9999999",
                        "subscription": {"enabled": False, "discount_ratio": "0"}}
    healthy_digest = hashlib.sha256(_json.dumps(
        healthy_unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    healthy_contract = {**healthy_unsigned, "contract_sha256": healthy_digest}
    (evidence / "generated-create-contract.json").write_text(
        _json.dumps(healthy_contract) + "\n", encoding="utf-8",
    )
    (tmp_path / "wakes.jsonl").write_text(_json.dumps({
        "pass_id": "wake-1", "status": "completed",
        "new_listing_draft": {
            "status": "prepared", "readback": 1, "public_effect": 0,
            "draft_service_id": "9999999", "contract_sha256": healthy_digest,
            "capability_family": "mobile_app_dev",
            "demand_evidence_path": "/evidence/mobile.json",
        },
    }) + "\n", encoding="utf-8")
    ledger.write_text(_json.dumps({
        "draft_service_id": "9999999", "status": "prepared", "public_effect": 0,
        "capability_family": "mobile_app_dev", "demand_evidence_path": "/evidence/mobile.json",
        "contract_sha256": healthy_digest,
    }) + "\n", encoding="utf-8")

    assert storefront_direct._deletable_drafts(ledger, ["9999999"]) == []


def test_a_draft_with_both_a_create_and_a_prepare_row_is_judged_by_the_prepare_row(tmp_path):
    """Draft 4385965 (mobile_app_dev) was correctly healed and prepared, then wrongly deleted on
    2026-09-05: `_deletable_drafts` matched ledger rows against the literal string
    `"draft_prepared"`, which `prepare_draft` never actually writes (it writes `"prepared"`), so
    the guard silently fell back to whichever row had status `"draft_created"` -- an earlier,
    now-superseded contract from before the draft was filled in. Comparing that stale contract to
    what healing produces today always looked like a mismatch, so a perfectly healthy, freshly
    prepared draft lost its protection and was deleted for no reason. Every draft that completes
    its normal create-then-prepare lifecycle carries exactly this two-row shape, so this is not an
    edge case -- it must be judged by its own latest (prepare) row, not its create row."""
    import hashlib
    import json as _json

    healthy_unsigned = {
        "draft_service_id": "4385965",
        "capability_evidence": {"family": "mobile_app_dev", "recurring_support_included": False},
        "demand_evidence_path": "/evidence/mobile.json",
        "subscription": {"enabled": False, "discount_ratio": "0"},
    }
    healthy_digest = hashlib.sha256(_json.dumps(
        healthy_unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    healthy_contract = {**healthy_unsigned, "contract_sha256": healthy_digest}
    evidence = tmp_path / "evidence" / "wake-2"
    evidence.mkdir(parents=True)
    (evidence / "generated-create-contract.json").write_text(
        _json.dumps(healthy_contract) + "\n", encoding="utf-8",
    )
    (tmp_path / "wakes.jsonl").write_text("\n".join(_json.dumps(row) for row in [
        {
            "pass_id": "wake-2", "status": "completed",
            "new_listing_draft": {
                "status": "prepared", "readback": 1, "public_effect": 0,
                "draft_service_id": "4385965", "contract_sha256": healthy_digest,
                "capability_family": "mobile_app_dev",
                "demand_evidence_path": "/evidence/mobile.json",
            },
        },
    ]) + "\n", encoding="utf-8")
    ledger = tmp_path / "new-listing-drafts.jsonl"
    # The create row is written first and carries a different (interim) contract_sha256, exactly
    # like a real draft_created row does before the form has been filled in.
    ledger.write_text("\n".join(_json.dumps(row) for row in [
        {"draft_service_id": "4385965", "status": "draft_created", "public_effect": 0,
         "capability_family": "mobile_app_dev", "demand_evidence_path": "/evidence/mobile.json",
         "contract_sha256": "interim-create-time-contract-sha"},
        {"draft_service_id": "4385965", "status": "prepared", "public_effect": 0,
         "capability_family": "mobile_app_dev", "demand_evidence_path": "/evidence/mobile.json",
         "contract_sha256": healthy_digest},
    ]) + "\n", encoding="utf-8")

    assert storefront_direct._deletable_drafts(ledger, ["4385965"]) == []
