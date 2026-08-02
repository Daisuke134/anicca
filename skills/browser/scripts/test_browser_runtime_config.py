"""Configuration seams required for one persistent browser per business loop."""
import fcntl
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cdp_context_lease as lease  # noqa: E402


def test_context_lease_uses_loop_specific_cdp_and_state(monkeypatch, tmp_path):
    monkeypatch.setenv("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9223")
    monkeypatch.setenv(
        "CLOAK_CONTEXT_LEASES_FILE", str(tmp_path / "gig-leases.json")
    )
    monkeypatch.setenv(
        "CLOAK_SESSION_VAULT_FILE", str(tmp_path / "gig-auth-state.json")
    )

    assert lease._cdp_base() == "http://127.0.0.1:9223"
    assert lease._leases_path() == str(tmp_path / "gig-leases.json")
    assert lease._vault_path() == str(tmp_path / "gig-auth-state.json")
    assert lease._page_ws("target-1") == (
        "ws://127.0.0.1:9223/devtools/page/target-1"
    )


def test_release_waits_for_active_target_operation(monkeypatch, tmp_path):
    leases_path = tmp_path / "gig-leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_path))
    leases_path.write_text(
        '{"gig":{"context_id":"context-1","target_id":"target-1"}}',
        encoding="utf-8",
    )
    calls = []

    async def fake_calls(pairs):
        calls.extend(pairs)
        return [{}]

    monkeypatch.setattr(lease, "_calls", fake_calls)
    lock_path = Path(lease._operation_lock_path("target-1"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    result = {}

    worker = threading.Thread(
        target=lambda: result.update(lease.release("gig")),
        daemon=True,
    )
    worker.start()
    time.sleep(0.05)

    assert worker.is_alive()
    assert calls == []

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    lock_handle.close()
    worker.join(timeout=1)

    assert result["ok"] is True
    assert calls[0][0] == "Target.disposeBrowserContext"


def test_acquire_returns_durable_fence_and_reuse_keeps_it(monkeypatch, tmp_path):
    leases_path = tmp_path / "gig-leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_path))
    monkeypatch.setenv("CLOAK_SESSION_VAULT_FILE", str(tmp_path / "missing.json"))

    responses = iter([
        [{"browserContextId": "context-1"}],
        [{"targetId": "target-1"}],
    ])

    async def fake_calls(_pairs):
        return next(responses)

    monkeypatch.setattr(lease, "_calls", fake_calls)
    first = lease.acquire("gig")
    second = lease.acquire("gig")

    assert re.fullmatch(r"[0-9a-f]{32}", first["token"])
    assert first["generation"] == 1
    assert second["reused"] is True
    assert second["token"] == first["token"]
    assert second["generation"] == first["generation"]
    stored = json.loads(leases_path.read_text(encoding="utf-8"))["gig"]
    assert stored["token"] == first["token"]
    assert stored["generation"] == 1


def test_heartbeat_and_release_reject_stale_fence(monkeypatch, tmp_path):
    leases_path = tmp_path / "gig-leases.json"
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(leases_path))
    leases_path.write_text(
        json.dumps({
            "gig": {
                "context_id": "context-1",
                "target_id": "target-1",
                "ws": "ws://127.0.0.1:9223/devtools/page/target-1",
                "ts": 1,
                "token": "a" * 32,
                "generation": 3,
            }
        }),
        encoding="utf-8",
    )
    calls = []

    async def fake_calls(pairs):
        calls.extend(pairs)
        return [{}]

    monkeypatch.setattr(lease, "_calls", fake_calls)

    stale_beat = lease.heartbeat("gig", token="b" * 32, generation=3)
    stale_release = lease.release("gig", token="a" * 32, generation=2)
    current_beat = lease.heartbeat("gig", token="a" * 32, generation=3)
    current_release = lease.release("gig", token="a" * 32, generation=3)

    assert stale_beat == {"ok": False, "reason": "lease_fence_mismatch"}
    assert stale_release == {"ok": False, "reason": "lease_fence_mismatch"}
    assert current_beat["ok"] is True
    assert current_release["ok"] is True
    assert calls == [("Target.disposeBrowserContext", {"browserContextId": "context-1"})]


def test_cli_heartbeat_accepts_parent_fence_flags(tmp_path):
    leases_path = tmp_path / "gig-leases.json"
    leases_path.write_text(
        json.dumps({
            "gig": {
                "context_id": "context-1",
                "target_id": "target-1",
                "ws": "ws://127.0.0.1:9223/devtools/page/target-1",
                "ts": 1,
                "token": "c" * 32,
                "generation": 4,
            }
        }),
        encoding="utf-8",
    )
    script = Path(lease.__file__)
    env = {**os.environ, "CLOAK_CONTEXT_LEASES_FILE": str(leases_path)}

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "heartbeat",
            "gig",
            "--token",
            "c" * 32,
            "--generation",
            "4",
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["generation"] == 4


def test_browser_guard_passes_owner_to_recovery_gc():
    source = (
        Path(__file__).resolve().parents[1] / "ensure_browser.sh"
    ).read_text(encoding="utf-8")

    assert 'CDP="${CLOAK_CDP_BASE_URL:-http://127.0.0.1:9222}"' in source
    assert 'cdp_tab_gc.py" --owner "$CLOAK_BROWSER_OWNER"' in source


def test_launchd_owned_browser_recovery_does_not_start_a_second_raw_process():
    source = (
        Path(__file__).resolve().parents[1] / "ensure_browser.sh"
    ).read_text(encoding="utf-8")

    assert 'CLOAK_BROWSER_LAUNCHD_LABEL' in source
    assert 'launchctl kickstart -k "gui/$(id -u)/$CLOAK_BROWSER_LAUNCHD_LABEL"' in source
    assert "wait_for_alive" in source
