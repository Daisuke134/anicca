"""D4: a holder killed with -9 must not linger in the lease ledger for up to idle_min.

Before this, gc() only reaped rows idle for idle_min minutes (default 45) -- the lease
row schema recorded no `pid` at all, so a crashed holder's row was indistinguishable from
a genuinely slow-but-alive one until the idle clock ran out. acquire()/heartbeat() now
stamp `pid` = os.getppid() (the calling shell/process that actually holds the lease) on
every successful call, and gc() reaps a row immediately if its recorded pid is confirmed
dead -- on top of, never instead of, the existing idle_min safety net. Missing/inconclusive
pid never triggers early reap (legacy rows, permission-denied cross-user pids, etc.).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parent / "cdp_context_lease.py"
    spec = importlib.util.spec_from_file_location("cdp_context_lease_pid_reap", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_leases(leases_file, leases):
    leases_file.write_text(json.dumps(leases), encoding="utf-8")


def _dead_pid():
    # Spawn and immediately reap a child so its pid is guaranteed dead but was real.
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_pid_alive_true_for_self():
    module = load_module()
    assert module._pid_alive(os.getpid()) is True


def test_pid_alive_false_for_a_reaped_child():
    module = load_module()
    assert module._pid_alive(_dead_pid()) is False


def test_pid_alive_none_for_missing_or_invalid():
    module = load_module()
    assert module._pid_alive(None) is None
    assert module._pid_alive(0) is None
    assert module._pid_alive("not-a-pid") is None


def test_acquire_stamps_pid_on_a_fresh_lease(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))

    async def create_ok(pairs, timeout=None):
        out = []
        for method, _ in pairs:
            if method == "Target.createBrowserContext":
                out.append({"browserContextId": "c1"})
            elif method == "Target.createTarget":
                out.append({"targetId": "t1"})
        return out

    monkeypatch.setattr(module, "_calls", create_ok)
    result = module.acquire("gig-task")

    assert result["pid"] == os.getppid()
    saved = json.loads(leases_file.read_text(encoding="utf-8"))
    assert saved["gig-task"]["pid"] == os.getppid()


def test_seed_cookies_prefers_live_browser_over_stale_vault(monkeypatch, tmp_path):
    module = load_module()
    vault = tmp_path / "auth-state.json"
    vault.write_text(json.dumps({"cookies": [{"name": "stale"}]}))
    monkeypatch.setenv("CLOAK_SESSION_VAULT_FILE", str(vault))

    async def live(pairs, timeout=None):
        if pairs[0][0] == "Target.getTargets":
            return [{"targetInfos": [{
                "type": "page", "url": "https://coconala.com/message",
                "browserContextId": "authenticated-context",
            }]}]
        assert pairs[0][1] == {"browserContextId": "authenticated-context"}
        return [{"cookies": [{"name": "current"}]}]

    monkeypatch.setattr(module, "_calls", live)
    assert module._seed_cookies() == [{"name": "current"}]


def test_gc_reaps_a_row_whose_pid_just_died_even_though_it_is_not_idle_stale(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    fresh_ts = int(time.time())  # NOT idle-stale -- only the dead pid should trigger reap
    _write_leases(leases_file, {
        "gig-task": {
            "context_id": "c1", "target_id": "t1",
            "ws": "ws://127.0.0.1:9222/devtools/page/t1",
            "ts": fresh_ts, "token": "a" * 32, "generation": 1,
            "pid": _dead_pid(),
        }
    })

    async def dispose_ok(pairs, timeout=None):
        return [{}]

    monkeypatch.setattr(module, "_calls", dispose_ok)
    result = module.gc(idle_min=45)

    assert result["reaped"] == ["gig-task"]
    assert json.loads(leases_file.read_text(encoding="utf-8")) == {}


def test_gc_does_not_reap_a_fresh_row_with_a_live_pid(monkeypatch, tmp_path):
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    _write_leases(leases_file, {
        "gig-task": {
            "context_id": "c1", "target_id": "t1",
            "ws": "ws://127.0.0.1:9222/devtools/page/t1",
            "ts": int(time.time()), "token": "a" * 32, "generation": 1,
            "pid": os.getpid(),
        }
    })

    result = module.gc(idle_min=45)

    assert result["reaped"] == []
    saved = json.loads(leases_file.read_text(encoding="utf-8"))
    assert saved["gig-task"]["context_id"] == "c1"


def test_gc_does_not_reap_a_legacy_row_missing_pid_before_idle_min(monkeypatch, tmp_path):
    # Rows written before this change have no pid field at all -- must fall back to the
    # unchanged idle_min-only behaviour, never treated as dead.
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    _write_leases(leases_file, {
        "gig-task": {
            "context_id": "c1", "target_id": "t1",
            "ws": "ws://127.0.0.1:9222/devtools/page/t1",
            "ts": int(time.time()), "token": "a" * 32, "generation": 1,
        }
    })

    result = module.gc(idle_min=45)

    assert result["reaped"] == []


def test_gc_does_not_reap_a_row_reacquired_by_a_live_pid_between_dispose_and_finalize(monkeypatch, tmp_path):
    # Same race the existing identity check covers, but for the pid-liveness path: a row
    # whose pid died was mid-dispose when a live process re-acquired the same task name and
    # refreshed both ts and pid. Finalize must re-read the CURRENT pid, not the stale one
    # captured at candidate-selection time, or a live lease gets destroyed underneath it.
    module = load_module()
    leases_file = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_file))
    dead = _dead_pid()
    _write_leases(leases_file, {
        "gig-task": {
            "context_id": "old-context", "target_id": "old-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/old-target",
            "ts": int(time.time()), "token": "a" * 32, "generation": 1,
            "pid": dead,
        }
    })

    async def dispose_then_reacquire(pairs, timeout=None):
        leases = module._leases()
        leases["gig-task"] = {
            "context_id": "old-context", "target_id": "old-target",
            "ws": "ws://127.0.0.1:9222/devtools/page/old-target",
            "ts": int(time.time()), "token": "b" * 32, "generation": 1,
            "pid": os.getpid(),  # live pid took over the same row via acquire's reuse path
        }
        module._save(leases)
        return [{}]

    monkeypatch.setattr(module, "_calls", dispose_then_reacquire)
    result = module.gc(idle_min=45)

    assert "gig-task" not in result["reaped"]
    saved = json.loads(leases_file.read_text(encoding="utf-8"))
    assert saved["gig-task"]["pid"] == os.getpid()
