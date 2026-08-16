"""Experiment metric measurement: measurable metrics are measured, rates are never invented.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_metric_learning.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

ACCEPTED_AT = 1_786_000_000
WINDOW_DAYS = 14
ELIGIBLE_AT = ACCEPTED_AT + WINDOW_DAYS * 86400
SERVICE_ID = "4313386"


def analytics_file(tmp_path, samples):
    path = tmp_path / "analytics.jsonl"
    path.write_text("".join(
        json.dumps({"service_id": SERVICE_ID, "observed_at_epoch": epoch,
                    "metrics": {"purchases": {"status": status, "value": value}}}) + "\n"
        for epoch, value, status in samples
    ), encoding="utf-8")
    return path


def measure(metric, analytics_path, transcripts=Path("/nonexistent/reply-transcripts.jsonl")):
    return sd._measure_experiment_metric(
        metric, reply_transcripts=transcripts, analytics_path=analytics_path,
        service_id=SERVICE_ID, accepted_at=ACCEPTED_AT, window_days=WINDOW_DAYS,
    )


def test_official_purchases_are_measured_as_a_snapshot_delta(tmp_path):
    path = analytics_file(tmp_path, [
        (ACCEPTED_AT - 100, 2, "known"),
        (ELIGIBLE_AT - 100, 5, "known"),
    ])
    result = measure("purchases", path)
    assert result["status"] == "known"
    assert (result["baseline"], result["observed"]) == (2, 5)
    # Never presented as a window-aligned count, because the official figure rolls 30 days.
    assert result["measurement"] == "rolling_30d_snapshot_delta"
    assert result["measured_metric"] == "purchases"


def test_a_view_based_ratio_is_never_invented_and_falls_back_to_a_measurable_metric(tmp_path):
    path = analytics_file(tmp_path, [
        (ACCEPTED_AT - 100, 0, "known"),
        (ELIGIBLE_AT - 100, 1, "known"),
    ])
    result = measure("views_to_purchase", path)
    assert result["requested_metric"] == "views_to_purchase"
    assert result["requested_metric_status"] == "unknown"
    assert result["requested_metric_reason"] == "official_views_are_rolling_30d_not_window_aligned"
    assert result["measured_metric"] == "purchases" and result["status"] == "known"


def test_missing_or_unknown_official_evidence_stays_unknown(tmp_path):
    assert measure("purchases", tmp_path / "absent.jsonl")["status"] == "unknown"
    only_baseline = analytics_file(tmp_path, [(ACCEPTED_AT - 100, 2, "known")])
    result = measure("purchases", only_baseline)
    assert result["status"] == "unknown"
    assert result["reason"] == "no_official_purchases_snapshot_inside_window"
    unknown_value = analytics_file(tmp_path, [
        (ACCEPTED_AT - 100, 0, "unavailable"), (ELIGIBLE_AT - 100, 0, "unavailable"),
    ])
    assert measure("purchases", unknown_value)["status"] == "unknown"


def test_an_unsupported_metric_is_reported_rather_than_guessed(tmp_path):
    result = measure("net_revenue_per_view", tmp_path / "absent.jsonl")
    assert result["status"] == "unknown" and result["reason"] == "unsupported_success_metric"
    assert result["measured_metric"] is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
