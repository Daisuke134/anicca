"""Tests for data models."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    AlertCondition,
    AppStoreMetrics,
    DailyMetrics,
    DataQuality,
    DayOverDay,
    MixpanelMetrics,
    RevenueCatMetrics,
)


class TestDayOverDay:
    def test_positive_diff(self):
        dod = DayOverDay(current=150.0, previous=100.0)
        assert dod.diff == 50.0
        assert dod.diff_str == "+50"

    def test_negative_diff(self):
        dod = DayOverDay(current=80.0, previous=100.0)
        assert dod.diff == -20.0
        assert dod.diff_str == "-20"

    def test_zero_diff(self):
        dod = DayOverDay(current=100.0, previous=100.0)
        assert dod.diff == 0.0
        assert dod.diff_str == "0"

    def test_decimal_diff(self):
        dod = DayOverDay(current=9.99, previous=0.0)
        assert dod.diff_str == "+9.99"


class TestAlertCondition:
    def test_triggered_when_below_threshold(self):
        alert = AlertCondition(
            metric_name="CVR", current_value=1.8, threshold=3.0, unit="%"
        )
        assert alert.is_triggered is True
        assert "1.8%" in alert.message
        assert "3.0%" in alert.message

    def test_not_triggered_when_above_threshold(self):
        alert = AlertCondition(
            metric_name="CVR", current_value=4.0, threshold=3.0, unit="%"
        )
        assert alert.is_triggered is False

    def test_not_triggered_when_equal(self):
        alert = AlertCondition(
            metric_name="CVR", current_value=3.0, threshold=3.0, unit="%"
        )
        assert alert.is_triggered is False


class TestDailyMetrics:
    def test_to_json_with_all_data(self):
        metrics = DailyMetrics(
            date="2026-01-28",
            app_store=AppStoreMetrics(
                total_downloads_7d=12,
                downloads_by_country=(("US", 5), ("JP", 4), ("EU", 3)),
                impressions=900,
                page_views=13,
                cvr_page_to_download=1.8,
            ),
            revenuecat=RevenueCatMetrics(
                mrr=149.85,
                active_subscriptions=15,
                active_trials=3,
                trial_to_paid_count=1,
                trial_expired_count=2,
                monthly_churn_rate=6.7,
            ),
            mixpanel=MixpanelMetrics(
                onboarding_started=100,
                onboarding_paywall_viewed=30,
                rc_trial_started_event=2,
            ),
            data_quality=DataQuality(asc="ok", rc="ok", mp="ok"),
        )
        data = json.loads(metrics.to_json())
        assert data["date"] == "2026-01-28"
        assert data["app_store"]["total_downloads_7d"] == 12
        assert data["revenuecat"]["mrr"] == 149.85
        assert data["mixpanel"]["rc_trial_started_event"] == 2
        assert data["mixpanel"]["onboarding_started"] == 100
        assert data["data_quality"]["mp"] == "ok"

    def test_to_json_with_partial_data(self):
        metrics = DailyMetrics(
            date="2026-01-28",
            app_store=None,
            revenuecat=RevenueCatMetrics(mrr=50.0),
            mixpanel=None,
            data_quality=DataQuality(asc="missing", rc="ok", mp="missing"),
            errors=("App Store Connect API: 401 Unauthorized",),
        )
        data = json.loads(metrics.to_json())
        assert data["app_store"] is None
        assert data["revenuecat"]["mrr"] == 50.0
        assert data["mixpanel"] is None
        assert data["data_quality"]["rc"] == "ok"
        assert len(data["errors"]) == 1

    def test_to_json_with_no_data(self):
        metrics = DailyMetrics(
            date="2026-01-28",
            errors=("ASC: 401", "RC: 500"),
        )
        data = json.loads(metrics.to_json())
        assert data["app_store"] is None
        assert data["revenuecat"] is None
        assert data["mixpanel"] is None
        assert len(data["errors"]) == 2
