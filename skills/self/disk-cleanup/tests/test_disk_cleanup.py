import errno
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import disk_cleanup  # noqa: E402
from disk_cleanup import (  # noqa: E402
    GiB,
    HostDiskGovernor,
    classify_tier,
)


@pytest.fixture(autouse=True)
def stub_bootstrap_health_for_governor_unit_tests(monkeypatch) -> None:
    monkeypatch.setattr(
        disk_cleanup,
        "_default_bootstrap_health",
        lambda _home, _state_dir: {"status": "not-applicable"},
    )


def test_tier_boundaries_use_bytes() -> None:
    assert classify_tier(20 * GiB) == "NORMAL"
    assert classify_tier(20 * GiB - 1) == "PREVENTIVE"
    assert classify_tier(11 * GiB) == "PREVENTIVE"
    assert classify_tier(11 * GiB - 1) == "PRESSURE"
    assert classify_tier(6 * GiB - 1) == "CRITICAL"
    assert classify_tier(3 * GiB - 1) == "ULTRA"


def test_closed_regenerable_artifact_is_reclaimed(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    candidate = tmp_path / "tmp" / "cfo-complete"
    candidate.mkdir(parents=True)
    (candidate / "payload").write_bytes(b"x" * 64)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(candidate.parent))
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=state,
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [{"path": candidate, "class": "ephemeral", "owner": "temporary-run", "discovery": "allowlisted"}]
    )

    assert result["reclaimed"] > 0
    assert not candidate.exists()
    receipt = json.loads((state / "last-receipt.json").read_text())
    assert receipt["protected_deletions"] == 0


def test_open_or_protected_artifact_is_preserved(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    open_candidate = tmp_path / "tmp" / "cfo-open"
    open_candidate.mkdir(parents=True)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(open_candidate.parent))
    protected = tmp_path / ".codex" / "logs.sqlite"
    protected.parent.mkdir()
    protected.write_bytes(b"x" * 64)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=state,
        lsof=lambda path: "open" if path == open_candidate else "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [
            {
                "path": open_candidate,
                "class": "ephemeral",
                "owner": "temporary-run",
                "discovery": "allowlisted",
            },
            {"path": protected, "class": "ephemeral", "owner": "unknown"},
        ]
    )

    assert result["reclaimed"] == 0
    assert open_candidate.exists()
    assert protected.exists()
    assert result["preserved"] == 2
    assert result["protected_deletions"] == 0


def test_protected_roots_never_enter_runtime_manifest(tmp_path: Path, monkeypatch) -> None:
    temporary = tmp_path / "tmp"
    disposable_candidate = temporary / "cfo-disposable"
    protected_candidates = []
    protected_paths = []
    for index, relative in enumerate(
        (
            ".claude/session.jsonl",
            ".codex/logs.sqlite",
            ".config/ai/config.json",
            ".openclaw/state/events.jsonl",
            ".openclaw/identity/device.json",
            ".openclaw/workspace/source.py",
            ".cloak/profile/Cookies",
            "anicca-rtdash/source.py",
            "anicca-monk-factory/source.py",
            "project/.git/config",
            "project/data.db",
            "project/credentials.json",
            "project/.env",
            "project/secret.key",
            "project/memory/fact",
            "project/publication-receipt.json",
        )
    ):
        candidate = temporary / f"cfo-protected-{index}"
        path = candidate / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("protected")
        protected_candidates.append(candidate)
        protected_paths.append(path)
    disposable_candidate.mkdir(parents=True)
    (disposable_candidate / "payload").write_text("regenerable")
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(temporary))
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [
            *[
                {"path": candidate, "class": "ephemeral", "owner": "temporary-run", "discovery": "allowlisted"}
                for candidate in protected_candidates
            ],
            {"path": disposable_candidate, "class": "ephemeral", "owner": "temporary-run", "discovery": "allowlisted"},
        ]
    )

    assert all(candidate.exists() for candidate in protected_candidates)
    assert all(path.exists() for path in protected_paths)
    assert not disposable_candidate.exists()
    assert result["preserved_reasons"] == {"protected_descendant": len(protected_candidates)}
    assert result["reclaimed"] > 0
    assert result["protected_deletions"] == 0


