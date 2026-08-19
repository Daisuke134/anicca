from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path


GIG_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = GIG_ROOT / "scripts" / "gig_disk_guard.py"
MANIFEST_PATH = GIG_ROOT / "config" / "launchd-jobs.json"


def _load_guard():
    spec = importlib.util.spec_from_file_location("gig_disk_guard_test", GUARD_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_reply_detector():
    path = GIG_ROOT / "scripts" / "reply_detector.py"
    spec = importlib.util.spec_from_file_location("gig_reply_detector_disk_guard_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_byte_under_threshold_writes_receipt_and_never_execs(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES - 1),
    )

    def unexpected_exec(*_args, **_kwargs):
        raise AssertionError("child must not execute with low disk headroom")

    monkeypatch.setattr(guard.os, "execvpe", unexpected_exec)

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    output = json.loads(capsys.readouterr().out)
    receipt_path = tmp_path / "state" / "disk-headroom.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert output == receipt
    assert receipt == {
        "available_bytes": guard.REQUIRED_BYTES - 1,
        "effect": 0,
        "failed": 1,
        "readback": 0,
        "reason": "disk_headroom_low",
        "required_bytes": guard.REQUIRED_BYTES,
        "status": "failed",
    }


def test_exact_threshold_execs_remaining_argv_and_environment_exactly(tmp_path, monkeypatch):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("GIG_DISK_GUARD_SENTINEL", "kept")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES),
    )
    calls = []
    monkeypatch.setattr(guard.os, "execvpe", lambda *args: calls.append(args))

    child_argv = ["/opt/homebrew/bin/python3", "/release/lane.py", "--flag", "value"]
    assert guard.main(child_argv) == 0

    assert calls == [(child_argv[0], child_argv, os.environ)]


def test_disk_measurement_exception_fails_closed_without_exec(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(guard.shutil, "disk_usage", lambda _path: (_ for _ in ()).throw(OSError("no stat")))
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("child must not execute when disk headroom is unknown")
    ))

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    receipt = json.loads(capsys.readouterr().out)
    assert receipt == {
        "effect": 0,
        "failed": 1,
        "readback": 0,
        "reason": "disk_headroom_unavailable",
        "required_bytes": guard.REQUIRED_BYTES,
        "status": "failed",
    }


def test_receipt_fsyncs_parent_directory_after_atomic_replace(tmp_path, monkeypatch):
    guard = _load_guard()
    fsynced = []
    closed = []
    original_close = guard.os.close

    monkeypatch.setattr(guard.os, "fsync", lambda fd: fsynced.append(fd))
    monkeypatch.setattr(
        guard.os, "close",
        lambda fd: (closed.append(fd), original_close(fd))[1],
    )

    guard._fsync_directory(tmp_path)

    assert len(fsynced) == 1
    assert len(closed) == 1


def test_low_headroom_skips_probe_worker_reconcile_and_sqlite(tmp_path, monkeypatch):
    detector = _load_reply_detector()
    args = SimpleNamespace(
        database=tmp_path / "supervisor.sqlite3",
        manifest=GIG_ROOT / "config" / "connectors" / "coconala.json",
        poll_seconds=0.01,
        workers=2,
        reconcile_seconds=0.01,
    )
    stop = detector.asyncio.Event()
    calls = {"probe": 0, "worker": 0, "reconcile": 0}

    monkeypatch.setattr(detector, "disk_headroom_ok", lambda: False)

    class UnexpectedSQLite:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("low headroom must not initialize SQLite")

    monkeypatch.setattr(detector, "ConnectorOutbox", UnexpectedSQLite)

    async def probe():
        calls["probe"] += 1
        return {"inquiries": []}

    async def worker(_work):
        calls["worker"] += 1

    async def reconcile():
        calls["reconcile"] += 1

    async def run():
        task = detector.asyncio.create_task(
            detector.supervise_replies(
                args, probe=probe, worker=worker, reconcile=reconcile, stop=stop,
            )
        )
        await detector.asyncio.sleep(0.04)
        stop.set()
        await task

    detector.asyncio.run(run())

    assert calls == {"probe": 0, "worker": 0, "reconcile": 0}


def test_manifest_wraps_only_four_business_lanes():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    jobs = {job["lane"]: job for job in manifest["jobs"]}
    business = {"apply", "negotiate", "storefront", "paid"}

    for lane in business:
        program = jobs[lane]["program"]
        assert program[0] == "{{PYTHON}}"
        assert program[1] == "{{RELEASE}}/skills/earn/gig/scripts/gig_disk_guard.py"
        assert program[2] == "{{PYTHON}}"

    for lane in {"browser", "release"}:
        program = jobs[lane]["program"]
        assert "gig_disk_guard.py" not in program
