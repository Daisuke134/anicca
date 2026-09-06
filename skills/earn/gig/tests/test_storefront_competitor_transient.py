"""A single empty competitor page read is a transient, not a vanished competitor.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_competitor_transient.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import storefront_direct as direct  # noqa: E402
import listing_inventory  # noqa: E402


def test_empty_then_nonempty_read_succeeds_and_is_not_marked_unread(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        body = "" if len(calls) == 1 else "fresh body"
        return {"url": url, "title": "official", "body": body}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert len(calls) == 2
    assert len(manifest["sources"]) == 1
    assert manifest["unread"] == []
    row = json.loads(Path(manifest["sources"][0]["path"]).read_text())
    assert row["body"] == "fresh body"


def test_source_empty_on_every_attempt_is_skipped_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        if "categories" in url:
            return {"url": url, "title": "official", "body": ""}
        return {"url": url, "title": "official", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert len([call for call in calls if "categories" in call]) == 5
    assert len(manifest["sources"]) == 1
    assert manifest["sources"][0]["source_type"] == "service"
    assert len(manifest["unread"]) == 1
    unread = manifest["unread"][0]
    assert unread["source_type"] == "category"
    assert unread["requested_url"] == "https://coconala.com/categories/230/66"
    assert unread["reason"] == "competitor_source_empty"
    assert unread["attempts"] == 5


def test_all_sources_empty_raises_competitor_source_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)

    async def observed(_ws, url, _expression):
        return {"url": url, "title": "official", "body": ""}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError, match="competitor_source_empty"):
        direct._collect_competitors("ws://leased", tmp_path, set())


@pytest.mark.parametrize("case", [
    ("own_service", "competitor_source_is_own_service"),
    ("not_official", "competitor_source_not_official"),
    ("redirected", "competitor_service_redirected"),
])
def test_correctness_guards_raise_on_first_observation_and_are_not_retried(tmp_path, monkeypatch, case):
    scenario, expected_reason = case
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    if scenario == "own_service":
        monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
            ("service", "https://coconala.com/services/111"),
        ))
        own_ids = {"111"}

        async def observed(_ws, url, _expression):
            calls.append(url)
            return {"url": url, "title": "official", "body": "fresh body"}
    else:
        monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
            ("service", "https://coconala.com/services/222"),
        ))
        own_ids = set()

        async def observed(_ws, url, _expression):
            calls.append(url)
            if scenario == "not_official":
                return {"url": "https://example.com/services/222", "title": "x", "body": "fresh body"}
            return {"url": "https://coconala.com/services/999", "title": "x", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError, match=expected_reason):
        direct._collect_competitors("ws://leased", tmp_path, own_ids)

    assert len(calls) == (0 if scenario == "own_service" else 1)


def test_manifest_unread_empty_and_all_sources_present_when_everything_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
        ("service", "https://coconala.com/services/333"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)

    async def observed(_ws, url, _expression):
        return {"url": url, "title": "official", "body": f"fresh body {url}"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert manifest["unread"] == []
    assert len(manifest["sources"]) == 3
