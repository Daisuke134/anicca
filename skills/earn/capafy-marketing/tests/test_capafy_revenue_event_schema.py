import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "capafy-revenue-event.schema.json"


def order_event() -> dict:
    return {
        "schema_version": 1,
        "event_id": "capafy:order.received:2026-08-13:revision-abc123",
        "event_type": "order.received",
        "occurred_at": "2026-08-13T00:00:00Z",
        "recorded_at": "2026-08-13T12:00:00Z",
        "loop": "company",
        "entity": {"type": "order_batch", "id": "2026-08-13"},
        "correlation_id": None,
        "summary": "Reconciled Capafy orders.",
        "status": {"before": None, "after": "measured"},
        "money": {
            "currency": "USD",
            "gross_delta": "19.98",
            "pending_delta": "0.00",
            "realized_delta": "0.00",
            "mrr_delta": "0.00",
            "cost_delta": "0.00",
            "contribution_delta": "0.00",
        },
        "metrics": {"orders": 2, "paid_orders": 1},
        "public_evidence": {"urls": [], "labels": ["reconciled"]},
        "technical_evidence_ref": "capafy:order.received:2026-08-13:revision-abc123",
        "source": {
            "producer": "capafy_earn_reconcile",
            "source_id": "capafy-sales:2026-08-13",
            "source_digest": "sha256:" + "a" * 64,
        },
        "next": {"owner": "company", "retry_at": None},
    }


def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_schema_accepts_paid_order_event() -> None:
    assert list(validator().iter_errors(order_event())) == []


def test_schema_rejects_paid_orders_on_non_order_event() -> None:
    event = order_event() | {"event_type": "content.measured"}

    assert list(validator().iter_errors(event))


def test_schema_rejects_paid_orders_without_orders() -> None:
    event = order_event() | {"metrics": {"paid_orders": 1}}

    assert list(validator().iter_errors(event))
