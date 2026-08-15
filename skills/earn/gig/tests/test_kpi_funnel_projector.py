from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
IDS = (
    "service_id", "service_version_hash", "opportunity_id", "application_id",
    "thread_id", "offer_id", "talkroom_id", "payment_receipt_id",
)
AS_OF = "2026-08-16T10:00:00+09:00"
HOUR = ("2026-08-16T09:00:00+09:00", "2026-08-16T10:00:00+09:00")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


projector = load("kpi_funnel_projector")
adapter = load("marketplace_kpi_adapter")


def ident(**values):
    return {key: values.get(key) for key in IDS}


def event(name: str, event_id: str, *, lane="apply", at="2026-08-16T09:10:00+09:00",
          identity=None, jpy=None):
    identity = identity or ident(opportunity_id="job-1", application_id="app-1")
    if lane == "storefront" and identity.get("service_id") is None:
        identity = ident(service_id="service-1", service_version_hash="b" * 64)
    reason = "unresolved acquisition" if lane == "unknown" else None
    return {
        "schema_version": 1, "record_kind": "event", "platform": "coconala",
        "acquisition_lane": lane, "observed_at": at,
        "source": {"collector": "test", "evidence_ref": "evidence://1",
                   "content_sha256": "a" * 64},
        "event_id": event_id, "event_name": name, "occurred_at": at,
        "identity": identity,
        "identity_status": "unknown" if lane == "unknown" else "known",
        "unknown_reason": reason,
        "amount": {
            "status": "known" if jpy is not None else "unknown",
            "net_jpy": jpy, "currency": "JPY" if jpy is not None else None,
            "unknown_reason": None if jpy is not None else "not a money event",
        },
    }


def snapshot(stage: str, value: int, snapshot_id: str, *, lane="storefront",
             window=HOUR, scope="lane_total", dimension=None, metric="stage_count"):
    return {
        "schema_version": 1, "record_kind": "metric_snapshot", "platform": "coconala",
        "acquisition_lane": lane, "aggregation_scope": scope,
        "lane_unknown_reason": "unresolved acquisition" if lane == "unknown" else None,
        "observed_at": window[1],
        "source": {"collector": "test", "evidence_ref": "evidence://snapshot",
                   "content_sha256": "c" * 64},
        "snapshot_id": snapshot_id, "metric_name": metric, "stage": stage,
        "window": {"start": window[0], "end": window[1],
                   "timezone": "Asia/Tokyo", "complete": True},
        "dimension": dimension or ident(),
        "value": {"status": "known", "value": value, "unknown_reason": None},
    }


def test_rebuilds_hour_day_and_seven_day_apply_events():
    records = [
        event("application_submitted", "application-1"),
        event("reply_received", "reply-1", at="2026-08-16T09:20:00+09:00",
              identity=ident(opportunity_id="job-1", application_id="app-1",
                             thread_id="thread-1")),
        event("estimate_sent", "estimate-1", at="2026-08-16T09:30:00+09:00",
              identity=ident(opportunity_id="job-1", application_id="app-1",
                             offer_id="offer-1")),
        event("order_confirmed", "order-1", at="2026-08-16T09:40:00+09:00",
              identity=ident(opportunity_id="job-1", application_id="app-1",
                             offer_id="offer-1", talkroom_id="room-1")),
        event("settled", "settled-1", at="2026-08-16T09:50:00+09:00", jpy=5000,
              identity=ident(opportunity_id="job-1", application_id="app-1",
                             talkroom_id="room-1", payment_receipt_id="receipt-1")),
    ]
    report = projector.project_records(records, as_of=AS_OF)
    hour = report["periods"]["hour"]["lanes"]["apply"]
    assert hour["stages"]["application"] == {"status": "known", "value": 1}
    assert hour["stages"]["reply"] == {"status": "known", "value": 1}
    assert hour["stages"]["estimate_order"] == {"status": "known", "value": 1}
    assert hour["stages"]["settled"] == {"status": "known", "value": 1}
    assert hour["net_jpy"] == {"status": "known", "value": 5000}
    assert report["periods"]["day"]["lanes"]["apply"]["net_jpy"]["value"] == 5000
    assert report["periods"]["seven_day"]["lanes"]["apply"]["net_jpy"]["value"] == 5000


def test_coconala_and_freelancer_use_one_adapter_projection_boundary():
    def envelope(platform: str):
        records = [
            event("application_submitted", f"{platform}:application"),
            event(
                "reply_received", f"{platform}:reply",
                identity=ident(opportunity_id="job-1", application_id="app-1",
                               thread_id="thread-1"),
            ),
        ]
        for record in records:
            record["platform"] = platform
        return {
            "schema_version": 1,
            "platform": platform,
            "official_readback": {
                "observed_at": "2026-08-16T09:30:00+09:00",
                "evidence_ref": f"official://{platform}/applications",
                "content_sha256": "d" * 64,
            },
            "records": records,
        }

    coconala = adapter.project_adapter_envelope(envelope("coconala"), as_of=AS_OF)
    freelancer = adapter.project_adapter_envelope(envelope("freelancer"), as_of=AS_OF)
    assert coconala["projection"]["periods"] == freelancer["projection"]["periods"]
    assert coconala["platform"] == "coconala"
    assert freelancer["platform"] == "freelancer"


