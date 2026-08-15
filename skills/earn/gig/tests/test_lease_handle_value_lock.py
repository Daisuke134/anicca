"""Characterization test: LeaseHandle._value_lock serializes recycle() vs the
heartbeat background thread.

Root cause this guards against (measured 2026-08-08): recycle() used to do
release(old) -> acquire(new) -> self.value = value with no lock while
_heartbeat_loop read self.lease_fence and fired a subprocess heartbeat call on
its own thread every heartbeat_seconds. An in-flight heartbeat carrying the
old token could land on the new lease row after the swap -> lease_fence_mismatch
-> the heartbeat thread's except caught it and returned (thread died) ->
assert_healthy raised at the end of the B2 pass, killing it late.

This test does not go through a real subprocess (that idiom lives in
test_application_atomic_boundary.py::test_parent_lease_heartbeats_and_releases_in_finally).
Instead it monkeypatches the instance's _run with a slow fake so the race
window is deterministic instead of relying on subprocess timing.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
PARENT_SCRIPT = SCRIPTS / "application_parent.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_recycle_blocks_until_an_in_flight_heartbeat_finishes(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lease_lock_test")

    lease = parent.LeaseHandle(
        lease_script=tmp_path / "unused.py",
        task="gig-test-B2",
        heartbeat_seconds=0.01,
    )
    lease.value = {"token": "0" * 32, "generation": 1, "ws": "ws://leased-target"}

    events: list[tuple[str, str]] = []
    events_lock = threading.Lock()
    heartbeat_started = threading.Event()

    def fake_run(*arguments: str) -> dict[str, object]:
        command = arguments[0]
        with events_lock:
            events.append(("start", command))
        if command == "heartbeat":
            heartbeat_started.set()
            time.sleep(0.15)  # Held inside the lock: recycle() must wait it out.
        with events_lock:
            events.append(("end", command))
        if command == "acquire":
            return {"ok": True, "ws": "ws://recycled-target", "token": "1" * 32, "generation": 2}
        return {"ok": True}

    lease._run = fake_run  # instance attribute shadows the bound method; no self arg needed

    beat_thread = threading.Thread(target=lease._heartbeat_loop, daemon=True)
    beat_thread.start()
    try:
        assert heartbeat_started.wait(timeout=2.0), "heartbeat never fired"
        recycle_start = time.monotonic()
        new_ws = lease.recycle()
        recycle_elapsed = time.monotonic() - recycle_start
    finally:
        lease._stop.set()
        beat_thread.join(timeout=2.0)

    assert new_ws == "ws://recycled-target"
    # recycle() could only return this fast if it acquired the lock before the
    # 0.15s heartbeat sleep finished, i.e. they interleaved.
    assert recycle_elapsed >= 0.14, f"recycle() did not block on the in-flight heartbeat: {recycle_elapsed}s"

    # No interleaving: every command's own start/end pair is contiguous, and the
    # heartbeat's end always precedes the release/acquire pair recycle() issued
    # while a beat happened to be mid-flight.
    heartbeat_end_index = events.index(("end", "heartbeat"))
    release_start_index = events.index(("start", "release"))
    assert heartbeat_end_index < release_start_index, events


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_recycle_blocks_until_an_in_flight_heartbeat_finishes(Path(tmp))
    print("ok")
