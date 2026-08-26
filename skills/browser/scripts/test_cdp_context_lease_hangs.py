"""A wedged renderer must cost one context, never the caller's whole recovery.

Measured 2026-08-06 06:35 in the gig loop's parent log: B2's between-candidate target
recovery called `cdp_context_lease.py release`, the browser's renderer was wedged, and
`Target.disposeBrowserContext` never answered. `_calls()` had no timeout on `ws.recv()`, so
the lease script hung until the caller's 35-second subprocess limit killed it -- the
recovery designed to survive a dead target died at its first step, inside the lease.

Two properties pin that shut:
  1. `_calls` finishes or raises within its deadline, never hangs.
  2. `release` on a context that cannot be disposed still drops the lease row (ok:true with
     a note) -- the gc reaps the corpse later; keeping the row would hand the same dead
     context to every future acquire.
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


def test_release_of_an_undisposable_context_still_drops_the_row(monkeypatch, tmp_path):
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
    assert json.loads(leases_file.read_text(encoding="utf-8")) == {}


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


def test_acquire_keeps_held_context_after_one_transient_probe_miss(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    leases_file.write_text(json.dumps({
        "fundraiser": {
            "context_id": "live-context",
            "target_id": "live-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/live-target",
            "ts": 0,
            "token": "a" * 32,
            "generation": 1,
        }
    }), encoding="utf-8")
    answers = iter((False, True))
    monkeypatch.setattr(module, "target_responds", lambda *_: next(answers))
    monkeypatch.setattr(module.time, "sleep", lambda *_: None)

    result = module.acquire("fundraiser")

    assert result["reused"] is True
    assert result["target_id"] == "live-target"
    assert json.loads(leases_file.read_text(encoding="utf-8"))["fundraiser"]["target_id"] == "live-target"
