from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = load("kpi_readback_audit")


def storefront(*sales: tuple[str, int]) -> dict:
    services = [
        {"service_id": service_id, "state": "公開中", "price_jpy": 5000,
         "sales_count": count}
        for service_id, count in sales
    ]
    canonical = json.dumps(
        services, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "observed_at": "2026-08-15T15:10:51+00:00",
        "services": services,
        "live_listings_count": len(services),
        "service_count": len(services),
        "content_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def apply_readback(*request_ids: str) -> dict:
    return {
        "source": "code_owned_cdp_readback",
        "observed": True,
        "not_found": False,
        "request_ids": list(request_ids),
        "applied_page_absent_request_ids": [],
        "urls": ["https://coconala.com/mypage/job_matching/applied/offers"],
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed_at": 1786806900,
        "pass_id": "readback-pass-1",
        "pages_walked": 1,
        "cards_seen": max(1, len(request_ids)),
        "has_next_page": True,
        "expected_request_ids": list(request_ids) or ["501"],
        "missing_count": 0,
        "unresolved_count": 0,
    }


def application(request_id: str, *, verified: bool = True) -> dict:
    return {
        "status": "applied" if verified else "reconcile_pending",
        "requestId": request_id,
        "pass_id": "pass-1",
        "submit_verified": verified,
        "applied_page_verified": verified,
        "ts": "2026-08-15T15:00:00+00:00",
    }


def settlement(lane: str, receipt: str) -> dict:
    return {
        "record_kind": "event", "event_name": "settled",
        "acquisition_lane": lane,
        "identity": {"payment_receipt_id": receipt},
    }


def build(sf: dict, app: dict, applications: list[dict], events: list[dict]) -> dict:
    return audit.audit_rows(
        sf, app, applications, events,
        observed_at="2026-08-16T00:20:00+09:00",
        input_hashes={
            "storefront_readback": "a" * 64,
            "storefront_contract": "e" * 64,
            "apply_readback": "b" * 64,
            "applied.jsonl": "c" * 64,
            "settlement_projection": "d" * 64,
        }, expected_storefront_ids={row["service_id"] for row in sf["services"]},
    )


def test_exact_official_sample_and_storefront_sales_match_local_truth():
    report = build(
        storefront(("100", 1), ("200", 0)),
        apply_readback("501", "502"),
        [application("501"), application("502"), application("503")],
        [settlement("storefront", "receipt-1"), settlement("apply", "receipt-2")],
    )

    assert report["status"] == "match"
    assert report["checks"]["storefront_sales"] == {
        "status": "match", "official_count": 1, "local_count": 1, "delta": 0,
    }
    assert report["checks"]["apply_sample"]["official_sample_count"] == 2
    assert report["checks"]["apply_sample"]["matched_count"] == 2
    assert report["checks"]["apply_sample"]["missing_local_ids"] == []
    assert report["checks"]["apply_sample"]["coverage"] == "official_sample_only"


def test_storefront_count_difference_is_an_exact_mismatch():
    report = build(
        storefront(("100", 2)), apply_readback("501"), [application("501")],
        [settlement("storefront", "receipt-1")],
    )
    assert report["status"] == "mismatch"
    assert report["checks"]["storefront_sales"]["delta"] == 1


def test_official_apply_id_requires_a_locally_verified_application():
    report = build(
        storefront(("100", 0)), apply_readback("501"),
        [application("501", verified=False)], [],
    )
    assert report["status"] == "mismatch"
    assert report["checks"]["apply_sample"]["missing_local_ids"] == ["501"]


def test_local_ids_absent_from_partial_official_sample_are_not_mismatches():
    report = build(
        storefront(("100", 0)), apply_readback("501"),
        [application("501"), application("502")], [],
    )
    assert report["status"] == "match"
    assert "502" not in report["checks"]["apply_sample"]["missing_local_ids"]


@pytest.mark.parametrize("change, message", [
    ({"content_sha256": "0" * 64}, "storefront content hash mismatch"),
    ({"service_count": 9}, "storefront service count mismatch"),
])
def test_storefront_contract_corruption_fails_unreadable(change: dict, message: str):
    readback = storefront(("100", 0))
    readback.update(change)
    with pytest.raises(audit.AuditError, match=message):
        build(readback, apply_readback("501"), [application("501")], [])


def test_unknown_storefront_sales_count_never_becomes_zero():
    readback = storefront(("100", 0))
    readback["services"][0]["sales_count"] = None
    canonical = json.dumps(
        readback["services"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    readback["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    with pytest.raises(audit.AuditError, match="storefront sales count unavailable"):
        build(readback, apply_readback("501"), [application("501")], [])


def test_unobserved_apply_page_never_passes():
    readback = apply_readback("501")
    readback["observed"] = False
    with pytest.raises(audit.AuditError, match="apply readback was not observed"):
        build(storefront(("100", 0)), readback, [application("501")], [])


def test_stale_or_incomplete_official_evidence_never_matches():
    old_storefront = storefront(("100", 0))
    old_storefront["observed_at"] = "2020-01-01T00:00:00+00:00"
    with pytest.raises(audit.AuditError, match="storefront readback is stale"):
        build(old_storefront, apply_readback("501"), [application("501")], [])

    unresolved = apply_readback("501")
    unresolved["applied_page_absent_request_ids"] = ["501"]
    with pytest.raises(audit.AuditError, match="unresolved identities"):
        build(storefront(("100", 0)), unresolved, [application("501")], [])


def test_local_jsonl_rejects_nonstandard_json_constants(tmp_path: Path):
    path = tmp_path / "applied.jsonl"
    path.write_text('{"status":"applied","value":NaN}\n')
    with pytest.raises(audit.AuditError, match="unreadable applied.jsonl"):
        audit._read_jsonl(path)


def test_durable_receipt_is_idempotent_and_conflicts_fail(tmp_path: Path):
    report = build(
        storefront(("100", 0)), apply_readback("501"), [application("501")], []
    )
    ledger = tmp_path / "kpi-readback-audit.jsonl"
    assert audit.append_receipt(ledger, report) is True
    assert audit.append_receipt(ledger, report) is False
    assert len(ledger.read_text().splitlines()) == 1

    later_same_inputs = dict(report)
    later_same_inputs["observed_at"] = "2026-08-16T01:20:00+09:00"
    assert audit.append_receipt(ledger, later_same_inputs) is False
    assert len(ledger.read_text().splitlines()) == 1

    conflict = dict(report)
    conflict["status"] = "mismatch"
    with pytest.raises(audit.AuditError, match="conflicting audit receipt"):
        audit.append_receipt(ledger, conflict)
