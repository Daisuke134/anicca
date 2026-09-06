"""A recoverable failure about ONE item must not end a wake with many items to read.

See skills/loop-engineering/references/transient-vs-fatal.md for the general rule:
a verdict about the decision fails closed; weather is retried with the house shape;
an answer about one item among many is recorded, skipped, and the job continues.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_per_item_failures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import storefront_direct as direct  # noqa: E402
import listing_inventory  # noqa: E402


# ---------------------------------------------------------------------------
# _collect_competitors: competitor_source_not_official / competitor_service_redirected
# ---------------------------------------------------------------------------

def test_one_competitor_redirected_is_recorded_and_skipped_others_still_read(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("service", "https://coconala.com/services/222"),
        ("service", "https://coconala.com/services/333"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        if url.endswith("/222"):
            # Redirected to a different service id -- delisted or moved.
            return {"url": "https://coconala.com/services/999", "title": "x", "body": "fresh body"}
        return {"url": url, "title": "official", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert len(manifest["sources"]) == 1
    assert manifest["sources"][0]["url"] == "https://coconala.com/services/333"
    assert len(manifest["unread"]) == 1
    unread = manifest["unread"][0]
    assert unread["requested_url"] == "https://coconala.com/services/222"
    assert unread["reason"] == "competitor_service_redirected"
    # A redirect is a stable answer, not weather: it is not retried.
    assert unread["attempts"] == 1
    assert len([call for call in calls if call.endswith("/222")]) == 1


def test_one_competitor_off_official_domain_is_recorded_and_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        if "categories" in url:
            # Went somewhere off coconala.com entirely.
            return {"url": "https://example.com/categories/230/66", "title": "x", "body": "fresh body"}
        return {"url": url, "title": "official", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert len(manifest["sources"]) == 1
    assert manifest["sources"][0]["source_type"] == "service"
    assert len(manifest["unread"]) == 1
    unread = manifest["unread"][0]
    assert unread["source_type"] == "category"
    assert unread["reason"] == "competitor_source_not_official"
    assert unread["attempts"] == 1
    assert len([call for call in calls if "categories" in call]) == 1


def test_own_service_still_raises_immediately_and_is_attempted_exactly_once(tmp_path, monkeypatch):
    # Unlike a redirect or an off-site page, an id from our own catalogue showing up
    # in the competitor list is a mistake in our own source list, not weather about a
    # competitor's page -- it must still fail the wake closed, on the first
    # observation, without ever calling out to read the page.
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("service", "https://coconala.com/services/111"),
        ("service", "https://coconala.com/services/222"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        return {"url": url, "title": "official", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError, match="competitor_source_is_own_service"):
        direct._collect_competitors("ws://leased", tmp_path, {"111"})

    assert calls == []


def test_all_sources_redirected_raises_naming_redirect_not_emptiness(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("service", "https://coconala.com/services/222"),
        ("service", "https://coconala.com/services/333"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)

    async def observed(_ws, url, _expression):
        return {"url": "https://coconala.com/services/999", "title": "x", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError) as excinfo:
        direct._collect_competitors("ws://leased", tmp_path, set())

    # "All fourteen redirected" must not be reported as "empty" -- the message names
    # what actually happened when every source failed for the same non-empty reason.
    assert str(excinfo.value) == "competitor_service_redirected"
    assert str(excinfo.value) != "competitor_source_empty"


def test_mixed_empty_redirected_and_good_sources_keeps_only_the_good_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
        ("service", "https://coconala.com/services/333"),
    ))
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)

    async def observed(_ws, url, _expression):
        if "categories" in url:
            return {"url": url, "title": "official", "body": ""}
        if url.endswith("/222"):
            return {"url": "https://coconala.com/services/999", "title": "x", "body": "fresh body"}
        return {"url": url, "title": "official", "body": "fresh body"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, set())

    assert len(manifest["sources"]) == 1
    assert manifest["sources"][0]["url"] == "https://coconala.com/services/333"
    reasons = {row["source_type"]: row["reason"] for row in manifest["unread"]}
    assert reasons == {
        "category": "competitor_source_empty",
        "service": "competitor_service_redirected",
    }


# ---------------------------------------------------------------------------
# _crawl_demand_cluster: the empty-body read gets the house retry shape, and its
# failures split into per-query-skippable vs whole-job-fatal depending on the caller.
# ---------------------------------------------------------------------------

def _patch_tab(monkeypatch, *, tab_ok=True):
    import storefront_draft

    monkeypatch.setattr(
        storefront_draft, "open_tab_with_retry",
        lambda *_a, **_k: direct.subprocess.CompletedProcess(
            [], 0, '{"ok": true, "ws": "ws://tab", "target_id": "t1"}' if tab_ok
            else '{"ok": false}', "",
        ),
    )
    monkeypatch.setattr(
        direct.subprocess, "run",
        lambda *_a, **_k: direct.subprocess.CompletedProcess([], 0, "", ""),
    )


def test_crawl_demand_cluster_retries_empty_body_then_succeeds(tmp_path, monkeypatch):
    _patch_tab(monkeypatch)
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        body = "" if len(calls) == 1 else "demand results"
        return {"url": url, "body": body}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    result = direct._crawl_demand_cluster(Path("tab.py"), tmp_path, "excel 自動化")

    assert len(calls) == 2
    assert result["query"] == "excel 自動化"


def test_crawl_demand_cluster_empty_on_every_attempt_raises_after_five_reads(tmp_path, monkeypatch):
    _patch_tab(monkeypatch)
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        return {"url": url, "body": ""}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError, match="storefront_demand_source_empty"):
        direct._crawl_demand_cluster(Path("tab.py"), tmp_path, "excel 自動化")

    assert len(calls) == 5


# The decision of which _crawl_demand_cluster failures are per-item vs whole-job is
# made at the call site, not inside the function (the function serves both a
# single-query bootstrap crawl and a many-candidate exploration loop). This predicate
# is what the exploration loop consults; it is a pure function so the decision is
# testable without driving the full run_once wake.
def test_demand_crawl_per_query_reasons_are_the_ones_the_exploration_loop_skips():
    # Per-item: an answer about the one query that failed, not our account/config.
    assert direct._demand_crawl_failure_is_per_query(
        RuntimeError("storefront_demand_tab_open_failed")
    ) is True
    assert direct._demand_crawl_failure_is_per_query(
        RuntimeError("storefront_demand_source_not_official")
    ) is True
    assert direct._demand_crawl_failure_is_per_query(
        RuntimeError("storefront_demand_source_empty")
    ) is True
    # Anything else (e.g. a bug surfaced as some other RuntimeError) is not
    # per-query and must still propagate and end the exploration attempt.
    assert direct._demand_crawl_failure_is_per_query(
        RuntimeError("storefront_demand_proposal_evidence_invalid")
    ) is False


# ---------------------------------------------------------------------------
# _observe_own_page: own_candidate_readback_invalid stays fatal.
#
# Every call site reads exactly ONE service that this wake's decision is already
# about (the mutation candidate, the gallery service, a recovery target, or the
# before/after readback for the accepted judgement) -- never one of several
# interchangeable items in a loop. So unlike the competitor sources, a readback that
# never settles is the whole wake's answer, not one skippable item among many, and it
# is left fatal. It already used the house retry shape before this pass; only the
# reasoning is new.
# ---------------------------------------------------------------------------

def test_own_page_readback_invalid_after_retries_still_ends_the_wake(tmp_path, monkeypatch):
    monkeypatch.setattr(direct.time, "sleep", lambda _seconds: None)
    calls = []

    async def observed(_ws, url, _expression):
        calls.append(url)
        # Never a valid readback: no service_image_ids at all.
        return {"url": url, "title": "t", "body": "body text"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)

    with pytest.raises(RuntimeError, match="own_candidate_readback_invalid"):
        direct._observe_own_page("ws://leased", tmp_path, service_id="222")

    assert len(calls) == 5
