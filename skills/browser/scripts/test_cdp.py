from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


def _load_module():
    path = Path(__file__).resolve().parent / "cdp.py"
    spec = importlib.util.spec_from_file_location("browser_cdp", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_host_matches_context_lease_websocket_host(monkeypatch):
    monkeypatch.delenv("CDP_HOST", raising=False)
    assert _load_module().HOST == "127.0.0.1"


def test_explicit_host_remains_supported(monkeypatch):
    monkeypatch.setenv("CDP_HOST", "browser.internal")
    assert _load_module().HOST == "browser.internal"


def test_new_claims_target_for_required_owner(monkeypatch, capsys):
    module = _load_module()
    events = []
    monkeypatch.setattr(
        module, "_browser_call", lambda method, params: {"targetId": "new-tab"}
    )
    monkeypatch.setattr(
        module.target_ownership,
        "claim_target",
        lambda target, owner, max_targets=None: events.append(
            (target, owner, max_targets)
        ),
    )

    assert module.main(["new", "about:blank", "paid-room"]) == 0
    assert capsys.readouterr().out.strip() == "new-tab"
    assert events == [("new-tab", "paid-room", 1)]


def test_close_refuses_foreign_target_before_cdp_call(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module.target_ownership, "owns_target", lambda _target, _owner: False
    )
    with patch.object(module, "_browser_call") as browser_call:
        with pytest.raises(PermissionError):
            module.main(["close", "foreign-tab", "paid-room"])
    browser_call.assert_not_called()