def test_adapter_rejects_cross_platform_records():
    payload = {
        "schema_version": 1,
        "platform": "freelancer",
        "official_readback": {
            "observed_at": "2026-08-16T09:30:00+09:00",
            "evidence_ref": "official://freelancer/applications",
            "content_sha256": "d" * 64,
        },
        "records": [event("application_submitted", "coconala:application")],
    }
    with pytest.raises(adapter.AdapterBoundaryError, match="does not match"):
        adapter.project_adapter_envelope(payload, as_of=AS_OF)


def test_explicit_zero_is_known_but_absence_is_unknown_and_dropoff_is_first():
    records = [
        snapshot("impression", 10, "imp"),
        snapshot("view", 4, "view"),
        snapshot("inquiry", 1, "inquiry"),
        snapshot("qualified", 0, "qualified"),
    ]
    lane = projector.project_records(records, as_of=AS_OF)["periods"]["hour"]["lanes"][
        "storefront"
    ]
    assert lane["stages"]["qualified"] == {"status": "known", "value": 0}
    assert lane["stages"]["settled"] == {
        "status": "unknown", "value": None, "reason": "no complete evidence"
    }
    assert lane["conversions"][0]["rate"] == 0.4
    assert lane["first_dropoff"] == {
        "from": "impression", "to": "view", "lost": 6, "rate": 0.4
    }


def test_non_monotonic_window_does_not_invent_conversion():
    records = [snapshot("view", 5, "view"), snapshot("inquiry", 6, "inquiry")]
    lane = projector.project_records(records, as_of=AS_OF)["periods"]["hour"]["lanes"][
        "storefront"
    ]
    conversion = next(item for item in lane["conversions"] if item["from"] == "view")
    assert conversion["status"] == "unknown"
    assert conversion["reason"] == "non-monotonic window counts"


def test_unknown_money_is_preserved_in_all_total():
    records = [
        event("settled", "apply-paid", jpy=3000,
              identity=ident(opportunity_id="job-1", application_id="app-1",
                             talkroom_id="room-1", payment_receipt_id="receipt-1")),
        event("settled", "unknown-paid", lane="unknown", jpy=7000,
              identity=ident(talkroom_id="room-2", payment_receipt_id="receipt-2")),
    ]
    period = projector.project_records(records, as_of=AS_OF)["periods"]["hour"]
    assert period["unknown"] == {
        "settled_count": {"status": "known", "value": 1},
        "net_jpy": {"status": "known", "value": 7000},
    }
    assert period["lanes"]["storefront"]["net_jpy"]["status"] == "unknown"
    assert period["all"]["settled_count"]["status"] == "unknown"
    assert period["all"]["net_jpy"]["status"] == "unknown"
    assert period["conserved"] is None


def test_absent_money_evidence_is_unknown_not_zero():
    period = projector.project_records([], as_of=AS_OF)["periods"]["hour"]
    assert period["all"]["net_jpy"] == {
        "status": "unknown", "value": None, "reason": "no complete evidence"
    }
    assert period["unknown"]["settled_count"]["status"] == "unknown"
    assert period["conserved"] is None


def test_complete_money_snapshots_conserve_all_lanes():
    records = [
        snapshot("settled", 0, "store-count", lane="storefront"),
        snapshot("settled", 0, "store-net", lane="storefront", metric="net_jpy"),
        snapshot("settled", 1, "apply-count", lane="apply"),
        snapshot("settled", 3000, "apply-net", lane="apply", metric="net_jpy"),
        snapshot("settled", 1, "unknown-count", lane="unknown"),
        snapshot("settled", 7000, "unknown-net", lane="unknown", metric="net_jpy"),
    ]
    period = projector.project_records(records, as_of=AS_OF)["periods"]["hour"]
    assert period["all"]["settled_count"] == {"status": "known", "value": 2}
    assert period["all"]["net_jpy"] == {"status": "known", "value": 10000}
    assert period["conserved"] is True


def test_future_observation_is_not_visible_in_historical_rebuild():
    row = event("settled", "late-observation", at="2026-08-16T09:10:00+09:00", jpy=5000,
                identity=ident(opportunity_id="job-1", application_id="app-1",
                               talkroom_id="room-1", payment_receipt_id="receipt-1"))
    row["observed_at"] = "2026-08-16T10:01:00+09:00"
    period = projector.project_records([row], as_of=AS_OF)["periods"]["hour"]
    assert period["lanes"]["apply"]["stages"]["settled"]["status"] == "unknown"
    assert period["all"]["net_jpy"]["status"] == "unknown"


