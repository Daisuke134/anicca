"""Tests for Slack message formatting."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AppStoreMetrics, DailyMetrics, DataQuality, MixpanelMetrics, RevenueCatMetrics
from slack_sender import format_error_message, format_slack_blocks


class TestFormatSlackBlocks:
    def test_full_metrics_format(self):
        metrics = DailyMetrics(
            date="2026-02-09",
            app_store=AppStoreMetrics(
                total_downloads_7d=112,
                downloads_by_country=(("JP", 108), ("US", 4)),
            ),
            revenuecat=RevenueCatMetrics(
                mrr=22.0,
                active_subscriptions=3,
                active_trials=1,
            ),
            mixpanel=MixpanelMetrics(
                onboarding_started=230,
                onboarding_paywall_viewed=58,
                rc_trial_started_event=3,
            ),
            data_quality=DataQuality(asc="ok", rc="ok", mp="ok"),
        )

        payload = format_slack_blocks(metrics)
        assert "blocks" in payload
        assert payload["blocks"][0]["type"] == "header"
        body = payload["blocks"][1]["text"]["text"]

        assert "APP STORE (7日): Downloads 112, Top: JP(108)" in body
        assert "REVENUE: MRR $22 (snapshot), Subs 3 (snapshot), Trials 1 (snapshot)" in body
        assert "FUNNEL (7日): onboarding 230, paywall 58, trial 3" in body
        assert "オンボ→Paywall 25.2% (58/230)" in body
        assert "Paywall→Trial 5.2% (3/58)" in body
        assert "Data Quality: ASC ok / RC ok / MP ok" in body

    def test_mixpanel_missing_outputs_na(self):
        metrics = DailyMetrics(
            date="2026-02-10",
            app_store=AppStoreMetrics(total_downloads_7d=109, downloads_by_country=(("JP", 103),)),
            revenuecat=RevenueCatMetrics(
                mrr=24.0,
                active_subscriptions=3,
                active_trials=1,
            ),
            mixpanel=None,
            data_quality=DataQuality(asc="ok", rc="ok", mp="missing"),
        )

        payload = format_slack_blocks(metrics)
        body = payload["blocks"][1]["text"]["text"]

        assert "FUNNEL (7日): onboarding N/A, paywall N/A, trial N/A" in body
        assert "オンボ→Paywall N/A N/A" in body
        assert "Paywall→Trial N/A N/A" in body
        assert "Data Quality: ASC ok / RC ok / MP missing" in body

    def test_alerts_line_shows_when_cvr_and_daily_dl_low(self):
        metrics = DailyMetrics(
            date="2026-02-10",
            app_store=AppStoreMetrics(
                total_downloads_7d=14,  # 2/day
                downloads_by_country=(("JP", 14),),
                cvr_page_to_download=1.9,
            ),
            data_quality=DataQuality(asc="ok", rc="missing", mp="missing"),
        )

        payload = format_slack_blocks(metrics)
        body = payload["blocks"][1]["text"]["text"]
        assert "Alerts:" in body
        assert "CVR低下" in body
        assert "DL低下" in body

    def test_trend_line_shows_when_previous_exists(self):
        current = DailyMetrics(
            date="2026-02-10",
            app_store=AppStoreMetrics(total_downloads_7d=110, downloads_by_country=(("JP", 100),)),
            revenuecat=RevenueCatMetrics(mrr=22.0, active_subscriptions=3, active_trials=1),
            mixpanel=MixpanelMetrics(onboarding_started=200, onboarding_paywall_viewed=50),
            data_quality=DataQuality(asc="ok", rc="ok", mp="ok"),
        )
        previous = DailyMetrics(
            date="2026-02-09",
            app_store=AppStoreMetrics(total_downloads_7d=100, downloads_by_country=(("JP", 90),)),
            revenuecat=RevenueCatMetrics(mrr=20.0, active_subscriptions=3, active_trials=1),
            mixpanel=MixpanelMetrics(onboarding_started=250, onboarding_paywall_viewed=50),
            data_quality=DataQuality(asc="ok", rc="ok", mp="ok"),
        )

        payload = format_slack_blocks(current, previous)
        body = payload["blocks"][1]["text"]["text"]
        assert "Trend:" in body
        assert "DL +10" in body
        assert "MRR +2.00" in body

    def test_trend_line_hidden_without_previous(self):
        metrics = DailyMetrics(
            date="2026-02-10",
            app_store=AppStoreMetrics(total_downloads_7d=110, downloads_by_country=(("JP", 100),)),
            data_quality=DataQuality(asc="ok", rc="missing", mp="missing"),
        )
        payload = format_slack_blocks(metrics, None)
        body = payload["blocks"][1]["text"]["text"]
        assert "Trend:" not in body

    def test_alerts_hidden_when_metrics_are_healthy(self):
        metrics = DailyMetrics(
            date="2026-02-10",
            app_store=AppStoreMetrics(
                total_downloads_7d=84,  # 12/day
                downloads_by_country=(("JP", 70),),
                cvr_page_to_download=3.5,
            ),
            data_quality=DataQuality(asc="ok", rc="missing", mp="missing"),
        )
        payload = format_slack_blocks(metrics)
        body = payload["blocks"][1]["text"]["text"]
        assert "Alerts:" not in body


class TestFormatErrorMessage:
    def test_error_format(self):
        payload = format_error_message(
            errors=["App Store Connect API: 認証エラー (401)"],
            successes=["RevenueCat API: 正常"],
        )
        blocks = payload["blocks"]
        assert blocks[0]["text"]["text"].startswith("🚨")
        status_text = blocks[1]["text"]["text"]
        assert "❌" in status_text
        assert "✅" in status_text
