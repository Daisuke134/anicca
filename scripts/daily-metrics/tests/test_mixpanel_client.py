"""Tests for Mixpanel client."""

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import mixpanel_client
from window import ReportingWindow


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.captured = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, auth=None):
        self.captured = {"url": url, "params": params, "auth": auth}
        return self._response


def test_fetch_mixpanel_metrics_counts_unique_distinct_ids(monkeypatch):
    ndjson = "\n".join([
        '{"event":"onboarding_started","properties":{"distinct_id":"u1"}}',
        '{"event":"onboarding_started","properties":{"distinct_id":"u1"}}',
        '{"event":"onboarding_paywall_viewed","properties":{"distinct_id":"u1"}}',
        '{"event":"rc_trial_started_event","properties":{"distinct_id":"u2"}}',
        '{"event":"rc_trial_started_event","properties":{"$user_id":"u3"}}',
    ])

    fake = _FakeClient(_FakeResponse(ndjson))

    monkeypatch.setenv("MIXPANEL_SERVICE_ACCOUNT", "svc_user:svc_secret")
    monkeypatch.setattr(mixpanel_client.httpx, "AsyncClient", lambda timeout=30.0: fake)

    result = asyncio.run(mixpanel_client.fetch_mixpanel_metrics())

    assert result.onboarding_started == 1
    assert result.onboarding_paywall_viewed == 1
    assert result.rc_trial_started_event == 2
    assert fake.captured["url"] == mixpanel_client.MIXPANEL_EXPORT_URL
    assert fake.captured["auth"] == ("svc_user", "svc_secret")
    assert "from_date" in fake.captured["params"]
    assert "to_date" in fake.captured["params"]
    assert "event" in fake.captured["params"]


def test_fetch_mixpanel_metrics_uses_explicit_window(monkeypatch):
    ndjson = '{"event":"onboarding_started","properties":{"distinct_id":"u1"}}'
    fake = _FakeClient(_FakeResponse(ndjson))

    monkeypatch.setenv("MIXPANEL_SERVICE_ACCOUNT", "svc_user:svc_secret")
    monkeypatch.setattr(mixpanel_client.httpx, "AsyncClient", lambda timeout=30.0: fake)

    window = ReportingWindow(start_date=date(2026, 1, 26), end_date=date(2026, 2, 1))
    asyncio.run(mixpanel_client.fetch_mixpanel_metrics(window=window))

    assert fake.captured["params"]["from_date"] == "2026-01-26"
    assert fake.captured["params"]["to_date"] == "2026-02-01"


def test_requires_mixpanel_service_account(monkeypatch):
    monkeypatch.delenv("MIXPANEL_SERVICE_ACCOUNT", raising=False)

    try:
        mixpanel_client._basic_auth()
    except KeyError as exc:
        assert "MIXPANEL_SERVICE_ACCOUNT" in str(exc)
    else:
        raise AssertionError("Expected KeyError when MIXPANEL_SERVICE_ACCOUNT is missing")