def test_event_cannot_be_observed_before_it_occurs():
    row = event("application_submitted", "application-1")
    row["observed_at"] = "2026-08-16T09:09:59+09:00"
    with pytest.raises(projector.ProjectionError, match="observed before occurrence"):
        projector.project_records([row], as_of=AS_OF)


def test_complete_snapshot_cannot_be_observed_before_window_ends():
    row = snapshot("view", 1, "view")
    row["observed_at"] = "2026-08-16T09:59:59+09:00"
    with pytest.raises(projector.ProjectionError, match="complete snapshot"):
        projector.project_records([row], as_of=AS_OF)


def test_duplicate_record_id_conflict_fails_but_exact_duplicate_collapses():
    original = event("application_submitted", "same-id")
    assert projector.project_records([original, dict(original)], as_of=AS_OF)["input"][
        "unique_records"
    ] == 1
    changed = event("reply_received", "same-id",
                    identity=ident(opportunity_id="job-1", application_id="app-1",
                                   thread_id="thread-1"))
    with pytest.raises(projector.ProjectionError, match="conflicting record id"):
        projector.project_records([original, changed], as_of=AS_OF)


def test_duplicate_payment_receipt_under_different_events_fails_closed():
    first = event("settled", "settled-1", jpy=3000,
                  identity=ident(opportunity_id="job-1", application_id="app-1",
                                 talkroom_id="room-1", payment_receipt_id="receipt-1"))
    second = event("settled", "settled-2", lane="unknown", jpy=3000,
                   identity=ident(talkroom_id="room-1", payment_receipt_id="receipt-1"))
    with pytest.raises(projector.ProjectionError, match="duplicate payment receipt"):
        projector.project_records([first, second], as_of=AS_OF)


def test_estimate_order_requires_exact_offer_and_snapshot_sources_do_not_mix():
    missing_offer = event("estimate_sent", "estimate-1")
    with pytest.raises(projector.ProjectionError, match="offer_id"):
        projector.project_records([missing_offer], as_of=AS_OF)

    total = snapshot("view", 4, "total")
    entity = snapshot(
        "view", 2, "entity", scope="entity",
        dimension=ident(service_id="service-1", service_version_hash="b" * 64),
    )
    with pytest.raises(projector.ProjectionError, match="mixed snapshot scopes"):
        projector.project_records([total, entity], as_of=AS_OF)


def test_net_snapshot_uses_settled_stage_only():
    row = snapshot("refund", -1000, "refund-net", metric="net_jpy")
    with pytest.raises(projector.ProjectionError, match="net_jpy snapshot"):
        projector.project_records([row], as_of=AS_OF)


def test_projection_is_order_independent_and_records_freshness():
    records = [snapshot("impression", 10, "imp"), snapshot("view", 4, "view")]
    first = projector.project_records(records, as_of=AS_OF)
    second = projector.project_records(list(reversed(records)), as_of=AS_OF)
    assert first == second
    freshness = first["periods"]["hour"]["lanes"]["storefront"]["freshness"]
    assert freshness == {"status": "known", "observed_at": HOUR[1], "lag_seconds": 0}


def test_state_entrypoint_reuses_exact_settlement_reconciliation(tmp_path: Path):
    rows = {
        "earnings.jsonl": [{
            "ts": "2026/08/16 09:30", "status": "検収完了",
            "talkroom_id": "room-1", "requestId": "room-1",
            "idem_key": "receipt-1", "jpy": 5000, "evidence": "revenue://1",
        }],
        "identity_chain.jsonl": [
            {"talkroom_id": "room-1", "request_id": "job-1"}
        ],
        "applied.jsonl": [
            {"status": "applied", "requestId": "job-1", "pass_id": "pass-1",
             "submit_verified": True, "applied_page_verified": True,
             "ts": "2026-08-16T09:00:00+09:00"}
        ],
    }
    for name, values in rows.items():
        (tmp_path / name).write_text(
            "".join(json.dumps(row) + "\n" for row in values), encoding="utf-8"
        )
    hour = projector.project_state(tmp_path, as_of=AS_OF)["periods"]["hour"]
    assert hour["lanes"]["apply"]["stages"]["settled"] == {
        "status": "known", "value": 1
    }
    assert hour["lanes"]["apply"]["net_jpy"] == {"status": "known", "value": 5000}
    assert hour["all"]["net_jpy"]["status"] == "unknown"


def test_kpi_jsonl_rejects_nonstandard_json_constant(tmp_path: Path):
    path = tmp_path / "kpi.jsonl"
    path.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(projector.ProjectionError, match="malformed KPI JSONL"):
        projector._jsonl(path)


def test_invalid_as_of_has_stable_error():
    with pytest.raises(projector.ProjectionError, match="invalid timestamp"):
        projector.project_records([], as_of="not-a-time")
