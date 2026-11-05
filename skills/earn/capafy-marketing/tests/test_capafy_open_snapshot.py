from __future__ import annotations
import datetime as dt
import importlib.util
from pathlib import Path
import sys
import datetime as dt
import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_open_snapshot.py"
sys.path.insert(0, str(SCRIPT.parent))

def load_module():
    spec = importlib.util.spec_from_file_location("capafy_open_snapshot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def test_hosted_refresh_uses_encrypted_runner_token_without_invoking_op(monkeypatch):
    module = load_module()
    monkeypatch.setenv("CAPAFY_WEB_TOKEN", "hosted-token")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("local vault lookup in hosted run"))
    assert module.read_token() == "hosted-token"

def test_traffic_rows_keep_page_and_detail_views_separate():
    module = load_module()
    rows = module.reconcile._traffic_merge([{
        "sourceType": "internal", "sourceName": "search",
        "pageViewCount": 3, "detailViewCount": 4, "uniqueVisitorCount": 2,
    }], [])
    assert rows[0]["page_views"] == 3
    assert rows[0]["detail_views"] == 4
    assert rows[0]["views"] == 7

def test_snapshot_retains_period_and_aggregate_metrics_without_private_sources(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module.reconcile, "_traffic_window", lambda *a, **k: {
        "status": "fresh", "window": {"start_utc": "start", "end_utc": "end"},
        "totals": {"views": 6, "page_views": 4, "detail_views": 2,
                   "unique_visitors": 5, "paid_orders": 2, "trial_orders": 1, "sales_usd": "9.99"}})
    monkeypatch.setattr(module.reconcile, "_impressions_window", lambda *a, **k: {
        "status": "fresh", "by_source": [
            {"source_type": "internal", "source_name": "search", "exposure_count": 12},
            {"source_type": "campaign", "source_name": "private-name", "exposure_count": 3}]})
    def trend(path, token, body):
        start = dt.date.fromisoformat(body["startDate"])
        end = dt.date.fromisoformat(body["endDate"])
        dates = [(start + dt.timedelta(days=n)).isoformat() for n in range((end-start).days+1)]
        rows = ([{"date": date, "revenue": "9.99" if n == 0 else "0.00",
                  "refundAmount": "0.00", "refundCount": 0, "orders": 2 if n == 0 else -1 if n == 3 else 0}
                 for n, date in enumerate(dates)] if path == "/app/sales/clickhouse/trend" else
                [{"date": date, "salesVolume": 5 if n == 0 else -1 if n == 3 else 0,
                  "freeTrialCount": 1 if n == 0 else 0} for n, date in enumerate(dates)])
        if path == "/app/sales/clickhouse/trend":
            data = {**body, "totalRevenue": "9.99", "data": rows}
        else:
            data = {**body, "totalSalesVolume": 4, "totalFreeTrialCount": 1, "data": rows}
        return {"code": 0, "data": data}
    monkeypatch.setattr(module.reconcile, "_post", trend)
    snapshot = module.build_snapshot("token", dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc))
    window = snapshot["windows"]["last_7d"]
    assert window["views"] == 6
    assert window["page_views"] == 4
    assert window["detail_views"] == 2
    assert window["attributed_unique_visitors"] == 5
    assert window["sales_usd"] == "9.99"
    assert window["platform_revenue_usd"] == "9.99"
    assert window["unit_sales"] == 4
    assert window["trial_units"] == 1
    assert len(window["daily"]) == 7
    assert window["daily"][3]["units"] == -1
    assert window["daily"][3]["orders"] == -1
    assert window["impressions"] == [{"name": "search", "count": 12}]
    assert window["omitted_impression_sources"] == 1
    assert snapshot["observed_at"] == "2026-11-05T00:00:00+00:00"

def test_failed_provider_read_does_not_overwrite_existing_output(monkeypatch, tmp_path):
    module = load_module()
    output = tmp_path / "capafy.json"
    output.write_text("prior")
    monkeypatch.setattr(module, "read_token", lambda: "token")
    monkeypatch.setattr(module.reconcile, "_traffic_window", lambda *a, **k: {"status": "unknown_source_error"})
    monkeypatch.setattr(module.reconcile, "_impressions_window", lambda *a, **k: {"status": "unknown_source_error"})
    with pytest.raises(RuntimeError):
        module.write_snapshot(output)
    assert output.read_text() == "prior"
