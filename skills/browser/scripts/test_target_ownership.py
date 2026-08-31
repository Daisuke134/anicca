"""Regression tests for loop-owned CDP targets.

The production browser is shared by several loops. A loop may only close targets
that it registered under its own owner name; unowned and foreign targets are
never garbage-collected.
"""
import asyncio
import json
import os
import sys
from types import SimpleNamespace

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


def test_visible_default_tab_uses_json_new_endpoint(tmp_path, monkeypatch):
    registry = tmp_path / "target-owners.json"
    monkeypatch.setenv("CLOAK_TARGET_OWNERS_FILE", str(registry))
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request.full_url, request.get_method(), timeout))
        return SimpleNamespace(read=lambda: json.dumps({
            "id": "visible-1",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9223/devtools/page/visible-1",
        }).encode())

    monkeypatch.setattr(default_tab.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        default_tab.cdp, "_browser_call",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy CDP createTarget")),
    )

    row = default_tab.open_tab(
        "https://coconala.com/talkrooms/18211957", owner="paid",
    )

    assert requests == [(
        "http://127.0.0.1:9222/json/new?https%3A%2F%2Fcoconala.com%2Ftalkrooms%2F18211957",
        "PUT",
        8,
    )]
    assert row["target_id"] == "visible-1"
    assert row["ws"] == "ws://127.0.0.1:9223/devtools/page/visible-1"
    assert ownership.owner_for_target("visible-1") == "paid"


def test_hidden_tab_closes_target_before_releasing_ownership(tmp_path, monkeypatch):
    registry = tmp_path / "target-owners.json"
    monkeypatch.setenv("CLOAK_TARGET_OWNERS_FILE", str(registry))
    sent = []

    class FakeWebSocket:
        async def send(self, payload):
            sent.append(json.loads(payload))

        async def recv(self):
            request_id = sent[-1]["id"]
            if request_id == 1:
                return json.dumps({"id": 1, "result": {"targetId": "hidden-1"}})
            return json.dumps({"id": 2, "result": {"success": True}})

    class FakeConnection:
        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(default_tab.websockets, "connect", lambda *_args, **_kwargs: FakeConnection())
    monkeypatch.setattr(
        default_tab.sys, "stdin", SimpleNamespace(buffer=SimpleNamespace(read=lambda: b"")),
    )

    asyncio.run(default_tab._serve_hidden_tab("https://coconala.com", owner="paid"))

    assert [row["method"] for row in sent] == ["Target.createTarget", "Target.closeTarget"]
    assert sent[-1]["params"] == {"targetId": "hidden-1"}
    assert ownership.owner_for_target("hidden-1") is None
