"""Fence browser-context leases so stale owners cannot tear down new work."""
import json
import os
import re
import stat
import subprocess
import sys
import textwrap
import threading
import types
from pathlib import Path

import pytest

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


def _install_flaky_dispose(monkeypatch, failures=1):
    calls = []
    state = {"contexts": 0, "targets": 0, "dispose_attempts": 0}

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
            elif method == "Target.disposeBrowserContext":
                state["dispose_attempts"] += 1
                if state["dispose_attempts"] <= failures:
                    raise RuntimeError("temporary CDP disconnect")
                results.append({})
            else:
                results.append({})
        return results

    monkeypatch.setattr(lease, "_calls", fake_calls)
    return calls, state


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
    assert re.fullmatch(r"[0-9a-f]{32}", first["token"])
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


def test_acquire_uses_full_128_bit_token_hex(monkeypatch, tmp_path):
    _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    token_sizes = []

    def token_hex(size):
        token_sizes.append(size)
        return "f" * 32

    def uuid4_must_not_be_used():
        raise AssertionError("uuid4 does not provide the required full 128 random bits")

    monkeypatch.setattr(
        lease, "secrets", types.SimpleNamespace(token_hex=token_hex), raising=False
    )
    monkeypatch.setattr(
        lease, "uuid", types.SimpleNamespace(uuid4=uuid4_must_not_be_used), raising=False
    )

    held = lease.acquire("gig", no_seed=True)

    assert held["token"] == "f" * 32
    assert token_sizes == [16]


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


def test_credentialless_release_refuses_a_fenced_lease(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    held = lease.acquire("gig", no_seed=True)
    before = list(calls)

    result = lease.release("gig")

    assert result["ok"] is False
    assert calls == before
    assert _read_lease(leases_path)["token"] == held["token"]


def test_credentialless_release_refuses_a_partially_fenced_lease(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "token": "a" * 32,
        "ts": 1.0,
        "heartbeat_at": 1.0,
    }
    _write_lease(leases_path, "gig", held, 1)

    result = lease.release("gig")

    assert result["ok"] is False
    assert calls == []
    assert _read_lease(leases_path) == held


def test_fenced_release_cannot_delete_a_replacement_seen_after_its_snapshot(
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
        target=lambda: result.update(lease.release("gig", old["token"], old["generation"])),
        daemon=True,
    )
    worker.start()
    assert snapshot_taken.wait(timeout=1)
    _write_lease(leases_path, "gig", replacement, 2)
    continue_release.set()
    worker.join(timeout=1)

    assert result["ok"] is False
    assert calls == []
    assert _read_lease(leases_path) == replacement


def test_corrupt_ledger_is_preserved_and_fails_closed(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    corrupt = "{ this is not valid json"
    leases_path.write_text(corrupt, encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        lease.acquire("gig", no_seed=True)

    assert leases_path.read_text(encoding="utf-8") == corrupt
    assert calls == []


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


def test_release_keeps_pending_lease_when_dispose_fails_and_retries(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    _calls, state = _install_flaky_dispose(monkeypatch)
    held = lease.acquire("gig", no_seed=True)

    failed = lease.release("gig", held["token"], held["generation"])
    pending = _read_lease(leases_path)

    assert failed["ok"] is False
    assert pending["dispose_pending"] is True
    assert pending["token"] == held["token"]
    assert lease.heartbeat("gig", held["token"], held["generation"])["ok"] is False
    assert lease.acquire("gig", no_seed=True)["ok"] is False

    retried = lease.release("gig", held["token"], held["generation"])

    assert retried["ok"] is True
    assert state["dispose_attempts"] == 2
    assert "gig" not in json.loads(leases_path.read_text(encoding="utf-8"))


def test_gc_keeps_pending_lease_when_dispose_fails_and_retries(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    _calls, state = _install_flaky_dispose(monkeypatch)
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

    failed = lease.gc(idle_min=1)
    pending = _read_lease(leases_path)

    assert failed["ok"] is False
    assert failed["reaped"] == []
    assert pending["dispose_pending"] is True
    assert "gig" in failed["still_held"]

    retried = lease.gc(idle_min=1)

    assert retried["ok"] is True
    assert retried["reaped"] == ["gig"]
    assert state["dispose_attempts"] == 2
    assert "gig" not in json.loads(leases_path.read_text(encoding="utf-8"))


def test_gc_finalizes_a_pending_lease_when_cdp_confirms_it_is_already_disposed(
    monkeypatch, tmp_path
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(lease.time, "time", lambda: 1_000.0)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1_000.0,
        "heartbeat_at": 1_000.0,
        "dispose_pending": True,
    }
    _write_lease(leases_path, "gig", held, 1)

    async def already_disposed(pairs):
        calls.extend(pairs)
        raise RuntimeError("Target.disposeBrowserContext: Browser context not found")

    monkeypatch.setattr(lease, "_calls", already_disposed)

    result = lease.gc(idle_min=45)

    assert result["ok"] is True
    assert result["reaped"] == ["gig"]
    assert calls[0][0] == "Target.disposeBrowserContext"
    assert "gig" not in json.loads(leases_path.read_text(encoding="utf-8"))


def test_ledger_rmw_is_serialized_across_processes(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1.0,
        "heartbeat_at": 1.0,
        "counter": 0,
    }
    _write_lease(leases_path, "gig", held, 1)
    worker = textwrap.dedent(
        """
        import os
        import sys
        import time

        sys.path.insert(0, os.environ["LEASE_SCRIPT_DIR"])
        import cdp_context_lease as lease

        for _ in range(8):
            with lease._ledger_lock():
                ledger = lease._read_ledger_locked()
                row = ledger["leases"]["gig"]
                value = row["counter"]
                time.sleep(0.01)
                row["counter"] = value + 1
                lease._save_ledger_locked(ledger)
        """
    )
    env = {
        **os.environ,
        "CLOAK_CONTEXT_LEASES_FILE": str(leases_path),
        "LEASE_SCRIPT_DIR": str(Path(__file__).parent),
    }
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", worker],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    for process in workers:
        _stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr.decode()

    assert _read_lease(leases_path)["counter"] == 16


def test_ledger_write_fsyncs_data_file_and_parent_directory(monkeypatch, tmp_path):
    _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    fsynced_kinds = []
    real_fsync = lease.os.fsync

    def recording_fsync(fd):
        fsynced_kinds.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        return real_fsync(fd)

    monkeypatch.setattr(lease.os, "fsync", recording_fsync)

    lease.acquire("gig", no_seed=True)

    assert False in fsynced_kinds
    assert True in fsynced_kinds


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
