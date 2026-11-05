from __future__ import annotations
import datetime as dt
import importlib.util
from pathlib import Path
import sys
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

def test_snapshot_retains_period_and_aggregate_metrics_without_private_sources(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module.reconcile, "_traffic_window", lambda *a, **k: {
        "status": "fresh", "window": {"start_utc": "start", "end_utc": "end"},
        "totals": {"views": 6, "paid_orders": 2, "trial_orders": 1, "sales_usd": "9.99"}})
    monkeypatch.setattr(module.reconcile, "_impressions_window", lambda *a, **k: {
        "status": "fresh", "by_source": [
            {"source_type": "internal", "source_name": "search", "exposure_count": 12},
            {"source_type": "campaign", "source_name": "private-name", "exposure_count": 3}]})
    snapshot = module.build_snapshot("token", dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc))
    window = snapshot["windows"]["last_7d"]
    assert window["views"] == 6
    assert window["sales_usd"] == "9.99"
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
