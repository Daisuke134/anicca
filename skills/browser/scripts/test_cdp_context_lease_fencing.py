"""Fence browser-context leases so stale owners cannot tear down new work."""
import json
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cdp_context_lease as lease  # noqa: E402


def _install_fake_cdp(monkeypatch):
    calls = []
    state = {"contexts": 0, "targets": 0}

    async def fake_calls(pairs):
        calls.extend(pairs)
        results = []
        for method, _params in pairs:
            if method == "Target.createBrowserContext":
                state["contexts"] += 1
                results.append({"browserContextId": f"context-{state['contexts']}"})
            elif method == "Target.createTarget":
                state["targets"] += 1
                results.append({"targetId": f"target-{state['targets']}"})
            else:
                results.append({})
        return results

    monkeypatch.setattr(lease, "_calls", fake_calls)
    return calls


def _set_lease_path(monkeypatch, tmp_path):
    leases_path = tmp_path / "leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_path))
    return leases_path


def _read_lease(leases_path, task="gig"):
    return json.loads(leases_path.read_text(encoding="utf-8"))[task]


def _write_lease(leases_path, task, held, generation):
    leases_path.parent.mkdir(parents=True, exist_ok=True)
    leases_path.write_text(
        json.dumps(
            {
                task: held,
                "_lease_fence_meta": {"generations": {task: generation}},
            }
        ),
        encoding="utf-8",
    )


def test_acquire_reuse_refreshes_heartbeat_and_next_generation(monkeypatch, tmp_path):
    _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    clock = iter((100.0, 101.0, 102.0))
    monkeypatch.setattr(lease.time, "time", lambda: next(clock))

    first = lease.acquire("gig", no_seed=True)
    reused = lease.acquire("gig", no_seed=True)

    assert first["reused"] is False
    assert len(first["token"]) == 32
    assert first["generation"] == 1
    assert first["heartbeat_at"] == 100.0
    assert reused["reused"] is True
    assert reused["token"] == first["token"]
    assert reused["generation"] == 1
    assert reused["heartbeat_at"] == 101.0
    assert _read_lease(tmp_path / "leases.json")["heartbeat_at"] == 101.0
    assert [method for method, _params in calls].count("Target.createBrowserContext") == 1

    assert lease.release("gig", first["token"], first["generation"])["ok"] is True
    second = lease.acquire("gig", no_seed=True)

    assert second["generation"] == 2
    assert second["token"] != first["token"]


