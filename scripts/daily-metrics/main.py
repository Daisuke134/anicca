"""Daily metrics collection: ASC + RevenueCat + Mixpanel -> Slack."""

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from models import AppStoreMetrics, DailyMetrics, DataQuality, MixpanelMetrics, RevenueCatMetrics
from window import asc_reporting_window, behavior_reporting_window

T = TypeVar("T")


async def collect_metrics() -> DailyMetrics:
    """Collect metrics from all sources in parallel. Partial failures are tolerated."""
    from asc_client import fetch_app_store_metrics
    from mixpanel_client import fetch_mixpanel_metrics
    from revenuecat_client import fetch_revenuecat_metrics

    errors: list[str] = []
    asc_window = asc_reporting_window()
    behavior_window = behavior_reporting_window()

    asc_task = asyncio.create_task(
        _safe_fetch("App Store Connect", lambda: fetch_app_store_metrics(asc_window))
    )
    rc_task = asyncio.create_task(
        _safe_fetch("RevenueCat", lambda: fetch_revenuecat_metrics(behavior_window))
    )
    mp_task = asyncio.create_task(
        _safe_fetch("Mixpanel", lambda: fetch_mixpanel_metrics(behavior_window))
    )

    asc_result, asc_error = await asc_task
    rc_result, rc_error = await rc_task
    mp_result, mp_error = await mp_task

    if asc_error:
        errors.append(f"App Store Connect API: {asc_error}")
    if rc_error:
        errors.append(f"RevenueCat API: {rc_error}")
    if mp_error:
        errors.append(f"Mixpanel API: {mp_error}")

    data_quality = DataQuality(
        asc="ok" if asc_result else "missing",
        rc="ok" if rc_result else "missing",
        mp="ok" if mp_result else "missing",
    )

    return DailyMetrics(
        date=date.today().isoformat(),
        app_store=asc_result,
        revenuecat=rc_result,
        mixpanel=mp_result,
        data_quality=data_quality,
        errors=tuple(errors),
    )


async def _safe_fetch(name: str, fn: Callable[[], Awaitable[T]]) -> tuple[T | None, str | None]:
    """Execute fetch function, returning (result, error_string)."""
    try:
        result = await fn()
        return result, None
    except Exception as e:
        print(f"ERROR: {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None, f"{type(e).__name__}: {e}"


async def send_report(metrics: DailyMetrics) -> None:
    """Format and send metrics to Slack."""
    from slack_sender import format_error_message, format_slack_blocks, send_to_slack

    previous = _load_previous_metrics()

    if metrics.app_store is None and metrics.revenuecat is None and metrics.mixpanel is None:
        # Total failure
        payload = format_error_message(errors=list(metrics.errors), successes=[])
    else:
        # Full or partial success
        payload = format_slack_blocks(metrics, previous)

    sent = await send_to_slack(payload)
    if not sent:
        print("ERROR: Failed to send Slack message after retries", file=sys.stderr)
        sys.exit(1)

    print(f"Slack message sent for {metrics.date}")


def _load_previous_metrics() -> DailyMetrics | None:
    """Load previous day's metrics from artifact JSON if available."""
    metrics_dir = Path(os.environ.get("METRICS_DIR", "metrics_archive"))
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    prev_file = metrics_dir / f"{yesterday}.json"

    if prev_file.exists():
        try:
            data = json.loads(prev_file.read_text())
            app_store = None
            if data.get("app_store"):
                asc_data = data["app_store"]
                # Convert list of lists back to tuple of tuples for countries
                countries = asc_data.get("downloads_by_country", [])
                if countries and isinstance(countries[0], list):
                    countries = tuple(tuple(c) for c in countries)
                else:
                    countries = tuple(countries) if countries else ()
                app_store = AppStoreMetrics(
                    total_downloads_7d=asc_data.get("total_downloads_7d", 0),
                    downloads_by_country=countries,
                    impressions=asc_data.get("impressions", 0),
                    page_views=asc_data.get("page_views", 0),
                    cvr_page_to_download=asc_data.get("cvr_page_to_download", 0.0),
                )
            revenuecat = None
            if data.get("revenuecat"):
                rc_data = data["revenuecat"]
                revenuecat = RevenueCatMetrics(
                    mrr=rc_data.get("mrr", 0.0),
                    active_subscriptions=rc_data.get("active_subscriptions", 0),
                    active_trials=rc_data.get("active_trials", 0),
                    trial_to_paid_count=rc_data.get("trial_to_paid_count", 0),
                    trial_expired_count=rc_data.get("trial_expired_count", 0),
                    monthly_churn_rate=rc_data.get("monthly_churn_rate", 0.0),
                )
            mixpanel = None
            if data.get("mixpanel"):
                mp_data = data["mixpanel"]
                mixpanel = MixpanelMetrics(
                    onboarding_started=mp_data.get("onboarding_started"),
                    onboarding_struggles_completed=mp_data.get("onboarding_struggles_completed"),
                    onboarding_live_demo_completed=mp_data.get("onboarding_live_demo_completed"),
                    onboarding_notifications_completed=mp_data.get("onboarding_notifications_completed"),
                    onboarding_completed=mp_data.get("onboarding_completed"),
                    onboarding_paywall_viewed=mp_data.get("onboarding_paywall_viewed"),
                    onboarding_paywall_dismissed_free=mp_data.get("onboarding_paywall_dismissed_free"),
                    onboarding_paywall_purchased=mp_data.get("onboarding_paywall_purchased"),
                    rc_trial_started_event=mp_data.get("rc_trial_started_event"),
                )
            dq_data = data.get("data_quality", {})
            return DailyMetrics(
                date=data["date"],
                app_store=app_store,
                revenuecat=revenuecat,
                mixpanel=mixpanel,
                data_quality=DataQuality(
                    asc=dq_data.get("asc", "missing"),
                    rc=dq_data.get("rc", "missing"),
                    mp=dq_data.get("mp", "missing"),
                ),
                errors=tuple(data.get("errors", [])),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"WARNING: Failed to load previous metrics: {e}", file=sys.stderr)
            return None
    return None


def save_metrics(metrics: DailyMetrics) -> None:
    """Save metrics as JSON for future day-over-day comparison."""
    metrics_dir = Path(os.environ.get("METRICS_DIR", "metrics_archive"))
    metrics_dir.mkdir(parents=True, exist_ok=True)
    output_path = metrics_dir / f"{metrics.date}.json"
    output_path.write_text(metrics.to_json())
    print(f"Metrics saved to {output_path}")


async def main() -> None:
    metrics = await collect_metrics()
    await send_report(metrics)
    save_metrics(metrics)


if __name__ == "__main__":
    asyncio.run(main())