def test_effect_recheck_preserves_new_protected_descendant(tmp_path: Path, monkeypatch) -> None:
    temporary = tmp_path / "tmp"
    candidate = temporary / "cfo-race"
    candidate.mkdir(parents=True)
    (candidate / "payload").write_text("regenerable")
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(temporary))
    real_bytes = disk_cleanup._bytes

    def inject_protected_descendant(path: Path, **kwargs) -> int | None:
        (path / ".env").write_text("credential")
        return real_bytes(path, **kwargs)

    monkeypatch.setattr(disk_cleanup, "_bytes", inject_protected_descendant)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [{"path": candidate, "class": "ephemeral", "owner": "temporary-run", "discovery": "allowlisted"}]
    )

    assert candidate.exists()
    assert (candidate / ".env").exists()
    assert result["preserved_reasons"] == {"protected_descendant": 1}


def test_unproved_candidate_is_preserved(tmp_path: Path) -> None:
    candidate = tmp_path / "important"
    candidate.write_bytes(b"do-not-delete")
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep([{"path": candidate, "class": "ephemeral", "owner": "operator"}])

    assert candidate.exists()
    assert result["preserved_reasons"] == {"unknown_artifact": 1}


def test_lsof_stderr_is_probe_error(monkeypatch) -> None:
    class Result:
        returncode = 1
        stdout = ""
        stderr = "permission denied"

    monkeypatch.setattr(disk_cleanup.subprocess, "run", lambda *args, **kwargs: Result())
    assert disk_cleanup._default_lsof(Path("/tmp/unknown")) == "probe-error"


def test_cli_candidate_is_rejected(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "disk_cleanup.py"
    result = subprocess.run(
        [sys.executable, str(script), "--home", str(tmp_path), "--candidate", str(tmp_path / "important")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--candidate is disabled" in result.stderr or "--candidate is disabled" in result.stdout


def test_lock_is_atomic(tmp_path: Path) -> None:
    first = HostDiskGovernor(home=tmp_path, state_dir=tmp_path / "state")
    second = HostDiskGovernor(home=tmp_path, state_dir=tmp_path / "state")
    assert first.acquire_lock()
    assert not second.acquire_lock()
    first.release_lock()


def test_launchd_is_five_minutes_and_single_owner() -> None:
    plist = Path(__file__).parents[1] / "launchd" / "ai.anicca.life-manager-disk-cleanup.plist"
    text = plist.read_text()
    assert "<integer>300</integer>" in text
    assert "disk_cleanup.py" in text


def test_legacy_hourly_trigger_delegates_to_the_same_host_guard() -> None:
    script = Path(__file__).parents[1] / "legacy-disk-janitor.sh"
    text = script.read_text()
    assert "EMERGENCY_GUARD_FULL_PASS=1" in text
    assert "disk_cleanup.py" in text


def test_run_once_records_inventory_summary(tmp_path: Path, monkeypatch) -> None:
    def fake_inventory(**_kwargs):
        return {"coverage": {"mount_count": 1, "root_count": 2, "gaps": ["size-deferred"]}}

    monkeypatch.setattr(disk_cleanup, "collect_host_inventory", fake_inventory)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (12 * GiB, 100 * GiB),
    )

    result = governor.run_once()

    assert result["inventory_mode"] == "full"
    assert (tmp_path / "state" / "host-inventory-full.at").exists()
    assert result["inventory_mounts"] == 1
    assert result["inventory_roots"] == 2
    assert result["inventory_gaps"] == 1
    receipt = json.loads((tmp_path / "state" / "last-receipt.json").read_text())
    assert receipt["inventory_roots"] == 2


def test_run_once_global_budget_preserves_candidate_and_does_not_advance_full_marker(
    tmp_path: Path, monkeypatch
) -> None:
    clock = [0.0]
    candidate = tmp_path / "tmp" / "cfo-budget"
    candidate.mkdir(parents=True)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(candidate.parent))

    def discover_candidates() -> list[dict]:
        clock[0] = 105.0
        return [
            {
                "path": candidate,
                "class": "ephemeral",
                "owner": "temporary-run",
                "discovery": "allowlisted",
            }
        ]

    def fake_inventory(**kwargs):
        assert kwargs["budget_seconds"] == 0
        return {
            "coverage": {
                "mount_count": 1,
                "root_count": 1,
                "gaps": ["size-budget-exhausted:/tmp"],
            }
        }

    monkeypatch.setattr(disk_cleanup, "collect_host_inventory", fake_inventory)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: (_ for _ in ()).throw(AssertionError("lsof must not run after budget")),
        usage=lambda: (12 * GiB, 100 * GiB),
        clock=lambda: clock[0],
    )
    monkeypatch.setattr(governor, "discover_candidates", discover_candidates)

    result = governor.run_once()

    assert candidate.exists()
    assert result["preserved_reasons"] == {"probe-budget-exhausted": 1}
    assert not (tmp_path / "state" / "host-inventory-full.at").exists()


