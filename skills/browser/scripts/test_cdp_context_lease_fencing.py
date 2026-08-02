"""Fence browser-context leases so stale owners cannot tear down new work."""
import json
import os
import re
import signal
import stat
import subprocess
import sys
import textwrap
import threading
import time
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


def _valid_held(**overrides):
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "ws": "ws://127.0.0.1/devtools/page/target-1",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1.0,
        "heartbeat_at": 1.0,
    }
    held.update(overrides)
    return held


def _shell_function(source, name, next_name):
    start = source.index(f"{name}(){{")
    end = source.index(f"\n{next_name}(){{", start)
    return source[start:end]


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


@pytest.mark.parametrize("failure_stage", ["seed", "target"])
def test_acquire_disposes_created_context_when_setup_fails(
    monkeypatch, tmp_path, failure_stage
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = []
    if failure_stage == "seed":
        vault_path = tmp_path / "auth-state.json"
        vault_path.write_text('{"cookies":[{"name":"sid"}]}', encoding="utf-8")
        monkeypatch.setenv("CLOAK_SESSION_VAULT_FILE", str(vault_path))

    async def fake_calls(pairs):
        calls.extend(pairs)
        if pairs[0][0] == "Target.createBrowserContext":
            return [{"browserContextId": "context-1"}]
        for method, _params in pairs:
            if method == "Storage.setCookies" and failure_stage == "seed":
                raise RuntimeError("cookie seed failed")
            if method == "Target.createTarget" and failure_stage == "target":
                raise RuntimeError("target creation failed")
        return [{} for _method, _params in pairs]

    monkeypatch.setattr(lease, "_calls", fake_calls)

    with pytest.raises(RuntimeError):
        lease.acquire("gig", no_seed=failure_stage == "target")

    assert (
        "Target.disposeBrowserContext",
        {"browserContextId": "context-1"},
    ) in calls
    assert not leases_path.exists()


def test_acquire_disposes_untracked_context_when_ledger_write_fails(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    operation_targets = []
    original_operation_lock_path = lease._operation_lock_path

    def record_operation_lock(target_id):
        operation_targets.append(target_id)
        return original_operation_lock_path(target_id)

    def write_fails(_ledger):
        raise OSError("ledger write failed")

    monkeypatch.setattr(lease, "_operation_lock_path", record_operation_lock)
    monkeypatch.setattr(lease, "_save_ledger_locked", write_fails)

    with pytest.raises(OSError, match="ledger write failed"):
        lease.acquire("gig", no_seed=True)

    assert (
        "Target.disposeBrowserContext",
        {"browserContextId": "context-1"},
    ) in calls
    assert operation_targets == ["target-1"]
    assert not leases_path.exists()


def test_acquire_keeps_exact_durable_candidate_after_directory_fsync_error(
    monkeypatch, tmp_path
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    real_fsync = lease.os.fsync

    def fail_after_directory_replace(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            real_fsync(fd)
            raise OSError("directory fsync interrupted")
        return real_fsync(fd)

    monkeypatch.setattr(lease.os, "fsync", fail_after_directory_replace)

    with pytest.raises(OSError, match="directory fsync interrupted"):
        lease.acquire("gig", no_seed=True)

    durable = _read_lease(leases_path)
    assert durable["context_id"] == "context-1"
    assert durable["target_id"] == "target-1"
    assert [method for method, _params in calls].count(
        "Target.disposeBrowserContext"
    ) == 0


@pytest.mark.parametrize(
    "invalid_row",
    [
        _valid_held(context_id=""),
        _valid_held(target_id=""),
        _valid_held(ws=""),
        _valid_held(ts="not-a-timestamp"),
        _valid_held(ts=float("nan")),
        _valid_held(ts=float("inf")),
        _valid_held(ts=-1),
        _valid_held(heartbeat_at="not-a-timestamp"),
        _valid_held(heartbeat_at=float("nan")),
        _valid_held(heartbeat_at=float("inf")),
        _valid_held(heartbeat_at=-1),
        _valid_held(dispose_pending="yes"),
        _valid_held(token=""),
        _valid_held(generation=0),
        {key: value for key, value in _valid_held().items() if key != "generation"},
        {key: value for key, value in _valid_held().items() if key != "token"},
    ],
)
def test_invalid_ledger_row_blocks_new_acquire_without_write_or_cdp(
    monkeypatch, tmp_path, invalid_row
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = _install_fake_cdp(monkeypatch)
    _write_lease(leases_path, "other", invalid_row, 1)
    before = leases_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        lease.acquire("gig", no_seed=True)

    assert leases_path.read_text(encoding="utf-8") == before
    assert calls == []


def test_acquire_upgrades_a_complete_legacy_row(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    legacy = _valid_held()
    del legacy["token"]
    del legacy["generation"]
    _write_lease(leases_path, "gig", legacy, 1)

    upgraded = lease.acquire("gig", no_seed=True)

    assert upgraded["ok"] is True
    assert upgraded["reused"] is True
    assert re.fullmatch(r"[0-9a-f]{32}", upgraded["token"])
    assert upgraded["generation"] == 2


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
        "ws": "ws://127.0.0.1/devtools/page/target-old",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1.0,
        "heartbeat_at": 1.0,
    }
    replacement = {
        "context_id": "context-new",
        "target_id": "target-new",
        "ws": "ws://127.0.0.1/devtools/page/target-new",
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
        "ws": "ws://127.0.0.1/devtools/page/target-1",
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
        "ws": "ws://127.0.0.1/devtools/page/target-old",
        "token": "a" * 32,
        "generation": 1,
        "ts": 0.0,
        "heartbeat_at": 0.0,
    }
    replacement = {
        "context_id": "context-new",
        "target_id": "target-new",
        "ws": "ws://127.0.0.1/devtools/page/target-new",
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
        "ws": "ws://127.0.0.1/devtools/page/target-1",
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


@pytest.mark.parametrize(
    "dispose_error",
    [
        "Target.disposeBrowserContext: Browser context not found",
        "Target.disposeBrowserContext: Failed to find context with id context-1",
    ],
)
def test_gc_finalizes_a_pending_lease_when_cdp_confirms_it_is_already_disposed(
    monkeypatch, tmp_path, dispose_error
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(lease.time, "time", lambda: 1_000.0)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "ws": "ws://127.0.0.1/devtools/page/target-1",
        "token": "a" * 32,
        "generation": 1,
        "ts": 1_000.0,
        "heartbeat_at": 1_000.0,
        "dispose_pending": True,
    }
    _write_lease(leases_path, "gig", held, 1)

    async def already_disposed(pairs):
        calls.extend(pairs)
        raise RuntimeError(dispose_error)

    monkeypatch.setattr(lease, "_calls", already_disposed)

    result = lease.gc(idle_min=45)

    assert result["ok"] is True
    assert result["reaped"] == ["gig"]
    assert calls[0][0] == "Target.disposeBrowserContext"
    assert "gig" not in json.loads(leases_path.read_text(encoding="utf-8"))


def test_release_finalizes_when_chromium_reports_failed_to_find_context_id(
    monkeypatch, tmp_path
):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    _install_fake_cdp(monkeypatch)
    held = lease.acquire("gig", no_seed=True)

    async def already_disposed(_pairs):
        raise RuntimeError(
            "Target.disposeBrowserContext: Failed to find context with id context-1"
        )

    monkeypatch.setattr(lease, "_calls", already_disposed)

    released = lease.release("gig", held["token"], held["generation"])

    assert released["ok"] is True
    assert "gig" not in json.loads(leases_path.read_text(encoding="utf-8"))


def test_ledger_rmw_is_serialized_across_processes(monkeypatch, tmp_path):
    leases_path = _set_lease_path(monkeypatch, tmp_path)
    held = {
        "context_id": "context-1",
        "target_id": "target-1",
        "ws": "ws://127.0.0.1/devtools/page/target-1",
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


@pytest.mark.parametrize(
    ("relative_path", "lease_prefix"),
    [
        ("skills/earn/gig/gig_pass.sh", "GIG_LEASE"),
        ("skills/earn/clip/clip_daily.sh", "CLIP_LEASE"),
        ("skills/earn/clip/clip_pass.sh", "CLIP_LEASE"),
    ],
)
def test_shell_parse_keeps_owned_fence_for_cleanup_when_ws_is_invalid(
    tmp_path, relative_path, lease_prefix
):
    root = Path(__file__).resolve().parents[3]
    source = (root / relative_path).read_text(encoding="utf-8")
    parse_lease = _shell_function(source, "parse_lease", "heartbeat_lease")
    release_lease = _shell_function(
        source, "release_lease", "lease_heartbeat_loop"
    )
    calls_path = tmp_path / "lease-calls.txt"
    lease_cli = tmp_path / "lease-cli.sh"
    lease_cli.write_text(
        "import os\nimport sys\n"
        "open(os.environ['HARNESS_CALLS'], 'w', encoding='utf-8').write("
        "' '.join(sys.argv[1:]) + '\\n')\n",
        encoding="utf-8",
    )
    lease_cli.chmod(0o755)
    malformed_owned = json.dumps(
        {"ok": True, "ws": 7, "token": "owned-token", "generation": 7}
    )
    shell = textwrap.dedent(
        f"""\
        set -uo pipefail
        {parse_lease}
        {release_lease}
        {lease_prefix}="shell-parse"
        {lease_prefix}_WS=""
        {lease_prefix}_TOKEN=""
        {lease_prefix}_GENERATION=""
        LEASE_SCRIPT="$HARNESS_LEASE_SCRIPT"
        if parse_lease "$HARNESS_LEASE_JSON"; then
          exit 19
        fi
        release_lease
        """
    )
    completed = subprocess.run(
        ["bash", "-c", shell],
        env={
            **os.environ,
            "HARNESS_CALLS": str(calls_path),
            "HARNESS_LEASE_JSON": malformed_owned,
            "HARNESS_LEASE_SCRIPT": str(lease_cli),
        },
        text=True,
        capture_output=True,
        timeout=5,
    )

    assert completed.returncode == 0, completed.stderr
    assert calls_path.read_text(encoding="utf-8") == (
        "release shell-parse --token owned-token --generation 7\n"
    )


def test_heartbeat_failure_waits_for_foreground_child_before_fenced_release(tmp_path):
    root = Path(__file__).resolve().parents[3]
    gig_pass = root / "skills/earn/gig/gig_pass.sh"
    functions = tmp_path / "gig-functions.sh"
    functions.write_text(
        gig_pass.read_text(encoding="utf-8").split(
            "# ── deterministic prelude", 1
        )[0],
        encoding="utf-8",
    )
    events_path = tmp_path / "events.txt"
    child_pid_path = tmp_path / "child.pid"
    lease_cli = tmp_path / "lease-cli.sh"
    agent = tmp_path / "agent.sh"
    lease_cli.write_text(
        textwrap.dedent(
            """\
            import os
            import sys

            command = sys.argv[1]
            if command == "heartbeat":
                child_pid_path = os.environ["HARNESS_CHILD_PID"]
                raise SystemExit(
                    1 if os.path.exists(child_pid_path) and os.path.getsize(child_pid_path) else 0
                )
            if command == "release":
                with open(os.environ["HARNESS_CHILD_PID"], encoding="utf-8") as handle:
                    child_pid = int(handle.read())
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    event = "release_after_child_exit"
                else:
                    event = "release_while_child_alive"
                with open(os.environ["HARNESS_EVENTS"], "a", encoding="utf-8") as handle:
                    handle.write(event + "\\n")
                raise SystemExit(0)
            raise SystemExit(64)
            """
        ),
        encoding="utf-8",
    )
    agent.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "$$" > "$HARNESS_CHILD_PID"
            trap 'echo child_exit >> "$HARNESS_EVENTS"; exit 0' TERM INT
            while :; do /bin/sleep 0.02; done
            """
        ),
        encoding="utf-8",
    )
    lease_cli.chmod(0o755)
    agent.chmod(0o755)
    harness = textwrap.dedent(
        """\
        set -uo pipefail
        source "$HARNESS_GIG_FUNCTIONS"
        LEASE_SCRIPT="$HARNESS_LEASE_SCRIPT"
        CLAUDE="$HARNESS_AGENT"
        GIG_LEASE="gig-harness"
        GIG_LEASE_WS="ws://harness"
        GIG_LEASE_TOKEN="harness-token"
        GIG_LEASE_GENERATION=1
        LEASE_HEARTBEAT_SECONDS=0.02
        LOCKD="$HARNESS_LOCK"
        mkdir -p "$LOCKD"
        trap cleanup EXIT
        if declare -F install_lease_signal_handlers >/dev/null; then
          install_lease_signal_handlers
        fi
        start_lease_heartbeat
        step "harness" "wait for heartbeat failure"
        """
    )
    completed = subprocess.Popen(
        ["bash", "-c", harness],
        env={
            **os.environ,
            "HARNESS_AGENT": str(agent),
            "HARNESS_CHILD_PID": str(child_pid_path),
            "HARNESS_EVENTS": str(events_path),
            "HARNESS_GIG_FUNCTIONS": str(functions),
            "HARNESS_LEASE_SCRIPT": str(lease_cli),
            "HARNESS_LOCK": str(tmp_path / "lock"),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        completed.wait(timeout=5)
        stderr = ""
    except subprocess.TimeoutExpired:
        completed.kill()
        completed.wait(timeout=1)
        pytest.fail("launcher did not exit after its heartbeat failed")
    finally:
        if child_pid_path.exists():
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    assert events_path.exists(), stderr
    events = events_path.read_text(encoding="utf-8")
    assert completed.returncode != 0, stderr
    assert "release_after_child_exit" in events
    assert "release_while_child_alive" not in events


def test_owned_callers_release_the_exact_fence_credentials():
    root = Path(__file__).resolve().parents[3]
    caller_paths = [
        "skills/browser/SKILL.md",
        "skills/earn/gig/gig_pass.sh",
        "skills/earn/gig/GIG_PASS_RUNBOOK.md",
        "skills/earn/clip/clip_daily.sh",
        "skills/earn/clip/clip_pass.sh",
        "skills/earn/clip/clip-cli.sh",
        "skills/earn/video/video-cli.sh",
    ]
    release_prefix = re.compile(
        r"(?:cdp_context_lease\.py|LEASE_SCRIPT)[\"']?\s+release\b"
    )
    fenced_release = re.compile(
        r"(?:cdp_context_lease\.py|LEASE_SCRIPT)[\"']?\s+release\s+\S+"
        r"\s+--token(?:\s|=)\S+\s+--generation(?:\s|=)\S+"
    )

    for relative_path in caller_paths:
        source = (root / relative_path).read_text()
        releases = list(release_prefix.finditer(source))
        assert releases, relative_path
        for release in releases:
            assert fenced_release.match(source, release.start()), relative_path
