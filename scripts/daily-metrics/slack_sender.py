"""Slack message formatter and sender for daily metrics."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from typing import Optional

import httpx

from models import DailyMetrics


def _safe_div_pct(numerator: Optional[int], denominator: Optional[int]) -> str:
    """Return percentage string with one decimal, or N/A when undefined."""
    if numerator is None or denominator is None:
        return "N/A"
    if denominator <= 0:
        return "N/A"
    return f"{(numerator / denominator) * 100:.1f}%"


def _raw_fraction(numerator: Optional[int], denominator: Optional[int]) -> str:
    """Return raw fraction text, or N/A when undefined."""
    if numerator is None or denominator is None:
        return "N/A"
    if denominator <= 0:
        return "N/A"
    return f"({numerator}/{denominator})"


def _top_country_line(metrics: DailyMetrics) -> str:
    if not metrics.app_store:
        return "Downloads N/A, Top: N/A"

    total = metrics.app_store.total_downloads_7d
    countries = metrics.app_store.downloads_by_country
    if not countries:
        return f"Downloads {total}, Top: N/A"

    top_country, top_count = countries[0]
    return f"Downloads {total}, Top: {top_country}({top_count})"


def _revenue_line(metrics: DailyMetrics) -> str:
    if not metrics.revenuecat:
        return "MRR N/A, Subs N/A, Trials N/A"

    rc = metrics.revenuecat
    mrr = f"${rc.mrr:.0f}" if float(rc.mrr).is_integer() else f"${rc.mrr:.2f}"
    return (
        f"MRR {mrr} (snapshot), "
        f"Subs {rc.active_subscriptions} (snapshot), "
        f"Trials {rc.active_trials} (snapshot)"
    )


def _funnel_values(metrics: DailyMetrics) -> tuple[Optional[int], Optional[int], Optional[int]]:
    onboarding = metrics.mixpanel.onboarding_started if metrics.mixpanel else None
    paywall = metrics.mixpanel.onboarding_paywall_viewed if metrics.mixpanel else None
    trial = metrics.mixpanel.rc_trial_started_event if metrics.mixpanel else None

    return onboarding, paywall, trial


def format_slack_blocks(metrics: DailyMetrics, previous: DailyMetrics | None = None) -> dict:
    """Format metrics into a concise daily report."""
    onboarding, paywall, trial = _funnel_values(metrics)

    onboarding_text = "N/A" if onboarding is None else str(onboarding)
    paywall_text = "N/A" if paywall is None else str(paywall)
    trial_text = "N/A" if trial is None else str(trial)

    rate_onboarding_paywall = _safe_div_pct(paywall, onboarding)
    rate_paywall_trial = _safe_div_pct(trial, paywall)

    raw_onboarding_paywall = _raw_fraction(paywall, onboarding)
    raw_paywall_trial = _raw_fraction(trial, paywall)

    report_text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 APP STORE (7日): {_top_country_line(metrics)}\n"
        f"💰 REVENUE: {_revenue_line(metrics)}\n"
        f"📈 FUNNEL (7日): onboarding {onboarding_text}, paywall {paywall_text}, trial {trial_text}\n"
        f"📊 変換率: オンボ→Paywall {rate_onboarding_paywall} {raw_onboarding_paywall}, "
        f"Paywall→Trial {rate_paywall_trial} {raw_paywall_trial}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Data Quality: ASC {metrics.data_quality.asc} / RC {metrics.data_quality.rc} / MP {metrics.data_quality.mp}\n"
        "🧘 Anicca Bot"
    )

    trend_line = _trend_line(metrics, previous)
    if trend_line:
        report_text += f"\n📊 Trend: {trend_line}"

    alerts_line = _alerts_line(metrics)
    if alerts_line:
        report_text += f"\n⚠️ Alerts: {alerts_line}"

    if metrics.errors:
        error_lines = "\n".join(f"- {err}" for err in metrics.errors)
        report_text += f"\n\nErrors:\n{error_lines}"

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📊 Anicca Daily Report ({metrics.date})"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": report_text},
            },
        ]
    }


def _trend_line(metrics: DailyMetrics, previous: DailyMetrics | None) -> str:
    if not previous:
        return ""

    parts: list[str] = []

    if metrics.app_store and previous.app_store:
        curr_dl = metrics.app_store.total_downloads_7d
        prev_dl = previous.app_store.total_downloads_7d
        parts.append(f"DL {curr_dl - prev_dl:+d}")

    if metrics.revenuecat and previous.revenuecat:
        curr_mrr = metrics.revenuecat.mrr
        prev_mrr = previous.revenuecat.mrr
        diff_mrr = curr_mrr - prev_mrr
        parts.append(f"MRR {diff_mrr:+.2f}")

    curr_onboarding, curr_paywall, _ = _funnel_values(metrics)
    prev_onboarding, prev_paywall, _ = _funnel_values(previous)
    curr_rate = _as_float_ratio(curr_paywall, curr_onboarding)
    prev_rate = _as_float_ratio(prev_paywall, prev_onboarding)
    if curr_rate is not None and prev_rate is not None:
        parts.append(f"Onbo→Paywall {(curr_rate - prev_rate) * 100:+.1f}pp")

    return ", ".join(parts)


def _alerts_line(metrics: DailyMetrics) -> str:
    alerts: list[str] = []

    if metrics.app_store:
        cvr = metrics.app_store.cvr_page_to_download
        if cvr < 3.0:
            alerts.append(f"CVR低下({cvr:.1f}% < 3.0%)")

        avg_dl = metrics.app_store.total_downloads_7d / 7
        if avg_dl < 10.0:
            alerts.append(f"DL低下({avg_dl:.1f}/日 < 10.0/日)")

    return ", ".join(alerts)


def _as_float_ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def format_error_message(errors: list[str], successes: list[str]) -> dict:
    """Format error notification for Slack (total failure case)."""
    today_str = date.today().isoformat()
    lines = [f"❌ {err}" for err in errors]
    lines.extend(f"✅ {suc}" for suc in successes)

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 Anicca Metrics Error ({today_str})"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines) if lines else "No details"},
            },
        ]
    }


async def send_to_slack(payload: dict) -> bool:
    """Send Block Kit payload to Slack.

    Priority:
    1) Incoming webhook (SLACK_METRICS_WEBHOOK_URL)
    2) Bot token + chat.postMessage fallback
    """
    webhook_url = os.environ.get("SLACK_METRICS_WEBHOOK_URL", "").strip()
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("SLACK_METRICS_CHANNEL_ID", "C091G3PKHL2").strip()

    text_fallback = "Anicca Daily Report"
    if payload.get("blocks"):
        # Header + section text first, to keep push notifications readable.
        try:
            header = payload["blocks"][0]["text"]["text"]
            body = payload["blocks"][1]["text"]["text"]
            text_fallback = f"{header}\n{body}"
        except (KeyError, IndexError, TypeError):
            pass

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(3):
            try:
                if webhook_url:
                    resp = await client.post(webhook_url, json=payload)
                elif bot_token:
                    resp = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            "Authorization": f"Bearer {bot_token}",
                            "Content-Type": "application/json; charset=utf-8",
                        },
                        json={
                            "channel": channel_id,
                            "text": text_fallback,
                            "blocks": payload.get("blocks", []),
                        },
                    )
                else:
                    print("Slack credentials missing: webhook and bot token are both unset", file=sys.stderr)
                    return False

                if resp.status_code == 200:
                    # chat.postMessage can return HTTP 200 with {"ok": false}
                    if not webhook_url:
                        data = resp.json()
                        if not data.get("ok", False):
                            print(f"Slack API error: {data}", file=sys.stderr)
                            return False
                    return True
                print(f"Slack API returned {resp.status_code}: {resp.text}", file=sys.stderr)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return False
            except httpx.HTTPError as e:
                print(f"Slack send attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt < 2:
                    await asyncio.sleep(1)
        return False