def test_run_once_rechecks_budget_after_lsof_before_reclaim(tmp_path: Path, monkeypatch) -> None:
    clock = [0.0]
    candidate = tmp_path / "tmp" / "cfo-lsof-budget"
    candidate.mkdir(parents=True)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(candidate.parent))

    def fake_inventory(**kwargs):
        assert kwargs["budget_seconds"] == 0
        return {"coverage": {"mount_count": 0, "root_count": 0, "gaps": ["size-budget-exhausted:/tmp"]}}

    monkeypatch.setattr(disk_cleanup, "collect_host_inventory", fake_inventory)

    def lsof(_path: Path) -> str:
        clock[0] = 106.0
        return "confirmed-closed"

    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lsof,
        usage=lambda: (12 * GiB, 100 * GiB),
        clock=lambda: clock[0],
    )
    monkeypatch.setattr(
        governor,
        "discover_candidates",
        lambda: [
            {
                "path": candidate,
                "class": "ephemeral",
                "owner": "temporary-run",
                "discovery": "allowlisted",
            }
        ],
    )

    result = governor.run_once()

    assert candidate.exists()
    assert result["preserved_reasons"] == {"probe-budget-exhausted": 1}
    assert not (tmp_path / "state" / "host-inventory-full.at").exists()


def test_bootstrap_health_failure_is_observation_only(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / "tmp" / "cfo-health-failure"
    candidate.mkdir(parents=True)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(candidate.parent))
    monkeypatch.setattr(
        disk_cleanup,
        "collect_host_inventory",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("inventory must not run")),
    )

    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        bootstrap_health=lambda: {
            "status": "failure",
            "error_code": "launchctl-141",
            "domain": "gui/501",
            "label": "ai.anicca.life-manager-disk-cleanup",
        },
        lsof=lambda _path: (_ for _ in ()).throw(AssertionError("lsof must not run")),
        usage=lambda: (12 * GiB, 100 * GiB),
    )
    monkeypatch.setattr(
        governor,
        "discover_candidates",
        lambda: [{"path": candidate, "class": "ephemeral", "owner": "temporary-run"}],
    )

    result = governor.run_once()

    assert result["reason"] == "gui-bootstrap-health-failure"
    assert result["evaluated"] == 0
    assert result["reclaimed"] == 0
    assert candidate.exists()
    receipt = json.loads((tmp_path / "state" / "last-receipt.json").read_text())
    assert receipt["reason"] == "gui-bootstrap-health-failure"
    assert receipt["health"]["error_code"] == "launchctl-141"
    assert not (tmp_path / "state" / "host-inventory-full.at").exists()


