"""A timed-out tab open is a transient environment failure, not a broken page.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_tab_open_retry.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import storefront_draft as draft  # noqa: E402
import storefront_direct as direct  # noqa: E402


def test_first_timeout_then_success_returns_result_after_two_calls(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr(draft.time, "sleep", lambda seconds: sleeps.append(seconds))

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=30)
        return subprocess.CompletedProcess(argv, 0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(draft.subprocess, "run", fake_run)
    result = draft.open_tab_with_retry(["fake"], timeout=30)

    assert result.stdout == '{"ok": true}'
    assert len(calls) == 2
    assert sleeps == [3]


def test_every_attempt_times_out_propagates_after_five_calls(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr(draft.time, "sleep", lambda seconds: sleeps.append(seconds))

    def fake_run(argv, **kwargs):
        calls.append(argv)
        raise subprocess.TimeoutExpired(cmd=argv, timeout=30)

    monkeypatch.setattr(draft.subprocess, "run", fake_run)

    with pytest.raises(subprocess.TimeoutExpired):
        draft.open_tab_with_retry(["fake"], timeout=30)

    assert len(calls) == 5
    assert sleeps == [3, 3, 3, 3]


def test_nonzero_return_code_is_returned_after_exactly_one_call(monkeypatch):
    calls = []

    def unexpected_sleep(_seconds):
        raise AssertionError("a non-zero return code must not be retried")

    monkeypatch.setattr(draft.time, "sleep", unexpected_sleep)

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, stdout='{"ok": false}', stderr="boom")

    monkeypatch.setattr(draft.subprocess, "run", fake_run)
    result = draft.open_tab_with_retry(["fake"], timeout=30)

    assert result.returncode == 1
    assert result.stdout == '{"ok": false}'
    assert len(calls) == 1


def test_successful_first_call_is_returned_after_exactly_one_call(monkeypatch):
    calls = []

    def unexpected_sleep(_seconds):
        raise AssertionError("a clean success must not be retried")

    monkeypatch.setattr(draft.time, "sleep", unexpected_sleep)

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(draft.subprocess, "run", fake_run)
    result = draft.open_tab_with_retry(["fake"], timeout=30)

    assert result.returncode == 0
    assert len(calls) == 1


def test_storefront_draft_call_site_routes_open_through_retry_helper(monkeypatch):
    """`create_or_claim_blank_draft` must call the shared helper, not `subprocess.run` directly."""
    calls = []

    def fake_helper(argv, **kwargs):
        calls.append(argv)
        raise RuntimeError("sentinel-stop")

    monkeypatch.setattr(draft, "open_tab_with_retry", fake_helper)

    with pytest.raises(RuntimeError, match="sentinel-stop"):
        draft.create_or_claim_blank_draft(Path("/fake/cdp_default_tab.py"), [])

    assert len(calls) == 1
    assert calls[0][-1] == "https://coconala.com/mypage/services_lists"


def test_storefront_direct_call_site_routes_open_through_retry_helper(monkeypatch):
    """`_seller_snapshot_from_fresh_tab` must call `storefront_draft.open_tab_with_retry`."""
    calls = []

    def fake_helper(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(stdout=json.dumps({"ok": True, "ws": "ws://leased"}), returncode=0)

    monkeypatch.setattr(draft, "open_tab_with_retry", fake_helper)
    monkeypatch.setattr(direct, "_seller_snapshot_for", lambda ws_url, service_id: {"snapshot": True})

    result = direct._seller_snapshot_from_fresh_tab(Path("/fake/cdp_default_tab.py"), "123")

    assert result == {"snapshot": True}
    assert len(calls) == 1
    assert calls[0][-1] == "https://coconala.com/mypage/services/123"
