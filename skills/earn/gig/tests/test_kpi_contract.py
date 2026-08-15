"""Behavioral tests for the Storefront/Apply KPI record contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import jsonschema
import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "kpi-record.schema.json"
SCRIPT = ROOT / "scripts" / "kpi_contract.py"
MAX = 9007199254740991
IDS = (
    "service_id", "service_version_hash", "opportunity_id", "application_id",
    "thread_id", "offer_id", "talkroom_id", "payment_receipt_id",
)


def ident(**values: str | None) -> dict[str, str | None]:
    return {key: values.get(key) for key in IDS}


def source(**values: str) -> dict[str, str]:
    return {
        "collector": values.get("collector", "test-collector"),
        "evidence_ref": values.get("evidence_ref", "https://example.test/evidence/1"),
        "content_sha256": values.get("content_sha256", "a" * 64),
    }


def amount(status: str = "known", net: int | None = 10000, reason: str | None = None):
    return {
        "status": status,
        "net_jpy": net if status == "known" else None,
        "currency": "JPY" if status == "known" else None,
        "unknown_reason": reason if status == "unknown" else None,
    }


def event(*, lane="storefront", name="settled", identity=None, identity_status="known",
          reason=None, money=None, **extra):
    identity = identity or ident(
        service_id="service-1", service_version_hash="b" * 64,
        talkroom_id="talkroom-1", payment_receipt_id="payment-1",
    )
    return {
        "schema_version": 1, "record_kind": "event", "platform": "coconala",
        "acquisition_lane": lane, "observed_at": "2026-08-15T10:00:00+09:00",
        "source": source(), "event_id": "event-1", "event_name": name,
        "occurred_at": "2026-08-15T09:59:00+09:00", "identity": identity,
        "identity_status": identity_status, "unknown_reason": reason,
        "amount": money or amount(), **extra,
    }


def snapshot(*, lane="storefront", scope="entity", stage="inquiry", dimension=None,
             value=None, lane_reason=None, **extra):
    dimension = dimension or ident(service_id="service-1", service_version_hash="b" * 64)
    return {
        "schema_version": 1, "record_kind": "metric_snapshot", "platform": "coconala",
        "acquisition_lane": lane, "aggregation_scope": scope,
        "lane_unknown_reason": lane_reason, "observed_at": "2026-08-15T10:00:00+09:00",
        "source": source(), "snapshot_id": "snapshot-1", "metric_name": "stage_count",
        "stage": stage,
        "window": {"start": "2026-08-15T09:00:00+09:00",
                    "end": "2026-08-15T10:00:00+09:00",
                    "timezone": "Asia/Tokyo", "complete": True},
        "dimension": dimension,
        "value": value or {"status": "known", "value": 3, "unknown_reason": None},
        **extra,
    }


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@lru_cache(maxsize=1)
def runtime_validator():
    spec = importlib.util.spec_from_file_location("kpi_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_kpi_record


def put(record, *path, value):
    result = copy.deepcopy(record)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return result


def without(record, *path):
    result = copy.deepcopy(record)
    target = result
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return result


def valid(validator, record):
    validator.validate(record)
    runtime_validator()(record)


def invalid(validator, record):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)
    with pytest.raises(ValueError):
        runtime_validator()(record)


@pytest.mark.parametrize("record", [
    event(),
    event(lane="apply", name="application_submitted",
          identity=ident(opportunity_id="opportunity-1", application_id="application-1"),
          money=amount("not_applicable", None)),
    snapshot(lane="apply", stage="eligible_opportunity",
             dimension=ident(opportunity_id="opportunity-1")),
    snapshot(lane="apply", stage="application",
             dimension=ident(opportunity_id="opportunity-1", application_id="application-1")),
    snapshot(lane="apply", scope="lane_total", stage="application", dimension=ident()),
    event(lane="unknown", name="inquiry_received", identity=ident(thread_id="thread-1"),
          identity_status="unknown", reason="acquisition lane unavailable",
          money=amount("not_applicable", None)),
    snapshot(lane="unknown", dimension=ident(thread_id="thread-1"),
             lane_reason="acquisition lane unavailable"),
    event(name="refund", money=amount(net=-500)),
], ids=["storefront-settled", "apply-event", "apply-eligible", "apply-later",
       "lane-total", "unknown-event", "unknown-snapshot", "refund"])
def test_valid_records(validator, record):
    valid(validator, record)


def test_schema_is_checked_and_format_is_rejected(validator):
    invalid(validator, put(event(), "observed_at", value="15 August 2026"))


@pytest.mark.parametrize("record", [
    event(lane="unknown", name="inquiry_received", identity=ident(),
          identity_status="unknown", money=amount("not_applicable", None)),
    snapshot(value={"status": "unknown", "value": 0, "unknown_reason": "not exposed"}),
    put(event(), "record_kind", value="metric_snapshot"),
    put(event(), "record_kind", value=None),
    without(event(), "record_kind"),
    put(event(name="application_submitted", money=amount("not_applicable", None)),
        "buyer_title", value="untrusted join"),
    ], ids=["unknown-lane-missing-reason", "unknown-not-zero", "wrong-record-kind",
       "record-kind-null", "record-kind-missing", "extra-join-field"])
def test_closed_or_unknown_records_are_rejected(validator, record):
    invalid(validator, record)


@pytest.mark.parametrize("record", [
    event(identity=ident(service_id="service-1", service_version_hash=None)),
    event(lane="apply", name="application_submitted",
          identity=ident(opportunity_id="opportunity-1", application_id=None),
          money=amount("not_applicable", None)),
    snapshot(lane="apply", stage="eligible_opportunity", dimension=ident()),
    snapshot(lane="apply", stage="eligible_opportunity",
             dimension=ident(opportunity_id="opportunity-1", application_id="application-1")),
    snapshot(lane="apply", stage="application",
             dimension=ident(opportunity_id="opportunity-1")),
    snapshot(dimension=ident(service_id="service-1", service_version_hash=None)),
    snapshot(lane="unknown", dimension=ident(), lane_reason="lane unavailable"),
    snapshot(scope="lane_total", dimension=ident(service_id="service-1", service_version_hash="b" * 64)),
], ids=["storefront-version", "apply-application", "apply-eligible-opportunity",
       "apply-eligible-no-application", "apply-later-application", "snapshot-service-version",
       "unknown-entity-all-null", "lane-total-representative-id"])
def test_identity_scope_requirements(validator, record):
    invalid(validator, record)


@pytest.mark.parametrize("record", [
    event(name="application_submitted", money=amount("not_applicable", None)),
    event(lane="apply", name="inquiry_received",
          identity=ident(opportunity_id="opportunity-1", application_id="application-1"),
          money=amount("not_applicable", None)),
    snapshot(stage="application"),
    snapshot(lane="apply", stage="view"),
    snapshot(scope="lane_total", stage="application", dimension=ident()),
], ids=["storefront-application", "apply-inquiry", "storefront-application-stage",
       "apply-view-stage", "storefront-lane-total-stage"])
def test_acquisition_lanes_do_not_cross_stages(validator, record):
    invalid(validator, record)


@pytest.mark.parametrize("record", [
    event(identity=ident(service_id="service-1", service_version_hash="b" * 64,
                         talkroom_id="talkroom-1", payment_receipt_id=None)),
    event(money=amount("unknown", None, "receipt unavailable")),
    event(money=amount(net=0)),
    event(name="refund", money=amount(net=1)),
], ids=["settled-payment-id", "settled-known-amount", "settled-positive", "refund-sign"])
def test_settlement_identity_and_sign_requirements(validator, record):
    invalid(validator, record)


@pytest.mark.parametrize("record", [
    event(money=amount(net=MAX)), event(name="refund", money=amount(net=-MAX)),
    snapshot(value={"status": "known", "value": MAX, "unknown_reason": None}),
    put(snapshot(metric_name="net_jpy", stage="settled",
                 value={"status": "known", "value": -MAX, "unknown_reason": None}),
        "value", value={"status": "known", "value": MAX, "unknown_reason": None}),
], ids=["settled-max", "refund-min", "stage-count-max", "net-max"])
def test_safe_integer_edges_are_valid(validator, record):
    valid(validator, record)


@pytest.mark.parametrize("record", [
    event(money=amount(net=MAX + 1)), event(name="refund", money=amount(net=-MAX - 1)),
    snapshot(value={"status": "known", "value": MAX + 1, "unknown_reason": None}),
    snapshot(metric_name="net_jpy", stage="settled",
             value={"status": "known", "value": -MAX - 1, "unknown_reason": None}),
    snapshot(value={"status": "known", "value": True, "unknown_reason": None}),
    snapshot(metric_name="net_jpy", stage="settled",
             value={"status": "known", "value": True, "unknown_reason": None}),
], ids=["amount-high", "refund-low", "stage-count-high", "net-low", "stage-bool", "net-bool"])
def test_safe_integer_bounds_are_rejected(validator, record):
    invalid(validator, record)


@pytest.mark.parametrize("record", [
    put(event(), "event_id", value="   "),
    put(event(), "source", "evidence_ref", value="   "),
    put(event(), "event_id", value="event-1\n"),
    put(event(), "identity", "service_id", value="service-1\x00"),
    put(event(), "source", "collector", value="collector\x00"),
    put(event(), "source", "content_sha256", value="a" * 64 + "\n"),
    put(event(), "platform", value="coconala\n"),
    put(event(), "observed_at", value="2026-08-15T10:00:00+09:00\n"),
    put(event(), "identity", "service_version_hash", value="b" * 64 + "\n"),
    event(lane="unknown", name="inquiry_received", identity=ident(), identity_status="unknown",
          reason="reason\n", money=amount("not_applicable", None)),
], ids=["blank-id", "blank-evidence", "id-newline", "identity-nul", "collector-nul",
       "sha-newline", "platform-newline", "timestamp-newline", "version-newline", "reason-newline"])
def test_strict_text_and_hash_boundaries(validator, record):
    invalid(validator, record)


def test_runtime_rejects_invalid_calendar_and_reversed_window(validator):
    calendar = put(event(), "occurred_at", value="2026-02-30T10:00:00+09:00")
    validator.validate(calendar)  # structural pattern allows runtime calendar check
    with pytest.raises(ValueError):
        runtime_validator()(calendar)
    reversed_window = put(snapshot(), "window", value={
        "start": "2026-08-15T10:00:00+09:00", "end": "2026-08-15T09:00:00+09:00",
        "timezone": "Asia/Tokyo", "complete": True,
    })
    validator.validate(reversed_window)
    with pytest.raises(ValueError):
        runtime_validator()(reversed_window)