def test_exact_canary_reclaims_one_regenerable_path_and_replay_is_noop(
    tmp_path: Path, monkeypatch
) -> None:
    temp_root = tmp_path / "tmp"
    canary = temp_root / "cfo-life-manager-canary"
    canary.mkdir(parents=True)
    (canary / "payload").write_bytes(b"canary" * 1024)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(temp_root))

    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        bootstrap_health=lambda: {"status": "not-applicable"},
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (12 * GiB, 100 * GiB),
    )

    first = governor.run_canary(canary)
    replay = governor.run_canary(canary)

    assert first["canary_path"] == str(canary.resolve())
    assert first["removed"] is True
    assert first["before_bytes"] > 0
    assert first["after_bytes"] == 0
    assert first["reclaimed"] == first["before_bytes"]
    assert replay["reason"] == "canary-path-missing"
    assert replay["duplicate_effect"] == 0
    receipt = json.loads((tmp_path / "state" / "canary-last-receipt.json").read_text())
    assert receipt["canary_path"] == str(canary.resolve())
    assert receipt["initial"]["removed"] is True
    assert receipt["initial"]["reclaimed"] == first["before_bytes"]
    assert receipt["replay"]["duplicate_effect"] == 0


def test_exact_canary_rejects_path_outside_temp_root(tmp_path: Path) -> None:
    outside = tmp_path / "important"
    outside.write_text("preserve", encoding="utf-8")
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        bootstrap_health=lambda: {"status": "not-applicable"},
        lsof=lambda _path: (_ for _ in ()).throw(AssertionError("lsof must not run")),
        usage=lambda: (12 * GiB, 100 * GiB),
    )

    result = governor.run_canary(outside)

    assert result["reason"] == "canary-path-not-allowlisted"
    assert outside.exists()


@pytest.mark.parametrize("failure_stage", ["write", "fsync", "replace"])
def test_receipt_enospc_retries_atomic_commit_once_and_restores_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    target = state / "last-receipt.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    target.chmod(0o600)
    reserve = state / ".receipt-reserve"
    reserve.write_bytes(b"\0" * (1024 * 1024))
    reserve.chmod(0o600)

    replace_calls = 0
    write_failures = 0
    fsync_calls = 0
    real_replace = disk_cleanup.os.replace
    real_fdopen = disk_cleanup.os.fdopen
    real_fsync = disk_cleanup.os.fsync

    class WriteFailOnce:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return self.wrapped.__exit__(exc_type, exc, tb)

        def write(self, data):
            nonlocal write_failures
            if write_failures == 0:
                write_failures += 1
                raise OSError(errno.ENOSPC, "receipt write full")
            return self.wrapped.write(data)

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

    def fdopen(fd, *args, **kwargs):
        wrapped = real_fdopen(fd, *args, **kwargs)
        return WriteFailOnce(wrapped) if failure_stage == "write" and write_failures == 0 else wrapped

    def fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        if failure_stage == "fsync" and fsync_calls == 1:
            raise OSError(errno.ENOSPC, "receipt fsync full")
        return real_fsync(fd)

    def replace(src, dst):
        nonlocal replace_calls
        if Path(dst).name == "last-receipt.json":
            replace_calls += 1
        if failure_stage == "replace" and replace_calls == 1:
            raise OSError(errno.ENOSPC, "receipt replace full")
        return real_replace(src, dst)

    monkeypatch.setattr(disk_cleanup.os, "fdopen", fdopen)
    monkeypatch.setattr(disk_cleanup.os, "fsync", fsync)
    monkeypatch.setattr(disk_cleanup.os, "replace", replace)

    governor = HostDiskGovernor(home=tmp_path, state_dir=state)
    governor._receipt({"value": "new"})

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["value"] == "new"
    if failure_stage == "replace":
        assert replace_calls == 2
    elif failure_stage == "fsync":
        assert fsync_calls >= 3
    else:
        assert write_failures == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(state.glob(".last-receipt.json.*.tmp"))
    reserve_stat = reserve.stat()
    assert stat.S_ISREG(reserve_stat.st_mode)
    assert stat.S_IMODE(reserve_stat.st_mode) == 0o600
    assert reserve_stat.st_size == 1024 * 1024
    assert reserve_stat.st_blocks > 0


