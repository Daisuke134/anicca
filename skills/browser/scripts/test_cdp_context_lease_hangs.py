"""A wedged renderer must cost one context, never the caller's whole recovery.

Measured 2026-08-06 06:35 in the gig loop's parent log: B2's between-candidate target
recovery called `cdp_context_lease.py release`, the browser's renderer was wedged, and
`Target.disposeBrowserContext` never answered. `_calls()` had no timeout on `ws.recv()`, so
the lease script hung until the caller's 35-second subprocess limit killed it -- the
recovery designed to survive a dead target died at its first step, inside the lease.

Three properties pin that shut:
  1. `_calls` finishes or raises within its deadline, never hangs.
  2. `release` on a context that cannot be disposed keeps a cleanup tombstone so gc can
     still identify the browser-side context.
  3. acquire never creates a replacement while that old context remains undisposable.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parent / "cdp_context_lease.py"
    spec = importlib.util.spec_from_file_location("cdp_context_lease_hangs", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NeverAnsweringSocket:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def send(self, message):
        return None

    async def recv(self):
        await asyncio.sleep(3600)


def test_calls_raises_within_its_deadline_instead_of_hanging(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "_browser_ws", lambda: "ws://127.0.0.1:1/devtools/browser/x")
    monkeypatch.setattr(
        module.websockets, "connect", lambda *a, **k: NeverAnsweringSocket()
    )
    started = time.monotonic()
    try:
        asyncio.run(module._calls([("Target.disposeBrowserContext", {"browserContextId": "c"})], timeout=1.0))
        raise AssertionError("a call that never answers must raise")
    except Exception:
        pass
    assert time.monotonic() - started < 10


def test_release_of_an_undisposable_context_keeps_cleanup_tombstone(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    leases_file.write_text(json.dumps({
        "gig-task": {
            "context_id": "dead-context",
            "target_id": "dead-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/dead-target",
            "ts": 0,
            "token": "a" * 32,
            "generation": 1,
        }
    }), encoding="utf-8")

    async def hang_forever(pairs, timeout=None):
        raise TimeoutError("Target.disposeBrowserContext never answered")

    monkeypatch.setattr(module, "_calls", hang_forever)
    result = module.release("gig-task", token="a" * 32, generation=1)

    assert result["ok"] is True
    assert "gc" in str(result.get("note") or "")
    assert result["cleanup_pending"] is True
    saved = json.loads(leases_file.read_text(encoding="utf-8"))
    assert saved["gig-task"]["cleanup_pending"] is True


def test_acquire_does_not_orphan_an_undisposable_dead_context(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    leases_file.write_text(json.dumps({
        "gig-task": {
            "context_id": "dead-context", "target_id": "dead-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/dead-target",
            "ts": 0, "token": "a" * 32, "generation": 1,
        }
    }), encoding="utf-8")
    monkeypatch.setattr(module, "target_responds", lambda *_args, **_kwargs: False)

    async def dispose_fails(pairs, timeout=None):
        raise TimeoutError("dispose did not answer")

    monkeypatch.setattr(module, "_calls", dispose_fails)
    try:
        module.acquire("gig-task")
        raise AssertionError("acquire must fail closed while cleanup is unconfirmed")
    except RuntimeError as error:
        assert str(error) == "context_cleanup_pending"
    saved = json.loads(leases_file.read_text(encoding="utf-8"))
    assert saved["gig-task"]["cleanup_pending"] is True


def test_gc_keeps_cleanup_tombstone_until_dispose_succeeds(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    leases_file.write_text(json.dumps({
        "gig-task": {
            "context_id": "dead-context", "target_id": "dead-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/dead-target",
            "ts": 0, "token": "a" * 32, "generation": 1,
            "cleanup_pending": True,
        }
    }), encoding="utf-8")

    async def dispose_fails(pairs, timeout=None):
        raise TimeoutError("dispose did not answer")

    monkeypatch.setattr(module, "_calls", dispose_fails)
    result = module.gc(idle_min=45)

    assert result["reaped"] == []
    assert result["cleanup_pending"] == ["gig-task"]
    assert "gig-task" in json.loads(leases_file.read_text(encoding="utf-8"))


def test_release_with_a_wrong_fence_still_refuses(monkeypatch, tmp_path):
    # Dropping rows on dispose failure must not weaken the fence: a caller with a stale
    # token still cannot free someone else's context.
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    leases_file.write_text(json.dumps({
        "gig-task": {
            "context_id": "c", "target_id": "t",
            "ws": "ws://127.0.0.1:9222/devtools/page/t",
            "ts": 0, "token": "a" * 32, "generation": 2,
        }
    }), encoding="utf-8")
    result = module.release("gig-task", token="b" * 32, generation=2)
    assert result["ok"] is False
    assert json.loads(leases_file.read_text(encoding="utf-8")) != {}
