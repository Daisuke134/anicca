from __future__ import annotations

import importlib.util
from pathlib import Path


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