def test_receipt_other_errno_keeps_old_target_and_reserve_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    target = state / "last-receipt.json"
    old = b'{"old":true}\n'
    target.write_bytes(old)
    target.chmod(0o600)
    reserve = state / ".receipt-reserve"
    reserve.write_bytes(b"\0" * (1024 * 1024))
    reserve.chmod(0o600)
    replace_calls = 0
    real_replace = disk_cleanup.os.replace

    def replace(src, dst):
        nonlocal replace_calls
        replace_calls += 1
        raise OSError(errno.EIO, "receipt I/O failure")

    monkeypatch.setattr(disk_cleanup.os, "replace", replace)
    governor = HostDiskGovernor(home=tmp_path, state_dir=state)

    with pytest.raises(OSError) as caught:
        governor._receipt({"value": "new"})

    assert caught.value.errno == errno.EIO
    assert replace_calls == 1
    assert target.read_bytes() == old
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(state.glob(".last-receipt.json.*.tmp"))
    reserve_stat = reserve.stat()
    assert stat.S_ISREG(reserve_stat.st_mode)
    assert stat.S_IMODE(reserve_stat.st_mode) == 0o600
    assert reserve_stat.st_size == 1024 * 1024
    assert reserve_stat.st_blocks > 0


def _seed_receipt_reserve(state: Path) -> Path:
    reserve = state / ".receipt-reserve"
    reserve.write_bytes(b"\0" * (1024 * 1024))
    reserve.chmod(0o600)
    return reserve


def test_receipt_reserve_rejects_sparse_file_with_nonzero_blocks(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    reserve = state / ".receipt-reserve"
    with reserve.open("wb") as stream:
        stream.truncate(1024 * 1024)
        stream.seek(0)
        stream.write(b"x")
    reserve.chmod(0o600)
    sparse_before = reserve.stat()
    assert sparse_before.st_blocks > 0
    assert sparse_before.st_blocks * 512 < 1024 * 1024

    HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    reserve_after = reserve.stat()
    assert reserve_after.st_blocks * 512 >= 1024 * 1024
    assert len(reserve.read_bytes()) == 1024 * 1024


@pytest.mark.parametrize("failure_stage", ["write", "flush", "fsync", "readback"])
def test_receipt_reserve_build_failure_has_no_partial_final_or_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    real_fdopen = disk_cleanup.os.fdopen
    real_fsync = disk_cleanup.os.fsync
    real_read_bytes = Path.read_bytes
    failures = 0

    class FailingStream:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return self.wrapped.__exit__(exc_type, exc, tb)

        def write(self, data):
            nonlocal failures
            if failure_stage == "write" and failures == 0:
                failures += 1
                raise OSError(errno.EIO, "reserve write failure")
            return self.wrapped.write(data)

        def flush(self):
            nonlocal failures
            if failure_stage == "flush" and failures == 0:
                failures += 1
                raise OSError(errno.EIO, "reserve flush failure")
            return self.wrapped.flush()

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

    def fdopen(fd, *args, **kwargs):
        return FailingStream(real_fdopen(fd, *args, **kwargs))

    def fsync(fd):
        nonlocal failures
        if failure_stage == "fsync" and failures == 0:
            failures += 1
            raise OSError(errno.EIO, "reserve fsync failure")
        return real_fsync(fd)

    def read_bytes(path):
        nonlocal failures
        if failure_stage == "readback" and path.name.startswith(".receipt-reserve") and failures == 0:
            failures += 1
            raise OSError(errno.EIO, "reserve readback failure")
        return real_read_bytes(path)

    monkeypatch.setattr(disk_cleanup.os, "fdopen", fdopen)
    monkeypatch.setattr(disk_cleanup.os, "fsync", fsync)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)

    with pytest.raises(OSError):
        HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    assert not (state / ".receipt-reserve").exists()
    assert not list(state.glob(".receipt-reserve.*.tmp"))
    assert not list(state.glob(".last-receipt.json.*.tmp"))


