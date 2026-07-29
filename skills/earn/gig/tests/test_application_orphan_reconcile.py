from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "application_orphan_reconcile.py"
)
SPEC = importlib.util.spec_from_file_location("application_orphan_reconcile", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_candidate_is_bound_to_archived_live_dom_and_pass(tmp_path):
    root = tmp_path / "gig-pass-1785278864-65816" / "agent-B2"
    root.mkdir(parents=True)
    path = root / "request-5170842.json"
    path.write_text(json.dumps({
        "url": "https://coconala.com/requests/5170842",
        "not_found": False,
        "observed": True,
        "title": "AIツール活用のWebサイト制作 | ココナラ",
    }) + "\n", encoding="utf-8")

    assert MODULE.candidate_from_evidence(path) == {
        "request_id": "5170842",
        "bucket": "single",
        "title": "AIツール活用のWebサイト制作",
        "url": "https://coconala.com/requests/5170842",
        "pass_id": "1785278864-65816",
        "source_evidence": str(path.resolve()),
    }


def test_canonical_readback_is_required_before_orphan_becomes_applied(tmp_path):
    candidate = {
        "request_id": "5170842",
        "bucket": "single",
        "title": "AIツール活用のWebサイト制作",
        "url": "https://coconala.com/requests/5170842",
        "pass_id": "1785278864-65816",
        "source_evidence": "/evidence/request-5170842.json",
    }
    output = tmp_path / "recovery.json"
    captured = {
        "source": "code_owned_cdp_readback",
        "request_ids": ["5170842"],
        "offers": [{
            "request_id": "5170842",
            "offer_url": "https://coconala.com/mypage/offers/6274001",
            "title": candidate["title"],
        }],
    }

    rows, payload = MODULE.reconcile_orphans(
        [],
        candidates=[candidate],
        captured=captured,
        recovery_id="recovery-1",
        observed_at=1785282000,
        evidence_path=output,
    )

    assert rows[0]["status"] == "applied"
    assert rows[0]["submit_verified"] is True
    assert rows[0]["applied_page_verified"] is True
    assert rows[0]["recorded_by"] == "canonical_orphan_reconciliation"
    assert payload["request_ids"] == ["5170842"]


def test_missing_canonical_identity_refuses_ledger_recovery(tmp_path):
    candidate = {
        "request_id": "5170842",
        "bucket": "single",
        "title": "AIツール活用のWebサイト制作",
        "url": "https://coconala.com/requests/5170842",
        "pass_id": "1785278864-65816",
        "source_evidence": "/evidence/request-5170842.json",
    }
    try:
        MODULE.reconcile_orphans(
            [],
            candidates=[candidate],
            captured={"request_ids": []},
            recovery_id="recovery-1",
            observed_at=1785282000,
            evidence_path=tmp_path / "recovery.json",
        )
    except ValueError as error:
        assert str(error) == "canonical_application_missing:5170842"
    else:
        raise AssertionError("missing canonical application was accepted")
