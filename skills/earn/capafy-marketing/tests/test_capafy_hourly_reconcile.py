from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_hourly_reconcile.py"


def load_module():
    spec = importlib.util.spec_from_file_location("capafy_hourly_reconcile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def live_payloads() -> dict:
    return {
        "account": {"code": 0, "data": {"email": "owner@example.com"}},
        "inventory": {
            "code": 0,
            "data": {
                "list": [
                    {"agentId": "a1", "agentStatus": "online"},
                    {"agentId": "a2", "agentStatus": "draft"},
                    {"agentId": "a3", "agentStatus": "under_review"},
                    {"agentId": "a4", "agentStatus": "review_rejected"},
                ]
            },
        },
        "sales": {
            "code": 0,
            "data": {
                "data": [
                    {
                        "date": "2026-08-22",
                        "orders": 2,
                        "revenue": 19.98,
                        "netRevenue": 17.98,
                        "refundCount": 1,
                        "refundAmount": 2.00,
                    }
                ]
            },
        },
        "payout": {
            "code": 0,
            "data": {"balancePayout": 8, "totalPayout": 0, "balancePending": 3},
        },
        "refunds": {"code": 0, "data": {"list": [{"refundId": "r-1"}]}},
        "seller_sales": {"code": 0, "data": {"totalRevenue": 9.99, "data": [{"orders": 1, "refundAmount": 0}]}},
        "seller_ranking": {"code": 0, "data": {"agents": [{
            "agentId": "6839055303",
            "agentTitle": "Academic Humanizer — Human Voice, No AI Tells",
            "totalSalesAmount": 9.99,
            "previousSalesAmount": 0.0,
            "changePercent": 0.0,
            "skuCount": 1,
            "skus": [{"skuName": "Per Download", "skuType": "buyout", "salesAmount": 9.99,
                      "previousSalesAmount": 0.0, "changePercent": 0.0}],
        }]}},
        "statements": {"code": 0, "data": {"list": [{"settlementMonth": "2026-07", "endingSettlementBalance": 8, "payableAmount": 0}]}},
    }


def test_receipt_separates_money_and_keeps_unobservable_mrr_unknown() -> None:
    module = load_module()
    receipt = module.build_receipt(live_payloads(), "2026-08-22T10:00:00Z")

    assert receipt["verdict"] == "success"
    assert receipt["money"] == {
        "gross_usd": "9.99",
        "one_time_revenue_usd": "9.99",
        "pending_usd": "8.00",
        "realized_usd": "0.00",
        "refunds_usd": "0.00",
        "settled_mrr_usd": "0.00",
        "net_mrr_usd": "0.00",
        "statement_ending_balance_usd": "8.00",
        "statement_payable_usd": "0.00",
    }
    assert receipt["money_status"]["one_time_revenue_usd"] == "fresh_official_seller_console"
    assert receipt["money_status"]["settled_mrr_usd"] == "fresh_zero_lifetime_subscription_sales"
    assert receipt["seller_winner"] == {
        "agent_id": "6839055303",
        "name": "Academic Humanizer — Human Voice, No AI Tells",
        "sales_usd": "9.99",
        "sku_type": "buyout",
        "revenue_kind": "one_time",
        "source": "official_publisher_console",
    }
    assert receipt["refunds"]["tickets"] == 1
    assert receipt["sources"]["sales"]["freshness"] == "fresh"


def test_failed_source_is_unknown_not_zero_and_receipt_is_degraded() -> None:
    module = load_module()
    payloads = live_payloads()
    payloads["payout"] = {"_error": "HTTP 503"}
    payloads["sales"] = {"_error": "timeout"}

    receipt = module.build_receipt(payloads, "2026-08-22T10:00:00Z")

    assert receipt["verdict"] == "degraded"
    assert receipt["money"]["gross_usd"] is None
    assert receipt["money"]["pending_usd"] is None
    assert receipt["money"]["realized_usd"] is None
    assert receipt["money"]["settled_mrr_usd"] is None
    assert receipt["sources"]["sales"]["freshness"] == "unknown"
    assert receipt["sources"]["payout"]["freshness"] == "unknown"


def test_inventory_shape_is_observed_without_claiming_normalized_slots() -> None:
    module = load_module()
    payloads = live_payloads()
    payloads["inventory"] = {"code": 0, "data": {"unexpected": [1, 2, 3]}}

    receipt = module.build_receipt(payloads, "2026-08-22T10:00:00Z")

    assert receipt["inventory"]["status"] == "unknown_unrecognized_shape"
    assert receipt["inventory"]["occupied"] is None
    assert receipt["inventory"]["free"] is None
    assert receipt["sources"]["inventory"]["freshness"] == "fresh"
    assert receipt["verdict"] == "degraded"


def test_inventory_normalizes_five_slot_lifecycle() -> None:
    module = load_module()

    receipt = module.build_receipt(live_payloads(), "2026-08-22T10:00:00Z")

    assert receipt["inventory"] == {
        "status": "normalized",
        "observed_agents": 4,
        "listed": 1,
        "occupied": 2,
        "free": 3,
        "retry": 1,
        "blocked": 0,
    }


def test_cli_fixture_run_writes_atomic_receipt(tmp_path: Path) -> None:
    module = load_module()
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for name, payload in live_payloads().items():
        (fixture_dir / f"{name}.json").write_text(json.dumps(payload))
    output = tmp_path / "state" / "receipt.json"

    rc = module.main(
        ["--fixture-dir", str(fixture_dir), "--output", str(output), "--observed-at", "2026-08-22T10:00:00Z"]
    )

    assert rc == 0
    assert json.loads(output.read_text())["observed_at"] == "2026-08-22T10:00:00Z"
    assert not output.with_suffix(".json.tmp").exists()