def test_receipt_retry_reserve_recreate_fsync_failure_raises_after_commit_without_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    reserve = _seed_receipt_reserve(state)
    target = state / "last-receipt.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    target.chmod(0o600)
    real_replace = disk_cleanup.os.replace
    real_fdopen = disk_cleanup.os.fdopen
    real_fsync = disk_cleanup.os.fsync
    reserve_fd = None
    replace_calls = 0

    class TrackReserveStream:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return self.wrapped.__exit__(exc_type, exc, tb)

        def write(self, data):
            nonlocal reserve_fd
            result = self.wrapped.write(data)
            if len(data) >= 1024 * 1024:
                reserve_fd = self.wrapped.fileno()
            return result

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

    def fdopen(fd, *args, **kwargs):
        return TrackReserveStream(real_fdopen(fd, *args, **kwargs))

    def fsync(fd):
        if reserve_fd is not None and fd == reserve_fd:
            raise OSError(errno.EIO, "reserve recreate fsync failure")
        return real_fsync(fd)

    def replace(src, dst):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError(errno.ENOSPC, "first receipt commit full")
        return real_replace(src, dst)

    monkeypatch.setattr(disk_cleanup.os, "fdopen", fdopen)
    monkeypatch.setattr(disk_cleanup.os, "fsync", fsync)
    monkeypatch.setattr(disk_cleanup.os, "replace", replace)

    with pytest.raises(OSError):
        HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    assert replace_calls == 2
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == "new"
    assert not reserve.exists()
    assert not list(state.glob(".receipt-reserve.*.tmp"))


def test_receipt_parent_dir_fsync_error_is_best_effort_and_does_not_consume_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    reserve = _seed_receipt_reserve(state)
    real_fsync = disk_cleanup.os.fsync
    dir_fsync_calls = 0

    def fsync(fd):
        nonlocal dir_fsync_calls
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            dir_fsync_calls += 1
            raise OSError(errno.EIO, "parent directory fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(disk_cleanup.os, "fsync", fsync)
    HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    assert dir_fsync_calls == 1
    assert json.loads((state / "last-receipt.json").read_text(encoding="utf-8"))["value"] == "new"
    assert reserve.exists()
    reserve_stat = reserve.stat()
    assert stat.S_IMODE(reserve_stat.st_mode) == 0o600
    assert reserve_stat.st_blocks * 512 >= 1024 * 1024


def test_receipt_second_enospc_has_one_retry_old_target_and_no_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    reserve = _seed_receipt_reserve(state)
    target = state / "last-receipt.json"
    old = b'{"old":true}\n'
    target.write_bytes(old)
    target.chmod(0o600)
    replace_calls = 0

    def replace(_src, _dst):
        nonlocal replace_calls
        replace_calls += 1
        raise OSError(errno.ENOSPC, "receipt full")

    monkeypatch.setattr(disk_cleanup.os, "replace", replace)
    with pytest.raises(OSError):
        HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    assert replace_calls == 2
    assert target.read_bytes() == old
    assert not reserve.exists()
    assert not list(state.glob(".last-receipt.json.*.tmp"))


def test_receipt_payload_over_64k_is_rejected_without_state_change(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    reserve = _seed_receipt_reserve(state)
    target = state / "last-receipt.json"
    old = b'{"old":true}\n'
    target.write_bytes(old)
    target.chmod(0o600)

    with pytest.raises(ValueError):
        HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "x" * 70000})

    assert target.read_bytes() == old
    assert reserve.exists()
    assert stat.S_IMODE(reserve.stat().st_mode) == 0o600
    assert reserve.stat().st_blocks * 512 >= 1024 * 1024
    assert not list(state.glob(".last-receipt.json.*.tmp"))


def test_receipt_replace_fd_reuse_does_not_close_unrelated_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    _seed_receipt_reserve(state)
    real_replace = disk_cleanup.os.replace
    retained_fd: int | None = None

    def replace(src, dst):
        nonlocal retained_fd
        if Path(dst).name == "last-receipt.json":
            retained_fd = os.open(os.devnull, os.O_RDONLY)
        return real_replace(src, dst)

    monkeypatch.setattr(disk_cleanup.os, "replace", replace)
    HostDiskGovernor(home=tmp_path, state_dir=state)._receipt({"value": "new"})

    assert retained_fd is not None
    try:
        os.fstat(retained_fd)
    finally:
        os.close(retained_fd)