def test_heartbeat_requires_exact_current_identity(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    monkeypatch.setattr(lease.time, "time", lambda: 50.0)
    held = lease.acquire("gig", no_seed=True)
    monkeypatch.setattr(lease.time, "time", lambda: 75.0)

    rejected = lease.heartbeat("gig", "stale-token", held["generation"])
    accepted = lease.heartbeat("gig", held["token"], held["generation"])

    assert rejected["ok"] is False
    assert accepted["ok"] is True
    assert accepted["heartbeat_at"] == 75.0
    assert _read_lease(leases_path)["heartbeat_at"] == 75.0


def test_heartbeat_rejects_boolean_generation(monkeypatch, tmp_path):
    _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    held = lease.acquire("gig", no_seed=True)

    result = lease.heartbeat("gig", held["token"], True)

    assert result["ok"] is False


def test_fenced_release_rejects_stale_identity_without_disposing_current_lease(
    monkeypatch, tmp_path
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    first = lease.acquire("gig", no_seed=True)
    assert lease.release("gig", first["token"], first["generation"])["ok"] is True
    second = lease.acquire("gig", no_seed=True)
    before = list(calls)

    stale = lease.release("gig", first["token"], first["generation"])

    assert stale["ok"] is False
    assert calls == before
    assert _read_lease(leases_path)["token"] == second["token"]
    assert _read_lease(leases_path)["generation"] == second["generation"]


def test_legacy_release_cannot_delete_a_replacement_seen_after_its_snapshot(
    monkeypatch, tmp_path
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    old = {
        "context_id": "context-old",
        "target_id": "target-old",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1.0,
        "heartbeat_at": 1.0,
    }
    replacement = {
        "context_id": "context-new",
        "target_id": "target-new",
        "token": "b" * 32,
        "generation": 2,
        "ts": 2.0,
        "heartbeat_at": 2.0,
    }
    _write_lease(leases_path, "gig", old, 1)
    snapshot_taken = threading.Event()
    continue_release = threading.Event()
    original_lock_path = lease._operation_lock_path

    def pause_before_operation_lock(target_id):
        snapshot_taken.set()
        assert continue_release.wait(timeout=1)
        return original_lock_path(target_id)

    monkeypatch.setattr(lease, "_operation_lock_path", pause_before_operation_lock)
    result = {}
    worker = threading.Thread(
        target=lambda: result.update(lease.release("gig")), daemon=True
    )
    worker.start()
    assert snapshot_taken.wait(timeout=1)
    _write_lease(leases_path, "gig", replacement, 2)
    continue_release.set()
    worker.join(timeout=1)

    assert result["ok"] is False
    assert calls == []
    assert _read_lease(leases_path) == replacement


def test_gc_does_not_reap_a_lease_refreshed_after_stale_snapshot(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    monkeypatch.setattr(lease.time, "time", lambda: 1_000.0)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "token": "a" * 32,
        "generation": 1,
        "ts": 0.0,
        "heartbeat_at": 0.0,
    }
    _write_lease(leases_path, "gig", held, 1)
    snapshot_taken = threading.Event()
    continue_gc = threading.Event()
    original_lock_path = lease._operation_lock_path

    def pause_before_operation_lock(target_id):
        snapshot_taken.set()
        assert continue_gc.wait(timeout=1)
        return original_lock_path(target_id)

    monkeypatch.setattr(lease, "_operation_lock_path", pause_before_operation_lock)
    result = {}
    worker = threading.Thread(target=lambda: result.update(lease.gc(idle_min=1)), daemon=True)
    worker.start()
    assert snapshot_taken.wait(timeout=1)
    held["heartbeat_at"] = 1_000.0
    _write_lease(leases_path, "gig", held, 1)
    continue_gc.set()
    worker.join(timeout=1)

    assert result["reaped"] == []
    assert calls == []
    assert _read_lease(leases_path)["heartbeat_at"] == 1_000.0


def test_gc_does_not_reap_a_replacement_generation(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    monkeypatch.setattr(lease.time, "time", lambda: 1_000.0)
    old = {
        "context_id": "context-old",
        "target_id": "target-old",
        "token": "a" * 32,
        "generation": 1,
        "ts": 0.0,
        "heartbeat_at": 0.0,
    }
    replacement = {
        "context_id": "context-new",
        "target_id": "target-new",
        "token": "b" * 32,
        "generation": 2,
        "ts": 0.0,
        "heartbeat_at": 0.0,
    }
    _write_lease(leases_path, "gig", old, 1)
    snapshot_taken = threading.Event()
    continue_gc = threading.Event()
    original_lock_path = lease._operation_lock_path

    def pause_before_operation_lock(target_id):
        snapshot_taken.set()
        assert continue_gc.wait(timeout=1)
        return original_lock_path(target_id)

    monkeypatch.setattr(lease, "_operation_lock_path", pause_before_operation_lock)
    result = {}
    worker = threading.Thread(target=lambda: result.update(lease.gc(idle_min=1)), daemon=True)
    worker.start()
    assert snapshot_taken.wait(timeout=1)
    _write_lease(leases_path, "gig", replacement, 2)
    continue_gc.set()
    worker.join(timeout=1)

    assert result["reaped"] == []
    assert calls == []
    assert _read_lease(leases_path) == replacement


def test_release_rejects_partial_identity_fail_closed(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    held = lease.acquire("gig", no_seed=True)
    before = list(calls)

    result = lease.release("gig", token=held["token"])

    assert result["ok"] is False
    assert calls == before
    assert _read_lease(leases_path)["token"] == held["token"]


def test_cli_heartbeat_and_partial_release_identity(monkeypatch, capsys):
    called = []

    def fake_heartbeat(task, token, generation):
        called.append((task, token, generation))
        return {"ok": True}

    monkeypatch.setattr(lease, "heartbeat", fake_heartbeat, raising=False)

    assert lease.main(["heartbeat", "gig", "--token", "tok", "--generation", "4"]) == 0
    assert called == [("gig", "tok", 4)]
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert lease.main(["release", "gig", "--token", "tok"]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False
