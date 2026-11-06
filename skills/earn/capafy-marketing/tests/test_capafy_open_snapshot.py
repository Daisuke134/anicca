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

def _snapshot_response(path, body, *, invalid_overview=None):
    start = dt.date.fromisoformat(body["startDate"])
    end = dt.date.fromisoformat(body["endDate"])
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
    if path.startswith("/app/developer/overview/v2/"):
        endpoint = path.rsplit("/", 1)[-1]
        rows = []
        for i, date in enumerate(dates):
            if endpoint == "exposure":
                row = {"totalCount": 10+i, "uniqueDeviceCount": 5+i}
            elif endpoint == "detail-view":
                row = {"totalCount": 4+i, "uniqueDeviceCount": 2+i}
            elif endpoint == "conversion":
                row = {"conversionRate": -0.06 if i == 3 else 0.03,
                       "orderCount": -1 if i == 3 else 1 if i == 0 else 0,
                       "userIdExposureCount": 5+i}
            else:
                row = {"newUserCount": 1 if i == 0 else 0}
            rows.append({"bucketDate": date, **row})
        common = {"startDate": body["startDate"], "endDate": body["endDate"],
                  "granularity": body["granularity"], "data": rows}
        flags = {"exposure": True, "detail-view": False, "conversion": True, "new-users": False}
        if endpoint in {"exposure", "detail-view"}:
            metrics = {"totalCount": 1234 if endpoint == "exposure" else 678,
                       "totalUniqueDeviceCount": 50 if endpoint == "exposure" else 40,
                       "totalCountChangePercent": -36.1 if endpoint == "exposure" else -42.9,
                       "uniqueDeviceChangePercent": -20.2 if endpoint == "exposure" else -30.1}
        elif endpoint == "conversion":
            metrics = {"totalConversionRate": 0.04, "conversionRateChange": 0.02,
                       "totalOrderCount": 5, "totalUserIdExposureCount": 50}
        else:
            metrics = {"totalNewUserCount": 4, "newUserChangePercent": 0.0}
        if endpoint == invalid_overview:
            flags[endpoint] = "true"
        return {"code": 0, "data": {**common, **metrics, "containsUnknownCountry": flags[endpoint]}}
    if path == "/app/sales/clickhouse/trend":
        rows = [{"date": date, "revenue": "9.99" if i == 0 else "0.00",
                 "refundAmount": "0.00", "refundCount": 0,
                 "orders": 2 if i == 0 else -1 if i == 3 else 0}
                for i, date in enumerate(dates)]
        return {"code": 0, "data": {**body, "totalRevenue": "9.99", "data": rows}}
    if path == "/app/unit-sales/clickhouse/trend":
        rows = [{"date": date, "salesVolume": 5 if i == 0 else -1 if i == 3 else 0,
                 "freeTrialCount": 1 if i == 0 else 0}
                for i, date in enumerate(dates)]
        return {"code": 0, "data": {**body, "totalSalesVolume": 4,
                                      "totalFreeTrialCount": 1, "data": rows}}
    raise AssertionError(f"unexpected Capafy endpoint: {path}")

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
    calls = []
    def trend(path, token, body):
        calls.append((path, body))
        return _snapshot_response(path, body)
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
    overview = snapshot["overview"]
    assert overview["source"] == "Capafy Developer Overview API"
    assert overview["observed_at"] == snapshot["observed_at"]
    seven = overview["windows"]["last_7d"]
    assert seven["start_date"] == "2026-10-30"
    assert seven["end_date"] == "2026-11-05"
    assert seven["exposure"] == {
        "total_count": 1234, "total_unique_device_count": 50,
        "total_count_change_percent": -36.1, "unique_device_change_percent": -20.2,
        "contains_unknown_country": True,
    }
    assert seven["detail_views"]["contains_unknown_country"] is False
    assert seven["conversion"]["total_conversion_rate"] == 0.04
    assert seven["conversion"]["conversion_rate_change"] == 0.02
    assert seven["conversion"]["contains_unknown_country"] is True
    assert seven["new_users"]["total_new_user_count"] == 4
    assert seven["new_users"]["contains_unknown_country"] is False
    assert len(seven["daily"]) == 7
    assert seven["daily"][3]["conversion_rate"] == -0.06
    assert seven["daily"][3]["order_count"] == -1
    assert len(overview["windows"]["last_30d"]["daily"]) == 30
    overview_calls = [(path, body) for path, body in calls if "/developer/overview/v2/" in path]
    assert len(overview_calls) == 8
    assert {path.rsplit("/", 1)[-1] for path, _ in overview_calls} == {
        "exposure", "detail-view", "conversion", "new-users",
    }
    assert all(body["granularity"] == "daily" for _, body in overview_calls)

def test_invalid_overview_country_flag_does_not_overwrite_existing_output(monkeypatch, tmp_path):
    module = load_module()
    output = tmp_path / "capafy.json"
    output.write_text("prior")
    monkeypatch.setattr(module, "read_token", lambda: "token")
    monkeypatch.setattr(module.reconcile, "_traffic_window", lambda *a, **k: {
        "status": "fresh", "window": {"start_utc": "start", "end_utc": "end"},
        "totals": {"views": 0, "page_views": 0, "detail_views": 0,
                   "unique_visitors": 0, "paid_orders": 0, "trial_orders": 0, "sales_usd": "0.00"}})
    monkeypatch.setattr(module.reconcile, "_impressions_window", lambda *a, **k: {
        "status": "fresh", "by_source": []})
    monkeypatch.setattr(module.reconcile, "_post", lambda path, token, body:
                       _snapshot_response(path, body, invalid_overview="exposure"))
    with pytest.raises(RuntimeError, match="Capafy Developer Overview malformed"):
        module.write_snapshot(output)
    assert output.read_text() == "prior"

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
