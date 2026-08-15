"""Regression tests for loop-owned CDP targets.

The production browser is shared by several loops. A loop may only close targets
that it registered under its own owner name; unowned and foreign targets are
never garbage-collected.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cdp_default_tab as default_tab  # noqa: E402
import cdp_tab_gc as tab_gc  # noqa: E402
import target_ownership as ownership  # noqa: E402


def test_registry_release_refuses_foreign_owner(tmp_path, monkeypatch):
    registry = tmp_path / "target-owners.json"
    monkeypatch.setenv("CLOAK_TARGET_OWNERS_FILE", str(registry))

    ownership.claim_target("gig-target", "gig-pass")
    ownership.claim_target("other-target", "article-loop")

    assert ownership.release_target("gig-target", "article-loop") is False
    assert ownership.targets_for_owner("gig-pass") == {"gig-target"}
    assert ownership.targets_for_owner("article-loop") == {"other-target"}


def test_gc_selects_only_callers_owned_surplus_targets(tmp_path, monkeypatch):
    registry = tmp_path / "target-owners.json"
    monkeypatch.setenv("CLOAK_TARGET_OWNERS_FILE", str(registry))
    ownership.claim_target("gig-keep", "gig-pass")
    ownership.claim_target("gig-close", "gig-pass")
    ownership.claim_target("foreign", "article-loop")

    tabs = [
        {"id": "gig-keep", "type": "page", "url": "https://coconala.com/mypage"},
        {"id": "gig-close", "type": "page", "url": "https://coconala.com/requests/1"},
        {"id": "foreign", "type": "page", "url": "https://coconala.com/requests/2"},
        {"id": "unowned", "type": "page", "url": "about:blank"},
    ]

    assert tab_gc.select_doomed_target_ids(tabs, "gig-pass", keep_coconala=1) == [
        "gig-close"
    ]


def test_default_tab_close_refuses_target_owned_by_another_loop(
    tmp_path, monkeypatch
):
    registry = tmp_path / "target-owners.json"
    monkeypatch.setenv("CLOAK_TARGET_OWNERS_FILE", str(registry))
    ownership.claim_target("foreign", "article-loop")
    calls = []

    async def fake_call(method, params=None):
        calls.append((method, params))
        return {}

    monkeypatch.setattr(default_tab, "_call", fake_call)

    with pytest.raises(PermissionError):
        default_tab.close_tab("foreign", owner="gig-pass")

    assert calls == []
